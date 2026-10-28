import { memo, useMemo } from 'react';
import Svg, { G, Path } from 'react-native-svg';
import { COLORS } from '../config/theme';
import type { LevelDef } from '../game/types';
import { arrowGeometry, gridDotsPath } from '../utils/arrowPath';

/**
 * Non-interactive board drawn with exactly the same geometry as the game,
 * used for the Help screen and the daily preview. One Svg, no animation.
 */
export const StaticBoard = memo(function StaticBoard({
  level,
  cell,
  colors,
}: {
  level: LevelDef;
  cell: number;
  /** Optional colour per arrow id. */
  colors?: Readonly<Record<number, string>>;
}) {
  const width = level.width * cell;
  const height = level.height * cell;
  const parts = useMemo(
    () =>
      level.arrows.map((a) => ({
        id: a.id,
        g: arrowGeometry(a, cell, level.width, level.height),
      })),
    [level, cell],
  );
  const grid = useMemo(() => gridDotsPath(level.width, level.height, cell), [level, cell]);
  return (
    <Svg width={width} height={height} pointerEvents="none">
      <Path d={grid} fill={COLORS.dot} />
      {parts.map(({ id, g }) => {
        const color = colors?.[id] ?? COLORS.arrow;
        return (
          <G key={id} transform={`translate(${g.left} ${g.top})`}>
            <Path d={g.body} stroke={color} strokeWidth={g.strokeWidth} strokeLinecap="round" strokeLinejoin="round" fill="none" />
            <Path d={g.head} fill={color} stroke={color} strokeWidth={g.strokeWidth * 0.5} strokeLinejoin="round" />
          </G>
        );
      })}
    </Svg>
  );
});
