import React, { useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, { interpolateColor, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import { useAccent } from '../theme/accent';
import { palette } from '../theme/tokens';
import { Tap } from './Tap';

type Props = { value: boolean; onChange: (v: boolean) => void; disabled?: boolean };

export function Toggle({ value, onChange, disabled }: Props) {
  const accent = useAccent();
  const t = useSharedValue(value ? 1 : 0);
  useEffect(() => {
    t.value = withTiming(value ? 1 : 0, { duration: 160 });
  }, [value, t]);
  const track = useAnimatedStyle(() => ({
    backgroundColor: interpolateColor(t.value, [0, 1], [palette.smoke, accent]),
  }));
  const thumb = useAnimatedStyle(() => ({
    transform: [{ translateX: t.value * 18 }],
    backgroundColor: interpolateColor(t.value, [0, 1], [palette.ash, palette.black]),
  }));
  return (
    <Tap onPress={() => onChange(!value)} disabled={disabled} haptic="selection" pressedOpacity={0.8}>
      <Animated.View style={[styles.track, track]}>
        <Animated.View style={[styles.thumb, thumb]} />
      </Animated.View>
    </Tap>
  );
}

const styles = StyleSheet.create({
  track: { width: 44, height: 26, borderRadius: 13, padding: 4 },
  thumb: { width: 18, height: 18, borderRadius: 9 },
});
