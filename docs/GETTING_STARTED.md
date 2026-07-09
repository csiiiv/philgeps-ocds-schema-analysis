# Getting started

## Prerequisites

- Python 3.10+ (3.11 recommended — `libcoveocds`, used for sample-release validation, does not build on 3.13+)
- Optional: `pip install -r requirements.txt` (only needed to **regenerate** JSON/markdown artifacts)
- Optional: `pip install -r requirements-dev.txt` (adds `libcoveocds` to validate the sample OCDS release)

## Clone and explore (no build required)

Most consumers only need the committed reference files:

```bash
git clone https://github.com/csiiiv/philgeps-ocds-schema-analysis.git
cd philgeps-ocds-schema-analysis
```

| Goal | Start here |
|------|------------|
| **Browse everything interactively** | [Run the webapp](#run-the-webapp) — canonical browser, OCDS crosswalk, staged output, data transformation (if embedded), search |
| Understand schema history | [references/philgeps-schema.md](../references/philgeps-schema.md) or [live schema page](https://philgeps.simple-systems.dev/about/schema) |
| Programmatic S1–S5 column names | [references/PHILGEPS_CANONICAL_FIELD_MAP.json](../references/PHILGEPS_CANONICAL_FIELD_MAP.json) |
| OCDS ↔ CSV gap analysis | [references/PHILGEPS_OCDS_CSV_CROSSWALK.md](../references/PHILGEPS_OCDS_CSV_CROSSWALK.md) |
| Pick the right reference file | [references/SCHEMA_FILES_COMPARISON.md](../references/SCHEMA_FILES_COMPARISON.md) |

## Run the webapp

The `app/` directory ships a Vite + React + TypeScript single-page app that renders every mapping interactively — the digestible replacement for reading the raw YAML and the 151-row markdown crosswalk by hand.

```bash
python scripts/build_schema_field_map.py   # emits app/src/data/schema_bundle.json
cd app
npm install
npm run dev                                 # http://localhost:5173
```

No backend, no runtime fetch — the bundle is compiled into the static site. See [../app/README.md](../app/README.md) for the full section list and scripts.

## Quick Python example

```python
import json
from pathlib import Path

root = Path("references/PHILGEPS_CANONICAL_FIELD_MAP.json")
data = json.loads(root.read_text(encoding="utf-8"))

by_field = {f["canonical_field"]: f for f in data["canonical_fields"]}

# Normalize a Schema 1 column name to canonical
s1_map = data["source_column_index"]["schema_1"]
canonical = s1_map["Organization Name"]  # → procuring_entity

# All export names for that field across schemas
by_field["procuring_entity"]["source_columns"]
# schema_1: Organization Name, schema_3: Procuring Entity, schema_4: Procuring Entity (PE), ...

# OCDS paths for the same field
by_field["procuring_entity"]["ocds_paths"]
```

## Detect schema period from a CSV header row

Use marker columns (by name, not position):

| Detected schema | Marker columns present |
|-----------------|------------------------|
| S1 | `UOM`, `Organization Name` |
| S2 | `Unit of Measurement`, `Organization Name` |
| S3 | `Procuring Entity`, `List of Bidder's` or `Created By` |
| S4 | `Procuring Entity (PE)`, `Region`, `Bid Notice Status` |
| S5 | `Procuring Entity (PE)` without `Region` (early V2 export quirk) |

Then load `source_column_index["schema_N"]` from the JSON dictionary (or `config/schema_mappings.yaml`).

## Regenerate derived artifacts

After editing `config/schema_mappings.yaml`, `config/canonical_to_ocds.yaml`, or `references/PHILGEPS_SCHEMA_ANALYSIS.json`:

```bash
pip install -r requirements.txt
python scripts/build_schema_field_map.py
```

This updates:

- `references/PHILGEPS_CANONICAL_FIELD_MAP.json`
- **Canonical** column in `references/PHILGEPS_OCDS_CSV_CROSSWALK.md`
- `app/src/data/schema_bundle.json` (data bundle consumed by the webapp)
- `references/SAMPLE_OCDS_RELEASE_PACKAGE.json` (sample OCDS release package)

Optionally validate the sample release against OCDS 1.1 (uses [libcoveocds](https://github.com/open-contracting/lib-cove-ocds), the engine behind the OCDS Data Review Tool):

```bash
pip install -r requirements-dev.txt
python scripts/validate_sample_release.py
```

After regenerating, restart `npm run dev` (or rebuild) inside `app/` so the webapp picks up the new bundle.

Curated crosswalk columns (OCDS, PhilGEPS 1.5/2.0, V1/V2 CSV) are preserved; see [CONTRIBUTING.md](CONTRIBUTING.md) for override hooks in the build script.

## Obtain raw data

This repo does not include exports. Download from:

[RAW_CSV — Google Drive](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing)

Suggested layout for local testing (monorepo: place at repo root as `raw/`):

```
raw/
  2000-2012/                    # XLSX (S1)
  PHILGEPS 2013-2021/           # quarterly XLSX
  PHILGEPS -- 2021-2025 (CSV)/  # yearly CSV (S3)
  Misc/PHILGEPS -- 2021 - 2025 (CSV) V2/   # quarterly CSV (S4/S5)
```

## OCDS outputs by year

Pre-built merged OCDS release packages (one JSON per calendar year, same layout as `references/transformed/by_year/`) are available without running the full ETL:

[OCDS by year — Google Drive](https://drive.google.com/drive/folders/1Bg4r6x6v64OjAFs0AJ1SQGC4exgddrl4?usp=sharing) (`philgeps_ocds_by_year.7z`)

Extract under `references/transformed/by_year/` to browse with the Release browser or validate with `validate_transform_sample.py`.

## Transform exports

### Single file (development)

Reference pipeline for turning one PhilGEPS export into OCDS releases:

```bash
pip install -r requirements.txt
python scripts/transform_to_ocds.py raw/<export>.csv --sample 1000
pip install -r requirements-dev.txt
python scripts/validate_transform_sample.py references/transformed/<basename>.json
python scripts/build_schema_field_map.py
```

→ [TRANSFORM.md](TRANSFORM.md) for DQ rules and grouping semantics  
→ [OCDS_PROCESS_AND_RELEASE_IDENTITY.md](OCDS_PROCESS_AND_RELEASE_IDENTITY.md) for OCDS process vs release concepts  
→ [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md) for PhilGEPS `ocid` / `release.id` policy

### Full dataset (batch ETL)

Transform all PhilGEPS exports, merge by calendar year, refresh the webapp bundle:

```bash
python scripts/run_full_dataset.py --no-quiet
python scripts/build_schema_field_map.py
cd app && npm run dev
```

Use `--resume` only when re-running the **same** compiler rules without policy changes. See [ETL_PIPELINE.md](ETL_PIPELINE.md) for output paths, post-ETL steps, and disk/RAM requirements.

## Next steps

- [ETL_PIPELINE.md](ETL_PIPELINE.md) — full batch ETL pipeline
- [TRANSFORM.md](TRANSFORM.md) — single-file transform, DQ rules, **Release browser**
- [OVERVIEW.md](OVERVIEW.md) — architecture and scope
- [VALIDATION.md](VALIDATION.md) — OCDS validation layers (sample + transform output)
- [TRANSFORM.md](TRANSFORM.md) — transform a real PhilGEPS CSV export into OCDS releases
- [CONTRIBUTING.md](CONTRIBUTING.md) — extend mappings, add schemas, publish changes
- [../app/README.md](../app/README.md) — webapp sections, scripts, architecture
- [../README.md](../README.md) — full file index
