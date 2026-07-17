"""Persistence: resumable progress log and final Excel export.

Progress is appended to a JSONL file after every company so an interrupted run
resumes without reprocessing completed rows. The final ``result.xlsx`` is
rebuilt from that log, guaranteeing output and progress never diverge.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from .utils import get_logger

# Output column order (matches the task specification exactly).
COLUMNS: list[str] = [
    "Input Company Name",
    "Matched Company Name",
    "Match Status",
    "Confidence Score",
    "Company Number",
    "Company Type",
    "Company Status",
    "Incorporation Date",
    "Registered Address",
    "Directors",
    "Company Secretary",
    "Business Nature",
    "Previous Names",
    "Remarks",
    "Source URL",
    "Crawl Timestamp",
]


class ProgressStore:
    """Append-only JSONL store of completed rows, keyed by input company name."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._log = get_logger()

    def completed_names(self) -> set[str]:
        """Return the set of input names already processed."""
        done: set[str] = set()
        if not self._path.exists():
            return done
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                name = row.get("Input Company Name")
                if name:
                    done.add(name)
        return done

    def append(self, row: dict[str, Any]) -> None:
        """Append one completed row to the progress log and flush to disk."""
        with self._path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            fh.flush()

    def load_rows(self) -> list[dict[str, Any]]:
        """Load all recorded rows in insertion order."""
        rows: list[dict[str, Any]] = []
        if not self._path.exists():
            return rows
        with self._path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return rows


def read_input_companies(path: Path) -> list[str]:
    """Read company names from the first sheet of an Excel file.

    Accepts a column literally named "Company Name" (any case) or, failing
    that, the first column. Blank cells are dropped.
    """
    df = pd.read_excel(path, dtype=str)
    if df.empty:
        return []
    col = None
    for c in df.columns:
        if str(c).strip().lower() == "company name":
            col = c
            break
    if col is None:
        col = df.columns[0]
    names = [str(v).strip() for v in df[col].tolist() if str(v).strip() and str(v) != "nan"]
    return names


def write_excel(rows: list[dict[str, Any]], out_path: Path) -> None:
    """Write ``rows`` to ``out_path`` as an .xlsx with the canonical columns."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(rows, columns=COLUMNS) if rows else pd.DataFrame(columns=COLUMNS)
    df.to_excel(out_path, index=False, engine="openpyxl")
    get_logger().info("Wrote %d rows to %s", len(df), out_path)
