#!/usr/bin/env python3
"""Smoke tests for scripts/_ocds_checks.check_release_package.

These are not unit tests for OCDS — they verify our pre-flight guards catch
each regression class we have actually hit (or could plausibly hit) when
generating the sample release package. If any of these stop raising, the
build-time hard-fail would silently let bad releases through.

Run via CI (see .github/workflows/build-and-validate.yml) or directly:

    python scripts/test_ocds_checks.py

Exits non-zero if any guard fails to fire on a known-bad mutation, or if the
clean baseline raises a false positive.
"""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _ocds_checks import check_release_package  # noqa: E402

CLEAN_PACKAGE: dict = {
    "version": "1.1",
    "extensions": [
        "https://raw.githubusercontent.com/open-contracting-extensions/ocds_bid_extension/v1.1.5/extension.json"
    ],
    "publishedDate": "2025-04-28T09:00:00+08:00",
    "releases": [
        {
            "ocid": "ocds-philgeps-1",
            "id": "r1",
            "date": "2025-04-28T09:00:00+08:00",
            "initiationType": "tender",
            "tag": ["compiled"],
            "tender": {
                "tenderPeriod": {
                    "startDate": "2025-04-01T08:00:00+08:00",
                    "endDate": "2025-04-22T10:00:00+08:00",
                }
            },
        }
    ],
}


def _clone() -> dict:
    # copy.deepcopy chokes on None values in some py versions; json round-trip is safe.
    return json.loads(json.dumps(CLEAN_PACKAGE))


def _expect_bad(label: str, mutator) -> None:
    pkg = _clone()
    mutator(pkg)
    issues = check_release_package(pkg)
    if not issues:
        raise AssertionError(f"`{label}` did NOT raise any issue (expected at least one)")
    print(f"[ok] {label} -> {len(issues)} issue(s): {issues[0]}")


def _expect_clean() -> None:
    issues = check_release_package(_clone())
    if issues:
        raise AssertionError(f"clean baseline raised false positives: {issues}")
    print("[ok] clean baseline raises no issues")


def main() -> int:
    failures: list[str] = []

    def run(label: str, fn):
        try:
            fn()
        except AssertionError as exc:
            failures.append(f"{label}: {exc}")
            print(f"[FAIL] {label}: {exc}", file=sys.stderr)

    # Each regression class we have hit (or could hit).
    run("wrapped release object", lambda: _expect_bad(
        "wrapped release object",
        lambda p: p.__setitem__("releases", [{"release": p["releases"][0]}]),
    ))
    run("version patch digit", lambda: _expect_bad(
        "version patch digit",
        lambda p: p.__setitem__("version", "1.1.5"),
    ))
    run("extension /master", lambda: _expect_bad(
        "extension /master",
        lambda p: p.__setitem__("extensions", [
            "https://raw.githubusercontent.com/open-contracting-extensions/ocds_bid_extension/master/extension.json"
        ]),
    ))
    run("datetime missing tz", lambda: _expect_bad(
        "datetime missing tz",
        lambda p: p["releases"][0]["tender"]["tenderPeriod"].__setitem__(
            "startDate", "2025-04-01T08:00:00"
        ),
    ))
    run("date-only on release.date", lambda: _expect_bad(
        "date-only on release.date",
        lambda p: p["releases"][0].__setitem__("date", "2025-05-12"),
    ))
    run("publishedDate missing tz", lambda: _expect_bad(
        "publishedDate missing tz",
        lambda p: p.__setitem__("publishedDate", "2025-04-28T09:00:00"),
    ))
    run("missing ocid", lambda: _expect_bad(
        "missing ocid",
        lambda p: p["releases"][0].pop("ocid"),
    ))
    run("empty releases", lambda: _expect_bad(
        "empty releases",
        lambda p: p.__setitem__("releases", []),
    ))
    run("clean baseline", _expect_clean)

    if failures:
        print(f"\n{len(failures)} check(s) failed to behave as expected", file=sys.stderr)
        return 1
    print("\nAll guards behave as expected.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
