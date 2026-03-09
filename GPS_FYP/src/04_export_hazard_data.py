"""
Hazard Data Export for Mobile App
Week 9 - Data Export & Format

This script takes the full hazard points GeoJSON and produces an
optimised, lightweight JSON file ready for the React Native mobile app.

Optimisations applied:
  - Only essential fields kept (lat, lon, score, type, bearing)
  - Coordinates rounded to 6 decimal places (~0.1 m precision)
  - Danger scores rounded to 3 decimal places
  - File is compact JSON (no pretty-print) for smaller size
  - Optional: split into regional tiles for lazy-loading

Output format (array of objects):
    [
        {
            "id": 1,
            "lat": 51.752034,
            "lon": -1.257712,
            "jLat": 51.751400,
            "jLon": -1.257200,
            "score": 0.723,
            "type": "T-junction",
            "bearing": 145.2,
            "road": "Woodstock Road",
            "roadType": "secondary"
        },
        ...
    ]

Usage:
    python src/04_export_hazard_data.py
"""

import json
import os
import sys
import geopandas as gpd
import pandas as pd
from pathlib import Path

# ──────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────

INPUT_GEOJSON = "data/processed/oxford_uk_hazard_points.geojson"
OUTPUT_DIR = "data/processed"
OUTPUT_FILENAME = "oxford_uk_hazard_mobile.json"

# Coordinate precision (6 dp ≈ 0.1 m)
COORD_DECIMALS = 6
SCORE_DECIMALS = 3


# ──────────────────────────────────────────────────────────
# Export functions
# ──────────────────────────────────────────────────────────

def load_hazard_data(path=INPUT_GEOJSON):
    """Load hazard GeoJSON produced by 03_generate_hazard_points.py."""
    if not os.path.exists(path):
        print(f"❌ Input file not found: {path}")
        print("   Run 03_generate_hazard_points.py first.")
        sys.exit(1)

    gdf = gpd.read_file(path)
    print(f"📂 Loaded {len(gdf)} hazard points from {path}")
    return gdf


def transform_for_mobile(gdf):
    """
    Convert the full GeoDataFrame to a lightweight list of dicts
    suitable for the mobile app.

    Fields kept:
        id          - sequential integer (compact)
        lat / lon   - warning point position (where the driver gets warned)
        jLat / jLon - actual junction position (for map marker)
        score       - danger score 0-1
        type        - junction type label
        bearing     - approach bearing the warning applies to
        road        - road name
        roadType    - OSM highway tag
    """
    records = []
    for idx, row in gdf.iterrows():
        records.append({
            "id": int(idx + 1),
            "lat": round(float(row["warning_lat"]), COORD_DECIMALS),
            "lon": round(float(row["warning_lon"]), COORD_DECIMALS),
            "jLat": round(float(row["junction_lat"]), COORD_DECIMALS),
            "jLon": round(float(row["junction_lon"]), COORD_DECIMALS),
            "score": round(float(row["danger_score"]), SCORE_DECIMALS),
            "type": str(row["junction_type"]),
            "bearing": round(float(row["approach_bearing"]), 1),
            "road": str(row.get("road_name", "Unnamed")),
            "roadType": str(row.get("road_type", "unknown")),
        })

    return records


def save_compact_json(records, output_path):
    """
    Save as compact JSON (no indentation, minimal whitespace).
    This reduces file size significantly for mobile delivery.
    """
    with open(output_path, 'w') as f:
        json.dump(records, f, separators=(',', ':'))

    size_bytes = os.path.getsize(output_path)
    size_kb = size_bytes / 1024
    print(f"💾 Saved compact JSON: {output_path}")
    print(f"   File size: {size_kb:.1f} KB ({size_bytes:,} bytes)")
    return size_bytes


