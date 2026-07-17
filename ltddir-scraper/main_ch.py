"""Entry point: look up companies via the official Companies House API.

This is the reliable alternative to scraping ltddir.com (which is Cloudflare
protected). It reads the same ``input/companies.xlsx`` and writes the same
``output/result.xlsx`` schema, with the same resumable progress and matching.

Setup:
    1. Get a free API key: https://developer.company-information.service.gov.uk/
    2. export CH_API_KEY=your_key        (Windows PowerShell: $env:CH_API_KEY="your_key")

Usage:
    python main_ch.py                    # process all companies
    python main_ch.py --limit 5          # smoke test
    python main_ch.py --fresh            # ignore prior progress
    python main_ch.py --input x.xlsx --output y.xlsx
"""

from __future__ import annotations

import argparse
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import config
from scraper.companies_house import (
    CompaniesHouseClient,
    CompaniesHouseError,
    company_web_url,
    profile_to_record,
)
from scraper.exporter import ProgressStore, read_input_companies, write_excel
from scraper.parser import CompanyRecord
from scraper.utils import choose_best_match, get_logger, setup_logging

CH_OUTPUT, CH_PROGRESS = config.tool_paths("uk")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Companies House company lookup")
    p.add_argument("--input", type=Path, default=config.INPUT_FILE, help="input .xlsx")
    p.add_argument("--output", type=Path, default=CH_OUTPUT, help="output .xlsx")
    p.add_argument("--limit", type=int, default=0, help="process at most N companies")
    p.add_argument("--fresh", action="store_true", help="ignore prior progress")
    p.add_argument("--verbose", action="store_true", help="debug logging")
    return p.parse_args()


def lookup_one(client: CompaniesHouseClient, input_name: str) -> dict[str, str]:
    """Search, match, fetch, and map one company into an output row."""
    log = get_logger()
    start = time.monotonic()
    items = client.search_companies(input_name)
    titles = [str(i.get("title", "")) for i in items]

    match = choose_best_match(
        input_name,
        titles,
        min_confidence=config.SETTINGS.min_confidence,
        strong_confidence=config.SETTINGS.strong_confidence,
    )

    record = CompanyRecord()
    if match.index >= 0 and match.status != "not_found":
        number = str(items[match.index].get("company_number", ""))
        profile = client.get_profile(number)
        if profile:
            officers = client.get_officers(number)
            record = profile_to_record(
                profile, officers, source_url=company_web_url(number)
            )
            if match.status == "low_confidence":
                record.remarks = "low-confidence match; verify manually"
        else:
            match = match.__class__(match.matched_name, match.confidence, "not_found", -1)

    duration = time.monotonic() - start
    log.info(
        "%s -> status=%s conf=%.3f number=%s (%.2fs)",
        input_name,
        match.status,
        match.confidence,
        record.company_number or "-",
        duration,
    )
    return {
        "Input Company Name": input_name,
        "Matched Company Name": match.matched_name,
        "Match Status": match.status,
        "Confidence Score": f"{match.confidence:.4f}",
        "Company Number": record.company_number,
        "Company Type": record.company_type,
        "Company Status": record.company_status,
        "Incorporation Date": record.incorporation_date,
        "Registered Address": record.registered_address,
        "Directors": record.directors,
        "Company Secretary": record.company_secretary,
        "Business Nature": record.business_nature,
        "Previous Names": record.previous_names,
        "Remarks": record.remarks,
        "Source URL": record.source_url,
        "Crawl Timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    """Run the Companies House lookup over the input list. Resumable."""
    args = parse_args()
    log = setup_logging(config.LOG_FILE, verbose=args.verbose)

    if not args.input.exists():
        log.error("Input file not found: %s", args.input)
        return 2

    try:
        client = CompaniesHouseClient(os.environ.get("CH_API_KEY", ""))
    except CompaniesHouseError as exc:
        log.error("%s", exc)
        return 2

    companies = read_input_companies(args.input)
    if args.limit > 0:
        companies = companies[: args.limit]

    progress = ProgressStore(CH_PROGRESS)
    if args.fresh and CH_PROGRESS.exists():
        CH_PROGRESS.unlink()

    done = progress.completed_names()
    todo = [c for c in companies if c not in done]
    log.info("%d companies (%d done, %d to process)", len(companies), len(done), len(todo))

    for i, name in enumerate(todo, 1):
        log.info("[%d/%d] %s", i, len(todo), name)
        try:
            row = lookup_one(client, name)
        except CompaniesHouseError as exc:
            log.error("FAILURE: %s -> %s", name, exc)
            row = _error_row(name, str(exc))
        except Exception as exc:  # noqa: BLE001 - never abort the whole run
            log.exception("UNEXPECTED: %s", name)
            row = _error_row(name, f"unexpected: {exc}")
        progress.append(row)
        time.sleep(0.4)  # gentle pacing (limit is 600 req / 5 min)

    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    write_excel(ordered, args.output)
    log.info("Done: %d/%d companies in output", len(ordered), len(companies))
    return 0


def _error_row(name: str, remark: str) -> dict[str, str]:
    """Build a not-found row carrying an error remark."""
    from scraper.exporter import COLUMNS

    row = {c: "" for c in COLUMNS}
    row.update(
        {
            "Input Company Name": name,
            "Match Status": "not_found",
            "Confidence Score": "0.0000",
            "Remarks": remark,
            "Crawl Timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    return row


if __name__ == "__main__":
    raise SystemExit(main())
