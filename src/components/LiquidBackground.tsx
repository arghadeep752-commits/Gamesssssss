/**
 * Pools of colored light behind the glass. The pools are still and the whole
 * background is cached in one GPU texture (renderToHardwareTextureAndroid),
 * so it costs a single texture draw per frame and nothing while idle.
 */
import React, { memo } from 'react';
import { Image, StyleSheet, View } from 'react-native';
import { usePalette } from '../theme/theme';

const pool = require('../../assets/liquid/pool.png');

interface PoolSpec {
  /** Size and position as fractions of the screen width / height. */
  size: number;
  x: number;
  y: number;
  opacity: number;
}

const POOLS: PoolSpec[] = [
  { size: 1.3, x: -0.34, y: -0.08, opacity: 1 },
  { size: 1.1, x: 0.18, y: 0.17, opacity: 0.85 },
  { size: 1.4, x: -0.25, y: 0.45, opacity: 0.8 },
  { size: 0.78, x: 0.37, y: 0.63, opacity: 0.7 },
];

interface Props {
  width: number;
  height: number;
}

export const LiquidBackground = memo(function LiquidBackground({
  width,
  height,
}: Props) {
  const p = usePalette();
  return (
    <View
      pointerEvents="none"
      renderToHardwareTextureAndroid
      style={[
        StyleSheet.absoluteFill,
        styles.wrap,
        { backgroundColor: p.base },
      ]}
    >
      {POOLS.map((spec, i) => {
        const size = spec.size * width;
        return (
          <Image
            key={i}
            source={pool}
            fadeDuration={0}
            style={[
              styles.pool,
              {
                width: size,
                height: size,
                left: spec.x * width,
                top: spec.y * height,
                tintColor: p.pools[i],
                opacity: p.poolOpacity * spec.opacity,
              },
            ]}
          />
        );
      })}
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
