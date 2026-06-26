#!/usr/bin/env python3
"""Build PHILGEPS_CANONICAL_FIELD_MAP.json and refresh crosswalk Canonical_AI column."""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "references"

SCHEMA_ANALYSIS = REFS / "PHILGEPS_SCHEMA_ANALYSIS.json"
SCHEMA_MAPPINGS = ROOT / "config" / "schema_mappings.yaml"
CANONICAL_TO_OCDS = ROOT / "config" / "canonical_to_ocds.yaml"
CODELIST_MAPPINGS = ROOT / "config" / "ocds_codelist_mappings.yaml"
CROSSWALK_MD = REFS / "PHILGEPS_OCDS_CSV_CROSSWALK.md"
FIELD_MAP_JSON = REFS / "PHILGEPS_CANONICAL_FIELD_MAP.json"
APP_BUNDLE_JSON = ROOT / "app" / "src" / "data" / "schema_bundle.json"
SAMPLE_RELEASE_JSON = REFS / "SAMPLE_OCDS_RELEASE_PACKAGE.json"

OPEN_SCHEMA_KEYS = [
    ("schema_1", "S1", "2000-2015 XLSX"),
    ("schema_2", "S2", "2016-2020 XLSX"),
    ("schema_3", "S3", "2021-2024 CSV (V1)"),
    ("schema_4", "S4", "2025 CSV (V2)"),
    ("schema_5", "S5", "2021-2024-V2 CSV"),
]

SCHEMA_KEY_ALIASES = {
    "schema_1_2_2000_2020": "schema_1",
    "schema_3_2021_2024": "schema_3",
    "schema_4_5_2025_v2": "schema_4",
}

# Explicit OCDS path → canonical field (or special rule key).
OCDS_CANONICAL: dict[str, str | tuple[str, ...]] = {
    "awards/contractPeriod/endDate": "contract_end_date",
    "awards/contractPeriod/startDate": "contract_effectivity_date",
    "awards/date": "award_date",
    "awards/description": "item_description",
    "awards/id": "award_reference_no",
    "awards/items/description": "item_description",
    "awards/items/id": "award_reference_no",
    "awards/items/unit/name": "uom",
    "awards/items/unit/value/amount": "item_budget",
    "awards/status": "award_notice_status",
    "awards/suppliers/name": "awardee_organization_name",
    "awards/title": "award_title",
    "awards/value/amount": "contract_amount",
    "buyer/name": "procuring_entity",
    "contracts/awardID": "award_reference_no",
    "contracts/dateSigned": "award_date",
    "contracts/description": "item_description",
    "contracts/implementation/transactions/payee/name": "awardee_organization_name",
    "contracts/implementation/transactions/payer/name": "procuring_entity",
    "contracts/items/description": "item_name",
    "contracts/items/id": "line_item_no",
    "contracts/items/quantity": "quantity",
    "contracts/items/unit/value/amount": "item_budget",
    "contracts/period/endDate": "contract_end_date",
    "contracts/period/startDate": "contract_effectivity_date",
    "contracts/status": "award_notice_status",
    "contracts/title": "award_title",
    "contracts/value/amount": "contract_amount",
    "parties/address/countryName": "awardee_country",
    "parties/details": "pe_organization_type",
    "parties/identifier/legalName": "procuring_entity",
    "planning/budget/amount/amount": "approved_budget",
    "planning/budget/description": "funding_source",
    "planning/budget/project": "notice_title",
    "relatedProcesses/id": "bid_reference_no",
    "relatedProcesses/title": "notice_title",
    "tender/additionalProcurementCategories": "business_category",
    "tender/awardPeriod/startDate": "award_published_date",
    "tender/contractPeriod/endDate": "contract_end_date",
    "tender/contractPeriod/startDate": "contract_effectivity_date",
    "tender/enquiryPeriod/endDate": "closing_date",
    "tender/enquiryPeriod/startDate": "published_date",
    "tender/id": "bid_reference_no",
    "tender/items/additionalClassifications/description": "unspsc_description",
    "tender/items/additionalClassifications/id": "unspsc_code",
    "tender/items/classification/description": "classification",
    "tender/items/description": "item_description",
    "tender/items/id": "line_item_no",
    "tender/items/unit/name": "uom",
    "tender/items/unit/value/amount": "item_budget",
    "tender/mainProcurementCategory": "classification",
    "tender/procurementMethod": "procurement_mode",
    "tender/procuringEntity/name": "procuring_entity",
    "tender/status": "bid_notice_status",
    "tender/tenderPeriod/endDate": "closing_date",
    "tender/tenderPeriod/startDate": "published_date",
    "tender/value/amount": "approved_budget",
}

