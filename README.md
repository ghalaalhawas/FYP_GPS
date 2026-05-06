# FYP_GPS

End-to-end pipeline and mobile app for a GPS safety warning system focused on
minor-to-major road merges. The pipeline extracts junctions from OpenStreetMap,
generates hazard points with scores, and exports compact JSON for the mobile
client, which triggers warnings based on proximity, bearing, and cooldown.

## Overview
- Build a road network from OpenStreetMap data for Oxford, UK
- Detect minor-to-major merge candidates and compute hazard scores
- Export compact mobile-ready JSON (plus a small test sample)
- React Native (Expo) app loads hazards, filters by distance, and warns drivers

## How it works
1) Download OSM network data
2) Detect junctions and minor-to-major merge candidates
3) Generate hazard points with a danger score
4) Export mobile JSON (full + sample set)
5) (Optional) Analyze telemetry and generate evaluation charts

## Repository layout
- src/ : Python pipeline scripts and helpers
	- 01_download_osm_data.py
	- 02_detect_junctions.py
	- 03_generate_hazard_points.py
	- 04_export_hazard_data.py
	- 05_analyze_evaluation.py
	- osm_parser.py
- data/raw/ : downloaded OSM data (GraphML, GeoJSON)
- data/processed/ : hazard points and exported mobile JSON
- data/visualizations/evaluation/ : evaluation charts
- gps-mobile-safety-abroad/ : Expo React Native mobile app

## Quick start

### Prerequisites
- Python 3.x and pip
- Node.js LTS and npm
- Expo Go (optional, for running on a device)

### 1) Python pipeline
```bash
python -m venv .venv
# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

python src/01_download_osm_data.py
python src/02_detect_junctions.py
python src/03_generate_hazard_points.py
python src/04_export_hazard_data.py
```

### 2) Mobile app
```bash
cd gps-mobile-safety-abroad
npm install
npx expo start
```

Full setup steps (including device and simulator notes) are in
[gps-mobile-safety-abroad/setup.md](gps-mobile-safety-abroad/setup.md).

By default the app uses the bundled sample file:
```
gps-mobile-safety-abroad/assets/data/oxford_uk_hazard_mobile_sample50.json
```

To use the full dataset, copy the exported JSON from:
```
data/processed/oxford_uk_hazard_mobile.json
```
into `gps-mobile-safety-abroad/assets/data/`, then update the import in:
```
gps-mobile-safety-abroad/src/services/hazardService.js
```

### 3) Evaluation (optional)
```bash
python src/05_analyze_evaluation.py
```
Charts are written to `data/visualizations/evaluation/`.

## Key outputs
- data/processed/oxford_uk_hazard_mobile.json (full mobile dataset)
- data/processed/oxford_uk_hazard_mobile_sample50.json (top-50 sample)
- gps-mobile-safety-abroad/assets/data/oxford_uk_hazard_mobile_sample50.json
- data/visualizations/evaluation/warning_accuracy.png
- data/visualizations/evaluation/warning_distances.png

## Tuning (mobile warnings)
Adjust thresholds in `gps-mobile-safety-abroad/src/services/hazardService.js`:
- PROXIMITY_RADIUS_M (default 300)
- BEARING_TOLERANCE_DEG (default 60)
- COOLDOWN_MS (default 60000)
- MIN_SCORE_THRESHOLD (default 0.35)
