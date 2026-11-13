import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeInDown, FadeOutDown } from 'react-native-reanimated';

import { hasAdjustments, type UiGrade } from '../../lib/grade';
import { lookName, useApp } from '../../state/app';
import { useLibrary } from '../../state/library';
import { palette, radius } from '../../theme/tokens';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { toast } from '../../ui/Toast';
import { AdjustPanel } from '../shared/AdjustPanel';
import { LookStrip } from '../shared/LookStrip';

type Props = {
  grade: UiGrade;
  onChange: (patch: Partial<UiGrade>) => void;
  note?: string | null;
};

/** Looks and manual grading over the live preview. */
export function LookDrawer({ grade, onChange, note }: Props) {
  const looks = useApp((s) => s.looks);
  const presets = useLibrary((s) => s.presets);
  const addPreset = useLibrary((s) => s.addPreset);
  const [tab, setTab] = useState<'looks' | 'adjust'>('looks');
  const [presetId, setPresetId] = useState<string | null>(null);

  const title = presetId ? presets.find((p) => p.id === presetId)?.name ?? lookName(looks, grade.look) : lookName(looks, grade.look);

  return (
    <Animated.View entering={FadeInDown.duration(200)} exiting={FadeOutDown.duration(160)} style={styles.root}>
      <View style={styles.head}>
        <View style={styles.tabs}>
          {(['looks', 'adjust'] as const).map((t) => (
            <Tap key={t} haptic="selection" onPress={() => setTab(t)} style={styles.tab}>
              <T variant="label" color={tab === t ? palette.ink : palette.ash}>
                {t === 'looks' ? 'Looks' : 'Adjust'}
              </T>
            </Tap>
          ))}
        </View>
        <T variant="label" color={palette.ash} numberOfLines={1} style={styles.title}>
          {title}
        </T>
        {tab === 'adjust' && hasAdjustments(grade.adj) ? (
          <View style={styles.actions}>
            <Tap
              haptic="light"
              onPress={() => {
                const p = addPreset(`Preset ${presets.length + 1}`, grade);
                setPresetId(p.id);
                toast(`Saved as ${p.name}`);
              }}
              style={styles.action}
            >
              <T variant="label" color={palette.ink}>
                Save
              </T>
            </Tap>
            <Tap haptic="light" onPress={() => onChange({ adj: {} })} style={styles.action}>
              <T variant="label" color={palette.ink}>
                Reset
              </T>
            </Tap>
          </View>
        ) : null}
      </View>
      {note ? (
        <T variant="caption" color={palette.ash} style={styles.note}>
          {note}
        </T>
      ) : null}
      {tab === 'looks' ? (
        <>
          <LookStrip
            looks={looks}
            presets={presets}
            selected={grade.look}
            selectedPreset={presetId}
            onSelect={(id) => {
              setPresetId(null);
              onChange({ look: id });
            }}
            onPreset={(p) => {
              setPresetId(p.id);
              onChange({ look: p.grade.look, intensity: p.grade.intensity, adj: p.grade.adj });
            }}
          />
          {grade.look !== 'none' ? (
            <View style={styles.intensity}>
              <Ruler min={0} max={100} step={1} value={grade.intensity} onChange={(v) => onChange({ intensity: v })} format={(v) => `${v}%`} majorEvery={10} spacing={4} reference={100} />
            </View>
          ) : null}
        </>
      ) : (
        <AdjustPanel adj={grade.adj} onChange={(k, v) => onChange({ adj: { ...grade.adj, [k]: v } })} />
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: {
    backgroundColor: 'rgba(21,20,19,0.94)',
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingTop: 6,
    paddingBottom: 8,
  },
  head: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: 8, height: 40 },
  tabs: { flexDirection: 'row' },
  tab: { paddingHorizontal: 10, paddingVertical: 8 },
  title: { flex: 1, textAlign: 'right', paddingHorizontal: 8 },
  actions: { flexDirection: 'row' },
  action: { paddingHorizontal: 10, paddingVertical: 8 },
  note: { paddingHorizontal: 18, paddingBottom: 6 },
  intensity: { paddingHorizontal: 16, paddingTop: 6 },
});
