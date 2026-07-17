"""Offline unit tests for the Hong Kong CR API helpers (no network)."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.hk_api import (
    extract_records,
    match_records,
    record_english_name,
    record_to_company,
    strip_legal_suffix,
)


def test_strip_legal_suffix() -> None:
    assert strip_legal_suffix("GOLDEN DRAGON LIMITED") == "GOLDEN DRAGON"
    assert strip_legal_suffix("JADE PHOENIX LTD.") == "JADE PHOENIX"
    assert strip_legal_suffix("LUCKY STAR TRADING CO. LIMITED") == "LUCKY STAR TRADING"
    assert strip_legal_suffix("NOSUFFIX") == "NOSUFFIX"


def test_extract_records_list() -> None:
    assert extract_records([{"a": 1}, {"b": 2}]) == [{"a": 1}, {"b": 2}]


def test_extract_records_container_keys() -> None:
    assert extract_records({"result": [{"a": 1}]}) == [{"a": 1}]
    assert extract_records({"data": {"records": [{"x": 1}]}}) == [{"x": 1}]


def test_extract_records_fallback_first_list() -> None:
    assert extract_records({"meta": "x", "rows": [{"a": 1}]}) == [{"a": 1}]
    assert extract_records({"nothing": "here"}) == []


def test_record_english_name_prefers_english() -> None:
    rec = {"Comp_Name_Chi": "金龍有限公司", "Comp_Name_Eng": "GOLDEN DRAGON LIMITED"}
    assert record_english_name(rec) == "GOLDEN DRAGON LIMITED"


def test_record_to_company_tolerant_fields() -> None:
    rec = {
        "Brn": "C0001",
        "Comp_Name_Eng": "GOLDEN DRAGON LIMITED",
        "Comp_Name_Chi": "金龍有限公司",
        "Ro_Addr": "1 Queen's Road, Central, HK",
    }
    r = record_to_company(rec)
    assert r.company_number == "C0001"
    assert r.company_name == "GOLDEN DRAGON LIMITED"
    assert "Queen's Road" in r.registered_address
    assert r.company_status == "Live"
    assert r.source_url.startswith("https://data.gov.hk")


def test_record_to_company_joins_multiple_address_fields() -> None:
    rec = {
        "Brn": "C0002",
        "Company Name": "JADE LIMITED",
        "Addr_Line_1": "88 Nathan Road",
        "Addr_Line_2": "Kowloon",
    }
    r = record_to_company(rec)
    assert "88 Nathan Road" in r.registered_address
    assert "Kowloon" in r.registered_address


def test_match_records_picks_best() -> None:
    records = [
        {"Comp_Name_Eng": "GOLDEN DRAGON HOLDINGS LIMITED", "Brn": "C1"},
        {"Comp_Name_Eng": "GOLDEN DRAGON LIMITED", "Brn": "C2"},
    ]
    row, match = match_records(
        "GOLDEN DRAGON LIMITED", records, min_confidence=0.6, strong_confidence=0.85
    )
    assert row["Brn"] == "C2"
    assert match.status == "exact"


def test_match_records_empty() -> None:
    row, match = match_records("X", [], min_confidence=0.6, strong_confidence=0.85)
    assert row is None
    assert match.status == "not_found"
