#!/usr/bin/env python3
"""Build per-year DQ caches from source ``.dq.json`` sidecars.

Writes ``references/transformed/by_year/dq/<year>.json`` for the webapp to
fetch on demand (see ADR-013).

Usage:
    python scripts/build_year_dq_cache.py
    python scripts/build_year_dq_cache.py --years 2004,2021
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _year_dq import write_year_dq_cache  # noqa: E402
from _year_utils import year_from_path  # noqa: E402

DEFAULT_FULL = ROOT / "references" / "transformed" / "full"
DEFAULT_BY_YEAR = ROOT / "references" / "transformed" / "by_year"


def discover_packages(input_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(input_root.rglob("*.json")):
        if path.name.endswith(".dq.json") or path.name.endswith(".report.json"):
            continue
        if path.name == "full_dataset_results.json":
            continue
        out.append(path)
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_FULL)
    p.add_argument("--by-year", type=Path, default=DEFAULT_BY_YEAR)
    p.add_argument("--years", type=str, default=None, help="Comma-separated years (default: all in by_year index)")
    args = p.parse_args()

    if args.years:
        years = [y.strip() for y in args.years.split(",") if y.strip()]
    else:
        index_path = args.by_year / "by_year_index.json"
        if index_path.exists():
            index = json.loads(index_path.read_text(encoding="utf-8"))
            years = [str(y["year"]) for y in index.get("years") or []]
        else:
            years = sorted(
                path.stem
                for path in args.by_year.glob("*.json")
                if not path.name.endswith(".report.json")
                and path.parent.name != "browser"
                and path.parent.name != "dq"
            )

    packages = discover_packages(args.input)
    by_year: dict[str, list[Path]] = {}
    for pkg_path in packages:
        year = year_from_path(pkg_path)
        if year:
            by_year.setdefault(year, []).append(pkg_path)

    if not years:
        print("No years to build.", file=sys.stderr)
        return 1

    built = 0
    skipped = 0
    for year in years:
        paths = by_year.get(year, [])
        if not paths:
            print(f"[skip] {year} — no source packages under {args.input.relative_to(ROOT)}")
            skipped += 1
            continue
        report_path = args.by_year / f"{year}.report.json"
        year_report = None
        if report_path.exists():
            year_report = json.loads(report_path.read_text(encoding="utf-8"))
        out = write_year_dq_cache(
            year,
            paths,
            output_root=args.by_year,
            year_report=year_report,
        )
        if out is None:
            print(f"[skip] {year} — no .dq.json sidecars")
            skipped += 1
            continue
        kb = out.stat().st_size / 1024
        print(f"[ok] {year} -> {out.relative_to(ROOT)} ({kb:.1f} KB)")
        built += 1

    print(f"\nBuilt {built} year DQ cache(s), skipped {skipped}.")
    return 0 if built else 1


if __name__ == "__main__":
    sys.exit(main())
