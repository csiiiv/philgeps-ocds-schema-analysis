# Overview

PhilGEPS Schema Analysis is a **standalone reference repository** for understanding Philippine government procurement open-data exports (2000–2025) and mapping them to a stable canonical schema and [Open Contracting Data Standard (OCDS)](https://standard.open-contracting.org/) 1.1.5.

It does **not** ship raw CSV/XLSX files or a full ETL pipeline. It ships **documentation, JSON references, and mapping config** that downstream tools can consume.

## Problem this repo solves

PhilGEPS public exports changed repeatedly over 25 years:

- **Format:** XLSX (headers on row 3) → CSV (headers on row 0)
- **Columns:** 40 → 43 → 46, with renames, additions, and removals
- **Semantics:** Same concept, different column name (`Organization Name` → `Procuring Entity (PE)`)
- **Systems:** Flat open CSV ≠ PhilGEPS 1.5 DB ≠ PhilGEPS 2.0 (mPhilGEPS) internal tables
- **Standards:** PS-DBM published OCDS mapping templates that do not line up 1:1 with flat CSV columns

Without a crosswalk, ingest code breaks silently when column **position** is assumed stable, or when only the latest CSV layout is handled.

## What this repo provides

| Layer | Artifact | Question it answers |
|-------|----------|-------------------|
| Schema evolution | `PHILGEPS_SCHEMA_ANALYSIS.json`, `philgeps-schema.md` | What columns exist in S1–S5? How did names change? |
| Canonical schema | `config/schema_mappings.yaml`, `PHILGEPS_CANONICAL_FIELD_MAP.json` | How do I normalize any year’s export to one field set? |
| OCDS alignment | `config/canonical_to_ocds.yaml`, `PHILGEPS_OCDS_CSV_CROSSWALK.md` | How do canonical fields map to OCDS paths? |
| Live-system templates | `philgeps-1.5.json`, `mphilgeps.json` | What did PS-DBM map from internal PhilGEPS tables? |
| **Interactive view** | **`app/` (Vite + React webapp)** | **Browse all of the above without reading YAML/JSON by hand** |

## Data layers (conceptual)

```
┌─────────────────────────────────────────────────────────────────┐
│  Raw open exports (not in repo)                                  │
│  Google Drive RAW_CSV · XLSX 2000–2020 · CSV 2021–2025 · V2     │
└────────────────────────────┬────────────────────────────────────┘
                             │ inspect headers / names
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Schema analysis (S1–S5)                                         │
│  PHILGEPS_SCHEMA_ANALYSIS.json · philgeps-schema.md              │
└────────────────────────────┬────────────────────────────────────┘
                             │ config/schema_mappings.yaml
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Canonical fields (53 open-data fields)                          │
│  PHILGEPS_CANONICAL_FIELD_MAP.json                               │
└────────────────────────────┬────────────────────────────────────┘
                             │ config/canonical_to_ocds.yaml
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  OCDS 1.1 paths                                                  │
│  PHILGEPS_OCDS_CSV_CROSSWALK.md · philgeps-*.json templates      │
│  SAMPLE_OCDS_RELEASE_PACKAGE.json (sample built from rules)      │
└────────────────────────────┬────────────────────────────────────┘
                             │ scripts/build_schema_field_map.py
                             │   (build_app_bundle, build_sample_release_package)
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  Interactive webapp (app/)                                       │
│  app/src/data/schema_bundle.json → React SPA                     │
└────────────────────────────┬────────────────────────────────────┘
                             │ scripts/validate_sample_release.py (libcoveocds)
                             ▼
                        OCDS 1.1 schema validation (CI)
```

## Schema periods (S1–S5)

| Key | Period | Format | Cols |
|-----|--------|--------|-----:|
| S1 | 2000–2015 | XLSX, header row 3 | 40 |
| S2 | 2016–2020 | XLSX, header row 3 | 40 |
| S3 | 2021–2024 | CSV | 43 |
| S4 | 2025+ | CSV | 46 |
| S5 | 2021–2024-V2 | CSV (same layout as S4) | 46 |

**Rule:** Always map by **column name**, never by column index.

## Interactive webapp (`app/`)

A Vite + React + TypeScript single-page app renders every layer above as searchable, filterable UI. It is the digestible replacement for scrolling the 151-row markdown crosswalk or reading YAML by hand.

| Section | What it shows |
|---------|---------------|
| Overview | Summary cards + the data-flow diagram above |
| Canonical fields | All 53 fields with type, S1–S5 columns, OCDS paths, expandable detail |
| OCDS crosswalk | 151 rows, filter by OCDS block and status (mapped / omit / derived / extension) |
| OCDS staged output | `canonical_to_ocds.yaml` as one card per OCDS block — path → canonical field |
| OCDS release package | Representative compiled OCDS release: overview, per-block jump links, syntax-highlighted raw JSON with copy and download |
| Schema periods | Per-schema column inventory |
| Schema evolution | Field-level change classification across 25 years |
| Source column lookup | Paste a CSV header → canonical field → OCDS path |
| Codelist mappings | PhilGEPS labels → OCDS closed codelists |
| Global search | Cross-section search for any column, path, or field |

The app imports a single bundled JSON (`app/src/data/schema_bundle.json`) emitted by `scripts/build_schema_field_map.py`. No backend, no runtime fetch.

```bash
python scripts/build_schema_field_map.py
cd app && npm install && npm run dev   # http://localhost:5173
```

See [../app/README.md](../app/README.md) for full details.

## External sources

| Source | URL |
|--------|-----|
| Raw exports archive | [Google Drive RAW_CSV](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing) |
| Interactive schema UI | [philgeps.simple-systems.dev/about/schema](https://philgeps.simple-systems.dev/about/schema) |
| OCDS mapping templates | [ocds.simple-systems.dev/p/mphilgeps/overview](https://ocds.simple-systems.dev/p/mphilgeps/overview) |
| Schema.tsx (upstream tables) | [philgeps-awards-dashboard](https://github.com/csiiiv/philgeps-awards-dashboard/blob/main/frontend/src/pages/About/Schema.tsx) |

## Relationship to other projects

This repo is designed to be **consumed independently**. A separate data pipeline (e.g. [philgeps_data_analysis](https://github.com/BetterGovPH/philgeps_data_analysis) or your own ingest) may:

- Import `PHILGEPS_CANONICAL_FIELD_MAP.json` for column normalization
- Copy or submodule `config/schema_mappings.yaml` as its mapping source
- Use the crosswalk for OCDS publication design

No runtime dependency on those projects is required to use the reference files.

## Out of scope (for now)

- Raw data storage or download scripts
- OCDS JSON compilation / Cardinal red-flag engine
- Live PhilGEPS API or WSF ingest
- Automated validation against production exports (planned extension point)

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to extend mappings and regenerate artifacts.
