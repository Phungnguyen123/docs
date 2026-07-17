"""Pure helper utilities: logging, text normalisation, similarity, retries.

Nothing in here touches Playwright or the network, so every function is
directly unit-testable offline.
"""

from __future__ import annotations

import asyncio
import logging
import random
import re
import string
import unicodedata
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")

_LOGGER_NAME = "ltddir"
_PUNCT_TABLE = str.maketrans("", "", string.punctuation)


# --------------------------------------------------------------------------- #
# Logging
# --------------------------------------------------------------------------- #
def setup_logging(log_file: Path, *, verbose: bool = False) -> logging.Logger:
    """Configure and return the package logger.

    Logs go both to ``log_file`` and stderr. Calling this repeatedly is safe;
    handlers are only attached once.
    """
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_LOGGER_NAME)
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

    if not logger.handlers:
        fmt = logging.Formatter(
            "%(asctime)s | %(levelname)-7s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(fmt)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(fmt)
        logger.addHandler(stream_handler)

    logger.propagate = False
    return logger


def get_logger() -> logging.Logger:
    """Return the shared package logger (assumes ``setup_logging`` ran)."""
    return logging.getLogger(_LOGGER_NAME)


# --------------------------------------------------------------------------- #
# Text normalisation & matching
# --------------------------------------------------------------------------- #
def normalize_name(name: str) -> str:
    """Normalise a company name for comparison.

    Lowercases, strips accents, removes punctuation, and collapses repeated
    whitespace so that "Foo  Ltd." and "foo ltd" compare equal.
    """
    if not name:
        return ""
    decomposed = unicodedata.normalize("NFKD", name)
    ascii_name = decomposed.encode("ascii", "ignore").decode("ascii")
    lowered = ascii_name.lower().translate(_PUNCT_TABLE)
    return re.sub(r"\s+", " ", lowered).strip()


def similarity(a: str, b: str) -> float:
    """Return a 0..1 similarity ratio between two names after normalisation."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    return SequenceMatcher(None, na, nb).ratio()


@dataclass(frozen=True)
class MatchResult:
    """Outcome of matching an input name against candidate result names."""

    matched_name: str
    confidence: float
    status: str  # "exact" | "fuzzy" | "low_confidence" | "not_found"
    index: int  # position of the chosen candidate, -1 if none


def choose_best_match(
    query: str,
    candidates: list[str],
    *,
    min_confidence: float,
    strong_confidence: float,
) -> MatchResult:
    """Pick the best candidate name for ``query``.

    Preference order: exact normalised match, then highest similarity. The
    returned status distinguishes exact / fuzzy / low-confidence / not-found.
    """
    if not candidates:
        return MatchResult("", 0.0, "not_found", -1)

    norm_query = normalize_name(query)
    scored = [(similarity(query, c), i, c) for i, c in enumerate(candidates)]

    # Exact normalised matches win outright.
    exacts = [(s, i, c) for s, i, c in scored if normalize_name(c) == norm_query]
    if exacts:
        _, idx, name = exacts[0]
        return MatchResult(name, 1.0, "exact", idx)

    score, idx, name = max(scored, key=lambda t: t[0])
    if score >= strong_confidence:
        status = "fuzzy"
    elif score >= min_confidence:
        status = "fuzzy"
    else:
        status = "low_confidence"
    return MatchResult(name, round(score, 4), status, idx)


# --------------------------------------------------------------------------- #
# Timing & retries
# --------------------------------------------------------------------------- #
async def random_delay(min_s: float, max_s: float) -> None:
    """Sleep for a random duration in ``[min_s, max_s]`` seconds."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def wait_for_challenge_clear(page, *, timeout_s: float = 40.0) -> bool:  # noqa: ANN001
    """Poll until an anti-bot challenge clears, or ``timeout_s`` elapses.

    A real (headed) browser often auto-solves Cloudflare's managed challenge
    within a few seconds; this waits for that to happen. Returns True if the
    page is no longer a challenge, False if it still looks blocked.
    """
    logger = get_logger()
    deadline_steps = max(1, int(timeout_s / 2))
    for step in range(deadline_steps):
        try:
            url = page.url
            body = await page.evaluate(
                "() => (document.body ? document.body.innerText : '')"
            )
        except Exception:  # noqa: BLE001 - transient during redirects
            body = ""
            url = ""
        if url and not looks_like_challenge(url, None, body) and len(body) > 200:
            if step:
                logger.info("Challenge cleared after ~%ds", step * 2)
            return True
        await asyncio.sleep(2.0)
    return False


# --------------------------------------------------------------------------- #
# Cloudflare / anti-bot handling
# --------------------------------------------------------------------------- #
# URL fragments Cloudflare adds while it runs a challenge.
CLOUDFLARE_URL_MARKERS = ("__cf_chl", "cf_chl_rt_tk", "cf_chl_jschl")

# Text that appears on interstitial / block pages.
ANTIBOT_TEXT_SIGNALS = (
    "just a moment",
    "checking your browser",
    "enable javascript and cookies",
    "cloudflare",
    "captcha",
    "are you a robot",
    "access denied",
    "attention required",
    "rate limit",
    "too many requests",
)

# JS injected before page scripts run to reduce trivial automation fingerprints.
STEALTH_INIT_SCRIPT = """
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
window.chrome = window.chrome || {runtime: {}};
"""

# Launch args that hide the "AutomationControlled" blink feature.
STEALTH_LAUNCH_ARGS = (
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
)


def looks_like_challenge(url: str, status: int | None, body_text: str) -> bool:
    """Heuristically decide whether the current page is an anti-bot challenge."""
    if any(m in url for m in CLOUDFLARE_URL_MARKERS):
        return True
    if status is not None and status in (403, 429, 503):
        return True
    low = (body_text or "").lower()
    return any(sig in low for sig in ANTIBOT_TEXT_SIGNALS)


class RetryError(RuntimeError):
    """Raised when all retry attempts are exhausted."""


async def retry_async(
    func: Callable[[], Awaitable[T]],
    *,
    retries: int,
    backoff_base_s: float,
    exceptions: tuple[type[BaseException], ...],
    on_retry: Callable[[int, BaseException], None] | None = None,
) -> T:
    """Run ``func`` with exponential-backoff retries.

    Retries only on ``exceptions``. Waits ``backoff_base_s * 2**attempt``
    seconds between tries. Raises :class:`RetryError` if all attempts fail.
    """
    last_exc: BaseException | None = None
    for attempt in range(retries + 1):
        try:
            return await func()
        except exceptions as exc:  # noqa: PERF203 - retry loop is intentional
            last_exc = exc
            if on_retry is not None:
                on_retry(attempt + 1, exc)
            if attempt < retries:
                await asyncio.sleep(backoff_base_s * (2**attempt))
    raise RetryError(f"Exhausted {retries} retries") from last_exc
