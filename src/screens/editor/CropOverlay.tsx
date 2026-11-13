import React, { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, type SharedValue } from 'react-native-reanimated';

import type { Rect } from '../../lib/transform';
import { palette } from '../../theme/tokens';

type Frame = { x: number; y: number; width: number; height: number };

type Props = {
  /** Where the uncropped picture sits inside the canvas, in dp. */
  frame: Frame;
  crop: Rect;
  /** Locked width/height ratio in normalized frame units, or null for free. */
  ratio: number | null;
  onChange: (crop: Rect) => void;
};

const MIN = 0.08;
const HANDLE = 44;
const ARM = 18;

type Corner = 'tl' | 'tr' | 'bl' | 'br';

function resize(corner: Corner, s: Rect, dx: number, dy: number, ratio: number): Rect {
  'worklet';
  const left = corner === 'tl' || corner === 'bl';
  const top = corner === 'tl' || corner === 'tr';
  const ax = left ? s.x + s.w : s.x;
  const ay = top ? s.y + s.h : s.y;
  const px = Math.min(1, Math.max(0, (left ? s.x : s.x + s.w) + dx));
  const py = Math.min(1, Math.max(0, (top ? s.y : s.y + s.h) + dy));
  const maxW = left ? ax : 1 - ax;
  const maxH = top ? ay : 1 - ay;
  let w = Math.min(maxW, Math.max(MIN, left ? ax - px : px - ax));
  let h = Math.min(maxH, Math.max(MIN, top ? ay - py : py - ay));
  if (ratio > 0) {
    if (w / ratio > h) h = w / ratio;
    else w = h * ratio;
    if (w > maxW) {
      w = maxW;
      h = w / ratio;
    }
    if (h > maxH) {
      h = maxH;
      w = h * ratio;
    }
  }
  return { x: left ? ax - w : ax, y: top ? ay - h : ay, w, h };
}

function CornerHandle({ corner, rect, start, frame, ratio, onEnd }: {
  corner: Corner;
  rect: SharedValue<Rect>;
  start: SharedValue<Rect>;
  frame: Frame;
  ratio: number;
  onEnd: (r: Rect) => void;
}) {
  const gesture = Gesture.Pan()
    .minDistance(0)
    .onBegin(() => {
      start.value = rect.value;
    })
    .onUpdate((e) => {
      rect.value = resize(corner, start.value, e.translationX / frame.width, e.translationY / frame.height, ratio);
    })
    .onFinalize(() => {
      runOnJS(onEnd)(rect.value);
    });
  const style = useAnimatedStyle(() => {
    const r = rect.value;
    const cx = frame.x + (corner === 'tl' || corner === 'bl' ? r.x : r.x + r.w) * frame.width;
    const cy = frame.y + (corner === 'tl' || corner === 'tr' ? r.y : r.y + r.h) * frame.height;
    return { left: cx - HANDLE / 2, top: cy - HANDLE / 2 };
  });
  const h = corner === 'tl' || corner === 'bl' ? { left: HANDLE / 2 - 1 } : { right: HANDLE / 2 - 1 };
  const v = corner === 'tl' || corner === 'tr' ? { top: HANDLE / 2 - 1 } : { bottom: HANDLE / 2 - 1 };
  return (
    <GestureDetector gesture={gesture}>
      <Animated.View style={[styles.handle, style]} hitSlop={8}>
        <View style={[styles.armH, h, v]} />
        <View style={[styles.armV, h, v]} />
      </Animated.View>
    </GestureDetector>
  );
}

/** Crop rectangle with corner handles, a thirds grid and the outside dimmed. */
export function CropOverlay({ frame, crop, ratio, onChange }: Props) {
  const rect = useSharedValue<Rect>(crop);
  const start = useSharedValue<Rect>(crop);

  useEffect(() => {
    rect.value = crop;
  }, [crop, rect]);

  const move = Gesture.Pan()
    .onBegin(() => {
      start.value = rect.value;
    })
    .onUpdate((e) => {
      const s = start.value;
      rect.value = {
        x: Math.min(1 - s.w, Math.max(0, s.x + e.translationX / frame.width)),
        y: Math.min(1 - s.h, Math.max(0, s.y + e.translationY / frame.height)),
        w: s.w,
        h: s.h,
      };
    })
    .onFinalize(() => {
      runOnJS(onChange)(rect.value);
    });

  const box = useAnimatedStyle(() => {
    const r = rect.value;
    return {
      left: frame.x + r.x * frame.width,
      top: frame.y + r.y * frame.height,
      width: r.w * frame.width,
      height: r.h * frame.height,
    };
  });
  const dimTop = useAnimatedStyle(() => ({
    left: frame.x,
    top: frame.y,
    width: frame.width,
    height: rect.value.y * frame.height,
  }));
  const dimBottom = useAnimatedStyle(() => {
    const r = rect.value;
    return { left: frame.x, top: frame.y + (r.y + r.h) * frame.height, width: frame.width, height: (1 - r.y - r.h) * frame.height };
  });
  const dimLeft = useAnimatedStyle(() => {
    const r = rect.value;
    return { left: frame.x, top: frame.y + r.y * frame.height, width: r.x * frame.width, height: r.h * frame.height };
  });
  const dimRight = useAnimatedStyle(() => {
    const r = rect.value;
    return {
      left: frame.x + (r.x + r.w) * frame.width,
      top: frame.y + r.y * frame.height,
      width: (1 - r.x - r.w) * frame.width,
      height: r.h * frame.height,
    };
  });

  const lock = ratio ?? 0;
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="box-none">
      <Animated.View style={[styles.dim, dimTop]} pointerEvents="none" />
      <Animated.View style={[styles.dim, dimBottom]} pointerEvents="none" />
      <Animated.View style={[styles.dim, dimLeft]} pointerEvents="none" />
      <Animated.View style={[styles.dim, dimRight]} pointerEvents="none" />
      <GestureDetector gesture={move}>
        <Animated.View style={[styles.box, box]}>
          <View style={[styles.gridV, { left: '33.333%' }]} />
          <View style={[styles.gridV, { left: '66.666%' }]} />
          <View style={[styles.gridH, { top: '33.333%' }]} />
          <View style={[styles.gridH, { top: '66.666%' }]} />
        </Animated.View>
      </GestureDetector>
      {(['tl', 'tr', 'bl', 'br'] as Corner[]).map((c) => (
        <CornerHandle key={c} corner={c} rect={rect} start={start} frame={frame} ratio={lock} onEnd={onChange} />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  dim: { position: 'absolute', backgroundColor: 'rgba(0,0,0,0.58)' },
  box: { position: 'absolute', borderWidth: 1, borderColor: palette.ink },
  gridV: { position: 'absolute', top: 0, bottom: 0, width: StyleSheet.hairlineWidth, backgroundColor: 'rgba(247,245,242,0.45)' },
  gridH: { position: 'absolute', left: 0, right: 0, height: StyleSheet.hairlineWidth, backgroundColor: 'rgba(247,245,242,0.45)' },
  handle: { position: 'absolute', width: HANDLE, height: HANDLE },
  armH: { position: 'absolute', width: ARM, height: 3, backgroundColor: palette.ink, borderRadius: 1.5 },
  armV: { position: 'absolute', width: 3, height: ARM, backgroundColor: palette.ink, borderRadius: 1.5 },
});
