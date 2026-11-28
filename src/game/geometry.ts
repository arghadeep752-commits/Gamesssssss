import { type Arrow, DX, DY, type Level, headOf } from './engine';

/**
 * Pixel geometry shared by the renderer and the tests. Everything here is
 * computed once per level layout (never per frame).
 *
 * An arrow is drawn as a thick polyline through its cell centres with round caps
 * and joins (built from axis-aligned capsules) plus a triangular head. While it
 * moves, the visible body is the window [s, s + L] of a longer "trajectory"
 * polyline that continues straight out of the head.
 */

/** Stroke width relative to the cell size. */
export const STROKE = 0.2;
/** Head triangle, relative to the cell size: tip ahead of the head cell centre, base behind it. */
export const HEAD_TIP = 0.42;
export const HEAD_BASE = 0.1;
export const HEAD_HALF = 0.3;
/** Size of the square box the head is drawn in (relative to the cell size). */
export const HEAD_BOX = 0.9;
/** Most straight runs any trajectory can have (body runs + the exit run). */
export const MAX_RUNS = 16;

export interface Seg {
  /** Axis-aligned, from vertex (x0, y0) to (x1, y1), in board pixels. */
  readonly x0: number;
  readonly y0: number;
  readonly x1: number;
  readonly y1: number;
}

export interface ArrowGeom {
  readonly id: number;
  /** Corner vertices tail..head (cell centres where the path turns, plus both ends). */
  readonly vx: readonly number[];
  readonly vy: readonly number[];
  readonly segs: readonly Seg[];
  /** Head cell centre. */
  readonly hx: number;
  readonly hy: number;
  readonly dx: number;
  readonly dy: number;
  /** Rotation of the head (degrees; 0 = pointing right). */
  readonly rot: number;
  /** Body length, centre of tail to centre of head. */
  readonly len: number;
}

const ROT = [270, 0, 90, 180];

export function cellCenter(level: Level, cell: number, size: number): [number, number] {
  return [((cell % level.w) + 0.5) * size, (Math.floor(cell / level.w) + 0.5) * size];
}

export function arrowGeom(level: Level, a: Arrow, size: number): ArrowGeom {
  const vx: number[] = [];
  const vy: number[] = [];
  const cells = a.cells;
  for (let i = 0; i < cells.length; i++) {
    const keep =
      i === 0 ||
      i === cells.length - 1 ||
      cells[i] - cells[i - 1] !== cells[i + 1] - cells[i]; // direction changes here
    if (keep) {
      const [x, y] = cellCenter(level, cells[i], size);
      vx.push(x);
      vy.push(y);
    }
  }
  const segs: Seg[] = [];
  for (let i = 0; i + 1 < vx.length; i++) segs.push({ x0: vx[i], y0: vy[i], x1: vx[i + 1], y1: vy[i + 1] });
  const [hx, hy] = cellCenter(level, headOf(a), size);
  return {
    id: a.id,
    vx,
    vy,
    segs,
    hx,
    hy,
    dx: DX[a.dir],
    dy: DY[a.dir],
    rot: ROT[a.dir],
    len: (cells.length - 1) * size,
  };
}

/** Rectangle (left, top, width, height) of a capsule drawn over a segment. */
export function capsuleRect(s: Seg, stroke: number): [number, number, number, number] {
  const r = stroke / 2;
  const left = Math.min(s.x0, s.x1) - r;
  const top = Math.min(s.y0, s.y1) - r;
  return [left, top, Math.abs(s.x1 - s.x0) + stroke, Math.abs(s.y1 - s.y0) + stroke];
}

/** Path data for the head triangle inside its box (pointing right, box centre = head cell centre). */
export function headPath(size: number): string {
  const box = HEAD_BOX * size;
  const c = box / 2;
  const tip = c + HEAD_TIP * size;
  const base = c - HEAD_BASE * size;
  const half = HEAD_HALF * size;
  const f = (n: number) => n.toFixed(2);
  return `M${f(tip)} ${f(c)}L${f(base)} ${f(c - half)}L${f(base)} ${f(c + half)}Z`;
}

/** Plain data handed to the UI thread for one flight (kept small and flat). */
export interface Flight {
  /** Number of trajectory vertices. */
  n: number;
  px: number[];
  py: number[];
  /** Arc length at each vertex. */
  cum: number[];
  /** Body length. */
  len: number;
  /** Head start position and direction (area pixels). */
  hx: number;
  hy: number;
  dx: number;
  dy: number;
  rot: number;
  /** How far the tail travels in total. */
  travel: number;
}

/**
 * Builds the trajectory for an exit (the arrow leaves the visible area) or a
 * bump (it slides up to the blocking arrow and comes back).
 *
 * (ox, oy) is the board's offset inside the play area of size areaW x areaH.
 */
