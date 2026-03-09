# Ghala Safety App - Mobile Application
**Week 5 - Hello World with GPS**

## Quick Start

### Prerequisites
- Node.js installed (v18+)
- Expo Go app on your phone ([iOS](https://apps.apple.com/app/expo-go/id982107779) | [Android](https://play.google.com/store/apps/details?id=host.exp.exponent))

### Setup

```bash
# Navigate to mobile app directory
cd mobile_app/GhalaSafetyApp

# Install dependencies
npm install

# Start development server
npx expo start
```

### Running on Device

1. Start the development server with `npx expo start`
2. Scan the QR code with Expo Go app
3. App will load on your device
4. Grant location permissions when prompted

## Current Features (Week 5)

✅ GPS location tracking  
✅ Map view with user location  
✅ Sample hazard point markers  
✅ Location permission handling  
✅ Real-time location updates  

## Project Structure

```
GhalaSafetyApp/
├── App.js                 # Main app entry point
├── package.json           # Dependencies
├── app.json              # Expo configuration
└── src/                  # Source code (Week 6+)
    ├── components/       # UI components
    ├── services/         # Business logic
    └── utils/            # Utility functions
```

## Next Steps (Week 6+)

- [ ] Load real hazard data from GeoJSON
- [ ] Implement proximity detection
- [ ] Add warning system
- [ ] Implement spatial indexing (R-tree)
- [ ] Add settings screen
- [ ] Implement offline caching

## Troubleshooting

**Can't connect to development server:**
- Ensure phone and computer on same Wi-Fi
- Try tunnel mode: `npx expo start --tunnel`

**Location not working:**
- Check location permissions in device settings
- Ensure location services enabled
- Try restarting Expo Go app

**Map not loading:**
- Check internet connection
- Restart app
- Check console for errors

## Week 5 Deliverable ✅

**Basic GPS functionality implemented:**
- [x] Location permissions
- [x] GPS tracking
- [x] Map view
- [x] Hello World app running on device

---

**Status:** Week 5 Complete  
**Last Updated:** January 27, 2026
