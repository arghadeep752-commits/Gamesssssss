import { forwardRef, memo, useCallback, useEffect, useImperativeHandle, useMemo, useRef, useState } from 'react';
import { StyleSheet, View, type ViewStyle } from 'react-native';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, {
  cancelAnimation,
  Easing,
  FadeIn,
  interpolateColor,
  makeMutable,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
  type SharedValue,
} from 'react-native-reanimated';
import type { Level } from '../game/engine';
import {
  arrowGeom,
  capsuleRect,
  type ArrowGeom,
  type Flight,
  flightMs,
  HEAD_BASE,
  HEAD_HALF,
  HEAD_TIP,
  hitTest,
  makeFlight,
  MAX_RUNS,
  type PieceFrame,
  pieceFrame,
} from '../game/geometry';
import { scheduleOnRN } from 'react-native-worklets';
import { onUI } from './worklets';
import { clamp, panLimit, resetZoom, type Zoom } from './zoom';

/**
 * The puzzle board.
 *
 * Performance notes (this is what keeps it smooth on low-end phones):
 * - Arrows at rest are plain native views (rounded bars + a border-drawn head),
 *   mounted a few dozen per frame so big boards never freeze the screen, and
 *   never re-rendered while playing. Views stay sharp when zoomed in.
 * - Motion never goes through React. A tap hands a small flat description of
 *   the move to the UI thread; a pre-mounted "flight slot" draws the moving
 *   arrow with transform-only updates while the resting copy is hidden in the
 *   same frame. The slither is computed per frame from one animated number.
 * - Pinch-zoom and pan run as UI-thread gestures; the board is a single
 *   transformed layer, so zooming does not touch React either.
 */

const SLOTS = 4;
const RUNS = Array.from({ length: MAX_RUNS }, (_, i) => i);
const EMPTY_FLIGHT: Flight = { n: 0, px: [], py: [], cum: [], len: 0, hx: 0, hy: 0, dx: 0, dy: 0, rot: 0, travel: 0 };
const HIDDEN: PieceFrame = { on: false, tx: 0, ty: 0, sx: 1, sy: 1 };
const FIRST_CHUNK = 36;
const CHUNK = 28;

const EXIT_EASE = Easing.bezier(0.42, 0.0, 0.86, 0.55);
const BUMP_OUT = Easing.out(Easing.quad);
const BUMP_BACK = Easing.inOut(Easing.quad);

interface Slot {
  s: SharedValue<number>;
  err: SharedValue<number>;
  active: SharedValue<number>;
  token: SharedValue<number>;
  geo: SharedValue<Flight>;
}

function useSlot(): Slot {
  return {
    s: useSharedValue(0),
    err: useSharedValue(0),
    active: useSharedValue(0),
    token: useSharedValue(0),
    geo: useSharedValue<Flight>(EMPTY_FLIGHT),
  };
}

function runFlight(slot: Slot, f: Flight, bump: boolean, ms: number, vis: SharedValue<number>) {
  'worklet';
  const token = slot.token.value + 1;
  slot.token.value = token;
  slot.geo.value = f;
  slot.err.value = 0;
  slot.s.value = 0;
  slot.active.value = 1;
  vis.value = 0;
  if (!bump) {
    slot.s.value = withTiming(f.travel, { duration: ms, easing: EXIT_EASE }, () => {
      'worklet';
      if (slot.token.value === token) slot.active.value = 0;
    });
    return;
  }
  slot.err.value = withSequence(
    withTiming(1, { duration: ms * 0.7 }),
    withDelay(ms * 0.5, withTiming(0, { duration: ms * 1.1 })),
  );
  slot.s.value = withSequence(
    withTiming(f.travel, { duration: ms, easing: BUMP_OUT }),
    withTiming(0, { duration: ms * 1.4, easing: BUMP_BACK }, () => {
      'worklet';
      vis.value = 1;
      if (slot.token.value === token) slot.active.value = 0;
    }),
  );
}

