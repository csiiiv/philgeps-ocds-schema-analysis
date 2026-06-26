# Getting started

## Prerequisites

- Python 3.10+
- Optional: `pip install -r requirements.txt` (only needed to **regenerate** JSON/markdown artifacts)

## Clone and explore (no build required)

Most consumers only need the committed reference files:

```bash
git clone <your-repo-url> philgeps-schema-analysis
cd philgeps-schema-analysis
```

| Goal | Start here |
|------|------------|
| **Browse everything interactively** | [Run the webapp](#run-the-webapp) — canonical browser, OCDS crosswalk, staged output, search |
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

After regenerating, restart `npm run dev` (or rebuild) inside `app/` so the webapp picks up the new bundle.

Curated crosswalk columns (OCDS, PhilGEPS 1.5/2.0, V1/V2 CSV) are preserved; see [CONTRIBUTING.md](CONTRIBUTING.md) for override hooks in the build script.

## Obtain raw data

This repo does not include exports. Download from:

[RAW_CSV — Google Drive](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing)

Suggested layout for local testing:

```
data/raw/
  2000-2012/          # XLSX
  2013-2020/          # XLSX
  2021-2025/          # CSV (S3)
  2021-2025-V2/       # CSV (S5)
```

## Next steps

- [OVERVIEW.md](OVERVIEW.md) — architecture and scope
- [CONTRIBUTING.md](CONTRIBUTING.md) — extend mappings, add schemas, publish changes
- [../app/README.md](../app/README.md) — webapp sections, scripts, architecture
- [../README.md](../README.md) — full file index
