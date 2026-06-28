"""General-purpose canonical→OCDS compiler.

Compiles a single canonical PhilGEPS row into an OCDS 1.1 compiled release by
walking the staging rules in config/canonical_to_ocds.yaml. Unlike the sample
builder in build_schema_field_map.py, this is row-driven: pass it any
canonicalized row (one that has already passed the data-quality gate) and it
returns a release object.

Reuse philosophy:
  - Staging rules come from canonical_to_ocds.yaml (single source of truth).
  - Codelist transforms come from ocds_codelist_mappings.yaml.
  - Value parsing (dates, decimals, NULL handling) comes from _data_quality.
  - Currency injection reuses the same algorithm as the sample builder.

OCDS structural shape:
  - One release per contracting process (grouped by bid_reference_no when
    present, else award_reference_no). Multiple awards under one bid become
    awards[]/contracts[] entries; line items merge into tender.items[].
  - Releases are wrapped into a package by the caller; this module only
    produces releases.

Safety:
  - Every value is parsed through _data_quality before assignment, so NULLs
    and malformed inputs become missing keys (not garbage) in the release.
  - Returned releases are NOT pre-validated against the OCDS schema; the
    caller is expected to run scripts/_ocds_checks.assert_release_package
    on the final package.
"""

from __future__ import annotations

import re
from typing import Any, Iterable

from _data_quality import (
    is_null,
    parse_date,
    parse_decimal,
    parse_int,
    PHILGEPS_TZ,
)


_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(value: str) -> str:
    """OCDS-safe slug for OCID fragments and party IDs (lowercase, ascii, dash-separated)."""
    text = _SLUG_RE.sub("-", str(value).strip().lower())
    return text.strip("-") or "unknown"


def _valid_ref(value: object) -> str | None:
    """Return a trimmed reference string, or None if missing/placeholder."""
    if is_null(value):
        return None
    text = str(value).strip()
    if text in ("", "0"):
        return None
    return text


def _process_identity(row: dict) -> tuple[str, str] | None:
    """Return ``(group_key, display_id)`` for one contracting process row.

    Grouping always prefers ``bid_reference_no`` when valid — it is the stable
    process key in PhilGEPS (Reference ID / Bid Reference No.). Solicitation
    numbers are **not** safe for grouping: the same label can repeat across
    unrelated bids (e.g. S3 ``2021-001`` → 62 distinct bid refs in a sample).

    ``display_id`` (release ``id`` / OCID slug) prefers ``bid_reference_no``,
    then ``solicitation_no``, then ``award_reference_no``. Human-readable
    solicitation stays on ``philgeps.solicitationNo`` / ``tender`` metadata.
    If two releases would share the same ``(ocid, id)``, the package compiler
    applies a composite display id and flags ``display_id_collision``.
    """
    bid = _valid_ref(row.get("bid_reference_no"))
    sol = _valid_ref(row.get("solicitation_no"))
    award = _valid_ref(row.get("award_reference_no"))

    if bid:
        group_key = f"bid:{bid}"
    elif sol:
        group_key = f"sol:{sol}"
    elif award:
        group_key = f"award:{award}"
    else:
        return None

    if bid:
        display_id = bid
    elif sol:
        display_id = sol
    else:
        display_id = award  # type: ignore[assignment]

    return group_key, display_id


def process_group_key(row: dict) -> str | None:
    """Stable grouping key for one contracting process (solicitation/bid/award)."""
    ident = _process_identity(row)
    return ident[0] if ident else None


def _process_ocid_and_id(rows: list[dict], ocds_cfg: dict) -> tuple[str, str] | None:
    """Derive (ocid, release_id) for a process group."""
    ocid_prefix = ocds_cfg.get("ocid_prefix", "ocds-philgeps")
    for row in rows:
        ident = _process_identity(row)
        if ident:
            _, display_id = ident
            return f"{ocid_prefix}-{_slugify(display_id)}", display_id
    return None


def _row_from_release(release: dict) -> dict:
    """Recover canonical identity fields from a compiled release."""
    tender = release.get("tender") or {}
    philgeps = release.get("philgeps") or {}
    awards = release.get("awards") or []
    return {
        "bid_reference_no": tender.get("id"),
        "solicitation_no": philgeps.get("solicitationNo"),
        "award_reference_no": awards[0].get("id") if awards else None,
    }


