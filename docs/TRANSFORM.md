# Data transformation

How to turn PhilGEPS exports into OCDS 1.1 releases using the validated mapping in this repo. This is the bridge between the mapping config (paper) and real published data.

For the **full batch pipeline** (all 54 exports → `by_year/` → `combined.report.json`), see **[ETL_PIPELINE.md](ETL_PIPELINE.md)**. For **design history and rationale** (grouping, `ocid`, reports), see **[ARCHITECTURAL_DECISIONS.md](ARCHITECTURAL_DECISIONS.md)**. For **`ocid` / `release.id` rules**, see **[OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md)**.

## Scope

The transformer compiles one OCDS release per contracting process (grouped by `bid_reference_no` when present, else `solicitation_no` or `award_reference_no`), collapsing line-item rows into `tender.items[]` and one or more `awards[]` / `contracts[]` entries under the same `ocid`.

Each run writes three artifacts: `<out>.json` (OCDS package), `<out>.dq.json` (DQ detail), and `<out>.report.json` (unified report merging source DQ + shape pre-flight + optional libcoveocds).

Out of scope: this is a reference transformer, not a production publisher. Cross-file dedup happens only in the calendar-year merge step — see [ETL_PIPELINE.md](ETL_PIPELINE.md).

## Quick start

```bash
pip install -r requirements.txt
python scripts/transform_to_ocds.py raw/<your-export>.csv
```

Outputs land in `references/transformed/<basename>.json`, `.dq.json`, and `.report.json`.

## Full dataset (batch)

```bash
python scripts/run_full_dataset.py --no-quiet
python scripts/build_schema_field_map.py
```

Produces `references/transformed/full/`, `by_year/` (with `browser/` and `dq/` caches), and `combined.report.json`. See [ETL_PIPELINE.md](ETL_PIPELINE.md). Do not `--resume` after compiler or identity policy changes without clearing stale `full/` outputs.

To validate the output against the OCDS 1.1 schema:

```bash
pip install -r requirements-dev.txt    # adds libcoveocds
python scripts/validate_sample_release.py   # synthetic sample
python scripts/validate_transform_sample.py references/transformed/sample1k.json
```

## The pipeline

Six stages, each a script you can inspect and extend:

| Stage | Script | What it does |
|-------|--------|--------------|
| 1. Detect schema | `transform_to_ocds.py` | Matches header columns against S1–S5 marker sets |
| 2. Map to canonical | `transform_to_ocds.py` + `config/schema_mappings.yaml` | Applies the column→canonical mapping for the detected schema |
| 3. Data-quality gate | `scripts/_data_quality.py` | `validate_row()` per CSV row; errors quarantine (excluded from grouping) |
| 4. Group by process | `transform_to_ocds.py` + `_data_quality.validate_process_group()` | Collapse line items; flag cross-row conflicts and duplicate `line_item_no` |
| 5. Compile to OCDS | `scripts/_ocds_compiler.py` + `config/canonical_to_ocds.yaml` | Walks the staging rules; sets `ocid` / `release.id` (bid-first) |
| 5b. Resolve id collisions | `resolve_release_display_collisions()` in `_ocds_compiler.py` | Composite `id` + `display_id_collision` DQ when `(ocid, id)` duplicates remain |
| 6. Validate & write | `_unified_report.py` + `_ocds_checks.py` | Unified `.report.json`; hard-fail on malformed shape before writing |

## Data-quality rules

Each row is inspected by `scripts/_data_quality.validate_row()` before the compiler sees it. Issues are tagged by severity and rule:

| Severity | Meaning | Effect on the row |
|----------|---------|-------------------|
| `error` | Row would be OCDS-invalid or unidentifiable | Quarantined — excluded from grouping and compilation |
| `warning` | Suspicious but compilable | Compiled; logged for review |
| `info` | Noteworthy (e.g. un-awarded tender, duplicate line items) | Logged; un-awarded rows are skipped (no release); others compile |

Row-level rules run in `validate_row()`. After rows are grouped by contracting process, `validate_process_group()` checks process-level fields and delegates to `validate_group()` per `award_reference_no` subgroup:

