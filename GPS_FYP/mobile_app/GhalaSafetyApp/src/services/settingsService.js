import AsyncStorage from '@react-native-async-storage/async-storage';

const SETTINGS_KEY = 'ghala_settings_v1';

const DEFAULT_SETTINGS = {
  alertSensitivity: 'normal',
  proximityRadiusM: 300,
  bearingToleranceDeg: 60,
  cooldownMs: 60000,
  vibrationEnabled: true,
  onlyHighRiskMarkers: false,
};

async function loadSettings() {
  try {
    const raw = await AsyncStorage.getItem(SETTINGS_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch (error) {
    console.warn('Failed to load settings:', error);
    return { ...DEFAULT_SETTINGS };
  }
}

async function saveSettings(nextSettings) {
  const merged = { ...DEFAULT_SETTINGS, ...nextSettings };
  await AsyncStorage.setItem(SETTINGS_KEY, JSON.stringify(merged));
  return merged;
}

function minScoreForSensitivity(level) {
  if (level === 'low') return 0.45;
  if (level === 'high') return 0.25;
  return 0.35;
}

export {
  DEFAULT_SETTINGS,
  loadSettings,
  saveSettings,
  minScoreForSensitivity,
};
