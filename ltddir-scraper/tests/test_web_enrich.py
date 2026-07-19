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


def test_extract_signals_unrelated_noise_is_weak_flag() -> None:
    # HELENA -> a law-firm/news page (not commercial) is weak noise, not a store.
    results = [
        {"link": "https://www.sainthelenabank.com/about-us/", "title": "Bank", "snippet": ""},
    ]
    sig = extract_signals(results, "HELENA LIMITED")
    assert sig.website_matches_name is False
    assert "no name-matching website (top results unrelated)" in sig.risk_cell()
    assert "storefront" not in sig.risk_cell()


def test_extract_signals_storefront_under_unrelated_domain() -> None:
    # The strong red flag: a real storefront running under a different name.
    results = [
        {"link": "https://cheap-outlet-deals.shop/pages/contact", "title": "Buy now", "snippet": "sale outlet"},
    ]
    sig = extract_signals(results, "HELENA LIMITED")
    assert sig.website == "https://cheap-outlet-deals.shop/pages/contact"
    assert "storefront under unrelated domain" in sig.risk_cell()


def test_extract_signals_no_website_flag() -> None:
    results = [
        {"link": "https://www.linkedin.com/company/x", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "X LIMITED")
    assert sig.website == ""
    assert "no company website found in search" in sig.risk_cell()
    assert "linkedin.com/company/x" in sig.socials_cell()


def test_extract_signals_marketplace_search_page_is_noise() -> None:
    # A generic Etsy *market/search* page is noise: not a website, not a lead.
    results = [
        {"link": "https://www.etsy.com/de/market/foo", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "VELOURA LIMITED")
    assert sig.website == ""
    assert sig.marketplace_cell() == ""
    assert "no company website found in search" in sig.risk_cell()


def test_extract_signals_marketplace_seller_page_is_a_lead() -> None:
    # A real Etsy *shop* page is kept as an investigative lead (own column),
    # not the company's website and never WHOIS'd.
    results = [
        {"link": "https://www.etsy.com/shop/VelouraStore", "title": "Veloura shop", "snippet": ""},
    ]
    sig = extract_signals(results, "VELOURA LIMITED")
    assert sig.website == ""  # marketplace is never the "website"
    assert "etsy.com/shop/VelouraStore" in sig.marketplace_cell()
    assert "sells on marketplace (verify seller)" in sig.risk_cell()
    assert "etsy.com/shop/VelouraStore" in sig.evidence_cell()


def test_extract_signals_name_matching_store_is_ok() -> None:
    # A store on the company's own matching domain is fine, not a red flag.
    results = [
        {"link": "https://vraxionyx.com/collections/all", "title": "Shop", "snippet": "buy now"},
        {"link": "https://www.reddit.com/r/scams/comments/abc", "title": "scam?", "snippet": "fraud"},
    ]
    sig = extract_signals(results, "VRAXIONYX LIMITED")
    assert sig.website_matches_name is True
    assert "storefront under unrelated domain" not in sig.risk_cell()
    assert "reddit.com" in sig.community_cell()
    assert "scam / blacklist / complaint mention" in sig.risk_cell()


def test_extract_signals_multiple_storefront_domains_flag() -> None:
    results = [
        {"link": "https://storeone.shop", "title": "", "snippet": ""},
        {"link": "https://storetwo.store", "title": "", "snippet": ""},
    ]
    sig = extract_signals(results, "APEX MONTARO LIMITED")
    assert "multiple storefront domains (2)" in sig.risk_cell()
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


def test_extract_signals_evidence_has_urls() -> None:
    results = [
        {"link": "https://cheap-outlet-deals.shop/p", "title": "Buy now sale", "snippet": "outlet discount"},
        {"link": "https://www.scamadviser.com/check/cheap-outlet-deals.shop", "title": "scam?", "snippet": "fraud"},
    ]
    sig = extract_signals(results, "HELENA LIMITED")
    ev = sig.evidence_cell()
    # Every flag with evidence must carry a verifiable URL.
    assert "https://cheap-outlet-deals.shop/p" in ev  # storefront evidence
    assert "scamadviser.com" in ev
    assert "storefront under unrelated domain:" in ev


def test_annotate_batch_evidence_lists_peers() -> None:
    rows = [
        {"Input Company Name": "AAA LTD", "Registered Address": "1 RD, HK", "Incorporation Date": "2025-01-01", "Risk Signals": "", "Evidence": ""},
        {"Input Company Name": "BBB LTD", "Registered Address": "1 rd, hk", "Incorporation Date": "2025-01-01", "Risk Signals": "", "Evidence": ""},
        {"Input Company Name": "CCC LTD", "Registered Address": "1 RD, HK", "Incorporation Date": "2025-01-01", "Risk Signals": "", "Evidence": ""},
    ]
    annotate_batch_signals(rows, min_shared=2, min_bulk=3)
    # AAA's evidence should name its address peers BBB and CCC.
    assert "BBB LTD" in rows[0]["Evidence"]
    assert "CCC LTD" in rows[0]["Evidence"]
    assert "shared address with:" in rows[0]["Evidence"]
