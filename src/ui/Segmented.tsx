import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import { useAccent } from '../theme/accent';
import { palette, radius } from '../theme/tokens';
import { T } from './T';
import { Tap } from './Tap';

export type SegmentOption<V extends string | number> = { value: V; label: string; disabled?: boolean; hint?: string };

type Props<V extends string | number> = {
  options: SegmentOption<V>[];
  value: V;
  onChange: (v: V) => void;
  scroll?: boolean;
};

/** Row of choices. The selected one is outlined in the accent colour. */
export function Segmented<V extends string | number>({ options, value, onChange, scroll }: Props<V>) {
  const accent = useAccent();
  const items = options.map((o) => {
    const selected = o.value === value;
    return (
      <Tap
        key={String(o.value)}
        disabled={o.disabled}
        haptic="selection"
        onPress={() => onChange(o.value)}
        style={[styles.item, selected ? { borderColor: accent } : null]}
      >
        <T variant="label" color={selected ? palette.ink : palette.ash}>
          {o.label}
        </T>
        {o.hint ? (
          <T variant="caption" color={selected ? accent : palette.iron} style={styles.hint}>
            {o.hint}
          </T>
        ) : null}
      </Tap>
    );
  });
  if (scroll) {
    return (
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {items}
      </ScrollView>
    );
  }
  return <View style={[styles.row, styles.wrap]}>{items}</View>;
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 8 },
  wrap: { flexWrap: 'wrap' },
  item: {
    minHeight: 40,
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: radius.md,
    borderWidth: 1.2,
    borderColor: palette.rule,
    backgroundColor: palette.panel,
    justifyContent: 'center',
    alignItems: 'center',
  },
  hint: { marginTop: 1 },
});
