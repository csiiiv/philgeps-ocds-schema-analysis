# OCDS `ocid` and release `id` generation

**Date:** 2026-06-28  
**Status:** Current production policy  
**Related:** [ADR-009](ARCHITECTURAL_DECISIONS.md#adr-009-process-level-releases-one-process-many-awards), [ADR-011](ARCHITECTURAL_DECISIONS.md#adr-011-process-identity-group-vs-display), [PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md)

This document explains how PhilGEPS canonical rows become OCDS `ocid` and `release.id` values, why the rules are what they are, and how collisions are handled.

---

## What OCDS requires

OCDS 1.1 treats each **compiled release** as one contracting process. Within a release package, the pair **`(ocid, id)` must be unique** across all releases. [libcoveocds](https://github.com/open-contracting/libcoveocds) enforces this strictly.

PhilGEPS flat exports are **denormalized**: many CSV/XLSX rows can belong to one process (same bid, different line items or awards). The transformer therefore:

1. **Groups** rows into one contracting process.
2. **Compiles** each group into one OCDS release.
3. Assigns **`ocid`** and **`release.id`** from process identity fields.
4. **Resolves collisions** if two compiled releases would still share the same `(ocid, id)`.

Grouping and naming are related but not identical. A field can be correct for grouping yet wrong as the public `release.id`.

---

## Canonical identity fields

All schema periods (S1–S5) map source columns into three canonical fields:

| Canonical field | S1/S2 source | S3 source | S4/S5 source |
|-----------------|--------------|-----------|--------------|
| `bid_reference_no` | Reference ID | Bid Reference No. | Bid Reference No. |
| `solicitation_no` | Solicitation No. | Solicitation No. | *(absent)* |
| `award_reference_no` | Award No. | Award No. | Award No. |

**Placeholder handling:** `bid_reference_no` values that are empty, null, or `"0"` are treated as **missing**. This is common in S3/S4 exports where the column was decommissioned or unused. DQ logs `placeholder_bid_ref` (warning) when bid is `0`.

---

## Pipeline overview

```text
canonical row
    │
    ├─ validate_row()
    │
    ├─ process_group_key(row)  ──► group rows (bid → sol → award)
    │
    ├─ validate_process_group()
    │
    ├─ compile_grouped(rows)     ──► one release; sets ocid + id from display_id
    │
    └─ resolve_release_display_collisions(releases)  ──► composite id + DQ if needed
```

**Implementation:**

| Step | Module | Function |
|------|--------|----------|
| Group key | `scripts/_ocds_compiler.py` | `_process_identity()`, `process_group_key()` |
| OCID / id at compile | `scripts/_ocds_compiler.py` | `_process_ocid_and_id()` inside `compile_grouped()` |
| Collision pass | `scripts/_ocds_compiler.py` | `resolve_release_display_collisions()` |
| Orchestration | `scripts/transform_to_ocds.py` | groups → compile → collision resolve |
| DQ reporting | `scripts/_data_quality.py` | `RunReport.add_package_warning("display_id_collision", …)` |

OCID prefix comes from `config/canonical_to_ocds.yaml`:

```yaml
ocid_prefix: ocds-philgeps
```

---

## Step 1: Group key (which rows merge into one release)

Rows with the same **group key** compile into **one** OCDS release (one `tender`, multiple `awards[]` / `contracts[]` when applicable).

```text
group_key =
    bid:{bid_reference_no}        if bid valid (not empty, not "0")
  | sol:{solicitation_no}         if bid missing and solicitation present
  | award:{award_reference_no}    last resort
```

### Why bid-first for grouping

Sample analysis (`scripts/analyze_process_identity.py`) showed solicitation labels are **not** unique across processes:

| Dataset | Solicitations mapping to multiple bid refs |
|---------|-------------------------------------------|
| S1 2004 | **117** (e.g. `ITAFE2404` → 8 bids) |
| S3 2021 | **679** (e.g. `2021-001` → 62 bids) |

Conversely, **0** bids mapped to multiple solicitations in S3 samples. When a valid bid exists, it is the stable process key.

**Never group by solicitation when a valid bid is present.**

---

## Step 2: Display id → `release.id` and `ocid`

After grouping, each compiled release needs a public identifier. The **display id** becomes:

- `release.id` — the release identifier string inside the package
- the slug portion of `ocid` — `ocds-philgeps-{slug(display_id)}`

```text
display_id =
    bid_reference_no           if bid valid
  | solicitation_no            if bid missing/"0" and solicitation present
  | award_reference_no           last resort

ocid = ocds-philgeps-{slugify(display_id)}
release.id = display_id   # original string, not slugified
```

### Slugification (`_slugify`)

Applied only to the OCID fragment, not to `release.id`:

- lowercase
- non-alphanumeric runs → single `-`
- trim leading/trailing `-`
- empty result → `unknown`

Example: display id `LG 2021-07-1869` → `ocid-philgeps-lg-2021-07-1869`, `release.id` stays `LG 2021-07-1869`.

### Why bid-first for display (not solicitation)

An earlier policy used `solicitation_no` as `release.id` when `bid_reference_no` was numeric-only (typical in S1/S2). That seemed user-friendly but **failed OCDS validation**:

- In S1 2004, **117** solicitation strings appear on rows with **different** bid refs.
- Eight separate processes could all get `release.id = "ITAFE2404"` and `ocid = ocds-philgeps-itafe2404`.
- libcoveocds reported **117** errors: *"Non-unique combination of ocid, id values @ releases"*.

**Bid refs are unique per process when present.** Solicitation remains available as human-readable metadata (see below) without being the primary key.

### Rejected policy (for reference)

```text
# DO NOT USE — caused 117 duplicate (ocid, id) errors on 2004 data
display_id = solicitation_no   if bid is numeric-only AND solicitation present
           | bid_reference_no  otherwise
```

---

## Step 3: Composite ids on collision

After all releases in a package are compiled, `resolve_release_display_collisions()` scans for duplicate `(ocid, id)` pairs. If any exist, **every release in the duplicate set** is rewritten to a **composite** display id.

```text
composite =
    {bid}-{solicitation}   if both available
  | {bid}-{award}          elif bid + award
  | {sol}-{award}          elif sol + award
  | fallback fields        otherwise

# If composite still collides, append -2, -3, … until unique
```

Each rewrite emits a **`display_id_collision`** DQ warning (package-level) with:

- `original_ocid`, `original_id`
- `resolved_ocid`, `resolved_id`
- `bid_reference_no`, `solicitation_no`

Stored in the transform report as `display_id_collisions` (see `.dq.json` / `.report.json`).

### When composites actually occur

With bid-first display, most packages need **no** composites. The 2004 full transform had **0** collisions after switching policy.

Composites are expected mainly when:

- `bid_reference_no` is `0` (missing),
- rows group at **award** level (different `award_reference_no`),
- but share the same **solicitation** fallback display id.

Example: two award-level groups both with `bid=0`, `solicitation_no=SHARED-SOL-001` → both initially get `id=SHARED-SOL-001` → resolved to `SHARED-SOL-001-AW-1` and `SHARED-SOL-001-AW-2` (pattern depends on available fields).

---

## Other OCDS identifiers (not `release.id`)

These are **separate** from `ocid` / `release.id` and serve different roles:

| OCDS path | Source | Purpose |
|-----------|--------|---------|
| `tender.id` | `bid_reference_no` | Tender/bid reference within the release (YAML mapping) |
| `philgeps.solicitationNo` | `solicitation_no` | Human-facing solicitation label |
| `awards[].id` | `award_reference_no` | One entry per distinct award in the process |
| `contracts[].id` | `award_reference_no` | Parallel to awards |
| `tender.items[].id` | `line_item_no` (+ disambiguation suffix) | Line items within the tender |

A single release can therefore have:

- `release.id = "39785"` (process key for OCDS package uniqueness)
- `tender.id = "39785"` (bid ref)
- `philgeps.solicitationNo = "BCDA-2004-0222"` (public label users recognize)
- `awards[].id ∈ {"6962", "6964", "6965", "6966"}` (per-award refs)

Browsers and search UIs should surface **solicitation** and **title** for humans; APIs and deduplication should key on **`ocid`** (and optionally `tender.id`).

---

## Worked examples

### BCDA-2004-0222 (S1, multi-award — normal case)

Four XLSX rows share bid `39785`, solicitation `BCDA-2004-0222`, awards `6962`–`6966`.

| Step | Value |
|------|-------|
| Group key | `bid:39785` |
| `release.id` | `39785` |
| `ocid` | `ocds-philgeps-39785` |
| Awards | 4 (`awards[]` / `contracts[]`) |
| Human label | `philgeps.solicitationNo = "BCDA-2004-0222"` |

### ITAFE2404 (S1 — why solicitation must not be `release.id`)

Eight different bid refs (`39710`, `39711`, …) share solicitation `ITAFE2404`.

| Policy | Result |
|--------|--------|
| Solicitation as `release.id` | 8 releases, same `(ocid, id)` → **libcoveocds failure** |
| Bid as `release.id` | 8 releases, unique ids → **valid** |

### S3 bid = `0` (fallback to solicitation)

| Field | Value |
|-------|-------|
| `bid_reference_no` | `0` → treated as missing |
| `solicitation_no` | `21-0471` |
| `award_reference_no` | `2997726` |
| Group key | `sol:21-0471` |
| `release.id` | `21-0471` |
| `ocid` | `ocds-philgeps-21-0471` |

---

## Data quality flags (identity-related)

| Rule | Severity | When |
|------|----------|------|
| `placeholder_bid_ref` | warning | `bid_reference_no` is `0` |
| `display_id_collision` | warning | Composite rewrite applied post-compile |
| `group_field_conflict` | error | Same process group disagrees on a process-level field |

---

## Validation

After transform, run OCDS validation on a package:

```powershell
.\.venv-validate\Scripts\python.exe scripts/validate_transform_sample.py `
  "references/transformed/full/2000-2012/Bid Notice and Award Details 2004.json"
```

2004 reference result (bid-first policy): **4,978 releases**, **0** libcoveocds errors, **0** `display_id_collisions`.

Unit tests: `scripts/test_ocds_compiler.py` (`test_multi_award_same_bid`, `test_display_id_collision_composite`).

---

## Decision summary

| Question | Answer |
|----------|--------|
| What groups rows? | `bid_reference_no` → `solicitation_no` → `award_reference_no` |
| What is `release.id`? | Same priority as display id: **bid first**, solicitation fallback |
| What is `ocid`? | `ocds-philgeps-{slug(display_id)}` |
| When is composite used? | Only when duplicate `(ocid, id)` remains after compile |
| Where does solicitation go? | `philgeps.solicitationNo`, not `release.id` |
| Why not solicitation-first? | Collides across unrelated processes; breaks OCDS uniqueness |
