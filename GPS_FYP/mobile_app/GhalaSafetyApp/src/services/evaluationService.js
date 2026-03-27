import AsyncStorage from '@react-native-async-storage/async-storage';

const EVAL_KEY = 'ghala_eval_events_v1';
const MAX_EVENTS = 2500;

async function readEvents() {
  try {
    const raw = await AsyncStorage.getItem(EVAL_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn('Failed to read evaluation events:', error);
    return [];
  }
}

async function writeEvents(events) {
  await AsyncStorage.setItem(EVAL_KEY, JSON.stringify(events.slice(-MAX_EVENTS)));
}

async function logWarningEvent(event) {
  const events = await readEvents();
  events.push({ type: 'warning', ts: Date.now(), ...event });
  await writeEvents(events);
}

async function logLocationSample(sample) {
  const events = await readEvents();
  events.push({ type: 'location', ts: Date.now(), ...sample });
  await writeEvents(events);
}

async function getEvaluationStats() {
  const events = await readEvents();
  const warnings = events.filter((e) => e.type === 'warning').length;
  const locations = events.filter((e) => e.type === 'location').length;
  return {
    totalEvents: events.length,
    warningEvents: warnings,
    locationSamples: locations,
  };
}

async function exportEvaluationJson() {
  const events = await readEvents();
  return JSON.stringify(events, null, 2);
}

async function clearEvaluationData() {
  await AsyncStorage.removeItem(EVAL_KEY);
}

export {
  logWarningEvent,
  logLocationSample,
  getEvaluationStats,
  exportEvaluationJson,
  clearEvaluationData,
};
