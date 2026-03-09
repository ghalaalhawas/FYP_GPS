"""
Hazard Point Generation Script
Week 7 - Danger Point Algorithm

This script generates displaced hazard warning points from junction data.
For each dangerous junction, it:
  1. Calculates an enhanced danger score using multiple factors
  2. Displaces a warning point 50-100m up each approaching secondary road
  3. Stores approach bearing so the app only warns from the correct direction

The displaced points are where a driver would actually receive a warning,
giving them time to react before reaching the junction.

Usage:
    python src/03_generate_hazard_points.py

Requires:
    - OSM data already downloaded (run 01_download_osm_data.py first)
    - osm_parser.py in same directory
"""

import sys
import os
import math
import numpy as np
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from pathlib import Path

# Add src directory to path so we can import osm_parser
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from osm_parser import OSMParser


# ──────────────────────────────────────────────────────────
# Constants
# ──────────────────────────────────────────────────────────

# Warning point displacement distance (metres)
DISPLACEMENT_DISTANCE_M = 75  # 50-100m as per spec, 75 is a good middle ground

# Minimum danger score to generate a hazard point
DANGER_THRESHOLD = 0.35

# Earth radius in metres (for haversine / bearing calculations)
EARTH_RADIUS_M = 6_371_000


# ──────────────────────────────────────────────────────────
# Geometry helpers
# ──────────────────────────────────────────────────────────

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate great-circle distance between two points in metres.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing_between(lat1, lon1, lat2, lon2):
    """
    Calculate initial bearing (degrees 0-360) from point 1 to point 2.
    """
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def displace_point(lat, lon, bearing_deg, distance_m):
    """
    Move a point along a given bearing by a given distance.

    Args:
        lat, lon: Starting coordinates (degrees)
        bearing_deg: Bearing in degrees (0 = north, 90 = east)
        distance_m: Distance to move in metres

    Returns:
        (new_lat, new_lon) in degrees
    """
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    bearing_r = math.radians(bearing_deg)
    d = distance_m / EARTH_RADIUS_M

    new_lat = math.asin(
        math.sin(lat_r) * math.cos(d) +
        math.cos(lat_r) * math.sin(d) * math.cos(bearing_r)
    )
    new_lon = lon_r + math.atan2(
        math.sin(bearing_r) * math.sin(d) * math.cos(lat_r),
        math.cos(d) - math.sin(lat_r) * math.sin(new_lat)
    )
    return math.degrees(new_lat), math.degrees(new_lon)


def angle_between_bearings(b1, b2):
    """Return the acute angle between two bearings (0-180)."""
    diff = abs(b1 - b2) % 360
    return min(diff, 360 - diff)


# ──────────────────────────────────────────────────────────
# Danger scoring
# ──────────────────────────────────────────────────────────

def calculate_enhanced_danger_score(junction_info, parser):
    """
    Calculate a danger score (0-1) based on multiple factors:
        1. Junction complexity      (more arms → harder to navigate)
        2. Road classification      (mismatch hints at priority confusion)
        3. Speed differential       (big speed gap → higher risk)
        4. Approach angle sharpness (tight angles reduce visibility)

    Args:
        junction_info: dict returned by parser.get_junction_info()
        parser: OSMParser instance (for road classification helper)

    Returns:
        float: danger score 0-1
    """
    scores = {}

    # --- 1. Junction complexity (0-1) ---
    street_count = junction_info['street_count']
    if street_count == 3:
        scores['complexity'] = 0.5      # T-junction
    elif street_count == 4:
        scores['complexity'] = 0.4      # Standard crossroads
    elif street_count >= 5:
        scores['complexity'] = 0.7      # Complex junction
    else:
        scores['complexity'] = 0.2

    # --- 2. Road classification mismatch (0-1) ---
    road_classes = []
    for edge in junction_info['edges']:
        road_classes.append(parser.get_road_classification(edge['highway']))

    if len(road_classes) >= 2:
        class_diff = max(road_classes) - min(road_classes)
        # Normalise: diff of 8+ maps to 1.0
        scores['class_mismatch'] = min(class_diff / 8.0, 1.0)
    else:
        scores['class_mismatch'] = 0.0

    # --- 3. Speed differential (0-1) ---
    speed_diff = junction_info.get('speed_differential', 0)
    # 40 mph difference maps to 1.0
    scores['speed_diff'] = min(speed_diff / 40.0, 1.0)

    # --- 4. Approach angle sharpness (0-1) ---
    # Compute pairwise approach bearings; tight angles are more dangerous
    if len(junction_info['edges']) >= 2:
        jlat, jlon = junction_info['location']
        bearings = []
        for edge in junction_info['edges']:
            other_id = edge['to'] if edge['from'] == junction_info['id'] else edge['from']
            try:
                other_node = parser.nodes.loc[other_id]
                b = bearing_between(jlat, jlon, other_node.geometry.y, other_node.geometry.x)
                bearings.append(b)
            except KeyError:
                continue

        if len(bearings) >= 2:
            min_angle = 180
            for i in range(len(bearings)):
                for j in range(i + 1, len(bearings)):
                    a = angle_between_bearings(bearings[i], bearings[j])
                    if a < min_angle:
                        min_angle = a
            # Angles < 45° are very tight and dangerous
            scores['angle'] = max(0, 1.0 - min_angle / 90.0)
        else:
            scores['angle'] = 0.0
    else:
        scores['angle'] = 0.0

    # --- Weighted combination ---
    weights = {
        'complexity': 0.20,
        'class_mismatch': 0.30,
        'speed_diff': 0.30,
        'angle': 0.20,
    }

    total = sum(scores[k] * weights[k] for k in weights)

    # Clamp 0-1
    return round(min(max(total, 0.0), 1.0), 4)


