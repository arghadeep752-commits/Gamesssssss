import {
  type Arrow,
  type Dir,
  type Level,
  buildOccupancy,
  dirBetween,
  firstBlocker,
  opposite,
  rayCells,
  solve,
  step,
} from './engine';
import { mulberry32, randInt, shuffleInPlace, type Rng } from './rng';
import { shapeMask, type Shape } from './shapes';

/**
 * Seeded level generator, solvable by construction.
 *
 * Arrows are placed one at a time in reverse solving order: a new arrow is only
 * accepted when the line in front of its head is empty right now. Every arrow
 * placed later sits behind it in the solving order, so in the finished puzzle
 * the arrows can always leave newest-first. Bodies grow backwards from the head
 * with a random walk, which gives the twisty snake shapes.
 */
export interface GenParams {
  readonly w: number;
  readonly h: number;
  readonly shape: Shape;
  readonly minLen: number;
  readonly maxLen: number;
  /** Chance (0..1) that a body turns at each step once it has run straight a little. */
  readonly bend: number;
  /** Target fraction of playable cells to cover. */
  readonly fill: number;
  /** Maximum straight runs per arrow (limits very knotted shapes). */
  readonly maxRuns: number;
}

export function generateLevel(p: GenParams, seed: number): Level {
  let best: Level | null = null;
  let bestScore = -1;
  for (let attempt = 0; attempt < 6; attempt++) {
    const lvl = tryGenerate(p, (seed + attempt * 0x9e3779b1) >>> 0);
    if (!solve(lvl)) continue;
    const covered = lvl.arrows.reduce((n, a) => n + a.cells.length, 0);
    const playable = lvl.mask.reduce((n, v) => n + v, 0);
    const score = covered / Math.max(1, playable) + Math.min(lvl.arrows.length, 4) * 0.05;
    if (score > bestScore) {
      best = lvl;
      bestScore = score;
    }
    if (covered >= Math.min(p.fill, 0.9) * playable * 0.95 && lvl.arrows.length >= 2) return lvl;
  }
  return best ?? tryGenerate({ ...p, shape: 'rect' }, seed ^ 0x5bd1e995);
}

function tryGenerate(p: GenParams, seed: number): Level {
  const rng = mulberry32(seed);
  const { w, h } = p;
  const n = w * h;
  const mask = shapeMask(p.shape, w, h);
  const occ = new Int16Array(n).fill(-1);
  const arrows: Arrow[] = [];
  let playable = 0;
  for (let i = 0; i < n; i++) playable += mask[i];
  const target = Math.floor(playable * p.fill);
  let covered = 0;
  const mark = new Int32Array(n); // scratch marks, generation-stamped
  let stamp = 1;
  const rays = new Uint8Array(n); // how many placed arrows exit through each cell

  const free = (c: number) => c >= 0 && mask[c] === 1 && occ[c] < 0;

  // clear[d * n + c] = 1 when every cell in front of c (direction d) is empty.
  const clear = new Uint8Array(4 * n);
  const fillClear = () => {
    for (let y = 0; y < h; y++) {
      for (let x = w - 1; x >= 0; x--) {
        const c = y * w + x; // right
        clear[n + c] = x === w - 1 ? 1 : occ[c + 1] < 0 && clear[n + c + 1] ? 1 : 0;
      }
      for (let x = 0; x < w; x++) {
        const c = y * w + x; // left
        clear[3 * n + c] = x === 0 ? 1 : occ[c - 1] < 0 && clear[3 * n + c - 1] ? 1 : 0;
      }
    }
    for (let x = 0; x < w; x++) {
      for (let y = 0; y < h; y++) {
        const c = y * w + x; // up
        clear[c] = y === 0 ? 1 : occ[c - w] < 0 && clear[c - w] ? 1 : 0;
      }
      for (let y = h - 1; y >= 0; y--) {
        const c = y * w + x; // down
        clear[2 * n + c] = y === h - 1 ? 1 : occ[c + w] < 0 && clear[2 * n + c + w] ? 1 : 0;
      }
    }
  };

  while (covered < target) {
    fillClear();
    const cands: number[] = [];
    for (let c = 0; c < n; c++) {
      if (!free(c)) continue;
      for (let d = 0 as Dir; d < 4; d = (d + 1) as Dir) {
        if (!clear[d * n + c]) continue;
        if (free(step(w, h, c, opposite(d)))) cands.push(c * 4 + d);
      }
    }
    if (!cands.length) break;
    shuffleInPlace(rng, cands);

    // Grow several candidate arrows and keep the best one. Arrows that land on the exit
    // line of an already placed arrow create "must clear me first" dependencies, which
    // is what makes a board feel like a real puzzle instead of a pile of free moves.
    let placed: number[] | null = null;
    let placedDir: Dir = 0;
    let placedScore = -1;
    const tries = Math.min(cands.length, 36);
    for (const need of [p.minLen, 2]) {
      let found = 0;
      for (let k = 0; k < tries && found < 8; k++) {
        const head = (cands[k] / 4) | 0;
        const d = (cands[k] % 4) as Dir;
        const len = randInt(rng, p.minLen, Math.max(p.minLen, p.maxLen));
        stamp++;
        const path = grow(rng, p, w, h, head, d, len, free, mark, stamp);
        if (path.length < need) continue;
        found++;
        let blocks = 0;
        for (const c of path) blocks += rays[c];
        const score = (blocks > 0 ? 20 : 0) + Math.min(blocks, 4) * 3 + path.length + rng() * 3;
        if (score > placedScore) {
          placedScore = score;
          placed = path;
          placedDir = d;
        }
      }
      if (placed) break;
    }
    if (!placed) break;
    const id = arrows.length;
    for (const c of placed) occ[c] = id;
    covered += placed.length;
    arrows.push({ id, cells: placed, dir: placedDir });
    let rc = step(w, h, placed[placed.length - 1], placedDir);
    while (rc >= 0) {
      rays[rc]++;
      rc = step(w, h, rc, placedDir);
    }
  }

  return tighten(rng, { w, h, mask, arrows });
}