def _composite_display_id(row: dict) -> str:
    """Build a composite public id when the default display id collides."""
    bid = _valid_ref(row.get("bid_reference_no"))
    sol = _valid_ref(row.get("solicitation_no"))
    award = _valid_ref(row.get("award_reference_no"))
    if bid and sol:
        return f"{bid}-{sol}"
    if bid and award:
        return f"{bid}-{award}"
    if sol and award:
        return f"{sol}-{award}"
    return bid or sol or award or "unknown"


def resolve_release_display_collisions(
    releases: list[dict],
    *,
    ocid_prefix: str = "ocds-philgeps",
) -> list[dict]:
    """Ensure unique ``(ocid, id)`` pairs within a package.

    Default display ids come from ``bid_reference_no`` (then solicitation, then
    award). When duplicates remain, rewrite colliding releases to a composite
    display id and return event records for DQ / reporting.
    """
    from collections import defaultdict

    by_pair: dict[tuple[str | None, str | None], list[int]] = defaultdict(list)
    for idx, release in enumerate(releases):
        by_pair[(release.get("ocid"), release.get("id"))].append(idx)

    dup_groups = [indices for indices in by_pair.values() if len(indices) > 1]
    if not dup_groups:
        return []

    events: list[dict] = []
    used_pairs: set[tuple[str, str]] = {
        pair  # type: ignore[misc]
        for pair, indices in by_pair.items()
        if len(indices) == 1 and pair[0] and pair[1]
    }

    for indices in dup_groups:
        for idx in indices:
            release = releases[idx]
            original_ocid = release.get("ocid")
            original_id = release.get("id")
            row = _row_from_release(release)
            new_id = _composite_display_id(row)
            new_ocid = f"{ocid_prefix}-{_slugify(new_id)}"
            suffix = 2
            while (new_ocid, new_id) in used_pairs:
                new_id = f"{_composite_display_id(row)}-{suffix}"
                new_ocid = f"{ocid_prefix}-{_slugify(new_id)}"
                suffix += 1

            events.append(
                {
                    "original_ocid": original_ocid,
                    "original_id": original_id,
                    "resolved_ocid": new_ocid,
                    "resolved_id": new_id,
                    "bid_reference_no": row.get("bid_reference_no"),
                    "solicitation_no": row.get("solicitation_no"),
                }
            )
            release["ocid"] = new_ocid
            release["id"] = new_id
            used_pairs.add((new_ocid, new_id))

    return events


def _supplier_id(row: dict) -> str:
    """Stable party id for an awardee. Prefer explicit ID, fall back to slugified name."""
    explicit = row.get("awardee_org_id")
    if not is_null(explicit):
        return str(explicit)
    name = row.get("awardee_organization_name")
    return _slugify(str(name)) if not is_null(name) else "unknown-supplier"


def _buyer_id(row: dict) -> str:
    """Stable party id for a buyer. Prefer UACS code, fall back to slugified name."""
    explicit = row.get("pe_uacs_code")
    if not is_null(explicit):
        return str(explicit)
    name = row.get("procuring_entity")
    return _slugify(str(name)) if not is_null(name) else "unknown-buyer"


def _collect_suppliers(
    row: dict,
    field_types: dict[str, str],
) -> list[tuple[str, str]]:
    """Primary awardee plus JV partners as (id, name) pairs, deduped by id."""
    suppliers: list[tuple[str, str]] = []
    seen_ids: set[str] = set()

    primary_name = row.get("awardee_organization_name")
    primary_id = _supplier_id(row)
    if not is_null(primary_name):
        suppliers.append((primary_id, str(primary_name).strip()))
        seen_ids.add(primary_id)

    jv_names = _coerce_value(
        "awardee_joint_venture", row.get("awardee_joint_venture"), field_types
    ) or []
    for partner in jv_names:
        if is_null(partner):
            continue
        name = str(partner).strip()
        partner_id = _slugify(name)
        if partner_id in seen_ids:
            continue
        suppliers.append((partner_id, name))
        seen_ids.add(partner_id)

    return suppliers


def _set_nested(target: dict, dotted_path: str, value: object) -> None:
    """Assign value into target at dotted/slash path, creating dicts as needed."""
    cursor = target
    parts = dotted_path.replace(".", "/").split("/")
    for part in parts[:-1]:
        nxt = cursor.setdefault(part, {})
        if not isinstance(nxt, dict):
            return
        cursor = nxt
    cursor[parts[-1]] = value