# Rows whose Canonical column cannot be inferred from schema_mappings alone.
CANONICAL_AI_OVERRIDES: dict[str, str] = {
    "awards/description": "S1–S5: Item Description → item_description (line-item scope)",
    "awards/documents/dateModified": "omit (documents not in open CSV)",
    "awards/documents/datePublished": "omit (documents not in open CSV)",
    "awards/documents/description": "omit",
    "awards/documents/id": "omit",
    "awards/items/id": "S1–S3: Award No. · S4–S5: Award Reference No. → award_reference_no (award-level id; use line_item_no for item rows)",
    "awards/suppliers/id": "derived: slug(awardee_organization_name)",
    "buyer/id": "derived: slug(procuring_entity)",
    "contracts/documents/dateModified": "omit",
    "contracts/documents/datePublished": "omit",
    "contracts/documents/id": "omit",
    "contracts/documents/title": "omit",
    "contracts/implementation/transactions/payee/id": "derived: slug(awardee_organization_name)",
    "contracts/implementation/transactions/payer/id": "derived: slug(procuring_entity)",
    "parties/address/locality": "S4–S5: Province → pe_province · S4–S5: Province of Awardee → awardee_province",
    "parties/address/region": "S4–S5: Region → pe_region · S4–S5: Region of Awardee → awardee_region",
    "parties/address/postalCode": "omit",
    "parties/address/streetAddress": "omit",
    "parties/contactPoint/email": "omit (privacy / not in CSV)",
    "parties/contactPoint/faxNumber": "omit",
    "parties/contactPoint/telephone": "omit",
    "parties/contactPoint/url": "omit",
    "parties/contactPoint/name": "omit (privacy excluded; S3 had Created By / Awardee Contact Person)",
    "parties/roles": "omit",
    "relatedProcesses/id": "S1–S2: Reference ID · S3–S5: Bid Reference No. → bid_reference_no (S3 fallback: Solicitation No. if 0)",
    "relatedProcesses/relationship": "constant: parent",
    "tender/amendments/date": "omit",
    "tender/amendments/description": "omit",
    "tender/amendments/id": "omit",
    "tender/amendments/rationale": "omit",
    "tender/awardCriteriaDetails": "S1–S3: Reason for Award → reason_for_award [extension]",
    "tender/awardPeriod/durationInDays": "derive: S1–S5 Contract Duration + Calendar Type → contract_duration",
    "tender/awardPeriod/startDate": "S1–S2: Publish Date(Award) · S3–S5: Published Date(Award) → award_published_date",
    "tender/description": "omit (use notice_title or item_description)",
    "tender/documents/dateModified": "omit",
    "tender/documents/datePublished": "omit",
    "tender/documents/documentType": "omit",
    "tender/documents/format": "omit",
    "tender/documents/id": "omit",
    "tender/documents/title": "omit",
    "tender/items/classification/id": "omit",
    "tender/items/unit/id": "omit",
    "tender/items/additionalClassifications/scheme": "constant: UNSPSC",
    "tender/milestones/code": "S1–S3: PreBid Date → prebid_date [milestone:preBid]",
    "tender/milestones/dateMet": "S1–S3: PreBid Date → prebid_date",
    "tender/procuringEntity/id": "derived: slug(procuring_entity)",
    "tender/tenderers/id": "derived: slug(parsed bidder name)",
    "tender/tenderers/name": "S3: List of Bidder's → bidders [parse ; html-unescape]",
}

# Disambiguate repeated OCDS paths (parties/name, parties/id) by PhilGEPS 1.5 source.
OCDS_ROW_DISAMBIGUATORS: dict[tuple[str, str], str] = {
    ("parties/name", "D_AwardAwardee (Awardee)"): "awardee_organization_name",
    ("parties/name", "M_Organization (OrgName)"): "procuring_entity",
    ("parties/name", "M_Tender (ProcuringEntityOrg)"): "procuring_entity",
    ("parties/name", "M_TenderBiddersList (OrgName)"): "bidders",
    ("parties/id", "D_AwardAwardee (AwardeeID)"): "derived:slug(awardee_organization_name)",
    ("parties/id", "M_Organization (OrgID)"): "derived:slug(procuring_entity)",
    ("parties/id", "M_Tender (ProcuringEntityOrgID)"): "derived:slug(procuring_entity)",
    ("parties/id", "M_TenderBiddersList (OrgID)"): "derived:slug(parsed bidder name)",
}

# Unmapped OCDS rows (ocds field —) keyed by PhilGEPS 1.5 + V2/V1 hints.
UNMAPPED_ROW_CANONICAL: dict[str, str] = {
    "D_AwardAwardee (AwardType)": "S1–S3: Award Type → award_type [extension]",
    "D_AwardAwardee (ContractNo)": "S1–S3: Contract No → contract_no [extension]",
    "D_AwardAwardee (Proceed Date)": "S1–S5: Notice to Proceed Date → notice_to_proceed_date [extension]",
    "D_Tender_Item (ItemDesc)": "S1–S2: Item Desc · S3–S5: Item Description → item_description",
    "D_Tender_Item (Qty)": "S1–S5: Quantity → quantity",
    "D_Tender_Item (UOM)": "S1: UOM · S2: Unit of Measurement · S3–S5: UOM → uom",
    "M_Tender (Funding Instrument)": "S1–S5: Funding Instrument → funding_instrument [extension]",
    "M_Tender (NoticeType)": "S1–S3: Notice Type → notice_type [extension]",
    "M_Tender (SolicitationNo)": "S1–S3: Solicitation No. → solicitation_no [extension]",
    "M_Tender (TradeAgreement)": "S1–S5: Trade Agreement → trade_agreement [extension]",
    "APP (ID)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "APP Details (Annual Year)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Auditor (Name)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Award_Participants (Vendor Name)": "S4–S5: Awardee Joint Venture → awardee_joint_venture [parse ;]",
    "Awards (Reason of Award)": "S1–S3: Reason for Award → reason_for_award [extension]",
    "Awards (Vendor Acceptance Date)": "S4–S5: Notice to Proceed Date → notice_to_proceed_date [extension]",
    "CSO (Organization Name)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Contract Payment Details (Contract Amount)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "PO GRN (Number of Days)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "PO Milestones (Name)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "PR (PR Date)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "PR (PR Number)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Purchase Orders (Vendor Name)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Supplier (City)": "S4–S5: City/Municipality of Awardee → awardee_city_municipality",
    "Supplier (Company Type)": "S4–S5: Awardee Size → awardee_size",
    "Supplier (SEC Registration Number)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Supplier (Tax Number)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Tender_BAC (Member Name)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "Tenders (Delivery Location)": "S1–S5: Area of Delivery → area_of_delivery [extension]",
    "Tenders Items (Item Name)": "S1–S5: Item Name → item_name",
    "Tenders Items (Quantity)": "S1–S5: Quantity → quantity",
    "agency_organization_types (grouped_name)": "S4–S5: PE Organization Type (Grouped) → pe_organization_type_grouped",
    "app_line_items (Total Estimated Budget)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "app_status_tracker (Status)": "omit (PhilGEPS 2.0 internal — not in flat open CSV)",
    "departments_government_agency (city_municipality)": "S4–S5: City/Municipality → pe_city_municipality",
    "departments_government_agency (city_name)": "S4–S5: City/Municipality → pe_city_municipality",
    "departments_government_agency (government_branch)": "S4–S5: Government Branch → pe_government_branch",
    "government_branchs (name)": "S4–S5: Government Branch → pe_government_branch",
}

