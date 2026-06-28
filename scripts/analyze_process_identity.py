#!/usr/bin/env python3
"""Sample PhilGEPS exports and compare process identity fields across schemas.

Helps choose grouping keys for process-level OCDS releases:
  bid_reference_no vs solicitation_no vs award_reference_no

Usage:
    python scripts/analyze_process_identity.py
    python scripts/analyze_process_identity.py --sample 50000
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _data_quality import is_null  # noqa: E402
from transform_to_ocds import (  # noqa: E402
    _canonicalize,
    detect_schema,
)

try:
    import yaml
except ImportError:
    yaml = None

SCHEMA_MAPPINGS = ROOT / "config" / "schema_mappings.yaml"
RAW = ROOT.parent / "raw"

_NUMERIC = re.compile(r"^\d+$")


def _load_mappings() -> dict:
    if yaml is None:
        raise RuntimeError("PyYAML required")
    return yaml.safe_load(SCHEMA_MAPPINGS.read_text(encoding="utf-8"))


def _valid(value: object) -> str | None:
    if is_null(value):
        return None
    text = str(value).strip()
    if text in ("", "0", "NULL"):
        return None
    return text


def _is_numeric_ref(text: str) -> bool:
    return bool(_NUMERIC.match(text))


def _reservoir_sample(path: Path, n: int, *, encoding: str = "utf-8-sig") -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding=encoding, newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=1):
            if len(rows) < n:
                rows.append(row)
            else:
                j = random.randint(1, i)
                if j <= n:
                    rows[j - 1] = row
    return rows


def _analyze_canonical_rows(
    canonical_rows: list[dict],
    *,
    schema_key: str,
    label: str,
) -> dict:
    n = len(canonical_rows)
    bid_present = sol_present = award_present = 0
    bid_numeric = bid_alpha = 0
    both_present = bid_eq_sol = 0

    by_bid_awards: dict[str, set[str]] = defaultdict(set)
    by_sol_awards: dict[str, set[str]] = defaultdict(set)
    by_bid_sol: dict[str, set[str]] = defaultdict(set)

    examples_multi_bid: list[dict] = []
    examples_multi_sol: list[dict] = []
    examples_bid_sol_split: list[dict] = []

    for row in canonical_rows:
        bid = _valid(row.get("bid_reference_no"))
        sol = _valid(row.get("solicitation_no"))
        award = _valid(row.get("award_reference_no"))

        if bid:
            bid_present += 1
            if _is_numeric_ref(bid):
                bid_numeric += 1
            else:
                bid_alpha += 1
        if sol:
            sol_present += 1
        if award:
            award_present += 1
        if bid and sol:
            both_present += 1
            if bid == sol:
                bid_eq_sol += 1
            by_bid_sol[bid].add(sol)

        if bid and award:
            by_bid_awards[bid].add(award)
        if sol and award:
            by_sol_awards[sol].add(award)

    multi_bid = {k: v for k, v in by_bid_awards.items() if len(v) > 1}
    multi_sol = {k: v for k, v in by_sol_awards.items() if len(v) > 1}
    split_bid_sol = {k: v for k, v in by_bid_sol.items() if len(v) > 1}

    for bid, awards in sorted(multi_bid.items(), key=lambda kv: -len(kv[1]))[:5]:
        sols = sorted(by_bid_sol.get(bid, []))
        examples_multi_bid.append({
            "bid_reference_no": bid,
            "solicitation_no": sols[:3],
            "award_count": len(awards),
            "award_sample": sorted(awards)[:6],
        })

    for sol, awards in sorted(multi_sol.items(), key=lambda kv: -len(kv[1]))[:5]:
        examples_multi_sol.append({
            "solicitation_no": sol,
            "award_count": len(awards),
            "award_sample": sorted(awards)[:6],
        })

    for bid, sols in sorted(split_bid_sol.items(), key=lambda kv: -len(kv[1]))[:5]:
        examples_bid_sol_split.append({
            "bid_reference_no": bid,
            "solicitation_nos": sorted(sols)[:5],
            "solicitation_count": len(sols),
        })

    return {
        "label": label,
        "schema_key": schema_key,
        "rows_sampled": n,
        "bid_reference_no": {
            "present_pct": round(100 * bid_present / n, 1) if n else 0,
            "numeric_only_pct": round(100 * bid_numeric / max(bid_present, 1), 1),
            "alpha_numeric_pct": round(100 * bid_alpha / max(bid_present, 1), 1),
        },
        "solicitation_no": {
            "present_pct": round(100 * sol_present / n, 1) if n else 0,
        },
        "award_reference_no": {
            "present_pct": round(100 * award_present / n, 1) if n else 0,
        },
        "bid_and_solicitation": {
            "both_present_pct": round(100 * both_present / n, 1) if n else 0,
            "equal_when_both_pct": round(100 * bid_eq_sol / max(both_present, 1), 1),
            "one_bid_many_solicitations": len(split_bid_sol),
        },
        "multi_award_processes": {
            "by_bid_reference_no": len(multi_bid),
            "by_solicitation_no": len(multi_sol),
            "max_awards_per_bid": max((len(v) for v in multi_bid.values()), default=0),
            "max_awards_per_solicitation": max((len(v) for v in multi_sol.values()), default=0),
        },
        "examples": {
            "multi_award_by_bid": examples_multi_bid,
            "multi_award_by_solicitation": examples_multi_sol,
            "one_bid_many_solicitations": examples_bid_sol_split,
        },
    }


def _analyze_file(path: Path, column_map: dict, schema_key: str, sample_n: int) -> dict:
    raw_rows = _reservoir_sample(path, sample_n)
    canonical = [_canonicalize(r, column_map) for r in raw_rows if _valid(r.get("Award No.") or r.get("Award Reference No.") or r.get("Award No") or "x")]
    # Keep awarded rows only for identity analysis
    awarded = [r for r in [_canonicalize(r, column_map) for r in raw_rows] if _valid(r.get("award_reference_no"))]
    return _analyze_canonical_rows(awarded, schema_key=schema_key, label=str(path.name))


def _find_bcda(rows: list[dict]) -> dict | None:
    group: list[dict] = []
    for row in rows:
        sol = _valid(row.get("solicitation_no"))
        bid = _valid(row.get("bid_reference_no"))
        if sol == "BCDA-2004-0222" or bid == "BCDA-2004-0222":
            group.append({
                "bid_reference_no": bid,
                "solicitation_no": sol,
                "award_reference_no": _valid(row.get("award_reference_no")),
                "line_item_no": _valid(row.get("line_item_no")),
                "procuring_entity": _valid(row.get("procuring_entity")),
            })
    if not group:
        return None
    return {
        "match": "BCDA-2004-0222",
        "rows": len(group),
        "distinct_bids": sorted({r["bid_reference_no"] for r in group if r["bid_reference_no"]}),
        "distinct_solicitations": sorted({r["solicitation_no"] for r in group if r["solicitation_no"]}),
        "distinct_awards": sorted({r["award_reference_no"] for r in group if r["award_reference_no"]}),
        "sample_rows": group[:4],
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sample", type=int, default=25_000, help="Rows to reservoir-sample per file")
    p.add_argument("--json", type=Path, default=ROOT / "scratch" / "out" / "process_identity_analysis.json")
    args = p.parse_args()

    mappings = _load_mappings()
    random.seed(42)

    sources: list[tuple[str, Path]] = [
        ("S1-2004", ROOT / "references" / "transformed" / "full" / "2000-2012" / "Bid Notice and Award Details 2004.sample.csv"),
        ("S1-2002", ROOT / "scratch" / "out" / "S1-2002.sample.csv"),
        ("S2-2013Q1", ROOT / "scratch" / "out" / "S2-2013Q1.sample.csv"),
        ("S2-2020Q4", ROOT / "scratch" / "out" / "S2-2020Q4.sample.csv"),
        ("S3-2021", RAW / "PHILGEPS -- 2021-2025 (CSV)" / "2021.csv"),
        ("S3-2024", RAW / "PHILGEPS -- 2021-2025 (CSV)" / "2024.csv"),
        ("S5-V2", RAW / "Misc" / "PHILGEPS -- 2021 - 2025 (CSV) V2" / "2024-10 -- 2024-12.csv"),
    ]

    results: list[dict] = []
    bcda_hits: list[dict] = []

    for label, path in sources:
        if not path.exists():
            print(f"[skip] missing {path}", file=sys.stderr)
            continue
        print(f"Analyzing {label} ({path.name})…", file=sys.stderr)
        if path.suffix.lower() == ".csv":
            header = path.open("r", encoding="utf-8-sig", newline="").readline()
            cols = next(csv.reader([header]))
            schema_key = detect_schema(cols)
        else:
            schema_key = "schema_1"
        column_map = mappings.get(schema_key) or {}
        raw_rows = _reservoir_sample(path, args.sample)
        canonical_awarded = [
            _canonicalize(r, column_map)
            for r in raw_rows
            if _valid(_canonicalize(r, column_map).get("award_reference_no"))
        ]
        stats = _analyze_canonical_rows(canonical_awarded, schema_key=schema_key, label=label)
        stats["source"] = str(path.relative_to(ROOT.parent)) if path.is_relative_to(ROOT.parent) else str(path)
        results.append(stats)
        hit = _find_bcda(canonical_awarded)
        if hit:
            hit["source"] = label
            bcda_hits.append(hit)

    # Full-file BCDA from transformed canonical sample if present
    bcda_path = ROOT / "references" / "transformed" / "full" / "2000-2012" / "Bid Notice and Award Details 2004.sample.csv"
    if bcda_path.exists():
        column_map = mappings["schema_1"]
        all_rows = list(csv.DictReader(bcda_path.open("r", encoding="utf-8-sig", newline="")))
        canon = [_canonicalize(r, column_map) for r in all_rows]
        hit = _find_bcda(canon)
        if hit:
            hit["source"] = "S1-2004-full-sample"
            bcda_hits.append(hit)

    payload = {
        "sample_rows_per_source": args.sample,
        "results": results,
        "bcda_case": bcda_hits,
        "recommendations": _recommendations(results, bcda_hits),
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(payload["recommendations"], indent=2))
    print(f"\nWrote {args.json.relative_to(ROOT)}", file=sys.stderr)
    return 0


def _recommendations(results: list[dict], bcda_hits: list[dict]) -> dict:
    by_schema: dict[str, list[dict]] = defaultdict(list)
    for r in results:
        by_schema[r["schema_key"]].append(r)

    schema_notes: dict[str, str] = {}
    for key, rows in by_schema.items():
        bid_num = sum(x["bid_reference_no"]["numeric_only_pct"] for x in rows) / len(rows)
        bid_eq = sum(x["bid_and_solicitation"]["equal_when_both_pct"] for x in rows) / len(rows)
        multi_bid = sum(x["multi_award_processes"]["by_bid_reference_no"] for x in rows)
        multi_sol = sum(x["multi_award_processes"]["by_solicitation_no"] for x in rows)

        if key in ("schema_1", "schema_2"):
            schema_notes[key] = (
                f"Bid ref is numeric-only ~{bid_num:.0f}% of the time (internal Reference ID). "
                f"Solicitation No. is the public process id (e.g. BCDA-2004-0222). "
                f"Prefer solicitation_no for OCID/display when bid is numeric; keep bid for grouping when numeric is stable. "
                f"Multi-award: {multi_bid} by bid vs {multi_sol} by solicitation in sample."
            )
        elif key == "schema_3":
            schema_notes[key] = (
                f"Bid Reference No. often placeholder `0` in samples; award ref is primary row id. "
                f"When bid is valid, it matches solicitation ~{bid_eq:.0f}% when both present. "
                f"Group by bid when valid, else award. Multi-award by bid: {multi_bid}."
            )
        else:
            schema_notes[key] = (
                f"S4/S5: Bid Reference No. is the process anchor when not `0`. "
                f"bid==solicitation ~{bid_eq:.0f}% when both present. "
                f"Prefer bid_reference_no; fall back to solicitation_no then award."
            )

    return {
        "grouping_priority": [
            "1. Use bid_reference_no when present and not placeholder `0` (all schemas).",
            "2. S1/S2 only: when bid_reference_no is numeric-only, also require solicitation_no for OCID/display id (public-facing ref).",
            "3. Group by solicitation_no when bid is missing/`0` but solicitation is present.",
            "4. Fall back to award_reference_no (legacy S3 rows with bid `0`).",
        ],
        "ocid_priority": [
            "Prefer human-readable process id: solicitation_no (S1/S2) or bid_reference_no (S3+).",
            "Do not use numeric-only Reference ID as public OCID slug when solicitation_no exists.",
        ],
        "by_schema": schema_notes,
        "bcda_verification": bcda_hits,
        "caveat": (
            "by_year/ merge must be re-run after compiler changes; stale year packages "
            "still show award-level releases in the Release browser."
        ),
    }


if __name__ == "__main__":
    sys.exit(main())
