#!/usr/bin/env python3
"""Generate webapp cache files from demo year packages.

The webapp expects browser and DQ cache files in subdirectories.
This script generates them from the demo year packages.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
DEMO_YEAR_DIR = ROOT / "references" / "transformed" / "demo_by_year"
BROWSER_CACHE_DIR = DEMO_YEAR_DIR / "browser"
DQ_CACHE_DIR = DEMO_YEAR_DIR / "dq"


def generate_browser_cache(year_file: Path) -> dict:
    """Generate browser cache with lightweight release summaries."""
    
    with open(year_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    releases = data.get('releases', [])
    browser_cache = {
        'releases': {},
        'metadata': {
            'year': year_file.stem,
            'total_releases': len(releases),
            'generated_at': str(Path(__file__).stat().st_mtime)
        }
    }
    
    for release in releases:
        ocid = release.get('ocid')
        if not ocid:
            continue
        
        # Create lightweight summary for browser
        browser_cache['releases'][ocid] = {
            'ocid': ocid,
            'id': release.get('id'),
            'date': release.get('date', ''),
            'tag': release.get('tag', []),
            'initiationType': release.get('initiationType'),
            
            # Tender summary
            'tender': {
                'title': release.get('tender', {}).get('title'),
                'status': release.get('tender', {}).get('status'),
                'procurementMethod': release.get('tender', {}).get('procurementMethod'),
                'procuringEntity': release.get('tender', {}).get('procuringEntity', {}).get('name'),
                'value': release.get('tender', {}).get('value', {}),
            } if release.get('tender') else None,
            
            # Awards count
            'awards_count': len(release.get('awards', [])),
            'has_awards': bool(release.get('awards')),
        }
    
    return browser_cache


def generate_dq_cache(year_file: Path) -> dict:
    """Generate data quality cache with minimal DQ metrics."""
    
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
    
    return {
        'year': year_file.stem,
        'metrics': dict(metrics),
        'summary': {
            'total': metrics['total_releases'],
            'warnings': len(metrics['warnings']),
            'errors': len(metrics['errors']),
            'completeness': f"{(metrics['releases_with_tender'] / metrics['total_releases'] * 100):.1f}%" if metrics['total_releases'] > 0 else "N/A"
        }
    }


def main():
    if not DEMO_YEAR_DIR.exists():
        print(f"ERROR: Demo year directory not found: {DEMO_YEAR_DIR}")
        sys.exit(1)
    
    # Create cache directories
    BROWSER_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DQ_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    
    # Find all demo year files
    year_files = sorted(DEMO_YEAR_DIR.glob("*.json"))
    year_files = [f for f in year_files if f.stem.isdigit() and 1900 <= int(f.stem) <= 2100]
    
    if not year_files:
        print("ERROR: No demo year files found")
        sys.exit(1)
    
    print(f"Found {len(year_files)} demo year files")
    print(f"Generating webapp caches...")
    
    # Process each year
    for year_file in year_files:
        year = year_file.stem
        print(f"  Processing {year}...", end=' ')
        
        try:
            # Generate browser cache
            browser_cache = generate_browser_cache(year_file)
            browser_file = BROWSER_CACHE_DIR / f"{year}.json"
            with open(browser_file, 'w', encoding='utf-8') as f:
                json.dump(browser_cache, f, indent=2, ensure_ascii=False)
            
            # Generate DQ cache
            dq_cache = generate_dq_cache(year_file)
            dq_file = DQ_CACHE_DIR / f"{year}.json"
            with open(dq_file, 'w', encoding='utf-8') as f:
                json.dump(dq_cache, f, indent=2, ensure_ascii=False)
            
            print(f"✅ ({browser_cache['metadata']['total_releases']} releases)")
            
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print(f"\n✅ Generated webapp caches:")
    print(f"   Browser cache: {BROWSER_CACHE_DIR}")
    print(f"   DQ cache: {DQ_CACHE_DIR}")
    print(f"\n📁 Cache files created:")
    print(f"   Browser: {len(list(BROWSER_CACHE_DIR.glob('*.json')))} files")
    print(f"   DQ: {len(list(DQ_CACHE_DIR.glob('*.json')))} files")


if __name__ == '__main__':
    main()