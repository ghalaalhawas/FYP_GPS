# GPS Mobile app to help driving safety abroad (React Native + Expo)

Mobile client for warning drivers about hazardous minor-to-major road merges.

For full setup instructions, see [setup.md](setup.md).

## What the App Does
- Shows user location on map
- Loads hazard points from local bundled JSON
- Uses R-tree filtering plus Haversine distance checks
- Triggers warning only when approaching from correct direction
- Vibrates and shows a warning banner when hazard is relevant
- Caches hazard data locally for offline-first behavior

## Quick Start

```bash
cd mobile_app/gps-mobile-safety-abroad
npm install
npx expo start
```

Then scan the QR code with Expo Go.

## Core Files
- App.js: app entry, GPS subscription, map rendering, warning handling
- src/services/hazardService.js: cache, R-tree index, nearby search, warning checks
- src/utils/geo.js: Haversine distance and bearing helpers
- src/components/WarningBanner.js: visual warning UI

## Scope Note
This app is intentionally kept simple and focused to match supervisor guidance:
algorithmic hazard detection quality plus efficient runtime warnings, without extra non-core features.
