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
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import config
from scraper.exporter import COLUMNS, ProgressStore, read_input_companies, write_workbook
from scraper.hk_api import (
    HKApiError,
    HKCrApiClient,
    match_records,
    record_to_company,
)
from scraper.domain_age import DomainAgeLookup, _today_utc, young_domain_flag
from scraper.networks import build_networks_sheet
from scraper.shop_scan import ShopScanner
from scraper.utils import get_logger, setup_logging
from scraper.web_enrich import (
    WebEnricher,
    annotate_batch_signals,
    build_cluster_sheets,
    extract_signals,
    registrable_domain,
)

DEFAULT_DATASET = config.BASE_DIR / "input" / "hk"
HK_OUTPUT, HK_PROGRESS = config.tool_paths("hk")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Hong Kong company lookup (data.gov.hk)")
    p.add_argument("--input", type=Path, default=config.INPUT_FILE, help="input .xlsx of names")
    p.add_argument("--output", type=Path, default=HK_OUTPUT, help="output .xlsx")
    p.add_argument(
        "--dataset",
        type=Path,
        default=None,
        help="use CSV mode: path to a downloaded data.gov.hk file/folder",
    )
    p.add_argument("--probe", type=str, default=None, help="dump raw API JSON for one name and exit")
    p.add_argument("--probe-web", type=str, default=None, help="dump raw web-search results + signals for one name and exit")
    p.add_argument("--enrich-web", action="store_true", help="add web/OSINT signal columns (needs a search API key)")
    p.add_argument("--deep", action="store_true", help="with --enrich-web: run an extra scam/complaint query per company")
    p.add_argument("--whois", action="store_true", help="with --enrich-web: look up domain registration age (RDAP, free)")
    p.add_argument("--scan-shop", action="store_true", help="with --enrich-web: fetch + score the website for scam-shop signals")
    p.add_argument("--limit", type=int, default=0, help="process at most N companies")
    p.add_argument("--fresh", action="store_true", help="ignore prior progress")
    p.add_argument("--show-columns", action="store_true", help="(CSV mode) print detected columns")
    p.add_argument("--verbose", action="store_true", help="debug logging")
    return p.parse_args()


def _to_row(name: str, match, record, signals=None) -> dict[str, str]:  # noqa: ANN001
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
                "Company Name (Chinese)": record.company_name_other,
                "Re-domiciliation Date": record.redomiciliation_date,
            }
        )
    if signals is not None:
        row["Website"] = signals.website
        row["Website Matches Name"] = signals.match_label()
        row["Domain Registered"] = signals.domain_registered
        row["Shop Scam Scan"] = signals.shop_scan
        row["Other Domains"] = signals.other_domains_cell()
        row["Social Media"] = signals.socials_cell()
        row["Marketplace Listings"] = signals.marketplace_cell()
        row["Community Mentions"] = signals.community_cell()
        row["Scam/Blacklist Mentions"] = signals.scam_cell()
        row["Risk Signals"] = signals.risk_cell()
        row["Evidence"] = signals.evidence_cell()
    return row


@dataclass
class _Tools:
    """Optional deep-signal helpers, built once per run."""

    enricher: "WebEnricher | None" = None
    age: "DomainAgeLookup | None" = None
    scanner: "ShopScanner | None" = None


def _make_tools(args: argparse.Namespace, log) -> _Tools:  # noqa: ANN001
    """Build the enrichment helpers requested by the CLI flags."""
    if not args.enrich_web:
        return _Tools()
    enricher = WebEnricher()
    if not enricher.enabled():
        log.warning(
            "--enrich-web set but no search API key found; "
            "set SERPAPI_KEY or GOOGLE_API_KEY + GOOGLE_CSE_ID. Skipping enrichment."
        )
        return _Tools()
    log.info("Web enrichment enabled via %s", enricher.provider())
    return _Tools(
        enricher=enricher,
        age=DomainAgeLookup() if args.whois else None,
        scanner=ShopScanner() if args.scan_shop else None,
    )


