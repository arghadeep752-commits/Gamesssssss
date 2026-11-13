import React from 'react';
import { StyleSheet, View } from 'react-native';

import { hairline, palette, space } from '../theme/tokens';
import { Icon } from './Icon';
import { T } from './T';
import { Tap } from './Tap';
import { Toggle } from './Toggle';

type Props = {
  label: string;
  detail?: string;
  value?: string;
  onPress?: () => void;
  toggle?: { value: boolean; onChange: (v: boolean) => void; disabled?: boolean };
  last?: boolean;
  disabled?: boolean;
};

/** Settings-style row: label and detail on the left, value, chevron or toggle on the right. */
export function Row({ label, detail, value, onPress, toggle, last, disabled }: Props) {
  const content = (
    <View style={[styles.row, !last && styles.divider]}>
      <View style={styles.text}>
        <T variant="body" color={disabled ? palette.iron : palette.ink}>
          {label}
        </T>
        {detail ? (
          <T variant="caption" color={palette.ash} style={styles.detail}>
            {detail}
          </T>
        ) : null}
      </View>
      {value ? (
        <T variant="label" color={palette.ash} style={styles.value}>
          {value}
        </T>
      ) : null}
      {toggle ? <Toggle value={toggle.value} onChange={toggle.onChange} disabled={toggle.disabled || disabled} /> : null}
      {onPress && !toggle ? <Icon name="chevron" size={18} color={palette.iron} /> : null}
    </View>
  );
  if (onPress && !toggle) {
    return (
      <Tap onPress={onPress} disabled={disabled} pressedOpacity={0.6}>
        {content}
      </Tap>
    );
  }
  return content;
}

export function Section({ title, children, note }: { title?: string; note?: string; children: React.ReactNode }) {
  return (
    <View style={styles.section}>
      {title ? (
        <T variant="label" color={palette.ash} style={styles.sectionTitle}>
          {title}
        </T>
      ) : null}
      <View style={styles.group}>{children}</View>
      {note ? (
        <T variant="caption" color={palette.iron} style={styles.note}>
          {note}
        </T>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { minHeight: 54, flexDirection: 'row', alignItems: 'center', paddingVertical: 10, paddingRight: space.lg, gap: 12 },
  divider: { borderBottomWidth: hairline, borderBottomColor: palette.rule },
  text: { flex: 1 },
  detail: { marginTop: 2 },
  value: { maxWidth: 170, textAlign: 'right' },
  section: { marginTop: space.xl },
  sectionTitle: { marginBottom: space.sm, paddingHorizontal: space.lg },
  group: { backgroundColor: palette.graphite, paddingLeft: space.lg },
  note: { paddingHorizontal: space.lg, marginTop: space.sm },
});
