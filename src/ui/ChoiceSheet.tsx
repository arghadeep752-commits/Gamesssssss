import React from 'react';
import { StyleSheet, View } from 'react-native';

import { useAccent } from '../theme/accent';
import { hairline, palette, space } from '../theme/tokens';
import { Icon } from './Icon';
import { Sheet } from './Sheet';
import { T } from './T';
import { Tap } from './Tap';

export type Choice<V> = { value: V; label: string; detail?: string; disabled?: boolean };

type Props<V> = {
  visible: boolean;
  title: string;
  note?: string;
  choices: Choice<V>[];
  value: V;
  onChange: (v: V) => void;
  onClose: () => void;
};

/** Pick one of a few options. Closes on choice. */
export function ChoiceSheet<V extends string | number>({ visible, title, note, choices, value, onChange, onClose }: Props<V>) {
  const accent = useAccent();
  return (
    <Sheet visible={visible} onClose={onClose} title={title}>
      {note ? (
        <T variant="caption" color={palette.ash} style={styles.note}>
          {note}
        </T>
      ) : null}
      {choices.map((c, i) => {
        const selected = c.value === value;
        return (
          <Tap
            key={String(c.value)}
            haptic="selection"
            disabled={c.disabled}
            onPress={() => {
              onChange(c.value);
              onClose();
            }}
            style={[styles.row, i < choices.length - 1 && styles.rule]}
            accessibilityState={{ selected }}
          >
            <View style={styles.text}>
              <T variant="body">{c.label}</T>
              {c.detail ? (
                <T variant="caption" color={palette.ash} style={styles.detail}>
                  {c.detail}
                </T>
              ) : null}
            </View>
            {selected ? <Icon name="check" size={20} color={accent} /> : null}
          </Tap>
        );
      })}
    </Sheet>
  );
}

const styles = StyleSheet.create({
  note: { marginBottom: space.sm },
  row: { minHeight: 52, flexDirection: 'row', alignItems: 'center', paddingVertical: 10, gap: space.md },
  rule: { borderBottomWidth: hairline, borderBottomColor: palette.rule },
  text: { flex: 1 },
  detail: { marginTop: 2 },
});
