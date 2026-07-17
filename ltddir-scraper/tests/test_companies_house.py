"""Offline unit tests for Companies House JSON -> record mapping."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scraper.companies_house import (
    company_web_url,
    format_address,
    previous_names,
    profile_to_record,
    split_officers,
)

SAMPLE_PROFILE = {
    "company_name": "HELENA LIMITED",
    "company_number": "12345678",
    "company_status": "active",
    "type": "ltd",
    "date_of_creation": "2015-04-01",
    "registered_office_address": {
        "address_line_1": "1 High Street",
        "locality": "London",
        "postal_code": "EC1A 1AA",
        "country": "United Kingdom",
    },
    "sic_codes": ["62012", "62020"],
    "previous_company_names": [
        {"name": "HELENA OLD LIMITED", "effective_from": "2010-01-01"},
    ],
}

SAMPLE_OFFICERS = [
    {"name": "SMITH, Jane", "officer_role": "director"},
    {"name": "DOE, John", "officer_role": "director", "resigned_on": "2020-01-01"},
    {"name": "BROWN, Sam", "officer_role": "secretary"},
]


def test_format_address_joins_nonempty() -> None:
    assert format_address(SAMPLE_PROFILE["registered_office_address"]) == (
        "1 High Street, London, EC1A 1AA, United Kingdom"
    )
    assert format_address(None) == ""
    assert format_address({}) == ""


def test_split_officers_active_only() -> None:
    directors, secretaries = split_officers(SAMPLE_OFFICERS)
    assert directors == "SMITH, Jane"  # resigned director excluded
    assert secretaries == "BROWN, Sam"


def test_previous_names_joined() -> None:
    assert previous_names(SAMPLE_PROFILE) == "HELENA OLD LIMITED"
    assert previous_names({}) == ""


def test_profile_to_record_full_mapping() -> None:
    rec = profile_to_record(
        SAMPLE_PROFILE, SAMPLE_OFFICERS, source_url=company_web_url("12345678")
    )
    assert rec.company_name == "HELENA LIMITED"
    assert rec.company_number == "12345678"
    assert rec.company_status == "Active"
    assert rec.company_type == "Private Limited Company"
    assert rec.incorporation_date == "2015-04-01"
    assert rec.registered_address.startswith("1 High Street")
    assert rec.directors == "SMITH, Jane"
    assert rec.company_secretary == "BROWN, Sam"
    assert rec.business_nature == "62012, 62020"
    assert rec.previous_names == "HELENA OLD LIMITED"
    assert rec.source_url.endswith("/company/12345678")


def test_profile_to_record_unknown_type_falls_back_to_code() -> None:
    rec = profile_to_record({"type": "weird-type"}, [], source_url="x")
    assert rec.company_type == "weird-type"


def test_web_url() -> None:
    assert company_web_url("SC123456").endswith("/company/SC123456")