/** Border-drawn triangle for a head pointing in direction `dir` (0 up, 1 right, 2 down, 3 left). */
export function headStyle(dir: number, hx: number, hy: number, size: number, color: string): ViewStyle {
  const tip = HEAD_TIP * size;
  const base = HEAD_BASE * size;
  const half = HEAD_HALF * size;
  const len = tip + base;
  const t = 'transparent';
  const common: ViewStyle = { position: 'absolute', width: 0, height: 0, borderStyle: 'solid' };
  switch (dir) {
    case 1:
      return { ...common, left: hx - base, top: hy - half, borderLeftWidth: len, borderTopWidth: half, borderBottomWidth: half, borderLeftColor: color, borderTopColor: t, borderBottomColor: t };
    case 3:
      return { ...common, left: hx - tip, top: hy - half, borderRightWidth: len, borderTopWidth: half, borderBottomWidth: half, borderRightColor: color, borderTopColor: t, borderBottomColor: t };
    case 2:
      return { ...common, left: hx - half, top: hy - base, borderTopWidth: len, borderLeftWidth: half, borderRightWidth: half, borderTopColor: color, borderLeftColor: t, borderRightColor: t };
    default:
      return { ...common, left: hx - half, top: hy - tip, borderBottomWidth: len, borderLeftWidth: half, borderRightWidth: half, borderBottomColor: color, borderLeftColor: t, borderRightColor: t };
  }
}

export interface BoardHandle {
  /** Starts an exit or bump animation and returns its total duration in ms. */
  fly(id: number, kind: 'exit' | 'bump', gap: number): number;
  /** Fills the background picture to `fraction` (0..1) of its final colour. */
  progress(fraction: number): void;
  /**
   * Stops every running board animation. Call this BEFORE the board is removed
   * (next level, restart, leaving the game): an animation that outlives its
   * views makes Reanimated log an error on every frame.
   */
  stopAll(): void;
}

function stopBoard(slots: Slot[], pulse: SharedValue<number>, reveal: SharedValue<number>, zoom: Zoom) {
  'worklet';
  for (let i = 0; i < slots.length; i++) {
    const sl = slots[i];
    sl.token.value = sl.token.value + 1;
    // An idle slot has nothing running. Touching its values would re-run all
    // 33 of its view styles right before the views are removed.
    if (sl.active.value === 0) continue;
    cancelAnimation(sl.s);
    cancelAnimation(sl.err);
    sl.active.value = 0;
  }
  cancelAnimation(pulse);
  cancelAnimation(reveal);
  cancelAnimation(zoom.s);
  cancelAnimation(zoom.x);
  cancelAnimation(zoom.y);
  resetZoom(zoom);
}

function setReveal(reveal: SharedValue<number>, fraction: number) {
  'worklet';
  reveal.value = withTiming(fraction, { duration: 420 });
}

interface Props {
  level: Level;
  areaW: number;
  areaH: number;
  ink: string;
  hintColor: string;
  errorColor: string;
  dotColor: string;
  gridColor: string;
  /** Colour the picture fills with as arrows are cleared. */
  revealColor: string;
  thin: boolean;
  grid: boolean;
  /** Arrow to highlight as a hint, or -1. */
  hintId: number;
  zoom: Zoom;
  /** Current occupancy (removed arrows cleared) for hit testing. */
  getOcc: () => Int16Array;
  onTapArrow: (id: number) => void;
  /** Reports how far this board can be zoomed in (1 = no zoom needed). */
  onMaxZoom?: (max: number) => void;
}

