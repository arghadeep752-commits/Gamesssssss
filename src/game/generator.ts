import { cellIndex, DIR_VECTORS, DIRECTIONS, inBounds, stepDirection } from './geometry';
import type { Rng } from './rng';
import type { ArrowDef, Cell, Direction } from './types';

/**
 * Seeded layout generator, used offline by the level tools and for the daily
 * puzzle. Solvable by construction:
 *
 * Arrows are placed one by one, and each new arrow must have a completely empty
 * exit corridor at the moment it is placed. A new arrow may sit inside the
 * corridors of earlier arrows (that is what creates blocking), but nothing can
 * ever sit in its own corridor except arrows placed after it. So removing the
 * arrows in reverse placement order is always legal, and the blocks relation can
 * never contain a cycle. Every generated level is still run through
 * validateLevel before it is used.
 */
export interface GeneratorOptions {
  width: number;
  height: number;
  /** Stop once this many arrows are placed. */
  targetArrows: number;
  minLen: number;
  maxLen: number;
  /** Chance of turning at each body step (0 = straight arrows only). */
  turnChance: number;
  /** Relative weight for hook-shaped bends that double back against the exit direction. */
  hookChance?: number;
  /** Placement candidates compared per arrow; higher values create deeper blocking chains. */
  candidates: number;
  /** Consecutive failed attempts before giving up on reaching the target. */
  maxFailures?: number;
  /** Weight for chain depth when comparing candidates (0 = only count blocked arrows). */
  depthWeight?: number;
  /** After the main pass, try to fill leftover gaps with short arrows. */
  fillGaps?: boolean;
}

const OPPOSITE: Record<Direction, Direction> = { U: 'D', D: 'U', L: 'R', R: 'L' };
const PERPENDICULAR: Record<Direction, readonly Direction[]> = {
  U: ['L', 'R'],
  D: ['L', 'R'],
  L: ['U', 'D'],
  R: ['U', 'D'],
};

interface Candidate {
  cells: Cell[]; // tail first
  dir: Direction;
  score: number;
  height: number;
}

