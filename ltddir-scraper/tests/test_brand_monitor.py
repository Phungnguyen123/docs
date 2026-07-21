"""Offline unit tests for the brand-abuse monitor (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.brand_monitor import (
    BrandMonitor,
    Suspect,
    Watchlist,
    build_brand_sheet,
    extract_crtsh_domains,
    extract_urlscan,
    is_official,
)


def test_is_official_allowlist() -> None:
    off = ["bbcincorp.com", "bbcincorp.sg"]
    assert is_official("https://www.bbcincorp.com/services", off)
    assert is_official("blog.bbcincorp.sg", off)
    assert not is_official("https://bbcincorp-hk.com", off)
    assert not is_official("globalchaincp.com", off)


def test_extract_crtsh_domains() -> None:
    records = [
        {"name_value": "bbcincorp-hk.com\n*.bbcincorp-hk.com"},
        {"common_name": "bbcincorp.co"},
        {"name_value": "not a domain"},
    ]
    doms = extract_crtsh_domains(records)
    assert "bbcincorp-hk.com" in doms
    assert "bbcincorp.co" in doms
    assert "not a domain" not in doms


def test_extract_urlscan() -> None:
    data = {"results": [
        {"page": {"domain": "fakebbc.com", "url": "https://fakebbc.com/x"}},
        {"page": {"domain": ""}},
    ]}
    pairs = extract_urlscan(data)
    assert ("fakebbc.com", "https://fakebbc.com/x") in pairs
    assert len(pairs) == 1


def test_suspect_score_and_row() -> None:
    s = Suspect(domain="globalchaincp.com")
    s.add("crt.sh", "TLS cert contains brand 'bbcincorp'", "https://crt.sh/?q=%25bbcincorp%25")
    s.add("search", "web page reuses protected ADDRESS", "https://globalchaincp.com/")
    s.registered = "2100-01-01"  # future -> not "young"; keeps test deterministic
    # 2 sources + address bonus (2) = 4
    assert s.score() == 4
    row = s.to_row()
    assert row["Suspect Domain"] == "globalchaincp.com"
    assert "ADDRESS" in row["Why Flagged"]
    assert "https://globalchaincp.com/" in row["Evidence"]


def test_build_brand_sheet_empty() -> None:
    df = build_brand_sheet([])
    assert list(df.columns) == ["Suspect Domain", "Risk Score", "Sources", "Domain Registered", "Why Flagged", "Evidence"]
    assert len(df) == 0


class _FakeAge:
    def registration_date(self, domain):  # noqa: ANN001
        return ""


class _FakeEnricher:
    def __init__(self, mapping):
        self._m = mapping

    def enabled(self):
        return True

    def raw_results(self, query):
        for needle, res in self._m.items():
            if needle in query:
                return res
        return []


def test_scan_flags_impersonator_not_official(monkeypatch) -> None:
    wl = Watchlist(
        brands=["bbcincorp"],
        official_domains=["bbcincorp.com"],
        addresses=["Office 3906, The Center, HK"],
        entities=[],
    )
    enricher = _FakeEnricher({
        "Office 3906": [
            {"link": "https://www.globalchaincp.com/"},
            {"link": "https://www.bbcincorp.com/about"},  # official -> must be ignored
        ],
    })
    mon = BrandMonitor(enricher=enricher, age=_FakeAge(), pause_s=0)
    # Stub the keyless network calls.
    monkeypatch.setattr(mon, "_crtsh", lambda term: {"bbcincorp-hk.com", "bbcincorp.com"})
    monkeypatch.setattr(mon, "_urlscan", lambda term: [("fakebbc.net", "https://fakebbc.net/x")])
    suspects = mon.scan(wl)
    domains = {s.domain for s in suspects}
    assert "globalchaincp.com" in domains       # address reuse via search
    assert "bbcincorp-hk.com" in domains         # typosquat via crt.sh
    assert "fakebbc.net" in domains              # via urlscan
    assert "bbcincorp.com" not in domains        # official allow-listed
    # The address-reuse suspect should outrank a single-source typosquat.
    top = suspects[0]
    assert top.domain == "globalchaincp.com"
