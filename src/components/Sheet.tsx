import React, { useEffect } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { COLORS, RADIUS, SPACE, TYPE } from '../config/theme';

/**
 * In-screen modal. It covers the whole screen and claims every touch, so
 * nothing underneath (the board in particular) can be tapped through it.
 */
export function Sheet({
  title,
  subtitle,
  children,
  reducedEffects,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  reducedEffects?: boolean;
}) {
  const t = useSharedValue(reducedEffects ? 1 : 0);
  useEffect(() => {
    if (!reducedEffects) t.value = withTiming(1, { duration: 180 });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const backdrop = useAnimatedStyle(() => ({ opacity: t.value }));
  const card = useAnimatedStyle(() => ({
    opacity: t.value,
    transform: [{ translateY: (1 - t.value) * 16 }, { scale: 0.96 + 0.04 * t.value }],
  }));
  return (
    <View
      style={StyleSheet.absoluteFill}
      onStartShouldSetResponder={() => true}
      accessibilityViewIsModal
    >
      <Animated.View style={[StyleSheet.absoluteFill, styles.backdrop, backdrop]} />
      <View style={styles.center} pointerEvents="box-none">
        <Animated.View style={[styles.card, card]}>
          <Text style={[TYPE.title, styles.title]} accessibilityRole="header">
            {title}
          </Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
          {children}
        </Animated.View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: { backgroundColor: COLORS.overlay },
  center: { flex: 1, alignItems: 'center', justifyContent: 'center', padding: SPACE.xl },
  card: {
    width: '100%',
    maxWidth: 380,
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    padding: SPACE.xl,
    gap: SPACE.md,
  },
  title: { textAlign: 'center', letterSpacing: 0.5 },
  subtitle: { ...TYPE.body, color: COLORS.inkSoft, textAlign: 'center', marginTop: -SPACE.xs },
});
