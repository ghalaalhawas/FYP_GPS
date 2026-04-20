# Ghala - GPS Safety App for Driving Abroad

Final Year Project (2025/2026)
Supervisor: Dr Crispin Cooper

This project warns drivers when approaching hazardous minor-to-major road merges using OpenStreetMap data and real-time GPS.

## Current Scope (Reduced and Focused)
- Minor road to major road hazard detection
- Curve-aware warning point displacement
- Mobile map with live GPS location
- Proximity + direction-aware warning trigger
- Offline hazard data caching
- R-tree spatial indexing for efficient lookup

## Repository Structure

```text
GPS_FYP/
├── src/
│   ├── 01_download_osm_data.py
│   ├── 02_detect_junctions.py
│   ├── 03_generate_hazard_points.py
│   ├── 04_export_hazard_data.py
│   └── 05_analyze_evaluation.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── visualizations/
├── mobile_app/GhalaSafetyApp/
│   ├── App.js
│   ├── package.json
│   └── src/
│       ├── components/WarningBanner.js
│       ├── services/hazardService.js
│       └── utils/geo.js
└── docs/
```

## Python Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Run Data Pipeline

```bash
python src/01_download_osm_data.py
python src/02_detect_junctions.py
python src/03_generate_hazard_points.py
python src/04_export_hazard_data.py
```

## Mobile App Setup

```bash
cd mobile_app/GhalaSafetyApp
npm install
npx expo start
```

Use Expo Go to open the app on a phone.

## Implemented Features
- OSM hazard data ingestion
- Junction risk scoring and hazard generation
- Curve-aware point displacement
- GPS tracking and location services
- Real-time proximity detection
- Direction-aware warning triggering
- In-app warning banner and vibration alerts
- Offline hazard caching and persistence
- Spatial indexing with R-tree optimization

## Notes
- The codebase intentionally avoids over-complex features to match the supervisor-approved scope.
- The main technical focus is algorithmic hazard generation and efficient runtime detection.
