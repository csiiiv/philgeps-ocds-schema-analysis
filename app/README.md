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
| **OCDS staged output** | Live rendering of `config/canonical_to_ocds.yaml` — one card per OCDS block (planning, buyer, tender, awards, contracts, bids, philgeps_extension) showing path → canonical field, plus generated fields, planning triggers, and defaults. |
| **OCDS release package** | A representative compiled OCDS release built by walking the staging rules. Overview cards, per-block jump links, syntax-highlighted raw JSON with copy and download. |
| **Codelist mappings** | PhilGEPS status / method / category labels → OCDS closed codelists. |
| **Global search** | Cross-section search for any column name, OCDS path, or canonical field. |
| **About & sources** | Bundle metadata, source file inventory, regen instructions, external links. |

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
app/src/data/schema_bundle.json   ← single bundled JSON
        │
        │  import (Vite bundles it; no runtime fetch)
        ▼
React SPA (hash-based routing, no router dependency)
```

- **No backend, no runtime fetch.** The bundle is compiled into the static site.
- **No UI library.** Styling is plain CSS with CSS variables (light + dark via `prefers-color-scheme`).
- **No router dependency.** Hash-based routing keeps the app deployable as a single static folder.

## Tech stack

- Vite 6, React 19, TypeScript 5 (strict).
- Dev dependencies only beyond React — the production bundle is ~84 KB gzipped.

## Refreshing data after mapping edits

Edit any file under `config/` or `references/` in the parent repo, then:

```bash
npm run regen-data   # from app/
```

Restart `npm run dev` (or rebuild) to pick up the new bundle.
