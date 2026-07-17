"""Offline unit tests for suspected-network link analysis."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.networks import build_link_keys, build_networks


def _row(name, addr="", date="", website="", other="", community="", scam="", risk=""):  # noqa: ANN001
    return {
        "Input Company Name": name,
        "Registered Address": addr,
        "Incorporation Date": date,
        "Website": website,
        "Other Domains": other,
        "Community Mentions": community,
        "Scam/Blacklist Mentions": scam,
        "Risk Signals": risk,
    }


def test_link_by_shared_address() -> None:
    rows = [
        _row("A LTD", addr="UNIT 5, 12 TOWER, HK"),
        _row("B LTD", addr="unit 5, 12 tower, hk"),
        _row("C LTD", addr="99 OTHER RD"),
    ]
    nets = build_networks(rows)
    assert len(nets) == 1
    assert set(nets[0].members) == {"A LTD", "B LTD"}
    assert any("shared address" in r for r in nets[0].reasons)


def test_link_transitively_via_domain_then_address() -> None:
    # A-B share a domain; B-C share an address -> all three are one network.
    rows = [
        _row("A LTD", website="https://ring.shop"),
        _row("B LTD", website="https://ring.shop", addr="1 HILL RD"),
        _row("C LTD", addr="1 hill rd"),
    ]
    nets = build_networks(rows)
    assert len(nets) == 1
    assert set(nets[0].members) == {"A LTD", "B LTD", "C LTD"}


def test_link_by_shared_scam_url() -> None:
    rows = [
        _row("A LTD", scam="https://scamadviser.com/check/ring.shop"),
        _row("B LTD", scam="https://scamadviser.com/check/ring.shop"),
    ]
    nets = build_networks(rows)
    assert len(nets) == 1
    assert any("co-mentioned link" in r for r in nets[0].reasons)


def test_bulk_date_links_only_when_many() -> None:
    # Two companies sharing a date do NOT link (below bulk threshold 3)...
    rows2 = [_row("A LTD", date="2026-04-09"), _row("B LTD", date="2026-04-09")]
    assert build_networks(rows2, bulk_date_min=3) == []
    # ...but three do.
    rows3 = rows2 + [_row("C LTD", date="2026-04-09")]
    nets = build_networks(rows3, bulk_date_min=3)
    assert len(nets) == 1
    assert set(nets[0].members) == {"A LTD", "B LTD", "C LTD"}


def test_risk_flag_count_aggregated() -> None:
    rows = [
        _row("A LTD", addr="X RD", risk="flag one; flag two"),
        _row("B LTD", addr="x rd", risk="flag three"),
    ]
    nets = build_networks(rows)
    assert nets[0].risk_flag_count == 3


def test_unrelated_companies_form_no_network() -> None:
    rows = [_row("A LTD", addr="1 RD"), _row("B LTD", addr="2 RD")]
    assert build_networks(rows) == []


def test_build_link_keys_requires_two() -> None:
    rows = [_row("A LTD", addr="only one")]
    assert build_link_keys(rows) == {}
