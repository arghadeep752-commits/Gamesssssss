import { forwardRef, memo, useCallback, useEffect, useImperativeHandle, useMemo, useRef } from 'react';
import { StyleSheet, View, type GestureResponderEvent } from 'react-native';
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
import Svg, { Path } from 'react-native-svg';
import type { Level } from '../game/engine';
import {
  arrowGeom,
  capsuleRect,
  type ArrowGeom,
  type Flight,
  flightMs,
  HEAD_BOX,
  headPath,
  hitTest,
  makeFlight,
  MAX_RUNS,
  type PieceFrame,
  pieceFrame,
  STROKE,
} from '../game/geometry';
import type { Palette } from './theme';
import { onUI } from './worklets';

/**
 * The puzzle board.
 *
 * Performance notes (this is what keeps it smooth on low-end phones):
 * - Arrows at rest are plain native Views (rounded capsules + a small head), built
 *   once per level and never re-rendered while playing.
 * - Motion never goes through React. A tap hands a small flat description of
 *   the move to the UI thread; a pre-mounted "flight slot" then draws the moving
 *   arrow with transform-only updates while the resting copy is hidden in the
 *   same frame. The slither (body following its own trail) is computed per
 *   frame on the UI thread from one animated number.
 * - Hit testing is a single touch responder plus an array lookup.
 */

const SLOTS = 6;
const RUNS = Array.from({ length: MAX_RUNS }, (_, i) => i);
const EMPTY_FLIGHT: Flight = { n: 0, px: [], py: [], cum: [], len: 0, hx: 0, hy: 0, dx: 0, dy: 0, rot: 0, travel: 0 };

const HIDDEN: PieceFrame = { on: false, tx: 0, ty: 0, sx: 1, sy: 1 };

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

export interface BoardHandle {
  /** Starts an exit or bump animation and returns its total duration in ms. */
  fly(id: number, kind: 'exit' | 'bump', gap: number): number;
}

interface Props {
  level: Level;
  areaW: number;
  areaH: number;
  palette: Palette;
  /** Arrow to highlight as a hint, or -1. */
  hintId: number;
  /** Current occupancy (removed arrows cleared) for hit testing. */
  getOcc: () => Int16Array;
  onTapArrow: (id: number) => void;
}

