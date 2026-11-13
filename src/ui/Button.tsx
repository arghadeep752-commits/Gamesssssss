import React from 'react';
import { ActivityIndicator, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';

import { useAccent } from '../theme/accent';
import { palette, radius } from '../theme/tokens';
import { T } from './T';
import { Tap } from './Tap';

type Props = {
  label: string;
  onPress: () => void;
  kind?: 'primary' | 'secondary' | 'plain' | 'danger';
  disabled?: boolean;
  busy?: boolean;
  style?: StyleProp<ViewStyle>;
};

export function Button({ label, onPress, kind = 'primary', disabled, busy, style }: Props) {
  const accent = useAccent();
  const bg =
    kind === 'primary' ? accent : kind === 'secondary' ? palette.smoke : kind === 'danger' ? palette.tally : 'transparent';
  const fg = kind === 'primary' ? palette.black : kind === 'plain' ? accent : palette.ink;
  return (
    <Tap onPress={onPress} disabled={disabled || busy} haptic="light" style={[styles.base, { backgroundColor: bg }, style]}>
      <View style={styles.row}>
        {busy ? <ActivityIndicator color={fg} size="small" style={styles.spinner} /> : null}
        <T variant="bodyStrong" color={fg}>
          {label}
        </T>
      </View>
    </Tap>
  );
}

const styles = StyleSheet.create({
  base: { height: 48, borderRadius: radius.md, paddingHorizontal: 20, alignItems: 'center', justifyContent: 'center' },
  row: { flexDirection: 'row', alignItems: 'center' },
  spinner: { marginRight: 10 },
});
