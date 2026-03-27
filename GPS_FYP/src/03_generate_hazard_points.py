"""
03_generate_hazard_points.py

Generates displaced hazard warning points for junctions where a
minor road merges into a major one. Warning points are pushed
50-100m back along the actual road curve so the driver gets warned
before reaching the junction.
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


# --- Constants ---

DISPLACEMENT_DISTANCE_M = 75   # how far to push the warning point back (metres)
DANGER_THRESHOLD = 0.35        # minimum score to generate a hazard point
MIN_CLASS_DIFFERENCE = 2       # minimum road class gap for minor->major

def haversine_distance(lat1, lon1, lat2, lon2):
    """Great-circle distance between two points in metres."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def bearing_between(lat1, lon1, lat2, lon2):
    """Initial bearing (0-360) from point 1 to point 2."""
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360


def displace_point(lat, lon, bearing_deg, distance_m):
    """Move a point along a given bearing by distance_m metres."""
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


# Earth radius in metres (for haversine / bearing calculations)
EARTH_RADIUS_M = 6_371_000


def displace_along_geometry(junction_lat, junction_lon, edge_geometry,
                            junction_is_start, distance_m):
    """Walk distance_m along the road LineString instead of a straight line.
    Returns (new_lat, new_lon, approach_bearing) or None on failure."""
    # Fallback: if no geometry, use straight-line displacement
    if edge_geometry is None or edge_geometry.is_empty:
        return None

    try:
        coords = list(edge_geometry.coords)  # list of (lon, lat)
    except Exception:
        return None

    if len(coords) < 2:
        return None

    # If the junction is at the END of the linestring, reverse it
    # so we always walk away from the junction from index 0.
    jpt = (junction_lon, junction_lat)
    start_dist = math.hypot(coords[0][0] - jpt[0], coords[0][1] - jpt[1])
    end_dist = math.hypot(coords[-1][0] - jpt[0], coords[-1][1] - jpt[1])

    if end_dist < start_dist:
        coords = list(reversed(coords))

    # Walk along the coordinate list, accumulating haversine distance
    walked = 0.0
    prev_lon, prev_lat = coords[0]

    for lon2, lat2 in coords[1:]:
        seg_len = haversine_distance(prev_lat, prev_lon, lat2, lon2)
        if walked + seg_len >= distance_m:
            # Interpolate within this segment
            remaining = distance_m - walked
            frac = remaining / seg_len if seg_len > 0 else 0
            new_lon = prev_lon + frac * (lon2 - prev_lon)
            new_lat = prev_lat + frac * (lat2 - prev_lat)

            # Bearing from displaced point toward junction
            approach_bearing = bearing_between(
                new_lat, new_lon, junction_lat, junction_lon)
            return (new_lat, new_lon, approach_bearing)

        walked += seg_len
        prev_lon, prev_lat = lon2, lat2

    # Road segment shorter than requested distance — place at end
    new_lat, new_lon = coords[-1][1], coords[-1][0]
    approach_bearing = bearing_between(
        new_lat, new_lon, junction_lat, junction_lon)
    return (new_lat, new_lon, approach_bearing)


def calculate_enhanced_danger_score(junction_info, parser):
    """Danger score (0-1) weighted toward minor->major class mismatch."""
    scores = {}

    # --- 1. Road classification mismatch (0-1) ---
    road_classes = []
    for edge in junction_info['edges']:
        road_classes.append(parser.get_road_classification(edge['highway']))

    if len(road_classes) >= 2:
        class_diff = max(road_classes) - min(road_classes)
        # Diff of 6+ maps to 1.0  (e.g. primary vs residential)
        scores['class_mismatch'] = min(class_diff / 6.0, 1.0)
    else:
        scores['class_mismatch'] = 0.0

    # --- 2. Speed differential (0-1) ---
    speed_diff = junction_info.get('speed_differential', 0)
    scores['speed_diff'] = min(speed_diff / 40.0, 1.0)

    # --- 3. Approach angle sharpness (0-1) ---
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
            scores['angle'] = max(0, 1.0 - min_angle / 90.0)
        else:
            scores['angle'] = 0.0
    else:
        scores['angle'] = 0.0

    # --- 4. Junction complexity (0-1) ---
    street_count = junction_info['street_count']
    if street_count == 3:
        scores['complexity'] = 0.5
    elif street_count == 4:
        scores['complexity'] = 0.4
    elif street_count >= 5:
        scores['complexity'] = 0.7
    else:
        scores['complexity'] = 0.2

    # --- Weighted combination (focused on minor→major) ---
    weights = {
        'class_mismatch': 0.35,
        'speed_diff':     0.30,
        'angle':          0.20,
        'complexity':     0.15,
    }

    total = sum(scores[k] * weights[k] for k in weights)
    return round(min(max(total, 0.0), 1.0), 4)


