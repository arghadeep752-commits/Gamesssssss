import { Image } from 'expo-image';
import React, { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { runOnJS, useAnimatedStyle, useSharedValue, withDecay, withTiming } from 'react-native-reanimated';

const MAX_SCALE = 6;
const DOUBLE_TAP_SCALE = 2.5;

type Props = {
  uri: string;
  width: number;
  height: number;
  /** Resets the zoom when the page scrolls away. */
  active: boolean;
  onTap: () => void;
  onZoomChange: (zoomed: boolean) => void;
};

/** Photo that pinches, pans and double-taps to zoom. Single tap toggles the viewer chrome. */
export function ZoomableImage({ uri, width, height, active, onTap, onZoomChange }: Props) {
  const scale = useSharedValue(1);
  const tx = useSharedValue(0);
  const ty = useSharedValue(0);
  const start = useSharedValue({ s: 1, x: 0, y: 0, fx: 0, fy: 0 });
  const fitW = useSharedValue(width);
  const fitH = useSharedValue(height);
  const [natural, setNatural] = useState<{ w: number; h: number } | null>(null);
  const [zoomed, setZoomed] = useState(false);

  useEffect(() => {
    if (!natural) {
      fitW.value = width;
      fitH.value = height;
      return;
    }
    const s = Math.min(width / natural.w, height / natural.h);
    fitW.value = natural.w * s;
    fitH.value = natural.h * s;
  }, [natural, width, height, fitW, fitH]);

  useEffect(() => {
    if (active) return;
    scale.value = 1;
    tx.value = 0;
    ty.value = 0;
    setZoomed(false);
  }, [active, scale, tx, ty]);

  const report = (z: boolean) => {
    setZoomed(z);
    onZoomChange(z);
  };

  const pinch = Gesture.Pinch()
    .onStart((e) => {
      start.value = { s: scale.value, x: tx.value, y: ty.value, fx: e.focalX - width / 2, fy: e.focalY - height / 2 };
      runOnJS(report)(true);
    })
    .onUpdate((e) => {
      const st = start.value;
      const s = Math.min(MAX_SCALE * 1.25, Math.max(0.75, st.s * e.scale));
      // Keep the image point that was under the fingers under the fingers.
      const px = (st.fx - st.x) / st.s;
      const py = (st.fy - st.y) / st.s;
      tx.value = e.focalX - width / 2 - s * px;
      ty.value = e.focalY - height / 2 - s * py;
      scale.value = s;
    })
    .onEnd(() => {
      const s = Math.min(MAX_SCALE, Math.max(1, scale.value));
      const bx = Math.max(0, (fitW.value * s - width) / 2);
      const by = Math.max(0, (fitH.value * s - height) / 2);
      scale.value = withTiming(s, { duration: 180 });
      tx.value = withTiming(s === 1 ? 0 : Math.min(bx, Math.max(-bx, tx.value)), { duration: 180 });
      ty.value = withTiming(s === 1 ? 0 : Math.min(by, Math.max(-by, ty.value)), { duration: 180 });
      runOnJS(report)(s > 1.01);
    });

  const pan = Gesture.Pan()
    .enabled(zoomed)
    .maxPointers(1)
    .onStart(() => {
      start.value = { s: scale.value, x: tx.value, y: ty.value, fx: 0, fy: 0 };
    })
    .onUpdate((e) => {
      tx.value = start.value.x + e.translationX;
      ty.value = start.value.y + e.translationY;
    })
    .onEnd((e) => {
      const bx = Math.max(0, (fitW.value * scale.value - width) / 2);
      const by = Math.max(0, (fitH.value * scale.value - height) / 2);
      tx.value = withDecay({ velocity: e.velocityX, clamp: [-bx, bx] });
      ty.value = withDecay({ velocity: e.velocityY, clamp: [-by, by] });
    });

  const doubleTap = Gesture.Tap()
    .numberOfTaps(2)
    .maxDelay(260)
    .onEnd((e) => {
      if (scale.value > 1.01) {
        scale.value = withTiming(1, { duration: 200 });
        tx.value = withTiming(0, { duration: 200 });
        ty.value = withTiming(0, { duration: 200 });
        runOnJS(report)(false);
        return;
      }
      const s = DOUBLE_TAP_SCALE;
      const bx = Math.max(0, (fitW.value * s - width) / 2);
      const by = Math.max(0, (fitH.value * s - height) / 2);
      const fx = e.x - width / 2;
      const fy = e.y - height / 2;
      scale.value = withTiming(s, { duration: 220 });
      tx.value = withTiming(Math.min(bx, Math.max(-bx, fx * (1 - s))), { duration: 220 });
      ty.value = withTiming(Math.min(by, Math.max(-by, fy * (1 - s))), { duration: 220 });
      runOnJS(report)(true);
    });

  const singleTap = Gesture.Tap().onEnd(() => {
    runOnJS(onTap)();
  });

  const gesture = Gesture.Simultaneous(pinch, pan, Gesture.Exclusive(doubleTap, singleTap));

  const style = useAnimatedStyle(() => ({
    transform: [{ translateX: tx.value }, { translateY: ty.value }, { scale: scale.value }],
  }));

  return (
    <GestureDetector gesture={gesture}>
      <View style={{ width, height }} collapsable={false}>
        <Animated.View style={[StyleSheet.absoluteFill, style]}>
          <Image
            source={{ uri }}
            style={StyleSheet.absoluteFill}
            contentFit="contain"
            transition={100}
            recyclingKey={uri}
            onLoad={(e) => setNatural({ w: e.source.width, h: e.source.height })}
          />
        </Animated.View>
      </View>
    </GestureDetector>
  );
}