- `group_field_conflict` — process- or award-level fields differ within a group (warning; **first row wins** at compile time)
- `duplicate_line_item_no` — same `line_item_no` but different item content within one award (info; item ids disambiguated at compile time)

Other row-level rules (see `_data_quality.py` for the full list):

- `missing_identity` / `placeholder_identity` — required identifiers (`award_reference_no`) missing or `0`
- `placeholder_bid_ref` — `bid_reference_no` is `0` (S4 decommissions this column)
- `display_id_collision` — composite `release.id` / `ocid` applied because two releases shared the same `(ocid, id)` (warning)
- `unawarded_tender` — row has no award because the tender closed/cancelled (info, not an error)
- `bad_numeric` / `bad_date` — value can't be parsed as the declared type
- `non_positive_amount` — numeric amount is zero or negative
- `award_missing_expected` — row is "Awarded" but missing awardee name, amount, or date
- `inverted_contract_period` — contract end date precedes start date

Rows with `NULL` or placeholder `award_reference_no` are never grouped. Fatal rows (DQ `error`) are quarantined before grouping.

## `.dq.json` and `.report.json`

Each run writes `<out>.dq.json` alongside the OCDS package. The unified `<out>.report.json` adds shape pre-flight and optional libcoveocds results under `layers.*`.

Key fields:

| Field | Purpose |
|-------|---------|
| `severity_counts` / `rule_counts` | Roll-up totals for the whole run |
| `quarantined_samples` | Up to **50** error rows (full detail in file) |
| `warning_samples` / `info_samples` | Up to **100** each, with `*_samples_omitted` when the cap is hit |
| `input_samples` | Up to **25** before/after pairs (raw CSV row + compiled release) |

Sample payloads are **compact** so the report stays usable: row lists cap at **20** indices (`row_indices_omitted` holds the rest), and long messages are truncated in embedded copies. The webapp bundle applies the same compaction via `build_schema_field_map.py`.

The full run report is surfaced in the webapp **ETL Pipeline** section:

- **Pipeline overview** — corpus stats and by-year table from `combined.report.json`
- **Year data quality** — per-year DQ caches (`by_year/dq/<year>.json`)
- **Corpus data quality** — dataset-wide roll-up
- **Release browser** — `#/etl-releases/{year}` with optional `/{ocid}` deep link

When only a single-file transform exists, the bundle embeds that file's `.dq.json` instead.

## Release browser (webapp)

The **Release browser** in the ETL Pipeline section loads per-year caches and supports deep links (`#/etl-releases/{year}/{ocid}`).

| UI area | What it shows |
|---------|----------------|
| **Sidebar list** | Tender title, buyer, award amount, `ocid`, and date for each embedded sample |
| **Search** | Filter by title, buyer, supplier, `ocid`, or procurement method |
| **Summary tab** | Award/tender values, procurement method and status, timeline (tender → award → contract), parties with roles, line items table, PhilGEPS extension fields, OCDS blocks present |
| **Raw JSON tab** | Full highlighted release JSON with copy and download (same viewer as before) |

Up to **50** releases are embedded in `schema_bundle.json` (`releases_sample`). The sidebar header shows how many samples are loaded versus `compiled_release_count` in the run report.

Parsing logic lives in `app/src/lib/releaseSummary.ts`; the UI component is `app/src/components/ReleaseBrowser.tsx`.

Refresh after a transform run:

```bash
python scripts/build_schema_field_map.py
cd app && npm run dev
```

## Row grouping semantics

PhilGEPS flat exports are **denormalized**: one contracting process (usually one `bid_reference_no`) repeats on many CSV rows, each row carrying line-item fields and often a distinct `award_reference_no`. The transformer groups rows before compilation:

