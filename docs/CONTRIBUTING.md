# Contributing

This repo is mapping-centric: changes flow from **config** → **generated JSON/markdown** → **downstream consumers**.

## Repository layout

```
philgeps-schema-analysis/
├── README.md                 # Entry point
├── config/
│   ├── schema_mappings.yaml  # Source of truth: export column → canonical field (S1–S5)
│   ├── canonical_to_ocds.yaml # Canonical field → OCDS 1.1 path
│   └── ocds_codelist_mappings.yaml # PhilGEPS value → OCDS codelist codes
├── references/               # Committed reference artifacts (human + machine)
│   └── SAMPLE_OCDS_RELEASE_PACKAGE.json  # Generated sample — validated in CI
├── scripts/
│   ├── build_schema_field_map.py    # Emits FIELD_MAP.json, crosswalk, app bundle, sample
│   ├── _ocds_checks.py              # Shared OCDS pre-flight rules (used by build + validate)
│   ├── validate_sample_release.py   # libcoveocds validation of the sample package
│   └── test_ocds_checks.py          # Guard integrity tests for _ocds_checks
├── app/                      # Interactive webapp (Vite + React + TS)
│   └── src/data/schema_bundle.json  # Generated — do not hand-edit
├── .github/workflows/
│   └── build-and-validate.yml # Regenerates artifacts, validates sample, builds webapp
└── docs/
```

## Change workflows

### Add or rename a canonical field

1. Add the field to `config/schema_mappings.yaml`:
   - `field_types` (string, decimal, date, …)
   - Each affected `schema_1` … `schema_5` block
2. If it maps to OCDS, add paths in `config/canonical_to_ocds.yaml` (or `philgeps_extension` for PhilGEPS-specific fields).
3. Run `python scripts/build_schema_field_map.py`.
4. If the field appears in the OCDS crosswalk, add or update the curated row in `references/PHILGEPS_OCDS_CSV_CROSSWALK.md` (OCDS / PhilGEPS 1.5 / 2.0 / V1 / V2 columns) and add overrides in the build script if needed (see below).

### Update schema evolution (new export layout)

1. Document findings in `references/philgeps-schema.md` (narrative) and/or update `references/PHILGEPS_SCHEMA_ANALYSIS.json` (structured).
2. Update `config/schema_mappings.yaml` for the new schema key (e.g. `schema_6`).
3. Extend `OPEN_SCHEMA_KEYS` in `scripts/build_schema_field_map.py` if a new period is added.
4. Regenerate artifacts.

### Fix crosswalk Canonical text only

Prefer driving changes through `schema_mappings.yaml` so JSON and crosswalk stay in sync.

For edge cases (derived IDs, omit rules, multi-field OCDS paths), edit dictionaries in `scripts/build_schema_field_map.py`:

| Dict | Purpose |
|------|---------|
| `OCDS_CANONICAL` | Default OCDS path → canonical field |
| `CANONICAL_AI_OVERRIDES` | Fixed Canonical column strings |
| `OCDS_ROW_DISAMBIGUATORS` | Repeated OCDS paths (e.g. `parties/name`) |
| `UNMAPPED_ROW_CANONICAL` | Rows with OCDS field `—` |

Then regenerate.

## Generated vs hand-curated

| File | Generated? | Notes |
|------|------------|-------|
| `PHILGEPS_CANONICAL_FIELD_MAP.json` | Yes | Full regen from config + schema analysis |
| Crosswalk **Canonical** column | Yes | Compact S1–S5 strings |
| Crosswalk other columns | Hand-curated | From PS-DBM templates + review |
| `app/src/data/schema_bundle.json` | Yes | Bundled JSON consumed by the webapp (single source for all sections) |
| `references/SAMPLE_OCDS_RELEASE_PACKAGE.json` | Yes | Sample OCDS release package compiled from `SAMPLE_CANONICAL_ROW`; validated against OCDS 1.1 via `libcoveocds` in CI |
| `philgeps-1.5.json`, `mphilgeps.json` | Imported | Re-import when PS-DBM publishes new template versions |
| `PHILGEPS_SCHEMA_ANALYSIS.json` | Hand-curated / synced from Schema.tsx | |

## OCDS sample release validation

The build emits `references/SAMPLE_OCDS_RELEASE_PACKAGE.json` and validates it through a three-layer pipeline: a build-time hard-fail, libcoveocds schema validation, and guard-integrity tests. The shared rules live in `scripts/_ocds_checks.py`.

See [VALIDATION.md](VALIDATION.md) for the full layered model, the rules each layer enforces, and how to extend them.

## Webapp development

The `app/` directory is a standalone Vite project. To iterate on UI only (no data changes), just run `npm run dev` — the committed `schema_bundle.json` is reused. To pick up mapping changes, run `npm run regen-data` (which calls `python ../scripts/build_schema_field_map.py`) and restart the dev server.

The bundle shape is typed in `app/src/data/types.ts`. If you add a new top-level key in `build_app_bundle()`, add the matching type and a section page; the rest of the app stays decoupled.

## Validation checklist

Before opening a PR:

- [ ] `python scripts/build_schema_field_map.py` runs cleanly
      (the build hard-fails on malformed OCDS shape via `scripts/_ocds_checks.py`
      before writing the sample — no bad release can land on disk)
- [ ] `python scripts/test_ocds_checks.py` passes
      (guards the guards: confirms each known regression class is still caught)
- [ ] `python scripts/validate_sample_release.py` reports `# OK`
      (full OCDS 1.1 schema validation via libcoveocds)
- [ ] JSON diff shows expected `canonical_fields` / `source_column_index` changes
- [ ] Crosswalk row count remains 151 (unless intentionally adding rows)
- [ ] New canonical fields have `field_types` entry
- [ ] Privacy-sensitive columns stay out of canonical output (`excluded_source_columns`)
- [ ] `app/src/data/schema_bundle.json` regenerated and `summary` counts look right
- [ ] (If UI changed) `cd app && npm run build` passes `tsc --noEmit`

## Planned extensions (standalone repo roadmap)

Ideas that fit this repo without requiring the full data pipeline:

- JSON Schema export for canonical records
- CLI: `philgeps-schema detect --headers file.csv`
- CI check: regen script produces clean git diff
- Validator: compare live export headers against `source_column_index`
- Package publish (`pip install philgeps-schema-analysis`)

## Provenance

When copying material from external sources, note the origin in commit messages:

- PS-DBM OCDS templates v0.91 → `philgeps-1.5.json`, `mphilgeps.json`
- Schema.tsx / Awards Data Explorer → `PHILGEPS_SCHEMA_ANALYSIS.*`
- Raw file inspection → `philgeps-schema.md`

## Questions

For PhilGEPS export format issues, cross-check [philgeps.simple-systems.dev/about/schema](https://philgeps.simple-systems.dev/about/schema) and the [Google Drive archive](https://drive.google.com/drive/folders/1kkqBC60VPHmdlZfntu3A-8pSKAdIh2Nx?usp=sharing).
