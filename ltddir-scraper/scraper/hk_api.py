"""Live client for the Hong Kong Companies Registry open API (data.cr.gov.hk).

data.gov.hk serves the "Registered Office Address of Live Local Companies"
dataset as a **searchable open API** (no key required) rather than a bulk file:

    https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/local/search
      ?query[0][key1]=Comp_name        # search field: Comp_name | Brn
      &query[0][key2]=begins_with      # operator: begins_with | equal
      &query[0][key3]=<company name>
      &format=json

The JSON field names are not published in a fetchable form, so this client uses
**keyword-tolerant extraction** (like the rest of this project) and ships a
``--probe`` mode (see main_hk.py) that dumps the raw response so the mapping can
be confirmed against reality. Extraction keywords are easy to adjust once the
real shape is seen.

Provides: company number (BRN), English name, registered office address, live
status. NOT directors/secretary/incorporation date (those need paid ICRIS).
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

from .parser import CompanyRecord
from .utils import MatchResult, choose_best_match, get_logger, normalize_name

API_LOCAL = "https://data.cr.gov.hk/cr/api/api/v1/api_builder/json/local/search"
DATASET_URL = "https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr"

# Legal suffixes stripped to build a broader "begins_with" query.
_LEGAL_SUFFIXES = ("limited", "ltd", "ltd.", "company", "co", "co.")

# Keyword hints for tolerant field extraction from a result record.
# (Confirmed against real API fields: Brn, English_Company_Name,
#  Address_of_Registered_Office, Company_Type, Date_of_Incorporation.)
_NUMBER_HINTS = ("brn", "cr_no", "crno", "cr no", "company_number", "reg_no", "number")
_NAME_EN_HINTS = ("english", "name_eng", "name_en", "eng_name", "comp_name_eng")
_NAME_ANY_HINTS = ("comp_name", "company_name", "name")
_CHINESE_HINTS = ("chi", "chinese", "_tc", "_sc", "中文")
_ADDRESS_HINTS = ("addr", "address")
_TYPE_HINTS = ("company_type", "comp_type", "type")
_INCORP_HINTS = ("date_of_incorporation", "incorporation", "incorp")
# Values that mean "empty" in this API (it returns the literal string "NULL").
_NULL_TOKENS = {"", "null", "none", "n/a", "nil"}


class HKApiError(RuntimeError):
    """Raised for non-recoverable API errors."""


class HKCrApiClient:
    """Thin client over the CR open search API for live local companies."""

    def __init__(
        self,
        *,
        timeout_s: float = 30.0,
        max_retries: int = 3,
        backoff_base_s: float = 2.0,
    ) -> None:
        self._session = requests.Session()
        self._session.headers.update({"Accept": "application/json"})
        self._timeout = timeout_s
        self._max_retries = max_retries
        self._backoff = backoff_base_s
        self._log = get_logger()

    def raw_search(self, value: str, *, key: str = "Comp_name", op: str = "begins_with") -> Any:
        """Return the raw decoded JSON for one query (used by --probe)."""
        params = {
            "query[0][key1]": key,
            "query[0][key2]": op,
            "query[0][key3]": value,
            "format": "json",
        }
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._session.get(API_LOCAL, params=params, timeout=self._timeout)
                if resp.status_code == 429:
                    wait = float(resp.headers.get("Retry-After", self._backoff * (2**attempt)))
                    self._log.warning("Rate limited; sleeping %.0fs", wait)
                    time.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except (requests.RequestException, ValueError) as exc:
                last_exc = exc
                if attempt < self._max_retries:
                    time.sleep(self._backoff * (2**attempt))
        raise HKApiError(f"API request failed: {last_exc}")

    def search_companies(self, name: str) -> list[dict[str, Any]]:
        """Return candidate record dicts for ``name``.

        Tries an exact-prefix search on the full name first, then falls back to
        the name without its legal suffix to catch LTD/LIMITED variations.
        """
        records = extract_records(self.raw_search(name, op="begins_with"))
        if not records:
            core = strip_legal_suffix(name)
            if core and core != name:
                records = extract_records(self.raw_search(core, op="begins_with"))
        return records


# --------------------------------------------------------------------------- #
# Pure helpers (unit-tested without network)
# --------------------------------------------------------------------------- #
def strip_legal_suffix(name: str) -> str:
    """Remove a trailing legal suffix (LIMITED/LTD/...) from ``name``."""
    tokens = name.strip().split()
    while tokens and tokens[-1].lower().strip(".,") in {s.strip(".") for s in _LEGAL_SUFFIXES}:
        tokens.pop()
    return " ".join(tokens)


def extract_records(data: Any) -> list[dict[str, Any]]:
    """Pull the list of record dicts out of an arbitrary API response shape."""
    if data is None:
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    if isinstance(data, dict):
        # Common container keys used by data.gov.hk / api_builder responses.
        for key in ("result", "results", "data", "records", "items", "rows", "response"):
            val = data.get(key)
            if isinstance(val, list):
                return [r for r in val if isinstance(r, dict)]
            if isinstance(val, dict):
                nested = extract_records(val)
                if nested:
                    return nested
        # Fall back to the first list-of-dicts value anywhere in the dict.
        for val in data.values():
            if isinstance(val, list) and val and isinstance(val[0], dict):
                return val
    return []


def clean_value(value: Any) -> str:
    """Trim a value and treat the API's literal 'NULL' etc. as empty."""
    s = "" if value is None else str(value).strip()
    return "" if s.lower() in _NULL_TOKENS else s


