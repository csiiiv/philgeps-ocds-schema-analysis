"""Build per-calendar-year DQ caches for the webapp (see ADR-013)."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from _data_quality import _compact_sample_payload, merge_diverse_dq_samples
from _row_accounting import merge_row_accounting_from_dqs

ROOT = Path(__file__).resolve().parents[1]
MAX_EMBEDDED_DQ_SAMPLES = 100


def _dq_path_for_package(pkg_path: Path) -> Path:
    return pkg_path.with_suffix(".dq.json")


def _load_dq(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _merge_rule_counts(target: Counter, rules: list[dict]) -> None:
    for entry in rules or []:
        key = (entry.get("rule"), entry.get("severity"))
        target[key] += int(entry.get("count") or 0)


def _rule_counts_to_list(counter: Counter) -> list[dict]:
    return [
        {"rule": rule, "severity": severity, "count": count}
        for (rule, severity), count in counter.most_common()
    ]


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


def _embed_samples(samples: list[dict] | None, *, cap: int = MAX_EMBEDDED_DQ_SAMPLES) -> tuple[list[dict], int]:
    raw = list(samples or [])
    omitted = max(0, len(raw) - cap)
    return [_compact_sample_payload(s) for s in raw[:cap]], omitted


def _sample_lists_from_dq_files(dq_files: Iterable[Path], bucket: str) -> list[list[dict]]:
    lists: list[list[dict]] = []
    for path in dq_files:
        dq = _load_dq(path)
        if not dq:
            continue
        samples = dq.get(bucket) or []
        if samples:
            lists.append(samples)
    return lists


def build_year_dq_payload(
    year: str,
    package_paths: list[Path],
    *,
    year_report: dict | None = None,
) -> dict | None:
    """Merge per-source ``.dq.json`` files into one year-scoped bundle for the webapp."""
    dq_files = [_dq_path_for_package(p) for p in package_paths]
    dq_files = [p for p in dq_files if p.exists()]
    if not dq_files:
        return None

    severity = Counter()
    rule_counter: Counter = Counter()
    issue_group_counter: Counter = Counter()
    rows_seen = rows_committed = rows_quarantined = 0
    source_meta: list[dict] = []
    header: list[str] = []
    schema_detected = "mixed"
    mapped_column_count = 0
    unmapped_columns: list[str] = []
    compiled_release_count = 0
    input_bytes = 0

    dq_payloads: list[dict] = []
    for pkg_path in package_paths:
        dq_path = _dq_path_for_package(pkg_path)
        dq = _load_dq(dq_path)
        if not dq:
            continue
        dq_payloads.append(dq)
        sc = dq.get("severity_counts") or {}
        for k, v in sc.items():
            severity[k] += int(v or 0)
        rows_seen += int(dq.get("rows_seen") or 0)
        rows_committed += int(dq.get("rows_committed") or 0)
        rows_quarantined += int(dq.get("rows_quarantined") or 0)
        _merge_rule_counts(rule_counter, dq.get("rule_counts"))
        _merge_issue_group_counts(issue_group_counter, dq.get("issue_group_counts"))
        compiled_release_count += int(dq.get("compiled_release_count") or 0)
        input_bytes += int(dq.get("input_bytes") or 0)
        if not header and dq.get("header"):
            header = list(dq.get("header") or [])
        if dq.get("schema_detected"):
            schema_detected = str(dq["schema_detected"])
        if dq.get("mapped_column_count"):
            mapped_column_count = max(mapped_column_count, int(dq["mapped_column_count"]))
        if dq.get("unmapped_columns"):
            unmapped_columns = list(dq.get("unmapped_columns") or [])
        source_meta.append({
            "path": str(pkg_path.relative_to(ROOT)),
            "dq_path": str(dq_path.relative_to(ROOT)),
            "input_file": dq.get("input_file"),
            "compiled_release_count": dq.get("compiled_release_count"),
        })

    if year_report:
        yr_src = year_report.get("layers", {}).get("source_dq") or {}
        if yr_src.get("severity_counts"):
            severity = Counter(yr_src["severity_counts"])
        if yr_src.get("rule_counts"):
            rule_counter = Counter()
            _merge_rule_counts(rule_counter, yr_src.get("rule_counts"))
        rows_seen = int(yr_src.get("rows_seen") or rows_seen)
        rows_committed = int(yr_src.get("rows_committed") or rows_committed)
        rows_quarantined = int(yr_src.get("rows_quarantined") or rows_quarantined)
        compiled_release_count = int(year_report.get("compiled_release_count") or compiled_release_count)

    quarantined, q_omitted = _embed_samples(
        merge_diverse_dq_samples(_sample_lists_from_dq_files(dq_files, "quarantined_samples"), cap=50, per_rule_cap=5)[0]
    )
    warnings, w_omitted = _embed_samples(
        merge_diverse_dq_samples(_sample_lists_from_dq_files(dq_files, "warning_samples"), cap=100, per_rule_cap=5)[0]
    )
    infos, i_omitted = _embed_samples(
        merge_diverse_dq_samples(_sample_lists_from_dq_files(dq_files, "info_samples"), cap=100, per_rule_cap=5)[0]
    )

    display_id_collisions: list[dict] = []
    for dq_path in dq_files:
        dq = _load_dq(dq_path)
        if dq:
            display_id_collisions.extend(dq.get("display_id_collisions") or [])

    input_label = (
        source_meta[0]["input_file"]
        if len(source_meta) == 1
        else f"Calendar year {year} ({len(source_meta)} source exports)"
    )

    merge_accounting = None
    if year_report:
        sources_releases = sum(int(d.get("compiled_release_count") or 0) for d in dq_payloads)
        merge_accounting = {
            "releases_before_dedup": sources_releases,
            "releases_after_dedup": int(
                year_report.get("compiled_release_count") or compiled_release_count
            ),
            "duplicate_ocids_overwritten": int(
                year_report.get("duplicate_ocids_overwritten") or 0
            ),
            "scope": "year",
        }
    row_accounting = merge_row_accounting_from_dqs(
        dq_payloads,
        merge_accounting=merge_accounting,
    )

    return {
        "scope": "calendar_year",
        "calendar_year": year,
        "source_file_count": len(source_meta),
        "source_files": source_meta,
        "input_file": input_label,
        "input_bytes": input_bytes,
        "schema_detected": schema_detected,
        "mapped_column_count": mapped_column_count,
        "unmapped_columns": unmapped_columns,
        "header": header,
        "rows_seen": rows_seen,
        "rows_committed": rows_committed,
        "rows_quarantined": rows_quarantined,
        "severity_counts": dict(severity),
        "rule_counts": _rule_counts_to_list(rule_counter),
        "issue_group_counts": _issue_group_counts_to_list(issue_group_counter),
        "quarantined_samples": quarantined,
        "quarantined_samples_omitted": q_omitted,
        "warning_samples": warnings,
        "warning_samples_omitted": w_omitted,
        "info_samples": infos,
        "info_samples_omitted": i_omitted,
        "display_id_collisions": display_id_collisions[:20],
        "compiled_release_count": compiled_release_count,
        "row_accounting": row_accounting,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def write_year_dq_cache(
    year: str,
    package_paths: list[Path],
    *,
    output_root: Path,
    year_report: dict | None = None,
) -> Path | None:
    payload = build_year_dq_payload(year, package_paths, year_report=year_report)
    if not payload:
        return None
    out_dir = output_root / "dq"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{year}.json"
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return out_path
