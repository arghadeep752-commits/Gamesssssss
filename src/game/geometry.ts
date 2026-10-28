import type { ArrowDef, Cell, Direction, LevelDef, PackedLevel, Tier } from './types';

export const DIRECTIONS: readonly Direction[] = ['U', 'R', 'D', 'L'];

export const DIR_VECTORS: Readonly<Record<Direction, Cell>> = {
  U: { x: 0, y: -1 },
  D: { x: 0, y: 1 },
  L: { x: -1, y: 0 },
  R: { x: 1, y: 0 },
};

export function isDirection(value: string): value is Direction {
  return value === 'U' || value === 'D' || value === 'L' || value === 'R';
}

export function cellIndex(x: number, y: number, width: number): number {
  return y * width + x;
}

export function inBounds(x: number, y: number, width: number, height: number): boolean {
  return x >= 0 && y >= 0 && x < width && y < height;
}

/** Direction of the step a -> b, or null when the cells are not 4-adjacent. */
export function stepDirection(a: Cell, b: Cell): Direction | null {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  if (dx === 1 && dy === 0) return 'R';
  if (dx === -1 && dy === 0) return 'L';
  if (dx === 0 && dy === 1) return 'D';
  if (dx === 0 && dy === -1) return 'U';
  return null;
}

/**
 * Arrow token format: two base-36 characters for the tail (x then y) followed by
 * one letter per step (U, D, L, R). The exit direction is the last step.
 * Example: "12RRD" is a tail at (1,2) that goes right, right, down and exits down.
 */
export function decodeArrow(token: string, id: number): ArrowDef {
  if (token.length < 3) throw new Error(`Arrow token "${token}" is too short`);
  const x = parseInt(token[0], 36);
  const y = parseInt(token[1], 36);
  if (Number.isNaN(x) || Number.isNaN(y)) throw new Error(`Arrow token "${token}" has a bad tail`);
  const cells: Cell[] = [{ x, y }];
  let cx = x;
  let cy = y;
  let dir: Direction = 'R';
  for (let i = 2; i < token.length; i++) {
    const step = token[i];
    if (!isDirection(step)) throw new Error(`Arrow token "${token}" has a bad step "${step}"`);
    const v = DIR_VECTORS[step];
    cx += v.x;
    cy += v.y;
    cells.push({ x: cx, y: cy });
    dir = step;
  }
  return { id, cells, dir };
}

export function encodeArrow(arrow: ArrowDef): string {
  const tail = arrow.cells[0];
  let token = tail.x.toString(36) + tail.y.toString(36);
  for (let i = 1; i < arrow.cells.length; i++) {
    const d = stepDirection(arrow.cells[i - 1], arrow.cells[i]);
    if (!d) throw new Error(`Arrow ${arrow.id} has non-adjacent cells`);
    token += d;
  }
  return token;
}

export function packLevel(width: number, height: number, arrows: readonly ArrowDef[]): PackedLevel {
  return { w: width, h: height, a: arrows.map(encodeArrow).join(' ') };
}

export function unpackLevel(
  packed: PackedLevel,
  meta: { id: string; number: number; tier: Tier },
): LevelDef {
  const tokens = packed.a.trim().length ? packed.a.trim().split(/\s+/) : [];
  return {
    id: meta.id,
    number: meta.number,
    tier: meta.tier,
    width: packed.w,
    height: packed.h,
    arrows: tokens.map((t, i) => decodeArrow(t, i)),
  };
}

/**
 * Cells swept by an arrow sliding rigidly in its exit direction until it leaves
 * the board, excluding the arrow's own cells. Returned as flat cell indices in a
 * stable order (by source cell, then by distance).
 */
export function corridorIndices(arrow: ArrowDef, width: number, height: number): number[] {
  const v = DIR_VECTORS[arrow.dir];
  const own = new Set<number>();
  for (const c of arrow.cells) own.add(cellIndex(c.x, c.y, width));
  const seen = new Set<number>();
  const out: number[] = [];
  for (const c of arrow.cells) {
    let x = c.x + v.x;
    let y = c.y + v.y;
    while (inBounds(x, y, width, height)) {
      const idx = cellIndex(x, y, width);
      if (!own.has(idx) && !seen.has(idx)) {
        seen.add(idx);
        out.push(idx);
      }
      x += v.x;
      y += v.y;
    }
  }
  return out;
}

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export function arrowBounds(arrow: ArrowDef): Bounds {
  let minX = Infinity;
  let minY = Infinity;
  let maxX = -Infinity;
  let maxY = -Infinity;
  for (const c of arrow.cells) {
    if (c.x < minX) minX = c.x;
    if (c.y < minY) minY = c.y;
    if (c.x > maxX) maxX = c.x;
    if (c.y > maxY) maxY = c.y;
  }
  return { minX, minY, maxX, maxY };
}

/**
 * Number of cells an arrow must travel so that every one of its cells has
 * left the board.
 */
export function exitDistanceCells(arrow: ArrowDef, width: number, height: number): number {
  const b = arrowBounds(arrow);
  switch (arrow.dir) {
    case 'R':
      return width - b.minX;
    case 'L':
      return b.maxX + 1;
    case 'D':
      return height - b.minY;
    case 'U':
      return b.maxY + 1;
  }
}
