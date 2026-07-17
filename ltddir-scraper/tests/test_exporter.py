"""Offline unit tests for progress store and Excel I/O."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.exporter import (
    COLUMNS,
    ProgressStore,
    read_input_companies,
    write_excel,
)


def _row(name: str) -> dict[str, str]:
    return {c: "" for c in COLUMNS} | {"Input Company Name": name}


def test_progress_roundtrip_and_resume(tmp_path: Path) -> None:
    store = ProgressStore(tmp_path / "p.jsonl")
    assert store.completed_names() == set()

    store.append(_row("HELENA LIMITED"))
    store.append(_row("FITAZZY LIMITED"))

    reopened = ProgressStore(tmp_path / "p.jsonl")
    assert reopened.completed_names() == {"HELENA LIMITED", "FITAZZY LIMITED"}
    assert len(reopened.load_rows()) == 2


def test_write_excel_has_canonical_columns(tmp_path: Path) -> None:
    out = tmp_path / "result.xlsx"
    write_excel([_row("HELENA LIMITED")], out)
    df = pd.read_excel(out, dtype=str)
    assert list(df.columns) == COLUMNS
    assert df.iloc[0]["Input Company Name"] == "HELENA LIMITED"


def test_write_excel_empty_still_writes_header(tmp_path: Path) -> None:
    out = tmp_path / "empty.xlsx"
    write_excel([], out)
    df = pd.read_excel(out, dtype=str)
    assert list(df.columns) == COLUMNS
    assert len(df) == 0


def test_read_input_companies_named_column(tmp_path: Path) -> None:
    src = tmp_path / "in.xlsx"
    pd.DataFrame({"Company Name": ["A LTD", "B LTD", ""]}).to_excel(src, index=False)
    assert read_input_companies(src) == ["A LTD", "B LTD"]


def test_read_input_companies_first_column_fallback(tmp_path: Path) -> None:
    src = tmp_path / "in.xlsx"
    pd.DataFrame({"whatever": ["X LTD", "Y LTD"]}).to_excel(src, index=False)
    assert read_input_companies(src) == ["X LTD", "Y LTD"]
