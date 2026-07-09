# Demo Year Data Guide

This repository now includes comprehensive demo datasets spanning the entire PhilGEPS history (2000-2025), enabling immediate development and testing without downloading large files.

## Demo Data Structure

### Raw Demo Data (CSV files)
- `raw_demo/2024-10--2024-12-demo.csv` - 200 rows from recent period (155 KB)
- Used for transformation pipeline testing

### Transformed Demo Data (OCDS packages)  
- `references/transformed/demo_by_year/*.json` - Year-by-year OCDS demo packages
- Each file contains ~200-1000 releases per year
- Total size: ~60MB vs 10GB+ for full dataset

## Year Coverage

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

The webapp will automatically use demo year data from `references/transformed/demo_by_year/` for:
- **Release Browser** - Browse releases by year
- **Year Data Quality** - View DQ reports per year
- **ETL Pipeline Stats** - See transformation metrics

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