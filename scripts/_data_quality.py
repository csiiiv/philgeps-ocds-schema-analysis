"""Categorized data-quality validator for canonical PhilGEPS rows.

Real PhilGEPS exports contain messy values: `NULL` literals, malformed dates,
missing identifiers on "awarded" rows, non-numeric strings in numeric fields,
and encoding artifacts. OCDS compilation would silently propagate these into
invalid releases. This module inspects each canonical row BEFORE the compiler
sees it and accumulates a structured report so issues can be reviewed,
counted, and surfaced in the webapp.

Design:
  - Severity-tagged: `error` (release would be OCDS-invalid or unidentifiable),
    `warning` (suspicious but compilable), `info` (noteworthy).
  - Rule-tagged: every issue carries a stable `rule` id (e.g. `missing_ocid`)
    so we can group, count, and track rule-specific prevalence over time.
  - Append-only: callers validate a row, then ask `report.fatal_count` etc.
    to decide whether to compile or quarantine the row.
  - Serializable: `report.to_dict()` produces the payload the webapp consumes.

This module does NOT decide policy. The transformer decides what to do with
the report (drop the row, fix in place, or compile anyway). Adding a new rule
is a one-liner in `validate_row` and shows up everywhere downstream.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Iterable, Iterator


# Severity ordering matters for escalation: any `error` blocks OCDS compilation.
SEVERITIES = ("error", "warning", "info")


@dataclass(frozen=True)
class Issue:
    """A single data-quality finding for one canonical row."""

    rule: str            # stable id, e.g. "missing_award_id"
    severity: str        # one of SEVERITIES
    field: str           # canonical field name (or "" for row-level)
    value: object        # the offending value (kept for review)
    message: str         # human-readable description


@dataclass
class DataQualityReport:
    """Append-only collection of issues with roll-up stats."""

    issues: list[Issue] = field(default_factory=list)

    def add(self, rule: str, severity: str, field: str, value: object, message: str) -> None:
        if severity not in SEVERITIES:
            raise ValueError(f"unknown severity {severity!r}; expected one of {SEVERITIES}")
        self.issues.append(Issue(rule=rule, severity=severity, field=field, value=value, message=message))

    # --- convenience constructors for the common severities -----------------
    def error(self, rule: str, field: str, value: object, message: str) -> None:
        self.add(rule, "error", field, value, message)

    def warning(self, rule: str, field: str, value: object, message: str) -> None:
        self.add(rule, "warning", field, value, message)

    def info(self, rule: str, field: str, value: object, message: str) -> None:
        self.add(rule, "info", field, value, message)

    # --- roll-up views ------------------------------------------------------
    @property
    def fatal(self) -> bool:
        return any(i.severity == "error" for i in self.issues)

    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "error")

    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "warning")

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == "info")

    def by_rule(self) -> dict[str, list[Issue]]:
        out: dict[str, list[Issue]] = {}
        for issue in self.issues:
            out.setdefault(issue.rule, []).append(issue)
        return out

    def __iter__(self) -> Iterator[Issue]:
        return iter(self.issues)

    def __len__(self) -> int:
        return len(self.issues)


# ---------------------------------------------------------------------------
# Value parsing helpers (shared with the compiler so parsing stays consistent)
# ---------------------------------------------------------------------------

# Treated as "missing" — PhilGEPS exports use the literal string `NULL`.
NULL_TOKENS = frozenset({"", "null", "none", "n/a", "na", "-"})

_ISSUE_CTX_RE = re.compile(r"^(row \d+|award [^:]+):\s*", re.IGNORECASE)
_ISSUE_ROW_LIST_RE = re.compile(r"\[[\d,\s]+\]")


def issue_message_pattern(message: str) -> str:
    """Normalize issue text for grouping (mirrors webapp ``messagePattern``)."""
    text = _ISSUE_CTX_RE.sub("", message or "")
    text = _ISSUE_ROW_LIST_RE.sub("[rows]", text)
    return text.strip()

# PhilGEPS S4 dates are dd/MM/yyyy. Compile-time always emits ISO 8601 with
# Asia/Manila offset (PhilGEPS is a Philippine system).
PHILGEPS_TZ = "+08:00"


def is_null(value: object) -> bool:
    """True if `value` should be treated as missing data."""
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip().lower() in NULL_TOKENS
    return False


def parse_decimal(value: object) -> tuple[float | None, str | None]:
    """Parse a numeric field. Returns (value_or_None, error_or_None).

    Accepts plain numbers and comma/PHP-peso formatted strings ("1,234.56").
    Returns (None, None) for null values; (None, msg) for unparseable input.
    """
    if is_null(value):
        return None, None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value), None
    text = str(value).strip().replace(",", "")
    try:
        return float(text), None
    except ValueError:
        return None, f"not numeric: {value!r}"


def parse_date(value: object) -> tuple[str | None, str | None]:
    """Parse a PhilGEPS date into ISO 8601 with +08:00 tz.

    Returns (iso_string_or_None, error_or_None). Null inputs yield (None, None).
    Datetimes are emitted at noon local time when only a date is available —
    OCDS date-time fields require a time component, and noon is a neutral
    placeholder that survives round-trips.

    Accepted formats:
      - dd/MM/yyyy, dd-MM-yyyy, dd/MM/yy  (CSV S3 exports)
      - yyyy-mm-dd                         (CSV ISO date)
      - ISO 8601 datetime with offset      (XLSX-derived strings, e.g. 2002-01-02T00:00:00+08:00)
      - bare datetime yyyy-mm-dd HH:MM:SS  (some XLSX serializations)
    """
    if is_null(value):
        return None, None
    text = str(value).strip()
    # Try ISO 8601 first (handles offsets, bare datetimes, and bare dates uniformly).
    iso_candidates = (
        text,
        # If a bare "yyyy-mm-dd HH:MM:SS" came through, swap the space for T.
        text.replace(" ", "T") if " " in text and "T" not in text else text,
    )
    for candidate in iso_candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            # If no tz, assume Asia/Manila.
            if parsed.tzinfo is None:
                from datetime import timezone, timedelta
                parsed = parsed.replace(tzinfo=timezone(timedelta(hours=8)))
            # OCDS pre-flight (_ocds_checks) accepts second precision only; CSV S3
            # exports often carry microsecond timestamps from the source system.
            parsed = parsed.replace(microsecond=0)
            return parsed.isoformat(), None
        except ValueError:
            pass
    # Fall back to legacy dd/MM/yyyy-family formats.
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed.strftime(f"%Y-%m-%dT12:00:00{PHILGEPS_TZ}"), None
        except ValueError:
            continue
    return None, f"not a date in any expected format (dd/MM/yyyy or ISO): {value!r}"


def parse_int(value: object) -> tuple[int | None, str | None]:
    if is_null(value):
        return None, None
    if isinstance(value, int) and not isinstance(value, bool):
        return value, None
    text = str(value).strip().replace(",", "")
    try:
        return int(text), None
    except ValueError:
        return None, f"not an integer: {value!r}"


# ---------------------------------------------------------------------------
# Row-level validation
# ---------------------------------------------------------------------------

# Fields whose absence makes a row unidentifiable for OCDS (cannot form an OCID
# or anchor a release).
IDENTITY_FIELDS = ("procuring_entity", "award_reference_no", "bid_reference_no")

# Fields expected to be present when a row claims to be awarded. Missing these
# is suspicious but not fatal — the row may be a legitimate cancellation.
AWARD_EXPECTED_FIELDS = (
    "awardee_organization_name",
    "contract_amount",
    "award_date",
)

# Process-level fields duplicated on every row of a multi-award bid. The
# compiler uses the first row with a valid bid_reference_no (or the first
# awarded row); differing values within a process group are suspicious.
PROCESS_CONFLICT_FIELDS = (
    "procuring_entity",
    "approved_budget",
    "notice_title",
    "procurement_mode",
    "bid_notice_status",
    "published_date",
    "closing_date",
    "bid_reference_no",
)

# Award-level fields expected to match within one award_reference_no subgroup.
AWARD_GROUP_CONFLICT_FIELDS = (
    "awardee_organization_name",
    "awardee_org_id",
    "contract_amount",
    "award_date",
    "award_notice_status",
    "awardee_joint_venture",
)

# Union kept for award-scoped validate_group().
GROUP_CONFLICT_FIELDS = PROCESS_CONFLICT_FIELDS + AWARD_GROUP_CONFLICT_FIELDS

# Line-item fields used to detect duplicate line_item_no with distinct content.
LINE_ITEM_IDENTITY_FIELDS = (
    "item_name",
    "item_description",
    "quantity",
    "item_budget",
    "unspsc_code",
)

# Numeric fields where a non-positive value is suspicious for an awarded row.
POSITIVE_AMOUNT_FIELDS = (
    ("approved_budget", "tender value"),
    ("contract_amount", "award value"),
    ("item_budget", "item unit value"),
    ("quantity", "item quantity"),
)


def validate_row(row: dict, *, row_index: int) -> DataQualityReport:
    """Run all data-quality rules against one canonical row.

    `row_index` is the source CSV line number (1-based, header excluded) for
    traceability; included in messages so reports point back to the raw file.
    """
    report = DataQualityReport()
    ctx = f"row {row_index}"

    # --- Identity: required to anchor an OCDS release ------------------------
    # `award_reference_no` is the primary OCID source for S4/S5 exports; its
    # absence or placeholder status is normally fatal. EXCEPTION: rows that
    # represent closed/cancelled/failed tenders (no award was ever made) are
    # expected to have no award reference — those are downgraded to `info`,
    # since they're correctly excluded from OCDS compilation rather than being
    # data-quality defects.
    notice_status = str(row.get("bid_notice_status", "")).strip().lower()
    award_status = str(row.get("award_notice_status", "")).strip().lower()
    is_unawarded_tender = (
        notice_status in ("closed", "cancelled", "failed", "active", "shortlisted")
        or award_status in ("null", "", "cancelled")
    ) and is_null(row.get("contract_amount"))

    for field_name in IDENTITY_FIELDS:
        value = row.get(field_name)
        if is_null(value):
            if field_name == "award_reference_no" and is_unawarded_tender:
                # Legitimate non-awarded tender; not a data-quality defect.
                report.info(
                    rule="unawarded_tender",
                    field=field_name,
                    value=value,
                    message=(
                        f"{ctx}: no `{field_name}` (tender `{notice_status or 'unknown'}`, "
                        f"no award) — excluded from OCDS compilation as expected"
                    ),
                )
                continue
            severity = "error" if field_name != "bid_reference_no" else "warning"
            report.add(
                rule="missing_identity",
                severity=severity,
                field=field_name,
                value=value,
                message=f"{ctx}: identity field `{field_name}` is missing",
            )
        elif str(value).strip() == "0":
            severity = "error" if field_name == "award_reference_no" else "warning"
            rule = "placeholder_identity" if severity == "error" else "placeholder_bid_ref"
            report.add(
                rule=rule,
                severity=severity,
                field=field_name,
                value=value,
                message=(
                    f"{ctx}: `{field_name}` is `0` (placeholder, not a real reference)"
                    if severity == "error"
                    else f"{ctx}: `{field_name}` is `0` (S4 decommissions this column; "
                         f"award_reference_no is the primary identifier)"
                ),
            )

    # --- Type sanity on numeric fields ---------------------------------------
    for field_name, _label in POSITIVE_AMOUNT_FIELDS:
        raw = row.get(field_name)
        if is_null(raw):
            continue
        value, err = parse_decimal(raw)
        if err:
            report.error(
                rule="bad_numeric",
                field=field_name,
                value=raw,
                message=f"{ctx}: `{field_name}` {err}",
            )
        elif value is not None and value <= 0:
            # Only flag for awarded rows; un-awarded tenders legitimately have a 0 budget placeholder.
            award_status = str(row.get("award_notice_status", "")).lower()
            if field_name == "approved_budget" and award_status not in ("awarded", "active", "posted", "updated"):
                continue
            report.warning(
                rule="non_positive_amount",
                field=field_name,
                value=raw,
                message=f"{ctx}: `{field_name}` is non-positive ({value})",
            )

    # --- Date sanity ---------------------------------------------------------
    for field_name in ("published_date", "closing_date", "award_published_date", "award_date",
                       "notice_to_proceed_date", "contract_effectivity_date", "contract_end_date"):
        raw = row.get(field_name)
        if is_null(raw):
            continue
        _iso, err = parse_date(raw)
        if err:
            report.error(
                rule="bad_date",
                field=field_name,
                value=raw,
                message=f"{ctx}: `{field_name}` {err}",
            )

    # --- Cross-field consistency --------------------------------------------
    award_status = str(row.get("award_notice_status", "")).lower()
    is_awarded = award_status in ("awarded", "active", "posted", "updated")
    if is_awarded:
        for field_name in AWARD_EXPECTED_FIELDS:
            if is_null(row.get(field_name)):
                report.warning(
                    rule="award_missing_expected",
                    field=field_name,
                    value=row.get(field_name),
                    message=f"{ctx}: row is `{award_status}` but `{field_name}` is missing",
                )

    # Contract period inverted: end before start.
    start_iso, _ = parse_date(row.get("contract_effectivity_date"))
    end_iso, _ = parse_date(row.get("contract_end_date"))
    if start_iso and end_iso and end_iso < start_iso:
        report.warning(
            rule="inverted_contract_period",
            field="contract_end_date",
            value=row.get("contract_end_date"),
            message=f"{ctx}: contract end precedes effectivity ({row.get('contract_effectivity_date')} → {row.get('contract_end_date')})",
        )

    return report


def _normalized_group_value(field_name: str, value: object) -> str:
    """Normalize a field value for within-group equality checks."""
    if is_null(value):
        return ""
    if field_name in ("contract_amount", "approved_budget", "item_budget", "quantity"):
        parsed, _ = parse_decimal(value)
        return "" if parsed is None else f"{parsed:g}"
    return str(value).strip().lower()


def _line_item_fingerprint(row: dict) -> tuple[str, ...]:
    return tuple(_normalized_group_value(f, row.get(f)) for f in LINE_ITEM_IDENTITY_FIELDS)


# Cap row lists embedded in sample payloads (webapp + .dq.json must stay small).
MAX_ROW_INDICES_IN_SAMPLE = 20
ROW_REF_PREVIEW = 5
MAX_RAW_ROW_KEYS_IN_SAMPLE = 30

SAMPLE_ROW_FIELDS = (
    "bid_reference_no",
    "solicitation_no",
    "award_reference_no",
    "procuring_entity",
    "notice_title",
    "bid_notice_status",
    "award_notice_status",
    "awardee_organization_name",
    "approved_budget",
    "item_budget",
    "contract_amount",
    "award_date",
    "published_date",
    "closing_date",
    "line_item_no",
    "item_name",
    "item_description",
    "procurement_mode",
)


def _trim_raw_row(raw_row: dict | None, *, max_keys: int = MAX_RAW_ROW_KEYS_IN_SAMPLE) -> dict | None:
    """Non-empty source columns for sample verification (capped)."""
    if not raw_row:
        return None
    out: dict[str, str] = {}
    for key, value in raw_row.items():
        if value is None:
            continue
        text = str(value).strip()
        if not text or text.upper() == "NULL":
            continue
        out[str(key)] = text
        if len(out) >= max_keys:
            break
    return out or None


def _build_sample_row_entry(
    issues: list[dict],
    canonical: dict | None = None,
    raw_row: dict | None = None,
) -> dict:
    """Compact canonical fields for verifying a DQ sample in the webapp."""
    entry: dict = {}
    issue_fields = [str(i.get("field") or "") for i in issues if i.get("field")]
    keys: list[str] = []
    for key in SAMPLE_ROW_FIELDS:
        if key not in keys:
            keys.append(key)
    for field in issue_fields:
        if field and field not in keys:
            keys.append(field)
    if canonical:
        for key in keys:
            value = canonical.get(key)
            if not is_null(value):
                entry[key] = _coerce_json(value)
    return entry


def _attach_sample_context(
    payload: dict,
    issues: list[dict],
    *,
    canonical: dict | None = None,
    raw_row: dict | None = None,
) -> dict:
    """Add row_entry / raw_row so samples are verifiable without opening the source file."""
    out = dict(payload)
    row_entry = _build_sample_row_entry(issues, canonical=canonical, raw_row=raw_row)
    if row_entry:
        out["row_entry"] = row_entry
    trimmed = _trim_raw_row(raw_row)
    if trimmed:
        out["raw_row"] = trimmed
    return out


def _sample_has_context(sample: dict) -> bool:
    return bool(sample.get("row_entry") or sample.get("raw_row"))


def merge_diverse_dq_samples(
    sample_lists: Iterable[list[dict]],
    *,
    cap: int = 100,
    per_rule_cap: int = 5,
) -> tuple[list[dict], int]:
    """Merge DQ sample lists, preferring rule coverage and row context for verification."""
    candidates: list[dict] = []
    for samples in sample_lists:
        for sample in samples or []:
            candidates.append(sample)

  # Newer transforms embed row_entry/raw_row; prefer those over legacy index-only samples.
    candidates.sort(key=lambda s: (0 if _sample_has_context(s) else 1))

    merged: list[dict] = []
    rule_counts: Counter[str] = Counter()
    total_seen = len(candidates)
    for sample in candidates:
        issues = sample.get("issues") or []
        rules = {str(i.get("rule") or "") for i in issues if i.get("rule")}
        if not rules:
            continue
        if any(rule_counts[rule] >= per_rule_cap for rule in rules):
            continue
        merged.append(sample)
        for rule in rules:
            rule_counts[rule] += 1
        if len(merged) >= cap:
            break
    return merged, max(0, total_seen - len(merged))


def _row_ref_text(indices: list[int], max_show: int = ROW_REF_PREVIEW) -> str:
    if len(indices) <= max_show:
        return str(indices)
    head = ", ".join(str(i) for i in indices[:max_show])
    return f"[{head}, … +{len(indices) - max_show} more]"


def _compact_sample_payload(payload: dict) -> dict:
    """Shrink group samples so a single entry cannot megabytes of row indices."""
    out = dict(payload)
    indices = out.get("row_indices")
    if isinstance(indices, list) and len(indices) > MAX_ROW_INDICES_IN_SAMPLE:
        out["row_indices_omitted"] = len(indices) - MAX_ROW_INDICES_IN_SAMPLE
        out["row_indices"] = indices[:MAX_ROW_INDICES_IN_SAMPLE]
    issues = out.get("issues")
    if isinstance(issues, list):
        compact_issues = []
        for iss in issues:
            if not isinstance(iss, dict):
                compact_issues.append(iss)
                continue
            ci = dict(iss)
            msg = str(ci.get("message") or "")
            if len(msg) > 400:
                ci["message"] = f"{msg[:400]}… (+{len(msg) - 400} chars, see .dq.json)"
            compact_issues.append(ci)
        out["issues"] = compact_issues
    return out


def validate_group(
    rows: list[tuple[int, dict]],
    *,
    award_reference_no: str,
) -> DataQualityReport:
    """Validate a group of rows sharing one award_reference_no.

    Catches process-level field conflicts (first-row-wins assumption) and
    repeated line_item_no values that mask distinct line items.
    """
    report = DataQualityReport()
    if len(rows) < 2:
        return report

    ctx = f"award {award_reference_no}"
    row_indices = [idx for idx, _ in rows]

    for field_name in AWARD_GROUP_CONFLICT_FIELDS:
        distinct: dict[str, list[int]] = {}
        for row_index, row in rows:
            norm = _normalized_group_value(field_name, row.get(field_name))
            if not norm:
                continue
            distinct.setdefault(norm, []).append(row_index)
        if len(distinct) > 1:
            report.warning(
                rule="group_field_conflict",
                field=field_name,
                value=sorted(distinct.keys()),
                message=(
                    f"{ctx}: `{field_name}` differs across rows "
                    f"{_row_ref_text(row_indices)} ({len(row_indices)} rows) — "
                    f"compiler uses first row only"
                ),
            )

    by_line_no: dict[str, list[tuple[int, dict]]] = {}
    for row_index, row in rows:
        line_no = str(row.get("line_item_no") or "1").strip()
        by_line_no.setdefault(line_no, []).append((row_index, row))

    for line_no, line_rows in by_line_no.items():
        if len(line_rows) < 2:
            continue
        fingerprints = {_line_item_fingerprint(row) for _, row in line_rows}
        if len(fingerprints) > 1:
            report.info(
                rule="duplicate_line_item_no",
                field="line_item_no",
                value=line_no,
                message=(
                    f"{ctx}: line_item_no `{line_no}` on "
                    f"{_row_ref_text([idx for idx, _ in line_rows])} "
                    f"({len(line_rows)} rows) with distinct item content — "
                    f"item ids will be disambiguated at compile time"
                ),
            )

    return report


def validate_process_group(
    rows: list[tuple[int, dict]],
    *,
    process_key: str,
) -> DataQualityReport:
    """Validate rows sharing one contracting process (bid-first grouping key).

    Checks process-level field consistency across all rows, then runs
    award-scoped ``validate_group()`` on each award_reference_no subgroup.
    """
    report = DataQualityReport()
    if len(rows) < 2:
        return report

    ctx = f"process {process_key}"
    row_indices = [idx for idx, _ in rows]

    for field_name in PROCESS_CONFLICT_FIELDS:
        distinct: dict[str, list[int]] = {}
        for row_index, row in rows:
            norm = _normalized_group_value(field_name, row.get(field_name))
            if not norm:
                continue
            distinct.setdefault(norm, []).append(row_index)
        if len(distinct) > 1:
            report.warning(
                rule="group_field_conflict",
                field=field_name,
                value=sorted(distinct.keys()),
                message=(
                    f"{ctx}: `{field_name}` differs across rows "
                    f"{_row_ref_text(row_indices)} ({len(row_indices)} rows) — "
                    f"compiler uses first row only"
                ),
            )

    by_award: dict[str, list[tuple[int, dict]]] = defaultdict(list)
    for row_index, row in rows:
        award_ref = row.get("award_reference_no")
        if is_null(award_ref) or str(award_ref).strip() in ("", "0"):
            continue
        by_award[str(award_ref).strip()].append((row_index, row))

    for award_ref, award_rows in by_award.items():
        if len(award_rows) >= 2:
            sub = validate_group(award_rows, award_reference_no=award_ref)
            report.issues.extend(sub.issues)

    return report


# ---------------------------------------------------------------------------
# Aggregate reporting across a full run
# ---------------------------------------------------------------------------


@dataclass
class RunReport:
    """Roll-up of per-row reports across a transform run, plus run metadata."""

    rows_seen: int = 0
    rows_committed: int = 0          # passed validation and got compiled
    rows_quarantined: int = 0        # had >= 1 error
    rows_excluded_no_award: int = 0
    rows_excluded_no_process_key: int = 0
    rows_grouped: int = 0
    process_group_count: int = 0
    per_row: list[tuple[int, DataQualityReport]] = field(default_factory=list)
    # Sample of quarantined rows kept for review (capped to avoid bloat).
    quarantined_samples: list[dict] = field(default_factory=list)
    quarantined_sample_cap: int = 50
    # Sample of warning-bearing rows/groups for iterative review.
    warning_samples: list[dict] = field(default_factory=list)
    warning_sample_cap: int = 100
    warning_sample_per_rule_cap: int = 5
    # Sample of info-level group findings (e.g. duplicate_line_item_no).
    info_samples: list[dict] = field(default_factory=list)
    info_sample_cap: int = 100
    info_sample_per_rule_cap: int = 5
    quarantined_samples_omitted: int = 0
    warning_samples_omitted: int = 0
    info_samples_omitted: int = 0
    group_validations: list[tuple[str, list[int], DataQualityReport]] = field(
        default_factory=list
    )
    package_warnings: list[dict] = field(default_factory=list)

    def add_package_warning(self, rule: str, message: str, payload: dict) -> None:
        """Record a package-level warning (e.g. display id collision after compile)."""
        self.package_warnings.append({
            "rule": rule,
            "severity": "warning",
            "message": message,
            **payload,
        })
        if len(self.warning_samples) >= self.warning_sample_cap:
            self.warning_samples_omitted += 1
            return
        self.warning_samples.append({
            **{k: v for k, v in payload.items() if k not in ("rule", "severity", "message")},
            "issues": [{
                "rule": rule,
                "severity": "warning",
                "field": "ocid",
                "value": payload.get("original_id"),
                "message": message,
            }],
        })

    def _issue_dicts(self, report: DataQualityReport) -> list[dict]:
        return [
            {"rule": i.rule, "severity": i.severity, "field": i.field,
             "value": _coerce_json(i.value), "message": i.message}
            for i in report.issues
        ]

    def _warning_rule_count(self, rule: str) -> int:
        return sum(
            1
            for sample in self.warning_samples
            if any(issue["rule"] == rule for issue in sample["issues"])
        )

    def _info_rule_count(self, rule: str) -> int:
        return sum(
            1
            for sample in self.info_samples
            if any(issue["rule"] == rule for issue in sample["issues"])
        )

    def _maybe_add_warning_sample(
        self,
        payload: dict,
        report: DataQualityReport,
        *,
        canonical: dict | None = None,
        raw_row: dict | None = None,
        priority: bool = False,
    ) -> None:
        if len(self.warning_samples) >= self.warning_sample_cap:
            self.warning_samples_omitted += 1
            return
        warning_issues = [
            issue for issue in self._issue_dicts(report)
            if issue["severity"] == "warning"
        ]
        if not warning_issues:
            return
        compact = _compact_sample_payload(
            _attach_sample_context(payload, warning_issues, canonical=canonical, raw_row=raw_row)
        )
        if priority:
            self.warning_samples.insert(0, {**compact, "issues": warning_issues})
            if len(self.warning_samples) > self.warning_sample_cap:
                self.warning_samples.pop()
            return
        filtered = [
            issue for issue in warning_issues
            if self._warning_rule_count(issue["rule"]) < self.warning_sample_per_rule_cap
        ]
        if filtered:
            contextual = _attach_sample_context(payload, filtered, canonical=canonical, raw_row=raw_row)
            self.warning_samples.append({**_compact_sample_payload(contextual), "issues": filtered})

    def _maybe_add_info_sample(
        self,
        payload: dict,
        report: DataQualityReport,
        *,
        canonical: dict | None = None,
        raw_row: dict | None = None,
        priority: bool = False,
    ) -> None:
        if len(self.info_samples) >= self.info_sample_cap:
            self.info_samples_omitted += 1
            return
        info_issues = [
            issue for issue in self._issue_dicts(report)
            if issue["severity"] == "info"
        ]
        if not info_issues:
            return
        if priority:
            contextual = _attach_sample_context(payload, info_issues, canonical=canonical, raw_row=raw_row)
            self.info_samples.insert(0, {**_compact_sample_payload(contextual), "issues": info_issues})
            if len(self.info_samples) > self.info_sample_cap:
                self.info_samples.pop()
            return
        filtered = [
            issue for issue in info_issues
            if self._info_rule_count(issue["rule"]) < self.info_sample_per_rule_cap
        ]
        if filtered:
            contextual = _attach_sample_context(payload, filtered, canonical=canonical, raw_row=raw_row)
            self.info_samples.append({**_compact_sample_payload(contextual), "issues": filtered})

    def add(
        self,
        row_index: int,
        report: DataQualityReport,
        *,
        canonical: dict | None = None,
        raw_row: dict | None = None,
    ) -> None:
        self.per_row.append((row_index, report))
        self.rows_seen += 1
        if report.fatal:
            self.rows_quarantined += 1
            if len(self.quarantined_samples) < self.quarantined_sample_cap:
                issues = self._issue_dicts(report)
                payload = _attach_sample_context(
                    {"row_index": row_index},
                    issues,
                    canonical=canonical,
                    raw_row=raw_row,
                )
                self.quarantined_samples.append({
                    **_compact_sample_payload(payload),
                    "issues": issues,
                })
            else:
                self.quarantined_samples_omitted += 1
        else:
            self.rows_committed += 1
            self._maybe_add_warning_sample(
                {"row_index": row_index},
                report,
                canonical=canonical,
                raw_row=raw_row,
            )
            self._maybe_add_info_sample(
                {"row_index": row_index},
                report,
                canonical=canonical,
                raw_row=raw_row,
            )

    def add_group(
        self,
        group_key: str,
        row_indices: list[int],
        report: DataQualityReport,
        *,
        canonical: dict | None = None,
        raw_row: dict | None = None,
    ) -> None:
        if not report.issues:
            return
        self.group_validations.append((group_key, row_indices, report))
        payload = {
            "group_key": group_key,
            "award_reference_no": group_key,
            "row_indices": row_indices,
        }
        self._maybe_add_warning_sample(
            payload,
            report,
            canonical=canonical,
            raw_row=raw_row,
            priority=True,
        )
        self._maybe_add_info_sample(
            payload,
            report,
            canonical=canonical,
            raw_row=raw_row,
            priority=True,
        )

    def _all_reports(self) -> Iterable[DataQualityReport]:
        for _, report in self.per_row:
            yield report
        for _, _, report in self.group_validations:
            yield report

    def severity_counts(self) -> dict[str, int]:
        c: Counter[str] = Counter()
        for report in self._all_reports():
            c["error"] += report.error_count
            c["warning"] += report.warning_count
            c["info"] += report.info_count
        c["warning"] += len(self.package_warnings)
        return dict(c)

    def rule_counts(self) -> list[dict]:
        """Top rules by occurrence, for the webapp's data-quality panel."""
        c: Counter[str] = Counter()
        severity_by_rule: dict[str, str] = {}
        for report in self._all_reports():
            for issue in report:
                c[issue.rule] += 1
                severity_by_rule[issue.rule] = issue.severity
        for warning in self.package_warnings:
            rule = str(warning.get("rule") or "package_warning")
            c[rule] += 1
            severity_by_rule[rule] = str(warning.get("severity") or "warning")
        return [
            {"rule": rule, "severity": severity_by_rule[rule], "count": count}
            for rule, count in c.most_common()
        ]

    def issue_group_counts(self) -> list[dict]:
        """Per (rule, field, message-pattern) totals for nested DQ sample trees."""
        c: Counter[tuple[str, str, str, str]] = Counter()
        for report in self._all_reports():
            for issue in report:
                pattern = issue_message_pattern(issue.message)
                c[(issue.rule, issue.severity, issue.field, pattern)] += 1
        for warning in self.package_warnings:
            rule = str(warning.get("rule") or "package_warning")
            msg = str(warning.get("message") or "")
            field = str(warning.get("field") or "ocid")
            pattern = issue_message_pattern(msg)
            c[(rule, "warning", field, pattern)] += 1
        return [
            {
                "rule": rule,
                "severity": severity,
                "field": field,
                "pattern": pattern,
                "count": count,
            }
            for (rule, severity, field, pattern), count in c.most_common()
        ]

    def compile_accounting_dict(self, *, releases_compiled: int | None = None) -> dict:
        releases = (
            int(releases_compiled)
            if releases_compiled is not None
            else self.process_group_count
        )
        return {
            "rows_excluded_no_award": self.rows_excluded_no_award,
            "rows_excluded_no_process_key": self.rows_excluded_no_process_key,
            "rows_grouped": self.rows_grouped,
            "process_group_count": self.process_group_count,
            "rows_merged_into_groups": max(0, self.rows_grouped - self.process_group_count),
            "releases_compiled": releases,
        }

    def to_dict(self) -> dict:
        sc = self.severity_counts()
        return {
            "rows_seen": self.rows_seen,
            "rows_committed": self.rows_committed,
            "rows_quarantined": self.rows_quarantined,
            "compile_accounting": self.compile_accounting_dict(),
            "severity_counts": sc,
            "rule_counts": self.rule_counts(),
            "issue_group_counts": self.issue_group_counts(),
            "quarantined_samples": self.quarantined_samples,
            "quarantined_samples_omitted": self.quarantined_samples_omitted,
            "warning_samples": self.warning_samples,
            "warning_samples_omitted": self.warning_samples_omitted,
            "info_samples": self.info_samples,
            "info_samples_omitted": self.info_samples_omitted,
            "display_id_collisions": self.package_warnings,
        }


def _coerce_json(value: object) -> object:
    """Best-effort conversion for JSON serialization (fallback to str)."""
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    return str(value)
