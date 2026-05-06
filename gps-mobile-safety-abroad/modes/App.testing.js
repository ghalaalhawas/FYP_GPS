import React, { useEffect, useRef, useState } from 'react';
import { ActivityIndicator, Alert, Pressable, StyleSheet, Text, Vibration, View } from 'react-native';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

import { initializeHazardService, getAllHazards, checkForWarning, markWarned } from './src/services/hazardService';
import { bearingBetween } from './src/utils/geo';
import WarningBanner from './src/components/WarningBanner';

const OXFORD_REGION = {
  latitude: 51.752,
  longitude: -1.2577,
  latitudeDelta: 0.12,
  longitudeDelta: 0.12,
};
const EARTH_RADIUS_M = 6371000;

function makeRegion(latitude, longitude, delta = 0.01) {
  return {
    latitude,
    longitude,
    latitudeDelta: delta,
    longitudeDelta: delta,
  };
}

function movePointByMeters(lat, lon, bearingDeg, distanceM) {
  const latRad = (lat * Math.PI) / 180;
  const lonRad = (lon * Math.PI) / 180;
  const bearingRad = (bearingDeg * Math.PI) / 180;
  const angularDistance = distanceM / EARTH_RADIUS_M;

  const newLatRad = Math.asin(
    Math.sin(latRad) * Math.cos(angularDistance) +
      Math.cos(latRad) * Math.sin(angularDistance) * Math.cos(bearingRad)
  );

  const newLonRad =
    lonRad +
    Math.atan2(
      Math.sin(bearingRad) * Math.sin(angularDistance) * Math.cos(latRad),
      Math.cos(angularDistance) - Math.sin(latRad) * Math.sin(newLatRad)
    );

  return {
    latitude: (newLatRad * 180) / Math.PI,
    longitude: (newLonRad * 180) / Math.PI,
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

  const mapRef = useRef(null);
  const mapRegionRef = useRef(null);
  const prevCoords = useRef(null);
  const watchSubRef = useRef(null);
  const bannerTimeoutRef = useRef(null);
  const fakeLocationRef = useRef(null);
  const useFakeLocationRef = useRef(false);
  const lastFakeHazardIdRef = useRef(null);
  const developerSnapshotRef = useRef(null);

  useEffect(() => {
    fakeLocationRef.current = fakeLocation;
  }, [fakeLocation]);

  useEffect(() => {
    useFakeLocationRef.current = useFakeLocation;
  }, [useFakeLocation]);

  const runWarningCheck = (latitude, longitude, userBearing = null) => {
    const warning = checkForWarning(latitude, longitude, userBearing);
    if (!warning) return;

    markWarned(warning.id);
    setActiveWarning(warning);
    Vibration.vibrate(400);

    if (bannerTimeoutRef.current) clearTimeout(bannerTimeoutRef.current);
    bannerTimeoutRef.current = setTimeout(() => setActiveWarning(null), 8000);
  };

  const jumpToRegion = (region) => {
    if (!mapRef.current) return;
    mapRef.current.animateToRegion(region, 700);
  };

  const jumpToOxford = () => {
    jumpToRegion(OXFORD_REGION);
  };

  const jumpToMyLocation = () => {
    if (!location) return;
    jumpToRegion(location);
  };

  const openDeveloperMode = () => {
    developerSnapshotRef.current = {
      useFakeLocation: useFakeLocationRef.current,
      fakeLocation: fakeLocationRef.current,
      region: mapRegionRef.current || location || null,
    };

    if (location) {
      setDeveloperEntryLocation({
        latitude: location.latitude,
        longitude: location.longitude,
      });
    } else {
      setDeveloperEntryLocation(null);
    }

    setDeveloperModeOpen(true);
  };

  const restoreBeforeDeveloperMode = () => {
    const snapshot = developerSnapshotRef.current;

    if (snapshot) {
      setUseFakeLocation(!!snapshot.useFakeLocation);
      setFakeLocation(snapshot.fakeLocation ?? null);

      if (snapshot.region) {
        jumpToRegion(snapshot.region);
      }
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
      .filter((h) => Number.isFinite(h.lat) && Number.isFinite(h.lon))
      .sort((a, b) => b.score - a.score);

    if (!candidates.length) {
      Alert.alert('No valid hazards', 'Hazard list did not include valid coordinates.');
      return;
    }

    let pool = candidates;
    if (candidates.length > 1 && lastFakeHazardIdRef.current != null) {
      const filtered = candidates.filter((h) => h.id !== lastFakeHazardIdRef.current);
      if (filtered.length > 0) {
        pool = filtered;
      }
    }

    const idx = Math.floor(Math.random() * pool.length);
    const best = pool[idx];
    lastFakeHazardIdRef.current = best.id;

    // Put the simulated user a random distance BEFORE the hazard point
    // so warnings display meaningful non-zero "ahead" values.
    const randomAheadMeters = 20 + Math.floor(Math.random() * 81); // 20-100m
    const backwardBearing = Number.isFinite(best.bearing)
      ? (best.bearing + 180) % 360
      : Math.floor(Math.random() * 360);

    const nextFake = movePointByMeters(best.lat, best.lon, backwardBearing, randomAheadMeters);

    setFakeLocation(nextFake);
    setUseFakeLocation(true);
    jumpToRegion(makeRegion(nextFake.latitude, nextFake.longitude, 0.02));
    runWarningCheck(nextFake.latitude, nextFake.longitude, null);
  };

  const toggleFakeLocationMode = () => {
    if (useFakeLocation) {
      setUseFakeLocation(false);
      return;
    }

    if (!fakeLocation) {
      setFakeToHazard();
      return;
    }

    setUseFakeLocation(true);
    jumpToRegion(makeRegion(fakeLocation.latitude, fakeLocation.longitude, 0.02));
    runWarningCheck(fakeLocation.latitude, fakeLocation.longitude, null);
  };

  useEffect(() => {
    let isMounted = true;

    const boot = async () => {
      try {
        await initializeHazardService();
        if (isMounted) {
          setHazards(getAllHazards());
        }

        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted') {
          if (!isMounted) return;
          setErrorMsg('Permission to access location was denied');
          setLoading(false);
          Alert.alert(
            'Location Permission Required',
            'This app needs location access to warn you about dangerous junctions.',
            [{ text: 'OK' }]
          );
          return;
        }

        const loc = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.Balanced,
        });

        if (!isMounted) return;

        const initial = {
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        };
        setLocation(initial);
        prevCoords.current = {
          latitude: loc.coords.latitude,
          longitude: loc.coords.longitude,
        };
        setLoading(false);

        const subscription = await Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.Balanced,
            timeInterval: 10000,
            distanceInterval: 20,
          },
          (newLoc) => {
            const { latitude, longitude } = newLoc.coords;

            let userBearing = null;
            if (prevCoords.current) {
              const prev = prevCoords.current;
              const dlat = latitude - prev.latitude;
              const dlon = longitude - prev.longitude;
              if (Math.abs(dlat) > 0.00002 || Math.abs(dlon) > 0.00002) {
                userBearing = bearingBetween(prev.latitude, prev.longitude, latitude, longitude);
              }
            }
            prevCoords.current = { latitude, longitude };

            const shouldUseFake = useFakeLocationRef.current && !!fakeLocationRef.current;
            const activeCoords = shouldUseFake
              ? fakeLocationRef.current
              : { latitude, longitude };
            const activeBearing = shouldUseFake ? null : userBearing;

            if (activeCoords) {
              runWarningCheck(activeCoords.latitude, activeCoords.longitude, activeBearing);
            }

            setLocation({
              latitude,
              longitude,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            });
          }
        );

        watchSubRef.current = subscription;
      } catch (error) {
        console.error('Startup error:', error);
        if (isMounted) {
          setErrorMsg('Startup error: ' + error.message);
          setLoading(false);
        }
      }
    };

    boot();

    return () => {
      isMounted = false;
      if (watchSubRef.current) {
        watchSubRef.current.remove();
      }
      if (bannerTimeoutRef.current) {
        clearTimeout(bannerTimeoutRef.current);
      }
    };
  }, []);

  if (loading) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Loading GPS...</Text>
        <Text style={styles.infoText}>
          Make sure location services are enabled on your device
        </Text>
      </View>
    );
  }

  if (errorMsg) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>{errorMsg}</Text>
        <Text style={styles.infoText}>
          Please enable location permissions in your device settings
        </Text>
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
        onRegionChangeComplete={(region) => {
          mapRegionRef.current = region;
        }}
        showsUserLocation={!useFakeLocation}
        showsMyLocationButton={true}
      >
        {hazards.map((hazard) => (
          <Marker
            key={hazard.id}
            coordinate={{ latitude: hazard.lat, longitude: hazard.lon }}
            title={`${hazard.type} (${hazard.score.toFixed(2)})`}
            description={(hazard.road || 'Unnamed').replace(/[\[\]']/g, '')}
            pinColor={hazard.score >= 0.7 ? 'red' : 'orange'}
          />
        ))}
        {developerModeOpen && developerEntryLocation ? (
          <Marker
            key="developer-entry-location"
            coordinate={{
              latitude: developerEntryLocation.latitude,
              longitude: developerEntryLocation.longitude,
            }}
            title="Your Real Location"
            description="Captured when Developer Mode opened"
            pinColor="#20bf6b"
          />
        ) : null}
        {useFakeLocation && fakeLocation ? (
          <Marker
            key="fake-user-location"
            coordinate={{
              latitude: fakeLocation.latitude,
              longitude: fakeLocation.longitude,
            }}
            title="Simulated User"
            description="Debug fake GPS location"
            pinColor="#2b8aff"
          />
        ) : null}
      </MapView>

      <View style={styles.infoOverlay}>
        <Text style={styles.appTitle}>GPS Mobile app to help driving safety abroad</Text>
        <Text style={styles.statusText}>
          {useFakeLocation ? 'Fake GPS Active' : 'GPS Active'} | {visibleLocation.latitude.toFixed(5)}, {visibleLocation.longitude.toFixed(5)}
        </Text>
        <Text style={styles.versionText}>
          {hazards.length} hazard points loaded
        </Text>
      </View>

      {developerModeOpen ? (
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
              <Text style={styles.debugBtnText}>Random Fake Hazard</Text>
            </Pressable>
            <Pressable
              style={[styles.debugBtn, useFakeLocation ? styles.debugBtnActive : null]}
              onPress={toggleFakeLocationMode}
            >
              <Text style={styles.debugBtnText}>{useFakeLocation ? 'Use Real GPS' : 'Use Fake GPS'}</Text>
            </Pressable>
          </View>
          <View style={styles.debugRow}>
            <Pressable style={[styles.debugBtn, styles.backToNormalBtn]} onPress={restoreBeforeDeveloperMode}>
              <Text style={styles.debugBtnText}>Back To Normal</Text>
            </Pressable>
          </View>
        </View>
      ) : null}

      <Pressable
        style={[styles.devModeButton, developerModeOpen ? styles.devModeButtonActive : null]}
        onPress={() => {
          if (!developerModeOpen) {
            openDeveloperMode();
          }
        }}
      >
        <Text style={styles.devModeButtonText}>{developerModeOpen ? 'Developer Mode On' : 'Developer Mode'}</Text>
      </Pressable>

      <WarningBanner hazard={activeWarning} visible={!!activeWarning} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
    alignItems: 'center',
    justifyContent: 'center',
  },
  map: {
    width: '100%',
    height: '100%',
  },
  infoOverlay: {
    position: 'absolute',
    top: 50,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    padding: 15,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.25,
    shadowRadius: 3.84,
    elevation: 5,
  },
  appTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#0066cc',
    marginBottom: 5,
  },
  statusText: {
    fontSize: 12,
    color: '#333',
    marginBottom: 3,
  },
  versionText: {
    fontSize: 10,
    color: '#666',
    fontStyle: 'italic',
  },
  debugPanel: {
    position: 'absolute',
    top: 140,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(15, 39, 66, 0.9)',
    borderRadius: 10,
    padding: 10,
  },
  debugTitle: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '700',
    marginBottom: 8,
  },
  debugRow: {
    flexDirection: 'row',
    marginBottom: 8,
    justifyContent: 'space-between',
  },
  debugBtn: {
    flex: 1,
    marginHorizontal: 4,
    backgroundColor: '#1f4d7a',
    borderRadius: 8,
    paddingVertical: 8,
    alignItems: 'center',
  },
  debugBtnActive: {
    backgroundColor: '#0f7b4b',
  },
  backToNormalBtn: {
    backgroundColor: '#8e2a2a',
  },
  debugBtnText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  devModeButton: {
    position: 'absolute',
    right: 12,
    bottom: 95,
    backgroundColor: 'rgba(12, 34, 56, 0.92)',
    borderRadius: 999,
    paddingHorizontal: 12,
    paddingVertical: 8,
  },
  devModeButtonActive: {
    backgroundColor: 'rgba(15, 110, 74, 0.95)',
  },
  devModeButtonText: {
    color: '#fff',
    fontSize: 11,
    fontWeight: '700',
  },
  loadingText: {
    fontSize: 18,
    marginTop: 20,
    color: '#333',
  },
  infoText: {
    fontSize: 14,
    marginTop: 10,
    color: '#666',
    textAlign: 'center',
    paddingHorizontal: 20,
  },
  errorText: {
    fontSize: 16,
    color: '#cc0000',
    marginBottom: 10,
    textAlign: 'center',
    paddingHorizontal: 20,
  },
});
