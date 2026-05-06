# Setup (macOS and Windows)

This project is an Expo React Native app. Use the steps below to run it on macOS
or Windows.

## 1) Requirements

### macOS
- macOS
- Node.js LTS: https://nodejs.org
- Xcode (for iOS simulator)

### Windows
- Windows 10/11
- Node.js LTS: https://nodejs.org
- Expo Go (iOS or Android): https://expo.dev/client
- Optional: Android Studio for the Android emulator
	https://developer.android.com/studio

Verify Node.js:
```bash
node -v
npm -v
```

## 2) Xcode setup (iOS simulator, macOS only)
1) Install Xcode from the App Store
2) Open Xcode once and accept the license
3) Install Command Line Tools:
```bash
xcode-select --install
```

## 3) Install dependencies
```bash
cd path/to/gps-mobile-safety-abroad
npm install
```

## 4) Run on Xcode iOS simulator (macOS only)
```bash
npx expo start
```
- In the Expo terminal, press `i`

Optional shortcut:
```bash
npm run ios
```

## 5) Run on a normal iPhone (Expo Go, no Xcode)
1) Install Expo Go from the App Store
2) Make sure the iPhone and Mac are on the same Wi-Fi
3) Start the dev server:
```bash
npx expo start
```
4) Scan the QR code
- iPhone: open the Camera app and scan

If the phone cannot connect:
```bash
npx expo start --tunnel
```

## 6) Windows: run on Android emulator (optional)
1) Install Android Studio:
	https://developer.android.com/studio
2) Open Android Studio and install an Android SDK + emulator image.
3) Start an emulator from the Device Manager.
4) Start the Expo dev server:
```bash
npx expo start
```
5) Press `a` in the Expo terminal to open the app on the emulator.

## 7) Windows: run on a device (Expo Go)
1) Install Expo Go:
	https://expo.dev/client
2) Ensure your phone and PC are on the same Wi-Fi.
3) Start the dev server:
```bash
npx expo start
```
4) Scan the QR code with the Expo Go app.

If the phone cannot connect:
```bash
npx expo start --tunnel
```

## 8) Expo SDK mismatch note (SDK 55 project vs SDK 54 Expo Go)
This project uses Expo SDK 55 (see package.json `expo: ~55.0.0`).

If Expo Go on your iPhone is still on SDK 54, it will refuse to open this project.

Choose one option:
- Option A: Update Expo Go from the App Store and try again (wait for SDK 55 support).
- Option B: Temporarily downgrade the project to SDK 54 for Expo Go:
```bash
npx expo install expo@~54.0.0 react-native expo-location expo-status-bar react-native-maps
npm install
npx expo start
```

When Expo Go supports SDK 55, you can switch back:
```bash
npx expo install expo@~55.0.0 react-native expo-location expo-status-bar react-native-maps
npm install
npx expo start
```
