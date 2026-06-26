#!/usr/bin/env python3
"""Validate references/SAMPLE_OCDS_RELEASE_PACKAGE.json against OCDS 1.1.

Uses libcoveocds (the same engine as open-contracting/cove-ocds, the OCDS Data
Review Tool) to validate the sample release package emitted by
build_schema_field_map.py. This performs JSON Schema validation and resolves
any extensions listed in the package's `extensions` array.

Scope note: this validates the SHAPE of the sample release (that our staging
rules produce OCDS-conformant JSON). It is NOT a data-quality check and does
NOT validate the mapping config against real PhilGEPS exports. For real-data
validation, run libcoveocds or the OCDS Data Review Tool against the downstream
compiler's actual output.

Usage:
    python scripts/validate_sample_release.py

Exits non-zero on any validation error.
"""

from __future__ import annotations

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "references" / "SAMPLE_OCDS_RELEASE_PACKAGE.json"


def _structural_checks(data: dict) -> list[str]:
    """Cheap pre-flight checks that surface common issues before schema validation."""
    issues: list[str] = []

    if "releases" not in data:
        issues.append("package missing top-level `releases` array")
        return issues
    if not isinstance(data["releases"], list) or not data["releases"]:
        issues.append("`releases` must be a non-empty array")
        return issues

    release = data["releases"][0]
    if not isinstance(release, dict):
        issues.append("`releases[0]` must be an object")
        return issues

    for required in ("ocid", "id", "date", "initiationType", "tag"):
        if required not in release:
            issues.append(f"release missing required field: {required}")

    if "version" in data and isinstance(data["version"], str) and data["version"].count(".") > 1:
        issues.append(
            f"version '{data['version']}' includes a patch digit; "
            "OCDS uses major.minor only (e.g. '1.1')"
        )

    for ext_url in data.get("extensions", []) or []:
        if not isinstance(ext_url, str):
            continue
        if ext_url.endswith("/master/extension.json") or "/master/" in ext_url:
            issues.append(
                f"extension pinned to /master branch (use a tag for reproducibility): {ext_url}"
            )
    return issues


def _libcove_validate(path: Path) -> tuple[list, list, str | None] | None:
    """Run libcoveocds validation. Returns (validation_errors, additional_checks, version_used)
    or None if libcoveocds is unavailable."""
    try:
        from libcoveocds.api import ocds_json_output
    except ImportError as exc:
        print(
            f"libcoveocds is not installed or failed to import: {exc}\n"
            "Run: pip install -r requirements-dev.txt",
            file=sys.stderr,
        )
        return None

    tmp = Path(tempfile.mkdtemp(prefix="libcoveocds-"))
    try:
        result = ocds_json_output(str(tmp), str(path), schema_version="1.1")
        return (
            result.get("validation_errors") or [],
            result.get("additional_checks") or [],
            result.get("version_used"),
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    if not SAMPLE.exists():
        print(
            f"missing file: {SAMPLE} (run python scripts/build_schema_field_map.py first)",
            file=sys.stderr,
        )
        return 1

    print(f"# Validating {SAMPLE.relative_to(ROOT)}")

    try:
        data = json.loads(SAMPLE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"invalid JSON: {exc}", file=sys.stderr)
        return 1

    issues = _structural_checks(data)
    if issues:
        print("Pre-flight checks failed:", file=sys.stderr)
        print("\n".join(f"  - {i}" for i in issues), file=sys.stderr)
        return 1

    errors, additional, version_used = _libcove_validate(SAMPLE)
    if errors is None:
        return 1  # libcoveocds unavailable — already reported above

    if version_used:
        print(f"# OCDS schema version used: {version_used}")

    if errors:
        print(f"# FAIL: {len(errors)} validation error(s)", file=sys.stderr)
        for err in errors:
            print(f"  - {err.get('description', err)} @ {err.get('path', '?')}", file=sys.stderr)
        return 1

    if additional:
        print(f"# NOTE: {len(additional)} additional check(s) flagged")
        for check in additional:
            print(f"  - {check}")

    print("# OK: sample release package validates against OCDS 1.1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
