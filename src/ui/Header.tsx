import { useNavigation } from '@react-navigation/native';
import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { palette, space } from '../theme/tokens';
import { Icon } from './Icon';
import { T } from './T';
import { Tap } from './Tap';

type Props = { title?: string; right?: React.ReactNode; onBack?: () => void; large?: boolean };

/** Screen header: back on the left, optional title, actions on the right. */
export function Header({ title, right, onBack, large }: Props) {
  const nav = useNavigation();
  const insets = useSafeAreaInsets();
  return (
    <View style={{ paddingTop: insets.top }}>
      <View style={styles.bar}>
        <Tap onPress={onBack ?? (() => nav.goBack())} haptic="selection" style={styles.back}>
          <Icon name="back" size={24} color={palette.ink} />
        </Tap>
        {!large && title ? (
          <T variant="bodyStrong" style={styles.inlineTitle} numberOfLines={1}>
            {title}
          </T>
        ) : (
          <View style={styles.flex} />
        )}
        <View style={styles.right}>{right}</View>
      </View>
      {large && title ? (
        <T variant="title" style={styles.largeTitle}>
          {title}
        </T>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  bar: { height: 52, flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.sm },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  inlineTitle: { flex: 1, textAlign: 'center' },
  flex: { flex: 1 },
  right: { minWidth: 44, flexDirection: 'row', alignItems: 'center', justifyContent: 'flex-end', gap: 4 },
  largeTitle: { paddingHorizontal: space.lg, paddingBottom: space.sm },
});
