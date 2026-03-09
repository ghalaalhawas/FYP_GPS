# Ghala - GPS Safety App for Driving Abroad

**Final Year Project - 2025/2026** | **Supervisor:** Crispin Cooper

Warns drivers about dangerous road junctions when driving abroad, using OpenStreetMap data and real-time GPS proximity detection.

---

## Repository Structure

```
GPS_FYP/
├── src/
│   ├── osm_parser.py                   # Reusable OSM data loader / parser
│   ├── 02_detect_junctions.py          # Junction detection & classification
│   ├── 03_generate_hazard_points.py    # Danger scoring + 75m point displacement
│   └── 04_export_hazard_data.py        # Export optimised JSON for mobile app
├── data/
│   ├── processed/
│   │   ├── oxford_uk_junctions.geojson
│   │   ├── oxford_uk_hazard_points.geojson
│   │   ├── oxford_uk_hazard_mobile.json          # Compact JSON for app (48 KB)
│   │   ├── oxford_uk_hazard_mobile_pretty.json
│   │   └── oxford_uk_hazard_mobile_sample50.json
│   └── visualizations/
│       ├── oxford,_uk_junctions_all.png
│       ├── oxford,_uk_junctions_by_type.png
│       ├── oxford,_uk_danger_scores.png
│       ├── oxford,_uk_hazard_points.png
│       └── oxford,_uk_displacement_example.png
├── mobile_app/GhalaSafetyApp/
│   ├── App.js                          # Main React Native entry point
│   ├── app.json
│   ├── package.json
│   └── src/
├── requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Data processing | Python 3.9+, osmnx, geopandas, shapely, pyproj |
| Data format | GeoJSON → compact JSON for mobile |
| Mobile app | React Native (Expo) |
| Maps | react-native-maps |
| GPS | expo-location |
| Spatial index | rbush (R-tree) |

---

## Python Setup

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows

# Install dependencies
pip install -r requirements.txt
```

### Run the pipeline

```bash
# 1. Download OSM data (Oxford, UK) - local only, not in repo
python src/01_download_osm_data.py

# 2. Detect and classify junctions
python src/02_detect_junctions.py

# 3. Generate displaced hazard warning points
python src/03_generate_hazard_points.py

# 4. Export optimised JSON for mobile app
python src/04_export_hazard_data.py
```

> Steps 2–4 use cached data — no re-download needed if `data/raw/` exists.

### How OSM data is downloaded

OSMnx downloads the street network directly from the OpenStreetMap Overpass API:

```python
import osmnx as ox
G = ox.graph_from_place('Oxford, UK', network_type='drive')
ox.save_graphml(G, filepath='data/raw/oxford_uk_network.graphml')
```