def _parse_string_array(raw: object) -> list[str]:
    """Split PhilGEPS list fields (bidders, JV partners) on comma or semicolon."""
    if isinstance(raw, list):
        return [s.strip() for s in raw if s and not is_null(s)]
    if is_null(raw):
        return []
    parts = re.split(r"[;,]", str(raw))
    return [s.strip() for s in parts if s.strip() and not is_null(s.strip())]


def _coerce_value(canonical: str, raw: object, field_types: dict[str, str]) -> object:
    """Parse `raw` according to the canonical field's declared type.

    Returns the typed value, or None if the input is missing/unparseable.
    """
    if is_null(raw):
        return None
    ftype = field_types.get(canonical)

    if ftype == "decimal":
        v, _ = parse_decimal(raw)
        return v
    if ftype == "integer":
        v, _ = parse_int(raw)
        return v
    if ftype in ("date", "datetime"):
        v, _ = parse_date(raw)
        return v
    if ftype == "string_array":
        return _parse_string_array(raw)
    # Default: string, stripped.
    return str(raw).strip()


def _inject_currency(node: object, currency: str) -> None:
    """Walk a release subtree and add `currency` next to every numeric `amount`.

    Skips nodes where `amount` is itself a dict (already wrapped by the
    staging-time currency application). This prevents the double-nesting bug
    where `value/amount` paths get wrapped again at injection time.
    """
    if isinstance(node, dict):
        amount = node.get("amount")
        if (
            isinstance(amount, (int, float))
            and not isinstance(amount, bool)
            and "currency" not in node
        ):
            node["currency"] = currency
        for v in node.values():
            _inject_currency(v, currency)
    elif isinstance(node, list):
        for item in node:
            _inject_currency(item, currency)


def _codelist_transform(canonical: str, value: object, codelists: dict) -> object:
    """Translate PhilGEPS labels to OCDS codes. Passes through unmapped values."""
    if value is None:
        return None
    table_map = {
        "procurement_mode": "procurement_method",
        "classification": "main_procurement_category",
        "bid_notice_status": "tender_status",
        "award_notice_status": "award_status",
    }
    table = table_map.get(canonical)
    if not table:
        return value
    mapping = codelists.get(table, {})
    return mapping.get(value, value)