def identify_secondary_roads(junction_info, parser):
    """Find the minor roads at a junction that feed into a major road.
    Only returns results when there's a clear class gap (>= MIN_CLASS_DIFFERENCE)."""
    edges = junction_info['edges']
    if not edges:
        return []

    # Classify each edge
    classified = []
    for edge in edges:
        rc = parser.get_road_classification(edge['highway'])
        classified.append({'edge': edge, 'road_class': rc})

    max_class = max(c['road_class'] for c in classified)
    min_class = min(c['road_class'] for c in classified)

    # Only generate hazard when minor road actually meets a major one
    if (max_class - min_class) < MIN_CLASS_DIFFERENCE:
        return []  # roads are too similar — not a minor→major merge

    # Only pick the minor (lower-class) roads
    secondary = [c for c in classified if c['road_class'] < max_class]
    if not secondary:
        return []

    jlat, jlon = junction_info['location']
    result = []
    for item in secondary:
        edge = item['edge']
        other_id = edge['to'] if edge['from'] == junction_info['id'] else edge['from']
        try:
            other_node = parser.nodes.loc[other_id]
            olat, olon = other_node.geometry.y, other_node.geometry.x
            approach_bearing = bearing_between(olat, olon, jlat, jlon)
            result.append({
                'edge': edge,
                'road_class': item['road_class'],
                'max_class': max_class,
                'other_lat': olat,
                'other_lon': olon,
                'approach_bearing': approach_bearing,
            })
        except KeyError:
            continue

    return result


def generate_hazard_points(parser, danger_threshold=DANGER_THRESHOLD,
                           displacement_m=DISPLACEMENT_DISTANCE_M):
    """Go through every junction, score it, and generate displaced warning points."""
    junctions = parser.get_junctions(min_streets=3)

    print(f"\n--- Generating Hazard Points ---")
    print(f"Threshold: {danger_threshold}, displacement: {displacement_m}m")

    hazard_records = []
    skipped = 0
    skipped_no_merge = 0
    errors = 0
    curve_displaced = 0

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

        # Identify MINOR roads that merge into a MAJOR road
        secondary_roads = identify_secondary_roads(info, parser)

        if not secondary_roads:
            skipped_no_merge += 1
            continue

        for road in secondary_roads:
            jlat, jlon = info['location']

            # --- Curve-aware displacement (follows actual road shape) ---
            edge_geom = road['edge'].get('geometry', None)
            displaced = displace_along_geometry(
                jlat, jlon, edge_geom,
                junction_is_start=(road['edge']['from'] == junction_id),
                distance_m=displacement_m
            )

            if displaced is not None:
                wlat, wlon, approach_bearing = displaced
                curve_displaced += 1
            else:
                # Fallback: straight-line displacement
                away_bearing = (road['approach_bearing'] + 180) % 360
                wlat, wlon = displace_point(jlat, jlon, away_bearing, displacement_m)
                approach_bearing = road['approach_bearing']

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
                'merge_type': 'minor_to_major',
                'street_count': sc,
                'approach_bearing': round(approach_bearing, 1),
                'road_name': road['edge'].get('name', 'Unnamed'),
                'road_type': road['edge'].get('highway', 'unknown'),
                'major_road_class': road.get('max_class', 0),
                'minor_road_class': road.get('road_class', 0),
                'speed_differential': info.get('speed_differential', 0),
                'geometry': Point(wlon, wlat),   # GeoJSON is (lon, lat)
            })

    print(f"\n  Generated {len(hazard_records)} hazard warning points")
    print(f"  Skipped {skipped} below threshold, {skipped_no_merge} with no minor->major merge")
    print(f"  {curve_displaced}/{len(hazard_records)} displaced along road curve")
    if errors:
        print(f"  {errors} junctions had errors (missing data)")

    if not hazard_records:
        print("  No hazard points generated - try lowering the threshold.")
        return gpd.GeoDataFrame()

    gdf = gpd.GeoDataFrame(hazard_records, crs="EPSG:4326")
    return gdf


def visualize_hazard_points(parser, hazard_gdf, place_name="Oxford"):
    """Map showing junctions and their displaced warning points."""
    if hazard_gdf.empty:
        print("  No hazard points to visualise.")
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
    print(f"  Saved: {out}")
    plt.close()


def visualize_displacement_example(parser, hazard_gdf, place_name="Oxford"):
    """Zoomed-in view of a few high-danger junctions with arrows showing displacement."""
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
    print(f"  Saved: {out}")
    plt.close()


def save_hazard_points(hazard_gdf, place_name="Oxford"):
    """Save hazard points as GeoJSON."""
    os.makedirs("data/processed", exist_ok=True)
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    out = f"data/processed/{filename}_hazard_points.geojson"
    hazard_gdf.to_file(out, driver="GeoJSON")
    print(f"  Saved: {out}  ({len(hazard_gdf)} features)")


def main():
    print("\n--- Hazard Point Generation ---\n")

    place_name = "Oxford, UK"

    # 1. Load network via parser
    parser = OSMParser(place_name)
    parser.load_network()
    parser.print_statistics()

    # 2. Generate hazard points (only minor→major merges)
    hazard_gdf = generate_hazard_points(parser)

    if hazard_gdf.empty:
        print("\nNo hazard points generated.")
        return

    # Summary
    print(f"\n--- Hazard Point Summary ---")
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
              f"minor={r['road_name']} ({r['road_type']})  "
              f"speed_diff={r['speed_differential']} mph")

    visualize_hazard_points(parser, hazard_gdf, place_name)
    visualize_displacement_example(parser, hazard_gdf, place_name)
    save_hazard_points(hazard_gdf, place_name)

    print(f"\nDone - {len(hazard_gdf)} hazard points generated and saved.\n")


if __name__ == "__main__":
    main()
