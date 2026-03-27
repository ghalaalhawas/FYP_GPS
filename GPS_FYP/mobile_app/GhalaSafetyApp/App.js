import React, { useState, useEffect, useRef } from 'react';
import { StyleSheet, View, Text, Alert, ActivityIndicator, Vibration, Pressable } from 'react-native';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

import {
  initializeHazardService,
  getAllHazards,
  checkForWarning,
  markWarned,
  getHazardServiceStats,
} from './src/services/hazardService';
import { bearingBetween } from './src/utils/geo';
import WarningBanner from './src/components/WarningBanner';
import SettingsPanel from './src/components/SettingsPanel';
import {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  minScoreForSensitivity,
} from './src/services/settingsService';
import {
  logWarningEvent,
  logLocationSample,
  getEvaluationStats,
  exportEvaluationJson,
  clearEvaluationData,
} from './src/services/evaluationService';

export default function App() {
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeWarning, setActiveWarning] = useState(null);
  const [hazards, setHazards] = useState([]);
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [evalStats, setEvalStats] = useState({
    totalEvents: 0,
    warningEvents: 0,
    locationSamples: 0,
  });
  const [hazardStats, setHazardStats] = useState({
    initialized: false,
    hazardCount: 0,
  });

  const prevCoords = useRef(null);
  const settingsRef = useRef(DEFAULT_SETTINGS);
  const watchSubRef = useRef(null);
  const bannerTimeoutRef = useRef(null);
  const locationLogCounterRef = useRef(0);

  useEffect(() => {
    settingsRef.current = settings;
  }, [settings]);

  useEffect(() => {
    let isMounted = true;

    const boot = async () => {
      try {
        const saved = await loadSettings();
        if (isMounted) {
          setSettings(saved);
          settingsRef.current = saved;
        }

        await initializeHazardService();
        if (isMounted) {
          setHazards(getAllHazards());
          setHazardStats(getHazardServiceStats());
        }

        const stats = await getEvaluationStats();
        if (isMounted) setEvalStats(stats);

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
          async (newLoc) => {
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

            const activeSettings = settingsRef.current;
            const warning = checkForWarning(latitude, longitude, userBearing, {
              proximityRadiusM: activeSettings.proximityRadiusM,
              bearingToleranceDeg: activeSettings.bearingToleranceDeg,
              cooldownMs: activeSettings.cooldownMs,
              minScore: minScoreForSensitivity(activeSettings.alertSensitivity),
            });

            if (warning) {
              markWarned(warning.id);
              setActiveWarning(warning);
              if (activeSettings.vibrationEnabled) Vibration.vibrate(400);

              if (bannerTimeoutRef.current) clearTimeout(bannerTimeoutRef.current);
              bannerTimeoutRef.current = setTimeout(() => setActiveWarning(null), 8000);

              await logWarningEvent({
                hazardId: warning.id,
                hazardScore: warning.score,
                distance: warning.distance,
                userLat: latitude,
                userLon: longitude,
                userBearing,
              });
            }

            locationLogCounterRef.current += 1;
            if (locationLogCounterRef.current % 3 === 0) {
              await logLocationSample({
                userLat: latitude,
                userLon: longitude,
                userBearing,
              });
            }

            const statsAfter = await getEvaluationStats();
            setEvalStats(statsAfter);

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

  const saveSettingsAndClose = async (next) => {
    const saved = await saveSettings(next);
    setSettings(saved);
    setSettingsVisible(false);
  };

  const clearEvaluationAndRefresh = async () => {
    await clearEvaluationData();
    const stats = await getEvaluationStats();
    setEvalStats(stats);
  };

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

  return (
    <View style={styles.container}>
      <StatusBar style="auto" />

      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={location}
        region={location}
        showsUserLocation={true}
        showsMyLocationButton={true}
        followsUserLocation={true}
      >
        {hazards
          .filter((h) => (settings.onlyHighRiskMarkers ? h.score >= 0.7 : true))
          .map((h) => (
          <Marker
            key={h.id}
            coordinate={{ latitude: h.lat, longitude: h.lon }}
            title={`${h.type} (${h.score.toFixed(2)})`}
            description={h.road.replace(/[\[\]']/g, '')}
            pinColor={h.score >= 0.7 ? 'red' : 'orange'}
          />
        ))}
      </MapView>

      {/* Top info bar */}
      <View style={styles.infoOverlay}>
        <Text style={styles.appTitle}>Ghala Safety App</Text>
        <Text style={styles.statusText}>
          GPS Active | {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
        </Text>
        <Text style={styles.versionText}>
          {hazards.length} hazard points loaded | cache: {hazardStats.initialized ? 'yes' : 'no'}
        </Text>
      </View>

      <Pressable style={styles.settingsBtn} onPress={() => setSettingsVisible(true)}>
        <Text style={styles.settingsBtnText}>Settings</Text>
      </Pressable>

      <WarningBanner hazard={activeWarning} visible={!!activeWarning} />

      <SettingsPanel
        visible={settingsVisible}
        settings={settings}
        evalStats={evalStats}
        onClose={() => setSettingsVisible(false)}
        onSave={saveSettingsAndClose}
        onClearEvaluation={clearEvaluationAndRefresh}
        onExportEvaluation={exportEvaluationJson}
      />
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
  settingsBtn: {
    position: 'absolute',
    top: 50,
    right: 10,
    backgroundColor: '#0f2742',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 4,
  },
  settingsBtnText: {
    color: '#fff',
    fontSize: 12,
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
