#!/usr/bin/env python3
"""Smoke tests for scripts/_unified_report.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from _unified_report import build_shape_layer, build_unified_report, write_unified_report

CLEAN_PACKAGE = {
    "version": "1.1",
    "extensions": [],
    "publishedDate": "2025-04-28T09:00:00+08:00",
    "releases": [
        {
            "ocid": "ocds-philgeps-1",
            "id": "r1",
            "date": "2025-04-28T09:00:00+08:00",
            "initiationType": "tender",
            "tag": ["compiled"],
            "tender": {
                "tenderPeriod": {
                    "startDate": "2025-04-01T08:00:00+08:00",
                    "endDate": "2025-04-22T10:00:00+08:00",
                }
            },
        }
    ],
}

DQ_SAMPLE = {
    "input_file": "test.csv",
    "input_bytes": 100,
    "schema_detected": "schema_3",
    "compiled_release_count": 1,
    "rows_seen": 10,
    "rows_committed": 9,
    "rows_quarantined": 1,
    "severity_counts": {"error": 1, "warning": 2, "info": 3},
    "rule_counts": [
        {"rule": "unawarded_tender", "severity": "info", "count": 3},
        {"rule": "placeholder_bid_ref", "severity": "warning", "count": 2},
        {"rule": "bad_date", "severity": "error", "count": 1},
    ],
    "quarantined_samples": [],
    "warning_samples": [],
    "info_samples": [],
}


def test_shape_layer_clean() -> None:
    layer = build_shape_layer(CLEAN_PACKAGE)
    assert layer["passed"] is True
    assert layer["issue_count"] == 0


def test_shape_layer_detects_bad_date() -> None:
    bad = json.loads(json.dumps(CLEAN_PACKAGE))
    bad["releases"][0]["date"] = "2025-05-12"
    layer = build_shape_layer(bad)
    assert layer["passed"] is False
    assert layer["issue_count"] >= 1


def test_unified_report_merges_layers() -> None:
    report = build_unified_report(
        dq_payload=DQ_SAMPLE,
        package=CLEAN_PACKAGE,
        run_ocds=False,
    )
    assert report["layers"]["source_dq"]["severity_counts"]["warning"] == 2
    assert report["layers"]["shape_preflight"]["passed"] is True
    assert report["summary"]["finding_counts"]["source_info"] == 3
    assert any(f["rule"] == "unawarded_tender" for f in report["summary"]["top_findings"])


def test_write_unified_report(tmp_path: Path) -> None:
    report = build_unified_report(dq_payload=DQ_SAMPLE, package=CLEAN_PACKAGE, run_ocds=False)
    path = write_unified_report(tmp_path / "out", report, write_validation_json=False)
    assert path.exists()
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["report_version"] == "1"
    assert "_validation_full" not in loaded


def main() -> int:
    failures: list[str] = []
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        tests = [
            ("shape layer clean", test_shape_layer_clean),
            ("shape layer bad date", test_shape_layer_detects_bad_date),
            ("unified report merges layers", test_unified_report_merges_layers),
            ("write unified report", lambda: test_write_unified_report(tmp_path)),
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
    print("\nAll unified-report tests passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