Alternatively, download `.osm.pbf` files from [Geofabrik](https://download.geofabrik.de/) and place in `data/raw/`.

---

## Mobile App Setup

```bash
cd mobile_app/GhalaSafetyApp
npm install
npx expo start
```

Scan the QR code with **Expo Go** on your phone (Android / iOS).

---

## Data Pipeline

```
OSM API
  ↓  osm_parser.py
Street Network (GraphML)
  ↓  02_detect_junctions.py
Classified Junctions → data/visualizations/*.png
  ↓  03_generate_hazard_points.py
Hazard Points displaced 75m (GeoJSON)
  ↓  04_export_hazard_data.py
Compact JSON for mobile app (48 KB for Oxford)
```

### Danger scoring factors
- Junction type (T-junction = 0.7, crossroads = 0.5, 5-way = 0.8)
- Speed differential between connecting roads
- Road classification mismatch (e.g. primary meets residential)

### Oxford, UK results (March 2026)
- 3,388 road nodes — 2,258 junctions identified
- **274 hazard warning points** generated (threshold ≥ 0.35)
- Danger scores: 0.35 – 0.745 | Export: **48.5 KB**

---

## Milestones

| Date | Milestone |
|------|-----------|
| Feb 2, 2026 | Initial plan submitted ✅ |
| Mar 2, 2026 | Data processing complete ✅ |
| Apr 6, 2026 | Core app functionality |
| May 4, 2026 | Testing & refinement |
| Jul 5, 2026 | Final report submission |


### Data Processing:
- Python 3.9+
- Libraries: osmnx, shapely, geopandas, pyproj
- Jupyter notebooks for exploration
- GeoJSON format for data export

### Mobile App:
- **To be decided by end of Week 1**
- Options: React Native, Flutter, or Native iOS (Swift)
- See [mobile_frameworks_comparison.md](research/mobile_frameworks_comparison.md) for details

## Setup Instructions

### Python Environment:
```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Downloading OSM Data:

The processed data and visualizations are included in this repository under `data/processed/` and `data/visualizations/`.

If you need to download fresh OSM data:

**Option 1: Using OSMnx (Recommended)**
```python
import osmnx as ox

# Download by place name
G = ox.graph_from_place('Oxford, UK', network_type='drive')

# Download by bounding box
G = ox.graph_from_bbox(north, south, east, west, network_type='drive')

# Save to file
ox.save_graphml(G, filepath='data/raw/oxford.graphml')
```

**Option 2: Download from Geofabrik**
1. Visit: https://download.geofabrik.de/
2. Select your region (e.g., Europe → Great Britain)
3. Download `.osm.pbf` file
4. Place in `data/raw/` directory

**Option 3: Using Overpass API**
```bash
# Install osmium-tool
# Then extract specific areas as needed
```

### Mobile App:
```bash
# Navigate to mobile app directory
cd mobile_app/GhalaSafetyApp

# Install dependencies
npm install

# Start development server
npx expo start

# Scan QR code with Expo Go app on your phone
```

## Development Timeline

### January 2026
- **Week 1 (Jan 1-5):** Research and technology stack decision ✅
- **Week 2 (Jan 6-12):** Environment setup and initial data exploration
- **Week 3 (Jan 13-19):** Initial plan preparation
- **Week 4 (Jan 20-26):** Initial plan finalization
- **Week 5 (Jan 27-Feb 2):** **Initial plan submission (Feb 2)**

### Key Milestones

| Date | Milestone |
|------|-----------|
| Feb 2, 2026 | Initial Plan Submission |
| Mar 2, 2026 | Data processing complete |
| Apr 6, 2026 | Core app functionality complete |
| May 4, 2026 | Testing and refinement complete |
| Jun 1, 2026 | Evaluation complete |
| **Jul 5, 2026** | **Final Report Submission** |

## Current Status

### Week 1 (Jan 1-5): Project Setup & Initial Research ✅
**Completed:**
- ✅ Project structure created
- ✅ Technology research completed
  - OpenStreetMap data structure and APIs
  - Python geospatial libraries (osmnx, shapely, geopandas, pyproj)
  - Mobile development frameworks comparison
- ✅ Research documents created
- ✅ Git setup guide prepared
- 🔄 Technology stack decision document in progress

**Next Steps (Week 2):**
- Set up Python development environment
- Download and explore sample OSM data
- Create initial data visualization
- Make final mobile framework decision
- Set up version control (Git/GitHub)

## Research Documents

All research completed in Week 1:

1. **[OSM Research Notes](research/osm_research_notes.md)**
   - OpenStreetMap data structure
   - Junction detection methods
   - OSMnx library usage examples

2. **[Python Libraries Guide](research/python_libraries_guide.md)**
   - Detailed documentation for osmnx, shapely, geopandas, pyproj
   - Code examples and use cases
   - Installation instructions

3. **[Mobile Frameworks Comparison](research/mobile_frameworks_comparison.md)**
   - React Native vs Flutter vs Native iOS/Android
   - Pros and cons of each framework
   - Decision matrix and recommendations

4. **[Technology Stack Decision](docs/technology_stack_decision.md)**
   - Final technology decisions with justification
   - Data format choices (GeoJSON)
   - Development environment setup

5. **[Git Setup Guide](docs/git_setup_guide.md)**
   - Version control setup instructions
   - Git workflow and best practices
   - GitHub repository creation

## Core Functionality

### Phase 1: Data Processing (Feb-Mar)
- Download OpenStreetMap data for target regions
- Identify road junctions programmatically
- Classify junction types (T-junction, crossroads, etc.)
- Calculate "danger scores" based on:
  - Junction geometry and angles
  - Speed differentials between roads
  - Road classification mismatch
  - Visibility factors
- Generate hazard points (displaced 50-100m up secondary road)
- Export as GeoJSON format

### Phase 2: Mobile App (Feb-May)
- GPS location tracking with high accuracy
- Load and cache hazard point data
- Proximity detection (warn within 200m of hazard)
- Directional awareness (only warn from correct approach)
- Visual and audio warning system
- Offline capability with local caching
- User settings and preferences

### Phase 3: Optimization (Apr)
- Spatial indexing (BSP tree or R-tree)
- Performance optimization for mobile
- Battery usage optimization
- Background location updates

### Phase 4: Evaluation (May)
- User testing and feedback
- Accuracy measurements
- Performance benchmarking
- Safety impact assessment

## Risk Management

**Risk 1: Mobile development environment issues**
- Mitigation: Start early, use cross-platform framework if needed, seek help promptly

**Risk 2: OSM data processing too complex**
- Mitigation: Start with small region, use existing libraries, simplify if needed

**Risk 3: GPS accuracy issues**
- Mitigation: Test early, adjust thresholds, document limitations

**Risk 4: Time management**
- Mitigation: Follow weekly plan, adjust if falling behind, prioritize core features

## Questions for Supervisor

1. Any preference on mobile framework? (React Native vs Flutter vs Native)
2. Expected dataset size - how much of UK/Europe should we cover?
3. Are there specific types of junctions to focus on?
4. Should the app work completely offline or require internet?
5. Any specific evaluation criteria for the app?

## Resources

### Documentation
- OSMnx: https://osmnx.readthedocs.io/
- Shapely: https://shapely.readthedocs.io/
- GeoPandas: https://geopandas.org/
- React Native: https://reactnative.dev/
- Flutter: https://flutter.dev/

### Data Sources
- OpenStreetMap: https://www.openstreetmap.org/
- Geofabrik: https://download.geofabrik.de/


---

**Last Updated:** January 1, 2026  
**Project Start Date:** January 1, 2026  
**Submission Deadline:** July 5, 2026
