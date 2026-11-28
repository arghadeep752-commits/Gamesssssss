import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue } from 'react-native-reanimated';
import { Icon } from './Icon';
import { Pressy } from './kit';
import { useTheme } from './theme';
import { onUI } from './worklets';
import { clamp, zoomAt, zoomStep, type Zoom } from './zoom';

const THUMB = 22;

/** − [slider] + zoom control (like a map), driven entirely on the UI thread. */
export const ZoomBar = memo(function ZoomBar({ zoom }: { zoom: Zoom }) {
  const t = useTheme();
  const trackW = useSharedValue(120);

  const slide = Gesture.Pan()
    .minDistance(0)
    .onBegin((e: { x: number }) => {
      'worklet';
      const k = clamp((e.x - THUMB / 2) / Math.max(1, trackW.value - THUMB), 0, 1);
      zoomAt(zoom, 1 + k * (zoom.max.value - 1), zoom.aw.value / 2, zoom.ah.value / 2, false);
    })
    .onUpdate((e: { x: number }) => {
      'worklet';
      const k = clamp((e.x - THUMB / 2) / Math.max(1, trackW.value - THUMB), 0, 1);
      zoomAt(zoom, 1 + k * (zoom.max.value - 1), zoom.aw.value / 2, zoom.ah.value / 2, false);
    });

  const thumbStyle = useAnimatedStyle(() => {
    const max = zoom.max.value;
    const k = max > 1.001 ? clamp((zoom.s.value - 1) / (max - 1), 0, 1) : 0;
    return { transform: [{ translateX: k * (trackW.value - THUMB) }] };
  });
  const fillStyle = useAnimatedStyle(() => {
    const max = zoom.max.value;
    const k = max > 1.001 ? clamp((zoom.s.value - 1) / (max - 1), 0, 1) : 0;
    return { transform: [{ scaleX: Math.max(0.001, k) }] };
  });

  return (
    <View style={styles.row}>
      <Pressy onPress={() => onUI(zoomStep, zoom, 1 / 1.5)} label="Zoom out" style={[styles.btn, { backgroundColor: t.surface, borderColor: t.border }]}>
        <Icon name="minus" size={18} color={t.text} strokeWidth={2.4} />
      </Pressy>
      <GestureDetector gesture={slide}>
        <View
          style={styles.trackHit}
          onLayout={(e: { nativeEvent: { layout: { width: number } } }) => {
            trackW.value = e.nativeEvent.layout.width;
          }}
          accessibilityLabel="Zoom"
        >
          <View style={[styles.track, { backgroundColor: t.surfaceAlt }]}>
            <Animated.View style={[styles.fill, { backgroundColor: t.accent }, fillStyle]} />
          </View>
          <Animated.View style={[styles.thumb, { backgroundColor: t.surface, borderColor: t.accent }, thumbStyle]} />
        </View>
      </GestureDetector>
      <Pressy onPress={() => onUI(zoomStep, zoom, 1.5)} label="Zoom in" style={[styles.btn, { backgroundColor: t.surface, borderColor: t.border }]}>
        <Icon name="plus" size={18} color={t.text} strokeWidth={2.4} />
      </Pressy>
    </View>
  );
});

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  btn: { width: 36, height: 36, borderRadius: 18, borderWidth: 1, alignItems: 'center', justifyContent: 'center' },
  trackHit: { width: 92, height: 36, justifyContent: 'center' },
  track: { height: 6, borderRadius: 3, overflow: 'hidden' },
  fill: { ...StyleSheet.absoluteFillObject, transformOrigin: '0% 50%' },
  thumb: { position: 'absolute', left: 0, width: THUMB, height: THUMB, borderRadius: THUMB / 2, borderWidth: 3 },
});