EXTENSION_FIELDS = {
    "trade_agreement",
    "funding_instrument",
    "solicitation_no",
    "reason_for_award",
    "notice_to_proceed_date",
    "area_of_delivery",
    "award_type",
    "contract_no",
    "notice_type",
}


def load_yaml(path: Path) -> dict:
    if yaml is None:
        raise SystemExit("PyYAML required: pip install pyyaml")
    with path.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def invert_schema_mappings(config: dict) -> dict[str, dict[str, str | None]]:
    """canonical_field -> {schema_key: source_column}."""
    result: dict[str, dict[str, str | None]] = defaultdict(dict)
    open_keys = [k for k, _, _ in OPEN_SCHEMA_KEYS]
    for schema_key in open_keys:
        mapping = config.get(schema_key, {})
        for source_col, canonical in mapping.items():
            result[canonical][schema_key] = source_col
    for schema_key in open_keys:
        for canonical in result:
            result[canonical].setdefault(schema_key, None)
    return dict(result)


def build_semantic_index(analysis: dict) -> dict[str, dict]:
    """semantic field_name -> metadata from PHILGEPS_SCHEMA_ANALYSIS.json."""
    index: dict[str, dict] = {}
    for group in analysis.get("semantic_grouping", []):
        category = group["category"]
        for field in group.get("fields", []):
            name = field["field_name"]
            source_columns: dict[str, str | None] = {}
            for json_key, schema_key in SCHEMA_KEY_ALIASES.items():
                val = field.get(json_key)
                if val == "REMOVED":
                    val = None
                source_columns[schema_key] = val
            if field.get("schema_1_2_2000_2020"):
                raw = field["schema_1_2_2000_2020"]
                if "UOM (2000-2015)" in raw:
                    source_columns["schema_1"] = "UOM"
                    source_columns["schema_2"] = "Unit of Measurement"
                else:
                    source_columns.setdefault("schema_1", raw)
                    source_columns.setdefault("schema_2", raw)
            index[name] = {
                "category": category,
                "semantic_name": name,
                "source_columns_semantic": source_columns,
                "evolution_notes": field.get("evolution_notes"),
            }
    return index


def canonical_to_semantic_name(canonical: str, inverted: dict[str, dict[str, str | None]], semantic_index: dict) -> str | None:
    cols = inverted.get(canonical, {})
    for meta in semantic_index.values():
        sem = meta["source_columns_semantic"]
        for sk in ("schema_1", "schema_2", "schema_3", "schema_4"):
            sem_val = sem.get(sk)
            col_val = cols.get(sk)
            if sem_val and col_val and sem_val == col_val:
                return meta["semantic_name"]
            if sem_val and col_val and sem_val in ("UOM", "Unit of Measurement") and col_val in ("UOM", "Unit of Measurement"):
                return meta["semantic_name"]
    return None


def reverse_ocds_map(config: dict) -> dict[str, list[str]]:
    """ocds_path -> [canonical_fields]."""
    result: dict[str, list[str]] = defaultdict(list)
    for block in ("planning", "tender", "awards", "contracts", "buyer", "bids"):
        block_data = config.get(block, {})
        if not isinstance(block_data, dict):
            continue
        for path, canonical in block_data.items():
            if isinstance(canonical, str) and not canonical.startswith("_"):
                full_path = path if "/" in path else f"{block}/{path}"
                result[full_path].append(canonical)
    for ext_key, canonical in config.get("philgeps_extension", {}).items():
        result[f"extension/{ext_key}"].append(canonical)
    return dict(result)


def compact_schema_groups(source_by_schema: dict[str, str | None]) -> list[tuple[str, str]]:
    """Group consecutive schemas sharing the same source column label."""
    groups: list[tuple[str, str]] = []
    current_label: str | None = None
    current_keys: list[str] = []

    def flush() -> None:
        nonlocal current_label, current_keys
        if current_label and current_keys:
            groups.append((_format_schema_range(current_keys), current_label))
        current_label = None
        current_keys = []

    for schema_key, short, _ in OPEN_SCHEMA_KEYS:
        label = source_by_schema.get(schema_key)
        if label is None:
            flush()
            continue
        if label == current_label:
            current_keys.append(short)
        else:
            flush()
            current_label = label
            current_keys = [short]
    flush()
    return groups


def _format_schema_range(keys: list[str]) -> str:
    if len(keys) == 1:
        return keys[0]
    nums = [int(k[1:]) for k in keys]
    if nums == list(range(nums[0], nums[-1] + 1)):
        return f"{keys[0]}–{keys[-1]}"
    return "/".join(keys)


def format_canonical_ai(
    canonical: str | None,
    inverted: dict[str, dict[str, str | None]],
    suffix: str = "",
) -> str:
    if not canonical:
        return "omit"
    cols = inverted.get(canonical, {})
    if not any(cols.values()):
        if canonical in EXTENSION_FIELDS:
            return f"omit in S4–S5 (removed or internal); S1–S3 may map → {canonical} [extension]"
        return f"omit (not in open CSV) → {canonical}"

    groups = compact_schema_groups(cols)
    if not groups:
        return f"omit → {canonical}"

    parts = [f"{rng}: {label}" for rng, label in groups]
    base = " · ".join(parts)
    tag = ""
    if canonical in EXTENSION_FIELDS:
        tag = " [extension]"
    elif canonical in {"classification", "procurement_mode", "bid_notice_status", "award_notice_status"}:
        tag = " [codelist map]"
    return f"{base} → {canonical}{suffix}{tag}"