def _enrich(tools: _Tools, args, name: str, match, region_hint: str):  # noqa: ANN001
    """Return enriched WebSignals for a matched company, or None."""
    if tools.enricher is None or match.status == "not_found":
        return None
    signals = tools.enricher.gather(match.matched_name or name, region_hint=region_hint, deep=args.deep)
    if signals.website:
        if tools.age is not None:
            iso = tools.age.registration_date(registrable_domain(signals.website))
            signals.domain_registered = iso
            flag = young_domain_flag(iso, today=_today_utc())
            if flag:
                signals.add_flag(*flag)
        if tools.scanner is not None:
            scan = tools.scanner.scan(signals.website)
            signals.shop_scan = scan.summary()
            if scan.fetched and scan.score >= 3:
                signals.add_flag(f"scam-shop score {scan.score}/6", signals.website)
    time.sleep(0.3)  # pace the search API too
    return signals


def run_api_mode(args: argparse.Namespace) -> int:
    """Look up each company via the live CR API. Resumable."""
    log = get_logger()
    client = HKCrApiClient()
    tools = _make_tools(args, log)

    companies = read_input_companies(args.input)
    if args.limit > 0:
        companies = companies[: args.limit]

    progress = ProgressStore(HK_PROGRESS)
    if args.fresh and HK_PROGRESS.exists():
        HK_PROGRESS.unlink()

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
        presence = _enrich(tools, args, name, match, region_hint="Hong Kong")
        log.info("[%d/%d] %s -> %s (%.3f)", i, len(todo), name, match.status, match.confidence)
        progress.append(_to_row(name, match, record, presence))
        time.sleep(0.5)  # polite pacing

    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    annotate_batch_signals(ordered)
    sheets = build_cluster_sheets(ordered)
    net = build_networks_sheet(ordered)
    if net is not None:
        sheets["Suspected Networks"] = net
    write_workbook(ordered, args.output, sheets)
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
    tools = _make_tools(args, log)
    companies = read_input_companies(args.input)
    if args.limit > 0:
        companies = companies[: args.limit]

    progress = ProgressStore(HK_PROGRESS)
    if args.fresh and HK_PROGRESS.exists():
        HK_PROGRESS.unlink()

    done = progress.completed_names()
    todo = [c for c in companies if c not in done]
    log.info("%d companies (%d done, %d to process)", len(companies), len(done), len(todo))

    s = config.SETTINGS
    for i, name in enumerate(todo, 1):
        row_data, match = index.lookup(
            name, min_confidence=s.min_confidence, strong_confidence=s.strong_confidence
        )
        record = index.row_to_record(row_data) if row_data else None
        presence = _enrich(tools, args, name, match, region_hint="Hong Kong")
        log.info("[%d/%d] %s -> %s (%.3f)", i, len(todo), name, match.status, match.confidence)
        progress.append(_to_row(name, match, record, presence))

    rows_by_name = {r["Input Company Name"]: r for r in progress.load_rows()}
    ordered = [rows_by_name[c] for c in companies if c in rows_by_name]
    annotate_batch_signals(ordered)
    sheets = build_cluster_sheets(ordered)
    net = build_networks_sheet(ordered)
    if net is not None:
        sheets["Suspected Networks"] = net
    write_workbook(ordered, args.output, sheets)
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

    if args.probe_web is not None:
        enricher = WebEnricher()
        if not enricher.enabled():
            print(
                "No search API key found. Set SERPAPI_KEY, or "
                "GOOGLE_API_KEY + GOOGLE_CSE_ID."
            )
            return 2
        print(f"Provider: {enricher.provider()}")
        results = enricher.raw_results(f'"{args.probe_web}" Hong Kong')
        print(json.dumps(results, indent=2, ensure_ascii=False)[:6000])
        sig = extract_signals(results, args.probe_web)
        print("\nExtracted signals:")
        print("  website:            ", sig.website or "(none)")
        print("  matches name:       ", sig.match_label() or "(n/a)")
        print("  other domains:      ", sig.other_domains_cell() or "(none)")
        print("  social media:       ", sig.socials_cell() or "(none)")
        print("  community mentions: ", sig.community_cell() or "(none)")
        print("  scam/blacklist:     ", sig.scam_cell() or "(none)")
        print("  RISK SIGNALS:       ", sig.risk_cell() or "(none)")
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
