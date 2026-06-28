# Schema Evolution Verification & Cross-Schema Mapping Run

**Date:** 2026-06-27  
**Scope:** Verify documented PhilGEPS schema evolution (S1–S5) against files in `raw/` (excluding `raw/Misc` for primary inventory; S5 tested from `raw/Misc`), then sample 1,000 rows per representative file and run the OCDS transform pipeline.

**Related:** [TRANSFORM.md](TRANSFORM.md) · [ETL_PIPELINE.md](ETL_PIPELINE.md) · [references/philgeps-schema.md](../references/philgeps-schema.md) · [references/SCHEMA_FILES_COMPARISON.md](../references/SCHEMA_FILES_COMPARISON.md)

---

## Actions Taken

1. **Header verification** — Read actual column headers from one file per schema/year using `scratch/verify_headers.py` and `scratch/verify_xlsx_headers.py`.
2. **Cross-check** — Compared detected headers against `config/schema_mappings.yaml` (S1–S5 column maps).
3. **Sampling + transform** — `scratch/sample_and_transform.py`: reservoir-sample 1,000 rows per file, canonicalize, data-quality gate, group by `award_reference_no`, compile to OCDS release package.
4. **Validation** — `scratch/validate_ocds.py` using `libcoveocds` (OCDS 1.1 schema).
5. **Fixes applied during run:**
   - XLSX dates: `openpyxl` returns `datetime` objects; added normalization in sampler + extended `parse_date()` in `_data_quality.py` for ISO input.
   - CSV streaming: reservoir sampling without loading multi-GB files into memory.
   - Microsecond timestamps (S3 CSV): `parse_date()` now strips sub-second precision so `_ocds_checks` pre-flight passes.

**Artifacts:** `scratch/out/*.json`, `*.dq.json`, `*.validation.json`

---

## Schema Evolution Verification

### Summary: documentation vs reality

| Claim (philgeps-schema.md) | Verified? | Notes |
|----------------------------|-----------|-------|
| S1: 2000–2015, 40 cols, `UOM`, XLSX header row 3 | **Mostly** | Headers at **row 4** (1-based), not row 3 — docs use 0-based indexing. Columns match exactly. |
| S2: 2016–2020, only change `UOM` → `Unit of Measurement` | **Yes** | Transition confirmed between **Q4 2015 and Q1 2016**. |
| S3: 2021–2024, 43 cols, CSV | **Yes** | All 43 columns match. `Created By` / `Awardee Contact Person` intentionally excluded in mapping (privacy). |
| S4: 2025, 46 cols, location fields | **No for main export** | `raw/PHILGEPS -- 2021-2025 (CSV)/2025.csv` is still **43-column S3**, not S4. |
| S5: 2021–2024-V2, same as S4 | **Partial** | Only one V2 file present: `raw/Misc/.../2024-10 -- 2024-12.csv` (46 cols, S4 structure). |

### Header row index (XLSX)

All tested XLSX files (2002–2021 Q2) have the header on **row 4** (1-based). Rows 1–3 are metadata/empty. The schema doc says "row 3" meaning 0-based.

### S1 vs S2 boundary

| File | Col 21 | Schema |
|------|--------|--------|
| Jan–Mar 2013 | `UOM` | S1 |
| Oct–Dec 2015 | `UOM` | S1 |
| Jan–Mar 2016 | `Unit of Measurement` | S2 |
| Oct–Dec 2020 | `Unit of Measurement` | S2 |
| Apr–Jun 2021 (XLSX) | `Unit of Measurement` | S2 |

2013–2015 files in `PHILGEPS 2013-2021/` are still **S1**, not S2. S2 starts in 2016.

### S3 vs S4/S5 column sets

**S3 (43 cols)** — `Procuring Entity`, `Bid Reference No.`, … `List of Bidder's`  
Present in: `2021.csv`, `2024.csv`, **`2025.csv`** (mislabeled as S4 in some docs).

**S4/S5 (46 cols)** — `Procuring Entity (PE)`, `Region`, `Province`, … `Awardee Joint Venture`  
Present in: `raw/Misc/PHILGEPS -- 2021 - 2025 (CSV) V2/2024-10 -- 2024-12.csv`

### `schema_mappings.yaml` alignment

| Schema key | Mapped cols | Header match (verified files) |
|------------|-------------|-------------------------------|
| `schema_1` | 40 | 100% — S1 XLSX (2002, 2012, 2013 Q1) |
| `schema_2` | 40 | 100% — S2 XLSX (2016, 2020) |
| `schema_3` | 41 | 100% — S3 CSV; 2 cols excluded by policy (`Created By`, `Awardee Contact Person`) |
| `schema_4` / `schema_5` | 46 | 100% — V2 CSV |

---

## Mapping Run Results (1,000 rows each)