export const Board = memo(
  forwardRef<BoardHandle, Props>(function Board(
    { level, areaW, areaH, ink, hintColor, errorColor, dotColor, gridColor, revealColor, thin, grid, hintId, zoom, getOcc, onTapArrow, onMaxZoom },
    ref,
  ) {
    const pad = 10;
    const fit = Math.min((areaW - pad * 2) / level.w, (areaH - pad * 2) / level.h, level.w <= 5 ? 72 : 60);
    const size = Math.max(6, Math.floor(fit * 2) / 2);
    const bw = size * level.w;
    const bh = size * level.h;
    const ox = Math.round((areaW - bw) / 2);
    const oy = Math.round((areaH - bh) / 2);
    const stroke = Math.max(1.4, Math.round(size * (thin ? 0.11 : 0.16) * 4) / 4);
    const maxZoom = Math.max(1, Math.min(5, 46 / size));

    const geoms = useMemo(() => level.arrows.map((a) => arrowGeom(level, a, size)), [level, size]);
    const vis = useMemo(() => level.arrows.map(() => makeMutable(1)), [level]);

    // Keep the zoom state in step with this board.
    useEffect(() => {
      zoom.aw.value = areaW;
      zoom.ah.value = areaH;
      zoom.bw.value = bw;
      zoom.bh.value = bh;
      zoom.max.value = maxZoom;
      onMaxZoom?.(maxZoom);
    }, [zoom, areaW, areaH, bw, bh, maxZoom, onMaxZoom]);
    const s0 = useSlot();
    const s1 = useSlot();
    const s2 = useSlot();
    const s3 = useSlot();
    const slots = useMemo(() => [s0, s1, s2, s3], [s0, s1, s2, s3]);
    const busy = useRef<number[]>(new Array(SLOTS).fill(0));
    const reveal = useSharedValue(0);
    const pulse = useSharedValue(0.3);

    const layout = useRef({ size, ox, oy, areaW, areaH, geoms, vis, stroke });
    layout.current = { size, ox, oy, areaW, areaH, geoms, vis, stroke };

    useImperativeHandle(
      ref,
      (): BoardHandle => ({
        fly(id: number, kind: 'exit' | 'bump', gap: number) {
          const L = layout.current;
          const g = L.geoms[id];
          if (!g) return 0;
          const f = makeFlight(g, L.size, L.ox, L.oy, L.areaW, L.areaH, kind, gap);
          const ms = flightMs(f, L.size, kind);
          const total = kind === 'bump' ? Math.round(ms * 2.4) : ms;
          const b = busy.current;
          let k = 0;
          for (let i = 1; i < b.length; i++) if (b[i] < b[k]) k = i;
          b[k] = Date.now() + total + 40;
          onUI(runFlight, slots[k], f, kind === 'bump', ms, L.vis[id]);
          return total;
        },
        progress(fraction: number) {
          onUI(setReveal, reveal, fraction);
        },
        stopAll() {
          onUI(stopBoard, slots, pulse, reveal, zoom);
        },
      }),
      [slots, reveal, pulse, zoom],
    );

    // ---- gestures: tap (JS), pinch + pan (UI thread) ----
    const tapRef = useRef(onTapArrow);
    tapRef.current = onTapArrow;
    const occRef = useRef(getOcc);
    occRef.current = getOcc;
    const levelRef = useRef(level);
    levelRef.current = level;

    // Called on the JS thread with board-content coordinates (converted on the UI thread,
    // so JS never has to read animated values).
    const tapContent = useCallback((qx: number, qy: number) => {
      const L = layout.current;
      const id = hitTest(levelRef.current, occRef.current(), qx - L.ox, qy - L.oy, L.size);
      if (id >= 0) tapRef.current(id);
    }, []);

    const gs = useSharedValue({ s0: 1, x0: 0, y0: 0, fx: 0, fy: 0 });
    const gesture = useMemo(() => {
      const pinch = Gesture.Pinch()
        .onStart((e: { focalX: number; focalY: number }) => {
          'worklet';
          gs.value = { s0: zoom.s.value, x0: zoom.x.value, y0: zoom.y.value, fx: e.focalX, fy: e.focalY };
        })
        .onUpdate((e: { focalX: number; focalY: number; scale: number }) => {
          'worklet';
          const g0 = gs.value;
          const s = clamp(g0.s0 * e.scale, 1, Math.max(1, zoom.max.value));
          const cx = zoom.aw.value / 2;
          const cy = zoom.ah.value / 2;
          const k = s / g0.s0;
          const lx = panLimit(zoom.bw.value, zoom.aw.value, s);
          const ly = panLimit(zoom.bh.value, zoom.ah.value, s);
          zoom.s.value = s;
          zoom.x.value = clamp(e.focalX - cx - (g0.fx - cx - g0.x0) * k, -lx, lx);
          zoom.y.value = clamp(e.focalY - cy - (g0.fy - cy - g0.y0) * k, -ly, ly);
        });
      const pan = Gesture.Pan()
        .maxPointers(1)
        .minDistance(16)
        .onStart(() => {
          'worklet';
          gs.value = { s0: zoom.s.value, x0: zoom.x.value, y0: zoom.y.value, fx: 0, fy: 0 };
        })
        .onUpdate((e: { translationX: number; translationY: number }) => {
          'worklet';
          const s = zoom.s.value;
          const lx = panLimit(zoom.bw.value, zoom.aw.value, s);
          const ly = panLimit(zoom.bh.value, zoom.ah.value, s);
          zoom.x.value = clamp(gs.value.x0 + e.translationX, -lx, lx);
          zoom.y.value = clamp(gs.value.y0 + e.translationY, -ly, ly);
        });
      const tap = Gesture.Tap()
        .maxDistance(14)
        .maxDuration(600)
        .onEnd((e: { x: number; y: number }, success: boolean) => {
          'worklet';
          if (!success) return;
          const s = zoom.s.value || 1;
          const cx = zoom.aw.value / 2;
          const cy = zoom.ah.value / 2;
          scheduleOnRN(tapContent, cx + (e.x - cx - zoom.x.value) / s, cy + (e.y - cy - zoom.y.value) / s);
        });
      return Gesture.Race(Gesture.Simultaneous(pinch, pan), tap);
    }, [zoom, gs, tapContent]);

    const contentStyle = useAnimatedStyle(() => ({
      transform: [{ translateX: zoom.x.value }, { translateY: zoom.y.value }, { scale: zoom.s.value }],
    }));

    // ---- static layers ----
    const dots = useMemo(() => {
      const covered = new Uint8Array(level.w * level.h);
      for (const a of level.arrows) for (const c of a.cells) covered[c] = 1;
      const r = Math.max(1.2, size * 0.07);
      const out = [];
      for (let i = 0; i < level.w * level.h; i++) {
        if (!level.mask[i] || covered[i]) continue;
        const cx = ((i % level.w) + 0.5) * size;
        const cy = (Math.floor(i / level.w) + 0.5) * size;
        out.push(
          <View
            key={i}
            style={{ position: 'absolute', left: cx - r, top: cy - r, width: r * 2, height: r * 2, borderRadius: r, backgroundColor: dotColor }}
          />,
        );
      }
      return out;
    }, [level, size, dotColor]);

    const gridLines = useMemo(() => {
      if (!grid) return null;
      const { w, h, mask } = level;
      const on = (x: number, y: number) => x >= 0 && y >= 0 && x < w && y < h && mask[y * w + x] === 1;
      const t = Math.max(0.6, size * 0.03);
      const out = [];
      // Horizontal cell borders: run along each border line where either side is on the board.
      for (let y = 0; y <= h; y++) {
        let x = 0;
        while (x < w) {
          if (!(on(x, y - 1) || on(x, y))) {
            x++;
            continue;
          }
          const x0 = x;
          while (x < w && (on(x, y - 1) || on(x, y))) x++;
          out.push(<View key={`h${y}:${x0}`} style={{ position: 'absolute', left: x0 * size, top: y * size - t / 2, width: (x - x0) * size, height: t, backgroundColor: gridColor }} />);
        }
      }
      for (let x = 0; x <= w; x++) {
        let y = 0;
        while (y < h) {
          if (!(on(x - 1, y) || on(x, y))) {
            y++;
            continue;
          }
          const y0 = y;
          while (y < h && (on(x - 1, y) || on(x, y))) y++;
          out.push(<View key={`v${x}:${y0}`} style={{ position: 'absolute', left: x * size - t / 2, top: y0 * size, width: t, height: (y - y0) * size, backgroundColor: gridColor }} />);
        }
      }
      return out;
    }, [grid, level, size, gridColor]);

    // The picture: one bar per run of board cells in each row (crisp at any zoom).
    const silhouette = useMemo(() => {
      const { w, h, mask } = level;
      const runs: { x: number; y: number; n: number }[] = [];
      for (let y = 0; y < h; y++) {
        let x = 0;
        while (x < w) {
          if (!mask[y * w + x]) {
            x++;
            continue;
          }
          const x0 = x;
          while (x < w && mask[y * w + x]) x++;
          runs.push({ x: x0, y, n: x - x0 });
        }
      }
      return runs;
    }, [level]);
    const picture = (color: string) =>
      silhouette.map((r) => (
        <View
          key={`${r.x}:${r.y}`}
          style={{ position: 'absolute', left: r.x * size, top: r.y * size, width: r.n * size, height: size + 0.5, backgroundColor: color }}
        />
      ));
    const basePicture = useMemo(() => picture(ink), [silhouette, size, ink]); // eslint-disable-line react-hooks/exhaustive-deps
    const revealPicture = useMemo(() => picture(revealColor), [silhouette, size, revealColor]); // eslint-disable-line react-hooks/exhaustive-deps
    const revealStyle = useAnimatedStyle(() => ({ opacity: 0.04 + reveal.value * 0.3 }));

    const statics = useMemo(
      () => geoms.map((g, i) => <StaticArrow key={g.id} g={g} dir={level.arrows[i].dir} vis={vis[g.id]} stroke={stroke} size={size} color={ink} />),
      [geoms, level, vis, stroke, size, ink],
    );

    // Mount big boards progressively (a few dozen arrows per frame).
    const [shown, setShown] = useState(Math.min(statics.length, FIRST_CHUNK));
    useEffect(() => {
      if (shown >= statics.length) return;
      const id = requestAnimationFrame(() => setShown((c) => Math.min(statics.length, c + CHUNK)));
      return () => cancelAnimationFrame(id);
    }, [shown, statics.length]);

    const hint = hintId >= 0 ? geoms[hintId] : undefined;

    return (
      <GestureDetector gesture={gesture}>
        <View style={styles.area} collapsable={false}>
          <Animated.View collapsable={false} style={[StyleSheet.absoluteFill, contentStyle]} pointerEvents="none">
            <Animated.View collapsable={false} entering={FadeIn.duration(240)} style={[styles.board, { left: ox, top: oy, width: bw, height: bh }]}>
              <View style={[StyleSheet.absoluteFill, styles.base]}>{basePicture}</View>
              <Animated.View collapsable={false} style={[StyleSheet.absoluteFill, revealStyle]}>{revealPicture}</Animated.View>
              {gridLines}
              {dots}
              {hint ? <HintGlow key={hint.id} g={hint} stroke={stroke} size={size} color={hintColor} pulse={pulse} /> : null}
              {shown >= statics.length ? statics : statics.slice(0, shown)}
            </Animated.View>
            <View style={StyleSheet.absoluteFill}>
              {slots.map((slot, i) => (
                <FlightSlot key={i} slot={slot} stroke={stroke} size={size} ink={ink} error={errorColor} />
              ))}
            </View>
          </Animated.View>
        </View>
      </GestureDetector>
    );
  }),
);

