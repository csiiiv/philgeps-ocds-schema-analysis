#!/usr/bin/env python3
"""Build per-year Release browser caches from ``by_year/<year>.json`` packages.

Writes ``references/transformed/by_year/browser/<year>.json`` for the webapp to
fetch on demand (see app/vite.config.ts).

Usage:
    python scripts/build_year_browser_cache.py
    python scripts/build_year_browser_cache.py --years 2004,2021,2023
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _release_browser import refresh_browser_cache_from_package  # noqa: E402

DEFAULT_BY_YEAR = ROOT / "references" / "transformed" / "by_year"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_BY_YEAR)
    p.add_argument("--years", type=str, default=None, help="Comma-separated years (default: all packages)")
    p.add_argument("--max-package-mb", type=float, default=2500)
    args = p.parse_args()

    if args.years:
        years = [y.strip() for y in args.years.split(",") if y.strip()]
    else:
        years = sorted(
            path.stem
            for path in args.input.glob("*.json")
            if path.name not in ("by_year_index.json",)
            and not path.name.endswith(".report.json")
            and path.parent.name != "browser"
        )

    if not years:
        print("No year packages found.", file=sys.stderr)
        return 1

    built = 0
    skipped = 0
    for year in years:
        pkg_path = args.input / f"{year}.json"
        if not pkg_path.exists():
            print(f"[skip] missing {pkg_path.relative_to(ROOT)}")
            skipped += 1
            continue
        out = refresh_browser_cache_from_package(
            pkg_path,
            year=year,
            output_root=args.input,
            max_package_mb=args.max_package_mb,
        )
        if out is None:
            print(f"[skip] {year} — unreadable or over {args.max_package_mb} MB")
            skipped += 1
            continue
        mb = out.stat().st_size / 1e6
        try:
            rel_path = out.relative_to(ROOT)
        except ValueError:
            rel_path = out  # Fallback to absolute path if not relative to ROOT
        print(f"[ok] {year} -> {rel_path} ({mb:.1f} MB)")
        built += 1

    print(f"\nBuilt {built} browser cache(s), skipped {skipped}.")
    return 0 if built else 1


if __name__ == "__main__":
    sys.exit(main())
