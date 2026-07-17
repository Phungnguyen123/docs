"""Hong Kong company lookup from the free data.gov.hk open dataset.

Hong Kong's official registry (ICRIS) has no free API — detailed particulars
(directors, secretary) are pay-per-document. But the Companies Registry
publishes a **free** open dataset on data.gov.hk:

    "Registered Office Address of Live Local Companies"
    https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr

It contains, for every *live* local company: the company number (CR No. / BRN),
the English (and Chinese) name, and the registered office address — free for
commercial and non-commercial re-use, updated daily.

This module loads that CSV/XLSX locally and matches your input names against it.
Because the exact header names can change (e.g. CR No. vs BRN after the 2023 UBI
change), columns are **auto-detected** by keyword rather than hard-coded; run
``main_hk.py --show-columns`` to see what was detected, and override in
``config.py`` if needed.

Fields available: Company Number, Registered Address, Company Status (Live).
NOT available here (needs paid ICRIS): directors, secretary, incorporation date.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .parser import CompanyRecord
from .utils import MatchResult, choose_best_match, get_logger, normalize_name

DATASET_URL = "https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr"

# Header keywords used to auto-detect columns (checked case-insensitively).
_NUMBER_KEYWORDS = ("cr no", "cr number", "brn", "business registration", "company number", "registration no")
_NAME_EN_KEYWORDS = ("english company name", "company name (english)", "english name", "company name in english")
_NAME_GENERIC_KEYWORDS = ("company name", "name of company", "name")
_CHINESE_HINT = ("chinese", "中文")
_ADDRESS_KEYWORDS = ("registered office address", "principal place", "address")


@dataclass(frozen=True)
class HKColumns:
    """Detected column names for the HK dataset."""

    number: str | None
    name_en: str | None
    address: tuple[str, ...]  # one or more columns joined for the full address

    def is_usable(self) -> bool:
        """True if at least a name column was found (number/address optional)."""
        return self.name_en is not None


def detect_columns(columns: list[str]) -> HKColumns:
    """Auto-detect the number / English-name / address columns from headers."""
    lowered = {c: str(c).strip().lower() for c in columns}

    def first_match(keywords: tuple[str, ...], *, exclude_chinese: bool = False) -> str | None:
        for col, low in lowered.items():
            if exclude_chinese and any(h in low for h in _CHINESE_HINT):
                continue
            if any(k in low for k in keywords):
                return col
        return None

    number = first_match(_NUMBER_KEYWORDS)
    name_en = (
        first_match(_NAME_EN_KEYWORDS, exclude_chinese=True)
        or first_match(_NAME_GENERIC_KEYWORDS, exclude_chinese=True)
    )
    address = tuple(
        col for col, low in lowered.items() if any(k in low for k in _ADDRESS_KEYWORDS)
    )
    return HKColumns(number=number, name_en=name_en, address=address)


def load_dataset(path: Path, columns_override: HKColumns | None = None) -> tuple[pd.DataFrame, HKColumns]:
    """Load the HK dataset (CSV or XLSX; a single file or a folder of files).

    Returns the DataFrame and the detected/overridden column mapping.
    """
    log = get_logger()
    frames: list[pd.DataFrame] = []
    files = _dataset_files(path)
    if not files:
        raise FileNotFoundError(f"No CSV/XLSX dataset files found at: {path}")

    for f in files:
        log.info("Loading HK dataset file: %s", f.name)
        if f.suffix.lower() in (".xlsx", ".xls"):
            frames.append(pd.read_excel(f, dtype=str))
        else:
            frames.append(pd.read_csv(f, dtype=str, encoding="utf-8-sig", low_memory=False))
    df = pd.concat(frames, ignore_index=True).fillna("")

    cols = columns_override or detect_columns(list(df.columns))
    if not cols.is_usable():
        raise ValueError(
            "Could not detect a company-name column. Columns present: "
            f"{list(df.columns)}. Set an override in config.py."
        )
    log.info(
        "Detected columns -> number=%r name=%r address=%r",
        cols.number,
        cols.name_en,
        cols.address,
    )
    return df, cols


def _dataset_files(path: Path) -> list[Path]:
    """Return the list of dataset files for a file or directory path."""
    if path.is_dir():
        return sorted(
            p for p in path.iterdir()
            if p.suffix.lower() in (".csv", ".xlsx", ".xls")
        )
    return [path] if path.exists() else []


class HKRegistryIndex:
    """In-memory index over the HK dataset for fast exact + blocked-fuzzy match."""

    def __init__(self, df: pd.DataFrame, cols: HKColumns) -> None:
        self._cols = cols
        self._log = get_logger()
        # Exact index: normalised English name -> row dict.
        self._exact: dict[str, dict[str, str]] = {}
        # Blocking index: first normalised token -> list of (norm_name, row dict).
        self._blocks: dict[str, list[tuple[str, dict[str, str]]]] = {}

        name_col = cols.name_en
        for row in df.to_dict("records"):
            raw_name = str(row.get(name_col, "")).strip()
            if not raw_name:
                continue
            norm = normalize_name(raw_name)
            if not norm:
                continue
            self._exact.setdefault(norm, row)
            first = norm.split(" ", 1)[0]
            self._blocks.setdefault(first, []).append((norm, row))
        self._log.info("Indexed %d HK companies", len(self._exact))

    def lookup(
        self, query: str, *, min_confidence: float, strong_confidence: float
    ) -> tuple[dict[str, str] | None, MatchResult]:
        """Return (row, match) for the best candidate matching ``query``."""
        norm = normalize_name(query)
        # 1) Exact normalised hit.
        if norm in self._exact:
            row = self._exact[norm]
            name = str(row.get(self._cols.name_en, ""))
            return row, MatchResult(name, 1.0, "exact", 0)

        # 2) Blocked fuzzy: only compare within the same first-token block.
        first = norm.split(" ", 1)[0] if norm else ""
        block = self._blocks.get(first, [])
        if not block:
            return None, MatchResult("", 0.0, "not_found", -1)

        candidate_names = [n for n, _ in block]
        match = choose_best_match(
            query,
            candidate_names,
            min_confidence=min_confidence,
            strong_confidence=strong_confidence,
        )
        if match.index < 0:
            return None, MatchResult("", 0.0, "not_found", -1)
        _, row = block[match.index]
        display = str(row.get(self._cols.name_en, ""))
        return row, MatchResult(display, match.confidence, match.status, match.index)

    def row_to_record(self, row: dict[str, str]) -> CompanyRecord:
        """Map a dataset row into a :class:`CompanyRecord`."""
        number = str(row.get(self._cols.number, "")).strip() if self._cols.number else ""
        address = ", ".join(
            str(row.get(c, "")).strip() for c in self._cols.address if str(row.get(c, "")).strip()
        )
        return CompanyRecord(
            company_name=str(row.get(self._cols.name_en, "")).strip(),
            company_number=number,
            company_status="Live",  # dataset lists only live local companies
            registered_address=address,
            remarks="from data.gov.hk live-companies dataset (no directors/incorporation date)",
            source_url=DATASET_URL,
        )