# ──────────────────────────────────────────────────────────
# Hazard point generation
# ──────────────────────────────────────────────────────────

def identify_secondary_roads(junction_info, parser):
    """
    For a given junction, identify the *secondary* (lower-class) roads.
    The warning point is placed on these roads because a driver coming
    from a minor road onto a major road needs the most warning.

    Returns:
        list of dicts with keys: edge, bearing_toward_junction, road_class
    """
    edges = junction_info['edges']
    if not edges:
        return []

    # Classify each edge
    classified = []
    for edge in edges:
        rc = parser.get_road_classification(edge['highway'])
        classified.append({'edge': edge, 'road_class': rc})

    # Find the maximum (most major) road class at this junction
    max_class = max(c['road_class'] for c in classified)

    # Secondary roads are those strictly below the maximum,
    # or ALL roads if they are all the same class (roundabout / equal junction)
    secondary = [c for c in classified if c['road_class'] < max_class]
    if not secondary:
        # All roads are equal class - pick all of them
        secondary = classified

    # Calculate bearing from each secondary road toward the junction
    jlat, jlon = junction_info['location']
    result = []
    for item in secondary:
        edge = item['edge']
        other_id = edge['to'] if edge['from'] == junction_info['id'] else edge['from']
        try:
            other_node = parser.nodes.loc[other_id]
            olat, olon = other_node.geometry.y, other_node.geometry.x
            # Bearing FROM the other node TOWARD the junction
            approach_bearing = bearing_between(olat, olon, jlat, jlon)
            result.append({
                'edge': edge,
                'road_class': item['road_class'],
                'other_lat': olat,
                'other_lon': olon,
                'approach_bearing': approach_bearing,
            })
        except KeyError:
            continue

    return result