export function makeFlight(
  g: ArrowGeom,
  size: number,
  ox: number,
  oy: number,
  areaW: number,
  areaH: number,
  kind: 'exit' | 'bump',
  gap: number,
): Flight {
  const px = g.vx.map((x) => x + ox);
  const py = g.vy.map((y) => y + oy);
  const hx = g.hx + ox;
  const hy = g.hy + oy;
  let travel: number;
  if (kind === 'exit') {
    const edge = g.dx > 0 ? areaW - hx : g.dx < 0 ? hx : g.dy > 0 ? areaH - hy : hy;
    travel = g.len + Math.max(0, edge) + STROKE * size + HEAD_TIP * size;
  } else {
    // Slide until the head tip meets the blocking arrow's stroke, then come back.
    travel = (gap + 0.42) * size;
  }
  // The exit run continues straight out of the head far enough for the whole window.
  const reach = travel + size;
  px.push(hx + g.dx * reach);
  py.push(hy + g.dy * reach);
  const cum = [0];
  for (let i = 1; i < px.length; i++) cum.push(cum[i - 1] + Math.abs(px[i] - px[i - 1]) + Math.abs(py[i] - py[i - 1]));
  return { n: px.length, px, py, cum, len: g.len, hx, hy, dx: g.dx, dy: g.dy, rot: g.rot, travel };
}

/** Placement of one piece of a moving arrow for the current travel `s`. */
export interface PieceFrame {
  on: boolean;
  tx: number;
  ty: number;
  sx: number;
  sy: number;
}

/**
 * Where piece j of a moving arrow goes when its tail has travelled `s` along the
 * trajectory. Piece j is either the straight part of run j (a stroke-sized square
 * scaled into a bar) or, with `dot`, the round cap where that run's visible part
 * starts. Runs on the UI thread every frame, so it only does a little arithmetic.
 */
export function pieceFrame(f: Flight, s: number, j: number, stroke: number, dot: boolean): PieceFrame {
  'worklet';
  const half = stroke / 2;
  if (j >= f.n - 1) return { on: false, tx: 0, ty: 0, sx: 1, sy: 1 };
  const a = f.cum[j];
  const b = f.cum[j + 1];
  const u = Math.max(a, s);
  const v = Math.min(b, s + f.len);
  if (v - u < 0.01 || b - a < 0.01) return { on: false, tx: 0, ty: 0, sx: 1, sy: 1 };
  const ax = f.px[j];
  const ay = f.py[j];
  const ex = f.px[j + 1];
  const ey = f.py[j + 1];
  const t0 = (u - a) / (b - a);
  const x0 = ax + (ex - ax) * t0;
  const y0 = ay + (ey - ay) * t0;
  if (dot) return { on: true, tx: x0 - half, ty: y0 - half, sx: 1, sy: 1 };
  const t1 = (v - a) / (b - a);
  const x1 = ax + (ex - ax) * t1;
  const y1 = ay + (ey - ay) * t1;
  const horizontal = Math.abs(ey - ay) < 0.5;
  const rw = horizontal ? Math.abs(x1 - x0) : stroke;
  const rh = horizontal ? stroke : Math.abs(y1 - y0);
  const cx = horizontal ? (x0 + x1) / 2 : ax;
  const cy = horizontal ? ay : (y0 + y1) / 2;
  return { on: true, tx: cx - half, ty: cy - half, sx: rw / stroke, sy: rh / stroke };
}

/** Time for a flight: quick for short hops, never sluggish for long exits. */
export function flightMs(f: Flight, size: number, kind: 'exit' | 'bump'): number {
  if (kind === 'bump') return Math.max(110, Math.min(280, 90 + (f.travel / size) * 28));
  return Math.round(Math.max(260, Math.min(720, 170 + f.travel * 0.9)));
}

/** Finds the arrow under a touch point (board pixels), with a little tolerance around thin arrows. */
export function hitTest(level: Level, occ: Int16Array, bx: number, by: number, size: number): number {
  const x = Math.floor(bx / size);
  const y = Math.floor(by / size);
  if (x >= 0 && y >= 0 && x < level.w && y < level.h) {
    const id = occ[y * level.w + x];
    if (id >= 0) return id;
  }
  let best = -1;
  let bestD = 0.8 * size * (0.8 * size);
  for (let yy = y - 1; yy <= y + 1; yy++) {
    for (let xx = x - 1; xx <= x + 1; xx++) {
      if (xx < 0 || yy < 0 || xx >= level.w || yy >= level.h) continue;
      const id = occ[yy * level.w + xx];
      if (id < 0) continue;
      const cx = (xx + 0.5) * size;
      const cy = (yy + 0.5) * size;
      const d = (cx - bx) * (cx - bx) + (cy - by) * (cy - by);
      if (d < bestD) {
        bestD = d;
        best = id;
      }
    }
  }
  return best;
}
