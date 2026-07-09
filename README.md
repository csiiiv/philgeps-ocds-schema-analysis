# PhilGEPS Schema Analysis

Reference repository for **PhilGEPS open-data schema evolution (2000–2025)** and **mapping to a canonical field model and [OCDS](https://standard.open-contracting.org/) 1.1.5**.

Use this repo to answer: *What column names appear in which export era? How do they normalize to one schema? How does that relate to OCDS and PhilGEPS 1.5/2.0 internal fields?*

**This repo does not include raw CSV/XLSX data** — only documentation, mapping config, JSON/markdown references, and a **reference ETL pipeline** that transforms local exports into OCDS. Raw exports live on [Google Drive](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing). After cloning [philgeps-ocds-schema-analysis](https://github.com/csiiiv/philgeps-ocds-schema-analysis), place them under `raw/` at the repository root.

---

## Quick start

```bash
git clone https://github.com/csiiiv/philgeps-ocds-schema-analysis.git
cd philgeps-ocds-schema-analysis
```

**No install required** to read the references. To regenerate derived files:

```bash
pip install -r requirements.txt
python scripts/build_schema_field_map.py
```

---

## Demo data workflow

For development, testing, and CI/CD, this repository includes **demo datasets** (~200 rows, <1MB) in the `raw_demo/` directory. This allows you to:

- Clone and run the analysis without downloading large datasets (350MB+)
- Build and deploy the webapp immediately after `git pull`
- Test data transformations without full datasets
- Use in CI/CD pipelines for continuous validation

### Using demo data

```bash
# Transform demo data to OCDS (works with any S4/S5 CSV)
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv

# Run webapp with demo-transformed data
python scripts/build_schema_field_map.py
cd app && npm install && npm run dev
```

The webapp and validation scripts work identically with demo data, just with fewer records.

### Generating new demo data

If you have access to full datasets and want to create new demo samples:

```bash
# Generate demo data from any large CSV export
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/demo.csv --rows 200

# Or with different sample size
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/demo.csv --rows 500
```

The `generate_demo_data.py` script ensures diversity by sampling across:
- Procurement modes (19 modes)
- Organization types (14 types)  
- Regions (17+ regions)
- Notice/award statuses
- Award vs. non-award records

### Full dataset workflow

For production analysis with complete datasets, download from Google Drive:

→ [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) for full dataset download

→ [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md)

---

## Run the webapp

The `app/` directory is a Vite + React + TypeScript single-page app that renders the schema mappings interactively (canonical field browser, OCDS crosswalk, OCDS staged output, codelists, schema evolution, global search).

**Demo Mode (Fast, Lightweight)**
```bash
# 1. (Re)generate the data bundle from YAML + JSON references
python scripts/build_schema_field_map.py

# 2. Generate webapp caches from demo data
python scripts/generate_webapp_caches.py

# 3. Install and run the dev server
cd app
npm install
npm run dev      # http://localhost:5173
```

The webapp now uses lightweight demo data (~60MB) from `references/transformed/demo_by_year/` for instant startup and responsive exploration. Full dataset available on Google Drive (see External Sources below).

**Full Dataset Mode (Complete Analysis)**
```bash
# Download full year packages from Google Drive
# Place in references/transformed/by_year/
# Webapp will automatically use full data when available
```

Production build: `npm run build` → static files in `app/dist/`.

→ [app/README.md](app/README.md) for full details

---

## OCDS validation

The build script emits a sample OCDS 1.1 release package and validates it through a multi-layer pipeline (see [docs/VALIDATION.md](docs/VALIDATION.md)). All guard tests run in CI.

```bash
pip install -r requirements-dev.txt          # libcoveocds (Python ≥3.9, <3.13)
python scripts/build_schema_field_map.py     # layer 1: hard-fail on bad shape
python scripts/test_ocds_checks.py           # layer 3
python scripts/test_ocds_compiler.py         # layer 4
python scripts/test_data_quality.py          # layer 5
python scripts/validate_sample_release.py    # layer 2: synthetic sample
```

→ [docs/VALIDATION.md](docs/VALIDATION.md) for the layered model and how to extend the rules

---

## Transform data

Turn PhilGEPS exports into OCDS 1.1 releases using the validated mapping. **Demo data included, full dataset optional.**

### Demo data workflow (recommended for development)

```bash
pip install -r requirements.txt

# Transform demo data (included in git - no download needed)
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv

# Build webapp with demo data
python scripts/build_schema_field_map.py
cd app && npm install && npm run dev
```

Demo data outputs land in `references/transformed/` (gitignored). The webapp loads transformed data for the **ETL Pipeline** and **Release Browser** sections.

### Full dataset workflow (for production analysis)

```bash
# Download full datasets from Google Drive first (see GETTING_STARTED.md)
# Then transform any number of files

# One CSV export
python scripts/transform_to_ocds.py raw/<your-export>.csv

# Full dataset (54 files → by_year/ + combined.report.json)
python scripts/run_full_dataset.py --no-quiet
python scripts/build_schema_field_map.py
cd app && npm run dev
```

Outputs land in `references/transformed/` (gitignored). The webapp **ETL Pipeline** section embeds `combined.report.json` for corpus stats; **Year data quality**, **Release browser** (`#/etl-releases/{year}`), and per-year caches load from `by_year/dq/` and `by_year/browser/` at dev time.

→ [docs/TRANSFORM.md](docs/TRANSFORM.md) — single-file pipeline, DQ rules  
→ [docs/ETL_PIPELINE.md](docs/ETL_PIPELINE.md) — full batch ETL, outputs, reports  
→ [docs/ARCHITECTURAL_DECISIONS.md](docs/ARCHITECTURAL_DECISIONS.md) — ADR log (why the pipeline is shaped this way)

---

## Schema periods (S1–S5)

| Key | Period | Format | Columns |
|-----|--------|--------|--------:|
| **S1** | 2000–2015 | XLSX (header row 3) | 40 |
| **S2** | 2016–2020 | XLSX (header row 3) | 40 |
| **S3** | 2021–2024 | CSV | 43 |
| **S4** | 2025+ | CSV | 46 |
| **S5** | 2021–2024-V2 | CSV (same as S4) | 46 |

Map by **column name**, not column position. Details: [references/philgeps-schema.md](references/philgeps-schema.md) · [live UI](https://philgeps.simple-systems.dev/about/schema)

---

## Key artifacts

| Artifact | Audience | Purpose |
|----------|----------|---------|
| [**PHILGEPS_CANONICAL_FIELD_MAP.json**](references/PHILGEPS_CANONICAL_FIELD_MAP.json) | Developers | 53 canonical fields, S1–S5 source columns, OCDS paths, embedded crosswalk |
| [**PHILGEPS_OCDS_CSV_CROSSWALK.md**](references/PHILGEPS_OCDS_CSV_CROSSWALK.md) | Analysts / OCDS implementers | 151-row OCDS ↔ PhilGEPS 1.5/2.0 ↔ CSV ↔ canonical join |
| [**app/**](app/) | Everyone | Interactive webapp rendering all of the above — [run locally](#run-the-webapp) |
| [**SAMPLE_OCDS_RELEASE_PACKAGE.json**](references/SAMPLE_OCDS_RELEASE_PACKAGE.json) | OCDS implementers | Sample OCDS 1.1 release package built from the staging rules; validated in CI with `libcoveocds` |
| [**config/schema_mappings.yaml**](config/schema_mappings.yaml) | Pipeline authors | **Source of truth** for export column → canonical field |
| [**references/transformed/combined.report.json**](references/transformed/combined.report.json) | Integrators / webapp | Full-dataset DQ roll-up + per-year stats (local; see [ETL_PIPELINE.md](docs/ETL_PIPELINE.md)) |
| [**config/canonical_to_ocds.yaml**](config/canonical_to_ocds.yaml) | OCDS publishers | Canonical field → OCDS 1.1 path |
| [config/ocds_codelist_mappings.yaml](config/ocds_codelist_mappings.yaml) | OCDS publishers | PhilGEPS status/mode values → OCDS codelists |
| [PHILGEPS_SCHEMA_ANALYSIS.json](references/PHILGEPS_SCHEMA_ANALYSIS.json) | Tools | Structured schema evolution tables |

Full index: [references/README.md](references/README.md) · File chooser: [references/SCHEMA_FILES_COMPARISON.md](references/SCHEMA_FILES_COMPARISON.md)

---

## Example (Python)

```python
import json
data = json.load(open("references/PHILGEPS_CANONICAL_FIELD_MAP.json"))
idx = data["source_column_index"]["schema_1"]
idx["Organization Name"]  # → procuring_entity
```

---

## Repository structure

```
├── .github/workflows/  # CI: regenerate artifacts, validate sample, build webapp
├── app/                 # Interactive webapp (Vite + React + TS) — see app/README.md
├── config/              # Mapping source of truth (YAML)
├── references/          # Schema docs, OCDS templates, generated JSON, sample release, transformed/
├── scripts/             # build_schema_field_map.py, transform_to_ocds.py, generate_demo_data.py, …
├── docs/                # Overview, ETL pipeline, transform, validation, getting started
├── raw/                 # Large raw exports (gitignored — download from Google Drive)
└── raw_demo/            # Demo datasets for development (included in git)
```

→ [docs/OVERVIEW.md](docs/OVERVIEW.md) for architecture and scope

---

## External sources

| Resource | Link |
|----------|------|
| Raw exports | [Google Drive RAW_CSV](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing) |
| OCDS by year | [Google Drive OCDS](https://drive.google.com/drive/folders/1Bg4r6x6v64OjAFs0AJ1SQGC4exgddrl4?usp=sharing) — merged `by_year/` packages (`philgeps_ocds_by_year.7z`) |
| Schema explorer UI | [philgeps.simple-systems.dev/about/schema](https://philgeps.simple-systems.dev/about/schema) |
| PS-DBM OCDS templates | [ocds.simple-systems.dev/p/mphilgeps/overview](https://ocds.simple-systems.dev/p/mphilgeps/overview) |

---

## Contributing

Edit `config/*.yaml` or schema analysis JSON, then run the build script. See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

---

## Related work

Downstream pipelines (ingest, Parquet, OCDS compile, Cardinal) may live in separate repos and **submodule or copy** this mapping config. This repository is intentionally standalone — no dependency on a parent monorepo.

| Item | Value |
|------|-------|
| Schema analysis date | 2025-11-14 |
| OCDS template | PS-DBM v0.91 (OCDS 1.1.5) |
| Canonical fields (S1–S5) | 53 |
| Crosswalk rows | 151 |