| Field class | Examples | Compile rule |
|-------------|----------|--------------|
| Line-item | `item_name`, `quantity`, `item_budget`, `line_item_no`, `unspsc_code` | Merged into `tender.items[]`; each award subgroup gets its own `awards[].items[]` |
| Process-level | `procuring_entity`, `approved_budget`, `notice_title`, procurement dates | Taken from the **first row with a valid bid ref** (or first awarded row); must match across the process |
| Award-level | `contract_amount`, `award_date`, `awardee_organization_name` | Taken from the first row of each `award_reference_no` subgroup |
| In-cell arrays | `bidders`, `awardee_joint_venture` | Parsed within a row (`;` or `,` separated); JV partners expand to `awards[].suppliers[]` and `parties[]` |
| Generated | `ocid`, release `id` | `bid_reference_no` → `solicitation_no` → `award_reference_no`; composite on collision ([OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md)) |

When every row in a group has `line_item_no = 1` but different items, OCDS item ids are disambiguated as `1`, `1-2`, `1-3`, … so libcoveocds does not see duplicate `items/id` values.

`validate_process_group()` runs after row grouping to flag process-level `group_field_conflict` (warning) and award-level `duplicate_line_item_no` (info).

## Iterating on rules

Real data surfaces edge cases the rules don't yet cover. The intended workflow:

1. Run the transform on a new export.
2. Review `<out>.dq.json` — `rule_counts`, sample trees, and quarantined rows.
3. Add or refine rules in `_data_quality.py` (`validate_row` and/or `validate_group`).
4. Re-run the transform and validate:

```bash
python scripts/transform_to_ocds.py raw/<export>.csv --sample 1000   # quick check
python scripts/validate_transform_sample.py references/transformed/<basename>.json
python scripts/test_data_quality.py    # group rules + sampling guards
python scripts/test_ocds_compiler.py   # item-id disambiguation + JV expansion
```

5. Refresh the webapp bundle:

```bash
python scripts/build_schema_field_map.py   # prefers combined.report.json
cd app && npm run dev
```

Every rule added improves the next run automatically — the compiler, transformer, and webapp all read from the same modules.

## Compiler design

`scripts/_ocds_compiler.py` is row-driven: pass it any canonical row that passed the DQ gate and it returns an OCDS release. It reuses the staging rules in `canonical_to_ocds.yaml` (single source of truth — the same config the sample builder uses).

Key behaviors:

- **NULL handling**: `NULL` literals in the CSV become missing keys in the release (not garbage values).
- **Date parsing**: `dd/MM/yyyy` strings are converted to ISO 8601 with `+08:00` (Asia/Manila).
- **Codelist transforms**: PhilGEPS labels are mapped to OCDS codes via `ocds_codelist_mappings.yaml`.
- **Currency injection**: every numeric `amount` gets a sibling `currency: PHP` field.
- **Party dedup**: buyer and supplier with the same ID within a release are merged (avoids the OCDS "Non-unique id values" error).
- **JV expansion**: `awardee_joint_venture` partners are parsed and emitted as additional `awards[].suppliers` and `parties` entries (extension field retained for traceability).

## Known limitations / future iterations

These are deliberately tracked as follow-ups rather than blocking issues:

- **Closed tenders**: rows with no award are excluded from OCDS output. A future iteration could emit tender-only releases for these.
- **Bidders data**: S4 exports don't include bidder lists. The bids extension block is only populated when source data has it.
- **Cross-file dedup**: single-file transform does not dedup across exports. Calendar-year merge dedups by `ocid` within each year — see [ETL_PIPELINE.md](ETL_PIPELINE.md).
- **Party IDs without UACS**: when `pe_uacs_code` is missing, party IDs fall back to slugified names — not stable across files.

See the [open issues](https://github.com/csiiiv/philgeps-ocds-schema-analysis/issues) for the running list.

## See also

- [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md) — `ocid` / `release.id` policy and collision handling
- [ETL_PIPELINE.md](ETL_PIPELINE.md) — full batch ETL, output layout, `combined.report.json`
- [VALIDATION.md](VALIDATION.md) — how the OCDS shape of the output is validated
- [CONTRIBUTING.md](CONTRIBUTING.md) — how to add mapping rules and regenerate artifacts
- The **ETL Pipeline** section of the webapp renders aggregate or per-year run reports
