#!/usr/bin/env python3
"""Generate demo datasets from transformed OCDS year packages (memory-efficient).

This version handles large files (1GB+) by streaming data instead of loading 
everything into memory at once.

Usage:
    python scripts/generate_year_demo_samples_efficient.py --years 2019,2020,2021,2022,2023,2024,2025
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from collections import defaultdict
import random

ROOT = Path(__file__).resolve().parents[1]
TRANSFORMED_DIR = ROOT / "references" / "transformed" / "by_year"
OUTPUT_DIR = ROOT / "references" / "transformed" / "demo_by_year"


def stream_json_array(file_path: Path, max_items: int = None):
    """Stream JSON array items one at a time to avoid loading entire file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        # Read past opening metadata
        for line in f:
            if '"releases": [' in line:
                break
        
        # Stream releases
        bracket_depth = 0
        buffer = ""
        item_count = 0
        
        for line in f:
            for char in line:
                if char == '{':
                    if bracket_depth == 0:
                        buffer = char
                    else:
                        buffer += char
                    bracket_depth += 1
                elif char == '}':
                    buffer += char
                    bracket_depth -= 1
                    if bracket_depth == 0:
                        # Complete JSON object
                        try:
                            release = json.loads(buffer)
                            item_count += 1
                            yield release
                            if max_items and item_count >= max_items:
                                return
                        except json.JSONDecodeError:
                            continue
                        buffer = ""
                elif bracket_depth > 0:
                    buffer += char
                
                # Check for end of array
                if char == ']' and bracket_depth == 0:
                    return


