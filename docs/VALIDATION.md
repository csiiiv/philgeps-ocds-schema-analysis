# OCDS validation

How this repo guarantees the sample OCDS release package is schema-conformant — and how the same rules can be reused downstream.

## Scope

This repo validates OCDS 1.1 **shape** in two contexts:

1. **Synthetic sample** — `SAMPLE_OCDS_RELEASE_PACKAGE.json`, built from `SAMPLE_CANONICAL_ROW` via `config/canonical_to_ocds.yaml` (runs in CI).
2. **Transform output** — release packages from `scripts/transform_to_ocds.py`, validated on demand with `scripts/validate_transform_sample.py` (not in CI; outputs are gitignored and large).

Validation does **not** certify that every canonical mapping decision is correct against all PhilGEPS exports — only that emitted JSON conforms to OCDS structure and schema. Process identity (`ocid`, `release.id`) must be unique per release within a package — see [OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md).

## Validation layers

These layers run in CI for the synthetic sample. Transform output uses layers 1–2 via `validate_transform_sample.py`; layers 3–5 are unit-test guards shared with the transform pipeline.

| Layer | Script | When | Catches | Requires |
|-------|--------|------|---------|----------|
| 1. Build-time hard-fail | `build_schema_field_map.py` → `_ocds_checks.assert_release_package` | Before the sample file is written | Malformed structure, version/extension rules, date formats | Nothing |
| 2. Pre-flight + deep schema | `validate_sample_release.py` or `validate_transform_sample.py` | On demand / after transform | Layer 1 rules, then full JSON Schema via libcoveocds | `requirements-dev.txt` |
| 3. Pre-flight guard integrity | `test_ocds_checks.py` | CI | Known package-shape regressions still fire | Nothing |
| 4. Compiler guard integrity | `test_ocds_compiler.py` | CI | Grouped item-id disambiguation, JV supplier expansion | PyYAML |
| 5. Data-quality guard integrity | `test_data_quality.py` | CI | Group validation rules, sample caps / compaction | Nothing |

Layer 1 is the most important: a bad release **cannot land on disk**. The build raises a `ValueError` with the offending paths before opening the output file.

## Transform output validation

Real PhilGEPS exports are transformed by `scripts/transform_to_ocds.py` (CSV) or `scratch/sample_and_transform.py` (XLSX). Batch processing: `scripts/run_full_dataset.py`. Outputs live in `references/transformed/` (gitignored — regenerate locally).

Each file produces `.json`, `.dq.json`, and unified `.report.json`. Dataset-wide stats: `references/transformed/combined.report.json`. See [ETL_PIPELINE.md](ETL_PIPELINE.md).

```bash
# Quick iteration (1000 rows)
python scripts/transform_to_ocds.py raw/<export>.csv --sample 1000 --out references/transformed/sample1k

# Pre-flight + libcoveocds on the transformed package
python scripts/validate_transform_sample.py references/transformed/sample1k.json

# Full export (large; ~4–5 minutes on the 356MB S4 file)
python scripts/transform_to_ocds.py "raw/2024-10 -- 2024-12.csv"
python scripts/validate_transform_sample.py "references/transformed/2024-10 -- 2024-12.json"
```

`validate_transform_sample.py` runs the same two layers as the sample pipeline: `_ocds_checks` pre-flight, then libcoveocds JSON Schema validation.

## What the rules catch

The shared rules live in `scripts/_ocds_checks.py` (function `check_release_package`). They cover every error class we have actually hit while building the sample:

| Rule | Example bad input | Why it matters |
|------|-------------------|----------------|
| `releases` is a direct array of release objects | `[{"release": {...}}]` (wrapped) | A wrapped release passes Python type checks but fails OCDS schema — the historical regression that prompted this layer |
| `version` is `major.minor` only | `"1.1.5"` | OCDS schema rejects patch digits; the tool always uses the latest patch for a major.minor |
| Extensions pinned to tags, not `/master` | `.../ocds_bid_extension/master/extension.json` | `/master` references drift and can break extension resolution (the `SubmissionTerms` error we hit) |
| Date-times are RFC 3339 with explicit timezone | `"2025-04-28T09:00:00"` (missing offset) | OCDS date-time fields require `Z` or `+HH:MM`; without it, validation fails |
| Date-time fields have a time component | `"2025-05-12"` on `release.date` | Bare dates are valid RFC 3339 but wrong for `date-time`-typed fields |
| Required release fields present | missing `ocid`, `id`, `date`, `initiationType`, `tag` | Core OCDS schema requirement |
| Unique `(ocid, id)` per release | two releases with same `ocid` and `id` | libcoveocds rejects duplicate keys; bid-first display policy avoids most cases ([OCDS_ID_GENERATION.md](OCDS_ID_GENERATION.md)) |

The date walker recurses the entire package tree, so nested dates (tender periods, award dates, contract periods, bid dates, milestones) are covered — not just the top-level fields.

## Running locally

```bash
pip install -r requirements-dev.txt          # libcoveocds; Python ≥3.9, <3.13
python scripts/build_schema_field_map.py     # layer 1
python scripts/test_ocds_checks.py           # layer 3
python scripts/test_ocds_compiler.py         # layer 4
python scripts/test_data_quality.py          # layer 5
python scripts/validate_sample_release.py    # layer 2 (synthetic sample)
```

Layers 1, 3, 4, and 5 have no libcoveocds dependency. Layer 2 requires libcoveocds (engine behind the [OCDS Data Review Tool](https://ocds-data-review-tool.readthedocs.io/)).

## Extending the rules

When a new failure mode appears (whether caught by libcoveocds or found by hand):

1. Add a check to `check_release_package()` in `scripts/_ocds_checks.py`. Return a human-readable string describing the issue; include the JSON pointer to the offending value.
2. Add a regression case to `scripts/test_ocds_checks.py` that mutates the clean baseline package and asserts the new rule fires.
3. Run `python scripts/test_ocds_checks.py` to confirm the guard works, then `python scripts/build_schema_field_map.py` to confirm the build still passes on clean input.

Both the build (layer 1) and the validator (layer 2) automatically pick up the new rule — they share the module.

## Relationship to the OCDS Data Review Tool

[open-contracting/cove-ocds](https://github.com/open-contracting/cove-ocds) is a Django web app that validates complete, compiled OCDS release packages and records against the standard. We use its underlying library, [libcoveocds](https://github.com/open-contracting/lib-cove-ocds), as layer 2 of this pipeline.

The Data Review Tool is designed for publishers to validate their real output. Our transform pipeline reuses the same libcoveocds engine via `validate_transform_sample.py` for local checks on real CSV exports — see [TRANSFORM.md](TRANSFORM.md).