export const Board = memo(
  forwardRef<BoardHandle, Props>(function Board({ level, areaW, areaH, palette, hintId, getOcc, onTapArrow }, ref) {
    const pad = 14;
    const size = Math.max(
      10,
      Math.floor(Math.min((areaW - pad * 2) / level.w, (areaH - pad * 2) / level.h, level.w <= 4 ? 70 : 60)),
    );
    const bw = size * level.w;
    const bh = size * level.h;
    const ox = Math.round((areaW - bw) / 2);
    const oy = Math.round((areaH - bh) / 2);
    const stroke = Math.max(3, Math.round(size * STROKE * 2) / 2);

    const geoms = useMemo(() => level.arrows.map((a) => arrowGeom(level, a, size)), [level, size]);
    const vis = useMemo(() => level.arrows.map(() => makeMutable(1)), [level]);
    const headD = useMemo(() => headPath(size), [size]);

    const s0 = useSlot();
    const s1 = useSlot();
    const s2 = useSlot();
    const s3 = useSlot();
    const s4 = useSlot();
    const s5 = useSlot();
    const slots = useMemo(() => [s0, s1, s2, s3, s4, s5], [s0, s1, s2, s3, s4, s5]);
    const busy = useRef<number[]>(new Array(SLOTS).fill(0));

    const layout = useRef({ size, ox, oy, areaW, areaH, geoms, vis });
    layout.current = { size, ox, oy, areaW, areaH, geoms, vis };

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
      }),
      [slots],
    );

    const tapRef = useRef(onTapArrow);
    tapRef.current = onTapArrow;
    const onGrant = useCallback(
      (e: GestureResponderEvent) => {
        const L = layout.current;
        const { locationX, locationY } = e.nativeEvent;
        const id = hitTest(level, getOcc(), locationX - L.ox, locationY - L.oy, L.size);
        if (id >= 0) tapRef.current(id);
      },
      [level, getOcc],
    );

    const dots = useMemo(() => {
      const r = Math.max(1.6, size * 0.075);
      let d = '';
      for (let i = 0; i < level.w * level.h; i++) {
        if (!level.mask[i]) continue;
        const cx = ((i % level.w) + 0.5) * size;
        const cy = (Math.floor(i / level.w) + 0.5) * size;
        d += `M${(cx - r).toFixed(1)} ${cy.toFixed(1)}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
      }
      return d;
    }, [level, size]);

    const arrows = useMemo(
      () =>
        geoms.map((g) => (
          <StaticArrow key={g.id} g={g} vis={vis[g.id]} stroke={stroke} size={size} color={palette.ink} headD={headD} />
        )),
      [geoms, vis, stroke, size, palette.ink, headD],
    );

    const hint = hintId >= 0 ? geoms[hintId] : undefined;

    return (
      <View
        style={styles.area}
        onStartShouldSetResponder={() => true}
        onResponderTerminationRequest={() => false}
        onResponderGrant={onGrant}
      >
        <Animated.View
          entering={FadeIn.duration(260)}
          pointerEvents="none"
          style={[styles.board, { left: ox, top: oy, width: bw, height: bh }]}
        >
          <Svg width={bw} height={bh} style={StyleSheet.absoluteFill}>
            <Path d={dots} fill={palette.dot} />
          </Svg>
          {hint ? <HintGlow key={hint.id} g={hint} stroke={stroke} color={palette.hint} /> : null}
          {arrows}
        </Animated.View>
        <View pointerEvents="none" style={StyleSheet.absoluteFill}>
          {slots.map((slot, i) => (
            <FlightSlot
              key={i}
              slot={slot}
              stroke={stroke}
              size={size}
              headD={headD}
              ink={palette.ink}
              error={palette.error}
            />
          ))}
        </View>
      </View>
    );
  }),
);

/* ------------------------------------------------------------------ */
/* Resting arrow                                                       */
/* ------------------------------------------------------------------ */

interface StaticProps {
  g: ArrowGeom;
  vis: SharedValue<number>;
  stroke: number;
  size: number;
  color: string;
  headD: string;
}

const StaticArrow = memo(function StaticArrow({ g, vis, stroke, size, color, headD }: StaticProps) {
  const style = useAnimatedStyle(() => ({ opacity: vis.value }));
  const box = HEAD_BOX * size;
  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {g.segs.map((s, i) => {
        const [left, top, width, height] = capsuleRect(s, stroke);
        return (
          <View
            key={i}
            style={{ position: 'absolute', left, top, width, height, borderRadius: stroke / 2, backgroundColor: color }}
          />
        );
      })}
      <View
        style={{
          position: 'absolute',
          left: g.hx - box / 2,
          top: g.hy - box / 2,
          width: box,
          height: box,
          transform: [{ rotate: `${g.rot}deg` }],
        }}
      >
        <Svg width={box} height={box}>
          <Path d={headD} fill={color} stroke={color} strokeWidth={size * 0.06} strokeLinejoin="round" />
        </Svg>
      </View>
    </Animated.View>
  );
});

/** Soft pulsing halo behind the hinted arrow. */
const HintGlow = memo(function HintGlow({ g, stroke, color }: { g: ArrowGeom; stroke: number; color: string }) {
  const pulse = useSharedValue(0.25);
  useEffect(() => {
    pulse.value = withRepeat(withTiming(0.75, { duration: 650, easing: Easing.inOut(Easing.quad) }), -1, true);
    return () => cancelAnimation(pulse);
  }, [pulse]);
  const style = useAnimatedStyle(() => ({ opacity: pulse.value }));
  const wide = stroke * 2.6;
  const dot = wide * 1.5;
  return (
    <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, style]}>
      {g.segs.map((s, i) => {
        const [left, top, width, height] = capsuleRect(s, wide);
        return (
          <View
            key={i}
            style={{ position: 'absolute', left, top, width, height, borderRadius: wide / 2, backgroundColor: color }}
          />
        );
      })}
      <View
        style={{
          position: 'absolute',
          left: g.hx - dot / 2,
          top: g.hy - dot / 2,
          width: dot,
          height: dot,
          borderRadius: dot / 2,
          backgroundColor: color,
        }}
      />
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
  headD: string;
  ink: string;
  error: string;
}

const FlightSlot = memo(function FlightSlot({ slot, stroke, size, headD, ink, error }: SlotProps) {
  return (
    <>
      {RUNS.map((j) => (
        <RunPiece key={`r${j}`} j={j} slot={slot} stroke={stroke} ink={ink} error={error} dot={false} />
      ))}
      {RUNS.map((j) => (
        <RunPiece key={`d${j}`} j={j} slot={slot} stroke={stroke} ink={ink} error={error} dot />
      ))}
      <FlightHead slot={slot} size={size} headD={headD} ink={ink} error={error} />
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
    <Animated.View
      pointerEvents="none"
      style={[
        { position: 'absolute', left: 0, top: 0, width: stroke, height: stroke, borderRadius: dot ? stroke / 2 : 0 },
        style,
      ]}
    />
  );
});

const FlightHead = memo(function FlightHead({
  slot,
  size,
  headD,
  ink,
  error,
}: {
  slot: Slot;
  size: number;
  headD: string;
  ink: string;
  error: string;
}) {
  const box = HEAD_BOX * size;
  const style = useAnimatedStyle(() => {
    const f = slot.geo.value;
    const s = slot.s.value;
    const on = slot.active.value === 1 && f.n > 1;
    return {
      opacity: on ? 1 : 0,
      transform: [
        { translateX: f.hx + f.dx * s - box / 2 },
        { translateY: f.hy + f.dy * s - box / 2 },
        { rotate: `${f.rot}deg` },
      ],
    };
  });
  const redStyle = useAnimatedStyle(() => ({ opacity: slot.err.value }));
  return (
    <Animated.View pointerEvents="none" style={[{ position: 'absolute', left: 0, top: 0, width: box, height: box }, style]}>
      <Svg width={box} height={box}>
        <Path d={headD} fill={ink} stroke={ink} strokeWidth={size * 0.06} strokeLinejoin="round" />
      </Svg>
      <Animated.View style={[StyleSheet.absoluteFill, redStyle]}>
        <Svg width={box} height={box}>
          <Path d={headD} fill={error} stroke={error} strokeWidth={size * 0.06} strokeLinejoin="round" />
        </Svg>
      </Animated.View>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  area: { flex: 1, overflow: 'hidden' },
  board: { position: 'absolute' },
});
