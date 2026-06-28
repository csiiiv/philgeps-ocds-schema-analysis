"""Build per-year JSON caches for the webapp Release browser.

Summaries match ``app/src/lib/releaseSummary.ts`` so the UI can list and search
releases without loading multi-GB ``by_year/<year>.json`` packages. Full release
JSON is included only for a capped detail subset (first N, multi-award, etc.).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

MAX_INDEX_ENTRIES = 10_000
MAX_DETAIL_RELEASES = 80
FIRST_DETAIL = 40
MULTI_AWARD_DETAIL = 30

BROWSER_DIR_NAME = "browser"


def _as_record(value: object) -> dict | None:
    if isinstance(value, dict):
        return value
    return None


def _as_array(value: object) -> list:
    return value if isinstance(value, list) else []


def _str(value: object, fallback: str = "—") -> str:
    if value is None or value == "":
        return fallback
    return str(value)


def _read_money(obj: dict | None) -> dict:
    value = _as_record((obj or {}).get("value"))
    amount = value.get("amount") if isinstance(value, dict) else None
    if not isinstance(amount, (int, float)) or isinstance(amount, bool):
        amount = None
    currency = _str(value.get("currency") if value else None, "PHP")
    return {"amount": amount, "currency": currency}


def _total_award_money(awards: list[dict]) -> dict:
    total = 0.0
    has_amount = False
    currency = "PHP"
    for award in awards:
        money = _read_money(award)
        amount = money.get("amount")
        if isinstance(amount, (int, float)) and not isinstance(amount, bool):
            total += float(amount)
            has_amount = True
            currency = money.get("currency") or currency
    return {"amount": total if has_amount else None, "currency": currency}


def _format_money(money: dict | None) -> str:
    if not money or money.get("amount") is None:
        return "—"
    amount = money["amount"]
    formatted = f"{amount:,.2f}".rstrip("0").rstrip(".")
    currency = money.get("currency") or ""
    return f"{formatted} {currency}".strip()


def _party_name(release: dict, role: str) -> str:
    for party in _as_array(release.get("parties")):
        rec = _as_record(party)
        if not rec:
            continue
        roles = _as_array(rec.get("roles"))
        if role in roles and rec.get("name"):
            return _str(rec["name"])
    buyer = _as_record(release.get("buyer"))
    if role == "buyer" and buyer and buyer.get("name"):
        return _str(buyer["name"])
    for award in _as_array(release.get("awards")):
        rec = _as_record(award)
        if not rec:
            continue
        suppliers = _as_array(rec.get("suppliers"))
        if suppliers:
            first = _as_record(suppliers[0])
            if first and first.get("name"):
                return _str(first["name"])
    return "—"


def _collect_items(release: dict) -> list[dict]:
    tender = _as_record(release.get("tender"))
    tender_items = _as_array(tender.get("items") if tender else None)
    award_items: list = []
    for award in _as_array(release.get("awards")):
        rec = _as_record(award)
        if rec:
            award_items.extend(_as_array(rec.get("items")))
    raw = tender_items if tender_items else award_items

    rows: list[dict] = []
    for index, item in enumerate(raw):
        rec = _as_record(item) or {}
        unit = _as_record(rec.get("unit"))
        unit_value = _as_record(unit.get("value") if unit else None)
        classification = _as_record(rec.get("classification"))
        qty = rec.get("quantity")
        if qty is None and unit:
            qty = unit.get("quantity")
        rows.append({
            "id": _str(rec.get("id"), str(index + 1)),
            "description": _str(rec.get("description") or (classification or {}).get("description")),
            "quantity": _str(qty) if qty is not None else "—",
            "unit": _str(unit.get("name") if unit else None),
            "unitPrice": _format_money(_read_money({"value": unit_value} if unit_value else None)),
            "total": _format_money(_read_money(rec)),
        })
    return rows


def _collect_parties(release: dict) -> list[dict]:
    rows: list[dict] = []
    for party in _as_array(release.get("parties")):
        rec = _as_record(party)
        if not rec:
            continue
        rows.append({
            "name": _str(rec.get("name")),
            "roles": [str(r) for r in _as_array(rec.get("roles"))],
        })
    return rows


def _resolve_supplier_name(suppliers: object, parties: list[dict]) -> str:
    refs = _as_array(suppliers)
    if not refs:
        return "—"
    first = _as_record(refs[0])
    if not first:
        return "—"
    if first.get("name"):
        return _str(first["name"])
    supplier_id = first.get("id")
    if supplier_id:
        for party in parties:
            rec = _as_record(party)
            if rec and rec.get("id") == supplier_id and rec.get("name"):
                return _str(rec["name"])
    return "—"


def _collect_awards(release: dict) -> list[dict]:
    parties = _as_array(release.get("parties"))
    rows: list[dict] = []
    for index, award in enumerate(_as_array(release.get("awards"))):
        rec = _as_record(award)
        if not rec:
            continue
        rows.append({
            "id": _str(rec.get("id"), str(index + 1)),
            "title": _str(rec.get("title")),
            "status": _str(rec.get("status")),
            "date": _format_date_label(rec.get("date")),
            "value": _format_money(_read_money(rec)),
            "supplier": _resolve_supplier_name(rec.get("suppliers"), parties),
            "itemCount": len(_as_array(rec.get("items"))),
        })
    return rows


def _collect_contracts(release: dict) -> list[dict]:
    rows: list[dict] = []
    for index, contract in enumerate(_as_array(release.get("contracts"))):
        rec = _as_record(contract)
        if not rec:
            continue
        period = _as_record(rec.get("period"))
        rows.append({
            "id": _str(rec.get("id"), str(index + 1)),
            "awardId": _str(rec.get("awardID") or rec.get("awardId")),
            "status": _str(rec.get("status")),
            "value": _format_money(_read_money(rec)),
            "startDate": _format_date_label(period.get("startDate") if period else None),
            "endDate": _format_date_label(period.get("endDate") if period else None),
        })
    return rows


def _format_date_label(iso: object) -> str:
    text = _str(iso, "")
    if not text or text == "—":
        return "—"
    return text[:10]


def summarize_release(release: dict) -> dict:
    """Return a ReleaseSummary-shaped dict for the webapp."""
    tender = _as_record(release.get("tender"))
    awards = [_as_record(a) for a in _as_array(release.get("awards"))]
    awards = [a for a in awards if a]
    contracts = [_as_record(c) for c in _as_array(release.get("contracts"))]
    contracts = [c for c in contracts if c]
    first_award = awards[0] if awards else None
    first_contract = contracts[0] if contracts else None
    contract_period = _as_record(first_contract.get("period") if first_contract else None)
    tender_period = _as_record(tender.get("tenderPeriod") if tender else None)
    philgeps = _as_record(release.get("philgeps")) or {}

    title = _str(tender.get("title") if tender else None)
    if title == "—" and first_award:
        title = _str(first_award.get("title"), _str(release.get("ocid"), "Untitled release"))
    if title == "—":
        title = _str(release.get("ocid"), "Untitled release")

    items = _collect_items(release)
    return {
        "ocid": _str(release.get("ocid"), "?"),
        "id": _str(release.get("id"), "?"),
        "date": _str(release.get("date")),
        "dateLabel": _format_date_label(release.get("date")),
        "title": title,
        "buyer": _party_name(release, "buyer"),
        "supplier": _party_name(release, "supplier"),
        "award": _read_money(first_award),
        "awardTotal": _total_award_money(awards),
        "tender": _read_money(tender),
        "tenderStatus": _str(tender.get("status") if tender else None),
        "awardStatus": _str(first_award.get("status") if first_award else None),
        "procurementMethod": _str(
            (tender or {}).get("procurementMethodDetails") or (tender or {}).get("procurementMethod")
        ),
        "category": _str(tender.get("mainProcurementCategory") if tender else None),
        "tenderStart": _format_date_label(tender_period.get("startDate") if tender_period else None),
        "tenderEnd": _format_date_label(tender_period.get("endDate") if tender_period else None),
        "awardDate": _format_date_label(first_award.get("date") if first_award else None),
        "contractStart": _format_date_label(contract_period.get("startDate") if contract_period else None),
        "contractEnd": _format_date_label(contract_period.get("endDate") if contract_period else None),
        "itemCount": len(items),
        "awardCount": len(awards),
        "partyCount": len(_as_array(release.get("parties"))),
        "tags": [str(t) for t in _as_array(release.get("tag"))],
        "initiationType": _str(release.get("initiationType")),
        "philgeps": philgeps,
        "items": items,
        "parties": _collect_parties(release),
        "awards": _collect_awards(release),
        "contracts": _collect_contracts(release),
    }


def _pick_detail_releases(releases: list[dict]) -> dict[str, dict]:
    """Choose full releases to embed for the Raw JSON tab."""
    detail: dict[str, dict] = {}
    ordered = sorted(releases, key=lambda r: (r.get("date") or "", r.get("ocid") or ""))

    for release in ordered[:FIRST_DETAIL]:
        ocid = release.get("ocid")
        if ocid:
            detail[str(ocid)] = release

    multi = [r for r in ordered if len(_as_array(r.get("awards"))) > 1]
    added = 0
    for release in multi:
        if len(detail) >= MAX_DETAIL_RELEASES:
            break
        ocid = release.get("ocid")
        if not ocid or str(ocid) in detail:
            continue
        detail[str(ocid)] = release
        added += 1
        if added >= MULTI_AWARD_DETAIL:
            break

    return detail


def build_browser_cache(releases: list[dict], *, year: str) -> dict[str, Any]:
    """Build the payload written to ``by_year/browser/<year>.json``."""
    ordered = sorted(releases, key=lambda r: (r.get("date") or "", r.get("ocid") or ""))
    index_source = ordered[:MAX_INDEX_ENTRIES]
    index = [summarize_release(r) for r in index_source]
    detail_map = _pick_detail_releases(ordered)

    return {
        "year": year,
        "compiled_release_count": len(releases),
        "index_count": len(index),
        "index_truncated": len(releases) > MAX_INDEX_ENTRIES,
        "detail_count": len(detail_map),
        "index": index,
        "releases": detail_map,
    }


def browser_cache_path(output_root: Path, year: str) -> Path:
    return output_root / BROWSER_DIR_NAME / f"{year}.json"


def write_browser_cache(
    releases: list[dict],
    *,
    year: str,
    output_root: Path,
) -> Path | None:
    if not releases:
        return None
    payload = build_browser_cache(releases, year=year)
    out_path = browser_cache_path(output_root, year)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write("\n")
    return out_path


def refresh_browser_cache_from_package(
    package_path: Path,
    *,
    year: str,
    output_root: Path,
    max_package_mb: float = 2500,
) -> Path | None:
    """Rebuild browser cache from an on-disk year package."""
    if not package_path.exists():
        return None
    size_mb = package_path.stat().st_size / 1e6
    if size_mb > max_package_mb:
        return None
    try:
        pkg = json.loads(package_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    releases = pkg.get("releases") or []
    if not isinstance(releases, list):
        return None
    return write_browser_cache(releases, year=year, output_root=output_root)
