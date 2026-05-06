import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, Vibration, View } from 'react-native';
import MapView, { Marker, Polyline, PROVIDER_DEFAULT } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

import { initializeHazardService, getAllHazards, checkForWarning, markWarned, clearCooldowns } from './src/services/hazardService';
import { bearingBetween } from './src/utils/geo';
import WarningBanner from './src/components/WarningBanner';

const OXFORD_REGION = {
  latitude: 51.752,
  longitude: -1.2577,
  latitudeDelta: 0.12,
  longitudeDelta: 0.12,
};

const EARTH_RADIUS_M = 6371000;
const MIN_WARNING_DISPLAY_MS = 5000;

function makeRegion(lat, lon, delta = 0.01) {
  return { latitude: lat, longitude: lon, latitudeDelta: delta, longitudeDelta: delta };
}

function movePointByMeters(lat, lon, bearingDeg, distanceM) {
  const latR = (lat * Math.PI) / 180;
  const lonR = (lon * Math.PI) / 180;
  const bR = (bearingDeg * Math.PI) / 180;
  const d = distanceM / EARTH_RADIUS_M;

  const newLat = Math.asin(
    Math.sin(latR) * Math.cos(d) + Math.cos(latR) * Math.sin(d) * Math.cos(bR)
  );
  const newLon = lonR + Math.atan2(
    Math.sin(bR) * Math.sin(d) * Math.cos(latR),
    Math.cos(d) - Math.sin(latR) * Math.sin(newLat)
  );

  return {
    latitude: (newLat * 180) / Math.PI,
    longitude: (newLon * 180) / Math.PI,
  };
}

