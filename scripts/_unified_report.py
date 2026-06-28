"""Build a single JSON report merging source DQ, shape pre-flight, and OCDS validation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from _ocds_checks import check_release_package
from _ocds_validate import run_ocds_validation

REPORT_VERSION = "1"

# Fields copied from the per-run DQ payload into ``layers.source_dq``.
SOURCE_DQ_KEYS = (
    "rows_seen",
    "rows_committed",
    "rows_quarantined",
    "severity_counts",
    "rule_counts",
    "issue_group_counts",
    "quarantined_samples",
    "quarantined_samples_omitted",
    "warning_samples",
    "warning_samples_omitted",
    "info_samples",
    "info_samples_omitted",
)


def build_shape_layer(package: dict) -> dict[str, Any]:
    """Run OCDS shape pre-flight checks (scripts/_ocds_checks)."""
    issues = check_release_package(package)
    rule_counts = []
    if issues:
        rule_counts.append({
            "rule": "ocds_shape_preflight",
            "severity": "error",
            "layer": "shape_preflight",
            "count": len(issues),
        })
    return {
        "passed": not issues,
        "issue_count": len(issues),
        "issues": issues,
        "first_issues": issues[:15],
        "rule_counts": rule_counts,
    }


def _source_dq_layer(dq_payload: dict) -> dict[str, Any]:
    layer = {k: dq_payload[k] for k in SOURCE_DQ_KEYS if k in dq_payload}
    layer.setdefault("severity_counts", {"error": 0, "warning": 0, "info": 0})
    layer.setdefault("rule_counts", [])
    layer.setdefault("issue_group_counts", [])
    return layer


def _ocds_layer_summary(validation: dict) -> dict[str, Any]:
    """Public-facing slice of libcoveocds results (omit full error blobs)."""
    return {
        "available": validation.get("available"),
        "passed": validation.get("passed"),
        "error": validation.get("error"),
        "validation_error_count": validation.get("validation_error_count", 0),
        "validation_error_groups": validation.get("validation_error_groups", 0),
        "additional_checks_count": validation.get("additional_checks_count", 0),
        "conformance_error_count": validation.get("conformance_error_count", 0),
        "deprecated_field_count": validation.get("deprecated_field_count", 0),
        "first_errors": validation.get("first_errors") or [],
        "rule_counts": validation.get("error_type_counts") or [],
    }


def build_top_findings(
    source_dq: dict,
    shape: dict,
    ocds: dict,
    *,
    limit: int = 20,
) -> list[dict]:
    """Merge rule counts from all layers, sorted by count descending."""
    merged: list[dict] = []
    for entry in source_dq.get("rule_counts") or []:
        merged.append({
            "layer": "source_dq",
            "rule": entry["rule"],
            "severity": entry.get("severity", "warning"),
            "count": entry["count"],
        })
    for entry in shape.get("rule_counts") or []:
        merged.append(dict(entry))
    for entry in ocds.get("rule_counts") or []:
        merged.append(dict(entry))
    merged.sort(key=lambda x: x["count"], reverse=True)
    return merged[:limit]


def build_summary(
    source_dq: dict,
    shape: dict,
    ocds: dict,
    top_findings: list[dict],
) -> dict[str, Any]:
    sc = source_dq.get("severity_counts") or {}
    shape_count = shape.get("issue_count", 0)
    ocds_val = ocds.get("validation_error_count", 0)
    ocds_conf = ocds.get("conformance_error_count", 0)
    source_total = sum(sc.get(k, 0) for k in ("error", "warning", "info"))

    finding_counts = {
        "source_error": sc.get("error", 0),
        "source_warning": sc.get("warning", 0),
        "source_info": sc.get("info", 0),
        "shape_error": shape_count,
        "ocds_validation_error": ocds_val,
        "ocds_conformance_error": ocds_conf,
        "ocds_additional_check": ocds.get("additional_checks_count", 0),
    }
    all_passed = (
        sc.get("error", 0) == 0
        and shape.get("passed", False)
        and ocds.get("passed") is not False
        and ocds_conf == 0
    )
    return {
        "all_passed": all_passed,
        "total_findings": source_total + shape_count + ocds_val + ocds_conf,
        "finding_counts": finding_counts,
        "top_findings": top_findings,
    }


def build_unified_report(
    *,
    dq_payload: dict,
    package: dict,
    package_path: Path | str | None = None,
    dq_path: Path | str | None = None,
    validation_path: Path | str | None = None,
    run_ocds: bool = True,
    extra: dict | None = None,
) -> dict[str, Any]:
    """Assemble the unified report dict (does not write to disk)."""
    source_dq = _source_dq_layer(dq_payload)
    shape = build_shape_layer(package)

    if run_ocds and shape.get("passed"):
        validation_full = run_ocds_validation(package)
    elif run_ocds:
        validation_full = {
            "available": True,
            "passed": False,
            "error": "skipped: shape pre-flight failed",
            "validation_error_count": 0,
            "validation_error_groups": 0,
            "additional_checks_count": 0,
            "conformance_error_count": 0,
            "deprecated_field_count": 0,
            "validation_errors": [],
            "additional_checks": [],
            "conformance_errors": {},
            "deprecated_fields": {},
            "first_errors": [],
            "error_type_counts": [],
        }
    else:
        validation_full = {
            "available": False,
            "passed": None,
            "error": "skipped by caller",
            "validation_error_count": 0,
            "validation_error_groups": 0,
            "additional_checks_count": 0,
            "conformance_error_count": 0,
            "deprecated_field_count": 0,
            "validation_errors": [],
            "additional_checks": [],
            "conformance_errors": {},
            "deprecated_fields": {},
            "first_errors": [],
            "error_type_counts": [],
        }

    ocds_public = _ocds_layer_summary(validation_full)
    top_findings = build_top_findings(source_dq, shape, ocds_public)
    summary = build_summary(source_dq, shape, ocds_public, top_findings)

    report: dict[str, Any] = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_file": dq_payload.get("input_file"),
        "input_bytes": dq_payload.get("input_bytes"),
        "schema_detected": dq_payload.get("schema_detected"),
        "compiled_release_count": dq_payload.get("compiled_release_count"),
        "layers": {
            "source_dq": source_dq,
            "shape_preflight": shape,
            "ocds_validation": ocds_public,
        },
        "summary": summary,
        "artifacts": {
            "package": str(package_path) if package_path else None,
            "dq": str(dq_path) if dq_path else None,
            "validation": str(validation_path) if validation_path else None,
            "unified": None,
        },
    }
    if extra:
        report.update(extra)
    # Keep full libcoveocds payload for .validation.json compatibility
    report["_validation_full"] = validation_full
    return report


def write_unified_report(
    out_base: Path,
    report: dict,
    *,
    write_validation_json: bool = True,
) -> Path:
    """Write ``<out_base>.report.json`` and optionally ``<out_base>.validation.json``."""
    out_base = Path(out_base)
    report_path = out_base.with_suffix(".report.json")

    validation_full = report.pop("_validation_full", {})
    artifacts = report.setdefault("artifacts", {})
    artifacts["unified"] = str(report_path)

    val_path = None
    if write_validation_json and validation_full.get("available"):
        val_path = out_base.with_suffix(".validation.json")
        val_path.write_text(
            json.dumps(
                {
                    "validation_errors": validation_full.get("validation_errors") or [],
                    "additional_checks": validation_full.get("additional_checks") or [],
                    "conformance_errors": validation_full.get("conformance_errors") or {},
                    "deprecated_fields": validation_full.get("deprecated_fields") or {},
                    "validation_stats": validation_full.get("validation_stats"),
                },
                indent=2,
                default=str,
                ensure_ascii=False,
            ) + "\n",
            encoding="utf-8",
        )
        artifacts["validation"] = str(val_path)

    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )

    return report_path


def print_unified_summary(report: dict) -> None:
    """Print a human-readable summary to stdout."""
    sc = report["layers"]["source_dq"].get("severity_counts") or {}
    shape = report["layers"]["shape_preflight"]
    ocds = report["layers"]["ocds_validation"]
    summary = report.get("summary") or {}

    print()
    print("=" * 70)
    print("Unified report")
    print("=" * 70)
    print(f"Input:      {report.get('input_file')}")
    print(f"Schema:     {report.get('schema_detected')}")
    print(f"Releases:   {report.get('compiled_release_count')}")
    print()
    print("Layers:")
    print(f"  source DQ:  E={sc.get('error', 0)} W={sc.get('warning', 0)} I={sc.get('info', 0)}")
    print(f"  shape:      {'PASS' if shape.get('passed') else 'FAIL'} ({shape.get('issue_count', 0)} issues)")
    if ocds.get("available"):
        status = "PASS" if ocds.get("passed") else "FAIL"
        print(
            f"  libcoveocds: {status} "
            f"({ocds.get('validation_error_count', 0)} val, "
            f"{ocds.get('conformance_error_count', 0)} conformance)"
        )
    else:
        print(f"  libcoveocds: skipped ({ocds.get('error')})")
    print()
    if summary.get("top_findings"):
        print("Top findings (all layers):")
        for f in summary["top_findings"][:8]:
            print(f"  [{f.get('layer', '?'):16s}] {f['severity']:8s} {f['count']:>6}  {f['rule']}")
    print(f"\nOverall: {'PASS' if summary.get('all_passed') else 'ISSUES FOUND'}")
    print("=" * 70)
