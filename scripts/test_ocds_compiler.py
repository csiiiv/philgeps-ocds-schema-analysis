#!/usr/bin/env python3
"""Smoke tests for scripts/_ocds_compiler grouped compilation.

Verifies item-id disambiguation and JV supplier expansion — regression classes
we hit on real PhilGEPS S4 exports. Run via CI or directly:

    python scripts/test_ocds_compiler.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ocds_compiler import compile_grouped, resolve_release_display_collisions  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore


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
    return ocds_cfg, field_types, codelists


def _base_row(**overrides) -> dict:
    row = {
        "award_reference_no": "5257621-001",
        "procuring_entity": "Test Agency",
        "bid_reference_no": "0",
        "notice_title": "Test procurement",
        "item_description": "Line item",
        "item_name": "Widget",
        "quantity": "1",
        "item_budget": "1000",
        "line_item_no": "1",
        "awardee_organization_name": "Prime Contractor Inc.",
        "awardee_org_id": "SUP-001",
        "contract_amount": "5000",
        "award_date": "01/10/2024",
        "award_published_date": "15/10/2024",
        "published_date": "01/09/2024",
        "closing_date": "30/09/2024",
        "procurement_mode": "Public Bidding",
        "bid_notice_status": "Awarded",
        "award_notice_status": "Awarded",
        "unspsc_code": "12345678",
        "uom": "unit",
    }
    row.update(overrides)
    return row


def test_grouped_item_ids_unique() -> None:
    ocds_cfg, field_types, codelists = _load_configs()
    rows = [
        _base_row(item_name="Item A"),
        _base_row(item_name="Item B"),
        _base_row(item_name="Item C"),
    ]
    release = compile_grouped(rows, ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    item_ids = [item["id"] for item in release["tender"]["items"]]
    assert item_ids == ["1", "1-2", "1-3"], f"expected disambiguated ids, got {item_ids}"
    assert len(set(item_ids)) == 3


def test_jv_suppliers_expanded() -> None:
    ocds_cfg, field_types, codelists = _load_configs()
    row = _base_row(
        awardee_joint_venture="Partner One Ltd.; Partner Two Ltd.",
    )
    release = compile_grouped([row], ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    supplier_names = [s["name"] for s in release["awards"][0]["suppliers"]]
    assert supplier_names == [
        "Prime Contractor Inc.",
        "Partner One Ltd.",
        "Partner Two Ltd.",
    ], supplier_names
    party_names = sorted(p["name"] for p in release["parties"] if "supplier" in p["roles"])
    assert party_names == sorted(supplier_names)


def test_multi_award_same_bid() -> None:
    """BCDA-2004-0222 pattern: one bid, four awards, four line items."""
    ocds_cfg, field_types, codelists = _load_configs()
    shared = {
        "bid_reference_no": "39785",
        "solicitation_no": "BCDA-2004-0222",
        "procuring_entity": "BASES CONVERSION DEVELOPMENT AUTHORITY - Main",
        "approved_budget": "50000",
        "notice_title": "Multi-award test",
        "published_date": "01/01/2004",
        "closing_date": "15/01/2004",
        "procurement_mode": "Public Bidding",
        "bid_notice_status": "Awarded",
        "award_notice_status": "Awarded",
        "awardee_organization_name": "Supplier Inc.",
        "awardee_org_id": "SUP-100",
        "award_date": "01/02/2004",
        "award_published_date": "10/02/2004",
    }
    rows = [
        _base_row(
            **shared,
            award_reference_no="6962",
            line_item_no="1",
            item_name="ITEM1",
            item_budget="19945",
            contract_amount="19945",
        ),
        _base_row(
            **shared,
            award_reference_no="6964",
            line_item_no="2",
            item_name="ITEM2",
            item_budget="5840",
            contract_amount="5840",
        ),
        _base_row(
            **shared,
            award_reference_no="6965",
            line_item_no="3",
            item_name="ITEM3",
            item_budget="4928",
            contract_amount="4928",
        ),
        _base_row(
            **shared,
            award_reference_no="6966",
            line_item_no="4",
            item_name="ITEM4",
            item_budget="5830",
            contract_amount="5830",
        ),
    ]
    release = compile_grouped(rows, ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)
    assert release is not None
    assert release["ocid"] == "ocds-philgeps-39785"
    assert release["id"] == "39785"
    assert len(release["tender"]["items"]) == 4
    assert len(release["awards"]) == 4
    assert len(release["contracts"]) == 4
    award_ids = [a["id"] for a in release["awards"]]
    assert award_ids == ["6962", "6964", "6965", "6966"]
    assert len(release["awards"][0]["items"]) == 1
    assert release["awards"][0]["items"][0]["name"] == "ITEM1"
    assert release["philgeps"]["solicitationNo"] == "BCDA-2004-0222"


def test_display_id_collision_composite() -> None:
    """bid=0 + same solicitation + different awards → composite id after resolve."""
    ocds_cfg, field_types, codelists = _load_configs()
    shared = {
        "bid_reference_no": "0",
        "solicitation_no": "SHARED-SOL-001",
        "procuring_entity": "Test Agency",
        "notice_title": "Collision test",
        "published_date": "01/01/2024",
        "closing_date": "15/01/2024",
        "procurement_mode": "Public Bidding",
        "bid_notice_status": "Awarded",
        "award_notice_status": "Awarded",
        "awardee_organization_name": "Supplier Inc.",
        "awardee_org_id": "SUP-100",
        "award_date": "01/02/2024",
        "award_published_date": "10/02/2024",
        "item_name": "Widget",
        "quantity": "1",
        "item_budget": "1000",
        "line_item_no": "1",
        "contract_amount": "1000",
        "unspsc_code": "12345678",
        "uom": "unit",
    }
    r1 = compile_grouped(
        [_base_row(**shared, award_reference_no="AW-1")],
        ocds_cfg=ocds_cfg,
        field_types=field_types,
        codelists=codelists,
    )
    r2 = compile_grouped(
        [_base_row(**shared, award_reference_no="AW-2")],
        ocds_cfg=ocds_cfg,
        field_types=field_types,
        codelists=codelists,
    )
    assert r1 is not None and r2 is not None
    releases = [r1, r2]
    assert r1["id"] == r2["id"] == "SHARED-SOL-001"
    events = resolve_release_display_collisions(releases, ocid_prefix="ocds-philgeps")
    assert len(events) == 2
    ids = {r["id"] for r in releases}
    ocids = {r["ocid"] for r in releases}
    assert len(ids) == 2
    assert len(ocids) == 2
    assert all("SHARED-SOL-001" in e["resolved_id"] for e in events)


def main() -> int:
    failures: list[str] = []
    for name, fn in [
        ("grouped item ids unique", test_grouped_item_ids_unique),
        ("JV suppliers expanded", test_jv_suppliers_expanded),
        ("multi-award same bid", test_multi_award_same_bid),
        ("display id collision composite", test_display_id_collision_composite),
    ]:
        try:
            fn()
            print(f"[ok] {name}")
        except Exception as exc:  # noqa: BLE001 — test runner
            failures.append(f"{name}: {exc}")
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
    if failures:
        return 1
    print("\nAll compiler guards behave as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