def normalize_date(value: str) -> str:
    """Convert a DD-MM-YYYY date (as the API returns) to ISO YYYY-MM-DD."""
    m = re.match(r"^(\d{2})-(\d{2})-(\d{4})$", value.strip())
    if m:
        day, month, year = m.groups()
        return f"{year}-{month}-{day}"
    return value.strip()


def _find_field(record: dict[str, Any], hints: tuple[str, ...], *, exclude: tuple[str, ...] = ()) -> str:
    """Return the value of the first key whose name matches a hint."""
    for k, v in record.items():
        low = str(k).lower()
        if any(x in low for x in exclude):
            continue
        cleaned = clean_value(v)
        if any(h in low for h in hints) and cleaned:
            return cleaned
    return ""


def record_english_name(record: dict[str, Any]) -> str:
    """Best-effort English company name from a record."""
    return (
        _find_field(record, _NAME_EN_HINTS)
        or _find_field(record, _NAME_ANY_HINTS, exclude=_CHINESE_HINTS)
    )


def record_to_company(record: dict[str, Any]) -> CompanyRecord:
    """Map an API record dict into a :class:`CompanyRecord` (tolerant)."""
    address = ", ".join(
        clean_value(v)
        for k, v in record.items()
        if any(h in str(k).lower() for h in _ADDRESS_HINTS) and clean_value(v)
    )
    return CompanyRecord(
        company_name=record_english_name(record),
        company_number=_find_field(record, _NUMBER_HINTS),
        company_status="Live",
        company_type=_find_field(record, _TYPE_HINTS),
        incorporation_date=normalize_date(_find_field(record, _INCORP_HINTS)),
        registered_address=address,
        remarks="from data.gov.hk CR API (no directors/secretary)",
        source_url=DATASET_URL,
    )


def match_records(
    query: str,
    records: list[dict[str, Any]],
    *,
    min_confidence: float,
    strong_confidence: float,
) -> tuple[dict[str, Any] | None, MatchResult]:
    """Choose the best record for ``query`` by English-name similarity."""
    names = [record_english_name(r) for r in records]
    indexed = [(n, r) for n, r in zip(names, records) if n]
    if not indexed:
        return None, MatchResult("", 0.0, "not_found", -1)
    match = choose_best_match(
        query,
        [n for n, _ in indexed],
        min_confidence=min_confidence,
        strong_confidence=strong_confidence,
    )
    if match.index < 0:
        return None, MatchResult("", 0.0, "not_found", -1)
    return indexed[match.index][1], match
