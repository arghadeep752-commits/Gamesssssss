import { memo, useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withDelay, withSequence, withTiming } from 'react-native-reanimated';
import { COLORS } from '../config/theme';
import { Icon } from './Icon';

const Star = memo(function Star({ on, size, delay, animate }: { on: boolean; size: number; delay: number; animate: boolean }) {
  const scale = useSharedValue(animate && on ? 0 : 1);
  useEffect(() => {
    if (animate && on) {
      scale.value = withDelay(delay, withSequence(withTiming(1.25, { duration: 180 }), withTiming(1, { duration: 140 })));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <Animated.View style={style}>
      <Icon name="star" size={size} filled color={on ? COLORS.star : COLORS.starEmpty} />
    </Animated.View>
  );
});

export const Stars = memo(function Stars({
  count,
  size = 16,
  animate = false,
  gap = 2,
}: {
  count: number;
  size?: number;
  animate?: boolean;
  gap?: number;
}) {
  return (
    <View style={[styles.row, { gap }]} accessibilityLabel={`${count} of 3 stars`}>
      {[0, 1, 2].map((i) => (
        <Star key={i} on={i < count} size={size} delay={250 + i * 180} animate={animate} />
      ))}
    </View>
  );
});

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center' },
});
