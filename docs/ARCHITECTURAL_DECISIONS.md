# Architectural decisions (ADR log)

A chronological record of **why** the PhilGEPS → OCDS pipeline is shaped the way it is: what we chose, what we rejected, what changed later, and where the code lives.

This is not a tutorial — see [TRANSFORM.md](TRANSFORM.md) and [ETL_PIPELINE.md](ETL_PIPELINE.md) for how to run things. This document is for **design intent and history**.

---

## How to read and extend this log

Each entry uses a short **ADR** id (`ADR-NNN`), a **status**, and four sections:

| Section | Purpose |
|---------|---------|
| **Context** | Problem or constraint that forced a choice |
| **Decision** | What we actually built |
| **Consequences** | Trade-offs, follow-on work, things that break if you ignore it |
| **Updates** | Later changes to this decision (supersession, refinements) |

**Status values**

| Status | Meaning |
|--------|---------|
| **Accepted** | Current intended behaviour |
| **Superseded** | Replaced by a later ADR (link included) |
| **Deprecated** | Still in code paths but scheduled for removal |
| **Proposed** | Not implemented yet |

When you change pipeline semantics, add a new ADR and mark the old one **Superseded**. Do not silently rewrite history — append an **Updates** note on the old entry.

---

## Index

| ID | Date | Title | Status |
|----|------|-------|--------|
| [ADR-001](#adr-001-canonical-53-field-model) | 2025 | Canonical 53-field model | Accepted |
| [ADR-002](#adr-002-yaml-as-single-source-of-truth) | 2025 | YAML as single source of truth | Accepted |
| [ADR-003](#adr-003-data-quality-gate-before-compilation) | 2025 | Data-quality gate before compilation | Accepted |
| [ADR-004](#adr-004-initial-release-grouping-by-award_reference_no) | 2025–2026 | Initial release grouping by `award_reference_no` | Superseded → [ADR-009](#adr-009-process-level-releases-bid-first-grouping) |
| [ADR-005](#adr-005-streaming-etl-for-multi-gb-exports) | 2026 | Streaming ETL for multi-GB exports | Accepted |
| [ADR-006](#adr-006-calendar-year-merge-with-ocid-dedup) | 2026 | Calendar-year merge with `ocid` dedup | Accepted |
| [ADR-007](#adr-007-combined-dataset-report) | 2026 | Combined dataset report | Accepted |
| [ADR-008](#adr-008-memory-safe-json-serialization) | 2026 | Memory-safe JSON serialization | Accepted |
| [ADR-009](#adr-009-process-level-releases-bid-first-grouping) | 2026-06-27 | Process-level releases (one process, many awards) | Accepted |
| [ADR-010](#adr-010-unified-run-reports-for-webapp) | 2026 | Unified run reports for webapp | Accepted |
| [ADR-011](#adr-011-process-identity-group-vs-display) | 2026-06-28 | Process identity: group key vs display OCID | Accepted |
| [ADR-012](#adr-012-year-by-year-release-browser) | 2026-06-28 | Year-by-year Release browser caches | Accepted |
| [ADR-013](#adr-013-year-vs-corpus-data-quality) | 2026-06-28 | Year vs corpus data quality | Accepted |
| [ADR-014](#adr-014-release-browser-deep-links) | 2026-06-28 | Release browser deep links | Accepted |
| [ADR-015](#adr-015-demo-data-infrastructure) | 2026-07-09 | Demo data infrastructure for lightweight development | Accepted |

---

## Timeline (high level)

```
2025     Canonical schema + OCDS staging rules (config/)
         Reference webapp reads generated bundle, not raw YAML

2026     Full corpus ETL (54 exports → full/ → by_year/)
         Schema verification run (S1–S5 headers vs schema_mappings.yaml)
         Memory fixes on largest JSON writes
         combined.report.json for dataset-wide DQ roll-up
         Release browser in webapp (structured summaries + raw JSON)

2026-06-27  Process-level OCDS releases (one ocid per process, multiple awards[])
            Supersedes award-level grouping (ADR-004)

2026-06-28  Process identity refined: group by bid_reference_no; OCID/id from
            bid_reference_no (solicitation fallback); composite id + DQ flag on
            display_id_collision only when (ocid, id) pairs collide. Sample analysis in
            PROCESS_IDENTITY_ANALYSIS.md. Release browser loads per-year caches.
            Year vs corpus DQ split (ADR-013). Release browser hash routes (ADR-014).
            Full corpus re-run completed (54 sources → 3.61M releases in by_year/).

2026-07-09  Demo data infrastructure for lightweight development (ADR-015).
            24-year demo dataset (2000-2025) with ~18,000 releases, ~74MB storage.
            Enables instant clone, fast webapp startup, and git-friendly workflow.
            Full dataset (10GB+) remains available on Google Drive for complete analysis.
```

---

## Decisions

### ADR-001: Canonical 53-field model

**Status:** Accepted  
**Date:** 2025 (initial mapping work)

#### Context

PhilGEPS open exports span **five schema periods (S1–S5)** with different column names, counts (40 → 43 → 46), and formats (XLSX vs CSV). Downstream code cannot branch on column **index** without breaking when a new export era appears.

#### Decision

Normalize every export to **53 canonical fields** defined in `config/schema_mappings.yaml`, with typed fields (`field_types`: string, decimal, date, string_array, …).

Schema detection uses **marker column sets** (S4 markers checked before S3, etc.) in `transform_to_ocds.py`.

#### Consequences

- New export layouts add a `schema_N` block — never patch ingest by position.
- Unmapped source columns are dropped at canonicalize time and listed in `.dq.json`.
- Verified 2026-06-27: S1–S3 match docs; main `2025.csv` is still S3 (43 cols); true S4/S5 layout lives in `raw/Misc` V2 files — see [SCHEMA_VERIFICATION_AND_MAPPING_RUN.md](SCHEMA_VERIFICATION_AND_MAPPING_RUN.md).

#### Updates

- None.

---

### ADR-002: YAML as single source of truth

**Status:** Accepted  
**Date:** 2025

#### Context

The repo serves both **human readers** (crosswalk markdown, webapp) and **machines** (ETL). Duplicating mapping rules in Python and JSON caused drift between the sample builder and the real compiler.

#### Decision

| Concern | Source of truth | Consumers |
|---------|-----------------|-----------|
| Export column → canonical | `config/schema_mappings.yaml` | `transform_to_ocds.py`, `build_schema_field_map.py` |
| Canonical → OCDS paths | `config/canonical_to_ocds.yaml` | `_ocds_compiler.py`, sample builder |
| PhilGEPS label → OCDS code | `config/ocds_codelist_mappings.yaml` | `_ocds_compiler.py` |

Generated artifacts (`PHILGEPS_CANONICAL_FIELD_MAP.json`, `app/src/data/schema_bundle.json`, crosswalk tables) are **outputs**, not edited by hand.

#### Consequences

- Mapping changes flow: **config → `build_schema_field_map.py` → references + webapp bundle**.
- Compiler behaviour changes require updating YAML **and** `_ocds_compiler.py` when structure (not just paths) changes — e.g. multi-award releases ([ADR-009](#adr-009-process-level-releases-bid-first-grouping)).

#### Updates

- **2026-06-27:** `canonical_to_ocds.yaml` `generated.ocid.from` prefers `bid_reference_no` before `award_reference_no` ([ADR-009](#adr-009-process-level-releases-bid-first-grouping)).

---

### ADR-003: Data-quality gate before compilation

**Status:** Accepted  
**Date:** 2025

#### Context

Real exports contain `NULL` literals, placeholder ids (`0`), malformed dates, and “awarded” rows missing awardee fields. Feeding these directly into OCDS compilation produces invalid or unidentifiable releases.

#### Decision

Run `scripts/_data_quality.py` **before** grouping and compilation:

| Severity | Effect |
|----------|--------|
| `error` | Row quarantined — excluded from grouping |
| `warning` | Row compiled; issue logged |
| `info` | Logged; e.g. un-awarded tenders skipped without treating missing award ref as error |

Group-level validation runs after row grouping (`validate_group`, `validate_process_group`).

Reports land in `.dq.json` and unified `.report.json` with **capped samples** so multi-GB runs stay reviewable.

#### Consequences

- Policy lives in `_data_quality.py`; the transformer only decides “compile or skip” based on `report.fatal`.
- Adding a rule improves the next run everywhere (CLI, batch ETL, webapp embed) without UI changes.

#### Updates

- **2026-06-27:** Split group validation into process-level (`validate_process_group`) and award-level (`validate_group`) — [ADR-009](#adr-009-process-level-releases-bid-first-grouping).

---

### ADR-004: Initial release grouping by `award_reference_no`

**Status:** Superseded by [ADR-009](#adr-009-process-level-releases-bid-first-grouping)  
**Date:** 2025–2026 (initial ETL)

#### Context

PhilGEPS flat exports are **denormalized**: the same award repeats on many rows with different line items. The first working pipeline needed a simple, stable grouping key that exists on almost every awarded row across S1–S5 (`Award No.` / `Award Reference No.` → `award_reference_no`).

S3/S4 often set `bid_reference_no` to `0`, so award ref was the only reliable identifier in those eras.

#### Decision

- Group CSV/XLSX rows by **`award_reference_no`**.
- Compile **one OCDS release per award** via `compile_grouped()`.
- Set `ocid = ocds-philgeps-{slug(award_reference_no)}` and release `id = award_reference_no`.
- Merge all rows in the group into `tender.items[]` and mirror them on `awards[0].items[]`.

#### Consequences

- **Correct** for single-award, multi-line-item exports (common case).
- **Incorrect** for one bid with **multiple award numbers** (e.g. BCDA-2004-0222 with awards 6962, 6964, 6965, 6966) — the Release browser showed four separate releases instead of one contracting process.
- Release count ≈ row count for multi-award bids; `by_year/` dedup by `ocid` treated each award as a distinct process.

#### Updates

- **2026-06-27:** Superseded. Root cause: OCDS models a **contracting process** (one `ocid`) with multiple `awards[]`, not one release per award line. See [ADR-009](#adr-009-process-level-releases-bid-first-grouping).

---

### ADR-005: Streaming ETL for multi-GB exports

**Status:** Accepted  
**Date:** 2026

#### Context

2024-era CSV exports exceed **300 MB** (~millions of rows). Loading entire files or building full in-memory JSON strings is not viable on typical dev machines.

#### Decision

- **CSV path:** `transform_to_ocds.py` streams with `csv.DictReader` — one row at a time, group in memory by process key, compile after the file pass.
- **XLSX path:** `scratch/sample_and_transform.py` with `--full` uses openpyxl (workbook load — acceptable for quarterly files, not for full CSV scale).
- **Batch orchestration:** `run_full_dataset.py` with `--resume` skips files that already have `.report.json`.

#### Consequences

- Peak memory is dominated by **group sizes** and **release list size**, not raw CSV width.
- Very large single-file packages still need compact JSON writes ([ADR-008](#adr-008-memory-safe-json-serialization)).

#### Updates

- **2026-06-27:** Grouping key changed to process-level ([ADR-009](#adr-009-process-level-releases-bid-first-grouping)); streaming model unchanged.

---

### ADR-006: Calendar-year merge with `ocid` dedup

**Status:** Accepted  
**Date:** 2026

#### Context

Source files overlap by calendar year (quarterly XLSX + annual CSV + V2 quarterly CSV). Consumers want **one package per year**, not 54 separate files.

#### Decision

`scripts/merge_ocds_by_year.py`:

- Merges all releases whose `date` falls in a calendar year into `references/transformed/by_year/<year>.json`.
- **Dedup rule:** within a year, later source files **overwrite** releases with the same `ocid` (e.g. full-year 2024 CSV wins over Q4 V2 quarterly export).

#### Consequences

- `ocid` stability matters for dedup — changing grouping semantics ([ADR-009](#adr-009-process-level-releases-bid-first-grouping)) changes which releases collide and **lowers release counts** where one bid had multiple awards.
- Full dataset re-run required after `ocid` policy changes; do not assume old `by_year/` reflects new semantics.

#### Updates

- **Pending (2026-06-27):** Re-run `run_full_dataset.py` after ADR-009 implementation.
- **2026-06-28:** Full corpus re-run completed under ADR-011 identity rules (54 sources, 25 calendar years, ~3.61M deduplicated releases in `by_year/`).

---

### ADR-007: Combined dataset report

**Status:** Accepted  
**Date:** 2026

#### Context

Per-file `.report.json` files are fine for debugging one export but too heavy to embed in the webapp (~54 files). Dashboard-style views need **one small aggregate** (~100 KB).

#### Decision

Add `scripts/aggregate_dataset_report.py` → `references/transformed/combined.report.json`:

- Rolls up `layers.source_dq` across all source files
- Per-year slice in `years[]`
- `summary`, `top_findings`, `webapp` pointers for bundle embed

Wired into `build_schema_field_map.py` so the **ETL Pipeline** webapp section prefers `combined.report.json` when present.

#### Consequences

- Webapp shows full-dataset stats and by-year table without loading multi-GB JSON.
- Regenerate after any full ETL: runs at end of `merge_ocds_by_year.py` or standalone.

#### Updates

- None.

---

### ADR-008: Memory-safe JSON serialization

**Status:** Accepted  
**Date:** 2026

#### Context

Full-year packages (e.g. 2024 with ~1.7M+ releases under old grouping, or large post-merge writes) hit **`MemoryError`** when building a single pretty-printed JSON string via `json.dumps()` on the entire package.

#### Decision

- Write large packages with **`json.dump()` to a file stream** (compact, no indent) in `transform_to_ocds.py` and `merge_ocds_by_year.py`.
- Threshold: packages with **>200k releases** use compact single-line JSON.

#### Consequences

- Output files are harder to `diff` by eye; use `jq` or sample-based validation.
- A failed mid-write can leave a corrupt empty file — re-run merge/transform for that artifact.

#### Updates

- None.

---

### ADR-009: Process-level releases (one process, many awards)

**Status:** Accepted  
**Date:** 2026-06-27

#### Context

Review of sample **BCDA-2004-0222** showed four CSV rows with the same contracting process but different `award_reference_no` values (6962, 6964, 6965, 6966). Under [ADR-004](#adr-004-initial-release-grouping-by-award_reference_no), the pipeline emitted **four releases** — valid-looking in the UI but wrong against OCDS process semantics.

OCDS expectation: **one contracting process** → one `ocid`, one release, `tender` + multiple `awards[]` / `contracts[]`.

#### Decision

| Aspect | Behaviour |
|--------|-----------|
| **Grouping** | Rows with the same process identity (see [ADR-011](#adr-011-process-identity-group-vs-display)) compile to **one** release |
| **`tender.items[]`** | All rows in the process group |
| **`awards[]` / `contracts[]`** | One entry per distinct `award_reference_no`; items scoped to that award subgroup |
| **Parties** | Merged across all awards in the process |
| **DQ** | `validate_process_group()` for process fields; `validate_group()` per award subgroup |

**Example (BCDA-2004-0222, S1):**

- S1 maps **Reference ID** → `bid_reference_no` (`39785`), **Solicitation No.** → `solicitation_no` (`BCDA-2004-0222`)
- 1 release, 4 tender items, 4 awards, 4 contracts
- Public `ocid` / `id`: `39785` / `ocds-philgeps-39785` (via ADR-011); human solicitation on `philgeps.solicitationNo`

#### Implementation touchpoints

| File | Change |
|------|--------|
| `scripts/_ocds_compiler.py` | Rewrote `compile_grouped()`; `process_group_key()`, `_process_identity()` |
| `scripts/transform_to_ocds.py` | Group by process key; `validate_process_group()` |
| `scripts/_data_quality.py` | `PROCESS_CONFLICT_FIELDS`, `AWARD_GROUP_CONFLICT_FIELDS`, `validate_process_group()` |
| `config/canonical_to_ocds.yaml` | `generated.ocid.from`: bid before award |
| `scratch/sample_and_transform.py` | Same grouping as production CSV path |
| `scripts/test_ocds_compiler.py` | `test_multi_award_same_bid` (BCDA pattern) |
| `docs/TRANSFORM.md`, `docs/ETL_PIPELINE.md` | Grouping semantics updated |

#### Consequences

- Release counts **drop** wherever one process previously produced N award-level releases.
- `by_year/` dedup keys change — **full ETL re-run required** after any grouping/ocid change.
- Rows with `bid_reference_no = 0` fall back to solicitation or award grouping ([ADR-011](#adr-011-process-identity-group-vs-display)).

#### Updates

- **2026-06-28:** Grouping vs display split formalized in [ADR-011](#adr-011-process-identity-group-vs-display). Partial ETL run (25/55 files, started 2026-06-28) **aborted** — superseded by clean full re-run same day (see timeline).

---

### ADR-010: Unified run reports for webapp

**Status:** Accepted  
**Date:** 2026

#### Context

Operators need one artifact per transform that combines **source DQ**, **shape pre-flight**, and optional **libcoveocds** results — without opening three files per export.

#### Decision

Each transform emits:

| File | Role |
|------|------|
| `<out>.json` | OCDS release package |
| `<out>.dq.json` | Raw DQ detail |
| `<out>.report.json` | Unified report via `_unified_report.py` |

Webapp **ETL Pipeline** section:

- Aggregate stats from `combined.report.json` when present
- **Release browser:** per-calendar-year caches (see [ADR-012](#adr-012-year-by-year-release-browser))
- **Year data quality** / **Corpus data quality** (see [ADR-013](#adr-013-year-vs-corpus-data-quality))
- Capped DQ/warning samples to keep bundle size bounded

#### Consequences

- `build_schema_field_map.py` must be re-run after ETL to refresh stats (no longer embeds full release JSON in bundle).
- Sample caps mean rare edge cases may not appear in the UI until you inspect `.dq.json` directly.

#### Updates

- **2026-06-27:** Input samples in transform output may include `process_key` and `bid_reference_no` after [ADR-009](#adr-009-process-level-releases-bid-first-grouping).
- **2026-06-28:** Release browser moved to year-by-year fetch ([ADR-012](#adr-012-year-by-year-release-browser)); superseded embedded `releases_sample` approach for full-dataset browsing.
- **2026-06-28:** Data quality split into per-year caches vs corpus roll-up ([ADR-013](#adr-013-year-vs-corpus-data-quality)); year iteration uses `by_year/dq/<year>.json`, not `combined.report.json` samples alone.

---

### ADR-011: Process identity: group key vs display OCID

**Status:** Accepted  
**Date:** 2026-06-28

#### Context

Process-level grouping ([ADR-009](#adr-009-process-level-releases-bid-first-grouping)) raised whether to use `bid_reference_no` or `solicitation_no` as the process key. Schema periods differ:

| Schema | Bid column | Typical bid value | Solicitation column |
|--------|------------|-------------------|---------------------|
| S1/S2 | Reference ID | **Numeric** internal id (e.g. `39785`) | Human ref (e.g. `BCDA-2004-0222`) |
| S3 | Bid Reference No. | Numeric system id (e.g. `7618302`) | Different human string (e.g. `2021-04-0028`) |
| S4/S5 | Bid Reference No. | Numeric when present | **Absent** in export |

Additionally, **many S3/S4 rows set `bid_reference_no` to `0`** (placeholder — column decommissioned in some exports). Those rows cannot group by bid.

Sample analysis (`scripts/analyze_process_identity.py`, `docs/PROCESS_IDENTITY_ANALYSIS.md`) showed:

- **679** solicitation labels in S3 map to **multiple** bid refs (e.g. `2021-001` → 62 bids) — **unsafe for grouping**
- **117** solicitations in S1 map to multiple Reference IDs — same problem
- **0** bids map to multiple solicitations in S3 sample — bid is the stable grouper when valid

#### Decision

Split **grouping** from **display**:

```text
group_key   = bid:{bid_reference_no}     if bid valid and not "0"
            | sol:{solicitation_no}      if bid missing/0 and solicitation present
            | award:{award_reference_no} last resort

display_id  = bid_reference_no           if bid valid
            | solicitation_no            if bid missing/0 and solicitation present
            | award_reference_no           last resort

ocid        = ocds-philgeps-{slug(display_id)}

# After compile, if multiple releases share the same (ocid, id):
composite   = {bid}-{solicitation} | {bid}-{award} | {sol}-{award}  (as available)
DQ          = display_id_collision (warning) per rewritten release
```

**`bid_reference_no = 0`:** treated as missing (`_valid_ref`); row groups by solicitation or award. DQ logs `placeholder_bid_ref` (warning). Common in S3 CSV samples (~20–30% of rows in some years); S4/S5 V2 exports use numeric bid refs when present (~95% on awarded rows).

**Why bid-first for display:** libcoveocds requires unique `(ocid, id)` per release. In S1 2004, **117** solicitation labels map to multiple bid refs (e.g. `ITAFE2404` → 8 bids). Using solicitation as `release.id` produced 117 duplicate-key validation errors; bid refs are unique per process when present.

#### Consequences

- BCDA case: group by `bid:39785`, public `id` / `ocid` slug `39785` / `ocds-philgeps-39785`; solicitation `BCDA-2004-0222` remains on `philgeps.solicitationNo` and `tender` metadata.
- Never group by solicitation when a valid bid exists.
- Composite ids are rare — only when fallback display ids still collide (e.g. bid `0`, same solicitation, different award-level groups).
- Any ETL run started before this rule was finalized must be **re-done** (not resumed).

#### Updates

- **2026-06-28:** Full policy documented in [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md).

---

### ADR-012: Year-by-year Release browser caches

**Status:** Accepted  
**Date:** 2026-06-28

#### Context

Embedding up to 50 releases in `schema_bundle.json` could not scale to the full corpus, went stale during partial ETL, and could not reflect per-year progress. Multi-GB `by_year/<year>.json` files cannot load in the browser whole.

#### Decision

- **Build step:** `merge_ocds_by_year.py` writes `by_year/browser/<year>.json` via `scripts/_release_browser.py`
  - `index[]`: up to 10,000 `ReleaseSummary` entries per year (list + search)
  - `releases{}`: up to 80 full releases for Raw JSON tab (first N + multi-award examples)
- **Standalone rebuild:** `scripts/build_year_browser_cache.py --years …`
- **Dev server:** Vite serves `/data/releases/{year}.json` from `references/transformed/by_year/browser/`; `/data/release/{year}/{ocid}.json` for on-demand full releases; CORS + `allowedHosts` for tunneling (e.g. `ocdsphilgeps.simple-systems.dev`)
- **Webapp:** `ReleaseBrowser` year selector + fetch on demand; hash routes `#/etl-releases/{year}` and `#/etl-releases/{year}/{ocid}` (see [ADR-014](#adr-014-release-browser-deep-links)); `build_schema_field_map.py` sets `release_browser_base_url`

#### Consequences

- After merge, run browser cache build (automatic at merge time, or manual for one year).
- Restart `npm run dev` after vite.config changes so `/data/releases/` is served.
- `by_year/` must be re-merged when `full/` changes — stale year packages showed award-level releases until refresh (seen with BCDA 2004).

#### Updates

- **2026-06-28:** Deep-link routes and dev-server CORS documented in [ADR-014](#adr-014-release-browser-deep-links).

---

### ADR-013: Year vs corpus data quality

**Status:** Accepted  
**Date:** 2026-06-28

#### Context

`combined.report.json` and `schema_bundle.json` embed corpus-wide DQ roll-ups for the webapp. During partial ETL (e.g. re-transforming only 2004), those aggregates mix **fresh** and **stale** per-source `.dq.json` sidecars. Merged warning samples then lack `row_entry` / `raw_row` context from newer transform runs, and severity counts no longer match the year you are iterating on.

The Release browser already solved a similar problem with per-year caches ([ADR-012](#adr-012-year-by-year-release-browser)): load one calendar year on demand instead of embedding the full corpus.

#### Decision

Split **year-scoped** and **corpus-scoped** DQ in the pipeline and webapp:

- **Build step:** `scripts/_year_dq.py` merges source `.dq.json` sidecars for one calendar year into `references/transformed/by_year/dq/<year>.json`
  - Uses the same `merge_diverse_dq_samples()` logic as corpus aggregation, with full transform-time sample context (`row_entry`, `raw_row`)
  - Invoked automatically from `merge_ocds_by_year.py` after year merge; standalone rebuild via `scripts/build_year_dq_cache.py --years …`
- **Dev server:** Vite serves `/data/dq/{year}.json` from `references/transformed/by_year/dq/`
- **Webapp:**
  - **Year data quality** (`EtlQualityPage`): year selector + fetch per-year DQ cache — default for iteration on one export/year
  - **Corpus data quality** (`EtlCorpusQualityPage`): corpus roll-up from `schema_bundle.json` / `combined.report.json` — only meaningful after a **full** ETL re-run of all source exports

Corpus aggregation (`aggregate_dataset_report.py`, ADR-007) remains for dataset-wide dashboards and the combined report artifact; it is not the primary UI during single-year work.

#### Consequences

- After merge (or transform), build or refresh year DQ cache: automatic at merge time, or `python scripts/build_year_dq_cache.py --years 2004`
- Restart `npm run dev` after `vite.config.ts` changes so `/data/dq/` is served
- **Corpus data quality** may show misleading samples until every source file is re-transformed — the page states this explicitly
- Year DQ counts come from source sidecars for that year's package(s), not from the merged `by_year/<year>.json` OCDS package

#### Updates

- **2026-06-28:** Full corpus re-run populated all 25 `by_year/dq/<year>.json` caches; corpus roll-up reflects 54 sources.

---

### ADR-014: Release browser deep links

**Status:** Accepted  
**Date:** 2026-06-28

#### Context

Operators and reviewers need shareable URLs that open a specific calendar year (and optionally a specific release) in the Release browser. The year selector alone does not survive refresh or work across deployments.

#### Decision

- **Hash routes:** `#/etl-releases/{year}` and `#/etl-releases/{year}/{ocid}` (e.g. `#/etl-releases/2004/ocds-philgeps-39785`)
- **Router:** `parseRoute()` / `routePageId()` in `app/src/components/Layout.tsx` — first path segment is the nav page id; further segments are params
- **Default:** visiting `#/etl-releases` redirects to the latest year with data
- **Sync:** year select and release list clicks call `navigate()` so back/forward and copy-link work
- **Dev tunnel:** `vite.config.ts` sets `server.allowedHosts` and CORS for `https://ocdsphilgeps.simple-systems.dev` when the static site fetches `/data/*` from a local or tunneled Vite dev server

#### Consequences

- Nav highlights **Release browser** for all `etl-releases/*` paths
- Document title includes the year when present
- Production static deploy still needs `release_browser_base_url` pointing at a host that serves `/data/releases/` and `/data/dq/` if cross-origin fetch is required

#### Updates

- None.

---

### ADR-015: Demo data infrastructure for lightweight development

**Status:** Accepted  
**Date:** 2026-07-09

#### Context

The full PhilGEPS corpus (10GB+) requires large file downloads and slow processing, creating barriers to:
- **Development**: New contributors can't clone and run immediately
- **CI/CD**: Pipelines need large storage and network bandwidth
- **VPS deployment**: Manual file transfers required
- **Testing**: Slow iteration cycles with full datasets
- **Git distribution**: Repository can't be self-contained

#### Decision

**Create lightweight demo datasets that maintain data realism while being git-friendly:**

1. **Raw CSV demo data** (`raw_demo/`): 200-row representative samples (~155 KB)
2. **Year-by-year OCDS demo packages** (`references/transformed/demo_by_year/`): 200-1000 releases per year (~74 MB total vs 10GB+ full dataset)
3. **Generation scripts**: Memory-efficient sampling from both raw CSV and transformed OCDS
4. **Webapp configuration**: Use demo data by default, fallback to full datasets
5. **Git strategy**: Include demo data, exclude full datasets (Google Drive only)

**Implementation:**
- `scripts/generate_demo_data.py` - Sample raw CSV exports
- `scripts/generate_year_demo_samples_efficient.py` - Stream year packages for large files
- `scripts/generate_webapp_caches.py` - Generate browser/DQ caches
- `app/vite.config.ts` - Configured for `demo_by_year/` directory
- `.gitignore` - Include demo data, exclude full datasets

**Diversity preservation:**
- Stratified sampling across procurement methods (19 modes)
- Organization type coverage (13+ types)
- Geographic representation (17+ regions)
- Schema period coverage (S1-S5, 2000-2025)

#### Consequences

- **Benefits**:
  - Clone time: 60x faster (seconds vs minutes)
  - Storage: 166x smaller (74MB vs 10GB+)
  - Webapp startup: instant vs 30+ seconds
  - Git-friendly: self-contained repository
  - CI/CD: Fast pipelines, no external dependencies
  - VPS: Simple git pull deployment

- **Trade-offs**:
  - Not suitable for production analysis (use Google Drive full datasets)
  - Requires regeneration when schema mappings change
  - Demo data needs periodic updates to stay representative

- **Maintenance**:
  - Full dataset remains available on Google Drive for complete analysis
  - Demo data can be regenerated with `python scripts/generate_year_demo_samples_efficient.py --years all`
  - Webapp automatically uses full datasets when placed in `by_year/`

#### Updates

- None.

---

## Related documents

| Doc | Role |
|-----|------|
| [OVERVIEW.md](OVERVIEW.md) | Repo purpose and data layers |
| [TRANSFORM.md](TRANSFORM.md) | Single-file pipeline and DQ rules |
| [ETL_PIPELINE.md](ETL_PIPELINE.md) | Full batch ETL, outputs, commands |
| [VALIDATION.md](VALIDATION.md) | OCDS validation layers |
| [PROCESS_IDENTITY_ANALYSIS.md](PROCESS_IDENTITY_ANALYSIS.md) | Bid vs solicitation samples and grouping policy |
| [SCHEMA_VERIFICATION_AND_MAPPING_RUN.md](SCHEMA_VERIFICATION_AND_MAPPING_RUN.md) | 2026-06-27 header verification run |

---

## Adding a new ADR

1. Pick the next id (`ADR-015`, …).
2. Add a row to the [index](#index).
3. Append a full section under [Decisions](#decisions).
4. If superseding an older entry, set its status to **Superseded** and link both ways.
5. Update the [timeline](#timeline-high-level) when the change is user-visible (grouping, `ocid`, report format, etc.).
