// WarningBanner.js - slides in from the bottom when a hazard is nearby

import React from 'react';
import { View, Text, StyleSheet, Animated } from 'react-native';

export default function WarningBanner({ hazard, visible }) {
  if (!visible || !hazard) return null;

  const isHigh = hazard.score >= 0.7;
  const accentColor = isHigh ? '#cc0000' : '#e68a00';
  const label = isHigh ? 'HIGH RISK' : 'CAUTION';

  return (
    <View style={[styles.banner, { borderLeftColor: accentColor }]}>  
      <Text style={[styles.label, { color: accentColor }]}>{label}</Text>
      <Text style={styles.title}>
        {hazard.type} ahead — {hazard.distance}m
      </Text>
      <Text style={styles.detail}>
        {hazard.road !== "['Unnamed']" ? hazard.road.replace(/[\[\]']/g, '') : 'Unnamed road'} ({hazard.roadType.replace(/[\[\]']/g, '')})
      </Text>
      <Text style={styles.score}>
        Danger score: {hazard.score.toFixed(2)}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    position: 'absolute',
    bottom: 30,
    left: 10,
    right: 10,
    backgroundColor: 'rgba(255, 255, 255, 0.97)',
    padding: 14,
    borderRadius: 10,
    borderLeftWidth: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
    elevation: 6,
  },
  label: {
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 1,
    marginBottom: 2,
  },
  title: {
    fontSize: 17,
    fontWeight: 'bold',
    color: '#222',
    marginBottom: 3,
  },
  detail: {
    fontSize: 13,
    color: '#555',
    marginBottom: 2,
  },
  score: {
    fontSize: 12,
    color: '#888',
  },
});
