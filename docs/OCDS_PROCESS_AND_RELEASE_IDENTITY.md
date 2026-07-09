# OCDS process vs release identity — a primer

**Date:** 2026-06-28  
**Audience:** Anyone mapping PhilGEPS (or similar flat procurement exports) to [OCDS 1.1](https://standard.open-contracting.org/latest/en/)  
**Related:** [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md) (PhilGEPS implementation policy) · [PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md) · [ADR-009](ARCHITECTURAL_DECISIONS.md#adr-009-process-level-releases-one-process-many-awards)

This document explains a common stumbling block when learning OCDS: **what `ocid` and `release.id` mean, how they differ, and when one CSV row is *not* one OCDS release.**

Official references:

- [Identifiers — `ocid` and release ID](https://standard.open-contracting.org/latest/en/schema/identifiers/)
- [How does the OCDS work?](https://standard.open-contracting.org/latest/en/primer/how/)
- [Release schema](https://standard.open-contracting.org/latest/en/schema/reference/)
- [Updates and amendments](https://standard.open-contracting.org/latest/en/guidance/map/amendments/)

---

## The three layers (memorize this)

OCDS stacks identifiers at three different levels. Confusing them causes most mapping bugs.

| Layer | OCDS field | Identifies | Scope |
|-------|----------|------------|-------|
| **Process** | `ocid` | The whole contracting lifecycle (tender → award → contract → implementation) | Global (with registered prefix) |
| **Publication** | `release.id` | One **immutable snapshot** published about that process | Unique within the same `ocid` |
| **In-process objects** | `awards[].id`, `contracts[].id`, `tender.items[].id`, … | Individual awards, contracts, line items inside the process | Unique within the same `ocid` |

```text
Contracting process (ocid)
│
├── Release publications (release.id)     ← version / event history
│       release id=001  tag=tender
│       release id=002  tag=tenderAmendment
│       release id=003  tag=award
│
├── tender.items[]                        ← line items
├── awards[]                              ← one or many awards
└── contracts[]
```

**Key rule:** `ocid` answers *which process?* `release.id` answers *which publication about that process?* `awards[].id` answers *which award inside the process?*

---

## What `ocid` is for

An **Open Contracting ID** is a globally unique identifier for **one contracting process**.

OCDS defines a contracting process as:

> *All the actions aimed at implementing one or more contracts.*

Construction:

```text
ocid = {registered-prefix}-{internal-process-id}
```

Example: `ocds-87sd3t-OM-DGRMSG-004-13` (from the [identifiers guidance](https://standard.open-contracting.org/latest/en/schema/identifiers/)).

### Properties

1. **One process → one `ocid`**, stable for the life of that process.
2. **Many releases share the same `ocid`** — that is how OCDS joins tender, award, and contract data over time.
3. **`ocid` must not repeat across different processes** — two different bids must have two different `ocid` values.
4. **Case-sensitive** — the string must match exactly everywhere it appears.
5. **Not fuzzy** — `ocds-philgeps-39785` and `ocds-philgeps-39786` are different processes, not “similar” versions of the same one.

### Common misconception

> “Each release needs its own `ocid`.”

**Wrong.** Each *process* gets one `ocid`. Each *publication* about that process gets a new `release.id` but keeps the same `ocid`.

---

## What `release.id` is for

The root `id` on a release object identifies **this particular publication** — one immutable JSON document published at a point in time.

From the [release schema](https://standard.open-contracting.org/latest/en/schema/reference/):

> *Releases are immutable … a new release can be created by changing the release's `id` and `date`.*

### Properties

1. **Unique within the same `ocid`** — no two releases for one process may share the same `id`.
2. **Stable for the same release** — if you republish the exact same release in another package, keep the same `id`.
3. **Must not contain `#`** (used in URI fragments).
4. **Paired with `date`** — `date` is when *this release* was issued; it drives merge ordering.
5. **New information → new `id` + new `date`** — do not edit a published release in place.

### Uniqueness scope

| Pair | Must be unique? |
|------|-----------------|
| `(ocid, release.id)` | Yes — identifies one publication |
| `release.id` alone | No — two different processes can both use `id = "001"` |
| `ocid` alone | Yes per process — one `ocid` per contracting process globally |

Validators such as [libcoveocds](https://github.com/open-contracting/libcoveocds) enforce unique `(ocid, id)` pairs within a release package.

---

## Two publishing modes

The same OCDS rules apply, but what you emit depends on whether you publish **live** or **bulk historical** data.

### Live / incremental publishing

A publisher emits a **new release** every time process information changes:

```text
ocid: ocds-philgeps-39785          ← never changes for this bid

release id=001  date=2004-01-12  tag=tender
release id=002  date=2004-01-20  tag=tenderAmendment
release id=003  date=2004-01-14  tag=award
release id=004  date=2004-01-27  tag=contract
```

Consumers merge all releases with the same `ocid` into a **record** (`compiledRelease` + optional `versionedRelease`).

### Bulk / historical publishing (PhilGEPS flat exports)

Open-data exports are usually a **final snapshot**: one denormalized row per line item or award, with no event log. The honest representation is:

```text
one process  →  one ocid  →  one compiled release  →  tag: ["compiled"]
```

You are saying: *here is everything we know about this process at export time.*

For compiled snapshots, the [merging guidance](https://standard.open-contracting.org/latest/en/guidance/build/merging/) suggests an interim convention: `release.id = {ocid}-{date}` where `date` is the most recent underlying event. PhilGEPS currently uses the internal bid reference as `release.id` because there is only **one** release per process in each package — see [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md).

---

## PhilGEPS vocabulary vs OCDS vocabulary

PhilGEPS column names do not line up with OCDS terms. This table avoids the most common mix-up:

| PhilGEPS concept | Canonical field | OCDS role |
|------------------|-----------------|-----------|
| Bid / Reference ID | `bid_reference_no` | **Process key** → `ocid` (and often `tender.id`) |
| Solicitation No. | `solicitation_no` | Human label → `philgeps.solicitationNo` (not the process key) |
| Award No. | `award_reference_no` | **Per-award id** → `awards[].id` |
| Line item | `line_item_no` | **Per-item id** → `tender.items[].id` |

**PhilGEPS “bid”** ≈ one procurement/tendering exercise in the system.  
**OCDS `bids[]`** (bid extension) = a supplier’s bid submission. Different things.

When a valid `bid_reference_no` exists, it is the best available **process** identifier. Solicitation numbers are **not** safe as the process key — see [PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md) (e.g. `2021-001` maps to 62 different bids in S3).

---

## Worked example: BCDA-2004-0222 (bid `39785`)

Four rows from the 2004 XLSX export share one bid but have different awards and line items:

| Row | Line item | Award No | PO | Posted |
|-----|-----------|----------|-----|--------|
| 1 | ITEM1 | 6962 | PO#2004-01-001951 | 01/30/2004 |
| 2 | ITEM2 | 6964 | PO#2004-01-001952 | 01/29/2004 |
| 3 | ITEM3 | 6965 | PO#2004-01-001953 | 02/05/2004 |
| 4 | ITEM4 | 6966 | PO#2004-01-001954 | 02/05/2004 |

All rows share: bid `39785`, solicitation `BCDA-2004-0222`, notice date `01/12/2004`, award notice date `01/14/2004`, status `Awarded`.

### Wrong mapping (common mistake)

```text
4 CSV rows  →  4 releases  →  4 ocids (or 4 duplicate ocid/id pairs)
```

This treats each **award line** as its own contracting process. OCDS explicitly allows **multiple awards per process** (e.g. split among providers). The Release browser showed four entries until process-level grouping was fixed ([ADR-009](ARCHITECTURAL_DECISIONS.md#adr-009-process-level-releases-one-process-many-awards)).

### Correct mapping (bulk export)

```text
4 CSV rows  →  1 process  →  1 ocid  →  1 compiled release
                              │
                              ├── tender.items[]  → ITEM1 … ITEM4
                              └── awards[]        → 6962, 6964, 6965, 6966
```

```json
{
  "ocid": "ocds-philgeps-39785",
  "id": "39785",
  "tag": ["compiled"],
  "tender": {
    "id": "39785",
    "items": [ "ITEM1", "ITEM2", "ITEM3", "ITEM4" ]
  },
  "awards": [
    { "id": "6962" },
    { "id": "6964" },
    { "id": "6965" },
    { "id": "6966" }
  ]
}
```

Solicitation `BCDA-2004-0222` stays on `philgeps.solicitationNo` for human-readable search — not as `release.id`.

### Would multiple `release.id` values ever apply here?

**Only if** you were reconstructing a **timeline of publications**, not because there are four rows.

A live publisher *might* have emitted:

```text
ocid: ocds-philgeps-39785

id=001  date=2004-01-12  tag=tender     → RFQ posted
id=002  date=2004-01-14  tag=award      → award notice
id=003  date=2004-01-29  tag=award      → more awards posted
id=004  date=2004-02-05  tag=award      → final awards posted
```

Notes:

- Same **`ocid`** throughout.
- **`release.id`** increments per **publication event**, not per CSV row.
- Later releases add or update `awards[]`; they do not create new processes.

The slightly different **Posted** dates (01/29–02/05) *could* justify multiple historical releases if you had evidence each date was a distinct disclosure event. Even then, the unit of release is **what changed in the process**, not **one row = one release**.

---

## Decision flowchart

```text
Do these rows share the same bid_reference_no (and same tender)?
│
├─ YES → ONE ocid (one contracting process)
│         │
│         ├─ Multiple award_reference_no / line items?
│         │     → multiple awards[] / items[] in ONE release (bulk)
│         │     → NOT multiple ocids
│         │
│         └─ Process updated on different calendar dates (live publisher)?
│               → SAME ocid, NEW release.id per publication
│
└─ NO → separate ocids (separate processes)
          │
          └─ Known relationship (re-tender, framework, planning)?
                → link with relatedProcesses (optional)
```

---

## When is a “parent” above the bid needed?

Sometimes one business “project” spans multiple PhilGEPS bids. OCDS does **not** require a parent `ocid` for every case, but `relatedProcesses` can link them.

| Situation | Same `ocid`? | How to model |
|-----------|--------------|--------------|
| Multi-award under one tender | Yes | One process, many `awards[]` |
| Tender amended / rescheduled, **same bid ref** | Yes | New release (`tenderAmendment`), same `ocid` |
| Failed tender, **new bid ref** | No | New `ocid`; optional `relatedProcesses` |
| Framework → call-offs | No (usually) | Parent framework `ocid`; children reference it |
| One solicitation label, many bids | No | **Do not** group by solicitation — each bid is its own process |

**Solicitation is usually not the parent.** Sample analysis shows many solicitation strings map to dozens of unrelated bids ([PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md)).

**Rule of thumb:** same internal process key in the source system → same `ocid`. New process key → new `ocid`.

---

## FAQ

### Does `ocid` need to be unique across all releases?

**Yes and no — read carefully.**

- **`ocid` is unique per contracting process** across the entire OCDS universe (with prefix).
- **Many releases reuse the same `ocid`** when they describe the same process.
- **Different processes must never share an `ocid`.**

So: `ocid` is globally unique *as a process identifier*, not *one per release document*.

### If two releases have the same `ocid`, are they the same process?

**Yes** — exact string match on `ocid` means same process. Use `release.id` and `date` to tell publications apart.

### One PhilGEPS bid = one OCDS release?

- **Process (`ocid`):** yes — one bid → one process when `bid_reference_no` is valid.
- **Release object:** in bulk export, yes — one compiled release per bid.
- **Live publishing:** one bid → one `ocid`, but **many** releases over time.

### One CSV row = one OCDS release?

**No.** Flat exports are denormalized. Many rows often belong to one process (multi-award, multi-line-item). Group first, then compile.

### Can `release.id` equal the bid reference?

**In a one-shot compiled export:** yes, that is what this repo does.  
**In a live system:** only for the first snapshot — later updates need new `release.id` values.

---

## Where this repo implements the rules

| Concern | Document / code |
|---------|-----------------|
| Grouping rows into processes | [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md), `scripts/_ocds_compiler.py` |
| Why bid beats solicitation | [PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md), [ADR-011](ARCHITECTURAL_DECISIONS.md#adr-011-process-identity-group-vs-display) |
| Why one release, many awards | [ADR-009](ARCHITECTURAL_DECISIONS.md#adr-009-process-level-releases-one-process-many-awards) |
| Validation of `(ocid, id)` uniqueness | [VALIDATION.md](VALIDATION.md) |

---

## Further reading

- [OCDS primer — releases and records](https://standard.open-contracting.org/latest/en/primer/releases_and_records/)
- [OCDS merging guidance](https://standard.open-contracting.org/latest/en/guidance/build/merging/)
- [Register an OCID prefix](https://standard.open-contracting.org/latest/en/guidance/build/#register-an-ocid-prefix)