def build_canonical_fields(
    config: dict,
    analysis: dict,
    ocds_reverse: dict[str, list[str]],
) -> list[dict]:
    inverted = invert_schema_mappings(config)
    semantic_index = build_semantic_index(analysis)
    field_types = config.get("field_types", {})
    type_lookup = {}
    for ftype, names in field_types.items():
        for name in names:
            type_lookup[name] = ftype

    entries = []
    for canonical in sorted(inverted):
        source_columns = inverted[canonical]
        semantic_name = canonical_to_semantic_name(canonical, inverted, semantic_index)
        meta = semantic_index.get(semantic_name or "", {})
        ocds_paths = sorted(
            path for path, fields in ocds_reverse.items() if canonical in fields
        )
        present_in = [sk for sk, col in source_columns.items() if col]
        entries.append(
            {
                "canonical_field": canonical,
                "field_type": type_lookup.get(canonical),
                "category": meta.get("category"),
                "semantic_name": semantic_name,
                "source_columns": source_columns,
                "present_in_schemas": present_in,
                "ocds_paths": ocds_paths,
                "evolution_notes": meta.get("evolution_notes"),
                "canonical_ai": format_canonical_ai(canonical, inverted),
                "excluded": any(
                    source_columns.get(sk) in config.get("excluded_source_columns", [])
                    for sk in present_in
                ),
            }
        )
    return entries


def parse_crosswalk_rows(md_text: str) -> list[dict]:
    rows = []
    row_re = re.compile(
        r"^\|\s*`([^`]*)`\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$"
    )
    for line in md_text.splitlines():
        if line.startswith("| OCDS field") or line.startswith("|---"):
            continue
        match = row_re.match(line)
        if not match:
            continue
        ocds, p15, p20, v2, v1, canon = match.groups()
        rows.append(
            {
                "ocds_field": ocds,
                "philgeps_1_5": p15,
                "philgeps_2_0": p20,
                "v2_csv": v2,
                "v1_csv": v1,
                "canonical_ai_old": canon,
            }
        )
    return rows


def resolve_canonical_ai(row: dict, inverted: dict[str, dict[str, str | None]], ocds_reverse: dict[str, list[str]]) -> str:
    ocds = row["ocds_field"]
    p15 = row["philgeps_1_5"]

    if ocds == "—":
        p20 = row["philgeps_2_0"]
        for key, text in UNMAPPED_ROW_CANONICAL.items():
            if key in p15 or key in p20:
                return text
        # Infer from V2/V1 CSV columns when present
        v2, v1 = row["v2_csv"], row["v1_csv"]
        for col in (v2, v1):
            if col and col != "—":
                for canonical, cols in inverted.items():
                    if cols.get("schema_4") == col or cols.get("schema_3") == col:
                        return format_canonical_ai(canonical, inverted)
        return row["canonical_ai_old"]

    disambig = OCDS_ROW_DISAMBIGUATORS.get((ocds, p15))
    if disambig:
        if disambig.startswith("derived:"):
            return disambig.replace("derived:", "derived: ", 1)
        return format_canonical_ai(disambig, inverted)

    if ocds in CANONICAL_AI_OVERRIDES:
        return CANONICAL_AI_OVERRIDES[ocds]

    canonical = OCDS_CANONICAL.get(ocds)
    if not canonical:
        fields = ocds_reverse.get(ocds, [])
        if len(fields) == 1:
            canonical = fields[0]
        else:
            return row["canonical_ai_old"]

    return format_canonical_ai(canonical, inverted)


def render_crosswalk_md(rows: list[dict]) -> str:
    header = """# PhilGEPS OCDS ↔ CSV field crosswalk

Side-by-side reference: **OCDS field** → **PhilGEPS 1.5** → **PhilGEPS 2.0** → **V2 CSV** → **V1 CSV** → **Canonical** (all open-data schemas → canonical field).

> **Canonical column** uses compact schema keys: **S1** (2000–2015 XLSX), **S2** (2016–2020 XLSX), **S3** (2021–2024 CSV), **S4** (2025 CSV), **S5** (2021–2024-V2 CSV). Full per-schema dictionary: [`PHILGEPS_CANONICAL_FIELD_MAP.json`](PHILGEPS_CANONICAL_FIELD_MAP.json).

"""
    table_lines = [
        "| OCDS field | PhilGEPS 1.5 field | PhilGEPS 2.0 field | V2 CSV column | V1 CSV column | Canonical |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        table_lines.append(
            "| `{ocds}` | {p15} | {p20} | {v2} | {v1} | {canon} |".format(
                ocds=row["ocds_field"],
                p15=row["philgeps_1_5"],
                p20=row["philgeps_2_0"],
                v2=row["v2_csv"],
                v1=row["v1_csv"],
                canon=row["canonical_ai"],
            )
        )

    footer = """
## Legend

| Term | Source |
|---|---|
| **OCDS field** | PS-DBM v0.91 template `mapping_details` |
| **PhilGEPS 1.5** | `philgeps-1.5.json` — legacy notice/award tables |
| **PhilGEPS 2.0** | `mphilgeps.json` — modernized system (`Tenders`, `APP`, `PR`, `Supplier`, etc.) |
| **V2 CSV** | Schema 4/5 — `raw/PHILGEPS -- 2021 - 2025 (CSV) V2/` (46 cols) |
| **V1 CSV** | Schema 3 — `raw/PHILGEPS -- 2021-2025 (CSV)/` (43 cols) |
| **Canonical** | All open schemas S1–S5 → canonical field; see `PHILGEPS_CANONICAL_FIELD_MAP.json` and `config/schema_mappings.yaml` |
| **S1–S5** | Schema periods from `PHILGEPS_SCHEMA_ANALYSIS.json` (includes 2000–2020 XLSX, not only V1/V2 CSV) |

PhilGEPS 2.0 column uses **semantic** links (curated from `mphilgeps.json` table/field names and PS-DBM docs), not raw template column offsets — the shipped `mphilgeps.json` has known column-shift artefacts in `mapping_details`.

`—` = not present. `*(unmapped)*` = PhilGEPS 1.5 template field not marked mapped. `[extension]` = emit via `philgeps_extension` block in `canonical_to_ocds.yaml`. `[codelist map]` = map through `config/ocds_codelist_mappings.yaml`.

Regenerate this file and the JSON dictionary:

```bash
python scripts/build_schema_field_map.py
```

## Summary

"""
    mapped = sum(1 for r in rows if not r["canonical_ai"].startswith("omit"))
    omit = sum(1 for r in rows if r["canonical_ai"].startswith("omit"))
    derived = sum(1 for r in rows if r["canonical_ai"].startswith("derived:"))
    with_ocds = sum(1 for r in rows if r["ocds_field"] != "—")

    footer += f"""- **{len(rows)}** total rows ({with_ocds} with OCDS path).
- **{mapped}** rows with a suggested open-data mapping in Canonical.
- **{omit}** rows marked omit (not in flat open CSV or privacy-excluded).
- **{derived}** rows using derived/slug identifiers.
- Canonical prefers **S4–S5** (V2) when available, then **S3** (V1), then **S1–S2** (XLSX); PhilGEPS 2.0-only internal fields (APP, PR, PO) require WSF export or API access.
"""
    return header + "\n".join(table_lines) + footer


