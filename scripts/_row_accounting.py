"""Row → release accounting for DQ reports and the webapp."""

from __future__ import annotations

from typing import Any


def _rule_count(rule_counts: list[dict] | None, rule: str, *, severity: str | None = None) -> int:
    total = 0
    for entry in rule_counts or []:
        if entry.get("rule") != rule:
            continue
        if severity is not None and entry.get("severity") != severity:
            continue
        total += int(entry.get("count") or 0)
    return total


def _sum_compile_accounting(accountings: list[dict]) -> dict:
    keys = (
        "rows_excluded_no_award",
        "rows_excluded_no_process_key",
        "rows_grouped",
        "process_group_count",
        "releases_compiled",
    )
    out = {k: 0 for k in keys}
    for acc in accountings:
        for k in keys:
            out[k] += int(acc.get(k) or 0)
    out["rows_merged_into_groups"] = max(0, out["rows_grouped"] - out["process_group_count"])
    return out


def compile_accounting_from_dq(dq: dict) -> dict | None:
    """Read per-source compile counters from a ``.dq.json`` payload."""
    raw = dq.get("compile_accounting")
    if isinstance(raw, dict) and raw.get("process_group_count") is not None:
        acc = dict(raw)
        acc["releases_compiled"] = int(
            acc.get("releases_compiled") or dq.get("compiled_release_count") or 0
        )
        acc["rows_merged_into_groups"] = max(
            0,
            int(acc.get("rows_grouped") or 0) - int(acc.get("process_group_count") or 0),
        )
        return acc

    # Fallback for transforms before compile_accounting existed.
    unawarded = _rule_count(dq.get("rule_counts"), "unawarded_tender", severity="info")
    releases = int(dq.get("compiled_release_count") or 0)
    rows_committed = int(dq.get("rows_committed") or 0)
    rows_quarantined = int(dq.get("rows_quarantined") or 0)
    rows_seen = int(dq.get("rows_seen") or 0)
    excluded_est = min(unawarded, max(0, rows_committed))
    grouped_est = max(0, rows_committed - excluded_est)
    return {
        "rows_excluded_no_award": excluded_est,
        "rows_excluded_no_process_key": 0,
        "rows_grouped": grouped_est,
        "process_group_count": releases,
        "rows_merged_into_groups": max(0, grouped_est - releases),
        "releases_compiled": releases,
        "estimated": True,
        "rows_seen": rows_seen,
        "rows_quarantined": rows_quarantined,
    }


