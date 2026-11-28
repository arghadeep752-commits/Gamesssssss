import { memo, useMemo } from 'react';
import Svg, { Path } from 'react-native-svg';
import type { Level } from '../game/engine';
import { arrowGeom, HEAD_BASE, HEAD_HALF, HEAD_TIP } from '../game/geometry';

/** Small static picture of a level (home screen card). One Svg, drawn once. */
export const MiniBoard = memo(function MiniBoard({
  level,
  maxW,
  maxH,
  ink,
  dot,
}: {
  level: Level;
  maxW: number;
  maxH: number;
  ink: string;
  dot: string;
}) {
  const size = Math.floor(Math.min(maxW / level.w, maxH / level.h));
  const data = useMemo(() => {
    let lines = '';
    let heads = '';
    let dots = '';
    const r = Math.max(1, size * 0.07);
    for (let i = 0; i < level.w * level.h; i++) {
      if (!level.mask[i]) continue;
      const cx = ((i % level.w) + 0.5) * size;
      const cy = (Math.floor(i / level.w) + 0.5) * size;
      dots += `M${cx - r} ${cy}a${r} ${r} 0 1 0 ${2 * r} 0a${r} ${r} 0 1 0 ${-2 * r} 0`;
    }
    for (const a of level.arrows) {
      const g = arrowGeom(level, a, size);
      lines += g.vx.map((x, i) => `${i ? 'L' : 'M'}${x.toFixed(1)} ${g.vy[i].toFixed(1)}`).join('');
      // Triangle rotated by hand: forward = (dx, dy), side = (-dy, dx).
      const fx = g.dx;
      const fy = g.dy;
      const sx = -fy;
      const sy = fx;
      const tip = [g.hx + fx * HEAD_TIP * size, g.hy + fy * HEAD_TIP * size];
      const b = [g.hx - fx * HEAD_BASE * size, g.hy - fy * HEAD_BASE * size];
      const h = HEAD_HALF * size;
      heads += `M${tip[0].toFixed(1)} ${tip[1].toFixed(1)}L${(b[0] + sx * h).toFixed(1)} ${(b[1] + sy * h).toFixed(1)}L${(b[0] - sx * h).toFixed(1)} ${(b[1] - sy * h).toFixed(1)}Z`;
    }
    return { lines, heads, dots };
  }, [level, size]);
  return (
    <Svg width={size * level.w} height={size * level.h}>
      <Path d={data.dots} fill={dot} />
      <Path d={data.lines} stroke={ink} strokeWidth={size * 0.2} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d={data.heads} fill={ink} stroke={ink} strokeWidth={size * 0.06} strokeLinejoin="round" />
    </Svg>
  );
});
