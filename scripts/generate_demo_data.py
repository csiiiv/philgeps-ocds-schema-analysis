#!/usr/bin/env python3
"""Generate demo data from large PhilGEPS CSV exports for inclusion in git.

This script creates a representative sample from the full dataset that:
- Is small enough to include in git (~100-500 rows, <1MB)
- Contains diverse procurement modes, organizations, and data patterns
- Maintains the same schema as the full dataset
- Can be used for development, testing, and demonstration

Usage:
    python scripts/generate_demo_data.py raw/large_file.csv raw_demo/demo.csv [--rows N]
    
    Default: 200 rows (adjustable for diversity while staying small)
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from collections import defaultdict
import random

ROOT = Path(__file__).resolve().parents[1]


def analyze_diversity(rows: list[dict]) -> dict:
    """Analyze diversity metrics for a set of rows."""
    metrics = {
        'procurement_modes': set(),
        'organization_types': set(), 
        'regions': set(),
        'notice_statuses': set(),
        'award_statuses': set(),
        'has_awards': 0,
        'total': len(rows)
    }
    
    for row in rows:
        if row.get('Procurement Mode'):
            metrics['procurement_modes'].add(row['Procurement Mode'])
        if row.get('PE Organization Type'):
            metrics['organization_types'].add(row['PE Organization Type'])
        if row.get('Region'):
            metrics['regions'].add(row['Region'])
        if row.get('Bid Notice Status'):
            metrics['notice_statuses'].add(row['Bid Notice Status'])
        if row.get('Award Notice Status'):
            metrics['award_statuses'].add(row['Award Notice Status'])
        if row.get('Award Reference No.') and row['Award Reference No.'].strip():
            metrics['has_awards'] += 1
    
    return metrics


def select_diverse_sample(all_rows: list[dict], target_size: int) -> list[dict]:
    """Select a diverse sample using stratified sampling."""
    
    # Group by procurement mode for stratification
    by_mode = defaultdict(list)
    for row in all_rows:
        mode = row.get('Procurement Mode', 'Unknown')
        by_mode[mode].append(row)
    
    sample = []
    remaining = target_size
    
    # First, ensure we get at least some from each mode (if available)
    modes_to_sample = list(by_mode.keys())
    per_mode = max(1, target_size // len(modes_to_sample)) if modes_to_sample else target_size
    
    for mode, mode_rows in by_mode.items():
        if len(mode_rows) <= per_mode:
            # Take all from this mode if it's small
            sample.extend(mode_rows)
            remaining -= len(mode_rows)
        else:
            # Sample proportionally from this mode
            sample.extend(random.sample(mode_rows, per_mode))
            remaining -= per_mode
    
    # If we still need more rows, fill randomly
    if remaining > 0 and remaining < len(all_rows):
        already_sampled = set(id(row) for row in sample)
        remaining_rows = [row for row in all_rows if id(row) not in already_sampled]
        sample.extend(random.sample(remaining_rows, min(remaining, len(remaining_rows))))
    
    # Sort by original order for consistency
    return sample


def generate_demo_data(input_file: Path, output_file: Path, target_rows: int = 200) -> None:
    """Generate demo dataset from full CSV export."""
    
    print(f"Reading input file: {input_file}")
    print(f"Target sample size: {target_rows} rows")
    
    # Read all rows
    all_rows = []
    with open(input_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        headers = reader.fieldnames
        for row in reader:
            all_rows.append(row)
    
    if not all_rows:
        print("ERROR: No data found in input file")
        sys.exit(1)
    
    print(f"Total rows in source: {len(all_rows)}")
    
    # Analyze source diversity
    source_diversity = analyze_diversity(all_rows)
    print(f"\nSource data diversity:")
    print(f"  Procurement modes: {len(source_diversity['procurement_modes'])}")
    print(f"  Organization types: {len(source_diversity['organization_types'])}")
    print(f"  Regions: {len(source_diversity['regions'])}")
    print(f"  Notice statuses: {len(source_diversity['notice_statuses'])}")
    print(f"  Award statuses: {len(source_diversity['award_statuses'])}")
    print(f"  Rows with awards: {source_diversity['has_awards']}/{source_diversity['total']}")
    
    # Select diverse sample
    sample_rows = select_diverse_sample(all_rows, target_rows)
    
    # Analyze sample diversity
    sample_diversity = analyze_diversity(sample_rows)
    print(f"\nSample data diversity:")
    print(f"  Procurement modes: {len(sample_diversity['procurement_modes'])}")
    print(f"  Organization types: {len(sample_diversity['organization_types'])}")
    print(f"  Regions: {len(sample_diversity['regions'])}")
    print(f"  Notice statuses: {len(sample_diversity['notice_statuses'])}")
    print(f"  Award statuses: {len(sample_diversity['award_statuses'])}")
    print(f"  Rows with awards: {sample_diversity['has_awards']}/{sample_diversity['total']}")
    
    # Ensure output directory exists
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Write sample to output
    print(f"\nWriting demo data to: {output_file}")
    with open(output_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sample_rows)
    
    # Check file size
    file_size = output_file.stat().st_size
    size_mb = file_size / (1024 * 1024)
    
    print(f"✅ Demo data created successfully!")
    print(f"   Rows: {len(sample_rows)}")
    print(f"   Size: {size_mb:.2f} MB")
    print(f"   Ready to commit to git!")


def main():
    parser = argparse.ArgumentParser(
        description="Generate demo data from large PhilGEPS CSV exports"
    )
    parser.add_argument(
        'input',
        type=Path,
        help='Input CSV file (full dataset)'
    )
    parser.add_argument(
        'output',
        type=Path, 
        help='Output CSV file (demo dataset)'
    )
    parser.add_argument(
        '--rows',
        type=int,
        default=200,
        help='Target number of rows (default: 200)'
    )
    parser.add_argument(
        '--seed',
        type=int,
        default=42,
        help='Random seed for reproducibility (default: 42)'
    )
    
    args = parser.parse_args()
    
    if not args.input.exists():
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)
    
    # Set random seed for reproducibility
    random.seed(args.seed)
    
    generate_demo_data(args.input, args.output, args.rows)


if __name__ == '__main__':
    main()