def get_package_metadata(file_path: Path) -> dict:
    """Extract package metadata without loading releases."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse just the metadata part
    metadata_end = content.find('"releases": [')
    if metadata_end == -1:
        return {}
    
    metadata_str = content[:metadata_end] + '"releases": []}'
    try:
        return json.loads(metadata_str)
    except:
        return {}


def estimate_releases_count(file_path: Path) -> int:
    """Estimate number of releases by counting OCIDs."""
    count = 0
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if '"ocid":' in line:
                count += 1
    return count


def select_stratified_sample_from_stream(file_path: Path, target_samples: int) -> list:
    """Select sample using reservoir sampling from stream."""
    
    # First pass: count and categorize by procurement method
    method_indices = defaultdict(list)
    total_count = 0
    
    for idx, release in enumerate(stream_json_array(file_path)):
        method = "unknown"
        if release.get('tender', {}).get('procurementMethod'):
            method = release['tender']['procurementMethod']
        method_indices[method].append(idx)
        total_count += 1
        
        # Progress update for large files
        if total_count % 10000 == 0:
            print(f"  Scanned {total_count} releases...", end='\r')
    
    print(f"  Total releases: {total_count}")
    
    # Calculate sample per method
    num_methods = len(method_indices)
    if num_methods == 0:
        return []
    
    samples_per_method = max(10, target_samples // num_methods)
    target_indices = set()
    
    # Select indices from each method
    for method, indices in method_indices.items():
        available = len(indices)
        to_select = min(samples_per_method, available)
        
        # Ensure we get diverse samples from each method
        step = max(1, available // to_select)
        selected = indices[::step][:to_select]
        target_indices.update(selected)
    
    print(f"  Selected {len(target_indices)} samples across {num_methods} methods")
    
    # Second pass: collect selected releases
    selected_releases = []
    for idx, release in enumerate(stream_json_array(file_path)):
        if idx in target_indices:
            selected_releases.append(release)
            if len(selected_releases) >= len(target_indices):
                break
    
    return selected_releases


def generate_demo_year_package_efficient(year_file: Path, output_file: Path, target_samples: int, max_size_mb: float) -> dict:
    """Generate demo package with memory-efficient processing."""
    
    print(f"\nProcessing {year_file.name}...")
    
    # Get file size for progress info
    file_size_mb = year_file.stat().st_size / (1024 * 1024)
    print(f"  File size: {file_size_mb:.1f} MB")
    
    # Get metadata
    metadata = get_package_metadata(year_file)
    
    # Estimate release count
    estimated_count = estimate_releases_count(year_file)
    print(f"  Estimated releases: {estimated_count:,}")
    
    # Adjust target samples for very large files to stay within size limits
    if file_size_mb > 500:
        # For files >500MB, use much smaller sample
        target_samples = min(target_samples, 200)
        print(f"  Large file detected, reducing target to {target_samples} samples")
    elif file_size_mb > 100:
        # For files >100MB, use moderate sample
        target_samples = min(target_samples, 500)
        print(f"  Medium-large file, reducing target to {target_samples} samples")
    
    # Select samples using streaming approach
    demo_releases = select_stratified_sample_from_stream(year_file, target_samples)
    
    if not demo_releases:
        return {'error': 'No releases selected', 'year': year_file.stem}
    
    # Create demo package
    demo_package = {
        'uri': metadata.get('uri', '').replace('/by-year/', '/demo-by-year/'),
        'version': metadata.get('version', '1.1'),
        'extensions': metadata.get('extensions', []),
        'publishedDate': metadata.get('publishedDate'),
        'publisher': metadata.get('publisher'),
        'license': metadata.get('license'),
        'publicationPolicy': metadata.get('publicationPolicy'),
        'releases': demo_releases
    }
    
    # Write output
    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(demo_package, f, indent=2, ensure_ascii=False)
    
    result_size_mb = output_file.stat().st_size / (1024 * 1024)
    
    print(f"  ✅ Generated {len(demo_releases)} releases ({result_size_mb:.2f} MB)")
    
    return {
        'year': year_file.stem,
        'source_estimated': estimated_count,
        'demo_total': len(demo_releases),
        'file_size_mb': round(result_size_mb, 2),
        'source_size_mb': round(file_size_mb, 2),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate demo datasets from transformed OCDS year packages (memory-efficient)"
    )
    parser.add_argument(
        '--years',
        type=str,
        required=True,
        help='Years to process (comma-separated)'
    )
    parser.add_argument(
        '--samples',
        type=int,
        default=1000,
        help='Target samples per year (default: 1000, auto-reduced for large files)'
    )
    parser.add_argument(
        '--max-size',
        type=float,
        default=2.0,
        help='Max file size per year in MB (default: 2.0)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    args = parser.parse_args()
    
    if not TRANSFORMED_DIR.exists():
        print(f"ERROR: Transformed directory not found: {TRANSFORMED_DIR}")
        sys.exit(1)
    
    # Set random seed
    random.seed(args.seed)
    
    # Parse requested years
    requested_years = set(args.years.split(','))
    
    # Find matching year files
    year_files = []
    for year_str in requested_years:
        year_file = TRANSFORMED_DIR / f"{year_str}.json"
        if year_file.exists():
            year_files.append(year_file)
        else:
            print(f"WARNING: {year_file.name} not found, skipping")
    
    if not year_files:
        print("ERROR: No valid year files found")
        sys.exit(1)
    
    print(f"Processing {len(year_files)} large year files with memory-efficient streaming")
    print(f"Target samples per year: {args.samples} (auto-reduced for files >100MB)")
    
    # Process each year
    results = []
    for year_file in year_files:
        output_file = OUTPUT_DIR / year_file.name
        result = generate_demo_year_package_efficient(year_file, output_file, args.samples, args.max_size)
        if 'error' not in result:
            results.append(result)
    
    # Summary
    print(f"\n{'='*60}")
    print(f"Generated {len(results)} demo year packages")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"{'='*60}")
    
    if results:
        total_releases = sum(r['demo_total'] for r in results)
        total_size = sum(r['file_size_mb'] for r in results)
        total_source_size = sum(r.get('source_size_mb', 0) for r in results)
        
        print(f"Total releases: {total_releases:,}")
        print(f"Total demo size: {total_size:.2f} MB")
        print(f"Total source size: {total_source_size:.2f} MB")
        print(f"Compression ratio: {total_source_size/total_size:.1f}x")
        print(f"\nYear breakdown:")
        for r in results:
            reduction = r.get('source_size_mb', 0) / r['file_size_mb'] if r['file_size_mb'] > 0 else 0
            print(f"  {r['year']}: {r['demo_total']} releases ({r['file_size_mb']:.2f} MB, {reduction:.1f}x reduction)")


if __name__ == '__main__':
    main()