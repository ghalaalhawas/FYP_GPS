import React from 'react';
import { StyleSheet, Text, View } from 'react-native';

export default function WarningBanner({ hazard, visible }) {
  if (!visible || !hazard) return null;

  const isHigh = hazard.score >= 0.7;
  const accentColor = isHigh ? '#cc0000' : '#e68a00';
  const urgency = isHigh ? 'HIGH RISK' : 'CAUTION';
  const road = (hazard.road || 'Unnamed road').replace(/[\[\]']/g, '');

  const turnDir = hazard.turnDirection;
  const dirLabel = turnDir === 'right' ? 'KEEP RIGHT ►' : '◄ KEEP LEFT';
  const dirSub =
    turnDir === 'right'
      ? 'Bear right — stay on the right side when joining'
      : 'Bear left — stay on the left side when joining';

  return (
    <View style={[styles.banner, { borderLeftColor: accentColor }]}>
      <View style={styles.headerRow}>
        <Text style={[styles.label, { color: accentColor }]}>{urgency}</Text>
        <View style={[styles.dirBadge, { backgroundColor: accentColor }]}>
          <Text style={styles.dirText}>{dirLabel}</Text>
        </View>
      </View>
      <Text style={styles.title}>
        Narrow road joining wider road in {hazard.distance}m
      </Text>
      <Text style={styles.detail}>
        {dirSub}{road !== 'Unnamed road' ? ` — ${road}` : ''}
      </Text>
      <Text style={styles.sub}>
        {hazard.type} · danger score: {hazard.score.toFixed(2)}
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
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 4,
  },
  label: {
    fontSize: 13,
    fontWeight: 'bold',
    letterSpacing: 1,
  },
  dirBadge: {
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 3,
  },
  dirText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: 'bold',
    letterSpacing: 0.5,
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
  sub: {
    fontSize: 12,
    color: '#888',
    marginTop: 1,
  },
});
