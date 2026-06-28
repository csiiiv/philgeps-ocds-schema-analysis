#!/usr/bin/env python3
"""Validate a transformed OCDS release package (pre-flight + libcoveocds).

Default target is references/transformed/sample1k.json — generate it first:

    python scripts/transform_to_ocds.py raw/<export>.csv --sample 1000 --out references/transformed/sample1k
    python scripts/validate_transform_sample.py

Or point at any package produced by transform_to_ocds.py:

    python scripts/validate_transform_sample.py references/transformed/2024-10_2024-12.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ocds_checks import check_release_package  # noqa: E402

DEFAULT_TARGET = ROOT / "references" / "transformed" / "sample1k.json"


def validate(target: Path) -> int:
    if not target.exists():
        print(f"package not found: {target}", file=sys.stderr)
        print("Run transform_to_ocds.py first (see --help).", file=sys.stderr)
        return 1

    data = json.loads(target.read_text(encoding="utf-8"))

    issues = check_release_package(data)
    if issues:
        print(f"Pre-flight found {len(issues)} issue(s):")
        for issue in issues[:20]:
            print(f"  - {issue}")
        if len(issues) > 20:
            print(f"  ... and {len(issues) - 20} more")
        return 1
    print("Pre-flight: OK")

    try:
        from libcoveocds.api import ocds_json_output
    except ImportError:
        print("libcoveocds not installed. Run: pip install -r requirements-dev.txt", file=sys.stderr)
        return 2

    tmp = Path(tempfile.mkdtemp(prefix="libcove-"))
    try:
        result = ocds_json_output(str(tmp), str(target), schema_version="1.1")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    errors = result.get("validation_errors") or []
    additional = result.get("additional_checks") or []
    print(
        f"libcoveocds: {len(errors)} validation error(s), "
        f"{len(additional)} additional check(s)"
    )
    for err in errors[:25]:
        print(f"  - {err.get('description', err)} @ {err.get('path', '?')}")
    for check in additional[:10]:
        print(f"  [additional] {check}")
    if errors:
        return 1

    release_count = len(data.get("releases", []))
    print(f"OK: {target.name} ({release_count:,} releases) validates against OCDS 1.1")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "package",
        nargs="?",
        type=Path,
        default=DEFAULT_TARGET,
        help=f"OCDS package JSON (default: {DEFAULT_TARGET.relative_to(ROOT)})",
    )
    return validate(parser.parse_args().package)


if __name__ == "__main__":
    sys.exit(main())
