import { Image } from 'expo-image';
import React, { useRef, useState } from 'react';
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';

import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';

type Props = {
  frames: string[];
  durationMs: number;
  startMs: number;
  endMs: number;
  positionMs: number;
  /** While a handle moves (commit=false) and when it is let go (commit=true). */
  onTrim: (startMs: number, endMs: number, commit: boolean) => void;
  onSeek: (ms: number, done: boolean) => void;
};

const HEIGHT = 52;
const HANDLE_W = 16;
const MIN_LENGTH_MS = 500;

/** Film strip with trim handles at either end and the playhead. Drag the strip to scrub. */
export function Timeline({ frames, durationMs, startMs, endMs, positionMs, onTrim, onSeek }: Props) {
  const accent = useAccent();
  const [width, setWidth] = useState(0);
  const inner = Math.max(1, width - HANDLE_W * 2);
  const toX = (ms: number) => HANDLE_W + (durationMs > 0 ? (ms / durationMs) * inner : 0);
  const toMs = (x: number) => Math.max(0, Math.min(durationMs, ((x - HANDLE_W) / inner) * durationMs));
  const startRef = useRef({ start: startMs, end: endMs });

  const handle = (which: 'start' | 'end') =>
    Gesture.Pan()
      .runOnJS(true)
      .minDistance(0)
      .hitSlop({ horizontal: 14, vertical: 10 })
      .onBegin(() => {
        startRef.current = { start: startMs, end: endMs };
      })
      .onUpdate((e) => {
        const s = startRef.current;
        const delta = (e.translationX / inner) * durationMs;
        if (which === 'start') {
          const v = Math.max(0, Math.min(s.end - MIN_LENGTH_MS, s.start + delta));
          onTrim(v, s.end, false);
        } else {
          const v = Math.min(durationMs, Math.max(s.start + MIN_LENGTH_MS, s.end + delta));
          onTrim(s.start, v, false);
        }
      })
      .onFinalize((e) => {
        const s = startRef.current;
        const delta = (e.translationX / inner) * durationMs;
        if (which === 'start') onTrim(Math.max(0, Math.min(s.end - MIN_LENGTH_MS, s.start + delta)), s.end, true);
        else onTrim(s.start, Math.min(durationMs, Math.max(s.start + MIN_LENGTH_MS, s.end + delta)), true);
      });

  const scrub = Gesture.Pan()
    .runOnJS(true)
    .minDistance(0)
    .onBegin((e) => onSeek(Math.max(startMs, Math.min(endMs, toMs(e.x))), false))
    .onUpdate((e) => onSeek(Math.max(startMs, Math.min(endMs, toMs(e.x))), false))
    .onFinalize((e) => onSeek(Math.max(startMs, Math.min(endMs, toMs(e.x))), true));

  const sx = toX(startMs);
  const ex = toX(endMs);
  const px = toX(Math.max(startMs, Math.min(endMs, positionMs)));
  const frameW = frames.length ? inner / frames.length : inner;

  return (
    <View style={styles.root} onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}>
      {width > 0 ? (
        <>
          <GestureDetector gesture={scrub}>
            <View style={[styles.strip, { left: HANDLE_W, width: inner }]}>
              {frames.map((f, i) => (
                <Image key={f} source={{ uri: f }} style={{ width: frameW, height: HEIGHT }} contentFit="cover" />
              ))}
            </View>
          </GestureDetector>
          <View pointerEvents="none" style={[styles.dim, { left: HANDLE_W, width: Math.max(0, sx - HANDLE_W) }]} />
          <View pointerEvents="none" style={[styles.dim, { left: ex, width: Math.max(0, HANDLE_W + inner - ex) }]} />
          <View pointerEvents="none" style={[styles.edge, { left: sx, width: Math.max(0, ex - sx), borderColor: accent }]} />
          <View pointerEvents="none" style={[styles.playhead, { left: px - 1 }]} />
          <GestureDetector gesture={handle('start')}>
            <View style={[styles.handle, { left: sx - HANDLE_W, backgroundColor: accent, borderTopLeftRadius: 6, borderBottomLeftRadius: 6 }]}>
              <View style={styles.grip} />
            </View>
          </GestureDetector>
          <GestureDetector gesture={handle('end')}>
            <View style={[styles.handle, { left: ex, backgroundColor: accent, borderTopRightRadius: 6, borderBottomRightRadius: 6 }]}>
              <View style={styles.grip} />
            </View>
          </GestureDetector>
        </>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { height: HEIGHT + 8, justifyContent: 'center' },
  strip: { position: 'absolute', top: 4, height: HEIGHT, flexDirection: 'row', overflow: 'hidden', backgroundColor: palette.panel },
  dim: { position: 'absolute', top: 4, height: HEIGHT, backgroundColor: 'rgba(0,0,0,0.62)' },
  edge: { position: 'absolute', top: 4, height: HEIGHT, borderTopWidth: 2, borderBottomWidth: 2 },
  playhead: { position: 'absolute', top: 0, height: HEIGHT + 8, width: 2, borderRadius: 1, backgroundColor: palette.ink },
  handle: { position: 'absolute', top: 4, width: HANDLE_W, height: HEIGHT, alignItems: 'center', justifyContent: 'center' },
  grip: { width: 2, height: 16, borderRadius: 1, backgroundColor: palette.black },
});
