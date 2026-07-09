#!/usr/bin/env python3
"""Build per-year DQ caches for demo data.

Unlike the full dataset DQ caches which use .dq.json sidecars,
this generates simplified DQ metrics directly from demo year packages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DEMO_BY_YEAR = ROOT / "references" / "transformed" / "demo_by_year"
DQ_CACHE_DIR = DEMO_BY_YEAR / "dq"


def generate_dq_cache(year_file: Path) -> dict:
    """Generate DQ cache with basic metrics from demo year package."""
    
    with open(year_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    releases = data.get('releases', [])
    
    # Calculate basic DQ metrics
    metrics = {
        'total_releases': len(releases),
        'releases_with_tender': 0,
        'releases_with_awards': 0,
        'releases_with_buyers': 0,
        'releases_with_suppliers': 0,
        'missing_fields': defaultdict(int),
        'warnings': [],
        'errors': []
    }
    
    for release in releases:
        if release.get('tender'):
            metrics['releases_with_tender'] += 1
            if not release.get('tender', {}).get('title'):
                metrics['missing_fields']['tender.title'] += 1
                metrics['warnings'].append(f"Release {release.get('ocid')}: missing tender title")
        
        if release.get('awards'):
            metrics['releases_with_awards'] += 1
        else:
            metrics['warnings'].append(f"Release {release.get('ocid')}: no awards (may be cancelled tender)")
        
        if release.get('parties'):
            suppliers = [p for p in release['parties'] if p.get('roles') and 'supplier' in p['roles']]
            if suppliers:
                metrics['releases_with_suppliers'] += 1
    
    # Convert defaultdict to regular dict for JSON serialization
    metrics['missing_fields'] = dict(metrics['missing_fields'])
    
    return {
        'year': year_file.stem,
        'metrics': metrics,
        'summary': {
            'total': metrics['total_releases'],
            'warnings': len(metrics['warnings']),
            'errors': len(metrics['errors']),
            'completeness': f"{(metrics['releases_with_tender'] / metrics['total_releases'] * 100):.1f}%" if metrics['total_releases'] > 0 else "N/A"
        }
    }


def main():
    if not DEMO_BY_YEAR.exists():
        print(f"ERROR: Demo year directory not found: {DEMO_BY_YEAR}")
        return 1
    
    # Create DQ cache directory
    DQ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all demo year files
    year_files = sorted(DEMO_BY_YEAR.glob("*.json"))
    year_files = [f for f in year_files if f.stem.isdigit() and 1900 <= int(f.stem) <= 2100]
    
    if not year_files:
        print("ERROR: No demo year files found")
        return 1
    
    print(f"Found {len(year_files)} demo year files")
    print(f"Generating DQ caches...")
    
    built = 0
    for year_file in year_files:
        year = year_file.stem
        print(f"  Processing {year}...", end=' ')
        
        try:
            dq_cache = generate_dq_cache(year_file)
            dq_file = DQ_CACHE_DIR / f"{year}.json"
            with open(dq_file, 'w', encoding='utf-8') as f:
                json.dump(dq_cache, f, indent=2, ensure_ascii=False)
            
            kb = dq_file.stat().st_size / 1024
            print(f"✅ ({dq_cache['summary']['total']} releases, {kb:.1f} KB)")
            built += 1
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Built {built} DQ cache files")
    print(f"Output directory: {DQ_CACHE_DIR}")
    return 0 if built > 0 else 1


if __name__ == '__main__':
    sys.exit(main())