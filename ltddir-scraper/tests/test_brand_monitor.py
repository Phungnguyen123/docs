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
    s = Suspect(domain="globalchaincp.com", verified=True)
    s.add("crt.sh", "TLS cert contains brand 'bbcincorp'", "https://crt.sh/?q=%25bbcincorp%25")
    s.add("search", "page reuses ADDRESS (verified on page)", "https://globalchaincp.com/")
    s.registered = "2100-01-01"  # future -> not "young"; keeps test deterministic
    # 2 sources + verified-address bonus (2) = 4
    assert s.score() == 4
    row = s.to_row()
    assert row["Suspect Domain"] == "globalchaincp.com"
    assert "ADDRESS" in row["Why Flagged"]
    assert "https://globalchaincp.com/" in row["Evidence"]


def test_build_brand_sheet_empty() -> None:
    df = build_brand_sheet([])
    assert list(df.columns) == ["Suspect Domain", "Category", "Risk Score", "Sources", "Domain Registered", "Why Flagged", "Evidence"]
    assert len(df) == 0


def test_categorize() -> None:
    from scraper.brand_monitor import categorize
    brands = ["bbcincorp", "bcorpsec"]
    assert categorize("bbcincorplimited.website3.me", brands).startswith("impersonation")
    assert categorize("bbcincorp-hk.com", brands).startswith("impersonation")
    assert categorize("trustpilot.com", brands).startswith("known platform")
    assert categorize("crunchbase.com", brands).startswith("known platform")
    assert categorize("afficaglobal.com", brands, verified=True) == "unknown site — verify"
    # A search hit not confirmed on the page is downgraded, not trusted.
    assert categorize("x-kom.pl", brands, verified=False).startswith("unverified")


def test_find_excerpt() -> None:
    from scraper.brand_monitor import find_excerpt
    page = "Contact us. Registered office: Office 3906, 39th Floor, The Center. Thanks."
    ex = find_excerpt(page, "Office 3906, 39th Floor, The Center")
    assert "Office 3906" in ex and ex.startswith("...")
    # Slightly different formatting still matches on the leading chunk.
    assert find_excerpt("... office 3906 39th the center 99 queen ...", "Office 3906, 39th, The Center, 99 Queen's Road")
    assert find_excerpt("totally unrelated page about cats", "Office 3906") == ""


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
    mon = BrandMonitor(enricher=enricher, age=_FakeAge(), pause_s=0, verify=False)
    # Stub the keyless network calls.
    monkeypatch.setattr(mon, "_crtsh", lambda term: {"bbcincorp-hk.com", "bbcincorp.com"})
    monkeypatch.setattr(mon, "_urlscan", lambda term: [("fakebbc.net", "https://fakebbc.net/x")])
    suspects = mon.scan(wl)
    domains = {s.domain for s in suspects}
    assert "globalchaincp.com" in domains       # address reuse via search
    assert "bbcincorp-hk.com" in domains         # typosquat via crt.sh
    assert "fakebbc.net" in domains              # via urlscan
    assert "bbcincorp.com" not in domains        # official allow-listed
    # A brand-in-domain typosquat is impersonation → ranks above address reuse.
    assert suspects[0].domain == "bbcincorp-hk.com"
    assert suspects[0].category.startswith("impersonation")
