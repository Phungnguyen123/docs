"""Offline unit tests for OSINT trace helpers (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.osint_trace import (
    OsintTracer,
    build_osint_sheets,
    collect_pivots,
    is_trace_relevant,
    platform_of,
)


def test_platform_of() -> None:
    assert platform_of("https://t.me/somegroup") == "Telegram"
    assert platform_of("https://www.reddit.com/r/scams/x") == "Reddit"
    assert platform_of("https://www.quora.com/q") == "Quora"
    assert platform_of("https://discord.gg/abc") == "Discord"
    assert platform_of("https://www.scamadviser.com/x") == "Scam-report"
    assert platform_of("https://blackhatworld.com/threads/x") == "Forum/Community"
    assert platform_of("https://randomblog.example/post") == "Web"


def test_is_trace_relevant() -> None:
    assert is_trace_relevant({"link": "https://t.me/g", "title": "", "snippet": ""})
    assert is_trace_relevant({"link": "https://x.example/p", "title": "SCAM warning", "snippet": ""})
    assert not is_trace_relevant({"link": "https://x.example/p", "title": "nice product", "snippet": "buy"})


def test_collect_pivots_address_and_domains() -> None:
    rows = [
        {"Registered Address": "OFFICE 3906, THE CENTER, HK", "Website": "https://ring.shop", "Other Domains": "", "Marketplace Listings": ""},
        {"Registered Address": "office 3906, the center, hk", "Website": "https://ring.shop", "Other Domains": "second.store", "Marketplace Listings": ""},
        {"Registered Address": "office 3906, the center, hk", "Website": "", "Other Domains": "", "Marketplace Listings": "https://www.etsy.com/shop/x"},
    ]
    addresses, domains = collect_pivots(rows, shared_min=3, max_domains=25)
    assert addresses == ["OFFICE 3906, THE CENTER, HK"]  # 3 companies share it
    assert "ring.shop" in domains and "second.store" in domains
    assert not any("etsy" in d for d in domains)  # marketplace excluded from pivots


def test_collect_pivots_below_threshold() -> None:
    rows = [
        {"Registered Address": "A", "Website": "", "Other Domains": "", "Marketplace Listings": ""},
        {"Registered Address": "B", "Website": "", "Other Domains": "", "Marketplace Listings": ""},
    ]
    addresses, _ = collect_pivots(rows, shared_min=3)
    assert addresses == []


class _FakeEnricher:
    def __init__(self, mapping):
        self._mapping = mapping

    def enabled(self):
        return True

    def provider(self):
        return "fake"

    def raw_results(self, query):
        for needle, results in self._mapping.items():
            if needle in query:
                return results
        return []


def test_tracer_collects_and_dedups() -> None:
    rows = [
        {"Registered Address": "THE CENTER, HK", "Website": "https://ring.shop", "Other Domains": "", "Marketplace Listings": ""},
        {"Registered Address": "the center, hk", "Website": "https://ring.shop", "Other Domains": "", "Marketplace Listings": ""},
        {"Registered Address": "the center, hk", "Website": "https://ring.shop", "Other Domains": "", "Marketplace Listings": ""},
    ]
    enricher = _FakeEnricher({
        "THE CENTER": [
            {"link": "https://www.reddit.com/r/scams/comments/abc", "title": "shell company factory at The Center", "snippet": "scam"},
        ],
        "ring.shop": [
            {"link": "https://t.me/scamalert", "title": "ring.shop is a scam store", "snippet": ""},
            {"link": "https://legit-blog.example/nice", "title": "nice", "snippet": "great"},  # irrelevant -> dropped
        ],
    })
    mentions = OsintTracer(enricher, pause_s=0).trace(rows, shared_min=3)
    urls = {m.url for m in mentions}
    assert "https://www.reddit.com/r/scams/comments/abc" in urls
    assert "https://t.me/scamalert" in urls
    assert "https://legit-blog.example/nice" not in urls
    sheets = build_osint_sheets(mentions)
    assert "OSINT Trace" in sheets and "OSINT Summary" in sheets
    assert len(sheets["OSINT Trace"]) == 2


def test_build_osint_sheets_empty() -> None:
    assert build_osint_sheets([]) == {}
