# Demo Year Data Guide

Demo data is **only for the Release browser**. Pipeline overview, year data quality, and overall data quality use **full-dataset reports** (small JSON files committed or generated locally).

## What uses what

| Webapp section | Data source | Size | In git? |
|----------------|-------------|------|---------|
| **Pipeline overview** | `combined.report.json` → embedded in `schema_bundle.json` | ~9 MB | Yes (`combined.report.json`) |
| **Overall data quality** | same `combined.report.json` roll-up | (embedded) | Yes |
| **Year data quality** | `by_year/dq/{year}.json` | ~10 MB total | Yes (`by_year/dq/`) |
| **Release browser** | `demo_by_year/browser/` + `demo_by_year/release/` | ~100 MB deploy | Yes (`demo_by_year/`) |
| Full release corpus | `by_year/*.json` + `by_year/browser/` | 10+ GB | No (Google Drive) |

## Demo data structure (release browser only)

### Raw demo CSV
- `raw_demo/2024-10--2024-12-demo.csv` — 200 rows for transform pipeline testing

### Transformed demo OCDS packages
- `references/transformed/demo_by_year/*.json` — sampled year packages (~200–1000 releases/year)
- `references/transformed/demo_by_year/browser/` — release list caches for the browser
- Materialized at build time: `app/public/data/release/{year}/{ocid}.json`

## Full-dataset reports (small, committed)

| File | Purpose | Size |
|------|---------|------|
| `references/transformed/combined.report.json` | Corpus-wide DQ + per-year stats for Pipeline / Overall DQ | ~9 MB |
| `references/transformed/by_year/dq/{year}.json` | Per-year DQ with source row samples | ~300–35 KB/year |

Regenerate after full ETL:

```bash
python scripts/run_full_dataset.py --no-quiet
python scripts/build_year_dq_cache.py
python scripts/aggregate_dataset_report.py
python scripts/build_schema_field_map.py
```

## Year coverage (demo release browser)

| Years | Schema Period | Releases | File Size | Original Size |
|-------|--------------|----------|-----------|---------------|
| 2000 | S1 (2000-2015 XLSX) | ~50 | 8 KB | 8 KB |
| 2002-2003 | S1 | ~200-300 | 2.5-2.6 MB | 5.9-7.6 MB |
| 2004-2017 | S1-S2 | ~300-400 | 2.3-3.1 MB | 14-890 MB |
| 2018-2025 | S3-S4-S5 | ~200-500 | 2-3 MB | 640-1.4 GB |

## Usage

### Webapp Development
```bash
# Build schema bundle (includes demo data references)
python scripts/build_schema_field_map.py

# Start webapp - demo year data loads automatically
cd app && npm run dev
```

The webapp uses demo data from `references/transformed/demo_by_year/` **only for the Release browser** (`#/etl-releases/{year}`).

Pipeline overview, overall DQ, and year DQ use full-dataset reports:
- `combined.report.json` (embedded at build time)
- `by_year/dq/{year}.json` (fetched at `/data/dq/{year}.json`)

### Script Development
```bash
# Use demo CSV for transformation testing
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv

# Use specific year for OCDS analysis
python scripts/analyze_year.py --year 2020 --input references/transformed/demo_by_year/2020.json
```

### Data Exploration
```bash
# Explore demo releases directly
jq '.releases | length' references/transformed/demo_by_year/2020.json
jq '.releases[0].tender' references/transformed/demo_by_year/2020.json
```

## Demo Data Characteristics

### Diversity Coverage
- **Procurement Methods**: All 19 modes represented across years
- **Organizations**: National agencies, LGUs, hospitals, schools, etc.
- **Geographic Coverage**: All 17+ regions
- **Schema Evolution**: Complete S1-S5 timeline coverage

### Data Quality
- **Schema Validation**: All demo packages valid OCDS 1.1
- **Field Completeness**: Representative of full dataset patterns
- **Temporal Coverage**: Key historical periods included

## Generating New Demo Data

### From Raw CSV
```bash
# Generate new raw demo sample
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/new-demo.csv --rows 200
```

### From Transformed OCDS
```bash
# Generate additional year samples
python scripts/generate_year_demo_samples_efficient.py --years 2026 --samples 500

# Regenerate specific year with different sample size
python scripts/generate_year_demo_samples_efficient.py --years 2024 --samples 300
```

## Performance Benefits

### Development Workflow
- **Clone Time**: Seconds vs minutes (no large files)
- **Transform Speed**: 5-10 seconds vs minutes
- **Webapp Startup**: Instant (no large file loading)
- **Testing**: Fast iteration cycles

### CI/CD Pipeline
- **Build Time**: Minimal (no large data dependencies)
- **Storage**: Small Docker images
- **Reliability**: No network download failures

## File Sizes Comparison

| Data Type | Full Dataset | Demo Dataset | Reduction |
|-----------|--------------|--------------|-----------|
| Raw CSVs | 350+ MB | 155 KB | 2,250x |
| Year Packages | 10+ GB | ~60 MB | 166x |
| Individual Years | 139 MB - 1.4 GB | 2-3 MB | 50-700x |

## Switching to Full Datasets

When you need complete analysis:

```bash
# Download full datasets from Google Drive (see docs/GETTING_STARTED.md)
# Place in references/transformed/by_year/

# Webapp will automatically use full datasets when available
# Demo data ignored when full year packages exist
```

## Troubleshooting

### Webapp Not Loading Demo Data
```bash
# Verify demo year files exist
ls -la references/transformed/demo_by_year/

# Check webapp config points to demo directory
# app/src/data/ should reference demo_by_year for development
```

### Memory Issues with Large Years
Use the efficient script for files >100MB:
```bash
python scripts/generate_year_demo_samples_efficient.py --years 2024
```

### Missing Years
```bash
# Check which years are available
ls references/transformed/by_year/*.json | wc -l

# Generate missing years
python scripts/generate_year_demo_samples_efficient.py --years 2025
```

## Maintenance

### Adding New Years
1. Transform new year data to `references/transformed/by_year/YYYY.json`
2. Generate demo package: `python scripts/generate_year_demo_samples_efficient.py --years YYYY`
3. Update webapp configuration if needed

### Updating Demo Samples
```bash
# Regenerate all demo data with current settings
python scripts/generate_year_demo_samples_efficient.py --years all
```

## Next Steps

1. ✅ **Demo Data Generated** - Complete year coverage
2. 🔄 **Webapp Integration** - Configure to use demo data
3. 📄 **Documentation** - Update user guides
4. 🧪 **Testing** - Verify all features work with demo data
5. 🚀 **Deployment** - Push to git for easy VPS deployment

---

The demo year data provides comprehensive, realistic samples across the entire PhilGEPS timeline while keeping the repository lightweight and fast for development!