def generate_hazard_points(parser, danger_threshold=DANGER_THRESHOLD,
                           displacement_m=DISPLACEMENT_DISTANCE_M):
    """
    Main function: analyse every junction in the network and generate
    displaced hazard warning points.

    Args:
        parser: OSMParser instance with network loaded
        danger_threshold: Minimum score to create a hazard point
        displacement_m: How far to push the warning point up the road (metres)

    Returns:
        GeoDataFrame of hazard points
    """
    junctions = parser.get_junctions(min_streets=3)

    print(f"\n{'='*60}")
    print(f"GENERATING HAZARD POINTS")
    print(f"Danger threshold: {danger_threshold}")
    print(f"Displacement: {displacement_m} m")
    print(f"{'='*60}\n")

    hazard_records = []
    skipped = 0
    errors = 0

    for idx, junction_id in enumerate(junctions.index):
        if idx % 200 == 0:
            print(f"  Processing junction {idx + 1}/{len(junctions)}...")

        try:
            info = parser.get_junction_info(junction_id)
        except Exception:
            errors += 1
            continue

        # Calculate enhanced danger score
        danger_score = calculate_enhanced_danger_score(info, parser)

        if danger_score < danger_threshold:
            skipped += 1
            continue

        # Identify secondary roads for warning placement
        secondary_roads = identify_secondary_roads(info, parser)

        for road in secondary_roads:
            # Bearing FROM junction AWAY along secondary road (opposite of approach)
            away_bearing = (road['approach_bearing'] + 180) % 360

            # Displace point up the secondary road
            jlat, jlon = info['location']
            wlat, wlon = displace_point(jlat, jlon, away_bearing, displacement_m)

            # Junction type label
            sc = info['street_count']
            if sc == 3:
                jtype = "T-junction"
            elif sc == 4:
                jtype = "Crossroads"
            else:
                jtype = f"{sc}-way"

            hazard_records.append({
                'junction_id': junction_id,
                'junction_lat': jlat,
                'junction_lon': jlon,
                'warning_lat': wlat,
                'warning_lon': wlon,
                'danger_score': danger_score,
                'junction_type': jtype,
                'street_count': sc,
                'approach_bearing': round(road['approach_bearing'], 1),
                'road_name': road['edge'].get('name', 'Unnamed'),
                'road_type': road['edge'].get('highway', 'unknown'),
                'speed_differential': info.get('speed_differential', 0),
                'geometry': Point(wlon, wlat),   # GeoJSON is (lon, lat)
            })

    print(f"\n  ✅ Generated {len(hazard_records)} hazard warning points")
    print(f"  ⏩ Skipped {skipped} junctions below threshold")
    if errors:
        print(f"  ⚠️  {errors} junctions had errors (missing data)")

    if not hazard_records:
        print("  ⚠️  No hazard points generated! Try lowering the threshold.")
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(hazard_records, crs="EPSG:4326")
    return gdf


# ──────────────────────────────────────────────────────────
# Visualisation
# ──────────────────────────────────────────────────────────

def visualize_hazard_points(parser, hazard_gdf, place_name="Oxford"):
    """
    Create a map showing junction locations and their displaced warning points.
    """
    if hazard_gdf.empty:
        print("  ⚠️  No hazard points to visualise.")
        return

    os.makedirs("data/visualizations", exist_ok=True)

    fig, ax = plt.subplots(figsize=(14, 14))

    # Plot road network edges as background
    parser.edges.plot(ax=ax, color='#CCCCCC', linewidth=0.3)

    # Plot junction centres (small grey dots)
    junction_points = hazard_gdf.drop_duplicates(subset='junction_id')
    junction_geom = gpd.GeoDataFrame(
        junction_points,
        geometry=[Point(r.junction_lon, r.junction_lat)
                  for _, r in junction_points.iterrows()],
        crs="EPSG:4326"
    )
    junction_geom.plot(ax=ax, color='grey', markersize=8, alpha=0.4, zorder=2)

    # Plot hazard warning points coloured by danger score
    hazard_gdf.plot(
        ax=ax,
        column='danger_score',
        cmap='YlOrRd',
        markersize=18,
        alpha=0.8,
        legend=True,
        legend_kwds={'label': 'Danger Score', 'shrink': 0.5},
        zorder=3,
    )

    ax.set_title(
        f"{place_name} – Displaced Hazard Warning Points\n"
        f"({len(hazard_gdf)} points, threshold ≥ {DANGER_THRESHOLD})",
        fontsize=15, fontweight='bold'
    )
    ax.set_axis_off()

    out = f"data/visualizations/{place_name.lower().replace(' ', '_')}_hazard_points.png"
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"  ✅ Saved visualisation: {out}")
    plt.close()


