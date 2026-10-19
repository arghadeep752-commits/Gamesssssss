/**
 * Pools of colored light drifting slowly behind the glass. Every animation
 * runs on the native driver (UI thread), so it never competes with key
 * presses for the JavaScript thread.
 */
import React, { memo, useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';
import { usePalette } from '../theme/theme';

const pool = require('../../assets/liquid/pool.png');

interface PoolSpec {
  /** Size and position as fractions of the screen width / height. */
  size: number;
  x: number;
  y: number;
  dx: number;
  dy: number;
  scaleFrom: number;
  scaleTo: number;
  duration: number;
  opacity: number;
}

const POOLS: PoolSpec[] = [
  {
    size: 1.25,
    x: -0.45,
    y: -0.12,
    dx: 0.22,
    dy: 0.08,
    scaleFrom: 0.95,
    scaleTo: 1.15,
    duration: 21000,
    opacity: 1,
  },
  {
    size: 1.1,
    x: 0.3,
    y: 0.12,
    dx: -0.24,
    dy: 0.1,
    scaleFrom: 1.1,
    scaleTo: 0.9,
    duration: 26000,
    opacity: 0.85,
  },
  {
    size: 1.35,
    x: -0.35,
    y: 0.5,
    dx: 0.2,
    dy: -0.1,
    scaleFrom: 0.92,
    scaleTo: 1.12,
    duration: 31000,
    opacity: 0.8,
  },
  {
    size: 0.8,
    x: 0.45,
    y: 0.7,
    dx: -0.16,
    dy: -0.14,
    scaleFrom: 1.05,
    scaleTo: 0.88,
    duration: 17000,
    opacity: 0.7,
  },
];

interface Props {
  width: number;
  height: number;
  still: boolean;
}

function Pool({
  spec,
  color,
  opacity,
  width,
  height,
  still,
}: {
  spec: PoolSpec;
  color: string;
  opacity: number;
  width: number;
  height: number;
  still: boolean;
}) {
  const t = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (still) {
      t.setValue(0.5);
      return;
    }
    const ease = Easing.inOut(Easing.sin);
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(t, {
          toValue: 1,
          duration: spec.duration,
          easing: ease,
          useNativeDriver: true,
        }),
        Animated.timing(t, {
          toValue: 0,
          duration: spec.duration,
          easing: ease,
          useNativeDriver: true,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [still, spec.duration, t]);

  const size = spec.size * width;
  return (
    <Animated.Image
      source={pool}
      fadeDuration={0}
      style={[
        styles.pool,
        {
          width: size,
          height: size,
          left: spec.x * width,
          top: spec.y * height,
          tintColor: color,
          opacity: opacity * spec.opacity,
          transform: [
            {
              translateX: t.interpolate({
                inputRange: [0, 1],
                outputRange: [0, spec.dx * width],
              }),
            },
            {
              translateY: t.interpolate({
                inputRange: [0, 1],
                outputRange: [0, spec.dy * height],
              }),
            },
            {
              scale: t.interpolate({
                inputRange: [0, 1],
                outputRange: [spec.scaleFrom, spec.scaleTo],
              }),
            },
          ],
        },
      ]}
    />
  );
}

export const LiquidBackground = memo(function LiquidBackground({
  width,
  height,
  still,
}: Props) {
  const p = usePalette();
  return (
    <View
      pointerEvents="none"
      style={[
        StyleSheet.absoluteFill,
        styles.wrap,
        { backgroundColor: p.base },
      ]}
    >
      {POOLS.map((spec, i) => (
        <Pool
          key={i}
          spec={spec}
          color={p.pools[i]}
          opacity={p.poolOpacity}
          width={width}
          height={height}
          still={still}
        />
      ))}
    </View>
  );
});

const styles = StyleSheet.create({
  wrap: {
    overflow: 'hidden',
  },
  pool: {
    position: 'absolute',
  },
});