| Label | File | Detected | Rows | Quarantined | Releases | DQ errors | libcoveocds | Shape pre-flight |
|-------|------|----------|------|-------------|----------|-----------|-------------|------------------|
| S1-2002 | 2002.xlsx | schema_1 | 1000 | 0 | 281 | 0 | 0 | Pass |
| S1-2012H1 | Jan–Jun 2012.xlsx | schema_1 | 1000 | 0 | 232 | 0 | 0 | Pass |
| S2-2013Q1 | Jan–Mar 2013.xlsx | schema_1* | 1000 | 0 | 376 | 0 | 0 | Pass |
| S2-2020Q4 | Oct–Dec 2020.xlsx | schema_2 | 1000 | 0 | 299 | 0 | 0 | Pass |
| S3-2021 | 2021.csv (1.32M rows) | schema_3 | 1000 | 0 | 362 | 0 | 0 | Pass (retest) |
| S3-2024 | 2024.csv (1.59M rows) | schema_3 | 1000 | 0 | 422 | 0 | 0 | Pass (retest) |
| S3-2025 | 2025.csv (711K rows) | schema_3 | 1000 | 0 | 273 | 0 | 0 | Pass (retest) |
| S5-V2-Q4 | 2024-10 -- 2024-12.csv | schema_4 | 1000 | 0 | 483 | 0 | 0 | Pass |

\*File is in the 2013–2021 folder but detected as **schema_1** (still uses `UOM`).  
†Initial matrix run recorded S3 pre-flight failures on microsecond timestamps; **retest after `parse_date()` fix** (`scratch/out/S3-*-retest.dq.json`) shows `shape_error: null` and libcoveocds 0 errors.

### Typical data-quality patterns (non-blocking)

| Rule | Severity | S1 | S2 | S3 | S4/V2 |
|------|----------|----|----|----|----|
| `unawarded_tender` | info | ~70% | ~70% | ~64% | ~52% |
| `award_missing_expected` | warning | common | rare | rare | rare |
| `non_positive_amount` | warning | `item_budget`/`contract_amount` = 0 or -1 | same | same | same |
| `placeholder_bid_ref` | warning | — | — | ~1% (`bid_reference_no` = 0) | ~2% |

~50–70% of sampled rows are un-awarded tenders (no `award_reference_no`) — expected; they compile as info, not errors.

### Mapping coverage

- **S1/S2:** All 40 source columns map to canonical fields. Award identity uses `Award No.` → `award_reference_no`.
- **S3:** 41 mapped + 2 privacy-excluded. `List of Bidder's` → `list_of_bidders` (bids extension path in compiler).
- **S4/S5:** All 46 columns map. Location fields (`pe_region`, `awardee_region`, etc.) populate parties/addresses in compiler. No `bidders` column in S4 export.

---

## Issues Encountered

### 1. Production transform is CSV-only (schema detection fixed)

`transform_to_ocds.py` now detects S1–S4 via marker columns (same logic as the scratch sampler). It remains **CSV-only** — XLSX ingest (header row 4, datetime cell normalization) is still implemented only in `scratch/sample_and_transform.py` and should be merged next.

### 2. XLSX not supported in production transform

`transform_to_ocds.py` is CSV-only. XLSX requires header-row detection (row 4) and datetime cell normalization — implemented in scratch sampler only.

### 3. XLSX date type mismatch (fixed)

**Symptom:** 100% quarantine, rule `bad_date`, 0 releases on S1.  
**Cause:** `openpyxl` returns `datetime` objects; stringified as `2002-01-02 00:00:00`, which `parse_date()` did not accept.  
**Fix:** Normalize XLSX cells to ISO 8601; extend `parse_date()` for ISO input.

### 4. S3 microsecond timestamps (fixed)

**Symptom:** `_ocds_checks` pre-flight: `not RFC 3339: '2021-10-13T14:53:14.740000+08:00'`.  
**Cause:** S3 CSV `Published Date` values include fractional seconds; pre-flight parser does not.  
**Fix:** Strip microseconds in `parse_date()` output. libcoveocds accepted them either way.

### 5. `2025.csv` is S3, not S4

Documentation and quick-reference tables label 2025 as Schema 4 (46 cols). The file in `raw/PHILGEPS -- 2021-2025 (CSV)/` is still 43-column S3. True S4 structure only appears in the V2 export under `raw/Misc/`.

### 6. Header row documentation off-by-one

Docs say "row 3" for XLSX; actual header is row **4** (1-based). Data starts row 5.

### 7. Large CSV memory use (fixed in scratch)

Initial matrix run stalled loading full `2021.csv` (~953 MB). Reservoir streaming sampling fixes this for `--sample N` runs.

### 8. S3 `award_notice_status` values

S3 uses values like `Posted`, `Updated`, `Awarded` — mapped via `ocds_codelist_mappings.yaml`. Warnings fire when status is `posted` but awardee fields are `NULL` (line-item rows for in-progress notices).

---

## Data Pipeline (End-to-End)

How raw PhilGEPS files become valid OCDS release packages in this repo:

