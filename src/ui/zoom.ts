import { useMemo } from 'react';
import { useSharedValue, withTiming, type SharedValue } from 'react-native-reanimated';

/**
 * Board zoom/pan state, shared between the board (pinch, pan) and the zoom bar.
 * The board content is transformed as translate(x, y) scale(s) around the
 * centre of the play area; everything here runs on the UI thread.
 */
export interface Zoom {
  s: SharedValue<number>;
  x: SharedValue<number>;
  y: SharedValue<number>;
  max: SharedValue<number>;
  /** Play-area and board size (unscaled), used to keep the board in view. */
  aw: SharedValue<number>;
  ah: SharedValue<number>;
  bw: SharedValue<number>;
  bh: SharedValue<number>;
}

export function useZoom(): Zoom {
  const s = useSharedValue(1);
  const x = useSharedValue(0);
  const y = useSharedValue(0);
  const max = useSharedValue(1);
  const aw = useSharedValue(1);
  const ah = useSharedValue(1);
  const bw = useSharedValue(1);
  const bh = useSharedValue(1);
  return useMemo(() => ({ s, x, y, max, aw, ah, bw, bh }), [s, x, y, max, aw, ah, bw, bh]);
}

/** How far the content may move from centre along one axis at scale s. */
export function panLimit(board: number, area: number, s: number): number {
  'worklet';
  return Math.max(0, (board * s - area) / 2) + (s > 1.02 ? 36 : 0);
}

export function clamp(v: number, lo: number, hi: number): number {
  'worklet';
  return v < lo ? lo : v > hi ? hi : v;
}

/** Zooms to `target` keeping the content point under (fx, fy) in place. */
export function zoomAt(z: Zoom, target: number, fx: number, fy: number, animate: boolean): void {
  'worklet';
  const s0 = z.s.value;
  const s = clamp(target, 1, Math.max(1, z.max.value));
  const cx = z.aw.value / 2;
  const cy = z.ah.value / 2;
  const k = s / s0;
  const lx = panLimit(z.bw.value, z.aw.value, s);
  const ly = panLimit(z.bh.value, z.ah.value, s);
  const nx = clamp(fx - cx - (fx - cx - z.x.value) * k, -lx, lx);
  const ny = clamp(fy - cy - (fy - cy - z.y.value) * k, -ly, ly);
  if (animate) {
    const cfg = { duration: 220 };
    z.s.value = withTiming(s, cfg);
    z.x.value = withTiming(nx, cfg);
    z.y.value = withTiming(ny, cfg);
  } else {
    z.s.value = s;
    z.x.value = nx;
    z.y.value = ny;
  }
}

/** Zoom step used by the +/- buttons (around the centre of the board area). */
export function zoomStep(z: Zoom, factor: number): void {
  'worklet';
  zoomAt(z, z.s.value * factor, z.aw.value / 2, z.ah.value / 2, true);
}

export function resetZoom(z: Zoom): void {
  'worklet';
  z.s.value = 1;
  z.x.value = 0;
  z.y.value = 0;
}
