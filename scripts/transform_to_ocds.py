#!/usr/bin/env python3
"""Transform a PhilGEPS S4 CSV export into an OCDS 1.1 release package.

Streaming pipeline (handles the 373MB+ exports without loading into memory):

    raw CSV row
        │  1. detect schema (S4 marker columns)
        │  2. map columns → canonical fields (config/schema_mappings.yaml)
        │  3. data-quality gate (scripts/_data_quality.validate_row)
        │     └─ errors → quarantine; warnings/info → logged, row continues
        │  4. group by contracting process (bid_reference_no, else award_reference_no)
        │  5. compile canonical row → OCDS release (scripts/_ocds_compiler)
        ▼
    OCDS 1.1 release package (validated by scripts/_ocds_checks before write)

Outputs:
  - <out>.json             — release package (full OCDS 1.1)
  - <out>.dq.json          — data-quality report (counts + samples)
  - stdout                  — human-readable run summary

Usage:
    python scripts/transform_to_ocds.py <input.csv> [--out PATH] [--sample N] [--quiet]

`--sample N` caps the number of source rows processed (useful for quick
iteration without waiting on the full 373MB). `--out` defaults to
references/transformed/<basename>.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

_SLUGIFY = re.compile(r"[^a-zA-Z0-9]+")

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore

from _data_quality import RunReport, is_null, validate_process_group, validate_row  # noqa: E402
from _ocds_checks import assert_release_package  # noqa: E402
from _ocds_compiler import compile_grouped, process_group_key, resolve_release_display_collisions  # noqa: E402
from _unified_report import build_unified_report, print_unified_summary, write_unified_report  # noqa: E402


SCHEMA_MAPPINGS = ROOT / "config" / "schema_mappings.yaml"
CANONICAL_TO_OCDS = ROOT / "config" / "canonical_to_ocds.yaml"
CODELIST_MAPPINGS = ROOT / "config" / "ocds_codelist_mappings.yaml"

# Schema marker columns — checked most-specific first (S4 → S1).
S1_MARKERS = {"UOM", "Organization Name"}
S2_MARKERS = {"Unit of Measurement", "Organization Name"}
S3_MARKERS = {"Procuring Entity", "Created By", "List of Bidder's"}
S4_MARKERS = {"Procuring Entity (PE)", "Region", "Bid Notice Status"}


def _load_yaml(path: Path) -> dict:
    if yaml is None:
        print("PyYAML is required. Run: pip install -r requirements.txt", file=sys.stderr)
        sys.exit(2)
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _build_field_types(schema_mappings: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for ftype, fields in (schema_mappings.get("field_types") or {}).items():
        for f in fields:
            out[f] = ftype
    return out


def detect_schema(header: list[str]) -> str:
    """Return the schema_N key matching the header, defaulting to schema_4."""
    header_set = set(header)
    if S4_MARKERS.issubset(header_set):
        return "schema_4"
    if S3_MARKERS.issubset(header_set):
        return "schema_3"
    if S2_MARKERS.issubset(header_set):
        return "schema_2"
    if S1_MARKERS.issubset(header_set):
        return "schema_1"
    return "schema_4"


def _canonicalize(raw_row: dict, column_map: dict[str, str]) -> dict:
    """Apply column_map to a raw CSV row → canonical-field dict.

    Unmapped columns are dropped; mapped columns keep their raw string value.
    Type coercion happens later (in the compiler, via _coerce_value).
    """
    out: dict = {}
    for col, value in raw_row.items():
        canonical = column_map.get(col)
        if canonical:
            out[canonical] = value
    return out


def transform(
    input_csv: Path,
    *,
    out_base: Path,
    sample: int | None = None,
    quiet: bool = False,
    run_ocds_validate: bool = True,
) -> dict:
    """Run the full transform pipeline. Returns the run-report dict."""
    schema_mappings = _load_yaml(SCHEMA_MAPPINGS)
    ocds_cfg = _load_yaml(CANONICAL_TO_OCDS)
    codelists = _load_yaml(CODELIST_MAPPINGS)
    field_types = _build_field_types(schema_mappings)

    run_report = RunReport()
    # Grouped rows awaiting compilation: process key → list of canonical rows.
    grouped: dict[str, list[dict]] = defaultdict(list)
    grouped_indices: dict[str, list[int]] = defaultdict(list)
    # Track first canonical row per group (for the "before/after" webapp view).
    first_rows: dict[str, dict] = {}
    header: list[str] = []

    def _log(msg: str) -> None:
        if not quiet:
            print(msg, file=sys.stderr)

    _log(f"# Reading {input_csv.name} ({input_csv.stat().st_size:,} bytes)")
    with input_csv.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        header = reader.fieldnames or []
        schema_key = detect_schema(header)
        column_map = schema_mappings.get(schema_key) or {}
        _log(f"# Detected schema: {schema_key} ({len(column_map)} mapped columns)")

        unknown_cols = [c for c in header if c not in column_map]
        if unknown_cols:
            _log(f"# Unmapped columns ({len(unknown_cols)}): {', '.join(unknown_cols[:5])}"
                 + ("…" if len(unknown_cols) > 5 else ""))

        for i, raw_row in enumerate(reader, start=1):
            if sample is not None and i > sample:
                _log(f"# Stopping at sample limit ({sample} rows)")
                break
            if i % 50000 == 0:
                _log(f"# …processed {i:,} rows")

            canonical = _canonicalize(raw_row, column_map)
            row_report = validate_row(canonical, row_index=i)
            run_report.add(i, row_report, canonical=canonical, raw_row=raw_row)

            if row_report.fatal:
                continue

            award_ref = canonical.get("award_reference_no")
            if is_null(award_ref) or str(award_ref).strip() == "0":
                run_report.rows_excluded_no_award += 1
                continue  # no award to compile
            process_key = process_group_key(canonical)
            if process_key is None:
                run_report.rows_excluded_no_process_key += 1
                continue
            grouped[process_key].append(canonical)
            grouped_indices[process_key].append(i)
            run_report.rows_grouped += 1
            if process_key not in first_rows:
                # Keep the raw input row for the webapp's "input sample" view.
                first_rows[process_key] = dict(raw_row)

    _log(f"# Grouped into {len(grouped):,} contracting processes")
    run_report.process_group_count = len(grouped)

    for process_key, rows in grouped.items():
        indices = grouped_indices[process_key]
        group_report = validate_process_group(
            list(zip(indices, rows)),
            process_key=process_key,
        )
        run_report.add_group(
            process_key,
            indices,
            group_report,
            canonical=rows[0],
            raw_row=first_rows.get(process_key),
        )

    # Compile each group into one release.
    releases: list[dict] = []
    compiled_input_samples: list[dict] = []  # for webapp before/after view
    input_sample_cap = 25
    for process_key, rows in grouped.items():
        release = compile_grouped(
            rows, ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists
        )
        if release is None:
            continue
        releases.append(release)
        if len(compiled_input_samples) < input_sample_cap and process_key in first_rows:
            compiled_input_samples.append({
                "process_key": process_key,
                "bid_reference_no": rows[0].get("bid_reference_no"),
                "award_reference_no": rows[0].get("award_reference_no"),
                "raw_row": first_rows[process_key],
                "release": release,
                "row_count": len(rows),
            })

    _log(f"# Compiled {len(releases):,} releases")

    collision_events = resolve_release_display_collisions(
        releases,
        ocid_prefix=ocds_cfg.get("ocid_prefix", "ocds-philgeps"),
    )
    if collision_events:
        _log(f"# Resolved {len(collision_events)} display id collision(s)")
        for event in collision_events:
            run_report.add_package_warning(
                "display_id_collision",
                (
                    f"Duplicate release id {event['original_id']!r} resolved to "
                    f"{event['resolved_id']!r} (composite display id)"
                ),
                event,
            )

    # Build a URL-safe package URI from the input filename. The raw filename
    # often contains spaces and "--" separators that break the OCDS `uri`
    # format check ("Invalid 'uri' found").
    safe_stem = _SLUGIFY.sub("-", input_csv.stem).strip("-")
    package_uri = f"https://philgeps-ocds.example/{safe_stem}.json"

    # Assemble the package.
    package = {
        "uri": package_uri,
        "version": ocds_cfg.get("ocds_version", "1.1"),
        "extensions": ocds_cfg.get("extensions", []),
        "publishedDate": "2025-01-01T00:00:00+08:00",
        "publisher": {
            "name": "Philippine Government Electronic Procurement System (PhilGEPS)",
            "scheme": "PH-PhilGEPS",
            "uid": "ph-philgeps",
            "uri": "https://www.philgeps.gov.ph",
        },
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "publicationPolicy": "https://philgeps-ocds.example/policy",
        "releases": releases,
    }

    # Hard-fail before finishing if the package violates OCDS shape rules.
    # Write the unified report first so shape/validation findings are captured.
    out_base.parent.mkdir(parents=True, exist_ok=True)
    package_path = out_base.with_suffix(".json")
    dq_path = out_base.with_suffix(".dq.json")

    input_rel = _rel_path(input_csv) or str(input_csv)

    dq_payload = {
        "input_file": input_rel,
        "input_bytes": input_csv.stat().st_size,
        "schema_detected": schema_key,
        "header": header,
        "mapped_column_count": len(column_map),
        "unmapped_columns": unknown_cols,
        **run_report.to_dict(),
        "compiled_release_count": len(releases),
        "compile_accounting": run_report.compile_accounting_dict(releases_compiled=len(releases)),
        "input_samples": compiled_input_samples,
    }

    unified = build_unified_report(
        dq_payload=dq_payload,
        package=package,
        package_path=package_path,
        dq_path=dq_path,
        run_ocds=run_ocds_validate,
    )
    shape_passed = unified["layers"]["shape_preflight"]["passed"]
    dq_payload["shape_error"] = (
        unified["layers"]["shape_preflight"]["first_issues"][0]
        if not shape_passed and unified["layers"]["shape_preflight"]["first_issues"]
        else None
    )

    # Stream to disk — json.dumps() duplicates the whole package in RAM and can
    # MemoryError on multi-GB exports (e.g. 2024.csv).
    compact = len(releases) > 200_000
    with package_path.open("w", encoding="utf-8") as f:
        json.dump(package, f, indent=None if compact else 2, ensure_ascii=False)
        f.write("\n")
    with dq_path.open("w", encoding="utf-8") as f:
        json.dump(dq_payload, f, indent=2, ensure_ascii=False)
        f.write("\n")
    report_path = write_unified_report(out_base, unified)

    try:
        package_rel = str(package_path.resolve().relative_to(ROOT))
        dq_rel = str(dq_path.resolve().relative_to(ROOT))
        report_rel = str(report_path.resolve().relative_to(ROOT))
    except ValueError:
        package_rel = str(package_path)
        dq_rel = str(dq_path)
        report_rel = str(report_path)

    _log(f"# Wrote {package_rel} ({len(releases):,} releases)")
    _log(f"# Wrote {dq_rel} (data-quality report)")
    _log(f"# Wrote {report_rel} (unified report)")

    assert_release_package(package, source="transform_to_ocds.transform")

    dq_payload["unified_report"] = report_rel
    if not quiet:
        print_unified_summary(unified)
    return dq_payload


def _rel_path(path: Path) -> str | None:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return None


def _print_summary(dq: dict) -> None:
    sc = dq["severity_counts"]
    print()
    print("=" * 60)
    print(f"Input:           {dq['input_file']} ({dq['input_bytes']:,} bytes)")
    print(f"Schema detected: {dq['schema_detected']} ({dq['mapped_column_count']} cols mapped)")
    print(f"Rows seen:       {dq['rows_seen']:,}")
    print(f"  committed:     {dq['rows_committed']:,}")
    print(f"  quarantined:   {dq['rows_quarantined']:,}")
    print(f"Issues:          {sc.get('error', 0):,} error(s), "
          f"{sc.get('warning', 0):,} warning(s), "
          f"{sc.get('info', 0):,} info")
    print(f"Releases:        {dq['compiled_release_count']:,}")
    if dq["rule_counts"]:
        print("Top rules:")
        for r in dq["rule_counts"][:8]:
            print(f"  {r['severity']:8s} {r['count']:>6,}  {r['rule']}")
    print("=" * 60)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("input", type=Path, help="PhilGEPS CSV export to transform")
    p.add_argument("--out", type=Path, default=None,
                   help="Output base path (without extension). "
                        "Defaults to references/transformed/<input-basename>")
    p.add_argument("--sample", type=int, default=None,
                   help="Stop after N source rows (for quick iteration)")
    p.add_argument("--quiet", action="store_true", help="Suppress progress logs")
    p.add_argument(
        "--skip-ocds-validate",
        action="store_true",
        help="Skip libcoveocds validation (faster; unified report omits OCDS layer)",
    )
    args = p.parse_args()

    if not args.input.exists():
        print(f"input not found: {args.input}", file=sys.stderr)
        return 1

    out_base = args.out or (ROOT / "references" / "transformed" / args.input.stem)

    transform(
        args.input,
        out_base=out_base,
        sample=args.sample,
        quiet=args.quiet,
        run_ocds_validate=not args.skip_ocds_validate,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
