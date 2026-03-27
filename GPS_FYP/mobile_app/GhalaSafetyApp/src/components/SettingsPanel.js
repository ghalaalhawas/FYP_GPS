import React, { useEffect, useState } from 'react';
import {
  Modal,
  View,
  Text,
  StyleSheet,
  Pressable,
  TextInput,
  Switch,
  ScrollView,
  Alert,
} from 'react-native';

export default function SettingsPanel({
  visible,
  settings,
  evalStats,
  onClose,
  onSave,
  onClearEvaluation,
  onExportEvaluation,
}) {
  const [draft, setDraft] = useState(settings);

  useEffect(() => {
    setDraft(settings);
  }, [settings, visible]);

  const updateField = (key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  };

  const save = () => {
    onSave({
      ...draft,
      proximityRadiusM: Number(draft.proximityRadiusM) || 300,
      bearingToleranceDeg: Number(draft.bearingToleranceDeg) || 60,
      cooldownMs: Number(draft.cooldownMs) || 60000,
    });
  };

  const exportLogs = async () => {
    const json = await onExportEvaluation();
    Alert.alert(
      'Evaluation Export',
      `Exported ${json.length.toLocaleString()} characters. You can print this in console or wire file export next.`
    );
  };

  return (
    <Modal visible={visible} transparent animationType="slide" onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.sheet}>
          <Text style={styles.title}>Settings & Evaluation</Text>

          <ScrollView style={styles.scroll}>
            <Text style={styles.label}>Alert sensitivity</Text>
            <View style={styles.rowButtons}>
              {['low', 'normal', 'high'].map((level) => (
                <Pressable
                  key={level}
                  onPress={() => updateField('alertSensitivity', level)}
                  style={[
                    styles.pill,
                    draft.alertSensitivity === level && styles.pillActive,
                  ]}
                >
                  <Text
                    style={[
                      styles.pillText,
                      draft.alertSensitivity === level && styles.pillTextActive,
                    ]}
                  >
                    {level.toUpperCase()}
                  </Text>
                </Pressable>
              ))}
            </View>

            <Text style={styles.label}>Proximity radius (m)</Text>
            <TextInput
              value={String(draft.proximityRadiusM)}
              keyboardType="numeric"
              style={styles.input}
              onChangeText={(v) => updateField('proximityRadiusM', v)}
            />

            <Text style={styles.label}>Bearing tolerance (deg)</Text>
            <TextInput
              value={String(draft.bearingToleranceDeg)}
              keyboardType="numeric"
              style={styles.input}
              onChangeText={(v) => updateField('bearingToleranceDeg', v)}
            />

            <Text style={styles.label}>Warning cooldown (ms)</Text>
            <TextInput
              value={String(draft.cooldownMs)}
              keyboardType="numeric"
              style={styles.input}
              onChangeText={(v) => updateField('cooldownMs', v)}
            />

            <View style={styles.switchRow}>
              <Text style={styles.switchLabel}>Vibration enabled</Text>
              <Switch
                value={!!draft.vibrationEnabled}
                onValueChange={(v) => updateField('vibrationEnabled', v)}
              />
            </View>

            <View style={styles.switchRow}>
              <Text style={styles.switchLabel}>Only show high-risk markers</Text>
              <Switch
                value={!!draft.onlyHighRiskMarkers}
                onValueChange={(v) => updateField('onlyHighRiskMarkers', v)}
              />
            </View>

            <View style={styles.evalBox}>
              <Text style={styles.evalTitle}>Evaluation snapshot</Text>
              <Text style={styles.evalText}>Total events: {evalStats.totalEvents}</Text>
              <Text style={styles.evalText}>Warnings: {evalStats.warningEvents}</Text>
              <Text style={styles.evalText}>Location samples: {evalStats.locationSamples}</Text>
            </View>

            <Pressable style={styles.secondaryBtn} onPress={exportLogs}>
              <Text style={styles.secondaryBtnText}>Export evaluation JSON</Text>
            </Pressable>

            <Pressable style={styles.dangerBtn} onPress={onClearEvaluation}>
              <Text style={styles.dangerBtnText}>Clear evaluation logs</Text>
            </Pressable>
          </ScrollView>

          <View style={styles.footer}>
            <Pressable style={styles.cancelBtn} onPress={onClose}>
              <Text style={styles.cancelBtnText}>Close</Text>
            </Pressable>
            <Pressable style={styles.saveBtn} onPress={save}>
              <Text style={styles.saveBtnText}>Save</Text>
            </Pressable>
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.45)',
    justifyContent: 'flex-end',
  },
  sheet: {
    maxHeight: '86%',
    backgroundColor: '#fff',
    borderTopLeftRadius: 18,
    borderTopRightRadius: 18,
    paddingTop: 14,
    paddingHorizontal: 14,
    paddingBottom: 18,
  },
  title: {
    fontSize: 18,
    fontWeight: '700',
    color: '#0f2742',
    marginBottom: 10,
  },
  scroll: {
    maxHeight: '80%',
  },
  label: {
    marginTop: 10,
    marginBottom: 6,
    color: '#2f3f4e',
    fontSize: 13,
    fontWeight: '600',
  },
  input: {
    borderWidth: 1,
    borderColor: '#c7d0d9',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 9,
    color: '#15202b',
  },
  rowButtons: {
    flexDirection: 'row',
    gap: 8,
  },
  pill: {
    borderWidth: 1,
    borderColor: '#9fb1c3',
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: '#f5f8fb',
  },
  pillActive: {
    backgroundColor: '#0d6efd',
    borderColor: '#0d6efd',
  },
  pillText: {
    fontSize: 11,
    color: '#38516a',
    fontWeight: '700',
  },
  pillTextActive: {
    color: '#fff',
  },
  switchRow: {
    marginTop: 12,
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  switchLabel: {
    color: '#273848',
    fontSize: 14,
  },
  evalBox: {
    marginTop: 14,
    borderWidth: 1,
    borderColor: '#d5dde5',
    borderRadius: 12,
    padding: 10,
    backgroundColor: '#f8fbff',
  },
  evalTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: '#1f4469',
    marginBottom: 6,
  },
  evalText: {
    fontSize: 12,
    color: '#3d4d5d',
    marginBottom: 2,
  },
  secondaryBtn: {
    marginTop: 10,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#6f8297',
    alignItems: 'center',
  },
  secondaryBtnText: {
    color: '#2d4c6a',
    fontWeight: '700',
  },
  dangerBtn: {
    marginTop: 8,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#b43d3d',
    alignItems: 'center',
  },
  dangerBtnText: {
    color: '#9b1f1f',
    fontWeight: '700',
  },
  footer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 14,
  },
  cancelBtn: {
    flex: 1,
    marginRight: 8,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: '#92a4b4',
    paddingVertical: 12,
    alignItems: 'center',
  },
  cancelBtnText: {
    color: '#455b70',
    fontWeight: '700',
  },
  saveBtn: {
    flex: 1,
    marginLeft: 8,
    borderRadius: 10,
    backgroundColor: '#0d6efd',
    paddingVertical: 12,
    alignItems: 'center',
  },
  saveBtnText: {
    color: '#fff',
    fontWeight: '700',
  },
});