export default function App() {
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeWarning, setActiveWarning] = useState(null);
  const [hazards, setHazards] = useState([]);
  const [fakeLocation, setFakeLocation] = useState(null);
  const [useFakeLocation, setUseFakeLocation] = useState(false);
  const [developerModeOpen, setDeveloperModeOpen] = useState(false);
  const [developerEntryLocation, setDeveloperEntryLocation] = useState(null);
  const [simulating, setSimulating] = useState(false);
  const [simRoute, setSimRoute] = useState([]);

  const mapRef = useRef(null);
  const mapRegionRef = useRef(null);
  const prevCoords = useRef(null);
  const watchSubRef = useRef(null);
  const bannerTimeoutRef = useRef(null);
  const fakeLocationRef = useRef(null);
  const useFakeLocationRef = useRef(false);
  const lastFakeHazardIdRef = useRef(null);
  const developerSnapshotRef = useRef(null);
  const simIntervalRef = useRef(null);
  const simWaypointsRef = useRef([]);
  const simIndexRef = useRef(0);
  const simTurnDirectionsRef = useRef({});
  const activeWarningStartRef = useRef(null);

  useEffect(() => { fakeLocationRef.current = fakeLocation; }, [fakeLocation]);
  useEffect(() => { useFakeLocationRef.current = useFakeLocation; }, [useFakeLocation]);

  const showWarning = (warning) => {
    markWarned(warning.id);
    activeWarningStartRef.current = Date.now();
    const turnDirection = simTurnDirectionsRef.current[warning.id] ?? null;
    setActiveWarning({ ...warning, turnDirection });
    Vibration.vibrate(400);
    if (bannerTimeoutRef.current) clearTimeout(bannerTimeoutRef.current);
    bannerTimeoutRef.current = setTimeout(() => {
      setActiveWarning(null);
      activeWarningStartRef.current = null;
    }, 8000);
  };

  const runWarningCheck = (lat, lon, userBearing = null) => {
    // don't replace a warning that just appeared
    if (activeWarningStartRef.current !== null &&
        Date.now() - activeWarningStartRef.current < MIN_WARNING_DISPLAY_MS) return;

    const warning = checkForWarning(lat, lon, userBearing);
    if (warning) showWarning(warning);
  };

  const jumpToRegion = (region) => {
    if (mapRef.current) mapRef.current.animateToRegion(region, 700);
  };

  const jumpToOxford = () => jumpToRegion(OXFORD_REGION);

  const jumpToMyLocation = () => {
    if (location) jumpToRegion(location);
  };

  const openDeveloperMode = () => {
    developerSnapshotRef.current = {
      useFakeLocation: useFakeLocationRef.current,
      fakeLocation: fakeLocationRef.current,
      region: mapRegionRef.current || location || null,
    };
    setDeveloperEntryLocation(location ? { latitude: location.latitude, longitude: location.longitude } : null);
    setDeveloperModeOpen(true);
  };

  const restoreBeforeDeveloperMode = () => {
    const snap = developerSnapshotRef.current;
    if (snap) {
      setUseFakeLocation(!!snap.useFakeLocation);
      setFakeLocation(snap.fakeLocation ?? null);
      if (snap.region) jumpToRegion(snap.region);
    } else {
      setUseFakeLocation(false);
    }
    setDeveloperEntryLocation(null);
    setDeveloperModeOpen(false);
  };

  const setFakeToHazard = () => {
    if (!hazards.length) {
      Alert.alert('Hazards not loaded yet', 'Try again in a few seconds.');
      return;
    }

    const candidates = hazards
      .filter(h => Number.isFinite(h.lat) && Number.isFinite(h.lon))
      .sort((a, b) => b.score - a.score);

    if (!candidates.length) {
      Alert.alert('No valid hazards', 'No hazard coordinates available.');
      return;
    }

    let pool = candidates;
    if (candidates.length > 1 && lastFakeHazardIdRef.current != null) {
      const filtered = candidates.filter(h => h.id !== lastFakeHazardIdRef.current);
      if (filtered.length > 0) pool = filtered;
    }

    const best = pool[Math.floor(Math.random() * pool.length)];
    lastFakeHazardIdRef.current = best.id;

    const metersAhead = 20 + Math.floor(Math.random() * 81);
    const backBearing = Number.isFinite(best.bearing) ? (best.bearing + 180) % 360 : Math.floor(Math.random() * 360);
    const nextFake = movePointByMeters(best.lat, best.lon, backBearing, metersAhead);

    setFakeLocation(nextFake);
    setUseFakeLocation(true);
    jumpToRegion(makeRegion(nextFake.latitude, nextFake.longitude, 0.02));
    runWarningCheck(nextFake.latitude, nextFake.longitude, null);
  };

  const toggleFakeLocationMode = () => {
    if (useFakeLocation) { setUseFakeLocation(false); return; }
    if (!fakeLocation) { setFakeToHazard(); return; }
    setUseFakeLocation(true);
    jumpToRegion(makeRegion(fakeLocation.latitude, fakeLocation.longitude, 0.02));
    runWarningCheck(fakeLocation.latitude, fakeLocation.longitude, null);
  };

  const interpolateWaypoints = (waypoints, steps = 12) => {
    const result = [];
    for (let i = 0; i < waypoints.length - 1; i++) {
      const a = waypoints[i];
      const b = waypoints[i + 1];
      for (let j = 0; j < steps; j++) {
        const t = j / steps;
        result.push({
          latitude: a.latitude + t * (b.latitude - a.latitude),
          longitude: a.longitude + t * (b.longitude - a.longitude),
        });
      }
    }
    if (waypoints.length > 0) result.push(waypoints[waypoints.length - 1]);
    return result;
  };

  const stopRouteSimulation = () => {
    if (simIntervalRef.current) { clearInterval(simIntervalRef.current); simIntervalRef.current = null; }
    if (bannerTimeoutRef.current) clearTimeout(bannerTimeoutRef.current);
    simTurnDirectionsRef.current = {};
    activeWarningStartRef.current = null;
    setActiveWarning(null);
    setSimulating(false);
    setSimRoute([]);
  };

  const startRouteSimulation = () => {
    const valid = hazards.filter(
      h => Number.isFinite(h.lat) && Number.isFinite(h.lon) && Number.isFinite(h.bearing)
    );

    if (!valid.length) {
      Alert.alert('No hazards', 'Hazard data not loaded yet.');
      return;
    }

    const top = [...valid].sort((a, b) => b.score - a.score).slice(0, 3).sort((a, b) => a.lat - b.lat);

    const turnDirs = {};
    for (let i = 0; i < top.length; i++) {
      const h = top[i];
      const jLat = Number.isFinite(h.jLat) ? h.jLat : h.lat;
      const jLon = Number.isFinite(h.jLon) ? h.jLon : h.lon;

      let exitBearing;
      if (i + 1 < top.length) {
        const next = top[i + 1];
        const nextApproach = movePointByMeters(next.lat, next.lon, (next.bearing + 180) % 360, 150);
        exitBearing = bearingBetween(jLat, jLon, nextApproach.latitude, nextApproach.longitude);
      } else {
        exitBearing = h.bearing;
      }

      const rel = ((exitBearing - h.bearing) + 360) % 360;
      turnDirs[h.id] = rel < 180 ? 'right' : 'left';
    }
    simTurnDirectionsRef.current = turnDirs;

    clearCooldowns();
    activeWarningStartRef.current = null;

    const waypoints = [];
    for (const h of top) {
      const jLat = Number.isFinite(h.jLat) ? h.jLat : h.lat;
      const jLon = Number.isFinite(h.jLon) ? h.jLon : h.lon;
      waypoints.push(
        movePointByMeters(h.lat, h.lon, (h.bearing + 180) % 360, 150),
        { latitude: h.lat, longitude: h.lon },
        movePointByMeters(jLat, jLon, h.bearing, 80)
      );
    }

    const steps = interpolateWaypoints(waypoints, 12);
    simWaypointsRef.current = steps;
    simIndexRef.current = 0;
    setSimRoute(steps);
    setSimulating(true);
    setUseFakeLocation(true);
    setFakeLocation(steps[0]);
    jumpToRegion(makeRegion(steps[0].latitude, steps[0].longitude, 0.025));

    simIntervalRef.current = setInterval(() => {
      const idx = simIndexRef.current;
      const all = simWaypointsRef.current;

      if (idx >= all.length) { stopRouteSimulation(); return; }

      const curr = all[idx];
      const prev = idx > 0 ? all[idx - 1] : null;
      const bearing = prev ? bearingBetween(prev.latitude, prev.longitude, curr.latitude, curr.longitude) : null;

      setFakeLocation(curr);
      jumpToRegion(makeRegion(curr.latitude, curr.longitude, 0.015));
      runWarningCheck(curr.latitude, curr.longitude, bearing);
      simIndexRef.current += 1;
    }, 600);
  };

  useEffect(() => {
    let isMounted = true;

    const init = async () => {
      try {
        await initializeHazardService();
        if (isMounted) setHazards(getAllHazards());

        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          if (!isMounted) return;
          setErrorMsg('Location permission denied');
          setLoading(false);
          Alert.alert('Location Required', 'This app needs location access to warn you about dangerous junctions.', [{ text: 'OK' }]);
          return;
        }

        const loc = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        if (!isMounted) return;

        const initial = {
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        };
        setLocation(initial);
        prevCoords.current = { latitude: loc.coords.latitude, longitude: loc.coords.longitude };
        setLoading(false);

        const sub = await Location.watchPositionAsync(
          { accuracy: Location.Accuracy.Balanced, timeInterval: 10000, distanceInterval: 20 },
          (newLoc) => {
            const { latitude, longitude } = newLoc.coords;

            let userBearing = null;
            if (prevCoords.current) {
              const prev = prevCoords.current;
              if (Math.abs(latitude - prev.latitude) > 0.00002 || Math.abs(longitude - prev.longitude) > 0.00002) {
                userBearing = bearingBetween(prev.latitude, prev.longitude, latitude, longitude);
              }
            }
            prevCoords.current = { latitude, longitude };

            const usingFake = useFakeLocationRef.current && !!fakeLocationRef.current;
            const coords = usingFake ? fakeLocationRef.current : { latitude, longitude };
            const bearing = usingFake ? null : userBearing;

            if (coords) runWarningCheck(coords.latitude, coords.longitude, bearing);

            setLocation({ latitude, longitude, latitudeDelta: 0.01, longitudeDelta: 0.01 });
          }
        );

        watchSubRef.current = sub;
      } catch (err) {
        console.error(err);
        if (isMounted) { setErrorMsg('Startup error: ' + err.message); setLoading(false); }
      }
    };

    init();

    return () => {
      isMounted = false;
      if (watchSubRef.current) watchSubRef.current.remove();
      if (bannerTimeoutRef.current) clearTimeout(bannerTimeoutRef.current);
      if (simIntervalRef.current) clearInterval(simIntervalRef.current);
    };
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Loading GPS...</Text>
        <Text style={styles.infoText}>Make sure location services are enabled</Text>
      </View>
    );
  }

  if (errorMsg) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{errorMsg}</Text>
        <Text style={styles.infoText}>Please enable location permissions in settings</Text>
      </View>
    );
  }

  if (!location) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Acquiring GPS signal...</Text>
      </View>
    );
  }

  const visibleLocation = useFakeLocation && fakeLocation ? fakeLocation : location;

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />

      <MapView
        ref={mapRef}
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={location}
        onRegionChangeComplete={(r) => { mapRegionRef.current = r; }}
        showsUserLocation={!useFakeLocation}
        showsMyLocationButton={true}
      >
        {hazards.map(h => (
          <Marker
            key={h.id}
            coordinate={{ latitude: h.lat, longitude: h.lon }}
            title={`${h.type} (${h.score.toFixed(2)})`}
            description={(h.road || 'Unnamed').replace(/[\[\]']/g, '')}
            pinColor={h.score >= 0.7 ? 'red' : 'orange'}
          />
        ))}

        {developerModeOpen && developerEntryLocation && (
          <Marker
            key="entry-location"
            coordinate={developerEntryLocation}
            title="Your Real Location"
            description="Where you were when dev mode opened"
            pinColor="#20bf6b"
          />
        )}

        {useFakeLocation && fakeLocation && (
          <Marker
            key="fake-location"
            coordinate={fakeLocation}
            title="Simulated Position"
            description="Test GPS location"
            pinColor="#2b8aff"
          />
        )}

        {simRoute.length > 0 && (
          <Polyline
            coordinates={simRoute}
            strokeColor="#2b8aff"
            strokeWidth={3}
            lineDashPattern={[6, 4]}
          />
        )}
      </MapView>

      <View style={styles.infoOverlay}>
        <Text style={styles.appTitle}>GPS Mobile App — Driving Safety Abroad</Text>
        <Text style={styles.statusText}>Monitoring for narrow roads joining wider roads</Text>
        <Text style={styles.statusSmall}>
          {useFakeLocation ? 'Simulated GPS' : 'GPS Active'} · {hazards.length} hazard points loaded
        </Text>
      </View>

      {developerModeOpen && (
        <View style={styles.debugPanel}>
          <Text style={styles.debugTitle}>Test Controls</Text>
          <View style={styles.debugRow}>
            <Pressable style={styles.debugBtn} onPress={jumpToOxford}>
              <Text style={styles.debugBtnText}>Jump Oxford</Text>
            </Pressable>
            <Pressable style={styles.debugBtn} onPress={jumpToMyLocation}>
              <Text style={styles.debugBtnText}>Jump My GPS</Text>
            </Pressable>
          </View>
          <View style={styles.debugRow}>
            <Pressable style={styles.debugBtn} onPress={setFakeToHazard}>
              <Text style={styles.debugBtnText}>Random Hazard</Text>
            </Pressable>
            <Pressable
              style={[styles.debugBtn, useFakeLocation && styles.debugBtnActive]}
              onPress={toggleFakeLocationMode}
            >
              <Text style={styles.debugBtnText}>{useFakeLocation ? 'Use Real GPS' : 'Use Fake GPS'}</Text>
            </Pressable>
          </View>
          <View style={styles.debugRow}>
            <Pressable
              style={[styles.debugBtn, simulating ? styles.debugBtnStop : styles.debugBtnSim]}
              onPress={simulating ? stopRouteSimulation : startRouteSimulation}
            >
              <Text style={styles.debugBtnText}>{simulating ? '⏹ Stop' : '▶ Simulate A → B'}</Text>
            </Pressable>
          </View>
          <View style={styles.debugRow}>
            <Pressable style={[styles.debugBtn, styles.backToNormalBtn]} onPress={restoreBeforeDeveloperMode}>
              <Text style={styles.debugBtnText}>Back To Normal</Text>
            </Pressable>
          </View>
        </View>
      )}

      <Pressable
        style={[styles.devModeButton, developerModeOpen && styles.devModeButtonActive]}
        onPress={() => { if (!developerModeOpen) openDeveloperMode(); }}
      >
        <Text style={styles.devModeButtonText}>{developerModeOpen ? 'Developer Mode On' : 'Developer Mode'}</Text>
      </Pressable>

      <WarningBanner hazard={activeWarning} visible={!!activeWarning} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#fff', alignItems: 'center', justifyContent: 'center' },
  map: { width: '100%', height: '100%' },
  infoOverlay: {
    position: 'absolute',
    top: 50,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(255,255,255,0.95)',
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  appTitle: { fontSize: 20, fontWeight: 'bold', color: '#0066cc', marginBottom: 5 },
  statusText: { fontSize: 12, color: '#333', marginBottom: 3 },
  statusSmall: { fontSize: 10, color: '#666', fontStyle: 'italic' },
  debugPanel: {
    position: 'absolute',
    top: 140,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(15,39,66,0.9)',
    borderRadius: 10,
    padding: 10,
  },
  debugTitle: { color: '#fff', fontSize: 12, fontWeight: '700', marginBottom: 8 },
  debugRow: { flexDirection: 'row', marginBottom: 8, justifyContent: 'space-between' },
  debugBtn: {
    flex: 1,
    marginHorizontal: 4,
    backgroundColor: '#1f4d7a',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  debugBtnActive: { backgroundColor: '#0f7b4b' },
  debugBtnSim: { backgroundColor: '#2a6e2a' },
  debugBtnStop: { backgroundColor: '#8e2a2a' },
  backToNormalBtn: { backgroundColor: '#8e2a2a' },
  debugBtnText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  devModeButton: {
    position: 'absolute',
    right: 12,
    bottom: 95,
    backgroundColor: 'rgba(12,34,56,0.92)',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  devModeButtonActive: { backgroundColor: 'rgba(15,110,74,0.95)' },
  devModeButtonText: { color: '#fff', fontSize: 11, fontWeight: '700' },
  loadingText: { fontSize: 18, marginTop: 20, color: '#333' },
  infoText: { fontSize: 14, marginTop: 10, color: '#666', textAlign: 'center', paddingHorizontal: 20 },
  errorText: { fontSize: 16, color: '#cc0000', marginBottom: 10, textAlign: 'center', paddingHorizontal: 20 },
});
