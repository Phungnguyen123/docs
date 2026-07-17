"""Entry point: look up Hong Kong companies from the free data.gov.hk source.

data.gov.hk serves the Companies Registry "Registered Office Address of Live
Local Companies" data as a free open **API** (no key). Two modes:

  * API mode (default) — queries data.cr.gov.hk live, per company name.
  * CSV mode (--dataset) — if you have a downloaded CSV/XLSX, match locally.

Usage:
    python main_hk.py --probe "HELENA LIMITED"   # dump raw API JSON (confirm shape)
    python main_hk.py                             # API mode over input/companies.xlsx
    python main_hk.py --limit 5
    python main_hk.py --dataset input/hk/ro.csv   # CSV mode instead of the API
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from scraper.exporter import COLUMNS, ProgressStore, read_input_companies, write_excel
from scraper.hk_api import (
    HKApiError,
    HKCrApiClient,
    match_records,
    record_to_company,
)
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
        default=None,
        help="use CSV mode: path to a downloaded data.gov.hk file/folder",
    )
    p.add_argument("--probe", type=str, default=None, help="dump raw API JSON for one name and exit")
    p.add_argument("--limit", type=int, default=0, help="process at most N companies")
    p.add_argument("--fresh", action="store_true", help="ignore prior progress")
    p.add_argument("--show-columns", action="store_true", help="(CSV mode) print detected columns")
    p.add_argument("--verbose", action="store_true", help="debug logging")
    return p.parse_args()


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


def run_api_mode(args: argparse.Namespace) -> int:
    """Look up each company via the live CR API. Resumable."""
    log = get_logger()
    client = HKCrApiClient()

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
        try:
            records = client.search_companies(name)
            record_dict, match = match_records(
                name, records, min_confidence=s.min_confidence, strong_confidence=s.strong_confidence
            )
            record = record_to_company(record_dict) if record_dict else None
        except HKApiError as exc:
            log.error("FAILURE: %s -> %s", name, exc)
            from scraper.utils import MatchResult

            record, match = None, MatchResult("", 0.0, "not_found", -1)
            row = _to_row(name, match, None)
            row["Remarks"] = f"error: {exc}"
            progress.append(row)
            continue
        log.info("[%d/%d] %s -> %s (%.3f)", i, len(todo), name, match.status, match.confidence)
        progress.append(_to_row(name, match, record))
        time.sleep(0.5)  # polite pacing

    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    write_excel(ordered, args.output)
    log.info("Done: %d/%d companies in output", len(ordered), len(companies))
    return 0


def run_csv_mode(args: argparse.Namespace) -> int:
    """Match names against a downloaded data.gov.hk CSV/XLSX file. Resumable."""
    from scraper.hk_registry import HKRegistryIndex, detect_columns, load_dataset

    log = get_logger()
    dataset = args.dataset if args.dataset is not None else DEFAULT_DATASET

    if args.show_columns:
        import pandas as pd

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
        print("\nColumns:", list(df.columns))
        print(f"Detected -> number={cols.number!r} name={cols.name_en!r} address={cols.address!r}\n")
        return 0

    try:
        df, cols = load_dataset(dataset)
    except (FileNotFoundError, ValueError) as exc:
        log.error("%s", exc)
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


def main() -> int:
    """Dispatch to probe / CSV / API mode."""
    args = parse_args()
    setup_logging(config.LOG_FILE, verbose=args.verbose)

    if args.probe is not None:
        client = HKCrApiClient()
        try:
            data = client.raw_search(args.probe, op="begins_with")
        except HKApiError as exc:
            print(f"API error: {exc}")
            return 2
        print(json.dumps(data, indent=2, ensure_ascii=False)[:6000])
        return 0

    # CSV mode when a dataset path is given or --show-columns is requested.
    if args.dataset is not None or args.show_columns:
        return run_csv_mode(args)

    if not args.input.exists():
        get_logger().error("Input file not found: %s", args.input)
        return 2
    return run_api_mode(args)


if __name__ == "__main__":
    raise SystemExit(main())
