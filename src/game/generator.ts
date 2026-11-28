import {
  type Arrow,
  type Dir,
  type Level,
  buildOccupancy,
  dependencyDepth,
  dirBetween,
  freeArrows,
  opposite,
  rayCells,
  solve,
  step,
} from './engine';
import { mulberry32, randInt, shuffleInPlace, type Rng } from './rng';
import { shapeMask, type ShapeDef } from './shapes';

/**
 * Seeded level generator, solvable by construction.
 *
 * Arrows are placed one at a time in reverse solving order: a new arrow is only
 * accepted when the line in front of its head is empty right now, so in the
 * finished puzzle the arrows can always leave newest-first. Bodies grow
 * backwards from the head with a random walk, which gives the twisty snake
 * shapes. Placements that land on another arrow's exit line are preferred, and
 * afterwards free arrows are turned around whenever that makes them wait for
 * someone without creating a deadlock. Both make boards that have to be read
 * carefully instead of tapped at random.
 */
export interface GenParams {
  readonly w: number;
  readonly h: number;
  readonly shape: ShapeDef | 'rect';
  readonly minLen: number;
  readonly maxLen: number;
  /** Chance (0..1) that a body turns at each step once it has run straight a little. */
  readonly bend: number;
  /** Target fraction of playable cells to cover. */
  readonly fill: number;
  /** Maximum straight runs per arrow. */
  readonly maxRuns: number;
}

export interface LevelStats {
  readonly arrows: number;
  readonly coverage: number;
  /** Share of arrows that can leave at the start (lower is harder). */
  readonly freeShare: number;
  /** Rounds of "remove everything free" needed to clear the board (higher is harder). */
  readonly depth: number;
  readonly score: number;
}

export function levelStats(lvl: Level): LevelStats {
  const playable = lvl.mask.reduce((n, v) => n + v, 0);
  const covered = lvl.arrows.reduce((n, a) => n + a.cells.length, 0);
  const n = lvl.arrows.length;
  const free = n ? freeArrows(lvl, buildOccupancy(lvl), new Uint8Array(n)).length / n : 1;
  const depth = dependencyDepth(lvl);
  const coverage = covered / Math.max(1, playable);
  const score = depth * 3 + (1 - free) * 24 + coverage * 30 + Math.min(n, 200) * 0.03;
  return { arrows: n, coverage, freeShare: free, depth, score };
}

/** Builds `tries` candidates and keeps the hardest valid one. */
export function generateLevel(p: GenParams, seed: number, tries = 2): Level {
  let best: Level | null = null;
  let bestScore = -1;
  for (let attempt = 0; attempt < tries; attempt++) {
    const lvl = tryGenerate(p, (seed + attempt * 0x9e3779b1) >>> 0);
    if (lvl.arrows.length < 2 || !solve(lvl)) continue;
    const s = levelStats(lvl).score;
    if (s > bestScore) {
      best = lvl;
      bestScore = s;
    }
  }
  return best ?? tryGenerate({ ...p, shape: 'rect' }, seed ^ 0x5bd1e995);
}

