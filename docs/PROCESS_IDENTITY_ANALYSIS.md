# Process identity field analysis (bid vs solicitation)

**Date:** 2026-06-28  
**Script:** `scripts/analyze_process_identity.py` → `scratch/out/process_identity_analysis.json`  
**Bid ref samples:** `scripts/analyze_bid_reference_samples.py` → `scratch/out/bid_reference_samples.json`  
**Related:** [ARCHITECTURAL_DECISIONS.md](ARCHITECTURAL_DECISIONS.md) ADR-009, ADR-011 · [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md)

## Question

For process-level OCDS releases, should we group and name processes using `bid_reference_no`, `solicitation_no`, or both — and does the answer depend on schema (S1–S5)?

## Short answer

| Role | Field | Rule |
|------|-------|------|
| **Grouping** (merge rows → one release) | `bid_reference_no` | Use whenever present and not `0`. Same across all schemas. |
| **OCID / release `id`** | `bid_reference_no` → `solicitation_no` → `award_reference_no` | Bid first; solicitation is fallback when bid missing/`0`. |
| **Composite id** | `{bid}-{sol}` etc. | Only when two compiled releases would share the same `(ocid, id)`; flagged `display_id_collision`. |
| **Fallback grouping** | `solicitation_no` → `award_reference_no` | Only when bid is missing or `0`. |

**Do not group by `solicitation_no` when a valid bid ref exists** — solicitation labels collide across unrelated processes.

**Do not use solicitation as default `release.id`** — in S1 2004, 117 solicitations map to multiple bid refs; libcoveocds rejects duplicate `(ocid, id)` pairs.

## Verified samples

### BCDA-2004-0222 (S1, 2004 XLSX)

| Canonical field | Source column (S1) | Value (all 4 rows) |
|-----------------|-------------------|---------------------|
| `bid_reference_no` | Reference ID | `39785` |
| `solicitation_no` | Solicitation No. | `BCDA-2004-0222` |
| `award_reference_no` | Award No. | `6962`, `6964`, `6965`, `6966` |

- Grouping by **bid `39785`** → 1 process, 4 awards (correct).
- Public OCID / `id`: **`39785`** / `ocds-philgeps-39785`.
- Human solicitation **`BCDA-2004-0222`** on `philgeps.solicitationNo` (not the release `id`).

### S1/S2 (2004 sample, 8,250 awarded rows)

| Metric | Value |
|--------|-------|
| `bid_reference_no` numeric-only | **100%** |
| bid == solicitation when both present | **0%** |
| Multi-award processes (by bid) | 903 (max 115 awards/bid) |
| Solicitations mapping to **multiple** bid refs | **117** (e.g. `ITAFE2404` → 8 bids) |

→ Bid is the stable process key for grouping **and** for OCDS `id` uniqueness.

### S3 (2021 & 2024 CSV, ~15k awarded rows sampled)

| Metric | 2021 | 2024 |
|--------|------|------|
| bid present | 95.6% | 96.5% |
| bid numeric-only | 100% | 100% |
| bid == solicitation | 0% | 0% |
| Multi-award by bid | 162 | 193 |
| Multi-award by solicitation | 280 | 282 |
| **One solicitation → many bids** | **679** (max **62** bids for `2021-001`) | (same pattern) |
| One bid → many solicitations | **0** | **0** |

→ **Always group by bid.** Solicitation-only grouping would merge dozens of unrelated tenders that reuse generic numbers like `2021-001` or `001`.

Example multi-award under one bid (2021):

- bid `7618302` / solicitation `2021-04-0028` → **6** award refs.

### S4/S5 (2024 Q4 V2 CSV, ~7k awarded rows)

| Metric | Value |
|--------|-------|
| `solicitation_no` present | **0%** (column absent in export) |
| Multi-award by bid | 293 (max **55** awards/bid) |

→ **Bid reference only.**

### Bid reference validity (20k-row samples, 2026-06-28)

| Source | Schema | Awarded rows | bid valid | `0` placeholder | null |
|--------|--------|--------------|-----------|-----------------|------|
| S1-2004 | S1 | 3,250 | 100% | 0% | 0% |
| S1-2002 | S1 | 281 | 100% | 0% | 0% |
| S2-2013Q1 | S2 | 376 | 100% | 0% | 0% |
| S2-2020Q4 | S2 | 299 | 100% | 0% | 0% |
| S3-2021 | S3 | 7,610 | 95.4% | 4.6% | 0% |
| S3-2024 | S3 | 8,051 | 97.0% | 3.0% | 0% |
| S3-2025 | S3 | 5,371 | 94.3% | 5.7% | 0% |
| S5-V2-Q4 | S4/5 | 9,772 | 95.1% | 4.9% | 0% |

S1/S2 bids are always usable for grouping. S3/S4/S5 rows with `bid_reference_no = 0` fall back to solicitation or award grouping per ADR-011.

## Why the Release browser showed 4 entries

The compiler output in `full/2004.json` already had **one** release (`ocds-philgeps-39785`, 4 awards). The browser read **stale** `by_year/2004.json` (still 4 award-level releases). Re-merge `by_year/` after ETL to fix.

**Update (2026-06-28):** Full corpus re-run completed under this policy — `by_year/2004.json` now has 4,978 process-level releases; verify in Release browser at `#/etl-releases/2004/ocds-philgeps-39785`.

## Implementation policy (compiler)

```text
group_key   = bid:{bid_reference_no}     # if bid valid
            | sol:{solicitation_no}      # if bid missing/0
            | award:{award_reference_no} # last resort

display_id  = bid_reference_no           # if bid valid
            | solicitation_no            # if bid missing/0
            | award_reference_no         # last resort

ocid        = ocds-philgeps-{slug(display_id)}

# post-compile (transform_to_ocds.py):
on duplicate (ocid, id): composite display_id + display_id_collision DQ warning
```

Re-run analysis:

```bash
python scripts/analyze_process_identity.py --sample 15000
```