export function generateLayout(opts: GeneratorOptions, rng: Rng): ArrowDef[] {
  const { width, height } = opts;
  const occ = new Int16Array(width * height).fill(-1);
  // For each cell, which placed arrows have it in their corridor.
  const inCorridorOf: number[][] = Array.from({ length: width * height }, () => []);
  const placed: { cells: Cell[]; dir: Direction }[] = [];
  // chainHeight[i]: longest chain of arrows held up by arrow i, counting itself.
  const chainHeight: number[] = [];
  const maxFailures = opts.maxFailures ?? 160;
  const depthWeight = opts.depthWeight ?? 0;

  const empties = (): number[] => {
    const out: number[] = [];
    for (let i = 0; i < occ.length; i++) if (occ[i] === -1) out.push(i);
    return out;
  };

  const rayClear = (x: number, y: number, d: Direction, own: Set<number>): boolean => {
    const v = DIR_VECTORS[d];
    let cx = x + v.x;
    let cy = y + v.y;
    while (inBounds(cx, cy, width, height)) {
      const idx = cellIndex(cx, cy, width);
      if (occ[idx] !== -1 && !own.has(idx)) return false;
      cx += v.x;
      cy += v.y;
    }
    return true;
  };

  const usable = (x: number, y: number, d: Direction, own: Set<number>): boolean => {
    if (!inBounds(x, y, width, height)) return false;
    const idx = cellIndex(x, y, width);
    if (occ[idx] !== -1 || own.has(idx)) return false;
    return rayClear(x, y, d, own);
  };

  const build = (minLen: number, maxLen: number): Candidate | null => {
    const free = empties();
    if (free.length < minLen) return null;
    const d = rng.pick(DIRECTIONS);
    // Find a head cell whose forward ray is clear.
    let head = -1;
    for (let tries = 0; tries < 10; tries++) {
      const idx = rng.pick(free);
      const x = idx % width;
      const y = Math.floor(idx / width);
      if (rayClear(x, y, d, new Set([idx]))) {
        head = idx;
        break;
      }
    }
    if (head === -1) return null;
    const own = new Set<number>([head]);
    const reversed: Cell[] = [{ x: head % width, y: Math.floor(head / width) }];
    // Walk backwards from the head. The first backward step is forced so the
    // head continues its final segment.
    let walk: Direction = OPPOSITE[d];
    const target = rng.int(minLen, maxLen);
    while (reversed.length < target) {
      const cur = reversed[reversed.length - 1];
      const options: { dir: Direction; weight: number }[] = [];
      const first = reversed.length === 1;
      const straightW = first ? 1 : 1 - opts.turnChance;
      options.push({ dir: walk, weight: straightW });
      if (!first && opts.turnChance > 0) {
        for (const p of PERPENDICULAR[walk]) {
          // Walking backwards in the exit direction makes a hook; keep it rarer.
          const w = p === d ? (opts.hookChance ?? 0) : opts.turnChance / 2;
          if (w > 0) options.push({ dir: p, weight: w });
        }
      }
      const valid = options.filter((o) => {
        const v = DIR_VECTORS[o.dir];
        return usable(cur.x + v.x, cur.y + v.y, d, own);
      });
      if (!valid.length) break;
      let total = 0;
      for (const o of valid) total += o.weight;
      let r = rng.next() * total;
      let chosen = valid[valid.length - 1].dir;
      for (const o of valid) {
        r -= o.weight;
        if (r <= 0) {
          chosen = o.dir;
          break;
        }
      }
      const v = DIR_VECTORS[chosen];
      const nx = cur.x + v.x;
      const ny = cur.y + v.y;
      own.add(cellIndex(nx, ny, width));
      reversed.push({ x: nx, y: ny });
      walk = chosen;
    }
    if (reversed.length < minLen) return null;
    const cells = reversed.reverse();
    // Score: how many existing arrows this one would block, and how long the
    // resulting chain of dependencies becomes.
    const blocked = new Set<number>();
    for (const c of cells) for (const a of inCorridorOf[cellIndex(c.x, c.y, width)]) blocked.add(a);
    let h = 1;
    for (const a of blocked) if (chainHeight[a] + 1 > h) h = chainHeight[a] + 1;
    return { cells, dir: d, height: h, score: blocked.size + depthWeight * h + rng.next() * 0.5 };
  };

  const place = (cand: Candidate) => {
    const id = placed.length;
    placed.push({ cells: cand.cells, dir: cand.dir });
    chainHeight.push(cand.height);
    const own = new Set<number>();
    for (const c of cand.cells) {
      const idx = cellIndex(c.x, c.y, width);
      occ[idx] = id;
      own.add(idx);
    }
    const v = DIR_VECTORS[cand.dir];
    const seen = new Set<number>();
    for (const c of cand.cells) {
      let x = c.x + v.x;
      let y = c.y + v.y;
      while (inBounds(x, y, width, height)) {
        const idx = cellIndex(x, y, width);
        if (!own.has(idx) && !seen.has(idx)) {
          seen.add(idx);
          inCorridorOf[idx].push(id);
        }
        x += v.x;
        y += v.y;
      }
    }
  };

  const run = (minLen: number, maxLen: number, candidates: number, limit: number) => {
    let failures = 0;
    while (placed.length < opts.targetArrows && failures < limit) {
      let best: Candidate | null = null;
      for (let k = 0; k < Math.max(1, candidates); k++) {
        const cand = build(minLen, maxLen);
        if (cand && (!best || cand.score > best.score)) best = cand;
      }
      if (!best) {
        failures++;
        continue;
      }
      failures = 0;
      place(best);
    }
  };
  run(opts.minLen, opts.maxLen, opts.candidates, maxFailures);
  if (opts.fillGaps) run(2, Math.min(3, opts.maxLen), 1, maxFailures);

  // Present arrows in reading order of their tails so ids reveal nothing about
  // the solution order.
  const sorted = placed
    .slice()
    .sort((a, b) => a.cells[0].y - b.cells[0].y || a.cells[0].x - b.cells[0].x);
  return sorted.map((a, i) => {
    const last = stepDirection(a.cells[a.cells.length - 2], a.cells[a.cells.length - 1]);
    if (last !== a.dir) throw new Error('generator produced an inconsistent arrow head');
    return { id: i, cells: a.cells, dir: a.dir };
  });
}
