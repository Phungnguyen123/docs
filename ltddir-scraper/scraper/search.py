"""Search execution: submit a query and collect candidate result links.

Uses ordered selector strategies from :class:`config.Settings` so the code
adapts to markup changes by adding a selector rather than editing logic. If the
site turns out to expose a JSON API, ``inspect.py`` will surface it and this
module can be pointed at it, but the DOM path below works without that.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING
from urllib.parse import urljoin

from .utils import get_logger

if TYPE_CHECKING:  # pragma: no cover - typing only
    from playwright.async_api import Page

    from config import Settings


@dataclass(frozen=True)
class Candidate:
    """A single search-result candidate."""

    name: str
    url: str


class SearchClient:
    """Performs a search on the directory and returns candidate companies."""

    def __init__(self, settings: "Settings") -> None:
        self._s = settings
        self._log = get_logger()

    async def search(self, page: "Page", query: str) -> list[Candidate]:
        """Search ``query`` and return de-duplicated candidate results.

        Navigates to the search page fresh each time for isolation, submits the
        query via the first working input/submit strategy, waits for results,
        then harvests candidate links.
        """
        await page.goto(
            self._s.search_url,
            wait_until="domcontentloaded",
            timeout=self._s.navigation_timeout_ms,
        )
        submitted = await self._submit_query(page, query)
        if not submitted:
            self._log.warning("Could not locate a search box; trying URL query param")
            await self._search_via_url(page, query)

        await self._wait_for_results(page)
        return await self._collect_candidates(page)

    # ------------------------------------------------------------------ #
    async def _submit_query(self, page: "Page", query: str) -> bool:
        """Fill the search box and submit. Returns False if no box was found."""
        box = await self._first_visible(page, self._s.search_input_selectors)
        if box is None:
            return False
        await box.click()
        await box.fill(query)

        submit = await self._first_visible(page, self._s.search_submit_selectors)
        if submit is not None:
            await submit.click()
        else:
            await box.press("Enter")
        return True

    async def _search_via_url(self, page: "Page", query: str) -> None:
        """Fallback: many directories accept ?q= / ?s= query params."""
        from urllib.parse import urlencode

        for param in ("q", "s", "query", "keyword", "search"):
            url = f"{self._s.search_url}?{urlencode({param: query})}"
            await page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self._s.navigation_timeout_ms,
            )
            if await self._has_any(page, self._s.result_item_selectors):
                return

    async def _wait_for_results(self, page: "Page") -> None:
        """Wait until either result items or detail links appear (best effort)."""
        try:
            await page.wait_for_load_state(
                "networkidle", timeout=self._s.selector_timeout_ms
            )
        except Exception:  # noqa: BLE001 - networkidle can legitimately time out
            pass

    async def _collect_candidates(self, page: "Page") -> list[Candidate]:
        """Harvest candidate (name, url) pairs from the results page."""
        candidates: list[Candidate] = []
        seen: set[str] = set()

        # Preferred path: structured result items with a link inside each.
        for item_sel in self._s.result_item_selectors:
            items = page.locator(item_sel)
            count = await items.count()
            if count == 0:
                continue
            for i in range(count):
                item = items.nth(i)
                link = await self._link_in(item)
                if link is None:
                    continue
                name, href = link
                url = urljoin(self._s.base_url, href)
                if url not in seen:
                    seen.add(url)
                    candidates.append(Candidate(name=name, url=url))
            if candidates:
                return candidates

        # Fallback: any anchor on the page pointing at a detail-style URL.
        anchors = page.locator("a[href]")
        count = await anchors.count()
        for i in range(count):
            a = anchors.nth(i)
            href = (await a.get_attribute("href")) or ""
            if any(p in href for p in self._s.detail_link_href_patterns):
                name = (await a.inner_text()).strip()
                url = urljoin(self._s.base_url, href)
                if name and url not in seen:
                    seen.add(url)
                    candidates.append(Candidate(name=name, url=url))
        return candidates

    async def _link_in(self, item) -> tuple[str, str] | None:  # noqa: ANN001
        """Return (text, href) of the first matching link inside a result item."""
        for link_sel in self._s.result_link_selectors:
            link = item.locator(link_sel).first
            if await link.count() == 0:
                continue
            href = await link.get_attribute("href")
            if not href:
                continue
            text = (await link.inner_text()).strip()
            if not text:
                text = (await item.inner_text()).strip().split("\n")[0]
            return text, href
        return None

    async def _first_visible(self, page: "Page", selectors: tuple[str, ...]):  # noqa: ANN001
        """Return the first visible locator among ``selectors``, or None."""
        for sel in selectors:
            loc = page.locator(sel).first
            try:
                if await loc.count() > 0 and await loc.is_visible():
                    return loc
            except Exception:  # noqa: BLE001
                continue
        return None

    async def _has_any(self, page: "Page", selectors: tuple[str, ...]) -> bool:
        """True if any of ``selectors`` matches at least one element."""
        for sel in selectors:
            if await page.locator(sel).count() > 0:
                return True
        return False
