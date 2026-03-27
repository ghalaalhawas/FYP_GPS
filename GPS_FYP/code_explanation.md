# Ghala GPS Safety App — Code Explanation
**Weeks 4–18 (January–May 2026)**

---

## Table of Contents
1. [Week 4–5: OSM Data Parser (`osm_parser.py`)](#week-45-osm-data-parser)
2. [Week 6: Junction Detection (`02_detect_junctions.py`)](#week-6-junction-detection)
3. [Week 7: Hazard Point Generation (`03_generate_hazard_points.py`)](#week-7-hazard-point-generation)
4. [Week 9: Mobile Data Export (`04_export_hazard_data.py`)](#week-9-mobile-data-export)
5. [Week 10: Supervisor Feedback & Refinements](#week-10-supervisor-feedback--refinements)
6. [Week 11: Data Integration & Proximity Detection](#week-11-data-integration--proximity-detection)
7. [Week 12: Warning System & Direction Filtering](#week-12-warning-system--direction-filtering)
8. [Week 13: Caching & Offline Loading](#week-13-caching--offline-loading)
9. [Week 14: Spatial Optimization (R-tree)](#week-14-spatial-optimization-r-tree)
10. [Week 15: Validation Controls](#week-15-validation-controls)
11. [Week 16: Evaluation Event Logging](#week-16-evaluation-event-logging)
12. [Week 17: Settings UI & Persistence](#week-17-settings-ui--persistence)
13. [Week 18: Evaluation Export & Metrics](#week-18-evaluation-export--metrics)

---

## Week 4–5: OSM Data Parser

**File:** `src/osm_parser.py`  
**Purpose:** A reusable Python class that acts as a clean interface for loading, parsing, and querying OpenStreetMap (OSM) street network data. All later scripts import and use this class.

---

### Class Initialisation

```python
class OSMParser:
    def __init__(self, place_name="Oxford, UK", network_type="drive"):
        self.place_name = place_name
        self.network_type = network_type
        self.G = None       # NetworkX graph
        self.nodes = None   # GeoDataFrame of nodes (intersections)
        self.edges = None   # GeoDataFrame of edges (road segments)

        ox.settings.log_console = True
        ox.settings.use_cache = True  # Cache API responses to avoid re-downloading

        # Automatically create the data directories if they don't exist
        self.raw_dir = Path("data") / "raw"
        self.processed_dir = Path("data") / "processed"
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
```

**Key concepts:**  
- `self.G` stores the road network as a **directed NetworkX graph** — nodes are intersections, edges are road segments.  
- `ox.settings.use_cache = True` tells OSMnx to save Overpass API responses to disk so the same area is never downloaded twice.
- `Path("data") / "raw"` uses Python's `pathlib` for OS-independent path building.

---

### Loading the Network

```python
def load_network(self, force_download=False):
    filename = self._get_filename()
    graphml_path = self.raw_dir / f"{filename}_network.graphml"

    if graphml_path.exists() and not force_download:
        # Load from local file (fast — no internet needed)
        self.G = ox.load_graphml(graphml_path)
    else:
        # Download from OpenStreetMap's Overpass API
        self.G = ox.graph_from_place(
            self.place_name,
            network_type=self.network_type   # "drive" = roads only
        )
        ox.save_graphml(self.G, graphml_path)

    # Convert graph to two GeoDataFrames for easy analysis
    self.nodes, self.edges = ox.graph_to_gdfs(self.G)
    return self.G
```

**What `graph_to_gdfs` gives us:**  
- `self.nodes` — one row per intersection, columns include `street_count` (how many roads meet here), `x`, `y` coordinates.  
- `self.edges` — one row per road segment, columns include `highway` (road type tag), `maxspeed`, `name`, `length`.

**Why GraphML format?** It preserves the full graph structure including all OSM attributes, unlike GeoJSON which only stores geometry.

---

### Extracting Junctions

```python
def get_junctions(self, min_streets=3):
    # A junction is any node where 3 or more roads meet
    junctions = self.nodes[self.nodes['street_count'] >= min_streets].copy()
    return junctions
```

OSMnx pre-computes the `street_count` attribute for every node during graph construction. Filtering on `>= 3` removes dead-ends (1 road), through-roads (2 roads), and leaves only true junctions.

---

### Road Classification

```python
def get_road_classification(self, highway_tag):
    # Handle OSM tags that come as lists (when a road has multiple tags)
    if isinstance(highway_tag, list):
        highway_tag = highway_tag[0] if highway_tag else 'unknown'

    classification = {
        'motorway': 10,
        'trunk': 9,
        'primary': 8,
        'secondary': 6,
        'tertiary': 4,
        'unclassified': 3,
        'residential': 2,
        'service': 1,
        'unknown': 0
    }
    return classification.get(highway_tag, 0)
```

This converts OSM's string tags (e.g. `"primary"`) into numbers. The difference between two connected roads' scores is used later as a **danger factor** — a residential road (2) meeting a primary road (8) has a mismatch of 6, indicating priority confusion.

---

### Speed Limit Parsing

```python
def extract_speed_limit(self, maxspeed_tag):
    # OSM maxspeed can be: "30 mph", "50", "30 mph;40 mph", None
    if maxspeed_tag is None or maxspeed_tag == '':
        return None

    maxspeed_str = str(maxspeed_tag).lower()
    match = re.search(r'(\d+)', maxspeed_str)
    if not match:
        return None

    speed = int(match.group(1))

    # Convert km/h to mph if needed
    if 'km' in maxspeed_str or 'kph' in maxspeed_str:
        speed = int(speed * 0.621371)

    return speed


def infer_speed_limit(self, highway_tag):
    # Used as a fallback when maxspeed tag is absent
    typical_speeds = {
        'motorway': 70,  'trunk': 70,
        'primary': 60,   'secondary': 50,
        'tertiary': 40,  'unclassified': 40,
        'residential': 30, 'service': 20,
    }
    return typical_speeds.get(highway_tag, 30)
```

Many OSM roads lack explicit speed limits. Rather than discarding them, we infer UK typical speeds by road type as a fallback.

---

### Junction Info Aggregation

```python
def get_junction_info(self, junction_id):
    node = self.nodes.loc[junction_id]
    edges = self.get_junction_edges(junction_id)

    road_types = []
    speed_limits = []

    for edge in edges:
        road_types.append(edge['highway'])
        speed = self.extract_speed_limit(edge['maxspeed'])
        if speed is None:
            speed = self.infer_speed_limit(edge['highway'])
        speed_limits.append(speed)

    return {
        'id': junction_id,
        'location': (node.geometry.y, node.geometry.x),   # (lat, lon)
        'street_count': node['street_count'],
        'edges': edges,
        'road_types': road_types,
        'speed_limits': speed_limits,
        'max_speed': max(speed_limits) if speed_limits else None,
        'min_speed': min(speed_limits) if speed_limits else None,
        'speed_differential': max(speed_limits) - min(speed_limits) if speed_limits else 0
    }
```

`speed_differential` is the difference between the fastest and slowest road at a junction. A driver turning from a 30 mph residential road onto a 60 mph primary road faces a 30 mph differential — a significant risk factor.

---

## Week 6: Junction Detection

**File:** `src/02_detect_junctions.py`  
**Purpose:** Uses the `OSMParser` foundation to identify, classify, visualise, and save all road junctions in Oxford.

---

### Loading the Network

```python
def load_network(place_name="Oxford, UK"):
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    graphml_path = f"data/raw/{filename}_network.graphml"

    if os.path.exists(graphml_path):
        G = ox.load_graphml(graphml_path)   # Use cached file if available
    else:
        G = ox.graph_from_place(place_name, network_type="drive")

    nodes, edges = ox.graph_to_gdfs(G)
    return G, nodes, edges
```

This is a standalone version of the same logic in `osm_parser.py`, used before the parser class was abstracted out.

---

### Identifying Junctions

```python
def identify_junctions(nodes, min_streets=3):
    # street_count is an attribute OSMnx adds to every node
    junctions = nodes[nodes['street_count'] >= min_streets].copy()
    return junctions
```

For Oxford this yields **2,258 junctions** out of 3,388 total nodes. The remaining ~1,130 nodes are dead-ends or simple through-roads.

---

### Classifying Junction Types

```python
def classify_junctions(junctions):
    def get_junction_type(street_count):
        if street_count == 3:
            return "T-junction"
        elif street_count == 4:
            return "Crossroads"
        elif street_count == 5:
            return "5-way"
        else:
            return f"{street_count}-way"

    junctions['junction_type'] = junctions['street_count'].apply(get_junction_type)
    return junctions
```

Oxford results:
| Type | Count |
|------|-------|
| T-junction | 2,111 |
| Crossroads | 145 |
| 5-way | 2 |

---

### Preliminary Danger Score

```python
def calculate_danger_score(junctions, edges):
    def score_junction(row):
        street_count = row['street_count']
        if street_count == 3:
            base_score = 0.7    # T-junctions are high priority
        elif street_count == 4:
            base_score = 0.5    # Standard crossroads
        elif street_count >= 5:
            base_score = 0.8    # Complex = more confusion
        else:
            base_score = 0.3
        return base_score

    junctions['danger_score'] = junctions.apply(score_junction, axis=1)
    return junctions
```

This is a **simple first-pass** score based only on junction shape. It is replaced by the multi-factor algorithm in Week 7.

---

### Visualisation

Three maps are generated and saved to `data/visualizations/`:

```python
def visualize_junctions(G, junctions, place_name="Oxford"):
    os.makedirs("data/visualizations", exist_ok=True)

    # --- Map 1: All junctions as red dots ---
    fig, ax = ox.plot_graph(G, node_size=0, edge_linewidth=0.3,
                             edge_color='#CCCCCC', bgcolor='white',
                             show=False, close=False, figsize=(12, 12))
    junctions.plot(ax=ax, color='red', markersize=20, alpha=0.6, zorder=3)
    ax.set_title(f"{place_name} - Road Junctions (3+ roads)")
    plt.savefig(f"data/visualizations/...junctions_all.png", dpi=300, bbox_inches='tight')
    plt.close()

    # --- Map 2: Junctions colour-coded by type ---
    colors = {'T-junction': 'red', 'Crossroads': 'orange', '5-way': 'purple'}
    for junction_type, color in colors.items():
        subset = junctions[junctions['junction_type'] == junction_type]
        subset.plot(ax=ax, color=color, markersize=25, alpha=0.7,
                    label=junction_type, zorder=3)
    ax.legend(loc='upper right', fontsize=12)

    # --- Map 3: Heat gradient by danger score ---
    junctions.plot(ax=ax, column='danger_score', cmap='YlOrRd',
                   markersize=30, alpha=0.8, legend=True, zorder=3)
```

`ox.plot_graph` renders the road network as a background layer. `GeoDataFrame.plot` then overlays the junction points on the same axes (`ax`). `cmap='YlOrRd'` is a colour map from yellow (low) to red (high) danger.

---

### Saving Junction Data

```python
def save_junctions_data(junctions, place_name="Oxford"):
    filename = place_name.lower().replace(' ', '_').replace(',', '')
    output_path = f"data/processed/{filename}_junctions.geojson"

    # Only save the columns we actually need downstream
    output_cols = ['osmid', 'street_count', 'junction_type', 'danger_score', 'geometry']
    available_cols = [col for col in output_cols if col in junctions.columns]

    junctions[available_cols].to_file(output_path, driver="GeoJSON")
```

GeoJSON is chosen as the output format because it is human-readable, widely supported, and directly loadable by the mobile app.

---

## Week 7: Hazard Point Generation

**File:** `src/03_generate_hazard_points.py`  
**Purpose:** The core algorithm of the project. For each dangerous junction, it calculates a multi-factor danger score and places a **displaced warning point** 75 metres up each approaching road — giving drivers advance notice before they reach the junction.

---

### Geometry Helper Functions

#### Haversine Distance

```python
EARTH_RADIUS_M = 6_371_000

def haversine_distance(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))
```

The haversine formula calculates the **great-circle distance** (shortest path over the Earth's surface) between two GPS coordinates in metres. Used internally to verify displacement accuracy.

#### Bearing Calculation

```python
def bearing_between(lat1, lon1, lat2, lon2):
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    dlon = lon2 - lon1
    x = math.sin(dlon) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    bearing = math.degrees(math.atan2(x, y))
    return (bearing + 360) % 360    # Normalise to 0-360
```

Calculates the **compass bearing** (direction) from one GPS point to another. `atan2` gives the angle in radians; converting to degrees and adding 360 ensures the result is always positive (0° = North, 90° = East, 180° = South, 270° = West).

#### Point Displacement

```python
DISPLACEMENT_DISTANCE_M = 75

def displace_point(lat, lon, bearing_deg, distance_m):
    lat_r = math.radians(lat)
    lon_r = math.radians(lon)
    bearing_r = math.radians(bearing_deg)
    d = distance_m / EARTH_RADIUS_M   # Angular distance in radians

    new_lat = math.asin(
        math.sin(lat_r) * math.cos(d) +
        math.cos(lat_r) * math.sin(d) * math.cos(bearing_r)
    )
    new_lon = lon_r + math.atan2(
        math.sin(bearing_r) * math.sin(d) * math.cos(lat_r),
        math.cos(d) - math.sin(lat_r) * math.sin(new_lat)
    )
    return math.degrees(new_lat), math.degrees(new_lon)
```

This is the **inverse haversine** — given a starting point, a direction (bearing), and a distance, it computes the new coordinates. This is how the warning point is placed exactly 75 metres up the road from the junction, giving a driver roughly 3–5 seconds of warning at 30–60 mph.

---

### Enhanced Danger Score (4 Factors)

After supervisor feedback in Week 10, the weights were rebalanced to prioritise **road class mismatch** (the strongest signal that a minor road is merging into a major one):

```python
def calculate_enhanced_danger_score(junction_info, parser):
    scores = {}

    # Factor 1: Road classification mismatch  (HIGHEST weight — the core signal)
    road_classes = [parser.get_road_classification(e['highway'])
                    for e in junction_info['edges']]
    if len(road_classes) >= 2:
        class_diff = max(road_classes) - min(road_classes)
        scores['class_mismatch'] = min(class_diff / 6.0, 1.0)
    else:
        scores['class_mismatch'] = 0.0

    # Factor 2: Speed differential
    speed_diff = junction_info.get('speed_differential', 0)
    scores['speed_diff'] = min(speed_diff / 40.0, 1.0)

    # Factor 3: Approach angle sharpness
    # ... (same bearing pair-wise minimum as before)
    scores['angle'] = max(0, 1.0 - min_angle / 90.0)

    # Factor 4: Junction complexity
    street_count = junction_info['street_count']
    if street_count == 3:
        scores['complexity'] = 0.5
    elif street_count == 4:
        scores['complexity'] = 0.4
    elif street_count >= 5:
        scores['complexity'] = 0.7
    else:
        scores['complexity'] = 0.2

    # Weighted combination — focused on minor→major merges
    weights = {
        'class_mismatch': 0.35,   # up from 0.30
        'speed_diff':     0.30,
        'angle':          0.20,
        'complexity':     0.15,   # down from 0.20
    }

    total = sum(scores[k] * weights[k] for k in weights)
    return round(min(max(total, 0.0), 1.0), 4)
```

**Why these weights?**
- `class_mismatch` gets the highest weight (0.35) because a residential road (class 2) meeting a primary road (class 8) is the **core danger scenario** the project targets.
- `speed_diff` gets 0.30 because it is closely related — bigger class gaps usually mean bigger speed gaps.
- `angle` gets 0.20 — tight merge angles reduce visibility.
- `complexity` gets 0.15 — a supporting factor, not the main signal.

---

### Identifying Minor Road Approaches

After supervisor feedback, this function was tightened so it **only** returns results when there is a genuine minor→major class gap:

```python
MIN_CLASS_DIFFERENCE = 2   # residential(2) vs tertiary(4) = gap of 2, just qualifies

def identify_secondary_roads(junction_info, parser):
    edges = junction_info['edges']

    classified = [{'edge': e, 'road_class': parser.get_road_classification(e['highway'])}
                  for e in edges]

    max_class = max(c['road_class'] for c in classified)
    min_class = min(c['road_class'] for c in classified)

    # Only generate hazard when minor road actually meets a major one
    if (max_class - min_class) < MIN_CLASS_DIFFERENCE:
        return []   # roads are too similar — not a minor→major merge

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
                'other_lat': olat, 'other_lon': olon,
                'approach_bearing': approach_bearing,
            })
        except KeyError:
            continue
    return result
```

The `MIN_CLASS_DIFFERENCE = 2` filter means a junction where two residential roads meet (both class 2) produces **no** hazard points — there is no priority confusion. A residential road (2) meeting a tertiary road (4) just qualifies, and a residential road (2) meeting a primary road (8) gets a strong mismatch score.

---

### Generating All Hazard Points

The main loop now includes **curve-aware displacement** and tracks how many points were displaced along real road geometry vs straight-line fallback:

```python
DANGER_THRESHOLD = 0.35

def generate_hazard_points(parser, danger_threshold=DANGER_THRESHOLD,
                           displacement_m=DISPLACEMENT_DISTANCE_M):
    junctions = parser.get_junctions(min_streets=3)
    hazard_records = []
    skipped = 0
    skipped_no_merge = 0
    curve_displaced = 0

    for idx, junction_id in enumerate(junctions.index):
        info = parser.get_junction_info(junction_id)
        danger_score = calculate_enhanced_danger_score(info, parser)

        if danger_score < danger_threshold:
            skipped += 1
            continue

        secondary_roads = identify_secondary_roads(info, parser)

        if not secondary_roads:
            skipped_no_merge += 1    # passed the score but no minor→major gap
            continue

        for road in secondary_roads:
            jlat, jlon = info['location']

            # --- Try curve-aware displacement first ---
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

            hazard_records.append({
                'junction_id':      junction_id,
                'junction_lat':     jlat,
                'junction_lon':     jlon,
                'warning_lat':      wlat,
                'warning_lon':      wlon,
                'danger_score':     danger_score,
                'junction_type':    jtype,
                'merge_type':       'minor_to_major',
                'approach_bearing': round(approach_bearing, 1),
                'road_name':        road['edge'].get('name', 'Unnamed'),
                'road_type':        road['edge'].get('highway', 'unknown'),
                'major_road_class': road.get('max_class', 0),
                'minor_road_class': road.get('road_class', 0),
                'speed_differential': info.get('speed_differential', 0),
                'geometry':         Point(wlon, wlat),
            })

    gdf = gpd.GeoDataFrame(hazard_records, crs="EPSG:4326")
    return gdf
```

**Key changes from Week 7 to Week 10:**
- Two-stage filtering: junctions must pass both the danger score threshold **and** the `MIN_CLASS_DIFFERENCE` check.
- `displace_along_geometry()` is tried first; straight-line `displace_point()` is only a fallback.
- New fields `merge_type`, `major_road_class`, `minor_road_class` added to each record.
- `skipped_no_merge` counter tracks junctions that scored high but had no genuine minor→major gap.

---

### Displacement Visualisation

```python
def visualize_displacement_example(parser, hazard_gdf, place_name="Oxford"):
    # Pick top 5 unique junctions by danger score
    top = (hazard_gdf
           .sort_values('danger_score', ascending=False)
           .drop_duplicates('junction_id')
           .head(5))

    fig, ax = plt.subplots(figsize=(14, 14))
    parser.edges.plot(ax=ax, color='#CCCCCC', linewidth=0.4)

    # Zoom to the area of these junctions
    pad = 0.003
    ax.set_xlim(min_lon - pad, max_lon + pad)
    ax.set_ylim(min_lat - pad, max_lat + pad)

    for _, row in hazard_gdf[hazard_gdf['junction_id'].isin(top['junction_id'])].iterrows():
        # Blue line connecting junction to warning point
        ax.plot([row.junction_lon, row.warning_lon],
                [row.junction_lat, row.warning_lat],
                color='blue', linewidth=1, alpha=0.5, zorder=2)
        ax.plot(row.junction_lon, row.junction_lat, 'ko', markersize=6, zorder=4)  # Junction
        color = 'red' if row.danger_score >= 0.6 else 'orange'
        ax.plot(row.warning_lon, row.warning_lat, 'o', color=color,
                markersize=10, zorder=5)  # Warning point
```

This zoomed-in visualisation makes the 75 m displacement visible — the blue lines show the offset between each black junction dot and its coloured warning point.

---

## Week 9: Mobile Data Export

**File:** `src/04_export_hazard_data.py`  
**Purpose:** Converts the full GeoJSON hazard dataset into a compact, optimised JSON format ready for the React Native mobile app, then generates three output files.

---

### Loading the GeoJSON

```python
INPUT_GEOJSON = "data/processed/oxford_uk_hazard_points.geojson"

def load_hazard_data(path=INPUT_GEOJSON):
    if not os.path.exists(path):
        print(f"❌ Input file not found: {path}")
        print("   Run 03_generate_hazard_points.py first.")
        sys.exit(1)

    gdf = gpd.read_file(path)
    return gdf
```

A hard exit with a helpful message is better than a crash — it tells the user exactly which script to run first.

---

### Transforming to Mobile Format

```python
COORD_DECIMALS = 6   # 6 decimal places ≈ 0.1 m precision
SCORE_DECIMALS = 3

def transform_for_mobile(gdf):
    records = []
    for idx, row in gdf.iterrows():
        records.append({
            "id":       int(idx + 1),
            "lat":      round(float(row["warning_lat"]),  COORD_DECIMALS),  # Warning point
            "lon":      round(float(row["warning_lon"]),  COORD_DECIMALS),
            "jLat":     round(float(row["junction_lat"]), COORD_DECIMALS),  # Actual junction
            "jLon":     round(float(row["junction_lon"]), COORD_DECIMALS),
            "score":    round(float(row["danger_score"]), SCORE_DECIMALS),
            "type":     str(row["junction_type"]),
            "bearing":  round(float(row["approach_bearing"]), 1),
            "road":     str(row.get("road_name", "Unnamed")),
            "roadType": str(row.get("road_type", "unknown")),
        })
    return records
```

**Why explicit `float()` and `int()` casts?**  
GeoPandas reads values as NumPy types (`numpy.float64`, `numpy.int64`). Python's `json.dump` cannot serialise these — it raises `TypeError: Object of type ndarray is not JSON serializable`. Casting to native Python types (`float`, `int`, `str`) fixes this.

**Fields kept and why:**

| Field | Description | Used by app for |
|-------|-------------|-----------------|
| `lat` / `lon` | Warning point coords | Proximity detection trigger |
| `jLat` / `jLon` | Junction centre coords | Map marker placement |
| `score` | Danger score 0–1 | Warning severity / colour |
| `type` | Junction type string | Warning message text |
| `bearing` | Approach direction | Direction filtering (warn only if heading toward junction) |
| `road` | Road name | Warning message ("Warning on Woodstock Road") |
| `roadType` | OSM highway tag | UI styling |
| `majorClass` | Numeric class of the major road | Debugging / analysis |
| `minorClass` | Numeric class of the minor road | Debugging / analysis |

---

### Saving Compact JSON

```python
def save_compact_json(records, output_path):
    with open(output_path, 'w') as f:
        # separators=(',', ':') removes all unnecessary whitespace
        json.dump(records, f, separators=(',', ':'))

    size_bytes = os.path.getsize(output_path)
    return size_bytes
```

`separators=(',', ':')` strips all spacing from the JSON output. For 274 records this saves ~30% file size (48.5 KB vs 69.4 KB). At scale (50,000 UK-wide points), this saves roughly 2.5 MB.

---

### Saving Sample Subset

```python
def generate_sample_subset(records, n=50, output_path=None):
    # Sort by score and take top N — gives the most useful test data
    sorted_records = sorted(records, key=lambda r: r['score'], reverse=True)
    sample = sorted_records[:n]

    # Re-number IDs from 1
    for i, r in enumerate(sample):
        r['id'] = i + 1

    if output_path:
        with open(output_path, 'w') as f:
            json.dump(sample, f, indent=2)

    return sample
```

The 50-point sample is used during mobile development to load just a small dataset into the app, making it easier to test warning behaviour without the overhead of all 274 points.

---

### Export Summary and Scaling Estimates

```python
def print_export_summary(records, compact_size, pretty_size):
    per_point = compact_size / max(len(records), 1)

    print(f"Estimated sizes (compact):")
    for n in [1000, 5000, 10000, 50000]:
        est = per_point * n / 1024
        print(f"  {n:>6,} points → {est:>8.1f} KB ({est/1024:.2f} MB)")
```

This gives a realistic projection for future coverage expansion:

| Points | Estimated size |
|--------|---------------|
| 1,000 | ~177 KB |
| 10,000 | ~1.7 MB |
| 50,000 | ~8.7 MB |

For UK-wide coverage (estimated ~50,000 hazard points), the full dataset loads in under a second on a modern mobile connection and comfortably fits in device storage.

---

## Week 10: Supervisor Feedback & Refinements

After meeting with Dr Crispin Cooper, three changes were applied across the codebase:

### 1. Minor→Major Road Focus

The supervisor emphasised that the **core danger scenario** is a driver on a small road merging onto a bigger, faster one. The changes:

- `identify_secondary_roads()` now enforces `MIN_CLASS_DIFFERENCE = 2` — junctions where all roads are similar class produce no hazard points.
- Danger score weights rebalanced: `class_mismatch` raised to 0.35, `complexity` lowered to 0.15.
- Each hazard record now stores `merge_type: 'minor_to_major'`, `major_road_class`, and `minor_road_class` for downstream analysis.

### 2. Curve-Aware Point Displacement

The original `displace_point()` moved the warning point along a **straight-line bearing**. On curved roads this could place the point off the actual road. The new `displace_along_geometry()` walks along the real OSM LineString:

```python
def displace_along_geometry(junction_lat, junction_lon, edge_geometry,
                            junction_is_start, distance_m):
    """Walk distance_m along the road LineString instead of a straight line."""
    if edge_geometry is None or edge_geometry.is_empty:
        return None

    coords = list(edge_geometry.coords)   # list of (lon, lat) tuples

    # Make sure we walk AWAY from the junction
    jpt = (junction_lon, junction_lat)
    start_dist = math.hypot(coords[0][0] - jpt[0], coords[0][1] - jpt[1])
    end_dist   = math.hypot(coords[-1][0] - jpt[0], coords[-1][1] - jpt[1])
    if end_dist < start_dist:
        coords = list(reversed(coords))

    # Walk along segments, accumulating haversine distance
    walked = 0.0
    prev_lon, prev_lat = coords[0]

    for lon2, lat2 in coords[1:]:
        seg_len = haversine_distance(prev_lat, prev_lon, lat2, lon2)
        if walked + seg_len >= distance_m:
            remaining = distance_m - walked
            frac = remaining / seg_len if seg_len > 0 else 0
            new_lon = prev_lon + frac * (lon2 - prev_lon)
            new_lat = prev_lat + frac * (lat2 - prev_lat)
            approach_bearing = bearing_between(new_lat, new_lon, junction_lat, junction_lon)
            return (new_lat, new_lon, approach_bearing)

        walked += seg_len
        prev_lon, prev_lat = lon2, lat2

    # Road segment shorter than requested distance — place at far end
    new_lat, new_lon = coords[-1][1], coords[-1][0]
    approach_bearing = bearing_between(new_lat, new_lon, junction_lat, junction_lon)
    return (new_lat, new_lon, approach_bearing)
```

**How it works:** Starting at the junction end of the LineString, the function walks coordinate-by-coordinate, summing haversine distances. When the accumulated walk exceeds the target (75 m), it linearly interpolates within the current segment to land exactly at the right distance. The approach bearing is then computed from this displaced point back toward the junction.

If the edge has no geometry (some OSM edges are straight lines with only two endpoints), it returns `None` and the caller falls back to the original straight-line `displace_point()`.

### 3. Battery Optimisation in Mobile App

The GPS watcher in `App.js` was changed:

```javascript
Location.watchPositionAsync(
  {
    accuracy: Location.Accuracy.Balanced,  // was High
    timeInterval: 10000,                   // at most every 10s
    distanceInterval: 20,                  // or when moved 20m
  },
  (newLoc) => { ... }
);
```

Expo's **Balanced** mode uses the phone's fused location provider (Wi-Fi + cell + GPS) which draws less battery than continuous high-accuracy GPS. Since hazard zones start 200–300 m out, a 20 m movement trigger is more than sufficient.

---

## Week 11: Data Integration & Proximity Detection

**Files:** `src/utils/geo.js`, `src/services/hazardService.js`, updates to `App.js`  
**Purpose:** Replace hardcoded sample markers with real hazard data from the Python pipeline, and implement proximity detection so the app knows when the user is near a dangerous junction.

---

### Geometry Utilities (JavaScript)

**File:** `mobile_app/GhalaSafetyApp/src/utils/geo.js`

```javascript
const EARTH_RADIUS_M = 6371000;

function haversine(lat1, lon1, lat2, lon2) {
  const toRad = (deg) => (deg * Math.PI) / 180;
  const dLat = toRad(lat2 - lat1);
  const dLon = toRad(lon2 - lon1);
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2;
  return 2 * EARTH_RADIUS_M * Math.asin(Math.sqrt(a));
}

function bearingBetween(lat1, lon1, lat2, lon2) {
  // ... same formula as the Python version
  return (toDeg(Math.atan2(y, x)) + 360) % 360;
}

function angleDiff(b1, b2) {
  const diff = Math.abs(b1 - b2) % 360;
  return Math.min(diff, 360 - diff);
}
```

These are JavaScript translations of the same `haversine_distance`, `bearing_between`, and `angle_between_bearings` functions from the Python code. They run on the phone to compute distances and bearings in real time.

---

### Hazard Data Service

**File:** `mobile_app/GhalaSafetyApp/src/services/hazardService.js`

```javascript
import hazardData from '../../../data/processed/oxford_uk_hazard_mobile_sample50.json';

const PROXIMITY_RADIUS_M = 300;
const BEARING_TOLERANCE_DEG = 60;
const COOLDOWN_MS = 60000;   // 1 minute

const cooldowns = {};   // hazard id → timestamp of last warning
```

**Constants:**
- `PROXIMITY_RADIUS_M = 300` — the app starts checking a hazard when the user is within 300 m. This gives roughly 10–18 seconds of lead time at typical driving speeds (30–60 mph).
- `BEARING_TOLERANCE_DEG = 60` — only warn if the user's travel direction is within ±60° of the stored approach bearing. This prevents warnings when driving **past** a junction rather than toward it.
- `COOLDOWN_MS = 60000` — once a hazard triggers, it won't trigger again for 60 seconds (prevents the same junction spamming the driver).

#### Finding Nearby Hazards

```javascript
function findNearby(userLat, userLon) {
  const nearby = [];
  for (const h of hazardData) {
    const dist = haversine(userLat, userLon, h.lat, h.lon);
    if (dist <= PROXIMITY_RADIUS_M) {
      nearby.push({ ...h, distance: Math.round(dist) });
    }
  }
  nearby.sort((a, b) => a.distance - b.distance);
  return nearby;
}
```

A simple linear scan over all 50 hazard points. For 50 points this takes microseconds. For a larger UK-wide dataset an R-tree spatial index would be needed (Week 14 plan).

#### Direction Check

```javascript
function isApproaching(userBearing, hazard) {
  if (userBearing == null || hazard.bearing == null) return true;
  return angleDiff(userBearing, hazard.bearing) <= BEARING_TOLERANCE_DEG;
}
```

If the user is heading roughly the same direction as the stored `approach_bearing`, they are approaching the junction from the minor-road side and should be warned. If they are heading in a different direction (e.g. driving along the major road, or away from the junction), the warning is suppressed.

#### Main Warning Check

```javascript
function checkForWarning(userLat, userLon, userBearing) {
  const nearby = findNearby(userLat, userLon);
  for (const h of nearby) {
    if (!isCooldownClear(h.id)) continue;
    if (!isApproaching(userBearing, h)) continue;
    return h;   // closest qualifying hazard
  }
  return null;
}
```

This is called on every GPS update. It returns at most one hazard — the closest one that passes both the cooldown and direction checks.

---

### App.js Updates (Week 11)

The hardcoded `sampleHazards` array was removed and replaced with:

```javascript
import { getAllHazards, checkForWarning, markWarned } from './src/services/hazardService';
import { bearingBetween } from './src/utils/geo';

const hazards = getAllHazards();
```

Map markers now render from real data:

```javascript
{hazards.map((h) => (
  <Marker
    key={h.id}
    coordinate={{ latitude: h.lat, longitude: h.lon }}
    title={`${h.type} (${h.score.toFixed(2)})`}
    description={h.road.replace(/[\[\]']/g, '')}
    pinColor={h.score >= 0.7 ? 'red' : 'orange'}
  />
))}
```

Travel bearing is computed from consecutive GPS fixes:

```javascript
const prevCoords = useRef(null);

// inside the watchPositionAsync callback:
let userBearing = null;
if (prevCoords.current) {
  const prev = prevCoords.current;
  const dlat = latitude - prev.latitude;
  const dlon = longitude - prev.longitude;
  // Only compute bearing if we moved enough to be meaningful
  if (Math.abs(dlat) > 0.00002 || Math.abs(dlon) > 0.00002) {
    userBearing = bearingBetween(prev.latitude, prev.longitude, latitude, longitude);
  }
}
prevCoords.current = { latitude, longitude };
```

The threshold `0.00002` degrees is roughly 2 metres — below that the GPS jitter would produce random bearings.

---

## Week 12: Warning System & Direction Filtering

**File:** `src/components/WarningBanner.js`, further updates to `App.js`  
**Purpose:** Show a visual warning when the user is approaching a dangerous junction, with vibration, auto-dismiss, and cooldown.

---

### Warning Banner Component

**File:** `mobile_app/GhalaSafetyApp/src/components/WarningBanner.js`

```javascript
export default function WarningBanner({ hazard, visible }) {
  if (!visible || !hazard) return null;

  const isHigh = hazard.score >= 0.7;
  const accentColor = isHigh ? '#cc0000' : '#e68a00';
  const label = isHigh ? 'HIGH RISK' : 'CAUTION';

  return (
    <View style={[styles.banner, { borderLeftColor: accentColor }]}>
      <Text style={[styles.label, { color: accentColor }]}>{label}</Text>
      <Text style={styles.title}>
        {hazard.type} ahead — {hazard.distance}m
      </Text>
      <Text style={styles.detail}>
        {hazard.road} ({hazard.roadType})
      </Text>
      <Text style={styles.score}>
        Danger score: {hazard.score.toFixed(2)}
      </Text>
    </View>
  );
}
```

**Design decisions:**
- Two colour tiers: red (`#cc0000`) for scores ≥ 0.7, amber (`#e68a00`) otherwise.
- Shows the junction type, distance in metres, road name, road type, and numeric danger score.
- Positioned at the bottom of the screen with a thick coloured left border — visible without blocking the map.

---

### Wiring It Together in App.js

In the `watchPositionAsync` callback, after computing `userBearing`:

```javascript
const warning = checkForWarning(latitude, longitude, userBearing);
if (warning) {
  markWarned(warning.id);               // start cooldown
  setActiveWarning(warning);            // show banner
  Vibration.vibrate(400);               // 400ms haptic buzz
  setTimeout(() => setActiveWarning(null), 8000);  // auto-dismiss after 8s
}
```

The warning flow:
1. GPS update arrives.
2. `checkForWarning()` scans for the closest hazard within 300 m that passes the bearing and cooldown checks.
3. If found: vibrate, display the `WarningBanner`, mark the hazard as warned (60 s cooldown).
4. After 8 seconds the banner hides itself.
5. The same hazard won't re-trigger for another 60 seconds, but a **different** nearby hazard can trigger immediately.

---

## Week 13: Caching & Offline Loading

**Files:** `src/services/hazardService.js`  
**Purpose:** Make hazard loading resilient and offline-friendly by caching hazard data on-device.

The hazard service now initializes asynchronously and prioritizes local cache:

```javascript
import AsyncStorage from '@react-native-async-storage/async-storage';

const HAZARD_CACHE_KEY = 'ghala_hazard_cache_v1';

let hazards = [];
let isInitialized = false;

async function initializeHazardService() {
    const cached = await AsyncStorage.getItem(HAZARD_CACHE_KEY);
    if (cached) {
        const parsed = JSON.parse(cached);
        if (Array.isArray(parsed) && parsed.length > 0) {
            hazards = parsed.map(normalizeHazard);
        }
    }

    if (hazards.length === 0) {
        hazards = bundledHazards.map(normalizeHazard);
    }

    isInitialized = true;
    await AsyncStorage.setItem(HAZARD_CACHE_KEY, JSON.stringify(hazards));
    return hazards;
}
```

This gives an offline-first flow:
1. Try cached hazards.
2. If missing, load bundled sample JSON.
3. Persist the chosen dataset for next launch.

---

## Week 14: Spatial Optimization (R-tree)

**Files:** `src/services/hazardService.js`  
**Purpose:** Speed up nearby-hazard queries as dataset size grows.

An R-tree (`rbush`) is now used to prefilter candidates before haversine checks:

```javascript
import RBush from 'rbush';

let hazardTree = null;

function buildSpatialIndex(list) {
    const tree = new RBush();
    tree.load(list.map((h) => ({
        minX: h.lon,
        minY: h.lat,
        maxX: h.lon,
        maxY: h.lat,
        hazard: h,
    })));
    return tree;
}

function findNearby(userLat, userLon, radiusM = 300) {
    const latPad = metersToLat(radiusM);
    const lonPad = metersToLon(radiusM, userLat);

    const candidates = hazardTree.search({
        minX: userLon - lonPad,
        minY: userLat - latPad,
        maxX: userLon + lonPad,
        maxY: userLat + latPad,
    });

    // Final precise filtering with haversine distance
    // ...
}
```

Before: linear scan over all hazards.  
Now: bounding-box search + precise distance check.

---

## Week 15: Validation Controls

**Files:** `src/services/settingsService.js`, `App.js`  
**Purpose:** Add configurable thresholds so behaviour can be tuned during field testing.

```javascript
const DEFAULT_SETTINGS = {
    alertSensitivity: 'normal',
    proximityRadiusM: 300,
    bearingToleranceDeg: 60,
    cooldownMs: 60000,
    vibrationEnabled: true,
    onlyHighRiskMarkers: false,
};

function minScoreForSensitivity(level) {
    if (level === 'low') return 0.45;
    if (level === 'high') return 0.25;
    return 0.35;
}
```

`App.js` now passes these values directly to warning checks:

```javascript
const warning = checkForWarning(latitude, longitude, userBearing, {
    proximityRadiusM: activeSettings.proximityRadiusM,
    bearingToleranceDeg: activeSettings.bearingToleranceDeg,
    cooldownMs: activeSettings.cooldownMs,
    minScore: minScoreForSensitivity(activeSettings.alertSensitivity),
});
```

This supports controlled experiments (stricter vs more sensitive warnings) without code edits.

---

## Week 16: Evaluation Event Logging

**Files:** `src/services/evaluationService.js`, `App.js`  
**Purpose:** Capture warning behaviour and location traces for later analysis.

Two event types are stored in AsyncStorage:
- `warning`: triggered warning with hazard id, score, distance, and user bearing.
- `location`: periodic location sample with bearing.

```javascript
async function logWarningEvent(event) {
    const events = await readEvents();
    events.push({ type: 'warning', ts: Date.now(), ...event });
    await writeEvents(events);
}

async function logLocationSample(sample) {
    const events = await readEvents();
    events.push({ type: 'location', ts: Date.now(), ...sample });
    await writeEvents(events);
}
```

In `App.js`, location samples are throttled to every third GPS update to keep logs useful but compact.

---

## Week 17: Settings UI & Persistence

**Files:** `src/components/SettingsPanel.js`, `App.js`, `src/services/settingsService.js`  
**Purpose:** Provide user-facing controls and persistent app preferences.

The new settings modal includes:
- Alert sensitivity (`low`, `normal`, `high`)
- Proximity radius input
- Bearing tolerance input
- Cooldown input
- Vibration toggle
- High-risk marker filter toggle

All values are saved via `saveSettings()` and restored at startup with `loadSettings()`.

---

## Week 18: Evaluation Export & Metrics

**Files:** `src/services/evaluationService.js`, `src/components/SettingsPanel.js`, `App.js`  
**Purpose:** Prepare measurable outputs for formal evaluation.

Implemented evaluation utilities:

```javascript
async function getEvaluationStats() {
    const events = await readEvents();
    return {
        totalEvents: events.length,
        warningEvents: events.filter((e) => e.type === 'warning').length,
        locationSamples: events.filter((e) => e.type === 'location').length,
    };
}

async function exportEvaluationJson() {
    const events = await readEvents();
    return JSON.stringify(events, null, 2);
}
```

The settings panel now shows a live evaluation snapshot and provides:
- Export evaluation JSON
- Clear evaluation logs for clean reruns

---

## Data Flow Summary

```
01_download_osm_data.py    → downloads & caches street network (GraphML)
         ↓
osm_parser.py              → OSMParser class: loads, queries, classifies roads
         ↓
02_detect_junctions.py     → identifies 2,258 junctions, classifies types, saves GeoJSON
         ↓
03_generate_hazard_points.py
    ├── calculate_enhanced_danger_score()   → 4-factor weighted score per junction
    ├── identify_secondary_roads()          → finds minor road approaches (MIN_CLASS_DIFFERENCE ≥ 2)
    ├── displace_along_geometry()           → moves warning 75m along actual road curve
    └── displace_point()                    → straight-line fallback when no geometry
    → outputs hazard points + 2 visualisation maps
         ↓
04_export_hazard_data.py   → strips to essential fields, compact JSON, ~48.5 KB
         ↓
mobile_app/GhalaSafetyApp/
    ├── src/utils/geo.js                    → haversine, bearing, angleDiff (JS)
    ├── src/services/hazardService.js       → cached hazard loading + RBush spatial search
    ├── src/services/settingsService.js     → persistent runtime warning settings
    ├── src/services/evaluationService.js   → warning/location event logging + export
    ├── src/components/SettingsPanel.js     → settings + evaluation controls modal
    ├── src/components/WarningBanner.js     → visual alert with score + distance
    └── App.js                              → map, GPS tracking, configurable checks, logging
```

---

*Last updated: March 2026 — Week 18 implementation complete.*
