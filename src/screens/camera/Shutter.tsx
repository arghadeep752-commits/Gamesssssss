import React, { useEffect } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withSpring, withTiming } from 'react-native-reanimated';
import Svg, { Circle, Line } from 'react-native-svg';

import type { CameraMode } from '../../../modules/camero-engine';
import { palette } from '../../theme/tokens';

type Props = {
  mode: CameraMode;
  recording: boolean;
  busy?: boolean;
  disabled?: boolean;
  onPress: () => void;
  onLongPress?: () => void;
};

const SIZE = 76;

/**
 * Shutter: white disc for stills, red disc for video that squares off while recording.
 * Time-lapse adds a ring of ticks; slow motion a double ring.
 */
export function Shutter({ mode, recording, busy, disabled, onPress, onLongPress }: Props) {
  const video = mode === 'video' || mode === 'slowmo' || mode === 'timelapse';
  const press = useSharedValue(0);
  const rec = useSharedValue(recording ? 1 : 0);

  useEffect(() => {
    rec.value = withTiming(recording ? 1 : 0, { duration: 220 });
  }, [recording, rec]);

  const inner = useAnimatedStyle(() => {
    const base = video ? 58 - rec.value * 30 : 62;
    const scale = 1 - press.value * 0.08;
    return {
      width: base,
      height: base,
      borderRadius: video ? 29 - rec.value * 22 : 31,
      transform: [{ scale }],
      backgroundColor: video ? palette.tally : palette.ink,
      opacity: busy ? 0.6 : 1,
    };
  });

  return (
    <Pressable
      onPress={onPress}
      onLongPress={onLongPress}
      disabled={disabled}
      onPressIn={() => (press.value = withSpring(1, { damping: 20, stiffness: 400 }))}
      onPressOut={() => (press.value = withSpring(0, { damping: 20, stiffness: 300 }))}
      hitSlop={10}
      style={[styles.root, disabled && styles.disabled]}
      accessibilityRole="button"
      accessibilityLabel={video ? (recording ? 'Stop recording' : 'Start recording') : 'Take photo'}
    >
      <Svg width={SIZE} height={SIZE} style={StyleSheet.absoluteFill}>
        <Circle cx={SIZE / 2} cy={SIZE / 2} r={SIZE / 2 - 2} stroke={palette.ink} strokeWidth={3} fill="none" />
        {mode === 'slowmo' ? (
          <Circle cx={SIZE / 2} cy={SIZE / 2} r={SIZE / 2 - 6.5} stroke={palette.ink} strokeOpacity={0.45} strokeWidth={1} fill="none" />
        ) : null}
        {mode === 'timelapse'
          ? Array.from({ length: 24 }, (_, i) => {
              const a = (i / 24) * Math.PI * 2;
              const r1 = SIZE / 2 - 6;
              const r2 = SIZE / 2 - 9;
              return (
                <Line
                  key={i}
                  x1={SIZE / 2 + Math.cos(a) * r1}
                  y1={SIZE / 2 + Math.sin(a) * r1}
                  x2={SIZE / 2 + Math.cos(a) * r2}
                  y2={SIZE / 2 + Math.sin(a) * r2}
                  stroke={palette.ink}
                  strokeOpacity={0.55}
                  strokeWidth={1}
                />
              );
            })
          : null}
      </Svg>
      <View style={styles.center}>
        <Animated.View style={inner} />
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  root: { width: SIZE, height: SIZE, alignItems: 'center', justifyContent: 'center' },
  disabled: { opacity: 0.4 },
  center: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
});
