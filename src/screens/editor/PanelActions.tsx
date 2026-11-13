import React from 'react';
import { StyleSheet, View } from 'react-native';

import { useAccent } from '../../theme/accent';
import { palette, space } from '../../theme/tokens';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Action = { label: string; onPress: () => void; disabled?: boolean; strong?: boolean };

/** Quiet text actions under an editor panel. */
export function PanelActions({ actions }: { actions: Action[] }) {
  const accent = useAccent();
  return (
    <View style={styles.row}>
      {actions.map((a) => (
        <Tap key={a.label} haptic="selection" onPress={a.onPress} disabled={a.disabled} style={styles.action}>
          <T variant="label" color={a.strong ? accent : palette.ash}>
            {a.label}
          </T>
        </Tap>
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: 'row', justifyContent: 'center', gap: space.xl, paddingTop: space.sm },
  action: { paddingVertical: 6, paddingHorizontal: 4 },
});
