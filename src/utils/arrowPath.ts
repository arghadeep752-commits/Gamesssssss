import { arrowBounds, DIR_VECTORS, exitDistanceCells } from '../game/geometry';
import type { ArrowDef } from '../game/types';

/**
 * Converts engine geometry (cells) into drawing geometry (pixels). Pure and
 * cheap; components memoise the result per arrow and cell size, so it runs
 * once per arrow per layout, never per frame.
 *
 * Drawing rules: the body is a polyline through cell centres. The arrowhead is
 * a filled triangle inside the head cell, pointing in the exit direction. All
 * drawing stays inside the arrow's own cells, which is exactly the area the
 * engine uses for blocking, so what the player sees matches the rules.
 */
export interface ArrowGeometry {
  /** Position and size of the arrow's bounding box on the board, in px. */
  readonly left: number;
  readonly top: number;
  readonly width: number;
  readonly height: number;
  /** SVG path for the body stroke, in local coordinates. */
  readonly body: string;
  /** SVG path for the filled arrowhead, in local coordinates. */
  readonly head: string;
  readonly strokeWidth: number;
  /** Unit exit vector. */
  readonly dx: number;
  readonly dy: number;
  /** Pixels the arrow must travel to be completely off the board. */
  readonly exitDistance: number;
}

export function strokeWidthFor(cell: number): number {
  return Math.max(2.5, Math.min(4.5, cell * 0.12));
}

const f = (n: number) => (Math.round(n * 100) / 100).toString();

export function arrowGeometry(arrow: ArrowDef, cell: number, gridWidth: number, gridHeight: number): ArrowGeometry {
  const b = arrowBounds(arrow);
  const v = DIR_VECTORS[arrow.dir];
  const local = (x: number, y: number) => ({ x: (x - b.minX + 0.5) * cell, y: (y - b.minY + 0.5) * cell });
  const pts = arrow.cells.map((c) => local(c.x, c.y));
  const head = pts[pts.length - 1];
  const sw = strokeWidthFor(cell);

  const tipLen = cell * 0.4;
  const baseOff = cell * 0.02;
  const half = cell * 0.22;
  const tip = { x: head.x + v.x * tipLen, y: head.y + v.y * tipLen };
  const base = { x: head.x + v.x * baseOff, y: head.y + v.y * baseOff };
  // Perpendicular for the triangle base.
  const px = -v.y;
  const py = v.x;
  const headPath =
    `M${f(tip.x)} ${f(tip.y)}` +
    `L${f(base.x + px * half)} ${f(base.y + py * half)}` +
    `L${f(base.x - px * half)} ${f(base.y - py * half)}Z`;

  // Body ends just inside the arrowhead so the joint is seamless.
  const end = { x: head.x + v.x * cell * 0.08, y: head.y + v.y * cell * 0.08 };
  let body = `M${f(pts[0].x)} ${f(pts[0].y)}`;
  for (let i = 1; i < pts.length - 1; i++) body += `L${f(pts[i].x)} ${f(pts[i].y)}`;
  body += `L${f(end.x)} ${f(end.y)}`;

  return {
    left: b.minX * cell,
    top: b.minY * cell,
    width: (b.maxX - b.minX + 1) * cell,
    height: (b.maxY - b.minY + 1) * cell,
    body,
    head: headPath,
    strokeWidth: sw,
    dx: v.x,
    dy: v.y,
    exitDistance: exitDistanceCells(arrow, gridWidth, gridHeight) * cell + 2,
  };
}

/** One SVG path drawing a small dot at the centre of every listed cell. */
export function dotsPath(cells: readonly { x: number; y: number }[], cell: number, radius: number): string {
  let d = '';
  const r = f(radius);
  const r2 = f(radius * 2);
  for (const c of cells) {
    const cx = (c.x + 0.5) * cell;
    const cy = (c.y + 0.5) * cell;
    d += `M${f(cx - radius)} ${f(cy)}a${r} ${r} 0 1 0 ${r2} 0a${r} ${r} 0 1 0 -${r2} 0`;
  }
  return d;
}

/** The dotted background grid as a single path. */
export function gridDotsPath(width: number, height: number, cell: number): string {
  const cells: { x: number; y: number }[] = [];
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) cells.push({ x, y });
  return dotsPath(cells, cell, Math.max(1.2, cell * 0.045));
}

/** Exit animation length: longer trips take a little longer, within 250-400 ms. */
export function exitDurationMs(distanceCells: number, base: number, perCell: number, max: number): number {
  return Math.min(max, Math.max(base, base + perCell * distanceCells));
}
