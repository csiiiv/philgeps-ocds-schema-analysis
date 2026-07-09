#!/bin/bash
set -e

# Build script for production static hosting
# Usage: ./scripts/build_production.sh

echo "Building PhilGEPS Schema Explorer for production..."

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$REPO_ROOT"

echo "📁 Repository root: $REPO_ROOT"

# 1. Generate schema bundle
echo "📊 Generating schema bundle..."
python scripts/build_schema_field_map.py

# 2. Generate browser caches for demo data
echo "🗂️  Generating browser caches..."
python scripts/build_year_browser_cache.py --input references/transformed/demo_by_year

# 3. Generate DQ caches for demo data
echo "📈 Generating DQ caches..."
python scripts/build_demo_dq_caches.py

# 4. Materialize individual release files for static hosting
echo "📄 Materializing individual release files..."
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
echo "📊 Total size:"
du -sh dist/
echo ""
echo "🧪 Test locally: cd app && npx serve dist -p 4173"