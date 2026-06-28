#!/usr/bin/env python3
"""Aggregate per-file and per-year unified reports into one combined report.

Reads ``references/transformed/full/**/*.report.json`` for source-level DQ
totals (each raw export counted once) and ``references/transformed/by_year/*.report.json``
for calendar-year release totals. Writes ``references/transformed/combined.report.json``.

Usage:
    python scripts/aggregate_dataset_report.py
    python scripts/aggregate_dataset_report.py --output references/transformed/combined.report.json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _unified_report import REPORT_VERSION, build_top_findings, build_summary  # noqa: E402
from _data_quality import merge_diverse_dq_samples  # noqa: E402
from _row_accounting import corpus_merge_accounting, merge_row_accounting_from_dqs  # noqa: E402

DEFAULT_FULL = ROOT / "references" / "transformed" / "full"
DEFAULT_BY_YEAR = ROOT / "references" / "transformed" / "by_year"
DEFAULT_OUT = ROOT / "references" / "transformed" / "combined.report.json"
SKIP_NAMES = {"full_dataset_results.json"}


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _dq_path_for_report(report_path: Path) -> Path:
    name = report_path.name
    if name.endswith(".report.json"):
        return report_path.with_name(name[: -len(".report.json")] + ".dq.json")
    return report_path.with_suffix(".dq.json")


def _merge_rule_counts(target: Counter, rules: list[dict]) -> None:
    for entry in rules or []:
        key = (entry.get("rule"), entry.get("severity"), entry.get("layer", "source_dq"))
        target[key] += int(entry.get("count") or 0)


def _merge_issue_group_counts(target: Counter, entries: list[dict]) -> None:
    for entry in entries or []:
        key = (
            entry.get("rule"),
            entry.get("severity"),
            entry.get("field"),
            entry.get("pattern"),
        )
        target[key] += int(entry.get("count") or 0)


def _issue_group_counts_to_list(counter: Counter) -> list[dict]:
    return [
        {
            "rule": rule,
            "severity": severity,
            "field": field,
            "pattern": pattern,
            "count": count,
        }
        for (rule, severity, field, pattern), count in counter.most_common()
    ]


def _rule_counts_to_list(counter: Counter) -> list[dict]:
    rows = []
    for (rule, severity, layer), count in counter.most_common():
        row = {"rule": rule, "severity": severity, "count": count}
        if layer != "source_dq":
            row["layer"] = layer
        rows.append(row)
    return rows


def discover_source_reports(full_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(full_root.rglob("*.report.json")):
        if path.name in SKIP_NAMES:
            continue
        out.append(path)
    return out


def discover_year_reports(by_year_root: Path) -> list[Path]:
    return sorted(
        p for p in by_year_root.glob("*.report.json")
        if p.name != "combined.report.json"
    )


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path)


def _pick_webapp_sources(full_reports: list[Path], by_year_root: Path) -> dict:
    """Choose on-disk files and merged DQ samples for the webapp embed."""
    dq_path: Path | None = None
    best_score: tuple[int, int, int] | None = None
    for path in full_reports:
        report = _load_json(path)
        if not report:
            continue
        src = report.get("layers", {}).get("source_dq", {})
        rules_in_samples: set[str] = set()
        sample_count = 0
        for bucket in ("warning_samples", "info_samples", "quarantined_samples"):
            for sample in src.get(bucket) or []:
                sample_count += 1
                for issue in sample.get("issues") or []:
                    if issue.get("rule"):
                        rules_in_samples.add(str(issue["rule"]))
        score = (len(rules_in_samples), sample_count, int(report.get("compiled_release_count") or 0))
        if best_score is None or score > best_score:
            best_score = score
            dq_path = path

    merged_dq: dict[str, object] = {}
    reports_by_mtime = sorted(full_reports, key=lambda p: p.stat().st_mtime, reverse=True)
    for bucket in ("quarantined_samples", "warning_samples", "info_samples"):
        lists = []
        for path in reports_by_mtime:
            report = _load_json(path)
            if not report:
                continue
            src = report.get("layers", {}).get("source_dq", {})
            samples = src.get(bucket) or []
            if samples:
                lists.append(samples)
        merged, omitted = merge_diverse_dq_samples(lists, cap=100, per_rule_cap=5)
        merged_dq[bucket] = merged
        merged_dq[f"{bucket}_omitted"] = omitted

    releases_path: Path | None = None
    if by_year_root.exists():
        best: tuple[int, Path] | None = None
        for path in by_year_root.glob("*.json"):
            if path.name.endswith(".report.json"):
                continue
            if path.stat().st_size >= 20_000_000:
                continue
            report = _load_json(path.with_suffix(".report.json"))
            releases = int(report.get("compiled_release_count") or 0) if report else 0
            if best is None or releases > best[0]:
                best = (releases, path)
        if best:
            releases_path = best[1]

    hints: dict[str, object] = {}
    if dq_path:
        hints["dq_samples_from"] = _rel(dq_path)
    if merged_dq:
        hints["merged_dq_samples"] = merged_dq
    if releases_path:
        hints["releases_sample_from"] = _rel(releases_path)
    return hints


def aggregate_dataset_report(
    *,
    full_root: Path = DEFAULT_FULL,
    by_year_root: Path = DEFAULT_BY_YEAR,
    output_path: Path = DEFAULT_OUT,
) -> dict:
    source_reports = discover_source_reports(full_root)
    year_reports = discover_year_reports(by_year_root)

    severity = Counter()
    finding_counts = Counter()
    rule_counter: Counter = Counter()
    issue_group_counter: Counter = Counter()
    rows_seen = rows_committed = rows_quarantined = 0
    shape_issues = 0
    input_bytes_total = 0
    source_releases = 0
    all_source_passed = True

    source_files: list[dict] = []
    dq_payloads: list[dict] = []
    for path in source_reports:
        report = _load_json(path)
        if not report:
            continue

        src = report.get("layers", {}).get("source_dq", {})
        sc = src.get("severity_counts") or {}
        for k, v in sc.items():
            severity[k] += int(v or 0)
        rows_seen += int(src.get("rows_seen") or 0)
        rows_committed += int(src.get("rows_committed") or 0)
        rows_quarantined += int(src.get("rows_quarantined") or 0)
        _merge_rule_counts(rule_counter, src.get("rule_counts"))
        _merge_issue_group_counts(issue_group_counter, src.get("issue_group_counts"))
        shape = report.get("layers", {}).get("shape_preflight", {})
        if not shape.get("passed", True):
            shape_issues += int(shape.get("issue_count") or 0)
        fc = report.get("summary", {}).get("finding_counts") or {}
        for k, v in fc.items():
            finding_counts[k] += int(v or 0)
        if not report.get("summary", {}).get("all_passed", True):
            all_source_passed = False

        input_bytes = int(report.get("input_bytes") or 0)
        input_bytes_total += input_bytes
        releases = int(report.get("compiled_release_count") or 0)
        source_releases += releases

        source_files.append({
            "path": _rel(path.with_suffix("")),
            "report_path": _rel(path),
            "input_file": report.get("input_file"),
            "input_bytes": input_bytes,
            "schema_detected": report.get("schema_detected"),
            "compiled_release_count": releases,
            "all_passed": report.get("summary", {}).get("all_passed", True),
        })

        dq_path = _dq_path_for_report(path)
        dq = _load_json(dq_path)
        if dq:
            dq_payloads.append(dq)

    years: list[dict] = []
    year_releases = 0
    duplicate_ocids = 0
    package_mb_total = 0.0
    all_years_passed = True

    for path in year_reports:
        report = _load_json(path)
        if not report:
            continue
        year = report.get("calendar_year") or path.stem
        releases = int(report.get("compiled_release_count") or 0)
        dup = int(report.get("duplicate_ocids_overwritten") or 0)
        year_releases += releases
        duplicate_ocids += dup

        pkg_path = by_year_root / f"{year}.json"
        package_mb = round(pkg_path.stat().st_size / 1e6, 1) if pkg_path.exists() else 0.0
        package_mb_total += package_mb

        passed = report.get("summary", {}).get("all_passed", True)
        if not passed:
            all_years_passed = False

        years.append({
            "year": year,
            "source_file_count": report.get("source_file_count", 0),
            "compiled_release_count": releases,
            "duplicate_ocids_overwritten": dup,
            "package_mb": package_mb,
            "severity_counts": report.get("layers", {}).get("source_dq", {}).get("severity_counts") or {},
            "all_passed": passed,
            "report_path": _rel(path),
            "package_path": _rel(pkg_path) if pkg_path.exists() else None,
        })

    source_dq = {
        "rows_seen": rows_seen,
        "rows_committed": rows_committed,
        "rows_quarantined": rows_quarantined,
        "severity_counts": dict(severity),
        "rule_counts": _rule_counts_to_list(rule_counter),
        "issue_group_counts": _issue_group_counts_to_list(issue_group_counter),
    }
    shape_layer = {
        "passed": shape_issues == 0,
        "issue_count": shape_issues,
    }
    ocds_layer = {
        "available": False,
        "passed": None,
        "error": "skipped in full-dataset run",
        "validation_error_count": 0,
        "conformance_error_count": 0,
        "additional_checks_count": 0,
    }
    top_findings = build_top_findings(source_dq, shape_layer, ocds_layer)
    summary = build_summary(source_dq, shape_layer, ocds_layer, top_findings)
    summary["finding_counts"] = dict(finding_counts)

    webapp = _pick_webapp_sources(source_reports, by_year_root)

    row_accounting = merge_row_accounting_from_dqs(
        dq_payloads,
        merge_accounting=corpus_merge_accounting(
            {
                "compiled_release_count_sources": source_releases,
                "compiled_release_count": year_releases,
                "duplicate_ocids_overwritten": duplicate_ocids,
            }
        ),
    )

    combined = {
        "report_version": REPORT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "scope": "full_dataset",
        "source_file_count": len(source_files),
        "calendar_year_count": len(years),
        "input_bytes_total": input_bytes_total,
        "compiled_release_count": year_releases,
        "compiled_release_count_sources": source_releases,
        "duplicate_ocids_overwritten": duplicate_ocids,
        "package_mb_total": round(package_mb_total, 1),
        "layers": {
            "source_dq": source_dq,
            "shape_preflight": shape_layer,
            "ocds_validation": ocds_layer,
        },
        "summary": summary,
        "years": years,
        "source_files": source_files,
        "row_accounting": row_accounting,
        "webapp": webapp,
        "artifacts": {
            "combined_report": _rel(output_path),
            "by_year_index": _rel(by_year_root / "by_year_index.json"),
            "by_year_root": _rel(by_year_root),
            "full_root": _rel(full_root),
            "full_dataset_results": _rel(full_root / "full_dataset_results.json"),
        },
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(combined, f, indent=2, ensure_ascii=False)
        f.write("\n")

    return combined


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--full", type=Path, default=DEFAULT_FULL)
    p.add_argument("--by-year", type=Path, default=DEFAULT_BY_YEAR)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = p.parse_args()

    if not args.full.exists():
        print(f"full root not found: {args.full}", file=sys.stderr)
        return 1

    combined = aggregate_dataset_report(
        full_root=args.full,
        by_year_root=args.by_year,
        output_path=args.output,
    )
    print(
        f"Wrote {_rel(args.output)} — "
        f"{combined['source_file_count']} sources, "
        f"{combined['calendar_year_count']} years, "
        f"{combined['compiled_release_count']:,} releases"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
