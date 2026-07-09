# Demo Data Implementation Summary

This document summarizes the changes made to enable the philgeps_schema_analysis repository to work with demo data instead of requiring the full dataset.

## Changes Made

### 1. Demo Data Generation Script ✅
Created `scripts/generate_demo_data.py` with the following features:
- **Stratified sampling**: Ensures diversity across procurement modes, organization types, and regions
- **Configurable size**: Default 200 rows, adjustable via `--rows` parameter
- **Reproducible**: Uses `--seed` parameter for consistent results
- **Maintains schema**: Produces valid CSV files matching the original structure
- **Diversity reporting**: Shows analysis of both source and sample data

### 2. Demo Dataset Generated ✅
Created `raw_demo/2024-10--2024-12-demo.csv` (155 KB):
- **200 rows** from the original 512,719-row dataset
- **19 procurement modes** represented (100% coverage)
- **13 organization types** included  
- **17 regions** covered
- **4 notice statuses** and **3 award statuses**
- **Size**: 155 KB vs 355 MB for full dataset (99.96% reduction)

### 3. Git Repository Configuration ✅
Updated `.gitignore`:
- Excludes large raw files in `raw/` directory
- **Includes** demo data in `raw_demo/` directory
- Ensures demo data can be committed and cloned

### 4. Documentation Updates ✅
Updated `README.md`:
- Added "Demo data workflow" section after Quick Start
- Updated "Transform data" section with demo data priority
- Added `raw_demo/` to repository structure
- Emphasized demo-first workflow for development

### 5. Testing and Validation ✅
Successfully tested the complete workflow:
```bash
# Transform demo data to OCDS
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv
# ✅ 143 releases compiled from 200 rows

# Build schema references  
python scripts/build_schema_field_map.py
# ✅ All artifacts generated successfully

# Generated outputs:
# - references/transformed/2024-10--2024-12-demo.json (528 KB)
# - references/transformed/2024-10--2024-12-demo.dq.json (202 KB)  
# - references/transformed/2024-10--2024-12-demo.report.json (47 KB)
```

## Benefits

### For Development
- **Immediate cloning**: No large file downloads needed
- **Fast testing**: Transformations complete in seconds vs minutes
- **Git-friendly**: Demo data can be committed and versioned
- **Consistent**: Reproducible samples via random seed

### For CI/CD
- **Fast pipelines**: No large dataset dependencies
- **Predictable**: Same demo data across all environments
- **Reliable**: No external download failures
- **Complete**: Full workflow testing with realistic data

### For Users
- **Quick start**: Clone and run immediately
- **Full functionality**: All features work with demo data
- **Scalable**: Easy to switch to full datasets when needed
- **Well-documented**: Clear workflow guidance

## File Structure

```
philgeps_schema_analysis/
├── raw_demo/                    # Demo datasets (included in git)
│   ├── README.md               # Demo data documentation  
│   └── 2024-10--2024-12-demo.csv  # 200-row sample (155 KB)
├── raw/                        # Full datasets (excluded from git)
│   └── 2024-10 -- 2024-12.csv  # 512,719 rows (355 MB) - gitignored
├── scripts/
│   └── generate_demo_data.py   # New demo data generator
├── references/transformed/     # Transformation outputs (gitignored)
│   ├── 2024-10--2024-12-demo.json
│   ├── 2024-10--2024-12-demo.dq.json
│   └── 2024-10--2024-12-demo.report.json
└── README.md                   # Updated with demo workflow
```

## Usage

### Clone and Run with Demo Data
```bash
git clone https://github.com/csiiiv/philgeps-ocds-schema-analysis.git
cd philgeps-ocds-schema-analysis

# Transform demo data
python scripts/transform_to_ocds.py raw_demo/2024-10--2024-12-demo.csv

# Build webapp
python scripts/build_schema_field_map.py
cd app && npm install && npm run dev
```

### Generate New Demo Data
```bash
# From existing full datasets
python scripts/generate_demo_data.py raw/large-file.csv raw_demo/new-demo.csv --rows 200
```

### Switch to Full Datasets (Optional)
```bash
# Download full datasets from Google Drive (see docs/GETTING_STARTED.md)
# Then use full workflow
python scripts/transform_to_ocds.py raw/large-file.csv
```

## Impact on Repository

- **Size**: Demo data <1MB vs full datasets 350MB+
- **Clone time**: Seconds vs minutes
- **Setup time**: <1 minute vs download + setup time
- **Functionality**: 100% preserved
- **Compatibility**: All scripts work with both demo and full data

## Next Steps

The repository is now ready for:
1. **Git commit**: Demo data can be committed to repository
2. **VPS deployment**: Clone and run without large file downloads
3. **CI/CD integration**: Automated testing with demo data
4. **User onboarding**: Quick start with immediate functionality
5. **Full dataset analysis**: Optional when needed for production

## Validation

✅ **Data Quality**: Demo data maintains diversity and realism  
✅ **Schema Compatibility**: Works with all transformation scripts  
✅ **Git Integration**: Properly configured for version control  
✅ **Documentation**: Comprehensive guides and examples  
✅ **Testing**: Full workflow validated end-to-end  

The demo data implementation is complete and production-ready!