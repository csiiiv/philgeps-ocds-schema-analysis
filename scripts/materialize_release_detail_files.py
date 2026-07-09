#!/usr/bin/env python3
"""Materialize individual release JSON files for static hosting.

This script creates individual release files at public/data/release/{year}/{ocid}.json
so the webapp can fetch release details without a Node.js backend.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]
DEMO_BY_YEAR = ROOT / "references" / "transformed" / "demo_by_year"
OUTPUT_ROOT = ROOT / "app" / "public" / "data" / "release"


def materialize_year_releases(year_file: Path) -> int:
    """Extract individual releases from a year package."""
    
    with open(year_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    releases = data.get('releases', [])
    if not releases:
        return 0
    
    year = year_file.stem
    year_output_dir = OUTPUT_ROOT / year
    year_output_dir.mkdir(parents=True, exist_ok=True)
    
    materialized = 0
    for release in releases:
        ocid = release.get('ocid')
        if not ocid:
            continue
        
        # URL-encode the OCID for filename safety
        safe_ocid = quote(ocid, safe='')
        output_file = year_output_dir / f"{safe_ocid}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(release, f, indent=2, ensure_ascii=False)
        
        materialized += 1
    
    return materialized


def main():
    if not DEMO_BY_YEAR.exists():
        print(f"ERROR: Demo year directory not found: {DEMO_BY_YEAR}")
        return 1
    
    # Create output directory
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Find all demo year files
    year_files = sorted(DEMO_BY_YEAR.glob("*.json"))
    year_files = [f for f in year_files if f.stem.isdigit() and 1900 <= int(f.stem) <= 2100]
    
    if not year_files:
        print("ERROR: No demo year files found")
        return 1
    
    print(f"Found {len(year_files)} demo year files")
    print(f"Materializing individual release files...")
    
    total_releases = 0
    total_files = 0
    for year_file in year_files:
        year = year_file.stem
        print(f"  Processing {year}...", end=' ')
        
        try:
            count = materialize_year_releases(year_file)
            total_files += 1
            total_releases += count
            print(f"✅ ({count} releases)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Materialized {total_releases} releases from {total_files} years")
    print(f"Output directory: {OUTPUT_ROOT}")
    print(f"Total files created: {total_releases}")
    
    return 0


if __name__ == '__main__':
    sys.exit(main())