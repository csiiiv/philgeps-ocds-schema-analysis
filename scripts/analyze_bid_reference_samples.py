#!/usr/bin/env python3
"""Sample bid_reference_no values across PhilGEPS schemas (zeros, placeholders, examples).

Usage:
    python scripts/analyze_bid_reference_samples.py
    python scripts/analyze_bid_reference_samples.py --sample 30000
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _data_quality import is_null  # noqa: E402
from transform_to_ocds import _canonicalize, detect_schema  # noqa: E402

try:
    import yaml
except ImportError:
    yaml = None

RAW = ROOT.parent / "raw"
SCHEMA_MAPPINGS = ROOT / "config" / "schema_mappings.yaml"
_NUMERIC = re.compile(r"^\d+$")

CANONICAL_HEADERS = {"bid_reference_no", "award_reference_no", "procuring_entity"}


def _load_mappings() -> dict:
    return yaml.safe_load(SCHEMA_MAPPINGS.read_text(encoding="utf-8"))


def _classify_bid(raw: object) -> str:
    if is_null(raw):
        return "null_or_empty"
    text = str(raw).strip()
    if text == "":
        return "null_or_empty"
    if text == "0":
        return "zero"
    if text.upper() == "NULL":
        return "null_literal"
    if _NUMERIC.match(text):
        return "numeric"
    return "alpha_or_mixed"


def _reservoir(path: Path, n: int) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader, start=1):
            if len(rows) < n:
                rows.append(row)
            else:
                j = random.randint(1, i)
                if j <= n:
                    rows[j - 1] = row
    return rows


def _to_canonical(rows: list[dict], path: Path, mappings: dict) -> tuple[str, list[dict]]:
    if not rows:
        return "unknown", []
    header = list(rows[0].keys())
    if CANONICAL_HEADERS.issubset(set(header)):
        return rows[0].get("source_schema") or "canonical_export", rows
    schema_key = detect_schema(header)
    column_map = mappings.get(schema_key) or {}
    return schema_key, [_canonicalize(r, column_map) for r in rows]


def _summarize_bids(canonical_rows: list[dict], *, awarded_only: bool) -> dict:
    rows = canonical_rows
    if awarded_only:
        rows = [r for r in rows if _classify_bid(r.get("award_reference_no")) not in ("null_or_empty", "zero", "null_literal")
                and not is_null(r.get("award_reference_no")) and str(r.get("award_reference_no", "")).strip() not in ("", "0")]

    n = len(rows)
    if n == 0:
        return {"rows": 0}

    classes = Counter(_classify_bid(r.get("bid_reference_no")) for r in rows)
    valid_values = [
        str(r["bid_reference_no"]).strip()
        for r in rows
        if _classify_bid(r.get("bid_reference_no")) not in ("null_or_empty", "zero", "null_literal")
    ]
    value_counts = Counter(valid_values)

    def pct(key: str) -> float:
        return round(100 * classes.get(key, 0) / n, 2)

    # Diverse examples: top frequent + random rare
    top_examples = [{"value": v, "count": c} for v, c in value_counts.most_common(12)]
    rare = [v for v, c in value_counts.items() if c == 1][:8]

    return {
        "rows": n,
        "distribution": {
            "valid_numeric": {"count": classes.get("numeric", 0), "pct": pct("numeric")},
            "valid_alpha_or_mixed": {"count": classes.get("alpha_or_mixed", 0), "pct": pct("alpha_or_mixed")},
            "zero": {"count": classes.get("zero", 0), "pct": pct("zero")},
            "null_or_empty": {"count": classes.get("null_or_empty", 0), "pct": pct("null_or_empty")},
            "null_literal": {"count": classes.get("null_literal", 0), "pct": pct("null_literal")},
        },
        "valid_pct": round(100 * len(valid_values) / n, 2),
        "top_values": top_examples,
        "rare_value_samples": rare,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sample", type=int, default=20_000)
    p.add_argument("--json", type=Path, default=ROOT / "scratch" / "out" / "bid_reference_samples.json")
    args = p.parse_args()

    mappings = _load_mappings()
    random.seed(42)

    sources: list[tuple[str, Path, str]] = [
        ("S1-2004", ROOT / "references/transformed/full/2000-2012/Bid Notice and Award Details 2004.sample.csv", "schema_1"),
        ("S1-2002", ROOT / "scratch/out/S1-2002.sample.csv", "schema_1"),
        ("S2-2013Q1", ROOT / "scratch/out/S2-2013Q1.sample.csv", "schema_2"),
        ("S2-2020Q4", ROOT / "scratch/out/S2-2020Q4.sample.csv", "schema_2"),
        ("S3-2021", RAW / "PHILGEPS -- 2021-2025 (CSV)/2021.csv", "schema_3"),
        ("S3-2024", RAW / "PHILGEPS -- 2021-2025 (CSV)/2024.csv", "schema_3"),
        ("S3-2025", RAW / "PHILGEPS -- 2021-2025 (CSV)/2025.csv", "schema_3"),
        ("S5-V2-Q4", RAW / "Misc/PHILGEPS -- 2021 - 2025 (CSV) V2/2024-10 -- 2024-12.csv", "schema_4"),
    ]

    results: list[dict] = []
    for label, path, expected_schema in sources:
        if not path.exists():
            print(f"[skip] {path}", file=sys.stderr)
            continue
        print(f"Sampling {label}…", file=sys.stderr)
        raw_rows = _reservoir(path, args.sample)
        schema_key, canonical = _to_canonical(raw_rows, path, mappings)
        if schema_key == "canonical_export":
            schema_key = expected_schema

        results.append({
            "label": label,
            "schema_key": schema_key,
            "expected_schema": expected_schema,
            "source": str(path),
            "all_rows": _summarize_bids(canonical, awarded_only=False),
            "awarded_rows": _summarize_bids(canonical, awarded_only=True),
        })

    payload = {
        "sample_rows_per_source": args.sample,
        "results": results,
        "notes": {
            "zero": "Literal `0` — common in S3/S4 exports where Bid Reference No. was decommissioned.",
            "valid_numeric": "S1/S2 Reference ID and S3+ system bid ids (e.g. 7618302).",
            "valid_alpha_or_mixed": "Human-readable bid refs (e.g. BGHMCPB-2025-07) when present.",
        },
    }

    args.json.parent.mkdir(parents=True, exist_ok=True)
    args.json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Console summary table
    print("\n| Source | Schema | Awarded rows | bid valid % | zero % | null % |")
    print("|--------|--------|--------------|-------------|--------|--------|")
    for r in results:
        a = r["awarded_rows"]
        d = a.get("distribution", {})
        print(
            f"| {r['label']} | {r['schema_key']} | {a.get('rows', 0):,} | "
            f"{a.get('valid_pct', 0)}% | {d.get('zero', {}).get('pct', 0)}% | "
            f"{d.get('null_or_empty', {}).get('pct', 0)}% |"
        )

    print(f"\nWrote {args.json.relative_to(ROOT)}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
