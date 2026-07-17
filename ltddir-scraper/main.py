"""Entry point: read companies.xlsx, scrape each, write result.xlsx.

Resumable and fault-tolerant: progress is saved after every company, already
completed companies are skipped on restart, and a failure in one company never
aborts the run.

Usage:
    python main.py                 # headless, default paths
    python main.py --show          # run with a visible browser
    python main.py --limit 5       # process only the first 5 (smoke test)
    python main.py --input path.xlsx --output out.xlsx
"""

from __future__ import annotations

import argparse
import asyncio
import dataclasses
from pathlib import Path

import config
from scraper.crawler import Crawler
from scraper.exporter import (
    ProgressStore,
    read_input_companies,
    write_excel,
)
from scraper.utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="LTDDir company directory scraper")
    p.add_argument("--input", type=Path, default=config.INPUT_FILE, help="input .xlsx")
    p.add_argument("--output", type=Path, default=config.OUTPUT_FILE, help="output .xlsx")
    p.add_argument("--show", action="store_true", help="run with a visible browser")
    p.add_argument("--limit", type=int, default=0, help="process at most N companies")
    p.add_argument("--fresh", action="store_true", help="ignore prior progress and restart")
    p.add_argument("--verbose", action="store_true", help="debug-level logging")
    return p.parse_args()


async def run(args: argparse.Namespace) -> int:
    """Execute the full scraping run. Returns a process exit code."""
    logger = setup_logging(config.LOG_FILE, verbose=args.verbose)

    settings = dataclasses.replace(config.SETTINGS, headless=not args.show)

    if not args.input.exists():
        logger.error("Input file not found: %s", args.input)
        return 2

    companies = read_input_companies(args.input)
    if not companies:
        logger.error("No company names found in %s", args.input)
        return 2
    if args.limit > 0:
        companies = companies[: args.limit]

    progress = ProgressStore(config.PROGRESS_FILE)
    if args.fresh and config.PROGRESS_FILE.exists():
        config.PROGRESS_FILE.unlink()
        logger.info("Cleared prior progress (--fresh)")

    done = progress.completed_names()
    todo = [c for c in companies if c not in done]
    logger.info(
        "Loaded %d companies (%d already done, %d to process)",
        len(companies),
        len(done),
        len(todo),
    )

    if todo:
        async with Crawler(settings) as crawler:
            for i, name in enumerate(todo, 1):
                logger.info("[%d/%d] %s", i, len(todo), name)
                outcome = await crawler.process_company(name)
                progress.append(outcome.to_row())
                if i < len(todo):
                    await crawler.polite_pause()

    # Rebuild the final workbook from the complete progress log so output order
    # follows the input file and nothing is lost.
    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    write_excel(ordered, args.output)
    logger.info("Run complete: %d/%d companies in output", len(ordered), len(companies))
    return 0


def main() -> None:
    """Synchronous wrapper around the async run."""
    args = parse_args()
    raise SystemExit(asyncio.run(run(args)))


if __name__ == "__main__":
    main()
