"""Central configuration for the LTDDir scraper.

Everything site-specific lives here so the crawler/parser code stays generic.
After running ``inspect.py`` against the live site you can override any of the
selector lists below without touching the rest of the codebase.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------- #
# Paths
# --------------------------------------------------------------------------- #
BASE_DIR: Path = Path(__file__).resolve().parent
INPUT_FILE: Path = BASE_DIR / "input" / "companies.xlsx"
OUTPUT_FILE: Path = BASE_DIR / "output" / "result.xlsx"
PROGRESS_FILE: Path = BASE_DIR / "output" / "_progress.jsonl"
LOG_FILE: Path = BASE_DIR / "logs" / "scraper.log"


@dataclass(frozen=True)
class Settings:
    """Runtime settings for a scraping run."""

    # --- Target site ------------------------------------------------------- #
    base_url: str = "https://www.ltddir.com"
    search_url: str = "https://www.ltddir.com/companies/"

    # --- Browser ----------------------------------------------------------- #
    headless: bool = True
    # Optional explicit Chromium binary. Leave None to use the one installed by
    # ``playwright install``. Set it (or the env var below) for environments
    # with a pinned/pre-installed browser.
    chromium_executable_path: str | None = os.environ.get("PLAYWRIGHT_CHROMIUM_EXECUTABLE") or None
    # A realistic desktop UA reduces trivial bot blocking.
    user_agent: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    locale: str = "en-US"
    viewport_width: int = 1366
    viewport_height: int = 900

    # --- Timeouts (milliseconds) ------------------------------------------ #
    navigation_timeout_ms: int = 30_000
    selector_timeout_ms: int = 15_000

    # --- Reliability ------------------------------------------------------- #
    max_retries: int = 3
    retry_backoff_base_s: float = 2.0  # 2s, 4s, 8s
    delay_min_s: float = 1.0
    delay_max_s: float = 3.0
    # How long to wait for an anti-bot (e.g. Cloudflare) challenge to auto-solve
    # in a real browser before treating the company as blocked.
    challenge_wait_s: float = 40.0

    # --- Matching ---------------------------------------------------------- #
    # Below this similarity a match is recorded as "low_confidence".
    min_confidence: float = 0.60
    # At/above this an inexact candidate is treated as a confident fuzzy match.
    strong_confidence: float = 0.85

    # --- Selector strategies ---------------------------------------------- #
    # Ordered lists of candidate selectors. The crawler tries each in turn and
    # uses the first that matches, so an update to the site only needs a new
    # entry here. Populate/curate these from ``inspect.py`` output.
    search_input_selectors: tuple[str, ...] = (
        "input[type='search']",
        "input[name='q']",
        "input[name='query']",
        "input[name='s']",
        "input[name='keyword']",
        "input[name='company']",
        "form[role='search'] input[type='text']",
        "input[placeholder*='ompany' i]",
        "input[placeholder*='earch' i]",
    )
    search_submit_selectors: tuple[str, ...] = (
        "button[type='submit']",
        "input[type='submit']",
        "form[role='search'] button",
        "button[aria-label*='earch' i]",
    )
    # Containers that wrap an individual search result.
    result_item_selectors: tuple[str, ...] = (
        "ul.companies li",
        ".search-results .result",
        ".company-list .company",
        ".results li",
        "table.companies tbody tr",
        "article.company",
    )
    # Anchor pointing at a company detail page, relative to a result item.
    result_link_selectors: tuple[str, ...] = (
        "a[href*='/company/']",
        "a[href*='/companies/']",
        "h2 a",
        "h3 a",
        "a",
    )
    # Fallback: any anchor on the results page that points at a detail page.
    detail_link_href_patterns: tuple[str, ...] = (
        "/company/",
        "/companies/",
    )

    # Field labels expected on a company detail page. The parser matches these
    # case-insensitively against label text, so minor wording changes are fine.
    field_label_map: dict[str, tuple[str, ...]] = field(
        default_factory=lambda: {
            "company_number": ("company number", "registration number", "company no", "number"),
            "company_status": ("company status", "status"),
            "company_type": ("company type", "type", "category"),
            "incorporation_date": (
                "incorporation date",
                "incorporated",
                "date of incorporation",
                "registration date",
                "registered",
            ),
            "registered_address": (
                "registered address",
                "registered office address",
                "address",
                "office address",
            ),
            "directors": ("directors", "director", "officers", "people"),
            "company_secretary": ("company secretary", "secretary"),
            "business_nature": (
                "nature of business",
                "business nature",
                "sic",
                "industry",
                "activities",
            ),
            "previous_names": (
                "previous company names",
                "previous names",
                "former names",
                "also known as",
            ),
            "remarks": ("remarks", "notes", "comments"),
        }
    )

    def delay_bounds(self) -> tuple[float, float]:
        """Return the (min, max) inter-request delay in seconds."""
        return self.delay_min_s, self.delay_max_s


# Importable default instance. Override attributes by constructing a new
# ``Settings(headless=False, ...)`` and passing it into the crawler.
SETTINGS = Settings()
