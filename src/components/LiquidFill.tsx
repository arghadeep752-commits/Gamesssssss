/**
 * Liquid that rises inside a glass surface when it becomes active and drains
 * when it is released. The label on top of the liquid is counter-translated,
 * so it stays put while the rising surface reveals it. Native driver only.
 */
import React, { useEffect, useRef } from 'react';
import { Animated, Easing, StyleSheet, View } from 'react-native';

const wave = require('../../assets/liquid/wave.png');

interface Props {
  active: boolean;
  width: number;
  height: number;
  color: string;
  /** Optional gradient (CSS syntax) painted over the liquid color. */
  gradient?: string;
  still?: boolean;
  /** Content shown on the liquid (usually the label in the "on" color). */
  children?: React.ReactNode;
}

export function LiquidFill({
  active,
  width,
  height,
  color,
  gradient,
  still,
  children,
}: Props) {
  const level = useRef(new Animated.Value(active ? 1 : 0)).current;
  const flow = useRef(new Animated.Value(0)).current;
  const first = useRef(true);

  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    if (still) {
      level.setValue(active ? 1 : 0);
      return;
    }
    flow.setValue(0);
    Animated.parallel([
      Animated.spring(level, {
        toValue: active ? 1 : 0,
        stiffness: active ? 210 : 260,
        damping: active ? 17 : 26,
        mass: 1,
        useNativeDriver: true,
      }),
      Animated.timing(flow, {
        toValue: 1,
        duration: 900,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start();
  }, [active, still, level, flow]);

  const waveH = Math.max(8, Math.round(height * 0.2));
  // Top of the liquid column (wave crest) in the key's coordinates.
  const top = level.interpolate({
    inputRange: [0, 1],
    outputRange: [height + 2, -waveH],
  });
  // Opposite movement for the label so it stays aligned with the key.
  const counter = level.interpolate({
    inputRange: [0, 1],
    outputRange: [-(height + 2 + waveH), 0],
  });

  return (
    <Animated.View
      pointerEvents="none"
      style={[
        styles.column,
        {
          width,
          height: waveH + height * 1.6,
          transform: [{ translateY: top }],
        },
      ]}
    >
      <View style={[styles.waveRow, { height: waveH }]}>
        <Animated.Image
          source={wave}
          fadeDuration={0}
          resizeMode="stretch"
          style={{
            width: width * 2,
            height: waveH,
            tintColor: color,
            transform: [
              {
                translateX: flow.interpolate({
                  inputRange: [0, 1],
                  outputRange: [0, -width],
                }),
              },
            ],
          }}
        />
      </View>
      <View
        style={[
          styles.body,
          {
            width,
            height: height * 1.6,
            backgroundColor: color,
            backgroundImage: gradient,
          },
        ]}
      >
        {children ? (
          <Animated.View
            style={[
              styles.label,
              { width, height, transform: [{ translateY: counter }] },
            ]}
          >
            {children}
          </Animated.View>
        ) : null}
      </View>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  column: {
    position: 'absolute',
    left: 0,
    top: 0,
  },
  waveRow: {
    overflow: 'hidden',
  },
  body: {
    overflow: 'hidden',
  },
  label: {
    position: 'absolute',
    left: 0,
    top: 0,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