/* ------------------------------------------------------------------ */
/* Resting arrow                                                       */
/* ------------------------------------------------------------------ */

interface StaticProps {
  g: ArrowGeom;
  dir: number;
  vis: SharedValue<number>;
  stroke: number;
  size: number;
  color: string;
}

const StaticArrow = memo(function StaticArrow({ g, dir, vis, stroke, size, color }: StaticProps) {
  const style = useAnimatedStyle(() => ({ opacity: vis.value }));
  return (
    <Animated.View collapsable={false} pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {g.segs.map((s, i) => {
        const [left, top, width, height] = capsuleRect(s, stroke);
        return <View key={i} style={{ position: 'absolute', left, top, width, height, borderRadius: stroke / 2, backgroundColor: color }} />;
      })}
      <View style={headStyle(dir, g.hx, g.hy, size, color)} />
    </Animated.View>
  );
});

/** Soft pulsing halo behind the hinted arrow. */
const HintGlow = memo(function HintGlow({
  g,
  stroke,
  size,
  color,
  pulse,
}: {
  g: ArrowGeom;
  stroke: number;
  size: number;
  color: string;
  pulse: SharedValue<number>;
}) {
  useEffect(() => {
    // Start a moment after mounting, once the views exist natively.
    const id = setTimeout(() => {
      pulse.value = 0.3;
      pulse.value = withRepeat(withTiming(0.8, { duration: 620, easing: Easing.inOut(Easing.quad) }), -1, true);
    }, 120);
    return () => {
      clearTimeout(id);
      cancelAnimation(pulse);
    };
  }, [pulse]);
  const style = useAnimatedStyle(() => ({ opacity: pulse.value }));
  const wide = Math.max(stroke * 2.6, size * 0.5);
  const dot = size * 0.95;
  return (
    <Animated.View collapsable={false} pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {g.segs.map((s, i) => {
        const [left, top, width, height] = capsuleRect(s, wide);
        return <View key={i} style={{ position: 'absolute', left, top, width, height, borderRadius: wide / 2, backgroundColor: color }} />;
      })}
      <View style={{ position: 'absolute', left: g.hx - dot / 2, top: g.hy - dot / 2, width: dot, height: dot, borderRadius: dot / 2, backgroundColor: color }} />
    </Animated.View>
  );
});

