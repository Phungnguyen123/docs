"""Best-effort web enrichment: guess a company's website and social profiles.

This is NOT official registry data. It queries a web-search API and applies
heuristics to pick a likely official website and LinkedIn/Facebook page from the
results. Treat every value as a *candidate* to verify by hand — company-name
collisions and companies with no web presence are common.

Two providers are supported, auto-detected from environment variables:

  * SerpAPI:            SERPAPI_KEY
  * Google Programmable Search (CSE):   GOOGLE_API_KEY  +  GOOGLE_CSE_ID

If neither is set, enrichment is disabled and columns stay blank.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import requests

from .utils import get_logger, normalize_name

# Domains that are never the company's own website (directories, socials, etc.).
_EXCLUDE_DOMAINS = (
    "linkedin.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "youtube.com", "tiktok.com", "opencorporates.com", "ltddir.com",
    "gov.hk", "companieshouse.gov.uk", "find-and-update.company-information.service.gov.uk",
    "bloomberg.com", "crunchbase.com", "dnb.com", "tofler.in", "zaubacorp.com",
    "glassdoor.com", "indeed.com", "wikipedia.org", "google.com", "yelp.com",
    "companieshouse.hk", "hkgioc.com", "webb-site.com",
)


@dataclass
class WebPresence:
    """Best-effort web presence for a company."""

    website: str = ""
    linkedin: str = ""
    facebook: str = ""

    def social(self) -> str:
        """Return social links joined for a single spreadsheet cell."""
        return " | ".join(x for x in (self.linkedin, self.facebook) if x)


def registrable_domain(url: str) -> str:
    """Return the lowercased host of a URL without a leading 'www.'."""
    try:
        host = urlparse(url).netloc.lower()
    except ValueError:
        return ""
    return host[4:] if host.startswith("www.") else host


def _is_excluded(url: str) -> bool:
    host = registrable_domain(url)
    return any(host == d or host.endswith("." + d) for d in _EXCLUDE_DOMAINS)


def pick_website(results: list[dict[str, str]], company_name: str) -> str:
    """Choose the most likely official website from search results.

    Prefers a non-excluded domain that shares a word with the company name;
    otherwise the first non-excluded result.
    """
    tokens = {t for t in normalize_name(company_name).split() if len(t) > 2}
    fallback = ""
    for r in results:
        link = r.get("link", "")
        if not link or _is_excluded(link):
            continue
        if not fallback:
            fallback = link
        host = registrable_domain(link)
        host_core = host.split(".")[0]
        if any(tok in host_core or host_core in tok for tok in tokens):
            return link
    return fallback


def _first_matching(results: list[dict[str, str]], needle: str) -> str:
    """Return the first result link whose host matches ``needle``."""
    for r in results:
        link = r.get("link", "")
        if needle in registrable_domain(link):
            return link
    return ""


def pick_social(results: list[dict[str, str]]) -> tuple[str, str]:
    """Return (linkedin_url, facebook_url) from search results, if present."""
    return _first_matching(results, "linkedin.com"), _first_matching(results, "facebook.com")


def extract_presence(results: list[dict[str, str]], company_name: str) -> WebPresence:
    """Apply all heuristics to a normalised result list."""
    linkedin, facebook = pick_social(results)
    return WebPresence(
        website=pick_website(results, company_name),
        linkedin=linkedin,
        facebook=facebook,
    )


class WebEnricher:
    """Queries a web-search API and extracts a best-effort web presence."""

    def __init__(self, *, timeout_s: float = 20.0, max_retries: int = 2, backoff_base_s: float = 2.0) -> None:
        self._log = get_logger()
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff_base_s
        self._serpapi_key = os.environ.get("SERPAPI_KEY", "")
        self._google_key = os.environ.get("GOOGLE_API_KEY", "")
        self._google_cx = os.environ.get("GOOGLE_CSE_ID", "")
        self._session = requests.Session()

    def enabled(self) -> bool:
        """True if a supported search provider is configured."""
        return bool(self._serpapi_key or (self._google_key and self._google_cx))

    def provider(self) -> str:
        """Name of the active provider (for logging)."""
        if self._serpapi_key:
            return "serpapi"
        if self._google_key and self._google_cx:
            return "google_cse"
        return "none"

    def raw_results(self, query: str) -> list[dict[str, str]]:
        """Return normalised [{title, link, snippet}] results for ``query``."""
        if self._serpapi_key:
            data = self._get(
                "https://serpapi.com/search.json",
                {"q": query, "api_key": self._serpapi_key, "num": 10, "engine": "google"},
            )
            return _normalize_serpapi(data)
        if self._google_key and self._google_cx:
            data = self._get(
                "https://www.googleapis.com/customsearch/v1",
                {"q": query, "key": self._google_key, "cx": self._google_cx, "num": 10},
            )
            return _normalize_google(data)
        return []

    def find_presence(self, company_name: str, *, region_hint: str = "") -> WebPresence:
        """Search for a company and return its best-effort web presence."""
        query = f'"{company_name}"'
        if region_hint:
            query += f" {region_hint}"
        try:
            results = self.raw_results(query)
        except requests.RequestException as exc:
            self._log.warning("Web enrichment failed for %s: %s", company_name, exc)
            return WebPresence()
        return extract_presence(results, company_name)

    def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """GET JSON with light retries."""
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
        raise requests.RequestException(str(last_exc))


def _normalize_serpapi(data: dict[str, Any]) -> list[dict[str, str]]:
    """Normalise a SerpAPI response to [{title, link, snippet}]."""
    out: list[dict[str, str]] = []
    for r in data.get("organic_results", []) or []:
        out.append(
            {
                "title": str(r.get("title", "")),
                "link": str(r.get("link", "")),
                "snippet": str(r.get("snippet", "")),
            }
        )
    return out


def _normalize_google(data: dict[str, Any]) -> list[dict[str, str]]:
    """Normalise a Google CSE response to [{title, link, snippet}]."""
    out: list[dict[str, str]] = []
    for r in data.get("items", []) or []:
        out.append(
            {
                "title": str(r.get("title", "")),
                "link": str(r.get("link", "")),
                "snippet": str(r.get("snippet", "")),
            }
        )
    return out
