#!/usr/bin/env python3
"""Edge-case regression tests for PhilGEPS → OCDS pipeline.

Covers schema detection, date coercion, data-quality rules, and compiler
behaviour on formats we hit in real exports (S1 XLSX through S5 V2 CSV).

    python scripts/test_edge_cases.py
"""

from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from _data_quality import is_null, parse_date, validate_row  # noqa: E402
from _ocds_checks import _parse_rfc3339, check_release_package  # noqa: E402
from _ocds_compiler import compile_grouped  # noqa: E402
from transform_to_ocds import (  # noqa: E402
    S1_MARKERS,
    S2_MARKERS,
    S3_MARKERS,
    S4_MARKERS,
    _canonicalize,
    detect_schema,
)


def _load_configs() -> tuple[dict, dict, dict]:
    if yaml is None:
        raise RuntimeError("PyYAML required")
    ocds_cfg = yaml.safe_load((ROOT / "config" / "canonical_to_ocds.yaml").read_text(encoding="utf-8"))
    codelists = yaml.safe_load((ROOT / "config" / "ocds_codelist_mappings.yaml").read_text(encoding="utf-8"))
    schema_mappings = yaml.safe_load((ROOT / "config" / "schema_mappings.yaml").read_text(encoding="utf-8"))
    field_types: dict[str, str] = {}
    for ftype, fields in (schema_mappings.get("field_types") or {}).items():
        for field in fields:
            field_types[field] = ftype
    return ocds_cfg, field_types, codelists, schema_mappings


def test_parse_date_formats() -> None:
    cases = {
        "02/10/2024": "2024-10-02T12:00:00+08:00",
        "2021-10-13T14:53:14.740000+08:00": "2021-10-13T14:53:14+08:00",
        "2002-01-02 00:00:00": "2002-01-02T00:00:00+08:00",
    }
    for raw, expected in cases.items():
        iso, err = parse_date(raw)
        assert err is None, f"{raw!r}: {err}"
        assert iso == expected, f"{raw!r} -> {iso!r}, want {expected!r}"
        assert _parse_rfc3339(iso), f"pre-flight rejects {iso!r}"


def test_parse_date_rejects_garbage() -> None:
    iso, err = parse_date("not-a-date")
    assert iso is None
    assert err is not None


def test_xlsx_datetime_normalization() -> None:
    """openpyxl returns datetime objects; pipeline must stringify before parse_date."""
    from scratch.sample_and_transform import _normalize_cell  # noqa: E402

    cell = dt.datetime(2002, 1, 2, 0, 0, 0)
    text = _normalize_cell(cell)
    iso, err = parse_date(text)
    assert err is None, err
    assert iso == "2002-01-02T00:00:00+08:00"
    assert _parse_rfc3339(iso)


def test_detect_schema_all_variants() -> None:
    s1_header = list(S1_MARKERS) + ["Publish Date", "Contract Efectivity Date"]
    s2_header = list(S2_MARKERS) + ["Publish Date"]
    s3_header = list(S3_MARKERS) + ["Published Date"]
    s4_header = list(S4_MARKERS) + ["Published Date (Award)"]

    assert detect_schema(s1_header) == "schema_1"
    assert detect_schema(s2_header) == "schema_2"
    assert detect_schema(s3_header) == "schema_3"
    assert detect_schema(s4_header) == "schema_4"
    # S2 must not match when S3 markers present.
    assert detect_schema(s3_header + ["Unit of Measurement"]) == "schema_3"


def test_s1_typo_column_maps() -> None:
    _, _, _, schema_mappings = _load_configs()
    col_map = schema_mappings["schema_1"]
    assert col_map["Contract Efectivity Date"] == "contract_effectivity_date"
    assert col_map["Publish Date(Award)"] == "award_published_date"

    raw = {
        "Organization Name": "Agency",
        "Award No.": "A-1",
        "Reference ID": "B-1",
        "Contract Efectivity Date": "01/01/2024",
        "Contract End Date": "31/12/2024",
    }
    canon = _canonicalize(raw, col_map)
    iso, err = parse_date(canon["contract_effectivity_date"])
    assert err is None
    assert iso is not None


def test_placeholder_bid_reference_warning() -> None:
    report = validate_row(
        {
            "award_reference_no": "AWD-1",
            "procuring_entity": "PE",
            "bid_reference_no": "0",
        },
        row_index=1,
    )
    rules = [i.rule for i in report.issues]
    assert "placeholder_bid_ref" in rules


def test_award_missing_expected_for_posted() -> None:
    report = validate_row(
        {
            "award_reference_no": "AWD-2",
            "procuring_entity": "PE",
            "bid_reference_no": "123",
            "award_notice_status": "Posted",
            "awardee_organization_name": "",
            "contract_amount": "1000",
        },
        row_index=2,
    )
    rules = [i.rule for i in report.issues]
    assert "award_missing_expected" in rules


