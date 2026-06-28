#!/usr/bin/env python3
"""Run the PhilGEPS → OCDS transform on every raw export (full files, no sampling).

CSV files use ``scripts/transform_to_ocds.py`` (streaming). XLSX files use
``scratch/sample_and_transform.py --full``. libcoveocds validation is skipped
by default — shape pre-flight and source DQ still run via the unified report.

Usage:
    python scripts/run_full_dataset.py
    python scripts/run_full_dataset.py --resume
    python scripts/run_full_dataset.py --only "2021.csv"
    python scripts/run_full_dataset.py --dry-run
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT.parent / "raw"
OUT_ROOT = ROOT / "references" / "transformed" / "full"
PY = ROOT / ".venv-validate" / "Scripts" / "python.exe"
LOG_DIR = ROOT / "references" / "transformed" / "logs"

# Non-PhilGEPS paths under raw/ to skip
SKIP_PARTS = {"SSP", "flood-control-projects.csv"}


def discover_files() -> list[Path]:
    files: list[Path] = []
    for path in sorted(RAW.rglob("*")):
        if not path.is_file():
            continue
        if path.suffix.lower() not in (".csv", ".xlsx"):
            continue
        if path.stat().st_size == 0:
            continue
        rel = path.relative_to(RAW)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if path.name in SKIP_PARTS:
            continue
        if path.name.startswith("~$"):
            continue
        files.append(path)
    return files


def out_base_for(file_path: Path) -> Path:
    rel = file_path.relative_to(RAW)
    return OUT_ROOT / rel.with_suffix("")


def run_one(file_path: Path, *, run_ocds: bool, quiet: bool) -> dict:
    out_base = out_base_for(file_path)
    out_base.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.time()

    if file_path.suffix.lower() == ".csv":
        cmd = [
            str(PY),
            str(ROOT / "scripts" / "transform_to_ocds.py"),
            str(file_path),
            "--out",
            str(out_base),
            "--skip-ocds-validate",
        ]
        if quiet:
            cmd.append("--quiet")
    else:
        cmd = [
            str(PY),
            str(ROOT / "scratch" / "sample_and_transform.py"),
            str(file_path),
            "--full",
            "--out",
            str(out_base),
            "--skip-ocds-validate",
        ]

    if run_ocds:
        # Re-enable validation: remove skip flag and add validate step later if needed.
        cmd = [c for c in cmd if c != "--skip-ocds-validate"]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.time() - t0
    report_path = out_base.with_suffix(".report.json")

    row: dict = {
        "file": str(file_path.relative_to(RAW)),
        "bytes": file_path.stat().st_size,
        "out_base": str(out_base.relative_to(ROOT)),
        "elapsed_s": round(elapsed, 1),
        "returncode": proc.returncode,
    }

    if report_path.exists():
        report = json.loads(report_path.read_text(encoding="utf-8"))
        row["status"] = "ok" if proc.returncode == 0 else "failed"
        row["all_passed"] = report.get("summary", {}).get("all_passed")
        row["compiled_releases"] = report.get("compiled_release_count")
        fc = report.get("summary", {}).get("finding_counts", {})
        row["finding_counts"] = fc
        row["top_findings"] = (report.get("summary", {}).get("top_findings") or [])[:5]
        row["unified_report"] = str(report_path.relative_to(ROOT))
    elif proc.returncode != 0:
        row["status"] = "failed"
        row["stderr_tail"] = proc.stderr[-2000:]
        row["stdout_tail"] = proc.stdout[-1000:]
    else:
        row["status"] = "no_report"

    row["stdout_tail"] = proc.stdout[-1500:] if proc.stdout else ""
    return row


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--resume", action="store_true", help="Skip files that already have .report.json")
    p.add_argument("--dry-run", action="store_true", help="List files only")
    p.add_argument("--only", type=str, default=None, help="Substring filter on file path")
    p.add_argument(
        "--run-ocds-validate",
        action="store_true",
        help="Run libcoveocds on each output (very slow on full data)",
    )
    p.add_argument("--no-quiet", action="store_true", help="Show per-row progress from transforms")
    p.add_argument(
        "--merge-by-year",
        action="store_true",
        default=True,
        help="After each file (or at end), refresh references/transformed/by_year/ (default: on)",
    )
    p.add_argument(
        "--no-merge-by-year",
        action="store_false",
        dest="merge_by_year",
        help="Do not run merge_ocds_by_year after transforms",
    )
    args = p.parse_args()

    files = discover_files()
    if args.only:
        files = [f for f in files if args.only.lower() in str(f).lower()]

    print(f"Discovered {len(files)} PhilGEPS files ({sum(f.stat().st_size for f in files) / 1e9:.2f} GB)")
    for f in files:
        print(f"  {f.relative_to(RAW)}  ({f.stat().st_size / 1e6:.1f} MB)")

    if args.dry_run:
        return 0

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    results_path = OUT_ROOT / "full_dataset_results.json"
    results: list[dict] = []
    if args.resume and results_path.exists():
        try:
            payload = json.loads(results_path.read_text(encoding="utf-8"))
            if isinstance(payload, list):
                results = payload
            elif isinstance(payload, dict):
                results = list(payload.get("results") or [])
        except json.JSONDecodeError:
            results = []

    done_reports = {
        r["file"]
        for r in results
        if isinstance(r, dict) and r.get("status") == "ok" and r.get("unified_report")
    }

    for i, file_path in enumerate(files, 1):
        rel = str(file_path.relative_to(RAW))
        report_path = out_base_for(file_path).with_suffix(".report.json")
        if args.resume and (rel in done_reports or report_path.exists()):
            print(f"[{i}/{len(files)}] SKIP (resume) {rel}")
            continue

        print(f"\n[{i}/{len(files)}] RUN {rel}")
        try:
            row = run_one(
                file_path,
                run_ocds=args.run_ocds_validate,
                quiet=not args.no_quiet,
            )
        except Exception as exc:  # noqa: BLE001
            row = {
                "file": rel,
                "status": "exception",
                "error": str(exc),
            }
        results.append(row)
        print(
            f"  -> {row.get('status')}  "
            f"releases={row.get('compiled_releases', '?')}  "
            f"elapsed={row.get('elapsed_s', '?')}s"
        )
        if row.get("stderr_tail"):
            print(row["stderr_tail"][-500:], file=sys.stderr)

        # Incremental checkpoint
        payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "file_count": len(files),
            "completed": len(results),
            "results": results,
        }
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    if args.merge_by_year:
        print("\nMerging per-file OCDS packages into by_year/ ...")
        merge_cmd = [
            str(PY),
            str(ROOT / "scripts" / "merge_ocds_by_year.py"),
            "--resume",
        ]
        merge_proc = subprocess.run(merge_cmd, capture_output=True, text=True)
        print(merge_proc.stdout)
        if merge_proc.returncode != 0:
            print(merge_proc.stderr[-2000:], file=sys.stderr)
            return 1

    ok = sum(1 for r in results if r.get("status") == "ok")
    fail = sum(1 for r in results if r.get("status") not in ("ok", None))
    print(f"\nDone: {ok} ok, {fail} failed/skipped — {results_path}")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
