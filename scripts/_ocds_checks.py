"""Shared OCDS pre-flight checks used by build + validate.

These rules guard against the regression classes we have actually hit while
generating the sample release package:

  1. Package structure: `releases` must be a direct array of release objects,
     not wrapped (`{"release": {...}}`).
  2. Version format: OCDS uses `major.minor` (e.g. `1.1`); a patch digit
     fails schema validation.
  3. Extension URLs: must be pinned to an immutable tag, never `/master`.
  4. Date formats: every date-typed field must be RFC 3339 with an explicit
     timezone if a time component is present.

The build script runs these BEFORE writing the sample file and raises on any
failure, so a malformed release can never land on disk. The standalone
validator runs the same checks as a fast pre-flight before handing off to
libcoveocds for full schema validation.

Scope: these are cheap syntactic guards, NOT a substitute for libcoveocds.
They exist so the build fails fast without requiring libcoveocds to be
installed.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# Top-level release fields the OCDS release schema requires.
RELEASE_REQUIRED_FIELDS = ("ocid", "id", "date", "initiationType", "tag")


# Keys whose values are typed as `date` (not `date-time`) in the OCDS release
# schema. Everything else ending in `date` is assumed to be `date-time`, which
# is the dominant case in OCDS 1.1. Add to this set if a new pure-date field
# is introduced.
PURE_DATE_KEYS = frozenset({"year"})


def _is_date_key(key: str) -> bool:
    """True if `key` denotes a date-typed field in OCDS.

    Covers `date`, `startDate`, `endDate`, `publishedDate`, etc. Match is
    case-insensitive on the suffix `date`. Intentionally conservative —
    flagging an extra field is cheap, missing one defeats the guard.
    """
    if not isinstance(key, str) or not key:
        return False
    return key.lower().endswith("date")


def _requires_datetime(key: str) -> bool:
    """True if the field at `key` is typed `date-time` (needs a `T` and tz)."""
    return _is_date_key(key) and key not in PURE_DATE_KEYS


def _walk_date_strings(node: Any, path: str = "") -> list[tuple[str, str, bool]]:
    """Yield (json_pointer, value, requires_datetime) for every string value
    under a date-typed key."""
    found: list[tuple[str, str, bool]] = []
    if isinstance(node, dict):
        for k, v in node.items():
            child_path = f"{path}/{k}"
            if isinstance(v, str) and _is_date_key(k):
                found.append((child_path, v, _requires_datetime(k)))
            else:
                found.extend(_walk_date_strings(v, child_path))
    elif isinstance(node, list):
        for i, item in enumerate(node):
            found.extend(_walk_date_strings(item, f"{path}/{i}"))
    return found


def _parse_rfc3339(value: str) -> bool:
    """Return True if `value` is a valid RFC 3339 date-time.

    Accepts both full date-times (with optional timezone) and bare dates
    (`YYYY-MM-DD`). The caller decides whether bare dates are allowed for a
    given field; this helper only validates the syntactic shape.
    """
    if not isinstance(value, str) or not value:
        return False
    # Bare date: only valid if no time component. The OCDS release schema
    # types most date fields as `date-time`, so the caller must enforce that.
    formats = (
        "%Y-%m-%dT%H:%M:%S%z",  # 2025-04-28T09:00:00+08:00
        "%Y-%m-%dT%H:%M:%SZ",   # 2025-04-28T09:00:00Z (UTC)
        "%Y-%m-%dT%H:%M:%S",    # bare datetime — flagged separately
        "%Y-%m-%d",             # bare date
    )
    for fmt in formats:
        try:
            datetime.strptime(value, fmt)
            return True
        except ValueError:
            continue
    return False


def _has_explicit_timezone(value: str) -> bool:
    """True if a datetime string carries a `Z` or numeric offset.

    Only meaningful for values that already contain a `T` (i.e. datetimes).
    """
    if "T" not in value:
        return False
    tail = value.split("T", 1)[1]
    return tail.endswith("Z") or "+" in tail or (tail.count("-") >= 1 and not tail.startswith("-"))


def check_release_package(package: dict) -> list[str]:
    """Run all pre-flight checks against an OCDS release package.

    Returns a list of human-readable issue strings. Empty list means clean.
    Never raises — callers decide how to surface failures.
    """
    issues: list[str] = []
    if not isinstance(package, dict):
        return ["package must be a JSON object"]

    # --- Structure: releases must be a direct array of release objects ---------
    releases = package.get("releases")
    if not isinstance(releases, list):
        issues.append("package missing top-level `releases` array")
        return issues  # nothing else is meaningful without releases
    if not releases:
        issues.append("`releases` must be a non-empty array")
        return issues

    for i, release in enumerate(releases):
        if not isinstance(release, dict):
            issues.append(f"`releases/{i}` must be an object, got {type(release).__name__}")
            continue
        # Catch the historical regression: a release wrapped as
        # `{"release": {...}}` instead of the release object itself.
        if "release" in release and isinstance(release["release"], dict) and "ocid" not in release:
            issues.append(
                f"`releases/{i}` looks wrapped (has `release` key but no top-level `ocid`); "
                "the release object must be the array element, not nested under `release`"
            )
            continue

        for field in RELEASE_REQUIRED_FIELDS:
            if field not in release or release[field] in (None, "", [], {}):
                issues.append(f"`releases/{i}` missing required field: {field}")

    # --- Version format -------------------------------------------------------
    version = package.get("version")
    if isinstance(version, str):
        if version.count(".") > 1:
            issues.append(
                f"package.version '{version}' includes a patch digit; "
                "OCDS uses major.minor only (e.g. '1.1')"
            )
        elif "." not in version:
            issues.append(
                f"package.version '{version}' is missing minor segment; "
                "expected format like '1.1'"
            )
    elif version is None:
        issues.append("package missing `version` field (OCDS 1.1 releases must declare it)")

    # --- Extensions pinned to tags, not /master --------------------------------
    for ext_url in package.get("extensions", []) or []:
        if not isinstance(ext_url, str):
            issues.append(f"extension entry must be a string, got {type(ext_url).__name__}")
            continue
        if "/master/" in ext_url or ext_url.endswith("/master/extension.json"):
            issues.append(
                f"extension pinned to /master (use a tag for reproducibility): {ext_url}"
            )

    # --- Date formats ----------------------------------------------------------
    # Walk the whole package (including publishedDate at the top level and the
    # entire releases tree) so nested dates (periods, milestones, bids) are
    # covered. Any value under a date-typed key must be RFC 3339, and any
    # datetime-typed field must carry a `T` and an explicit timezone.
    for pointer, value, requires_dt in _walk_date_strings(package, ""):
        if not _parse_rfc3339(value):
            issues.append(f"date at `{pointer}` is not RFC 3339: {value!r}")
            continue
        if requires_dt:
            if "T" not in value:
                issues.append(
                    f"date-time at `{pointer}` is missing a time component (expected full "
                    f"datetime with timezone): {value!r}"
                )
            elif not _has_explicit_timezone(value):
                issues.append(
                    f"date-time at `{pointer}` is missing a timezone offset "
                    f"(expected `Z` or `+HH:MM`): {value!r}"
                )

    return issues


def assert_release_package(package: dict, *, source: str = "build") -> None:
    """Run check_release_package and raise ValueError on any issue.

    Use this in the build script so a bad release can never be written to
    disk. `source` is included in the error for traceability.
    """
    issues = check_release_package(package)
    if issues:
        bullets = "\n  - ".join(issues)
        raise ValueError(
            f"OCDS sample release package failed pre-flight checks ({source}):\n  - {bullets}\n"
            "Fix the staging config or SAMPLE_CANONICAL_ROW before regenerating."
        )