export function tryGenerate(p: GenParams, seed: number): Level {
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
        const c = y * w + x;
        clear[n + c] = x === w - 1 ? 1 : occ[c + 1] < 0 && clear[n + c + 1] ? 1 : 0;
      }
      for (let x = 0; x < w; x++) {
        const c = y * w + x;
        clear[3 * n + c] = x === 0 ? 1 : occ[c - 1] < 0 && clear[3 * n + c - 1] ? 1 : 0;
      }
    }
    for (let x = 0; x < w; x++) {
      for (let y = 0; y < h; y++) {
        const c = y * w + x;
        clear[c] = y === 0 ? 1 : occ[c - w] < 0 && clear[c - w] ? 1 : 0;
      }
      for (let y = h - 1; y >= 0; y--) {
        const c = y * w + x;
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

    let placed: number[] | null = null;
    let placedDir: Dir = 0;
    let placedScore = -1;
    const tries = Math.min(cands.length, 30);
    for (const need of [p.minLen, 2]) {
      let found = 0;
      for (let k = 0; k < tries && found < 7; k++) {
        const head = (cands[k] / 4) | 0;
        const d = (cands[k] % 4) as Dir;
        const len = randInt(rng, p.minLen, Math.max(p.minLen, p.maxLen));
        stamp++;
        const path = grow(rng, p, w, h, head, d, len, free, mark, stamp);
        if (path.length < need) continue;
        found++;
        let blocks = 0;
        for (const c of path) blocks += rays[c];
        const score = (blocks > 0 ? 20 : 0) + Math.min(blocks, 4) * 3 + path.length * 1.2 + rng() * 3;
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
      if (rays[rc] < 255) rays[rc]++;
      rc = step(w, h, rc, placedDir);
    }
  }

  return tighten(rng, { w, h, mask, arrows }, p);
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
    const pTurn = sinceTurn < 2 ? p.bend * 0.25 : p.bend;
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

/**
 * Turns free arrows around (head and tail swap ends) when that makes them wait
 * for another arrow and creates no deadlock. Uses the "waits for" graph: an
 * arrow waits for every arrow sitting on its exit line, and a board is solvable
 * exactly when that graph has no cycle. Turning X around only changes X's own
 * edges, so a cycle appears only if one of the arrows X would wait for already
 * (directly or not) waits for X.
 */
type MutableArrow = { id: number; cells: number[]; dir: Dir };

function tighten(rng: Rng, level: Level, p: GenParams): Level {
  const { w, h, mask } = level;
  const arrows: MutableArrow[] = level.arrows.map((a) => ({ id: a.id, cells: a.cells.slice(), dir: a.dir }));
  const lvl: Level = { ...level, arrows };
  const occ = buildOccupancy(lvl);
  const waits: number[][] = arrows.map((a) => waitsFor(lvl, occ, a));
  // Arrow ids never exceed the cell count (every arrow has at least two cells).
  const seen = new Int32Array(w * h + 1);
  let stamp = 0;

  /** Is `target` reachable from any of `from` along "waits for" edges? */
  const reaches = (from: readonly number[], target: number): boolean => {
    stamp++;
    const stack = from.slice();
    while (stack.length) {
      const v = stack.pop() as number;
      if (v === target) return true;
      if (seen[v] === stamp) continue;
      seen[v] = stamp;
      for (const u of waits[v]) if (seen[u] !== stamp) stack.push(u);
    }
    return false;
  };

  // 1) Turn free arrows around when they would then wait for someone.
  for (const id of shuffleInPlace(rng, arrows.map((a) => a.id))) {
    if (waits[id].length) continue;
    const a = arrows[id];
    const cells = a.cells.slice().reverse();
    const dir = dirBetween(w, cells[cells.length - 2], cells[cells.length - 1]);
    if (dir === -1) continue;
    const flipped: MutableArrow = { id, cells, dir };
    const ray = rayCells(lvl, flipped);
    if (ray.some((c) => cells.includes(c))) continue;
    const next = waitsFor(lvl, occ, flipped);
    if (!next.length || reaches(next, id)) continue;
    arrows[id] = flipped;
    waits[id] = next;
  }

  // Arrows whose head looks straight at cell c (c lies on their exit line).
  const watchersOf = (c: number, out: number[]) => {
    for (let d = 0 as Dir; d < 4; d = (d + 1) as Dir) {
      let e = step(w, h, c, d);
      while (e >= 0) {
        const o = occ[e];
        if (o >= 0) {
          const b = arrows[o];
          if (b.cells[b.cells.length - 1] === e && b.dir === opposite(d) && !out.includes(o)) out.push(o);
        }
        e = step(w, h, e, d);
      }
    }
    return out;
  };
  /** Would edges "watchers -> X" plus "X -> waitsX" close a cycle? */
  const closesCycle = (waitsX: readonly number[], watchers: readonly number[]) => {
    if (!waitsX.length || !watchers.length) return false;
    stamp++;
    const stack = waitsX.slice();
    while (stack.length) {
      const v = stack.pop() as number;
      if (watchers.includes(v)) return true;
      if (seen[v] === stamp) continue;
      seen[v] = stamp;
      for (const u of waits[v]) if (seen[u] !== stamp) stack.push(u);
    }
    return false;
  };
  const runsOf = (cells: readonly number[]) => {
    let r = 1;
    for (let i = 2; i < cells.length; i++) if (cells[i] - cells[i - 1] !== cells[i - 1] - cells[i - 2]) r++;
    return r;
  };
  const lenCap = p.maxLen + 3;

  // 2) Grow tails into leftover empty cells. Arrows whose exit line crosses the
  //    new cell start waiting for the grown arrow; skipped if that closes a cycle.
  const growTails = (passes: number) => {
    let changed = true;
    for (let pass = 0; changed && pass < passes; pass++) {
      changed = false;
      for (let c = 0; c < w * h; c++) {
        if (!mask[c] || occ[c] >= 0) continue;
        const watchers = watchersOf(c, []);
        for (let d = 0 as Dir; d < 4; d = (d + 1) as Dir) {
          const t = step(w, h, c, d);
          if (t < 0 || occ[t] < 0) continue;
          const a = arrows[occ[t]];
          if (a.cells[0] !== t || a.cells.length >= lenCap) continue;
          if (watchers.includes(a.id)) continue; // would sit on its own exit line
          if (runsOf([c, ...a.cells]) > p.maxRuns + 1) continue;
          if (closesCycle([a.id], watchers)) continue;
          a.cells.unshift(c);
          occ[c] = a.id;
          for (const b of watchers) if (!waits[b].includes(a.id)) waits[b].push(a.id);
          changed = true;
          break;
        }
      }
    }
  };
  growTails(4);

  // 3) Pack new arrows into the remaining gaps. Unlike the first phase their
  //    exit line does not have to be empty: they simply wait for whatever is in
  //    front of them, as long as no cycle appears. This is what makes boards as
  //    tightly packed as a real tangle.
  const tmp = new Int32Array(w * h);
  let tstamp = 0;
  const empties: number[] = [];
  for (let c = 0; c < w * h; c++) if (mask[c] && occ[c] < 0) empties.push(c);
  shuffleInPlace(rng, empties);
  for (const head of empties) {
    if (occ[head] >= 0) continue;
    const dirs = shuffleInPlace(rng, [0, 1, 2, 3] as Dir[]);
    for (const d of dirs) {
      const behind = step(w, h, head, opposite(d));
      if (behind < 0 || !mask[behind] || occ[behind] >= 0) continue;
      tstamp++;
      let e = step(w, h, head, d);
      while (e >= 0) {
        tmp[e] = tstamp; // own exit line is off limits for the body
        e = step(w, h, e, d);
      }
      const cells = [head, behind];
      tmp[head] = tstamp;
      tmp[behind] = tstamp;
      let back = opposite(d);
      let cur = behind;
      let runs = 1;
      let since = 1;
      const want = randInt(rng, p.minLen, Math.max(p.minLen, p.maxLen));
      while (cells.length < want) {
        const opts: Dir[] = [];
        for (const nd of [back, ((back + 1) % 4) as Dir, ((back + 3) % 4) as Dir]) {
          const nx = step(w, h, cur, nd);
          if (nx >= 0 && mask[nx] && occ[nx] < 0 && tmp[nx] !== tstamp && (nd === back || runs < p.maxRuns)) opts.push(nd);
        }
        if (!opts.length) break;
        let nd = opts[0];
        const turnOk = opts.filter((o) => o !== back);
        if (opts[0] !== back || (turnOk.length && rng() < (since < 2 ? p.bend * 0.25 : p.bend))) {
          nd = turnOk.length ? turnOk[Math.floor(rng() * turnOk.length)] : opts[0];
        }
        if (nd !== back) {
          runs++;
          since = 0;
        }
        back = nd;
        cur = step(w, h, cur, nd);
        cells.push(cur);
        tmp[cur] = tstamp;
        since++;
      }
      cells.reverse(); // tail first
      const id = arrows.length;
      const cand: MutableArrow = { id, cells, dir: d };
      const waitsX: number[] = [];
      e = step(w, h, head, d);
      while (e >= 0) {
        const o = occ[e];
        if (o >= 0 && !waitsX.includes(o)) waitsX.push(o);
        e = step(w, h, e, d);
      }
      const watchers: number[] = [];
      for (const c of cells) watchersOf(c, watchers);
      if (closesCycle(waitsX, watchers)) continue;
      arrows.push(cand);
      waits.push(waitsX);
      for (const c of cells) occ[c] = id;
      for (const b of watchers) if (!waits[b].includes(id)) waits[b].push(id);
      break;
    }
  }
  growTails(6);

  // 4) Holes straight in front of a head: push the head forward into them.
  for (let pass = 0; pass < 4; pass++) {
    let changed = false;
    for (let c = 0; c < w * h; c++) {
      if (!mask[c] || occ[c] >= 0) continue;
      for (let d = 0 as Dir; d < 4; d = (d + 1) as Dir) {
        const t = step(w, h, c, opposite(d)); // cell behind c, looking in direction d
        if (t < 0 || occ[t] < 0) continue;
        const a = arrows[occ[t]];
        if (a.cells[a.cells.length - 1] !== t || a.dir !== d || a.cells.length >= lenCap) continue;
        const watchers = watchersOf(c, []).filter((b) => b !== a.id);
        if (closesCycle([a.id], watchers)) continue;
        a.cells.push(c);
        occ[c] = a.id;
        for (const b of watchers) if (!waits[b].includes(a.id)) waits[b].push(a.id);
        changed = true;
        break;
      }
    }
    if (!changed) break;
  }
  growTails(2);
  return lvl;
}

function waitsFor(level: Level, occ: Int16Array, a: Arrow): number[] {
  const out: number[] = [];
  for (const c of rayCells(level, a)) {
    const o = occ[c];
    if (o >= 0 && o !== a.id && !out.includes(o)) out.push(o);
  }
  return out;
}
