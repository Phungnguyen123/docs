"""Official Companies House API client (the reliable alternative to scraping).

ltddir.com is a Cloudflare-protected aggregator of UK company data. The UK
registry itself — Companies House — exposes that same data through a free,
documented REST API with no anti-bot obstacles:

    https://developer.company-information.service.gov.uk/

This module wraps the three endpoints we need (search, company profile,
officers) and maps their JSON onto the same :class:`CompanyRecord` used by the
scraper, so the Excel output is identical regardless of data source.

Auth: register a free key, then pass it as the HTTP Basic *username* (empty
password). Set it via the ``CH_API_KEY`` environment variable.
"""

from __future__ import annotations

import time
from typing import Any

import requests

from .parser import CompanyRecord
from .utils import get_logger

API_BASE = "https://api.company-information.service.gov.uk"
WEB_BASE = "https://find-and-update.company-information.service.gov.uk"

# Human-readable labels for the most common company type / status codes.
_TYPE_LABELS: dict[str, str] = {
    "ltd": "Private Limited Company",
    "plc": "Public Limited Company",
    "llp": "Limited Liability Partnership",
    "private-unlimited": "Private Unlimited Company",
    "private-limited-guarant-nsc": "Private Limited by Guarantee (no share capital)",
    "community-interest-company": "Community Interest Company",
    "old-public-company": "Old Public Company",
}


class CompaniesHouseError(RuntimeError):
    """Raised for non-retryable API errors (e.g. bad key)."""


class CompaniesHouseClient:
    """Thin synchronous client over the Companies House REST API."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        backoff_base_s: float = 2.0,
    ) -> None:
        if not api_key:
            raise CompaniesHouseError(
                "Missing API key. Get a free key at "
                "https://developer.company-information.service.gov.uk/ and set CH_API_KEY."
            )
        self._session = requests.Session()
        self._session.auth = (api_key, "")  # key as username, empty password
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff_base_s
        self._log = get_logger()

    # ------------------------------------------------------------------ #
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any] | None:
        """GET a JSON endpoint with retries. Returns None on 404."""
        url = f"{API_BASE}{path}"
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(url, params=params, timeout=self._timeout)
                if resp.status_code == 404:
                    return None
                if resp.status_code == 429:
                    # Rate limited: honour Retry-After if present, else back off.
                    wait = float(resp.headers.get("Retry-After", self._backoff * (2**attempt)))
                    self._log.warning("Rate limited; sleeping %.0fs", wait)
                    time.sleep(wait)
                    continue
                if resp.status_code == 401:
                    raise CompaniesHouseError("401 Unauthorized — check CH_API_KEY.")
                resp.raise_for_status()
                return resp.json()
            except CompaniesHouseError:
                raise
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
        self._log.error("GET %s failed after retries: %s", path, last_exc)
        raise CompaniesHouseError(f"request failed: {last_exc}") from last_exc

    def search_companies(self, query: str, *, items: int = 20) -> list[dict[str, Any]]:
        """Return raw search-result items for ``query`` (may be empty)."""
        data = self._get("/search/companies", {"q": query, "items_per_page": items})
        return (data or {}).get("items", []) if data else []

    def get_profile(self, company_number: str) -> dict[str, Any] | None:
        """Return the company profile JSON, or None if not found."""
        return self._get(f"/company/{company_number}")

    def get_officers(self, company_number: str) -> list[dict[str, Any]]:
        """Return the company's officer items (directors, secretaries, ...)."""
        data = self._get(f"/company/{company_number}/officers", {"items_per_page": 100})
        return (data or {}).get("items", []) if data else []


# --------------------------------------------------------------------------- #
# Pure mappers (unit-tested without network)
# --------------------------------------------------------------------------- #
def format_address(addr: dict[str, Any] | None) -> str:
    """Join a registered-office-address dict into a single line."""
    if not addr:
        return ""
    parts = [
        addr.get("care_of"),
        addr.get("premises"),
        addr.get("address_line_1"),
        addr.get("address_line_2"),
        addr.get("locality"),
        addr.get("region"),
        addr.get("postal_code"),
        addr.get("country"),
    ]
    return ", ".join(str(p).strip() for p in parts if p and str(p).strip())


def split_officers(officers: list[dict[str, Any]]) -> tuple[str, str]:
    """Return (directors, secretaries) as comma-separated *active* names."""
    directors: list[str] = []
    secretaries: list[str] = []
    for off in officers:
        if off.get("resigned_on"):
            continue  # only currently-appointed officers
        role = str(off.get("officer_role", "")).lower()
        name = str(off.get("name", "")).strip()
        if not name:
            continue
        if "secretary" in role:
            secretaries.append(name)
        elif "director" in role:
            directors.append(name)
    return ", ".join(directors), ", ".join(secretaries)


def previous_names(profile: dict[str, Any]) -> str:
    """Join previous company names into a single string."""
    items = profile.get("previous_company_names") or []
    names = [str(i.get("name", "")).strip() for i in items if i.get("name")]
    return "; ".join(n for n in names if n)


def profile_to_record(
    profile: dict[str, Any],
    officers: list[dict[str, Any]],
    *,
    source_url: str,
) -> CompanyRecord:
    """Map a Companies House profile + officers into a :class:`CompanyRecord`."""
    directors, secretary = split_officers(officers)
    type_code = str(profile.get("type", ""))
    status = str(profile.get("company_status", "")).replace("-", " ").title()
    sic = profile.get("sic_codes") or []
    return CompanyRecord(
        company_name=str(profile.get("company_name", "")).strip(),
        company_number=str(profile.get("company_number", "")).strip(),
        company_status=status,
        company_type=_TYPE_LABELS.get(type_code, type_code),
        incorporation_date=str(profile.get("date_of_creation", "")).strip(),
        registered_address=format_address(profile.get("registered_office_address")),
        directors=directors,
        company_secretary=secretary,
        business_nature=", ".join(str(c) for c in sic),
        previous_names=previous_names(profile),
        remarks="",
        source_url=source_url,
    )


def company_web_url(company_number: str) -> str:
    """Return the public web URL for a company (used as Source URL)."""
    return f"{WEB_BASE}/company/{company_number}"
