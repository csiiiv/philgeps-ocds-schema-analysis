#!/bin/bash
set -e

# Build script for production static hosting
# Usage: ./scripts/build_production.sh
#
# Data split:
#   - Pipeline overview + Overall DQ → full combined.report.json (embedded in schema_bundle.json)
#   - Year data quality → full by_year/dq/*.json (~10 MB total)
#   - Release browser → demo_by_year samples only (~100 MB materialized)

echo "Building PhilGEPS Schema Explorer for production..."

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "📁 Repository root: $REPO_ROOT"

if [ ! -f references/transformed/combined.report.json ]; then
  echo "⚠️  WARNING: references/transformed/combined.report.json not found."
  echo "   Pipeline overview and Overall DQ will show demo/single-file stats only."
  echo "   Add combined.report.json (from full ETL) for full-dataset DQ roll-up."
fi

if [ ! -d references/transformed/by_year/dq ] || [ -z "$(ls -A references/transformed/by_year/dq/*.json 2>/dev/null)" ]; then
  echo "⚠️  WARNING: references/transformed/by_year/dq/ is empty."
  echo "   Year data quality pages will 404. Run: python scripts/build_year_dq_cache.py"
fi

# 1. Generate schema bundle (embeds combined.report.json when present)
echo "📊 Generating schema bundle..."
python scripts/build_schema_field_map.py

# 1b. Demo fallback: ETL pages need transform metadata in the JS bundle
echo "🔧 Ensuring transform metadata (demo fallback if no combined report)..."
python scripts/build_demo_transform_bundle.py

# 2. Generate demo browser caches for release browser
echo "🗂️  Generating demo browser caches..."
python scripts/build_year_browser_cache.py --input references/transformed/demo_by_year

# 3. Stage static data for production
echo "📁 Staging static data into app/public/data/..."
rm -rf app/public/data
mkdir -p app/public/data/releases app/public/data/dq

# Release browser: demo samples only
cp references/transformed/demo_by_year/browser/*.json app/public/data/releases/

# Year DQ: full-dataset caches (small)
if [ -d references/transformed/by_year/dq ]; then
  cp references/transformed/by_year/dq/*.json app/public/data/dq/ 2>/dev/null || true
fi

# 4. Materialize demo release detail files for static hosting
echo "📄 Materializing demo release detail files..."
python scripts/materialize_release_detail_files.py

# 5. Build webapp
echo "🏗️  Building production bundle..."
cd app
npm install
npm run build

# 6. Verify build
echo "✅ Build complete!"
echo ""
echo "📦 Build output: app/dist/"
du -sh dist/
echo ""
echo "Data sources:"
echo "  Pipeline / Overall DQ → combined.report.json (embedded in JS bundle)"
echo "  Year DQ             → dist/data/dq/ (full dataset, $(ls -1 dist/data/dq/*.json 2>/dev/null | wc -l) years)"
echo "  Release browser     → dist/data/releases/ + dist/data/release/ (demo samples)"
echo ""
echo "🧪 Test locally: cd app && npx serve dist -p 4173"
