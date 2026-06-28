# PhilGEPS Schema Explorer

Interactive webapp that renders the PhilGEPS open-data schema mappings (2000–2025) and their alignment to OCDS 1.1.5. It is the digestible, searchable replacement for the giant markdown crosswalk table and YAML configs in the parent repo.

## What it shows

| Section | Purpose |
|---|---|
| **Overview** | Summary cards + the 4-layer data-flow diagram (raw → schema analysis → canonical → OCDS). |
| **Canonical fields** | All 53 normalized fields with type, S1–S5 source columns, OCDS paths, evolution notes. Expandable rows. |
| **Schema periods (S1–S5)** | Per-schema column inventory with the canonical field each maps to. |
| **Schema evolution** | Field-level change classification (stable / added / renamed / removed) across 25 years. |
| **Source column lookup** | Ingest tool: paste a CSV header, find its canonical field and OCDS path. |
| **OCDS crosswalk** | All 151 crosswalk rows, filterable by OCDS block and status (mapped / omit / derived / extension). |
| **OCDS staged output** | Live rendering of `config/canonical_to_ocds.yaml` — one card per OCDS block. |
| **OCDS release package** | Representative compiled OCDS release from staging rules. |
| **Codelist mappings** | PhilGEPS status / method / category labels → OCDS closed codelists. |
| **ETL Pipeline** | See below — overview, year/overall DQ, Release browser, transform samples. |
| **Global search** | Cross-section search for any column name, OCDS path, or canonical field. |
| **About & sources** | Bundle metadata, source file inventory, regen instructions, external links. |

### ETL Pipeline (when transform output is embedded)

| Page | Purpose |
|------|---------|
| **Pipeline overview** | Stage diagram, overall run summary, by-year table, OCID/id policy |
| **Year data quality** | Per-calendar-year DQ from `by_year/dq/{year}.json` (samples with source row context) |
| **Overall data quality** | Dataset-wide roll-up from `combined.report.json` |
| **Release browser** | `#/etl-releases/{year}` and `#/etl-releases/{year}/{ocid}` — searchable list, Summary + Raw JSON |
| **Transform samples** | Capped input/output samples from the transform run |

## Quick start

From the repository root:

```bash
# 1. Generate the data bundle (writes app/src/data/schema_bundle.json)
pip install -r requirements.txt
python scripts/build_schema_field_map.py

# 2. Run the app
cd app
npm install
npm run dev          # opens http://localhost:5173
```

With a full ETL run, the dev server also serves per-year caches:

- `/data/releases/{year}.json` — Release browser list + sample full releases
- `/data/dq/{year}.json` — Year data quality
- `/data/release/{year}/{ocid}.json` — on-demand full release JSON

`vite.config.ts` allows `ocdsphilgeps.simple-systems.dev` (CORS + `allowedHosts`) when the deployed static site fetches data from a tunneled dev server.

## Scripts

| Command | Description |
|---|---|
| `npm run dev` | Start the Vite dev server with HMR. |
| `npm run build` | Type-check (`tsc --noEmit`) and produce a static build in `dist/`. |
| `npm run preview` | Serve the production build locally. |
| `npm run regen-data` | Re-run `python ../scripts/build_schema_field_map.py` to refresh the bundle. |
| `npm run lint` | Type-check only. |

## Architecture

```
config/*.yaml + references/*.json
        │
        │  scripts/build_schema_field_map.py  (build_app_bundle)
        ▼
app/src/data/schema_bundle.json   ← overall stats + metadata (embedded)
        │
        │  import (Vite bundles it)
        ▼
React SPA (hash routing: #/etl-releases/2004/…)
        │
        │  fetch at dev time (full ETL)
        ▼
references/transformed/by_year/browser/ + by_year/dq/
```

- **Overall stats** are embedded in `schema_bundle.json` (no runtime fetch).
- **Per-year release and DQ data** are fetched from `/data/*` when running `npm run dev` after a full ETL merge.
- **No UI library.** Plain CSS with CSS variables (light + dark via `prefers-color-scheme`).
- **Hash routing** — no router dependency; supports deep links like `#/etl-releases/2004/ocds-philgeps-39785`.

## Refreshing data after mapping or ETL changes

```bash
# After full ETL (from repo root)
python scripts/run_full_dataset.py --no-quiet
python scripts/build_schema_field_map.py

# Or from app/
npm run regen-data
```

Restart `npm run dev` to pick up bundle and cache changes.

→ [../docs/ETL_PIPELINE.md](../docs/ETL_PIPELINE.md) for batch pipeline details  
→ [../docs/ARCHITECTURAL_DECISIONS.md](../docs/ARCHITECTURAL_DECISIONS.md) for ADR log (browser caches, DQ split, deep links)

## Tech stack

- Vite 6, React 19, TypeScript 5 (strict).
- Mapping-only bundle is small; with full-dataset embed, the JS bundle is larger depending on sample counts.
