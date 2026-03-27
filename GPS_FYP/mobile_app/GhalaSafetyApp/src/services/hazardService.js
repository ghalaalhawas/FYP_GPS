import AsyncStorage from '@react-native-async-storage/async-storage';
import RBush from 'rbush';
import { haversine, angleDiff } from '../utils/geo';

import bundledHazards from '../../assets/data/oxford_uk_hazard_mobile_sample50.json';

const HAZARD_CACHE_KEY = 'ghala_hazard_cache_v1';

const PROXIMITY_RADIUS_M = 300;
const BEARING_TOLERANCE_DEG = 60;
const COOLDOWN_MS = 60000;

const cooldowns = {};

let hazards = [];
let hazardTree = null;
let isInitialized = false;

function normalizeHazard(raw, idx) {
  return {
    ...raw,
    id: raw.id ?? idx + 1,
    lat: Number(raw.lat),
    lon: Number(raw.lon),
    score: Number(raw.score ?? 0),
    bearing: raw.bearing == null ? null : Number(raw.bearing),
  };
}

function buildSpatialIndex(list) {
  const tree = new RBush();
  const entries = list.map((h) => ({
    minX: h.lon,
    minY: h.lat,
    maxX: h.lon,
    maxY: h.lat,
    hazard: h,
  }));
  tree.load(entries);
  return tree;
}

function metersToLat(radiusM) {
  return radiusM / 111320;
}

function metersToLon(radiusM, lat) {
  const cos = Math.cos((lat * Math.PI) / 180);
  const safeCos = Math.max(cos, 0.0001);
  return radiusM / (111320 * safeCos);
}

async function initializeHazardService() {
  try {
    const cached = await AsyncStorage.getItem(HAZARD_CACHE_KEY);
    if (cached) {
      const parsed = JSON.parse(cached);
      if (Array.isArray(parsed) && parsed.length > 0) {
        hazards = parsed.map(normalizeHazard);
      }
    }
  } catch (error) {
    console.warn('Failed to load hazard cache:', error);
  }

  if (hazards.length === 0) {
    hazards = bundledHazards.map(normalizeHazard);
  }

  hazardTree = buildSpatialIndex(hazards);
  isInitialized = true;

  try {
    await AsyncStorage.setItem(HAZARD_CACHE_KEY, JSON.stringify(hazards));
  } catch (error) {
    console.warn('Failed to save hazard cache:', error);
  }

  return hazards;
}

function getAllHazards() {
  return isInitialized ? hazards : bundledHazards;
}

function findNearby(userLat, userLon, radiusM = PROXIMITY_RADIUS_M) {
  const source = isInitialized ? hazards : bundledHazards;
  const latPad = metersToLat(radiusM);
  const lonPad = metersToLon(radiusM, userLat);

  let candidates = source;
  if (hazardTree) {
    candidates = hazardTree
      .search({
        minX: userLon - lonPad,
        minY: userLat - latPad,
        maxX: userLon + lonPad,
        maxY: userLat + latPad,
      })
      .map((entry) => entry.hazard);
  }

  const nearby = [];
  for (const h of candidates) {
    const dist = haversine(userLat, userLon, h.lat, h.lon);
    if (dist <= radiusM) {
      nearby.push({ ...h, distance: Math.round(dist) });
    }
  }
  nearby.sort((a, b) => a.distance - b.distance);
  return nearby;
}

function isApproaching(userBearing, hazard, toleranceDeg = BEARING_TOLERANCE_DEG) {
  if (userBearing == null || hazard.bearing == null) return true;
  return angleDiff(userBearing, hazard.bearing) <= toleranceDeg;
}

function isCooldownClear(hazardId, cooldownMs = COOLDOWN_MS) {
  const last = cooldowns[hazardId];
  if (!last) return true;
  return Date.now() - last > cooldownMs;
}

function markWarned(hazardId) {
  cooldowns[hazardId] = Date.now();
}

function checkForWarning(userLat, userLon, userBearing, options = {}) {
  const radiusM = options.proximityRadiusM ?? PROXIMITY_RADIUS_M;
  const toleranceDeg = options.bearingToleranceDeg ?? BEARING_TOLERANCE_DEG;
  const cooldownMs = options.cooldownMs ?? COOLDOWN_MS;
  const minScore = options.minScore ?? 0.0;

  const nearby = findNearby(userLat, userLon, radiusM);

  for (const h of nearby) {
    if (h.score < minScore) continue;
    if (!isCooldownClear(h.id, cooldownMs)) continue;
    if (!isApproaching(userBearing, h, toleranceDeg)) continue;
    return h;
  }
  return null;
}

function getHazardServiceStats() {
  return {
    initialized: isInitialized,
    hazardCount: hazards.length,
    cacheKey: HAZARD_CACHE_KEY,
  };
}

export {
  initializeHazardService,
  getAllHazards,
  findNearby,
  checkForWarning,
  markWarned,
  getHazardServiceStats,
  PROXIMITY_RADIUS_M,
  COOLDOWN_MS,
};
