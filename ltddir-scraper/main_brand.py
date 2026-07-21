"""Entry point: scan for websites impersonating a protected brand group.

Finds typosquats, clone sites, and impersonation pages (like the recovery-scam
``globalchaincp.com`` that reused BBCIncorp's address) by pivoting on a watchlist
of protected assets.

Setup:
    1. Copy .env.example -> .env and fill keys (GOOGLE_API_KEY + GOOGLE_CSE_ID
       recommended; SERPAPI_KEY optional; URLSCAN_API_KEY optional). Keys are
       loaded from .env so they never touch your shell history.
    2. Edit input/watchlist.json (brands, official domains, addresses, entities).

Usage:
    python main_brand.py                       # crt.sh + urlscan + web search
    python main_brand.py --no-search           # keyless only (crt.sh + urlscan)
    python main_brand.py --watchlist path.json --output out.xlsx
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import config

config.load_dotenv()  # pull keys from .env before anything reads os.environ

from scraper.brand_monitor import BrandMonitor, Watchlist, build_brand_sheet  # noqa: E402
from scraper.domain_age import DomainAgeLookup  # noqa: E402
from scraper.utils import get_logger, setup_logging  # noqa: E402
from scraper.web_enrich import WebEnricher  # noqa: E402

DEFAULT_WATCHLIST = config.BASE_DIR / "input" / "watchlist.json"
DEFAULT_OUTPUT = config.BASE_DIR / "output" / "brand_abuse.xlsx"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    p = argparse.ArgumentParser(description="Brand-abuse / impersonation monitor")
    p.add_argument("--watchlist", type=Path, default=DEFAULT_WATCHLIST, help="watchlist .json")
    p.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="output .xlsx")
    p.add_argument("--no-search", action="store_true", help="keyless only (skip Google/SerpAPI web search)")
    p.add_argument("--no-verify", action="store_true", help="skip fetching pages to confirm the string is really there (faster, noisier)")
    p.add_argument("--max-domains", type=int, default=200, help="cap suspect domains enriched")
    p.add_argument("--verbose", action="store_true", help="debug logging")
    return p.parse_args()


def main() -> int:
    """Run the brand-abuse sweep and write the suspects workbook."""
    args = parse_args()
    log = setup_logging(config.LOG_FILE, verbose=args.verbose)

    if not args.watchlist.exists():
        log.error(
            "Watchlist not found: %s — copy input/watchlist.example.json to it and edit.",
            args.watchlist,
        )
        return 2
    wl = Watchlist.from_dict(json.loads(args.watchlist.read_text(encoding="utf-8")))
    log.info(
        "Watchlist: %d brand(s), %d official domain(s), %d address(es), %d entity(ies)",
        len(wl.brands), len(wl.official_domains), len(wl.addresses), len(wl.entities),
    )

    enricher = None
    if not args.no_search:
        enricher = WebEnricher()
        if enricher.enabled():
            log.info("Web search enabled via %s", enricher.provider())
        else:
            log.warning("No search key found; using keyless sources only (crt.sh + urlscan).")
            enricher = None

    monitor = BrandMonitor(enricher=enricher, age=DomainAgeLookup(), verify=not args.no_verify)
    suspects = monitor.scan(wl, max_domains=args.max_domains)

    df = build_brand_sheet(suspects)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(args.output, index=False, engine="openpyxl")
    log.info("Wrote %d suspect domain(s) to %s", len(df), args.output)
    if len(df):
        top = suspects[0]
        log.info("Top suspect: %s (score %d)", top.domain, top.score())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