def classify_crosswalk_row(canonical_text: str, ocds_field: str) -> str:
    """Bucket a crosswalk row for UI filtering."""
    text = canonical_text.strip().lower()
    if text.startswith("omit"):
        return "omit"
    if text.startswith("derived"):
        return "derived"
    if ocds_field == "—":
        return "unmapped"
    if "[extension]" in text:
        return "extension"
    if text.startswith("constant"):
        return "constant"
    return "mapped"


def ocds_block_of(ocds_field: str) -> str:
    """Top-level OCDS block (tender, awards, parties, etc.) for filtering."""
    if ocds_field == "—" or "/" not in ocds_field:
        return "other"
    return ocds_field.split("/", 1)[0]


# Representative canonical sample row used to illustrate the OCDS staging rules.
# One line-item award against a single bid notice; values are illustrative.
SAMPLE_CANONICAL_ROW: dict[str, object] = {
    "procuring_entity": "Department of Education - Region V",
    "pe_uacs_code": "20000-DOE-V-2018",
    "bid_reference_no": "5257621",
    "solicitation_no": "S-2025-05-DEDR5-1234",
    "notice_title": "Supply and Delivery of Printing Materials",
    "classification": "Goods",
    "business_category": "Printing Equipment and Supplies",
    "funding_source": "General Fund",
    "funding_instrument": "GOCC Corporate Funds",
    "approved_budget": 1850000.00,
    "trade_agreement": "RP-USA",
    "procurement_mode": "Public Bidding",
    "area_of_delivery": "Region V",
    "contract_duration": 60,
    "calendar_type": "Calendar Days",
    "line_item_no": 1,
    "item_name": "A4 Bond Paper (80gsm, 500 sheets/ream)",
    "item_description": "A4 80gsm white bond paper, 500 sheets per ream",
    "quantity": 1000,
    "uom": "ream",
    "item_budget": 1850.00,
    "unspsc_code": "14111507",
    "unspsc_description": "Paper",
    "bid_notice_status": "Closed",
    "award_reference_no": "5257621-001",
    "award_title": "Supply and Delivery of Printing Materials (Lot 1)",
    "award_type": "Lot Award",
    "award_published_date": "2025-04-28T09:00:00+08:00",
    "award_date": "2025-05-12T14:00:00+08:00",
    "notice_to_proceed_date": "2025-05-20T09:00:00+08:00",
    "contract_effectivity_date": "2025-05-20T09:00:00+08:00",
    "contract_end_date": "2025-07-19T17:00:00+08:00",
    "contract_amount": 1840000.00,
    "contract_no": "DEDR5-2025-001",
    "award_notice_status": "Posted",
    "reason_for_award": "Lowest Calculated Responsive Bid",
    "awardee_organization_name": "Primeprint Trading Inc.",
    "awardee_org_id": "primeprint-trading-inc",
    "awardee_jointventure": ["Primeprint Trading Inc."],
    "awardee_country": "Philippines",
    "awardee_region": "Region V",
    "awardee_size": "Small",
    "bidders": [
        "Primeprint Trading Inc.",
        "National Bookstore Inc.",
        "Papercraft Philippines",
    ],
    "published_date": "2025-04-01T08:00:00+08:00",
    "closing_date": "2025-04-22T10:00:00+08:00",
    "prebid_date": "2025-04-10T10:00:00",
    "record_id": "5257621-001",
}


def _set_nested(target: dict, dotted_path: str, value: object) -> None:
    """Assign value into target at dotted_path, creating dicts as needed."""
    cursor = target
    parts = dotted_path.split("/")
    for part in parts[:-1]:
        nxt = cursor.setdefault(part, {})
        if not isinstance(nxt, dict):
            break
        cursor = nxt
    cursor[parts[-1]] = value


def _resolve_canonical_value(canonical: str, sample: dict) -> object:
    """Return the sample value for a canonical field (currency wrapping happens at assignment)."""
    return sample.get(canonical)


def _apply_currency(value: object, currency: str) -> object:
    if value is None:
        return None
    return {"amount": value, "currency": currency}


def _is_amount_leaf(dotted_path: str) -> bool:
    """True for OCDS paths whose leaf represents a monetary amount (needs currency wrapping)."""
    return dotted_path.endswith("/value/amount") or dotted_path == "value/amount"


