#!/usr/bin/env python3
"""Backfill transform metadata in schema_bundle.json from demo_by_year samples.

``build_schema_field_map.py`` only embeds transform stats when
``combined.report.json`` or a single ``*.dq.json`` sidecar exists. On a clean
clone with demo data only, the webapp shows "No transform output embedded".

This script patches ``app/src/data/schema_bundle.json`` after
``build_schema_field_map.py`` when transform metadata is missing, using
``references/transformed/demo_by_year/`` browser caches so ETL pages (pipeline
overview, release browser year list) work in demo deploys.

When ``combined.report.json`` is present, ``build_schema_field_map.py`` already
embeds full-dataset stats and this script is a no-op.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEMO_DIR = ROOT / "references" / "transformed" / "demo_by_year"
BROWSER_DIR = DEMO_DIR / "browser"
DQ_DIR = DEMO_DIR / "dq"
BUNDLE_PATH = ROOT / "app" / "src" / "data" / "schema_bundle.json"
MAX_RELEASE_SAMPLES = 50


def _load_json(path: Path) -> dict | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _year_release_count(cache: dict) -> int:
    if cache.get("compiled_release_count") is not None:
        return int(cache["compiled_release_count"])
    if cache.get("detail_count") is not None:
        return int(cache["detail_count"])
    releases = cache.get("releases")
    if isinstance(releases, dict):
        return len(releases)
    if isinstance(releases, list):
        return len(releases)
    return 0


def _build_year_summaries() -> list[dict]:
    years: list[dict] = []
    for path in sorted(BROWSER_DIR.glob("*.json")):
        cache = _load_json(path)
        if not cache:
            continue
        year = path.stem
        pkg_path = DEMO_DIR / f"{year}.json"
        package_mb = pkg_path.stat().st_size / 1e6 if pkg_path.exists() else 0.0

        severity_counts = {"error": 0, "warning": 0, "info": 0}
        all_passed = True
        dq_path = DQ_DIR / f"{year}.json"
        dq = _load_json(dq_path) if dq_path.exists() else None
        if dq:
            summary = dq.get("summary") or {}
            metrics = dq.get("metrics") or {}
            errors = int(summary.get("errors") or len(metrics.get("errors") or []))
            warnings = int(summary.get("warnings") or len(metrics.get("warnings") or []))
            severity_counts = {"error": errors, "warning": warnings, "info": 0}
            all_passed = errors == 0

        years.append(
            {
                "year": year,
                "compiled_release_count": _year_release_count(cache),
                "package_mb": round(package_mb, 3),
                "source_file_count": 1,
                "all_passed": all_passed,
                "severity_counts": severity_counts,
            }
        )
    return years


def _collect_release_samples() -> list[dict]:
    for path in sorted(DEMO_DIR.glob("*.json")):
        if path.parent.name != "demo_by_year":
            continue
        pkg = _load_json(path)
        if not pkg:
            continue
        releases = pkg.get("releases") or []
        if releases:
            return list(releases)[:MAX_RELEASE_SAMPLES]
    return []


def build_demo_transform_bundle() -> dict:
    years = _build_year_summaries()
    if not years:
        raise SystemExit(f"No demo browser caches found under {BROWSER_DIR}")

    total_releases = sum(y["compiled_release_count"] for y in years)
    package_mb_total = round(sum(y["package_mb"] for y in years), 3)

    return {
        "scope": "single_file",
        "input_file": f"PhilGEPS demo sample ({len(years)} calendar years, demo_by_year/)",
        "input_bytes": 0,
        "schema_detected": "mixed",
        "mapped_column_count": 0,
        "unmapped_columns": [],
        "header": [],
        "rows_seen": total_releases,
        "rows_committed": total_releases,
        "rows_quarantined": 0,
        "severity_counts": {"error": 0, "warning": 0, "info": 0},
        "rule_counts": [],
        "issue_group_counts": [],
        "quarantined_samples": [],
        "quarantined_samples_omitted": 0,
        "warning_samples": [],
        "warning_samples_omitted": 0,
        "info_samples": [],
        "info_samples_omitted": 0,
        "compiled_release_count": total_releases,
        "source_file_count": len(years),
        "calendar_year_count": len(years),
        "package_mb_total": package_mb_total,
        "years": years,
        "releases_sample": _collect_release_samples(),
        "release_browser_base_url": "/data/releases",
        "release_detail_base_url": "/data/release",
        "input_samples": [],
        "package_path": str(DEMO_DIR.relative_to(ROOT)),
        "combined_report_path": None,
    }


def _update_summary(bundle: dict, transform: dict) -> None:
    summary = bundle.setdefault("summary", {})
    summary["transform_available"] = True
    summary["transform_scope"] = transform.get("scope")
    summary["transform_release_count"] = transform.get("compiled_release_count")
    summary["transform_release_sample_count"] = len(transform.get("releases_sample") or [])
    summary["transform_source_file_count"] = transform.get("source_file_count")
    summary["transform_calendar_year_count"] = transform.get("calendar_year_count")


def patch_bundle(*, force: bool = False) -> bool:
    if not BUNDLE_PATH.exists():
        raise SystemExit(f"Bundle not found: {BUNDLE_PATH}")

    bundle = _load_json(BUNDLE_PATH)
    if bundle is None:
        raise SystemExit(f"Failed to parse {BUNDLE_PATH}")

    existing = bundle.get("transform")
    if existing and bundle.get("summary", {}).get("transform_available") and not force:
        print("Transform metadata already embedded; skipping demo backfill.")
        return False

    transform = build_demo_transform_bundle()
    bundle["transform"] = transform
    _update_summary(bundle, transform)
    BUNDLE_PATH.write_text(json.dumps(bundle, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Demo transform bundle written: {len(transform['years'])} years, "
        f"{transform['compiled_release_count']} releases."
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace existing transform metadata even when already present.",
    )
    args = parser.parse_args()
    patch_bundle(force=args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
