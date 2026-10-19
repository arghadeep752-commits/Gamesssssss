import React from 'react';
import { Image, StyleSheet, Text, View } from 'react-native';
import { fonts, usePalette } from '../theme/theme';
import { GlassButton } from './GlassButton';

const tuneIcon = require('../../assets/icons/tune.png');

interface Props {
  height: number;
  /** Hidden in landscape, where the display needs the room. */
  showTitle: boolean;
  showSciToggle: boolean;
  sciOpen: boolean;
  still: boolean;
  onToggleSci: () => void;
  onOpenSettings: () => void;
}

export function TopBar({
  height,
  showTitle,
  showSciToggle,
  sciOpen,
  still,
  onToggleSci,
  onOpenSettings,
}: Props) {
  const p = usePalette();
  const label = (color: string) => (
    <Text allowFontScaling={false} style={[styles.pillText, { color }]}>
      f(x)
    </Text>
  );
  return (
    <View style={[styles.bar, { height }]}>
      {showTitle ? (
        <View style={styles.brand}>
          <View
            style={[
              styles.dot,
              { backgroundImage: p.liquidGradient, backgroundColor: p.accent },
            ]}
          />
          <Text
            style={[styles.title, { color: p.ink }]}
            allowFontScaling={false}
            accessibilityRole="header"
          >
            Calc Pro
          </Text>
        </View>
      ) : (
        <View />
      )}
      <View style={styles.actions}>
        {showSciToggle ? (
          <GlassButton
            width={66}
            height={40}
            onPress={onToggleSci}
            accessibilityRole="switch"
            accessibilityState={{ checked: sciOpen }}
            accessibilityLabel="Scientific keys"
            active={sciOpen}
            still={still}
            activeChildren={label(p.accentInk)}
          >
            {label(p.ink)}
          </GlassButton>
        ) : null}
        <GlassButton
          width={40}
          height={40}
          onPress={onOpenSettings}
          accessibilityLabel="Settings"
        >
          <Image
            source={tuneIcon}
            fadeDuration={0}
            style={[styles.icon, { tintColor: p.ink }]}
          />
        </GlassButton>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingLeft: 24,
    paddingRight: 18,
  },
  brand: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 9,
  },
  dot: {
    width: 14,
    height: 14,
    borderRadius: 7,
  },
  title: {
    fontFamily: fonts.semibold,
    fontSize: 18,
    letterSpacing: -0.2,
  },
  actions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  pillText: {
    fontFamily: fonts.medium,
    fontSize: 15,
    includeFontPadding: false,
  },
  icon: {
    width: 20,
    height: 20,
  },
});
