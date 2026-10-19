import React, { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import type { AngleMode } from '../engine';
import type { Metrics } from '../hooks/useLayoutMetrics';
import {
  BASIC_ROWS,
  KeyId,
  KeySpec,
  SCI_LANDSCAPE,
  SCI_PORTRAIT,
  sciKey,
} from '../state/keys';
import { Key } from './Key';

function fontFor(spec: KeySpec, m: Metrics): number {
  if (spec.kind === 'op' || spec.kind === 'eq') {
    return m.opFont;
  }
  if (spec.kind === 'fn') {
    return spec.id === 'pct' ? m.digitFont * 0.92 : m.fnFont;
  }
  return m.digitFont;
}

interface BasicProps {
  m: Metrics;
  /** Operator waiting for its second operand (shown filled with liquid). */
  activeKey: KeyId | null;
  still: boolean;
  onKey: (id: KeyId) => void;
  onLongKey: (id: KeyId) => void;
}

export const BasicPad = memo(function BasicPad({
  m,
  activeKey,
  still,
  onKey,
  onLongKey,
}: BasicProps) {
  return (
    <View style={{ gap: m.gap }}>
      {BASIC_ROWS.map((row, r) => (
        <View key={r} style={[styles.row, { gap: m.gap }]}>
          {row.map(spec => (
            <Key
              key={spec.id}
              spec={spec}
              width={m.keyW}
              height={m.keyH}
              fontSize={fontFor(spec, m)}
              active={spec.id === activeKey}
              still={still}
              onPress={onKey}
              onLongPress={spec.id === 'back' ? onLongKey : undefined}
            />
          ))}
        </View>
      ))}
    </View>
  );
});

interface SciProps {
  m: Metrics;
  second: boolean;
  angle: AngleMode;
  activeKey: KeyId | null;
  still: boolean;
  onKey: (id: KeyId) => void;
}

export const SciPad = memo(function SciPad({
  m,
  second,
  angle,
  activeKey,
  still,
  onKey,
}: SciProps) {
  const rows = m.landscape ? SCI_LANDSCAPE : SCI_PORTRAIT;
  return (
    <View style={{ gap: m.sciGap }}>
      {rows.map((row, r) => (
        <View key={r} style={[styles.row, { gap: m.sciGap }]}>
          {row.map(slot => {
            const spec = sciKey(slot, second, angle);
            return (
              <Key
                key={slot}
                spec={spec}
                width={m.sciW}
                height={m.sciH}
                fontSize={m.sciFont}
                active={slot === 'second' ? second : spec.id === activeKey}
                still={still}
                onPress={onKey}
              />
            );
          })}
        </View>
      ))}
    </View>
  );
});

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
  },
});
