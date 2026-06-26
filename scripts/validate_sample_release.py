#!/usr/bin/env python3
"""Validate references/SAMPLE_OCDS_RELEASE_PACKAGE.json against OCDS 1.1.

Two layers:

  1. Pre-flight structural checks (scripts/_ocds_checks.check_release_package)
     — the same rules the build script enforces before writing the file.
     Runs without libcoveocds installed, so it works in any environment.
  2. Full JSON Schema validation via libcoveocds (the engine behind the OCDS
     Data Review Tool). Resolves extensions and runs the authoritative
     schema checks. Requires `pip install -r requirements-dev.txt`.

Scope note: this validates the SHAPE of the sample release (that our staging
rules produce OCDS-conformant JSON). It is NOT a data-quality check and does
NOT validate the mapping config against real PhilGEPS exports. For real-data
validation, run libcoveocds or the OCDS Data Review Tool against the
downstream compiler's actual output.

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
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _ocds_checks import check_release_package  # noqa: E402

SAMPLE = ROOT / "references" / "SAMPLE_OCDS_RELEASE_PACKAGE.json"


def _libcove_validate(path: Path) -> tuple[list, list, str | None] | None:
    """Run libcoveocds validation. Returns (validation_errors, additional_checks,
    version_used) or None if libcoveocds is unavailable."""
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

    # Layer 1: shared pre-flight checks. These run regardless of whether
    # libcoveocds is installed and stay in sync with the build-time guard.
    issues = check_release_package(data)
    if issues:
        print("Pre-flight checks failed:", file=sys.stderr)
        print("\n".join(f"  - {i}" for i in issues), file=sys.stderr)
        return 1

    # Layer 2: authoritative schema validation via libcoveocds.
    errors, additional, version_used = _libcove_validate(SAMPLE)
    if errors is None:
        # libcoveocds unavailable — pre-flight passed, but we couldn't run
        # the deep check. Treat as a failure so CI catches missing deps.
        return 1

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
