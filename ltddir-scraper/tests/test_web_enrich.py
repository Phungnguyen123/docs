"""Offline unit tests for OSINT signal extraction + batch analysis (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.web_enrich import (
    annotate_batch_signals,
    classify,
    company_core,
    extract_signals,
    looks_random_name,
    registrable_domain,
)


def test_registrable_domain_strips_www() -> None:
    assert registrable_domain("https://www.helena.com/about") == "helena.com"


def test_company_core_drops_generic_tokens() -> None:
    assert company_core("VRAXIONYX GROUP LIMITED") == "vraxionyxgroup"
    assert company_core("HELENA LIMITED") == "helena"


def test_classify_categories() -> None:
    assert classify("https://www.linkedin.com/company/x") == "social"
    assert classify("https://www.reddit.com/r/scams/comments/x") == "community"
    assert classify("https://www.scamadviser.com/check-website/x.com") == "scam"
    assert classify("https://opencorporates.com/companies/hk/1") == "directory"
    assert classify("https://some-shop.store/product") == "website"
    assert classify("https://bikeforum.net/thread") == "community"


def test_looks_random_name() -> None:
    assert looks_random_name("VRAXIONYX LIMITED") is True
    assert looks_random_name("QYLARIS LIMITED") is True
    assert looks_random_name("PURE HORIZON LIMITED") is False


def test_extract_signals_keeps_mismatched_website_and_flags_it() -> None:
    # The real case: HELENA LIMITED -> sainthelenabank.com is surfaced AND flagged.
    results = [
        {"link": "https://www.sainthelenabank.com/about-us/", "title": "Bank", "snippet": ""},
    ]
    sig = extract_signals(results, "HELENA LIMITED")
    assert sig.website == "https://www.sainthelenabank.com/about-us/"
    assert sig.website_matches_name is False
    assert "website domain does not match company name" in sig.risk_cell()


def test_extract_signals_no_website_flag() -> None:
    results = [
        {"link": "https://www.linkedin.com/company/x", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "X LIMITED")
    assert sig.website == ""
    assert "no website found in search" in sig.risk_cell()
    assert "linkedin.com/company/x" in sig.socials_cell()


def test_extract_signals_collects_community_and_scam() -> None:
    results = [
        {"link": "https://vraxionyx.com", "title": "Shop now", "snippet": "buy now sale outlet"},
        {"link": "https://www.reddit.com/r/scams/comments/abc", "title": "Is Vraxionyx a scam?", "snippet": "fraud"},
        {"link": "https://www.scamadviser.com/check-website/vraxionyx.com", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "VRAXIONYX LIMITED")
    assert "reddit.com" in sig.community_cell()
    assert sig.scam_cell() != ""
    risks = sig.risk_cell()
    assert "shopping / e-commerce keywords in results" in risks
    assert "scam / blacklist / complaint mention" in risks


def test_extract_signals_multiple_domains_flag() -> None:
    results = [
        {"link": "https://storeone.shop", "title": "", "snippet": ""},
        {"link": "https://storetwo.store", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "APEX MONTARO LIMITED")
    assert "multiple distinct domains (2)" in sig.risk_cell()
    assert "storetwo.store" in sig.other_domains_cell()


def test_annotate_batch_shared_address_and_bulk() -> None:
    rows = [
        {"Input Company Name": "PURE HORIZON LIMITED", "Registered Address": "FLAT A, 1 ROAD, HK", "Incorporation Date": "2025-06-25", "Risk Signals": ""},
        {"Input Company Name": "VRAXIONYX LIMITED", "Registered Address": "flat a, 1 road, hk", "Incorporation Date": "2025-06-25", "Risk Signals": ""},
        {"Input Company Name": "QYLARIS LIMITED", "Registered Address": "FLAT A, 1 ROAD, HK", "Incorporation Date": "2025-06-25", "Risk Signals": ""},
    ]
    annotate_batch_signals(rows, min_shared=2, min_bulk=3)
    for r in rows:
        assert "shared registered address (3 companies)" in r["Risk Signals"]
        assert "bulk incorporation date (3 on 2025-06-25)" in r["Risk Signals"]
    # VRAXIONYX + QYLARIS are random-looking; PURE HORIZON is not.
    assert "random-looking name" in rows[1]["Risk Signals"]
    assert "random-looking name" not in rows[0]["Risk Signals"]


def test_annotate_batch_preserves_existing_signals() -> None:
    rows = [
        {"Input Company Name": "A LTD", "Registered Address": "X", "Incorporation Date": "d", "Risk Signals": "website domain does not match company name"},
    ]
    annotate_batch_signals(rows)
    assert rows[0]["Risk Signals"].startswith("website domain does not match company name")
