#!/usr/bin/env python3
"""Smoke tests for scripts/_data_quality group validation and run reporting."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _data_quality import RunReport, validate_group, validate_process_group, validate_row  # noqa: E402


def test_process_group_field_conflict() -> None:
    report = validate_process_group(
        [
            (1, {"procuring_entity": "Agency A", "award_reference_no": "A1", "line_item_no": "1"}),
            (2, {"procuring_entity": "Agency B", "award_reference_no": "A2", "line_item_no": "2"}),
        ],
        process_key="bid:BID-1",
    )
    rules = [i.rule for i in report.issues]
    assert "group_field_conflict" in rules


def test_duplicate_line_item_no_info() -> None:
    report = validate_group(
        [
            (1, {"line_item_no": "1", "item_name": "Widget A"}),
            (2, {"line_item_no": "1", "item_name": "Widget B"}),
        ],
        award_reference_no="AWD-2",
    )
    rules = [i.rule for i in report.issues]
    assert "duplicate_line_item_no" in rules
    assert all(i.severity == "info" for i in report if i.rule == "duplicate_line_item_no")


def test_warning_sampling_diversifies_rules() -> None:
    run = RunReport()
    for i in range(10):
        report = validate_row(
            {"award_reference_no": f"A-{i}", "procuring_entity": "PE", "bid_reference_no": "0"},
            row_index=i + 1,
        )
        run.add(
            i + 1,
            report,
            canonical={"award_reference_no": f"A-{i}", "procuring_entity": "PE", "bid_reference_no": "0"},
        )
    group_report = validate_process_group(
        [
            (11, {"line_item_no": "1", "item_name": "A", "procuring_entity": "X", "award_reference_no": "A1"}),
            (12, {"line_item_no": "1", "item_name": "B", "procuring_entity": "Y", "award_reference_no": "A2"}),
        ],
        process_key="bid:BID-3",
    )
    run.add_group("bid:BID-3", [11, 12], group_report)
    rules = {
        issue["rule"]
        for sample in run.warning_samples
        for issue in sample["issues"]
    }
    assert "group_field_conflict" in rules
    assert sum(1 for s in run.warning_samples if s.get("row_index") is not None) <= 5
    assert any(s.get("row_entry") for s in run.warning_samples if s.get("row_index") is not None)


def test_issue_group_counts() -> None:
    run = RunReport()
    for i in range(3):
        report = validate_row(
            {
                "award_reference_no": f"A-{i}",
                "procuring_entity": "PE",
                "bid_reference_no": "0",
                "approved_budget": "0",
                "award_notice_status": "Posted",
            },
            row_index=i + 1,
        )
        run.add(i + 1, report, canonical={"award_reference_no": f"A-{i}"})
    counts = {(e["rule"], e["field"], e["pattern"]): e["count"] for e in run.issue_group_counts()}
    assert counts[("non_positive_amount", "approved_budget", "`approved_budget` is non-positive (0.0)")] == 3
    payload = run.to_dict()
    assert "issue_group_counts" in payload
    assert len(payload["issue_group_counts"]) >= 1


def main() -> int:
    failures: list[str] = []
    for name, fn in [
        ("process group field conflict", test_process_group_field_conflict),
        ("duplicate_line_item_no info", test_duplicate_line_item_no_info),
        ("warning sampling diversifies rules", test_warning_sampling_diversifies_rules),
        ("issue group counts", test_issue_group_counts),
    ]:
        try:
            fn()
            print(f"[ok] {name}")
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{name}: {exc}")
            print(f"[FAIL] {name}: {exc}", file=sys.stderr)
    if failures:
        return 1
    print("\nAll data-quality guards behave as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
