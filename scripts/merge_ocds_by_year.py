#!/usr/bin/env python3
"""Merge per-file OCDS packages under ``references/transformed/full/`` into per-year datasets.

Quarterly XLSX exports (e.g. Jan–Mar / Oct–Dec 2013) are combined into one
release package per calendar year. Yearly CSV files map 1:1. Outputs land in
``references/transformed/by_year/``.

Usage:
    python scripts/merge_ocds_by_year.py
    python scripts/merge_ocds_by_year.py --input references/transformed/full
    python scripts/merge_ocds_by_year.py --years 2009,2024
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _year_utils import year_from_path  # noqa: E402
from _release_browser import refresh_browser_cache_from_package, write_browser_cache  # noqa: E402
from _year_dq import write_year_dq_cache  # noqa: E402

DEFAULT_IN = ROOT / "references" / "transformed" / "full"
DEFAULT_OUT = ROOT / "references" / "transformed" / "by_year"

PACKAGE_SUFFIXES = {".json"}
SKIP_NAMES = {"full_dataset_results.json"}


def discover_packages(input_root: Path) -> list[Path]:
    out: list[Path] = []
    for path in sorted(input_root.rglob("*.json")):
        if path.name in SKIP_NAMES:
            continue
        if path.name.endswith(".dq.json") or path.name.endswith(".report.json"):
            continue
        if path.name.endswith(".validation.json"):
            continue
        out.append(path)
    return out


def year_from_package_path(path: Path) -> str | None:
    return year_from_path(path)


def _needs_merge(year: str, package_paths: list[Path], out_pkg: Path, resume: bool) -> bool:
    if not resume or not out_pkg.exists():
        return True
    if out_pkg.stat().st_size == 0:
        return True
    out_mtime = out_pkg.stat().st_mtime
    return any(p.stat().st_mtime > out_mtime for p in package_paths)


def _merge_rule_counts(target: Counter, rules: list[dict]) -> None:
    for entry in rules or []:
        key = (entry.get("rule"), entry.get("severity"), entry.get("layer", "source_dq"))
        target[key] += int(entry.get("count") or 0)


def _rule_counts_to_list(counter: Counter) -> list[dict]:
    rows = []
    for (rule, severity, layer), count in counter.most_common():
        row = {"rule": rule, "severity": severity, "count": count}
        if layer != "source_dq":
            row["layer"] = layer
        rows.append(row)
    return rows


def _write_json_file(path: Path, obj: object, *, compact: bool = False) -> None:
    """Write JSON to disk without building the full document string in RAM."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(obj, f, indent=None if compact else 2, ensure_ascii=False)
        f.write("\n")


