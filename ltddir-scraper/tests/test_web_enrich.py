"""Offline unit tests for web-enrichment heuristics (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.web_enrich import (
    WebPresence,
    extract_presence,
    pick_social,
    pick_website,
    registrable_domain,
)


def test_registrable_domain_strips_www() -> None:
    assert registrable_domain("https://www.helena.com/about") == "helena.com"
    assert registrable_domain("http://sub.helena.hk") == "sub.helena.hk"


def test_pick_website_prefers_name_matching_domain() -> None:
    results = [
        {"link": "https://www.linkedin.com/company/helena", "title": "", "snippet": ""},
        {"link": "https://directory.example.com/helena", "title": "", "snippet": ""},
        {"link": "https://helenaltd.com", "title": "", "snippet": ""},
    ]
    assert pick_website(results, "HELENA LIMITED") == "https://helenaltd.com"


def test_pick_website_skips_excluded_domains() -> None:
    results = [
        {"link": "https://www.facebook.com/helena", "title": "", "snippet": ""},
        {"link": "https://opencorporates.com/companies/hk/123", "title": "", "snippet": ""},
        {"link": "https://find-and-update.company-information.service.gov.uk/company/1", "title": "", "snippet": ""},
        {"link": "https://acme-supplies.net", "title": "", "snippet": ""},
    ]
    # No name match -> first non-excluded result.
    assert pick_website(results, "HELENA LIMITED") == "https://acme-supplies.net"


def test_pick_website_none_when_all_excluded() -> None:
    results = [
        {"link": "https://www.linkedin.com/company/x", "title": "", "snippet": ""},
        {"link": "https://en.wikipedia.org/wiki/X", "title": "", "snippet": ""},
    ]
    assert pick_website(results, "X LIMITED") == ""


def test_pick_social_finds_linkedin_and_facebook() -> None:
    results = [
        {"link": "https://helena.com", "title": "", "snippet": ""},
        {"link": "https://www.linkedin.com/company/helena-ltd", "title": "", "snippet": ""},
        {"link": "https://www.facebook.com/helenaltd", "title": "", "snippet": ""},
    ]
    linkedin, facebook = pick_social(results)
    assert "linkedin.com/company/helena-ltd" in linkedin
    assert "facebook.com/helenaltd" in facebook


def test_extract_presence_combines() -> None:
    results = [
        {"link": "https://helenaltd.com", "title": "", "snippet": ""},
        {"link": "https://www.linkedin.com/company/helena", "title": "", "snippet": ""},
    ]
    p = extract_presence(results, "HELENA LIMITED")
    assert p.website == "https://helenaltd.com"
    assert "linkedin.com" in p.linkedin
    assert p.facebook == ""
    assert "linkedin.com" in p.social()


def test_web_presence_social_join() -> None:
    p = WebPresence(website="x", linkedin="L", facebook="F")
    assert p.social() == "L | F"
    assert WebPresence().social() == ""