def test_unawarded_tender_is_info_not_error() -> None:
    report = validate_row(
        {
            "award_reference_no": "",
            "procuring_entity": "PE",
            "bid_reference_no": "123",
            "bid_notice_status": "Closed",
            "contract_amount": "",
        },
        row_index=3,
    )
    rules = {i.rule: i.severity for i in report.issues}
    assert rules.get("unawarded_tender") == "info"
    assert "missing_identity" not in rules


def test_inverted_contract_period() -> None:
    report = validate_row(
        {
            "award_reference_no": "AWD-3",
            "procuring_entity": "PE",
            "bid_reference_no": "123",
            "contract_effectivity_date": "31/12/2024",
            "contract_end_date": "01/01/2024",
        },
        row_index=4,
    )
    assert any(i.rule == "inverted_contract_period" for i in report.issues)


def test_s3_microsecond_date_compiles_clean() -> None:
    ocds_cfg, field_types, codelists, _ = _load_configs()
    row = {
        "award_reference_no": "5257621-001",
        "procuring_entity": "Test Agency",
        "bid_reference_no": "12345",
        "notice_title": "Test",
        "item_description": "Item",
        "item_name": "Widget",
        "quantity": "1",
        "item_budget": "1000",
        "line_item_no": "1",
        "published_date": "2021-10-13T14:53:14.740000+08:00",
        "award_published_date": "15/10/2024",
        "award_date": "01/10/2024",
        "closing_date": "30/09/2024",
        "procurement_mode": "Public Bidding",
        "bid_notice_status": "Awarded",
        "award_notice_status": "Awarded",
        "awardee_organization_name": "Prime Inc.",
        "contract_amount": "5000",
        "unspsc_code": "12345678",
        "uom": "unit",
    }
    release = compile_grouped([row], ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    assert ".740000" not in release["date"]
    pkg = {
        "version": "1.1",
        "extensions": [],
        "publishedDate": release["date"],
        "releases": [release],
    }
    issues = check_release_package(pkg)
    assert not issues, issues


def test_jv_comma_split() -> None:
    ocds_cfg, field_types, codelists, _ = _load_configs()
    row = {
        "award_reference_no": "5257621-002",
        "procuring_entity": "Test Agency",
        "bid_reference_no": "12345",
        "notice_title": "Test",
        "item_description": "Item",
        "item_name": "Widget",
        "quantity": "1",
        "line_item_no": "1",
        "awardee_organization_name": "Prime Inc.",
        "awardee_joint_venture": "Partner A, Partner B",
        "contract_amount": "5000",
        "award_notice_status": "Awarded",
        "bid_notice_status": "Awarded",
    }
    release = compile_grouped([row], ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    names = [s["name"] for s in release["awards"][0]["suppliers"]]
    assert names == ["Prime Inc.", "Partner A", "Partner B"]


def test_s3_bidders_extension() -> None:
    ocds_cfg, field_types, codelists, _ = _load_configs()
    row = {
        "award_reference_no": "5257621-003",
        "procuring_entity": "Test Agency",
        "bid_reference_no": "12345",
        "notice_title": "Test",
        "item_description": "Item",
        "item_name": "Widget",
        "quantity": "1",
        "line_item_no": "1",
        "list_of_bidders": "Bidder One; Bidder Two",
        "awardee_organization_name": "Prime Inc.",
        "contract_amount": "5000",
        "award_notice_status": "Awarded",
        "bid_notice_status": "Awarded",
    }
    release = compile_grouped([row], ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    bids = release.get("bids", {}).get("details", [])
    assert len(bids) == 2
    assert {b["tenderers"][0]["name"] for b in bids} == {"Bidder One", "Bidder Two"}


def main() -> int:
    failures: list[str] = []
    tests = [
        ("parse_date formats", test_parse_date_formats),
        ("parse_date rejects garbage", test_parse_date_rejects_garbage),
        ("XLSX datetime normalization", test_xlsx_datetime_normalization),
        ("detect_schema all variants", test_detect_schema_all_variants),
        ("S1 typo column maps", test_s1_typo_column_maps),
        ("placeholder bid_reference warning", test_placeholder_bid_reference_warning),
        ("award_missing_expected for Posted", test_award_missing_expected_for_posted),
        ("unawarded tender info", test_unawarded_tender_is_info_not_error),
        ("inverted contract period", test_inverted_contract_period),
        ("S3 microsecond date compiles clean", test_s3_microsecond_date_compiles_clean),
        ("JV comma split", test_jv_comma_split),
        ("S3 bidders extension", test_s3_bidders_extension),
    ]
    for name, fn in tests:
        try:
            fn()
            print(f"[ok] {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
    if failures:
        return 1
    print(f"\nAll {len(tests)} edge-case tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
