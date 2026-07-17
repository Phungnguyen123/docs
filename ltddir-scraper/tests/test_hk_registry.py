"""Offline unit tests for the Hong Kong data.gov.hk matcher."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.hk_registry import HKRegistryIndex, detect_columns, load_dataset


def test_detect_columns_typical_headers() -> None:
    cols = detect_columns(["CR No.", "Company Name (English)", "Company Name (Chinese)", "Registered Office Address"])
    assert cols.number == "CR No."
    assert cols.name_en == "Company Name (English)"
    assert cols.address == ("Registered Office Address",)
    assert cols.is_usable()


def test_detect_columns_brn_variant() -> None:
    cols = detect_columns(["BRN", "English Name", "Address Line 1", "Address Line 2"])
    assert cols.number == "BRN"
    assert cols.name_en == "English Name"
    assert set(cols.address) == {"Address Line 1", "Address Line 2"}


def test_detect_columns_excludes_chinese_name() -> None:
    cols = detect_columns(["Company Name (Chinese)", "Company Name (English)"])
    assert cols.name_en == "Company Name (English)"


def _make_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "CR No.": ["C0001", "C0002", "C0003"],
            "Company Name (English)": [
                "GOLDEN DRAGON LIMITED",
                "GOLDEN DRAGON HOLDINGS LIMITED",
                "JADE PHOENIX LIMITED",
            ],
            "Registered Office Address": [
                "1 Queen's Road, Central, HK",
                "88 Nathan Road, Kowloon, HK",
                "5 Des Voeux Road, HK",
            ],
        }
    )


def test_index_exact_match() -> None:
    df = _make_df()
    cols = detect_columns(list(df.columns))
    idx = HKRegistryIndex(df, cols)
    row, match = idx.lookup("golden dragon ltd.", min_confidence=0.6, strong_confidence=0.85)
    # "ltd" vs "limited" is not exact, but fuzzy within the same block picks it.
    assert row is not None
    assert match.matched_name == "GOLDEN DRAGON LIMITED"


def test_index_exact_identical() -> None:
    df = _make_df()
    cols = detect_columns(list(df.columns))
    idx = HKRegistryIndex(df, cols)
    row, match = idx.lookup("JADE PHOENIX LIMITED", min_confidence=0.6, strong_confidence=0.85)
    assert match.status == "exact"
    assert idx.row_to_record(row).company_number == "C0003"


def test_index_not_found() -> None:
    df = _make_df()
    cols = detect_columns(list(df.columns))
    idx = HKRegistryIndex(df, cols)
    row, match = idx.lookup("NONEXISTENT COMPANY XYZ", min_confidence=0.6, strong_confidence=0.85)
    assert row is None
    assert match.status == "not_found"


def test_row_to_record_fields() -> None:
    df = _make_df()
    cols = detect_columns(list(df.columns))
    idx = HKRegistryIndex(df, cols)
    rec = idx.row_to_record(df.to_dict("records")[0])
    assert rec.company_number == "C0001"
    assert rec.company_status == "Live"
    assert "Queen's Road" in rec.registered_address
    assert rec.source_url.startswith("https://data.gov.hk")


def test_load_dataset_from_csv(tmp_path: Path) -> None:
    df = _make_df()
    csv = tmp_path / "ro.csv"
    df.to_csv(csv, index=False)
    loaded, cols = load_dataset(csv)
    assert len(loaded) == 3
    assert cols.name_en == "Company Name (English)"
