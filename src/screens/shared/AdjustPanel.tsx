import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { ADJUSTMENTS, formatAdjustment, type AdjustmentKey, type UiAdjustments } from '../../lib/grade';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Props = {
  adj: UiAdjustments;
  onChange: (key: AdjustmentKey, value: number) => void;
  onCommit?: () => void;
  exclude?: AdjustmentKey[];
};

/** Manual grading: pick a control, then set it on the ruler. Double-tap the ruler to reset. */
export function AdjustPanel({ adj, onChange, onCommit, exclude = [] }: Props) {
  const accent = useAccent();
  const defs = ADJUSTMENTS.filter((d) => !exclude.includes(d.key));
  const [key, setKey] = useState<AdjustmentKey>(defs[0]?.key ?? 'exposure');
  const def = defs.find((d) => d.key === key) ?? defs[0];
  const value = adj[def.key] ?? 0;
  return (
    <View>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chips}>
        {defs.map((d) => {
          const v = adj[d.key] ?? 0;
          const selected = d.key === def.key;
          return (
            <Tap key={d.key} haptic="selection" pressedOpacity={0.7} onPress={() => setKey(d.key)} style={styles.chip}>
              <T variant="label" color={selected ? palette.ink : palette.ash}>
                {d.label}
              </T>
              <View style={styles.chipFoot}>
                {v ? (
                  <T variant="caption" color={accent}>
                    {formatAdjustment(d, v)}
                  </T>
                ) : (
                  <View style={[styles.underline, { backgroundColor: selected ? accent : 'transparent' }]} />
                )}
              </View>
            </Tap>
          );
        })}
      </ScrollView>
      <Ruler
        key={def.key}
        min={def.min}
        max={def.max}
        step={def.step}
        value={value}
        reference={0}
        majorEvery={def.key === 'exposure' ? 5 : 10}
        spacing={def.key === 'exposure' ? 12 : 6}
        format={(v) => formatAdjustment(def, v)}
        onChange={(v) => onChange(def.key, v)}
        onEnd={() => onCommit?.()}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  chips: { paddingHorizontal: 12, gap: 4, paddingBottom: 6 },
  chip: { paddingHorizontal: 10, paddingVertical: 6, alignItems: 'center', minWidth: 64 },
  chipFoot: { height: 16, justifyContent: 'center', marginTop: 2 },
  underline: { width: 14, height: 2, borderRadius: 1 },
});