/**
 * Turns some free arrows around (head and tail swap ends) when that makes them
 * wait for another arrow and the board stays solvable. Fewer arrows are free at
 * the start, so the player has to read the board instead of tapping anything.
 */
function tighten(rng: Rng, level: Level): Level {
  const arrows = level.arrows.slice();
  const lvl = { ...level, arrows };
  const order = shuffleInPlace(rng, arrows.map((a) => a.id));
  for (const id of order) {
    const a = arrows[id];
    const occ = buildOccupancy(lvl);
    if (firstBlocker(lvl, occ, a)) continue; // already waits for someone
    const cells = a.cells.slice().reverse();
    const dir = dirBetween(level.w, cells[cells.length - 2], cells[cells.length - 1]);
    if (dir === -1) continue;
    const flipped: Arrow = { id, cells, dir };
    const ray = rayCells(lvl, flipped);
    if (ray.some((c) => cells.includes(c))) continue;
    if (!firstBlocker(lvl, occ, flipped)) continue;
    arrows[id] = flipped;
    if (!solve(lvl)) arrows[id] = a;
  }
  return lvl;
}

/** Grows a body backwards from the head. Returns cells tail-first. */
function grow(
  rng: Rng,
  p: GenParams,
  w: number,
  h: number,
  head: number,
  d: Dir,
  len: number,
  free: (c: number) => boolean,
  mark: Int32Array,
  stamp: number,
): number[] {
  // Cells in front of the head are reserved: the body may never enter its own exit line.
  let c = step(w, h, head, d);
  while (c >= 0) {
    mark[c] = stamp;
    c = step(w, h, c, d);
  }
  const path = [head];
  mark[head] = stamp;
  let back = opposite(d); // direction of travel while walking from head to tail
  let cur = step(w, h, head, back);
  path.push(cur);
  mark[cur] = stamp;
  let runs = 1;
  let sinceTurn = 1;
  const ok = (cell: number) => free(cell) && mark[cell] !== stamp;

  while (path.length < len) {
    const straight = step(w, h, cur, back);
    const turnA = ((back + 1) % 4) as Dir;
    const turnB = ((back + 3) % 4) as Dir;
    const turns: Dir[] = [];
    if (runs < p.maxRuns) {
      if (ok(step(w, h, cur, turnA))) turns.push(turnA);
      if (ok(step(w, h, cur, turnB))) turns.push(turnB);
    }
    const canStraight = ok(straight);
    if (!canStraight && !turns.length) break;
    const pTurn = sinceTurn < 2 ? p.bend * 0.2 : p.bend;
    let nd: Dir = back;
    if (!canStraight || (turns.length && rng() < pTurn)) {
      nd = turns[Math.floor(rng() * turns.length)];
      runs++;
      sinceTurn = 0;
    }
    back = nd;
    cur = step(w, h, cur, nd);
    path.push(cur);
    mark[cur] = stamp;
    sinceTurn++;
  }
  return path.reverse();
}
