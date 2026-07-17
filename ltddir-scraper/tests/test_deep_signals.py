"""Offline unit tests for domain-age (RDAP) and shop-scan heuristics."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.domain_age import (
    age_days,
    parse_registration_date,
    registrable_from_host,
    young_domain_flag,
)
from scraper.shop_scan import score_html


def test_registrable_from_host() -> None:
    assert registrable_from_host("www.acme.com") == "acme.com"
    assert registrable_from_host("shop.acme.co.uk") == "acme.co.uk"
    assert registrable_from_host("a.b.acme.com.hk") == "acme.com.hk"
    assert registrable_from_host("acme.com") == "acme.com"


def test_parse_registration_date() -> None:
    rdap = {"events": [
        {"eventAction": "last changed", "eventDate": "2026-01-01T00:00:00Z"},
        {"eventAction": "registration", "eventDate": "2026-05-01T12:00:00Z"},
    ]}
    assert parse_registration_date(rdap) == "2026-05-01"
    assert parse_registration_date({"events": []}) == ""


def test_age_days() -> None:
    assert age_days("2026-01-01", today=date(2026, 4, 1)) == 90
    assert age_days("not-a-date", today=date(2026, 4, 1)) is None


def test_young_domain_flag() -> None:
    flag = young_domain_flag("2026-05-01", today=date(2026, 6, 1), young_days=180)
    assert flag is not None
    label, evidence = flag
    assert "newly registered domain" in label
    assert "2026-05-01" in evidence
    # Old domain -> no flag.
    assert young_domain_flag("2001-01-01", today=date(2026, 6, 1)) is None
    assert young_domain_flag("", today=date(2026, 6, 1)) is None


def test_score_html_flags_scam_shop() -> None:
    html = """
    <html><body>
      <h1>MEGA CLEARANCE up to 90% off - limited time, hurry!</h1>
      <button>Add to cart</button><button>Buy now</button>
      <a>Checkout</a> sale sale sale
    </body></html>
    """
    scan = score_html(html, "https://cheap.shop")
    assert scan.fetched
    assert scan.score >= 3
    joined = scan.summary()
    assert "urgency" in joined or "discount" in joined
    assert "no contact details found" in joined or "missing trust" in joined


def test_score_html_legit_shop_low_score() -> None:
    html = """
    <html><body>
      <h1>ACME Ltd</h1>
      <p>Company number 12345678. VAT GB123. Registered in Hong Kong.</p>
      <a href="/contact">Contact us</a> <a href="/returns">Returns</a>
      <a href="/privacy">Privacy</a> email: hello@acme.com tel: +852 1234
      <p>Quality products and careful service.</p>
    </body></html>
    """
    scan = score_html(html, "https://acme.com")
    assert scan.score <= 1
