/**
 * Ghala Safety App - Main Entry Point
 * Week 5 - Hello World with GPS and Map
 * 
 * This is a basic implementation showing:
 * - Map view with user location
 * - GPS location tracking
 * - Sample hazard point display
 * 
 * To run:
 *   npx expo start
 * Then scan QR code with Expo Go app
 */

import React, { useState, useEffect } from 'react';
import { StyleSheet, View, Text, Alert, ActivityIndicator } from 'react-native';
import MapView, { Marker, PROVIDER_DEFAULT } from 'react-native-maps';
import * as Location from 'expo-location';
import { StatusBar } from 'expo-status-bar';

export default function App() {
  const [location, setLocation] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [loading, setLoading] = useState(true);

  // Sample hazard points for Oxford
  const sampleHazards = [
    {
      id: 1,
      latitude: 51.7520,
      longitude: -1.2577,
      title: "Sample Hazard 1",
      description: "T-junction - High risk",
      dangerScore: 0.8
    },
    {
      id: 2,
      latitude: 51.7540,
      longitude: -1.2600,
      title: "Sample Hazard 2",
      description: "Crossroads - Medium risk",
      dangerScore: 0.6
    }
  ];

  useEffect(() => {
    (async () => {
      console.log('🔍 Requesting location permissions...');
      
      // Request location permissions
      let { status } = await Location.requestForegroundPermissionsAsync();
      
      if (status !== 'granted') {
        setErrorMsg('Permission to access location was denied');
        setLoading(false);
        Alert.alert(
          'Location Permission Required',
          'This app needs location access to warn you about dangerous junctions.',
          [{ text: 'OK' }]
        );
        return;
      }

      console.log('✅ Location permissions granted');
      console.log('📍 Getting current location...');

      // Get current location
      try {
        let location = await Location.getCurrentPositionAsync({
          accuracy: Location.Accuracy.High,
        });
        
        setLocation({
          latitude: location.coords.latitude,
          longitude: location.coords.longitude,
          latitudeDelta: 0.01,
          longitudeDelta: 0.01,
        });
        
        console.log('✅ Location obtained:', location.coords.latitude, location.coords.longitude);
        setLoading(false);

        // Start watching location (updates every few seconds)
        Location.watchPositionAsync(
          {
            accuracy: Location.Accuracy.High,
            timeInterval: 5000, // Update every 5 seconds
            distanceInterval: 10, // Or when moved 10 meters
          },
          (newLocation) => {
            console.log('📍 Location update:', newLocation.coords.latitude, newLocation.coords.longitude);
            setLocation({
              latitude: newLocation.coords.latitude,
              longitude: newLocation.coords.longitude,
              latitudeDelta: 0.01,
              longitudeDelta: 0.01,
            });
          }
        );
      } catch (error) {
        console.error('❌ Error getting location:', error);
        setErrorMsg('Error getting location: ' + error.message);
        setLoading(false);
      }
    })();
  }, []);

  // Loading state
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

  // Error state
  if (errorMsg) {
    return (
      <View style={styles.container}>
        <Text style={styles.errorText}>❌ {errorMsg}</Text>
        <Text style={styles.infoText}>
          Please enable location permissions in your device settings
        </Text>
      </View>
    );
  }

  // No location yet
  if (!location) {
    return (
      <View style={styles.container}>
        <ActivityIndicator size="large" color="#0066cc" />
        <Text style={styles.loadingText}>Acquiring GPS signal...</Text>
      </View>
    );
  }

  // Main app view
  return (
    <View style={styles.container}>
      <StatusBar style="auto" />
      
      {/* Map View */}
      <MapView
        style={styles.map}
        provider={PROVIDER_DEFAULT}
        initialRegion={location}
        region={location}
        showsUserLocation={true}
        showsMyLocationButton={true}
        followsUserLocation={true}
      >
        {/* Sample hazard markers */}
        {sampleHazards.map((hazard) => (
          <Marker
            key={hazard.id}
            coordinate={{
              latitude: hazard.latitude,
              longitude: hazard.longitude,
            }}
            title={hazard.title}
            description={hazard.description}
            pinColor={hazard.dangerScore > 0.7 ? 'red' : 'orange'}
          />
        ))}
      </MapView>

      {/* Info overlay */}
      <View style={styles.infoOverlay}>
        <Text style={styles.appTitle}>🚗 Ghala Safety App</Text>
        <Text style={styles.statusText}>
          ✅ GPS Active | 📍 Location: {location.latitude.toFixed(5)}, {location.longitude.toFixed(5)}
        </Text>
        <Text style={styles.versionText}>
          Week 5 - Hello World | v1.0.0
        </Text>
      </View>

      {/* Sample warning overlay (for demonstration) */}
      <View style={styles.warningPreview}>
        <Text style={styles.warningText}>ℹ️ Sample hazard markers shown</Text>
        <Text style={styles.warningSubtext}>Red = High risk | Orange = Medium risk</Text>
      </View>
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
  warningPreview: {
    position: 'absolute',
    bottom: 30,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.95)',
    padding: 12,
    borderRadius: 8,
    borderLeftWidth: 4,
    borderLeftColor: '#0066cc',
  },
  warningText: {
    fontSize: 14,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 3,
  },
  warningSubtext: {
    fontSize: 12,
    color: '#666',
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
