"""Offline unit tests for normalisation, matching, and field mapping."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import SETTINGS
from scraper.parser import map_labels_to_fields
from scraper.utils import choose_best_match, normalize_name, similarity


def test_normalize_name_handles_case_punct_space_accents() -> None:
    assert normalize_name("Foo  Ltd.") == "foo ltd"
    assert normalize_name("FOO LTD") == normalize_name("foo ltd")
    assert normalize_name("Café  Ltd!!") == "cafe ltd"
    assert normalize_name("  A,,B  C ") == "ab c"


def test_similarity_identical_after_normalisation_is_one() -> None:
    assert similarity("HELENA LIMITED", "helena  limited.") == 1.0


def test_choose_best_match_prefers_exact() -> None:
    result = choose_best_match(
        "HELENA LIMITED",
        ["Helena Holdings Limited", "HELENA LIMITED", "Helena Foods Ltd"],
        min_confidence=SETTINGS.min_confidence,
        strong_confidence=SETTINGS.strong_confidence,
    )
    assert result.status == "exact"
    assert result.index == 1
    assert result.confidence == 1.0


def test_choose_best_match_fuzzy_when_no_exact() -> None:
    result = choose_best_match(
        "FITAZZY LIMITED",
        ["Fitazzy Ltd", "Totally Different Corp"],
        min_confidence=SETTINGS.min_confidence,
        strong_confidence=SETTINGS.strong_confidence,
    )
    assert result.index == 0
    assert result.status in {"fuzzy", "low_confidence"}
    assert 0.0 < result.confidence <= 1.0


def test_choose_best_match_empty_is_not_found() -> None:
    result = choose_best_match(
        "ANYTHING LTD",
        [],
        min_confidence=SETTINGS.min_confidence,
        strong_confidence=SETTINGS.strong_confidence,
    )
    assert result.status == "not_found"
    assert result.index == -1


def test_map_labels_to_fields_basic() -> None:
    pairs = {
        "Company Number": "12345678",
        "Company Status": "Active",
        "Incorporation Date": "2020-01-15",
        "Registered Office Address": "1 High St, London",
        "Nature of Business": "Software",
        "Irrelevant": "ignore me",
    }
    mapped = map_labels_to_fields(pairs, SETTINGS.field_label_map)
    assert mapped["company_number"] == "12345678"
    assert mapped["company_status"] == "Active"
    assert mapped["incorporation_date"] == "2020-01-15"
    assert mapped["registered_address"] == "1 High St, London"
    assert mapped["business_nature"] == "Software"


def test_map_labels_prefers_specific_over_generic() -> None:
    # Both "Company Number" and a bare "Number" present; specific should win.
    pairs = {"Number": "999", "Company Number": "12345678"}
    mapped = map_labels_to_fields(pairs, SETTINGS.field_label_map)
    assert mapped["company_number"] == "12345678"


def test_map_labels_skips_missing_fields() -> None:
    mapped = map_labels_to_fields({"Company Number": "1"}, SETTINGS.field_label_map)
    assert "company_secretary" not in mapped
