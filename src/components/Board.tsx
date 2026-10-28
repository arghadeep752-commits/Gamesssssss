import { memo, useCallback, useMemo, useRef } from 'react';
import { StyleSheet, View, type GestureResponderEvent } from 'react-native';
import Svg, { Path } from 'react-native-svg';
import { TIMING } from '../config/gameConfig';
import { COLORS } from '../config/theme';
import type { PreparedLevel } from '../game/board';
import { exitDistanceCells } from '../game/geometry';
import { arrowGeometry, dotsPath, exitDurationMs, gridDotsPath } from '../utils/arrowPath';
import { hitTest } from '../utils/hitTest';
import { ArrowView, type ArrowTone } from './ArrowView';

export interface CorridorOverlay {
  /** Corridor cells to mark. */
  readonly cells: readonly { x: number; y: number; blocked: boolean }[];
  /** Colour for clear cells. */
  readonly tone: 'hint' | 'scan';
}

interface Props {
  prepared: PreparedLevel;
  cell: number;
  removed: readonly boolean[];
  moving: ReadonlySet<number>;
  shakes: Readonly<Record<number, number>>;
  tones: Readonly<Record<number, ArrowTone>>;
  pulseArrow: number | null;
  overlay: CorridorOverlay | null;
  reducedEffects: boolean;
  disabled: boolean;
  onTap: (arrowId: number) => void;
  onExited: (arrowId: number) => void;
}

/**
 * The puzzle board: dotted grid, arrows, and an optional corridor overlay.
 * A single touch responder handles every tap (no per-arrow touchables) and
 * resolves it through the engine's cell grid, so hit testing always matches
 * the drawn geometry. Touch is handled on press-down for instant response.
 */
export const Board = memo(function Board({
  prepared,
  cell,
  removed,
  moving,
  shakes,
  tones,
  pulseArrow,
  overlay,
  reducedEffects,
  disabled,
  onTap,
  onExited,
}: Props) {
  const { level } = prepared;
  const width = level.width * cell;
  const height = level.height * cell;

  // Geometry is computed once per layout, never per frame.
  const geoms = useMemo(
    () => level.arrows.map((a) => arrowGeometry(a, cell, level.width, level.height)),
    [level, cell],
  );
  const durations = useMemo(
    () =>
      level.arrows.map((a) =>
        exitDurationMs(exitDistanceCells(a, level.width, level.height), TIMING.exitBase, TIMING.exitPerCell, TIMING.exitMax),
      ),
    [level],
  );
  const grid = useMemo(() => gridDotsPath(level.width, level.height, cell), [level, cell]);

  const removedRef = useRef(removed);
  removedRef.current = removed;
  const disabledRef = useRef(disabled);
  disabledRef.current = disabled;

  const onGrant = useCallback(
    (e: GestureResponderEvent) => {
      if (disabledRef.current) return;
      const { locationX, locationY } = e.nativeEvent;
      const id = hitTest(prepared.occupancy, level.width, level.height, removedRef.current, locationX, locationY, cell);
      if (id >= 0) onTap(id);
    },
    [prepared, level, cell, onTap],
  );

  const overlayPaths = useMemo(() => {
    if (!overlay) return null;
    const r = Math.max(2.5, cell * 0.11);
    return {
      clear: dotsPath(overlay.cells.filter((c) => !c.blocked), cell, r),
      blocked: dotsPath(overlay.cells.filter((c) => c.blocked), cell, r * 1.35),
      tone: overlay.tone,
    };
  }, [overlay, cell]);

  return (
    <View
      style={[styles.board, { width, height }]}
      onStartShouldSetResponder={() => !disabledRef.current}
      onResponderTerminationRequest={() => true}
      onResponderGrant={onGrant}
      accessibilityLabel="Puzzle board"
    >
      <Svg width={width} height={height} style={StyleSheet.absoluteFill} pointerEvents="none">
        <Path d={grid} fill={COLORS.dot} />
      </Svg>
      {overlayPaths ? (
        <Svg width={width} height={height} style={StyleSheet.absoluteFill} pointerEvents="none">
          {overlayPaths.clear ? (
            <Path d={overlayPaths.clear} fill={overlayPaths.tone === 'hint' ? COLORS.hint : COLORS.inkSoft} opacity={0.75} />
          ) : null}
          {overlayPaths.blocked ? <Path d={overlayPaths.blocked} fill={COLORS.error} /> : null}
        </Svg>
      ) : null}
      <View style={StyleSheet.absoluteFill} pointerEvents="none">
        {level.arrows.map((a) => {
          const isMoving = moving.has(a.id);
          if (removed[a.id] && !isMoving) return null;
          return (
            <ArrowView
              key={a.id}
              id={a.id}
              geom={geoms[a.id]}
              phase={isMoving ? 'moving' : 'idle'}
              exitMs={durations[a.id]}
              tone={tones[a.id] ?? 'normal'}
              shakeSeq={shakes[a.id] ?? 0}
              pulse={pulseArrow === a.id}
              reducedEffects={reducedEffects}
              cell={cell}
              onExited={onExited}
            />
          );
        })}
      </View>
    </View>
  );
});

const styles = StyleSheet.create({
  board: { overflow: 'hidden' },
});
