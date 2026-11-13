import * as Haptics from 'expo-haptics';
import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import Svg, { Line } from 'react-native-svg';

import { useSettings } from '../state/settings';
import { useAccent } from '../theme/accent';
import { palette } from '../theme/tokens';
import { T } from './T';

type Props = {
  /** Discrete stops. When omitted, min/max/step define a linear scale. */
  values?: number[];
  min?: number;
  max?: number;
  step?: number;
  value: number;
  onChange: (value: number) => void;
  onEnd?: (value: number) => void;
  format?: (value: number) => string;
  /** Value drawn as the reference mark (usually 0). */
  reference?: number;
  majorEvery?: number;
  spacing?: number;
  disabled?: boolean;
  showLabel?: boolean;
  caption?: string;
};

function buildStops(values: number[] | undefined, min: number, max: number, step: number): number[] {
  if (values && values.length) return values;
  const n = Math.max(1, Math.round((max - min) / step) + 1);
  return Array.from({ length: n }, (_, i) => Math.round((min + i * step) * 1e6) / 1e6);
}

function nearestIndex(stops: number[], v: number): number {
  let best = 0;
  let bestD = Infinity;
  for (let i = 0; i < stops.length; i++) {
    const d = Math.abs(stops[i] - v);
    if (d < bestD) {
      bestD = d;
      best = i;
    }
  }
  return best;
}

const Ticks = memo(function Ticks({
  count,
  spacing,
  pad,
  majorEvery,
  referenceIndex,
  height,
}: {
  count: number;
  spacing: number;
  pad: number;
  majorEvery: number;
  referenceIndex: number;
  height: number;
}) {
  const width = pad * 2 + (count - 1) * spacing;
  const lines = [];
  for (let i = 0; i < count; i++) {
    const x = pad + i * spacing;
    const major = i % majorEvery === 0;
    const ref = i === referenceIndex;
    const h = ref ? 22 : major ? 16 : 9;
    lines.push(
      <Line
        key={i}
        x1={x}
        x2={x}
        y1={height / 2 - h / 2}
        y2={height / 2 + h / 2}
        stroke={ref ? palette.ink : major ? palette.ash : palette.iron}
        strokeWidth={ref ? 1.6 : 1.1}
        strokeLinecap="round"
      />
    );
  }
  return (
    <Svg width={width} height={height}>
      {lines}
    </Svg>
  );
});

/**
 * Engraved-scale slider: a strip of ticks slides under a fixed accent needle, like the distance
 * scale on a lens barrel. Used for zoom, ISO, shutter, white balance, focus and every adjustment.
 */
export function Ruler({
  values,
  min = 0,
  max = 100,
  step = 1,
  value,
  onChange,
  onEnd,
  format,
  reference,
  majorEvery = 10,
  spacing = 9,
  disabled,
  showLabel = true,
  caption,
}: Props) {
  const accent = useAccent();
  const haptics = useSettings((s) => s.haptics);
  const stops = useMemo(() => buildStops(values, min, max, step), [values, min, max, step]);
  const [width, setWidth] = useState(0);
  const [index, setIndex] = useState(() => nearestIndex(stops, value));
  const dragging = useRef(false);
  const offset = useSharedValue(nearestIndex(stops, value) * spacing);
  const start = useSharedValue(0);
  const lastIndex = useSharedValue(nearestIndex(stops, value));
  const maxOffset = (stops.length - 1) * spacing;
  const referenceIndex = reference === undefined ? -1 : nearestIndex(stops, reference);

  useEffect(() => {
    if (dragging.current) return;
    const i = nearestIndex(stops, value);
    setIndex(i);
    lastIndex.value = i;
    offset.value = withTiming(i * spacing, { duration: 140 });
  }, [value, stops, spacing, offset, lastIndex]);

  const emit = useCallback(
    (i: number, major: boolean) => {
      setIndex(i);
      const v = stops[i];
      onChange(v);
      if (haptics && major) Haptics.selectionAsync().catch(() => {});
    },
    [stops, onChange, haptics]
  );

  const finish = useCallback(
    (i: number) => {
      dragging.current = false;
      onEnd?.(stops[i]);
    },
    [stops, onEnd]
  );

  const begin = useCallback(() => {
    dragging.current = true;
  }, []);

  const pan = Gesture.Pan()
    .enabled(!disabled)
    .activeOffsetX([-4, 4])
    .onBegin(() => {
      start.value = offset.value;
      runOnJS(begin)();
    })
    .onUpdate((e) => {
      const next = Math.min(maxOffset, Math.max(0, start.value - e.translationX));
      offset.value = next;
      const i = Math.round(next / spacing);
      if (i !== lastIndex.value) {
        lastIndex.value = i;
        runOnJS(emit)(i, i % majorEvery === 0 || i === referenceIndex);
      }
    })
    .onFinalize(() => {
      const i = Math.round(offset.value / spacing);
      offset.value = withTiming(i * spacing, { duration: 120 });
      runOnJS(finish)(i);
    });

  const tap = Gesture.Tap()
    .enabled(!disabled)
    .numberOfTaps(2)
    .onEnd(() => {
      if (referenceIndex >= 0) {
        offset.value = withTiming(referenceIndex * spacing, { duration: 160 });
        lastIndex.value = referenceIndex;
        runOnJS(emit)(referenceIndex, true);
        runOnJS(finish)(referenceIndex);
      }
    });

  const strip = useAnimatedStyle(() => ({ transform: [{ translateX: -offset.value }] }));
  const onLayout = (e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width);
  const pad = width / 2;

  return (
    <View style={[styles.root, disabled && styles.disabled]} onLayout={onLayout}>
      {showLabel ? (
        <View style={styles.labelRow}>
          <T variant="readoutLarge" color={palette.ink}>
            {format ? format(stops[index]) : String(stops[index])}
          </T>
          {caption ? (
            <T variant="caption" color={palette.ash} style={styles.caption}>
              {caption}
            </T>
          ) : null}
        </View>
      ) : null}
      <GestureDetector gesture={Gesture.Exclusive(tap, pan)}>
        <View style={styles.track} collapsable={false}>
          {width > 0 ? (
            <Animated.View style={[styles.strip, strip]}>
              <Ticks
                count={stops.length}
                spacing={spacing}
                pad={pad}
                majorEvery={majorEvery}
                referenceIndex={referenceIndex}
                height={TRACK_HEIGHT}
              />
            </Animated.View>
          ) : null}
          <View pointerEvents="none" style={[styles.needle, { left: pad - 1, backgroundColor: accent }]} />
        </View>
      </GestureDetector>
    </View>
  );
}

const TRACK_HEIGHT = 40;

const styles = StyleSheet.create({
  root: { width: '100%' },
  disabled: { opacity: 0.35 },
  labelRow: { flexDirection: 'row', alignItems: 'baseline', justifyContent: 'center', marginBottom: 2, gap: 8 },
  caption: { marginLeft: 2 },
  track: { height: TRACK_HEIGHT, overflow: 'hidden' },
  strip: { position: 'absolute', left: 0, top: 0, height: TRACK_HEIGHT },
  needle: { position: 'absolute', top: 6, width: 2, height: TRACK_HEIGHT - 12, borderRadius: 1 },
});
