# OCDS validation

How this repo guarantees the sample OCDS release package is schema-conformant — and how the same rules can be reused downstream.

## Scope

This repo validates the **shape** of one sample OCDS 1.1 release package, built from `SAMPLE_CANONICAL_ROW` via the staging rules in `config/canonical_to_ocds.yaml`. It does **not** validate:

- The *correctness* of the canonical mapping against real PhilGEPS exports
- Real OCDS data produced by a downstream compiler pipeline

For real-data validation, run [libcoveocds](https://github.com/open-contracting/lib-cove-ocds) or the [OCDS Data Review Tool](https://ocds-data-review-tool.readthedocs.io/) against the downstream pipeline's actual output. That work is out of scope here.

## The three layers

Validation runs in three layers, each catching regressions earlier than the last. All three run in CI on every push and pull request.

| Layer | Script | When | Catches | Requires |
|-------|--------|------|---------|----------|
| 1. Build-time hard-fail | `build_schema_field_map.py` → `_ocds_checks.assert_release_package` | Before the sample file is written | Malformed structure, version/extension rules, date formats | Nothing |
| 2. Pre-flight + deep schema | `validate_sample_release.py` | After build, in CI and on demand | Same rules as layer 1, then full JSON Schema via libcoveocds | `pip install -r requirements-dev.txt` |
| 3. Guard integrity | `test_ocds_checks.py` | After layer 2, in CI | Verifies each known regression class still fires a failure | Nothing |

Layer 1 is the most important: a bad release **cannot land on disk**. The build raises a `ValueError` with the offending paths before opening the output file.

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

The date walker recurses the entire package tree, so nested dates (tender periods, award dates, contract periods, bid dates, milestones) are covered — not just the top-level fields.

## Running locally

```bash
pip install -r requirements-dev.txt          # only needed for layer 2 (libcoveocds); Python ≥3.9, <3.13
python scripts/build_schema_field_map.py     # layer 1: hard-fails on bad shape, nothing else needed
python scripts/test_ocds_checks.py           # layer 3: guard integrity (runs anywhere, no deps)
python scripts/validate_sample_release.py    # layer 2: full schema validation via libcoveocds
```

Layers 1 and 3 have no third-party dependencies — they run on a fresh checkout with only Python's standard library. Layer 2 pulls in libcoveocds, the engine behind the OCDS Data Review Tool.

## Extending the rules

When a new failure mode appears (whether caught by libcoveocds or found by hand):

1. Add a check to `check_release_package()` in `scripts/_ocds_checks.py`. Return a human-readable string describing the issue; include the JSON pointer to the offending value.
2. Add a regression case to `scripts/test_ocds_checks.py` that mutates the clean baseline package and asserts the new rule fires.
3. Run `python scripts/test_ocds_checks.py` to confirm the guard works, then `python scripts/build_schema_field_map.py` to confirm the build still passes on clean input.

Both the build (layer 1) and the validator (layer 2) automatically pick up the new rule — they share the module.

## Relationship to the OCDS Data Review Tool

[open-contracting/cove-ocds](https://github.com/open-contracting/cove-ocds) is a Django web app that validates complete, compiled OCDS release packages and records against the standard. We use its underlying library, [libcoveocds](https://github.com/open-contracting/lib-cove-ocds), as layer 2 of this pipeline.

The Data Review Tool is designed for publishers to validate their real output. It is **not** a schema-mapping validator, and our use of its engine here only checks the shape of one sample — it does not certify that our canonical mapping is correct against real PhilGEPS data.