def _inject_currency(node: object, currency: str) -> None:
    """Walk a release subtree and add `currency` next to every numeric `amount` field."""
    if isinstance(node, dict):
        if (
            isinstance(node.get("amount"), (int, float))
            and not isinstance(node.get("amount"), bool)
            and "currency" not in node
        ):
            node["currency"] = currency
        for v in node.values():
            _inject_currency(v, currency)
    elif isinstance(node, list):
        for item in node:
            _inject_currency(item, currency)


def _apply_codelist_transform(value: object, canonical: str, codelists: dict) -> object:
    """Translate PhilGEPS labels to OCDS codes via config/ocds_codelist_mappings.yaml."""
    if value is None:
        return None
    if canonical == "procurement_mode":
        return codelists.get("procurement_method", {}).get(value, value)
    if canonical == "classification":
        return codelists.get("main_procurement_category", {}).get(value, value)
    if canonical == "bid_notice_status":
        return codelists.get("tender_status", {}).get(value, value)
    if canonical == "award_notice_status":
        return codelists.get("award_status", {}).get(value, value)
    return value


def build_sample_release_package(ocds_cfg: dict, codelists: dict) -> dict:
    """Compile a sample compiled release by walking canonical_to_ocds.yaml staging rules."""
    defaults = codelists.get("defaults", {})
    currency = defaults.get("currency", "PHP")
    initiation = defaults.get("initiation_type", "tender")
    tag = defaults.get("tag", ["compiled"])
    classification_scheme = defaults.get("classification_scheme", "UNSPSC")
    bid_status_default = codelists.get("bid_status_default", "valid")
    ocid_prefix = ocds_cfg.get("ocid_prefix", "ocds-philgeps")

    row = SAMPLE_CANONICAL_ROW.copy()
    ocid = f"{ocid_prefix}-{row['procuring_entity']}-{row['award_reference_no']}".lower().replace(" ", "-")

    release: dict = {
        "ocid": ocid,
        "id": row["record_id"],
        "date": row["award_published_date"],
        "initiationType": initiation,
        "tag": tag,
        "language": "en",
    }

    def canon(canonical: str) -> object:
        value = _resolve_canonical_value(canonical, row)
        return _apply_codelist_transform(value, canonical, codelists)

    def stage_block(block_name: str) -> dict:
        out: dict = {}
        for path, canonical in ocds_cfg.get(block_name, {}).items():
            if isinstance(canonical, str) and not canonical.startswith("_"):
                value = canon(canonical)
                if value is not None:
                    _set_nested(out, path, value)
        return out

    # Planning block (triggered when planning_triggers present).
    planning_triggers = ocds_cfg.get("planning_triggers", [])
    planning_values = {t: row.get(t) for t in planning_triggers}
    if any(v is not None for v in planning_values.values()):
        planning = stage_block("planning")
        if planning:
            release["planning"] = planning

    # Buyer.
    buyer = stage_block("buyer")
    if buyer:
        release["buyer"] = buyer

    # Tender + tender/items + parties (buyer + suppliers).
    tender = stage_block("tender")
    release["tender"] = tender

    # Canonical_to_ocds.yaml writes items/* as nested dicts; OCDS items is a list.
    # Collapse to a single-item list using the sample line-item values.
    if "items" in tender:
        items_dict = tender.pop("items")
        if isinstance(items_dict, dict):
            item = dict(items_dict)
        else:
            item = {}
        item["id"] = row["line_item_no"]
        item["description"] = row["item_description"]
        item["quantity"] = row["quantity"]
        item["classification"] = {
            "scheme": classification_scheme,
            "id": row["unspsc_code"],
            "description": row["unspsc_description"],
        }
        item["additionalClassifications"] = [
            {
                "scheme": classification_scheme,
                "id": row["unspsc_code"],
                "description": row["unspsc_description"],
            }
        ]
        item["unit"] = {
            "name": row["uom"],
            "value": _apply_currency(row["item_budget"], currency),
        }
        tender["items"] = [item]

    # Awards + award items + suppliers. Pop the staging-written items dict and
    # replace it with the tender line-item list (OCDS items is always a list).
    awards: list[dict] = []
    award = stage_block("awards")
    award.pop("items", None)
    if tender.get("items"):
        award["items"] = tender["items"]
    award["suppliers"] = [
        {"id": row["awardee_org_id"], "name": row["awardee_organization_name"]}
    ]
    awards.append(award)
    release["awards"] = awards

    # Contracts.
    contract = stage_block("contracts")
    contracts: list[dict] = [contract]
    release["contracts"] = contracts

    # Bids (extension).
    bids_cfg = ocds_cfg.get("bids", {})
    if bids_cfg:
        bids = {"details": []}
        for bidder_name in row.get("bidders", []):
            bids["details"].append(
                {
                    "id": f"{ocid}-bid-{len(bids['details']) + 1}",
                    "tenderers": [{"id": bidder_name.lower().replace(" ", "-"), "name": bidder_name}],
                    "status": bid_status_default,
                    "date": row["closing_date"],
                }
            )
        release["bids"] = bids

    # Parties (buyer + suppliers).
    parties = []
    parties.append(
        {
            "id": buyer.get("id", row.get("pe_uacs_code")),
            "name": row["procuring_entity"],
            "roles": ["buyer", "procuringEntity"],
        }
    )
    parties.append(
        {
            "id": row["awardee_org_id"],
            "name": row["awardee_organization_name"],
            "roles": ["supplier", "payee", "tenderer"],
        }
    )
    release["parties"] = parties

    # PhilGEPS extension block.
    ext_payload: dict = {}
    for ext_key, canonical in ocds_cfg.get("philgeps_extension", {}).items():
        value = canon(canonical)
        if value is not None:
            ext_payload[ext_key] = value
    if ext_payload:
        release["philgeps"] = ext_payload

    # Add `currency` next to every numeric `amount` (value blocks, unit/value, etc.).
    _inject_currency(release, currency)

    package = {
        "uri": f"https://philgeps-ocds.example/{ocid}.json",
        "version": ocds_cfg.get("ocds_version", "1.1"),
        "extensions": ocds_cfg.get("extensions", []),
        "publishedDate": row["award_published_date"],
        "publisher": {
            "name": "Philippine Government Electronic Procurement System (PhilGEPS)",
            "scheme": "PH-PhilGEPS",
            "uid": "ph-philgeps",
            "uri": "https://www.philgeps.gov.ph",
        },
        "license": "https://creativecommons.org/licenses/by/4.0/",
        "publicationPolicy": "https://philgeps-ocds.example/policy",
        "releases": [release],
    }
    return package


