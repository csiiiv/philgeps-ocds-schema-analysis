# References index

All committed reference artifacts for PhilGEPS schema and OCDS mapping. See [SCHEMA_FILES_COMPARISON.md](SCHEMA_FILES_COMPARISON.md) for a detailed guide.

> Prefer to browse interactively? The [`app/`](../app/) webapp renders every file below as searchable UI — canonical fields, the 151-row OCDS crosswalk, the staged OCDS output, codelists, and schema evolution. See [../docs/GETTING_STARTED.md#run-the-webapp](../docs/GETTING_STARTED.md) to run it.

## Start here

| File | Use when |
|------|----------|
| [PHILGEPS_CANONICAL_FIELD_MAP.json](PHILGEPS_CANONICAL_FIELD_MAP.json) | Writing ingest code — S1–S5 column → canonical field |
| [PHILGEPS_OCDS_CSV_CROSSWALK.md](PHILGEPS_OCDS_CSV_CROSSWALK.md) | Tracing OCDS paths to CSV / live-system fields |
| [PHILGEPS_SCHEMA_ANALYSIS.json](PHILGEPS_SCHEMA_ANALYSIS.json) | Column layout facts across schema periods |

## Schema evolution

| File | Format |
|------|--------|
| [philgeps-schema.md](philgeps-schema.md) | Narrative deep dive (613 lines) |
| [PHILGEPS_SCHEMA_ANALYSIS.md](PHILGEPS_SCHEMA_ANALYSIS.md) | Tables-only summary |
| [PHILGEPS_SCHEMA_ANALYSIS.json](PHILGEPS_SCHEMA_ANALYSIS.json) | Machine-readable schema analysis |

## OCDS / PS-DBM templates

| File | Contents |
|------|----------|
| [philgeps-1.5.json](philgeps-1.5.json) | PhilGEPS 1.5 → OCDS 1.1.5 |
| [mphilgeps.json](mphilgeps.json) | mPhilGEPS 2.0 → OCDS 1.1.5 |
| [ocds_reference.json](ocds_reference.json) | OCDS 1.1.5 field tree |

Regenerate canonical map + crosswalk Canonical column + webapp data bundle:

```bash
python scripts/build_schema_field_map.py
```

## Transformed OCDS outputs (local, gitignored)

Produced by the reference ETL pipeline — not committed, but documented here for navigation:

| Path | Contents |
|------|----------|
| [transformed/combined.report.json](transformed/combined.report.json) | **Dataset-wide roll-up** — aggregate DQ, per-year stats, source index (~100 KB) |
| [transformed/by_year/browser/](transformed/by_year/browser/) | Per-year Release browser caches (list + sample full releases) |
| [transformed/by_year/dq/](transformed/by_year/dq/) | Per-year DQ roll-ups for the webapp |
| [transformed/full/](transformed/full/) | One OCDS package per raw export (mirrors `raw/` layout) |

Generate:

```bash
python scripts/run_full_dataset.py --no-quiet   # merge + browser + dq caches at end
python scripts/build_schema_field_map.py
```

Refresh combined report only: `python scripts/aggregate_dataset_report.py`

The webapp **ETL Pipeline** embeds `combined.report.json` for corpus stats; Release browser and Year data quality fetch `by_year/browser/` and `by_year/dq/` at dev time (`#/etl-releases/{year}`).

→ [../docs/ETL_PIPELINE.md](../docs/ETL_PIPELINE.md) for the full pipeline reference  
→ [../docs/TRANSFORM.md](../docs/TRANSFORM.md) for DQ rules and Release browser details