def _stage_block(
    block_name: str,
    ocds_cfg: dict,
    row: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict:
    """Walk staging rules for one OCDS block (tender, awards, etc.) and return a dict."""
    out: dict = {}
    defaults = codelists.get("defaults", {})
    currency = defaults.get("currency", "PHP")

    for path, canonical in ocds_cfg.get(block_name, {}).items():
        if not isinstance(canonical, str):
            continue

        # Compiler-emitted constants (prefixed with _ in the YAML).
        if canonical == "_default_currency":
            _set_nested(out, path, currency)
            continue
        if canonical == "_default_classification_scheme":
            _set_nested(out, path, defaults.get("classification_scheme", "UNSPSC"))
            continue
        if canonical == "_default_bid_status":
            _set_nested(out, path, codelists.get("bid_status_default", "valid"))
            continue

        raw_value = row.get(canonical)
        typed = _coerce_value(canonical, raw_value, field_types)
        if typed is None:
            continue
        transformed = _codelist_transform(canonical, typed, codelists)
        if transformed is None or transformed == "":
            continue

        # Monetary amount paths: write the raw number; _inject_currency walks the
        # final tree and adds a sibling `currency` field. This avoids the
        # double-nesting bug where wrapping here would create value.amount.amount.
        _set_nested(out, path, transformed)
    return out


def _release_date_from_rows(rows: list[dict]) -> str:
    """Latest parseable release date across process rows."""
    best: str | None = None
    for row in rows:
        for candidate in ("award_published_date", "published_date", "award_date"):
            parsed, _ = parse_date(row.get(candidate))
            if parsed and (best is None or parsed > best):
                best = parsed
    return best or ""


def _compile_items_from_rows(rows: list[dict], field_types: dict[str, str]) -> list[dict]:
    """Build disambiguated OCDS line items from canonical rows."""
    items: list[dict] = []
    seen_item_ids: set[str] = set()
    for idx, row in enumerate(rows):
        item = _line_item_from_row(row, field_types)
        if not item:
            continue
        base_id = str(row.get("line_item_no") or (idx + 1)).strip()
        item_id = base_id
        if item_id in seen_item_ids:
            item_id = f"{base_id}-{idx + 1}"
        seen_item_ids.add(item_id)
        item["id"] = item_id
        items.append(item)
    return items


def _compile_award_block(
    row: dict,
    award_items: list[dict],
    *,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict:
    """Build one OCDS award object from a canonical row."""
    award = _stage_block("awards", ocds_cfg, row, field_types, codelists)
    award.pop("items", None)
    award.pop("suppliers", None)
    if award_items:
        award["items"] = award_items
    suppliers_refs = [
        {"id": supplier_id, "name": supplier_name}
        for supplier_id, supplier_name in _collect_suppliers(row, field_types)
    ]
    if suppliers_refs:
        award["suppliers"] = suppliers_refs
    return award


def _compile_contract_block(
    row: dict,
    *,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict:
    return _stage_block("contracts", ocds_cfg, row, field_types, codelists)


def _add_parties(release: dict, rows: list[dict], field_types: dict[str, str]) -> None:
    """Merge buyer and supplier parties from all rows in a process."""
    parties: list[dict] = []
    party_index: dict[str, dict] = {}

    def _add_party(party_id: str, name: str, roles: list[str]) -> None:
        existing = party_index.get(party_id)
        if existing is None:
            party = {"id": party_id, "name": name, "roles": list(roles)}
            parties.append(party)
            party_index[party_id] = party
        else:
            for role in roles:
                if role not in existing["roles"]:
                    existing["roles"].append(role)

    for row in rows:
        if not is_null(row.get("procuring_entity")):
            _add_party(
                _buyer_id(row),
                str(row["procuring_entity"]).strip(),
                ["buyer", "procuringEntity"],
            )
        for supplier_id, supplier_name in _collect_suppliers(row, field_types):
            _add_party(supplier_id, supplier_name, ["supplier", "payee", "tenderer"])
    if parties:
        release["parties"] = parties


def _compile_bids_block(
    row: dict,
    ocid: str,
    *,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict | None:
    bids_cfg = ocds_cfg.get("bids", {})
    bidders = row.get("bidders") or row.get("list_of_bidders")
    if not bids_cfg or is_null(bidders):
        return None
    bidders_list = _coerce_value("bidders", bidders, field_types) or []
    if not bidders_list:
        return None
    details = []
    for name in bidders_list:
        details.append({
            "id": f"{ocid}-bid-{len(details) + 1}",
            "tenderers": [{"id": _slugify(name), "name": name}],
            "status": codelists.get("bid_status_default", "valid"),
        })
    return {"details": details}


def _compile_philgeps_extension(row: dict, ocds_cfg: dict, field_types: dict[str, str]) -> dict:
    ext_payload: dict = {}
    for ext_key, canonical in ocds_cfg.get("philgeps_extension", {}).items():
        if not isinstance(canonical, str):
            continue
        typed = _coerce_value(canonical, row.get(canonical), field_types)
        if typed is not None:
            ext_payload[ext_key] = typed
    return ext_payload


def compile_release(
    row: dict,
    *,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict | None:
    """Compile one canonical row into an OCDS 1.1 compiled release.

    Returns None if the row lacks the minimum identity to anchor a release
    (missing/placeholder award_reference_no). The caller's DQ gate already
    flagged these as errors; returning None here keeps the compiler defensive.
    """
    if _valid_ref(row.get("award_reference_no")) is None:
        return None
    return compile_grouped([row], ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists)


def _release_shell(
    anchor: dict,
    rows: list[dict],
    *,
    ocid: str,
    release_id: str,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict:
    """Build the process-level release envelope (tender shell, planning, buyer, bids)."""
    defaults = codelists.get("defaults", {})
    currency = defaults.get("currency", "PHP")
    initiation = defaults.get("initiation_type", "tender")
    tag = defaults.get("tag", ["compiled"])

    release: dict[str, Any] = {
        "ocid": ocid,
        "id": release_id,
        "date": _release_date_from_rows(rows),
        "initiationType": initiation,
        "tag": tag,
        "language": "en",
    }

    def stage(name: str) -> dict:
        return _stage_block(name, ocds_cfg, anchor, field_types, codelists)

    planning_triggers = ocds_cfg.get("planning_triggers", [])
    if any(not is_null(r.get(t)) for r in rows for t in planning_triggers):
        planning = stage("planning")
        if planning:
            release["planning"] = planning

    buyer = stage("buyer")
    if buyer:
        release["buyer"] = buyer

    tender = stage("tender")
    if tender:
        tender.pop("items", None)
        release["tender"] = tender

    bids = _compile_bids_block(
        anchor, ocid, ocds_cfg=ocds_cfg, field_types=field_types, codelists=codelists,
    )
    if bids:
        release["bids"] = bids

    ext_payload = _compile_philgeps_extension(anchor, ocds_cfg, field_types)
    if ext_payload:
        release["philgeps"] = ext_payload

    _add_parties(release, rows, field_types)
    _inject_currency(release, currency)
    return release


# ---------------------------------------------------------------------------
# Grouped compilation: collapse N rows of the same contracting process
# ---------------------------------------------------------------------------


def _line_item_from_row(row: dict, field_types: dict[str, str]) -> dict | None:
    """Build a single OCDS line item from one canonical row.

    Returns None if the row has no item name/description to anchor an item.
    """
    name = row.get("item_name")
    desc = row.get("item_description")
    if is_null(name) and is_null(desc):
        return None

    qty, _ = parse_decimal(row.get("quantity"))
    budget, _ = parse_decimal(row.get("item_budget"))

    item: dict[str, Any] = {
        "id": str(row.get("line_item_no") or 1),
    }
    if not is_null(desc):
        item["description"] = str(desc).strip()
    if not is_null(name):
        item["name"] = str(name).strip()
    if qty is not None:
        item["quantity"] = qty
    if not is_null(row.get("uom")):
        item["unit"] = {"name": str(row.get("uom")).strip()}
        if budget is not None:
            item["unit"]["value"] = {"amount": budget}

    unspsc_code = row.get("unspsc_code")
    unspsc_desc = row.get("unspsc_description")
    if not is_null(unspsc_code):
        item["classification"] = {
            "scheme": "UNSPSC",
            "id": str(unspsc_code).strip(),
        }
        if not is_null(unspsc_desc):
            item["classification"]["description"] = str(unspsc_desc).strip()
    return item


def compile_grouped(
    rows: Iterable[dict],
    *,
    ocds_cfg: dict,
    field_types: dict[str, str],
    codelists: dict,
) -> dict | None:
    """Compile N rows of the same contracting process into one release.

    Rows share a bid_reference_no when present (one OCDS contracting process);
    otherwise they fall back to a single award_reference_no (legacy S3/S4 rows
    with bid ref ``0``). Multiple distinct awards under one bid become separate
    ``awards[]`` / ``contracts[]`` entries; all line items merge into
    ``tender.items[]``.
    """
    rows_list = list(rows)
    if not rows_list:
        return None

    awarded_rows = [r for r in rows_list if _valid_ref(r.get("award_reference_no"))]
    if not awarded_rows:
        return None

    ids = _process_ocid_and_id(rows_list, ocds_cfg)
    if ids is None:
        return None
    ocid, release_id = ids

    anchor = next(
        (r for r in rows_list if _process_identity(r)),
        awarded_rows[0],
    )

    release = _release_shell(
        anchor,
        rows_list,
        ocid=ocid,
        release_id=release_id,
        ocds_cfg=ocds_cfg,
        field_types=field_types,
        codelists=codelists,
    )

    tender_items = _compile_items_from_rows(rows_list, field_types)
    if tender_items:
        tender = release.setdefault("tender", {})
        tender["items"] = tender_items

    by_award: dict[str, list[dict]] = {}
    for row in awarded_rows:
        award_ref = _valid_ref(row.get("award_reference_no"))
        assert award_ref is not None
        by_award.setdefault(award_ref, []).append(row)

    awards: list[dict] = []
    contracts: list[dict] = []
    for award_ref in sorted(by_award):
        award_rows = by_award[award_ref]
        award_anchor = award_rows[0]
        award_items = _compile_items_from_rows(award_rows, field_types)
        awards.append(
            _compile_award_block(
                award_anchor,
                award_items,
                ocds_cfg=ocds_cfg,
                field_types=field_types,
                codelists=codelists,
            )
        )
        contract = _compile_contract_block(
            award_anchor,
            ocds_cfg=ocds_cfg,
            field_types=field_types,
            codelists=codelists,
        )
        if contract:
            contracts.append(contract)

    if awards:
        release["awards"] = awards
    if contracts:
        release["contracts"] = contracts

    currency = codelists.get("defaults", {}).get("currency", "PHP")
    _inject_currency(release, currency)
    return release
