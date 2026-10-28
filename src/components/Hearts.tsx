import { memo, useEffect, useRef } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSequence, withTiming } from 'react-native-reanimated';
import { COLORS } from '../config/theme';
import { Icon } from './Icon';

const Heart = memo(function Heart({ full, size, animate }: { full: boolean; size: number; animate: boolean }) {
  const scale = useSharedValue(1);
  const wasFull = useRef(full);
  useEffect(() => {
    if (wasFull.current && !full && animate) {
      scale.value = withSequence(withTiming(1.45, { duration: 110 }), withTiming(0.85, { duration: 120 }), withTiming(1, { duration: 120 }));
    }
    wasFull.current = full;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [full]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  return (
    <Animated.View style={style}>
      <Icon name="heart" size={size} filled={full} color={full ? COLORS.heart : COLORS.heartEmpty} />
    </Animated.View>
  );
});

export const Hearts = memo(function Hearts({
  lives,
  max,
  size = 22,
  animate = true,
}: {
  lives: number;
  max: number;
  size?: number;
  animate?: boolean;
}) {
  return (
    <View style={styles.row} accessibilityLabel={`${lives} of ${max} hearts left`}>
      {Array.from({ length: max }, (_, i) => (
        <Heart key={i} full={i < lives} size={size} animate={animate} />
      ))}
    </View>
  );
});

const styles = StyleSheet.create({
  row: { flexDirection: 'row', gap: 4 },
});
