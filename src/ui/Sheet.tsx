import React, { useEffect, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import Animated, { Easing, runOnJS, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { palette, radius, space } from '../theme/tokens';
import { Icon } from './Icon';
import { T } from './T';
import { Tap } from './Tap';

type Props = {
  visible: boolean;
  onClose: () => void;
  title?: string;
  children: React.ReactNode;
  maxHeightRatio?: number;
  scroll?: boolean;
};

/** Bottom sheet on a dimmed backdrop. Stays mounted until its exit animation finishes. */
export function Sheet({ visible, onClose, title, children, maxHeightRatio = 0.8, scroll = true }: Props) {
  const { height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const [mounted, setMounted] = useState(visible);
  const progress = useSharedValue(0);

  useEffect(() => {
    if (visible) {
      setMounted(true);
      progress.value = withTiming(1, { duration: 240, easing: Easing.out(Easing.cubic) });
    } else if (mounted) {
      progress.value = withTiming(0, { duration: 180, easing: Easing.in(Easing.cubic) }, (done) => {
        if (done) runOnJS(setMounted)(false);
      });
    }
  }, [visible, mounted, progress]);

  const backdrop = useAnimatedStyle(() => ({ opacity: progress.value * 0.55 }));
  const panel = useAnimatedStyle(() => ({ transform: [{ translateY: (1 - progress.value) * 420 }], opacity: 0.2 + progress.value * 0.8 }));

  if (!mounted) return null;
  const Body = scroll ? ScrollView : View;
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Animated.View style={[StyleSheet.absoluteFill, styles.backdrop, backdrop]}>
        <Pressable style={StyleSheet.absoluteFill} onPress={onClose} />
      </Animated.View>
      <Animated.View style={[styles.panel, { maxHeight: height * maxHeightRatio, paddingBottom: insets.bottom + space.md }, panel]}>
        {title ? (
          <View style={styles.header}>
            <T variant="heading">{title}</T>
            <Tap onPress={onClose} haptic="selection" style={styles.close}>
              <Icon name="close" size={20} color={palette.ash} />
            </Tap>
          </View>
        ) : null}
        <Body style={styles.body} contentContainerStyle={scroll ? styles.content : undefined} showsVerticalScrollIndicator={false}>
          {children}
        </Body>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  backdrop: { backgroundColor: '#000' },
  panel: {
    position: 'absolute',
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: palette.graphite,
    borderTopLeftRadius: radius.lg,
    borderTopRightRadius: radius.lg,
    paddingTop: space.md,
  },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: space.lg, paddingBottom: space.sm },
  close: { padding: 6 },
  body: { flexGrow: 0 },
  content: { paddingHorizontal: space.lg, paddingBottom: space.sm },
});
