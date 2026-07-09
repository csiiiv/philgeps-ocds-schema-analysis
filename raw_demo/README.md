# Demo Datasets

This directory contains **demo datasets** for development, testing, and CI/CD pipelines.

## Purpose

These demo datasets allow you to:
- Clone and run the analysis without downloading large datasets (350MB+)
- Build and deploy the webapp immediately after `git pull`
- Test data transformations without full datasets
- Use in CI/CD pipelines for continuous validation
- Demonstrate the analysis workflow with real data patterns

## Files

- `2024-10--2024-12-demo.csv` - ~200 rows from Oct-Dec 2024 (0.15 MB)
  - Sample from the full 512,719-row dataset
  - Maintains diversity across procurement modes, organizations, and regions
  - Can be used with all transformation scripts

## Usage

```bash
# Transform demo data to OCDS
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv

# Build webapp with demo data
python scripts/build_schema_field_map.py
cd app && npm install && npm run dev
```

All scripts work identically with demo and full datasets - just with fewer records.

## Generating New Demo Data

If you have access to full datasets and want to create new demo samples:

```bash
# Generate from any large CSV export
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/new-demo.csv --rows 200

# With different sample size
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/new-demo.csv --rows 500

# With custom random seed for reproducibility  
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/new-demo.csv --seed 123
```

The `generate_demo_data.py` script ensures representative sampling by:
- Stratifying by procurement modes (19 modes)
- Ensuring organization type diversity (14 types)
- Including multiple regions (17+ regions)
- Covering notice/award statuses
- Maintaining award vs. non-award record ratios

## Size Guidelines

For inclusion in git, demo datasets should be:
- **< 1 MB** for quick cloning and development
- **100-500 rows** for meaningful diversity without overwhelming size
- **Stratified samples** representing key data patterns

## Full Datasets

For production analysis, download complete datasets from Google Drive:
→ [docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)