"""
04_export_hazard_data.py

Converts the hazard points GeoJSON into a lightweight JSON file
for the React Native mobile app and creates a small sample set
for quick testing.
"""

import json
import os
import sys
import geopandas as gpd
from pathlib import Path

# --- Config ---

INPUT_GEOJSON = "data/processed/oxford_uk_hazard_points.geojson"
OUTPUT_DIR = "data/processed"
OUTPUT_FILENAME = "oxford_uk_hazard_mobile.json"

COORD_DECIMALS = 6   # 6dp ~ 0.1m precision
SCORE_DECIMALS = 3

def load_hazard_data(path=INPUT_GEOJSON):
    """Load the GeoJSON from step 03."""
    if not os.path.exists(path):
        print(f"Input file not found: {path}")
        print("Run 03_generate_hazard_points.py first.")
        sys.exit(1)

    gdf = gpd.read_file(path)
    print(f"Loaded {len(gdf)} hazard points from {path}")
    return gdf


def transform_for_mobile(gdf):
    """Strip the GeoDataFrame down to just the fields the app needs."""
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
            "mergeType": str(row.get("merge_type", "minor_to_major")),
            "bearing": round(float(row["approach_bearing"]), 1),
            "road": str(row.get("road_name", "Unnamed")),
            "roadType": str(row.get("road_type", "unknown")),
            "majorClass": int(row.get("major_road_class", 0)),
            "minorClass": int(row.get("minor_road_class", 0)),
        })

    return records


def save_compact_json(records, output_path):
    """Save as compact JSON (no indentation) for smaller file size."""
    with open(output_path, 'w') as f:
        json.dump(records, f, separators=(',', ':'))

    size_bytes = os.path.getsize(output_path)
    size_kb = size_bytes / 1024
    print(f"Saved compact JSON: {output_path}")
    print(f"  File size: {size_kb:.1f} KB ({size_bytes:,} bytes)")
    return size_bytes


def generate_sample_subset(records, n=50, output_path=None):
    """Pick the top N highest-danger points as a small test dataset."""
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
        print(f"Saved sample ({n} points): {output_path}")

    return sample


def main():
    print("\n--- Hazard Data Export ---\n")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Load, transform, save
    gdf = load_hazard_data()

    print("\nTransforming for mobile...")
    records = transform_for_mobile(gdf)

    compact_path = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)
    compact_size = save_compact_json(records, compact_path)

    sample_path = os.path.join(OUTPUT_DIR,
                                OUTPUT_FILENAME.replace('.json', '_sample50.json'))
    generate_sample_subset(records, n=50, output_path=sample_path)

    print(f"\nDone. Output files:")
    print(f"  {compact_path}  (mobile)")
    print(f"  {sample_path}  (50-point test set)")
    print()


if __name__ == "__main__":
    main()