```
raw/  (XLSX S1/S2 or CSV S3/S4/S5)
  │
  ├─ 1. INGEST
  │     CSV: DictReader, utf-8-sig
  │     XLSX: openpyxl read_only, find header row (≥10 non-empty cells), skip metadata rows
  │
  ├─ 2. SCHEMA DETECT
  │     S4 markers: Procuring Entity (PE), Region, Bid Notice Status
  │     S3 markers: Procuring Entity, Created By, List of Bidder's
  │     S2 markers: Unit of Measurement + Organization Name
  │     S1 markers: UOM + Organization Name
  │     → select schema_1 … schema_4 from config/schema_mappings.yaml
  │
  ├─ 3. CANONICALIZE
  │     column_map: source header → canonical field (e.g. Award No. → award_reference_no)
  │     excluded_source_columns: Created By, Awardee Contact Person (privacy)
  │
  ├─ 4. DATA QUALITY (scripts/_data_quality.py)
  │     validate_row(): identity, dates, amounts, award completeness
  │     fatal errors → quarantine (skip grouping)
  │     validate_group(): field conflicts, duplicate line_item_no
  │
  ├─ 5. GROUP
  │     group by bid_reference_no (else solicitation_no, else award_reference_no)
  │     skip rows with no process identity
  │
  ├─ 6. COMPILE (scripts/_ocds_compiler.py + config/canonical_to_ocds.yaml)
  │     one release per process: tender.items[], awards[], contracts[], parties[]
  │     ocid / release.id from bid_reference_no (solicitation fallback; composite on collision)
  │     codelists: config/ocds_codelist_mappings.yaml
  │
  ├─ 7. PACKAGE
  │     uri, version 1.1, publisher, extensions (bids, lots), releases[]
  │
  ├─ 8. PRE-FLIGHT (scripts/_ocds_checks.py)
  │     required fields, date RFC 3339, version format
  │
  └─ 9. VALIDATE (libcoveocds / OCDS Data Review Tool)
        schema validation + additional checks
```

### Commands

```bash
# From philgeps_schema_analysis/
pip install -r requirements.txt -r requirements-dev.txt

# Single file (scratch sampler — supports XLSX + all schemas)
python scratch/sample_and_transform.py "../raw/2000-2012/Bid Notice and Award Details 2002.xlsx" --sample 1000
python scratch/sample_and_transform.py "../raw/PHILGEPS -- 2021-2025 (CSV)/2021.csv" --sample 1000

# Validate output
python scratch/validate_ocds.py scratch/out/S3-2021.json

# Production CSV path (S4-detected only today)
python scripts/transform_to_ocds.py raw/2024-10\ --\ 2024-12.csv --sample 1000
```

### Recommended next steps

1. **Merge** multi-schema detection + XLSX ingest from `scratch/sample_and_transform.py` into `scripts/transform_to_ocds.py`.
2. **Update** `philgeps-schema.md` and `raw/README.md`: correct 2025.csv schema label; fix header row wording; note 2013–2015 = S1.
3. **Normalize** `award_notice_status` codelist mapping for S3 `Posted`/`Updated` vs OCDS `active`/`complete`.
4. **Add** `source_schema` to compiled releases from detected schema key (field exists in `philgeps_extension` config).
5. **Obtain** more S5 V2 quarterly files if retroactive 2021–2024 location-enriched exports are needed.

---

## Conclusion

**Schema evolution documentation is largely accurate** for column names, counts, and S1→S2→S3 progression. Three material corrections:

1. **2025 main CSV is still S3** — S4 lives in the V2 export path under `raw/Misc/`.
2. **XLSX header is row 4** (1-based), not row 3.
3. **2013–2015 Excel files remain S1** until the 2016 UOM rename.

**OCDS mapping works across all verified schemas** after XLSX date and microsecond fixes: 0 quarantined rows, 0 libcoveocds validation errors on all 1,000-row samples (S3 re-verified 2025-06-27). Production `transform_to_ocds.py` has multi-schema detection but still needs XLSX ingest merged from scratch.

### Edge-case regression tests

`scripts/test_edge_cases.py` (12 tests) covers: ISO/microsecond dates, XLSX datetime cells, S1–S4 schema detection, S1 typo column names (`Contract Efectivity Date`), placeholder `bid_reference_no`, unawarded tenders, inverted contract periods, JV comma/semicolon split, and S3 bidders extension. Run with the other smoke tests:

```bash
python scripts/test_edge_cases.py
python scripts/test_data_quality.py
python scripts/test_ocds_compiler.py
python scripts/test_ocds_checks.py
python scripts/test_unified_report.py
```

### Unified report (`.report.json`)

Each transform run now writes a **single merged report** alongside `.json` and `.dq.json`:

| Layer | Source | What it counts |
|-------|--------|----------------|
| `layers.source_dq` | `_data_quality.RunReport` | Per-row rules (`unawarded_tender`, `bad_date`, …) |
| `layers.shape_preflight` | `_ocds_checks` | OCDS package shape (RFC 3339, wrapped releases, …) |
| `layers.ocds_validation` | `libcoveocds` | Schema validation, conformance, deprecated fields |

`summary.top_findings` merges rule counts from all three layers. `summary.all_passed` is true only when source errors, shape issues, and libcoveocds validation are all clean.

Artifacts: `<out>.report.json` (unified), `<out>.validation.json` (full libcoveocds payload), `<out>.dq.json` (unchanged — webapp still uses this).