def save_pretty_json(records, output_path):
    """Save pretty-printed version for debugging / inspection."""
    with open(output_path, 'w') as f:
        json.dump(records, f, indent=2)

    size_bytes = os.path.getsize(output_path)
    size_kb = size_bytes / 1024
    print(f"💾 Saved pretty JSON: {output_path}")
    print(f"   File size: {size_kb:.1f} KB ({size_bytes:,} bytes)")
    return size_bytes


def print_export_summary(records, compact_size, pretty_size):
    """Print a summary of the exported data."""
    print(f"\n{'='*60}")
    print("EXPORT SUMMARY")
    print(f"{'='*60}")
    print(f"Total hazard points:  {len(records)}")

    if records:
        scores = [r['score'] for r in records]
        print(f"Score range:          {min(scores):.3f} – {max(scores):.3f}")
        print(f"Mean score:           {sum(scores)/len(scores):.3f}")

        # Type breakdown
        from collections import Counter
        types = Counter(r['type'] for r in records)
        print(f"\nJunction types:")
        for t, count in types.most_common():
            print(f"  {t:15s} {count:5d}")

    print(f"\nFile sizes:")
    print(f"  Compact (mobile):   {compact_size/1024:.1f} KB")
    print(f"  Pretty  (debug):    {pretty_size/1024:.1f} KB")
    print(f"  Savings:            {(1 - compact_size/pretty_size)*100:.0f}% smaller")

    # Estimate for larger regions
    per_point = compact_size / max(len(records), 1)
    print(f"\nEstimated sizes (compact):")
    for n in [1000, 5000, 10000, 50000]:
        est = per_point * n / 1024
        print(f"  {n:>6,} points → {est:>8.1f} KB ({est/1024:.2f} MB)")


def generate_sample_subset(records, n=50, output_path=None):
    """
    Generate a small sample dataset for quick mobile testing.
    Picks the N highest-danger points.
    """
    if not records:
        return []

    sorted_records = sorted(records, key=lambda r: r['score'], reverse=True)
    sample = sorted_records[:n]

    # Re-number IDs
    for i, r in enumerate(sample):
        r['id'] = i + 1

    if output_path:
        with open(output_path, 'w') as f:
            json.dump(sample, f, indent=2)
        print(f"💾 Saved sample ({n} points): {output_path}")

    return sample


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  Hazard Data Export – Week 9                             ║
    ║  Optimised JSON for Mobile App                           ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Load full hazard GeoJSON
    gdf = load_hazard_data()

    # 2. Transform to mobile-friendly format
    print("\n🔄 Transforming data for mobile...")
    records = transform_for_mobile(gdf)

    # 3. Save compact JSON (for production / mobile delivery)
    compact_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    compact_size = save_compact_json(records, compact_path)

    # 4. Save pretty JSON (for debugging)
    pretty_path = os.path.join(OUTPUT_DIR,
                                OUTPUT_FILENAME.replace('.json', '_pretty.json'))
    pretty_size = save_pretty_json(records, pretty_path)

    # 5. Generate small sample for quick mobile testing
    sample_path = os.path.join(OUTPUT_DIR,
                                OUTPUT_FILENAME.replace('.json', '_sample50.json'))
    generate_sample_subset(records, n=50, output_path=sample_path)

    # 6. Summary
    print_export_summary(records, compact_size, pretty_size)

    print(f"\n{'='*60}")
    print("✅ DATA EXPORT COMPLETE!")
    print(f"{'='*60}")
    print(f"\nWeek 9 Deliverable achieved:")
    print(f"  ✅ Efficient mobile-ready JSON format designed")
    print(f"  ✅ Data export pipeline implemented")
    print(f"  ✅ Test dataset generated for Oxford, UK")
    print(f"  ✅ File size optimised (compact JSON)")
    print(f"  ✅ Sample subset for quick testing")
    print(f"\nOutput files:")
    print(f"  📱 {compact_path}  (load this in the app)")
    print(f"  🔍 {pretty_path}  (human-readable)")
    print(f"  🧪 {sample_path}  (50-point test set)")
    print()


if __name__ == "__main__":
    main()