def build_row_accounting(
    *,
    rows_seen: int,
    rows_committed: int,
    rows_quarantined: int,
    rule_counts: list[dict] | None = None,
    compile_accounting: dict | None = None,
    merge_accounting: dict | None = None,
    estimated: bool = False,
) -> dict:
    """Build a structured row→release breakdown for reports / webapp."""
    compile_acc = compile_accounting or {}
    excluded_no_award = int(compile_acc.get("rows_excluded_no_award") or 0)
    excluded_no_key = int(compile_acc.get("rows_excluded_no_process_key") or 0)
    rows_grouped = int(compile_acc.get("rows_grouped") or 0)
    process_groups = int(compile_acc.get("process_group_count") or 0)
    rows_merged = int(
        compile_acc.get("rows_merged_into_groups")
        or max(0, rows_grouped - process_groups)
    )
    releases_compiled = int(compile_acc.get("releases_compiled") or 0)

    if not compile_acc and rule_counts is not None:
        estimated = True
        unawarded = _rule_count(rule_counts, "unawarded_tender", severity="info")
        excluded_no_award = min(unawarded, max(0, rows_committed))
        rows_grouped = max(0, rows_committed - excluded_no_award)
        process_groups = releases_compiled
        rows_merged = max(0, rows_grouped - process_groups)

    breakdown: list[dict[str, Any]] = [
        {
            "id": "rows_seen",
            "label": "Raw rows read",
            "count": rows_seen,
            "detail": "One PhilGEPS export row after header mapping",
        },
        {
            "id": "quarantined",
            "label": "Quarantined (DQ errors)",
            "count": rows_quarantined,
            "detail": "Fatal validation — excluded from compilation",
        },
        {
            "id": "excluded_no_award",
            "label": "Excluded — no award reference",
            "count": excluded_no_award,
            "detail": "Closed / un-awarded tenders (no OCDS release emitted)",
        },
        {
            "id": "excluded_no_process_key",
            "label": "Excluded — no process identity",
            "count": excluded_no_key,
            "detail": "Passed DQ but missing bid / solicitation / award grouping key",
        },
        {
            "id": "rows_grouped",
            "label": "Rows grouped into processes",
            "count": rows_grouped,
            "detail": "Awarded rows assigned to a contracting-process group key",
        },
        {
            "id": "rows_merged",
            "label": "Rows merged (multi-row processes)",
            "count": rows_merged,
            "detail": "Line items / awards collapsed into the same release",
        },
        {
            "id": "releases_compiled",
            "label": "OCDS releases compiled",
            "count": releases_compiled or process_groups,
            "detail": "One release per process group in source transform output",
        },
    ]

    if merge_accounting:
        before = int(merge_accounting.get("releases_before_dedup") or 0)
        after = int(merge_accounting.get("releases_after_dedup") or 0)
        dup = int(merge_accounting.get("duplicate_ocids_overwritten") or 0)
        scope = merge_accounting.get("scope") or "year"
        if scope == "overall":
            before_label = "Releases from all sources (pre-merge)"
            dedup_label = "OCID dedup (year merges)"
            after_label = "Releases in merged dataset"
            before_detail = "Sum of per-source transform outputs before calendar-year merge"
            dedup_detail = "Duplicate ocid across quarterly exports merged per calendar year"
            after_detail = "Final count across all by_year/<year>.json packages"
        else:
            before_label = "Releases before year OCID dedup"
            dedup_label = "OCID dedup (year merge)"
            after_label = "Releases in merged year package"
            before_detail = "Sum of per-source packages contributing to this calendar year"
            dedup_detail = "Duplicate ocid across quarterly exports in the same calendar year"
            after_detail = "Final count in by_year/<year>.json"
        breakdown.extend([
            {
                "id": "releases_before_dedup",
                "label": before_label,
                "count": before,
                "detail": before_detail,
            },
            {
                "id": "ocid_dedup",
                "label": dedup_label,
                "count": dup,
                "detail": dedup_detail,
            },
            {
                "id": "releases_final",
                "label": after_label,
                "count": after,
                "detail": after_detail,
            },
        ])

    return {
        "rows_seen": rows_seen,
        "rows_committed": rows_committed,
        "rows_quarantined": rows_quarantined,
        "compile_accounting": {
            "rows_excluded_no_award": excluded_no_award,
            "rows_excluded_no_process_key": excluded_no_key,
            "rows_grouped": rows_grouped,
            "process_group_count": process_groups,
            "rows_merged_into_groups": rows_merged,
            "releases_compiled": releases_compiled or process_groups,
        },
        "merge_accounting": merge_accounting,
        "breakdown": breakdown,
        "estimated": estimated,
    }


def build_row_accounting_from_dq(dq: dict, *, merge_accounting: dict | None = None) -> dict:
    compile_raw = compile_accounting_from_dq(dq)
    estimated = bool(compile_raw.pop("estimated", False)) if compile_raw else False
    return build_row_accounting(
        rows_seen=int(dq.get("rows_seen") or 0),
        rows_committed=int(dq.get("rows_committed") or 0),
        rows_quarantined=int(dq.get("rows_quarantined") or 0),
        rule_counts=dq.get("rule_counts"),
        compile_accounting=compile_raw,
        merge_accounting=merge_accounting,
        estimated=estimated,
    )


def merge_row_accounting_from_dqs(
    dq_payloads: list[dict],
    *,
    merge_accounting: dict | None = None,
) -> dict:
    if not dq_payloads:
        return build_row_accounting(
            rows_seen=0,
            rows_committed=0,
            rows_quarantined=0,
            merge_accounting=merge_accounting,
        )

    rows_seen = rows_committed = rows_quarantined = 0
    compile_parts: list[dict] = []
    any_estimated = False
    for dq in dq_payloads:
        rows_seen += int(dq.get("rows_seen") or 0)
        rows_committed += int(dq.get("rows_committed") or 0)
        rows_quarantined += int(dq.get("rows_quarantined") or 0)
        part = compile_accounting_from_dq(dq)
        if part:
            if part.pop("estimated", False):
                any_estimated = True
            compile_parts.append(part)

    compile_merged = _sum_compile_accounting(compile_parts) if compile_parts else None
    return build_row_accounting(
        rows_seen=rows_seen,
        rows_committed=rows_committed,
        rows_quarantined=rows_quarantined,
        compile_accounting=compile_merged,
        merge_accounting=merge_accounting,
        estimated=any_estimated,
    )


def corpus_merge_accounting(combined: dict) -> dict:
    return {
        "releases_before_dedup": int(combined.get("compiled_release_count_sources") or 0),
        "releases_after_dedup": int(combined.get("compiled_release_count") or 0),
        "duplicate_ocids_overwritten": int(combined.get("duplicate_ocids_overwritten") or 0),
        "scope": "overall",
    }