def build_release_payload(ocds_cfg: dict, codelists: dict) -> dict:
    """Wrap the sample release package with a compact summary for the webapp."""
    package = build_sample_release_package(ocds_cfg, codelists)
    release = package["releases"][0]

    def block_keys(*names: str) -> list[str]:
        keys = []
        for name in names:
            if isinstance(release.get(name), dict):
                keys.extend(sorted(release[name].keys()))
            elif isinstance(release.get(name), list) and release[name] and isinstance(release[name][0], dict):
                keys.extend(sorted(release[name][0].keys()))
        return keys

    return {
        "package": package,
        "release": release,
        "summary": {
            "ocid": release.get("ocid"),
            "release_id": release.get("id"),
            "release_date": release.get("date"),
            "version": package.get("version"),
            "initiation_type": release.get("initiationType"),
            "tag": release.get("tag"),
            "language": release.get("language"),
            "publisher": package.get("publisher", {}).get("name"),
            "extensions": package.get("extensions", []),
            "top_level_blocks": sorted(
                k for k, v in release.items() if not isinstance(v, (list, dict)) or k in {"planning", "buyer"}
            ),
            "tender_item_count": len(release.get("tender", {}).get("items", [])),
            "award_count": len(release.get("awards", [])),
            "contract_count": len(release.get("contracts", [])),
            "party_count": len(release.get("parties", [])),
            "bid_count": len(release.get("bids", {}).get("details", [])),
            "has_planning": "planning" in release,
            "has_extension": "philgeps" in release,
            "tender_keys": block_keys("tender"),
            "award_keys": block_keys("awards"),
            "contract_keys": block_keys("contracts"),
        },
    }


def build_app_bundle(
    *,
    analysis: dict,
    mappings: dict,
    ocds_cfg: dict,
    codelists: dict,
    ocds_reverse: dict[str, list[str]],
    inverted: dict[str, dict[str, str | None]],
    canonical_fields: list[dict],
    rows: list[dict],
) -> dict:
    """Build a single bundled JSON the webapp imports directly."""
    schema_periods = {}
    for idx, (schema_key, short, _) in enumerate(OPEN_SCHEMA_KEYS):
        qr = analysis["quick_reference"][idx]
        schema_periods[schema_key] = {
            "key": schema_key,
            "short_key": short,
            "label": qr["schema"],
            "period": qr["period"],
            "format": qr["format"],
            "columns": qr["columns"],
            "key_change": qr["key_change"],
            "source_columns": mappings.get(schema_key, {}),
        }

    crosswalk = []
    for row in rows:
        crosswalk.append(
            {
                "ocds_field": row["ocds_field"],
                "ocds_block": ocds_block_of(row["ocds_field"]),
                "philgeps_1_5": row["philgeps_1_5"],
                "philgeps_2_0": row["philgeps_2_0"],
                "v2_csv": row["v2_csv"],
                "v1_csv": row["v1_csv"],
                "canonical": row["canonical_ai"],
                "status": classify_crosswalk_row(row["canonical_ai"], row["ocds_field"]),
            }
        )

    staged_blocks = []
    for block_name in ("planning", "buyer", "tender", "awards", "contracts", "bids"):
        block_data = ocds_cfg.get(block_name, {})
        if not isinstance(block_data, dict) or not block_data:
            continue
        paths = []
        for path, canonical in block_data.items():
            if isinstance(canonical, str) and not canonical.startswith("_"):
                paths.append(
                    {
                        "path": path if "/" in path else f"{block_name}/{path}",
                        "canonical": canonical,
                        "is_constant": canonical.startswith("_"),
                    }
                )
        staged_blocks.append({"block": block_name, "paths": paths})

    ext_paths = []
    for ext_key, canonical in ocds_cfg.get("philgeps_extension", {}).items():
        ext_paths.append({"path": f"philgeps_extension/{ext_key}", "canonical": canonical})
    if ext_paths:
        staged_blocks.append({"block": "philgeps_extension", "paths": ext_paths})

    generated = []
    for gen_key, spec in ocds_cfg.get("generated", {}).items():
        generated.append({"field": gen_key, "spec": spec})

    defaults = codelists.get("defaults", {})
    codelist_sections = []
    for codelist_name, label in (
        ("procurement_method", "Procurement method"),
        ("main_procurement_category", "Main procurement category"),
        ("tender_status", "Tender status"),
        ("award_status", "Award status"),
        ("contract_status", "Contract status"),
    ):
        entries = codelists.get(codelist_name)
        if not entries:
            continue
        codelist_sections.append(
            {
                "name": codelist_name,
                "label": label,
                "entries": [
                    {"philgeps": k, "ocds": v} for k, v in entries.items()
                ],
            }
        )

    semantic_groups = []
    for group in analysis.get("semantic_grouping", []):
        semantic_groups.append(
            {
                "category": group["category"],
                "fields": group.get("fields", []),
            }
        )

    field_types = mappings.get("field_types", {})

    return {
        "metadata": {
            "title": "PhilGEPS Schema Explorer",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_analysis_date": analysis.get("analysis_date"),
            "ocds_template": "PS-DBM v0.91 (OCDS 1.1.5)",
            "ocds_mapping_version": ocds_cfg.get("version"),
            "ocid_prefix": ocds_cfg.get("ocid_prefix"),
            "sources": {
                "schema_analysis": "references/PHILGEPS_SCHEMA_ANALYSIS.json",
                "schema_mappings": "config/schema_mappings.yaml",
                "canonical_to_ocds": "config/canonical_to_ocds.yaml",
                "codelists": "config/ocds_codelist_mappings.yaml",
                "crosswalk": "references/PHILGEPS_OCDS_CSV_CROSSWALK.md",
            },
        },
        "schemas": schema_periods,
        "semantic_grouping": semantic_groups,
        "canonical_fields": canonical_fields,
        "field_types": field_types,
        "excluded_source_columns": mappings.get("excluded_source_columns", []),
        "ocds_crosswalk": crosswalk,
        "ocds_staged": {
            "version": ocds_cfg.get("version"),
            "ocid_prefix": ocds_cfg.get("ocid_prefix"),
            "extensions": ocds_cfg.get("extensions", []),
            "planning_triggers": ocds_cfg.get("planning_triggers", []),
            "generated": generated,
            "blocks": staged_blocks,
            "defaults": defaults,
        },
        "ocds_release": build_release_payload(ocds_cfg, codelists),
        "codelists": codelist_sections,
        "ocds_reverse": {k: v for k, v in ocds_reverse.items()},
        "summary": {
            "schema_count": len(schema_periods),
            "canonical_field_count": len(canonical_fields),
            "crosswalk_row_count": len(crosswalk),
            "crosswalk_with_ocds": sum(1 for r in crosswalk if r["ocds_field"] != "—"),
            "crosswalk_mapped": sum(1 for r in crosswalk if r["status"] == "mapped"),
            "crosswalk_omit": sum(1 for r in crosswalk if r["status"] == "omit"),
            "crosswalk_derived": sum(1 for r in crosswalk if r["status"] == "derived"),
            "crosswalk_extension": sum(1 for r in crosswalk if r["status"] == "extension"),
            "staged_block_count": len(staged_blocks),
            "codelist_count": len(codelist_sections),
            "semantic_group_count": len(semantic_groups),
        },
    }