def _load_sidecar(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def merge_year(
    year: str,
    package_paths: list[Path],
    *,
    output_root: Path,
    resume: bool = False,
) -> dict:
    """Merge source packages into ``by_year/<year>.json`` and aggregated report."""
    output_root.mkdir(parents=True, exist_ok=True)
    out_pkg = output_root / f"{year}.json"
    out_report = output_root / f"{year}.report.json"

    if not _needs_merge(year, package_paths, out_pkg, resume):
        refresh_browser_cache_from_package(out_pkg, year=year, output_root=output_root)
        state = json.loads(out_report.read_text(encoding="utf-8")) if out_report.exists() else {}
        return {
            "year": year,
            "source_files": len(package_paths),
            "releases": state.get("compiled_release_count", 0),
            "duplicate_ocids_overwritten": state.get("duplicate_ocids_overwritten", 0),
            "package_mb": round(out_pkg.stat().st_size / 1e6, 1),
            "report_path": str(out_report.relative_to(ROOT)),
            "skipped": True,
        }

    releases_by_ocid: dict[str, dict] = {}
    duplicate_ocids = 0
    source_files: list[dict] = []

    package_template: dict | None = None
    severity = Counter()
    finding_counts = Counter()
    rule_counter: Counter = Counter()

    rows_seen = rows_committed = rows_quarantined = 0
    shape_issues = 0

    for pkg_path in package_paths:
        pkg = json.loads(pkg_path.read_text(encoding="utf-8"))
        if package_template is None:
            package_template = {
                k: v for k, v in pkg.items() if k != "releases"
            }

        n_before = len(releases_by_ocid)
        for release in pkg.get("releases") or []:
            ocid = release.get("ocid") or release.get("id")
            if not ocid:
                continue
            key = str(ocid)
            if key in releases_by_ocid:
                duplicate_ocids += 1
            releases_by_ocid[key] = release
        added = len(releases_by_ocid) - n_before

        rel_report = _load_sidecar(pkg_path.with_suffix(".report.json"))
        rel_dq = _load_sidecar(pkg_path.with_suffix(".dq.json"))
        meta = rel_report or rel_dq or {}

        source_files.append({
            "path": str(pkg_path.relative_to(ROOT)),
            "releases_in_file": len(pkg.get("releases") or []),
            "releases_added": added,
            "duplicate_ocids_overwritten": len(pkg.get("releases") or []) - added,
        })

        if rel_report:
            src = rel_report.get("layers", {}).get("source_dq", {})
            sc = src.get("severity_counts") or {}
            for k, v in sc.items():
                severity[k] += int(v or 0)
            rows_seen += int(src.get("rows_seen") or 0)
            rows_committed += int(src.get("rows_committed") or 0)
            rows_quarantined += int(src.get("rows_quarantined") or 0)
            _merge_rule_counts(rule_counter, src.get("rule_counts"))
            fc = rel_report.get("summary", {}).get("finding_counts") or {}
            for k, v in fc.items():
                finding_counts[k] += int(v or 0)
            if not rel_report.get("layers", {}).get("shape_preflight", {}).get("passed", True):
                shape_issues += rel_report["layers"]["shape_preflight"].get("issue_count", 0)
        elif rel_dq:
            sc = rel_dq.get("severity_counts") or {}
            for k, v in sc.items():
                severity[k] += int(v or 0)
            rows_seen += int(rel_dq.get("rows_seen") or 0)
            rows_committed += int(rel_dq.get("rows_committed") or 0)
            rows_quarantined += int(rel_dq.get("rows_quarantined") or 0)
            _merge_rule_counts(rule_counter, rel_dq.get("rule_counts"))

    releases = list(releases_by_ocid.values())
    releases.sort(key=lambda r: (r.get("date") or "", r.get("ocid") or ""))

    if package_template is None:
        package_template = {
            "version": "1.1",
            "extensions": [],
            "publishedDate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "publisher": {
                "name": "Philippine Government Electronic Procurement System (PhilGEPS)",
                "scheme": "PH-PhilGEPS",
                "uid": "ph-philgeps",
                "uri": "https://www.philgeps.gov.ph",
            },
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "publicationPolicy": "https://philgeps-ocds.example/policy",
        }

    merged_package = dict(package_template)
    merged_package["uri"] = f"https://philgeps-ocds.example/by-year/{year}.json"
    merged_package["releases"] = releases

    output_root.mkdir(parents=True, exist_ok=True)

    compact = len(releases) > 200_000
    _write_json_file(out_pkg, merged_package, compact=compact)

    top_findings = _rule_counts_to_list(rule_counter)[:20]
    all_passed = (
        severity.get("error", 0) == 0
        and shape_issues == 0
    )

    report = {
        "report_version": "1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "calendar_year": year,
        "source_file_count": len(package_paths),
        "source_files": source_files,
        "compiled_release_count": len(releases),
        "duplicate_ocids_overwritten": duplicate_ocids,
        "layers": {
            "source_dq": {
                "rows_seen": rows_seen,
                "rows_committed": rows_committed,
                "rows_quarantined": rows_quarantined,
                "severity_counts": dict(severity),
                "rule_counts": _rule_counts_to_list(rule_counter),
            },
            "shape_preflight": {
                "passed": shape_issues == 0,
                "issue_count": shape_issues,
            },
        },
        "summary": {
            "all_passed": all_passed,
            "finding_counts": dict(finding_counts),
            "top_findings": top_findings,
        },
        "artifacts": {
            "package": str(out_pkg.relative_to(ROOT)),
            "unified_report": str(out_report.relative_to(ROOT)),
        },
    }
    out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    artifacts_updated = False
    browser_path = write_browser_cache(releases, year=year, output_root=output_root)
    if browser_path:
        report.setdefault("artifacts", {})["browser_cache"] = str(browser_path.relative_to(ROOT))
        artifacts_updated = True

    dq_path = write_year_dq_cache(year, package_paths, output_root=output_root, year_report=report)
    if dq_path:
        report.setdefault("artifacts", {})["dq_cache"] = str(dq_path.relative_to(ROOT))
        artifacts_updated = True

    if artifacts_updated:
        out_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "year": year,
        "source_files": len(package_paths),
        "releases": len(releases),
        "duplicate_ocids_overwritten": duplicate_ocids,
        "package_mb": round(out_pkg.stat().st_size / 1e6, 1),
        "report_path": str(out_report.relative_to(ROOT)),
        "skipped": False,
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input", type=Path, default=DEFAULT_IN)
    p.add_argument("--output", type=Path, default=DEFAULT_OUT)
    p.add_argument("--years", type=str, default=None, help="Comma-separated years to merge (default: all found)")
    p.add_argument("--resume", action="store_true", help="Skip years whose output is newer than all sources")
    args = p.parse_args()

    packages = discover_packages(args.input)
    by_year: dict[str, list[Path]] = defaultdict(list)
    for pkg_path in packages:
        year = year_from_package_path(pkg_path)
        if not year:
            print(f"[skip] cannot infer year: {pkg_path}", file=sys.stderr)
            continue
        by_year[year].append(pkg_path)

    if args.years:
        wanted = {y.strip() for y in args.years.split(",")}
        by_year = {y: paths for y, paths in by_year.items() if y in wanted}

    if not by_year:
        print("No packages to merge.", file=sys.stderr)
        return 1

    print(f"Merging {len(packages)} package(s) into {len(by_year)} year(s) -> {args.output}")
    index: list[dict] = []
    for year in sorted(by_year):
        paths = by_year[year]
        print(f"  {year}: {len(paths)} source file(s)")
        for pth in paths:
            print(f"    - {pth.relative_to(args.input)}")
        row = merge_year(year, paths, output_root=args.output, resume=args.resume)
        index.append(row)
        tag = "skip" if row.get("skipped") else "ok"
        print(f"    -> {tag} {row['releases']:,} releases, {row['package_mb']} MB")

    index_path = args.output / "by_year_index.json"
    index_path.write_text(
        json.dumps(
            {
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "input_root": str(args.input.relative_to(ROOT)),
                "output_root": str(args.output.relative_to(ROOT)),
                "years": index,
            },
            indent=2,
            ensure_ascii=False,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"\nWrote index: {index_path.relative_to(ROOT)}")

    agg_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "aggregate_dataset_report.py")],
        capture_output=True,
        text=True,
    )
    if agg_proc.stdout.strip():
        print(agg_proc.stdout.strip())
    if agg_proc.returncode != 0 and agg_proc.stderr.strip():
        print(agg_proc.stderr.strip(), file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