/* ------------------------------------------------------------------ */
/* Moving arrow                                                        */
/* ------------------------------------------------------------------ */

interface SlotProps {
  slot: Slot;
  stroke: number;
  size: number;
  ink: string;
  error: string;
}

const FlightSlot = memo(function FlightSlot({ slot, stroke, size, ink, error }: SlotProps) {
  return (
    <>
      {RUNS.map((j) => (
        <RunPiece key={`r${j}`} j={j} slot={slot} stroke={stroke} ink={ink} error={error} dot={false} />
      ))}
      {RUNS.map((j) => (
        <RunPiece key={`d${j}`} j={j} slot={slot} stroke={stroke} ink={ink} error={error} dot />
      ))}
      <FlightHead slot={slot} size={size} ink={ink} error={error} />
    </>
  );
});

interface PieceProps {
  j: number;
  slot: Slot;
  stroke: number;
  ink: string;
  error: string;
  /** false: the straight part of run j; true: the round cap where run j's visible part starts. */
  dot: boolean;
}

/**
 * One straight run of a moving arrow (or the round cap at its start). Only
 * transform/opacity/colour change per frame; the view itself is a stroke-sized
 * square scaled into place.
 */
const RunPiece = memo(function RunPiece({ j, slot, stroke, ink, error, dot }: PieceProps) {
  const style = useAnimatedStyle(() => {
    const color = interpolateColor(slot.err.value, [0, 1], [ink, error]);
    const p = slot.active.value === 0 ? HIDDEN : pieceFrame(slot.geo.value, slot.s.value, j, stroke, dot);
    return {
      opacity: p.on ? 1 : 0,
      backgroundColor: color,
      transform: [{ translateX: p.tx }, { translateY: p.ty }, { scaleX: p.sx }, { scaleY: p.sy }],
    };
  });
  return (
    <Animated.View collapsable={false}
      pointerEvents="none"
      style={[{ position: 'absolute', left: 0, top: 0, width: stroke, height: stroke, borderRadius: dot ? stroke / 2 : 0 }, style]}
    />
  );
});

const FlightHead = memo(function FlightHead({ slot, size, ink, error }: { slot: Slot; size: number; ink: string; error: string }) {
  const box = size;
  const style = useAnimatedStyle(() => {
    const f = slot.geo.value;
    const s = slot.s.value;
    const on = slot.active.value === 1 && f.n > 1;
    return {
      opacity: on ? 1 : 0,
      transform: [{ translateX: f.hx + f.dx * s - box / 2 }, { translateY: f.hy + f.dy * s - box / 2 }, { rotate: `${f.rot}deg` }],
    };
  });
  const redStyle = useAnimatedStyle(() => ({ opacity: slot.err.value }));
  // The head drawn pointing right around the box centre; the box rotates.
  const c = box / 2;
  return (
    <Animated.View collapsable={false} pointerEvents="none" style={[{ position: 'absolute', left: 0, top: 0, width: box, height: box }, style]}>
      <View style={headStyle(1, c, c, size, ink)} />
      <Animated.View collapsable={false} style={[StyleSheet.absoluteFill, redStyle]}>
        <View style={headStyle(1, c, c, size, error)} />
      </Animated.View>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  area: { flex: 1, overflow: 'hidden' },
  board: { position: 'absolute' },
  base: { opacity: 0.055 },
});
