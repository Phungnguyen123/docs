"""Entry point: look up Hong Kong companies from the free data.gov.hk dataset.

No API key, no cost, no anti-bot. You download one open dataset file once, then
match your input names against it locally.

Setup (one-time):
    1. Open https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr
    2. Download the "Registered Office Address of Live Local Companies"
       resource (CSV or XLSX).
    3. Save it into  input/hk/  (any filename; a folder of files also works).

Usage:
    python main_hk.py --show-columns          # verify auto-detected columns
    python main_hk.py                          # match input/companies.xlsx
    python main_hk.py --dataset input/hk/ro.csv --limit 5
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import config
from scraper.exporter import COLUMNS, ProgressStore, read_input_companies, write_excel
from scraper.hk_registry import HKRegistryIndex, detect_columns, load_dataset
from scraper.utils import get_logger, setup_logging

DEFAULT_DATASET = config.BASE_DIR / "input" / "hk"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Hong Kong company lookup (data.gov.hk)")
    p.add_argument("--input", type=Path, default=config.INPUT_FILE, help="input .xlsx of names")
    p.add_argument("--output", type=Path, default=config.OUTPUT_FILE, help="output .xlsx")
    p.add_argument(
        "--dataset",
        type=Path,
        default=DEFAULT_DATASET,
        help="HK dataset file or folder (CSV/XLSX from data.gov.hk)",
    )
    p.add_argument("--limit", type=int, default=0, help="process at most N companies")
    p.add_argument("--fresh", action="store_true", help="ignore prior progress")
    p.add_argument("--show-columns", action="store_true", help="print detected columns and exit")
    p.add_argument("--verbose", action="store_true", help="debug logging")
    return p.parse_args()


def show_columns(dataset: Path) -> int:
    """Load just the headers, print auto-detected columns, and a sample row."""
    import pandas as pd

    log = get_logger()
    files = sorted(dataset.iterdir()) if dataset.is_dir() else [dataset]
    files = [f for f in files if f.suffix.lower() in (".csv", ".xlsx", ".xls")]
    if not files:
        log.error("No CSV/XLSX files found at %s", dataset)
        return 2
    first = files[0]
    df = (
        pd.read_excel(first, dtype=str, nrows=5)
        if first.suffix.lower() in (".xlsx", ".xls")
        else pd.read_csv(first, dtype=str, nrows=5, encoding="utf-8-sig")
    )
    cols = detect_columns(list(df.columns))
    print("\nAll columns in dataset:")
    for c in df.columns:
        print(f"  - {c!r}")
    print("\nAuto-detected mapping:")
    print(f"  Company Number  -> {cols.number!r}")
    print(f"  Company Name(EN)-> {cols.name_en!r}")
    print(f"  Address column(s)-> {cols.address!r}")
    print("\nFirst sample row:")
    if len(df):
        for k, v in df.iloc[0].items():
            print(f"  {k}: {v}")
    print(
        "\nIf the mapping is wrong, edit detect_columns keywords in "
        "scraper/hk_registry.py or pass an override.\n"
    )
    return 0


def main() -> int:
    """Match input names against the HK dataset and write result.xlsx."""
    args = parse_args()
    log = setup_logging(config.LOG_FILE, verbose=args.verbose)

    if args.show_columns:
        return show_columns(args.dataset)

    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        return 2

    try:
        df, cols = load_dataset(args.dataset)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
        log.error(
            "Download the dataset from "
            "https://data.gov.hk/en-data/dataset/hk-cr-crdata-list-addr into %s",
            args.dataset,
        )
        return 2

    index = HKRegistryIndex(df, cols)
    companies = read_input_companies(args.input)
    if args.limit > 0:
        companies = companies[: args.limit]

    progress = ProgressStore(config.PROGRESS_FILE)
    if args.fresh and config.PROGRESS_FILE.exists():
        config.PROGRESS_FILE.unlink()

    done = progress.completed_names()
    todo = [c for c in companies if c not in done]
    log.info("%d companies (%d done, %d to process)", len(companies), len(done), len(todo))

    s = config.SETTINGS
    for i, name in enumerate(todo, 1):
        row_data, match = index.lookup(
            name, min_confidence=s.min_confidence, strong_confidence=s.strong_confidence
        )
        record = index.row_to_record(row_data) if row_data else None
        log.info("[%d/%d] %s -> %s (%.3f)", i, len(todo), name, match.status, match.confidence)
        progress.append(_to_row(name, match, record))

    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    write_excel(ordered, args.output)
    log.info("Done: %d/%d companies in output", len(ordered), len(companies))
    return 0


def _to_row(name: str, match, record) -> dict[str, str]:  # noqa: ANN001
    """Serialise a lookup outcome into the canonical output row."""
    row = {c: "" for c in COLUMNS}
    row.update(
        {
            "Input Company Name": name,
            "Matched Company Name": match.matched_name,
            "Match Status": match.status,
            "Confidence Score": f"{match.confidence:.4f}",
            "Crawl Timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    if record is not None:
        row.update(
            {
                "Company Number": record.company_number,
                "Company Status": record.company_status,
                "Registered Address": record.registered_address,
                "Remarks": record.remarks,
                "Source URL": record.source_url,
            }
        )
    return row


if __name__ == "__main__":
    raise SystemExit(main())
