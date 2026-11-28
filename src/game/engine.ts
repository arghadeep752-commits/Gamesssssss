/**
 * Puzzle rules (pure TypeScript, no React).
 *
 * The board is a grid of cells. Each arrow is a snake-shaped path of adjacent
 * cells, tail first and head last; it points in the direction of its last step.
 * Tapping an arrow makes it slither forward: the head travels straight ahead and
 * the body follows its own trail. So an arrow can leave exactly when the straight
 * line of cells in front of its head (its "ray", up to the board edge) holds no
 * other arrow. Removing arrows only ever frees cells, so any free arrow is always
 * a safe move and a level is solvable when repeatedly removing free arrows
 * clears the board.
 */

export type Dir = 0 | 1 | 2 | 3; // up, right, down, left
export const DX: readonly number[] = [0, 1, 0, -1];
export const DY: readonly number[] = [-1, 0, 1, 0];

export interface Arrow {
  readonly id: number;
  /** Cell indices (y * w + x), tail first, head last. At least 2 cells. */
  readonly cells: readonly number[];
  readonly dir: Dir;
}

export interface Level {
  readonly w: number;
  readonly h: number;
  /** 1 = playable cell (drawn as a dot), 0 = outside the shape. */
  readonly mask: Uint8Array;
  readonly arrows: readonly Arrow[];
}

export function opposite(d: Dir): Dir {
  return ((d + 2) % 4) as Dir;
}

/** Neighbour index in direction d, or -1 when it leaves the grid. */
export function step(w: number, h: number, cell: number, d: Dir): number {
  const x = (cell % w) + DX[d];
  const y = Math.floor(cell / w) + DY[d];
  if (x < 0 || y < 0 || x >= w || y >= h) return -1;
  return y * w + x;
}

export function dirBetween(w: number, from: number, to: number): Dir | -1 {
  const dx = (to % w) - (from % w);
  const dy = Math.floor(to / w) - Math.floor(from / w);
  if (dx === 0 && dy === -1) return 0;
  if (dx === 1 && dy === 0) return 1;
  if (dx === 0 && dy === 1) return 2;
  if (dx === -1 && dy === 0) return 3;
  return -1;
}

export function headOf(a: Arrow): number {
  return a.cells[a.cells.length - 1];
}

/** Cells strictly in front of the head, in order, until the grid edge. */
export function rayCells(level: Level, a: Arrow): number[] {
  const out: number[] = [];
  let c = step(level.w, level.h, headOf(a), a.dir);
  while (c >= 0) {
    out.push(c);
    c = step(level.w, level.h, c, a.dir);
  }
  return out;
}

/** occupancy[cell] = arrow id, or -1. */
export function buildOccupancy(level: Level, removed?: ArrayLike<number>): Int16Array {
  const occ = new Int16Array(level.w * level.h).fill(-1);
  for (const a of level.arrows) {
    if (removed && removed[a.id]) continue;
    for (const c of a.cells) occ[c] = a.id;
  }
  return occ;
}

export interface Blocker {
  /** Id of the first arrow in the way. */
  readonly id: number;
  /** Free cells between the head and that arrow. */
  readonly gap: number;
}

/** The first arrow in this arrow's way, or null when it can leave. */
export function firstBlocker(level: Level, occ: Int16Array, a: Arrow): Blocker | null {
  let c = step(level.w, level.h, headOf(a), a.dir);
  let gap = 0;
  while (c >= 0) {
    const o = occ[c];
    if (o >= 0 && o !== a.id) return { id: o, gap };
    gap++;
    c = step(level.w, level.h, c, a.dir);
  }
  return null;
}

/** Ids of every arrow that can leave right now. */
export function freeArrows(level: Level, occ: Int16Array, removed: ArrayLike<number>): number[] {
  const out: number[] = [];
  for (const a of level.arrows) {
    if (removed[a.id]) continue;
    if (!firstBlocker(level, occ, a)) out.push(a.id);
  }
  return out;
}

/** A full removal order, or null if the level cannot be cleared. */
export function solve(level: Level): number[] | null {
  const removed = new Uint8Array(level.arrows.length);
  const occ = buildOccupancy(level);
  const order: number[] = [];
  let progress = true;
  while (progress && order.length < level.arrows.length) {
    progress = false;
    for (const a of level.arrows) {
      if (removed[a.id]) continue;
      if (!firstBlocker(level, occ, a)) {
        removed[a.id] = 1;
        for (const c of a.cells) occ[c] = -1;
        order.push(a.id);
        progress = true;
      }
    }
  }
  return order.length === level.arrows.length ? order : null;
}

/** Longest chain of "must leave before" dependencies (a rough difficulty measure). */
export function dependencyDepth(level: Level): number {
  const n = level.arrows.length;
  const removed = new Uint8Array(n);
  const occ = buildOccupancy(level);
  let depth = 0;
  let left = n;
  while (left > 0) {
    const wave = freeArrows(level, occ, removed);
    if (!wave.length) return -1;
    for (const id of wave) {
      removed[id] = 1;
      for (const c of level.arrows[id].cells) occ[c] = -1;
    }
    left -= wave.length;
    depth++;
  }
  return depth;
}

/**
 * Picks the most helpful free arrow for a hint: the one whose departure frees
 * the most other arrows (ties broken by the longest arrow, then lowest id).
 */
export function bestHint(level: Level, occ: Int16Array, removed: ArrayLike<number>): number {
  const free = freeArrows(level, occ, removed);
  if (!free.length) return -1;
  let best = free[0];
  let bestScore = -1;
  for (const id of free) {
    const a = level.arrows[id];
    let unblocks = 0;
    for (const b of level.arrows) {
      if (removed[b.id] || b.id === id) continue;
      const blk = firstBlocker(level, occ, b);
      if (blk && blk.id === id) unblocks++;
    }
    const score = unblocks * 100 + a.cells.length;
    if (score > bestScore) {
      bestScore = score;
      best = id;
    }
  }
  return best;
}

/** Structural checks used by tests and the generator. Returns a list of problems. */
export function validateLevel(level: Level): string[] {
  const errs: string[] = [];
  const { w, h, mask } = level;
  if (mask.length !== w * h) errs.push('mask size');
  const seen = new Int16Array(w * h).fill(-1);
  level.arrows.forEach((a, i) => {
    if (a.id !== i) errs.push(`arrow ${i}: id ${a.id}`);
    if (a.cells.length < 2) errs.push(`arrow ${i}: too short`);
    for (let k = 0; k < a.cells.length; k++) {
      const c = a.cells[k];
      if (c < 0 || c >= w * h) errs.push(`arrow ${i}: out of bounds`);
      else if (!mask[c]) errs.push(`arrow ${i}: outside shape`);
      else if (seen[c] >= 0) errs.push(`arrow ${i}: overlaps ${seen[c]}`);
      else seen[c] = i;
      if (k > 0 && dirBetween(w, a.cells[k - 1], c) < 0) errs.push(`arrow ${i}: broken path`);
    }
    if (a.cells.length >= 2) {
      const d = dirBetween(w, a.cells[a.cells.length - 2], headOf(a));
      if (d !== a.dir) errs.push(`arrow ${i}: head direction`);
    }
    const ray = rayCells(level, a);
    for (const c of ray) if (a.cells.includes(c)) errs.push(`arrow ${i}: points into itself`);
  });
  if (!solve(level)) errs.push('unsolvable');
  return errs;
}