def main() -> None:
    analysis = json.loads(SCHEMA_ANALYSIS.read_text(encoding="utf-8"))
    mappings = load_yaml(SCHEMA_MAPPINGS)
    ocds_cfg = load_yaml(CANONICAL_TO_OCDS)
    codelists = load_yaml(CODELIST_MAPPINGS)
    ocds_reverse = reverse_ocds_map(ocds_cfg)
    inverted = invert_schema_mappings(mappings)

    canonical_fields = build_canonical_fields(mappings, analysis, ocds_reverse)

    crosswalk_text = CROSSWALK_MD.read_text(encoding="utf-8")
    rows = parse_crosswalk_rows(crosswalk_text)
    for row in rows:
        row["canonical_ai"] = resolve_canonical_ai(row, inverted, ocds_reverse)

    payload = {
        "metadata": {
            "title": "PhilGEPS canonical field map (open-data schemas S1–S5)",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "sources": {
                "schema_analysis": "references/PHILGEPS_SCHEMA_ANALYSIS.json",
                "schema_mappings": "config/schema_mappings.yaml",
                "canonical_to_ocds": "config/canonical_to_ocds.yaml",
            },
        },
        "schemas": {
            schema_key: {
                "short_key": short,
                "label": analysis["quick_reference"][idx]["schema"],
                "period": analysis["quick_reference"][idx]["period"],
                "format": analysis["quick_reference"][idx]["format"],
                "columns": analysis["quick_reference"][idx]["columns"],
                "key_change": analysis["quick_reference"][idx]["key_change"],
            }
            for idx, (schema_key, short, _) in enumerate(OPEN_SCHEMA_KEYS)
        },
        "semantic_grouping": analysis.get("semantic_grouping"),
        "canonical_fields": canonical_fields,
        "source_column_index": {
            schema_key: mappings.get(schema_key, {})
            for schema_key, _, _ in OPEN_SCHEMA_KEYS
        },
        "ocds_crosswalk": [
            {
                "ocds_field": row["ocds_field"],
                "philgeps_1_5": row["philgeps_1_5"],
                "philgeps_2_0": row["philgeps_2_0"],
                "v2_csv": row["v2_csv"],
                "v1_csv": row["v1_csv"],
                "canonical": row["canonical_ai"],
            }
            for row in rows
        ],
    }

    FIELD_MAP_JSON.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {FIELD_MAP_JSON} ({len(canonical_fields)} canonical fields)")

    CROSSWALK_MD.write_text(render_crosswalk_md(rows), encoding="utf-8")
    print(f"Updated {CROSSWALK_MD} ({len(rows)} rows)")

    app_bundle = build_app_bundle(
        analysis=analysis,
        mappings=mappings,
        ocds_cfg=ocds_cfg,
        codelists=codelists,
        ocds_reverse=ocds_reverse,
        inverted=inverted,
        canonical_fields=canonical_fields,
        rows=rows,
    )
    APP_BUNDLE_JSON.parent.mkdir(parents=True, exist_ok=True)
    APP_BUNDLE_JSON.write_text(
        json.dumps(app_bundle, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {APP_BUNDLE_JSON} (webapp bundle)")

    # Emit the sample release package as a standalone JSON file so it can be
    # validated with ocdskit (see scripts/validate_sample_release.py).
    sample_package = build_sample_release_package(ocds_cfg, codelists)
    SAMPLE_RELEASE_JSON.write_text(
        json.dumps(sample_package, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {SAMPLE_RELEASE_JSON} (sample OCDS release package)")


if __name__ == "__main__":
    main()