def visualize_displacement_example(parser, hazard_gdf, place_name="Oxford"):
    """
    Zoomed-in example showing how warning points are displaced from junctions.
    Picks a few high-danger junctions and draws arrows.
    """
    if hazard_gdf.empty:
        return

    os.makedirs("data/visualizations", exist_ok=True)

    # Pick top 5 unique junctions by danger score
    top = (hazard_gdf
           .sort_values('danger_score', ascending=False)
           .drop_duplicates('junction_id')
           .head(5))

    fig, ax = plt.subplots(figsize=(14, 14))
    parser.edges.plot(ax=ax, color='#CCCCCC', linewidth=0.4)

    # Zoom to bounding box of these junctions (with padding)
    lats = list(top['junction_lat']) + list(top['warning_lat'])
    lons = list(top['junction_lon']) + list(top['warning_lon'])
    pad = 0.003
    ax.set_xlim(min(lons) - pad, max(lons) + pad)
    ax.set_ylim(min(lats) - pad, max(lats) + pad)

    # For each top junction, draw its hazard points and connecting lines
    for _, row in hazard_gdf[hazard_gdf['junction_id'].isin(top['junction_id'])].iterrows():
        # Line from junction to warning point
        ax.plot(
            [row.junction_lon, row.warning_lon],
            [row.junction_lat, row.warning_lat],
            color='blue', linewidth=1, alpha=0.5, zorder=2
        )
        # Junction dot
        ax.plot(row.junction_lon, row.junction_lat,
                'ko', markersize=6, zorder=4)
        # Warning point
        color = 'red' if row.danger_score >= 0.6 else 'orange'
        ax.plot(row.warning_lon, row.warning_lat,
                'o', color=color, markersize=10, zorder=5)

    ax.set_title(
        f"{place_name} – Warning Point Displacement Example\n"
        f"Black = junction centre, Coloured = displaced warning point ({DISPLACEMENT_DISTANCE_M}m)",
        fontsize=13, fontweight='bold'
    )
    ax.set_axis_off()

    out = f"data/visualizations/{place_name.lower().replace(' ', '_')}_displacement_example.png"
    plt.savefig(out, dpi=300, bbox_inches='tight')
    print(f"  ✅ Saved displacement example: {out}")
    plt.close()


# ──────────────────────────────────────────────────────────
# Save
# ──────────────────────────────────────────────────────────

def save_hazard_points(hazard_gdf, place_name="Oxford"):
    """Save full hazard points GeoDataFrame to GeoJSON."""
    os.makedirs("data/processed", exist_ok=True)
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    out = f"data/processed/{filename}_hazard_points.geojson"
    hazard_gdf.to_file(out, driver="GeoJSON")
    print(f"  ✅ Saved hazard points: {out}  ({len(hazard_gdf)} features)")


# ──────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║  Hazard Point Generation – Week 7                        ║
    ║  Enhanced danger scoring + point displacement            ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    place_name = "Oxford, UK"

    # 1. Load network via parser
    parser = OSMParser(place_name)
    parser.load_network()
    parser.print_statistics()

    # 2. Generate hazard points
    hazard_gdf = generate_hazard_points(parser)

    if hazard_gdf.empty:
        print("\n❌ No hazard points generated. Exiting.")
        return

    # 3. Print summary
    print(f"\n{'='*60}")
    print("HAZARD POINT SUMMARY")
    print(f"{'='*60}")
    print(f"Total warning points: {len(hazard_gdf)}")
    print(f"Unique junctions:     {hazard_gdf['junction_id'].nunique()}")
    print(f"\nDanger score distribution:")
    print(hazard_gdf['danger_score'].describe().to_string())
    print(f"\nJunction type breakdown:")
    print(hazard_gdf['junction_type'].value_counts().to_string())
    print(f"\nTop 10 most dangerous:")
    top10 = hazard_gdf.nlargest(10, 'danger_score')
    for _, r in top10.iterrows():
        print(f"  {r['junction_type']:12s}  score={r['danger_score']:.3f}  "
              f"road={r['road_name']}  speed_diff={r['speed_differential']} mph")

    # 4. Visualise
    visualize_hazard_points(parser, hazard_gdf, place_name)
    visualize_displacement_example(parser, hazard_gdf, place_name)

    # 5. Save
    save_hazard_points(hazard_gdf, place_name)

    print(f"\n{'='*60}")
    print("✅ HAZARD POINT GENERATION COMPLETE!")
    print(f"{'='*60}")
    print(f"\nWeek 7 Deliverable achieved:")
    print(f"  ✅ Enhanced danger scoring algorithm")
    print(f"  ✅ Point displacement logic ({DISPLACEMENT_DISTANCE_M}m)")
    print(f"  ✅ {len(hazard_gdf)} hazard warning points generated")
    print(f"  ✅ Visualisations saved in data/visualizations/")
    print(f"  ✅ GeoJSON saved in data/processed/")
    print()


if __name__ == "__main__":
    main()
