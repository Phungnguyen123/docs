"""Browser orchestration for a single company and the overall run.

``Crawler`` owns the Playwright browser/context lifecycle. For each company it
searches, chooses the best match, opens the detail page, and parses it — all
wrapped in retry logic. Any failure for one company is caught and recorded so
the run never aborts midway.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from types import TracebackType
from typing import TYPE_CHECKING

from playwright.async_api import (
    Error as PlaywrightError,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from .parser import CompanyRecord, parse_company_page
from .search import Candidate, SearchClient
from .utils import (
    MatchResult,
    RetryError,
    choose_best_match,
    get_logger,
    random_delay,
    retry_async,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.async_api import Browser, BrowserContext, Page

    from config import Settings

# Exceptions worth retrying (transient navigation / network / timeouts).
RETRYABLE: tuple[type[BaseException], ...] = (PlaywrightTimeoutError, PlaywrightError)


@dataclass
class CompanyOutcome:
    """Everything produced for one input company, ready to be serialised."""

    input_name: str
    match: MatchResult
    record: CompanyRecord
    duration_s: float

    def to_row(self) -> dict[str, str]:
        """Serialise into the exporter's canonical column dict."""
        r = self.record
        return {
            "Input Company Name": self.input_name,
            "Matched Company Name": self.match.matched_name,
            "Match Status": self.match.status,
            "Confidence Score": f"{self.match.confidence:.4f}",
            "Company Number": r.company_number,
            "Company Type": r.company_type,
            "Company Status": r.company_status,
            "Incorporation Date": r.incorporation_date,
            "Registered Address": r.registered_address,
            "Directors": r.directors,
            "Company Secretary": r.company_secretary,
            "Business Nature": r.business_nature,
            "Previous Names": r.previous_names,
            "Remarks": r.remarks,
            "Source URL": r.source_url,
            "Crawl Timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }


class AntiBotError(RuntimeError):
    """Raised when a bot-block page (Cloudflare/CAPTCHA/etc.) is detected."""


class Crawler:
    """Async context manager that scrapes companies one at a time."""

    def __init__(self, settings: "Settings") -> None:
        self._s = settings
        self._log = get_logger()
        self._search = SearchClient(settings)
        self._pw = None
        self._browser: "Browser | None" = None
        self._context: "BrowserContext | None" = None

    async def __aenter__(self) -> "Crawler":
        self._pw = await async_playwright().start()
        launch_kwargs: dict[str, object] = {"headless": self._s.headless}
        if self._s.chromium_executable_path:
            launch_kwargs["executable_path"] = self._s.chromium_executable_path
        self._browser = await self._pw.chromium.launch(**launch_kwargs)
        self._context = await self._browser.new_context(
            user_agent=self._s.user_agent,
            locale=self._s.locale,
            viewport={"width": self._s.viewport_width, "height": self._s.viewport_height},
        )
        self._context.set_default_timeout(self._s.selector_timeout_ms)
        self._context.set_default_navigation_timeout(self._s.navigation_timeout_ms)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()

    # ------------------------------------------------------------------ #
    async def process_company(self, input_name: str) -> CompanyOutcome:
        """Search, match, open, and parse one company. Never raises.

        Failures are converted into a ``not_found`` outcome with the error in
        the Remarks field so the run continues.
        """
        start = time.monotonic()
        self._log.info("Processing: %s", input_name)
        try:
            outcome = await self._process_with_retries(input_name)
        except RetryError as exc:
            self._log.error("FAILURE: %s -> %s", input_name, exc)
            outcome = self._failure_outcome(input_name, f"error: {exc}", start)
        except AntiBotError as exc:
            self._log.error("BLOCKED: %s -> %s", input_name, exc)
            outcome = self._failure_outcome(input_name, f"blocked: {exc}", start)
        except Exception as exc:  # noqa: BLE001 - last-resort guard, must not abort run
            self._log.exception("UNEXPECTED FAILURE: %s", input_name)
            outcome = self._failure_outcome(input_name, f"unexpected: {exc}", start)

        outcome.duration_s = time.monotonic() - start
        self._log.info(
            "Done: %s | status=%s confidence=%.3f | %.1fs",
            input_name,
            outcome.match.status,
            outcome.match.confidence,
            outcome.duration_s,
        )
        return outcome

    # ------------------------------------------------------------------ #
    async def _process_with_retries(self, input_name: str) -> CompanyOutcome:
        """Run the per-company pipeline under retry_async."""

        def _on_retry(attempt: int, exc: BaseException) -> None:
            self._log.warning(
                "Retry %d/%d for %s: %s",
                attempt,
                self._s.max_retries,
                input_name,
                exc,
            )

        async def _attempt() -> CompanyOutcome:
            return await self._run_pipeline(input_name)

        return await retry_async(
            _attempt,
            retries=self._s.max_retries,
            backoff_base_s=self._s.retry_backoff_base_s,
            exceptions=RETRYABLE,
            on_retry=_on_retry,
        )

    async def _run_pipeline(self, input_name: str) -> CompanyOutcome:
        """The single-attempt pipeline: search -> match -> parse."""
        assert self._context is not None
        page = await self._context.new_page()
        try:
            await self._guard_anti_bot(page, before_navigation=False)
            candidates = await self._search.search(page, input_name)
            await self._guard_anti_bot(page, before_navigation=False)

            match = choose_best_match(
                input_name,
                [c.name for c in candidates],
                min_confidence=self._s.min_confidence,
                strong_confidence=self._s.strong_confidence,
            )
            if match.index < 0 or match.status == "not_found":
                return CompanyOutcome(input_name, match, CompanyRecord(), 0.0)

            chosen: Candidate = candidates[match.index]
            await page.goto(
                chosen.url,
                wait_until="domcontentloaded",
                timeout=self._s.navigation_timeout_ms,
            )
            await self._guard_anti_bot(page, before_navigation=False)

            record = await parse_company_page(
                page,
                self._s.field_label_map,
                source_url=chosen.url,
                fallback_name=chosen.name,
            )
            if match.status == "low_confidence":
                record.remarks = _join_remark(
                    record.remarks, "low-confidence match; verify manually"
                )
            return CompanyOutcome(input_name, match, record, 0.0)
        finally:
            await page.close()

    async def _guard_anti_bot(self, page: "Page", *, before_navigation: bool) -> None:
        """Detect common bot-block pages and raise :class:`AntiBotError`."""
        try:
            title = (await page.title()) or ""
            body = await page.evaluate(
                "() => (document.body ? document.body.innerText : '').slice(0, 400)"
            )
        except Exception:  # noqa: BLE001 - detection must never itself crash
            return
        haystack = f"{title}\n{body}".lower()
        signals = (
            "just a moment",
            "checking your browser",
            "cloudflare",
            "captcha",
            "are you a robot",
            "access denied",
            "rate limit",
            "too many requests",
        )
        if any(sig in haystack for sig in signals):
            raise AntiBotError(f"bot-block signal in page: {title!r}")

    async def polite_pause(self) -> None:
        """Sleep a random 1-3s between companies to be a good citizen."""
        await random_delay(*self._s.delay_bounds())

    def _failure_outcome(
        self, input_name: str, remark: str, start: float
    ) -> CompanyOutcome:
        """Build a not-found outcome carrying an explanatory remark."""
        record = CompanyRecord(remarks=remark)
        match = MatchResult("", 0.0, "not_found", -1)
        return CompanyOutcome(input_name, match, record, time.monotonic() - start)


def _join_remark(existing: str, addition: str) -> str:
    """Append a remark, separating with '; ' if there is existing text."""
    existing = (existing or "").strip()
    return f"{existing}; {addition}" if existing else addition
