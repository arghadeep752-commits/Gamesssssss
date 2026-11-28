/**
 * Board outlines: objects, animals and symbols drawn with simple geometry in a
 * small design space, then rasterised to whatever grid size a level needs.
 * Cells outside the outline stay empty.
 */
type Pred = (x: number, y: number) => boolean;

const circle = (cx: number, cy: number, r: number): Pred => (x, y) => (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
const ellipse = (cx: number, cy: number, rx: number, ry: number): Pred => (x, y) =>
  ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2 <= 1;
const rect = (x0: number, y0: number, x1: number, y1: number): Pred => (x, y) => x >= x0 && x <= x1 && y >= y0 && y <= y1;
const rrect = (x0: number, y0: number, x1: number, y1: number, r: number): Pred => (x, y) => {
  if (x < x0 || x > x1 || y < y0 || y > y1) return false;
  const cx = Math.min(Math.max(x, x0 + r), x1 - r);
  const cy = Math.min(Math.max(y, y0 + r), y1 - r);
  return (x - cx) ** 2 + (y - cy) ** 2 <= r * r;
};
const capsule = (x0: number, y0: number, x1: number, y1: number, r: number): Pred => (x, y) => {
  const dx = x1 - x0;
  const dy = y1 - y0;
  const l2 = dx * dx + dy * dy || 1;
  const t = Math.max(0, Math.min(1, ((x - x0) * dx + (y - y0) * dy) / l2));
  const px = x0 + t * dx - x;
  const py = y0 + t * dy - y;
  return px * px + py * py <= r * r;
};
const poly = (...p: number[]): Pred => (x, y) => {
  let inside = false;
  for (let i = 0, j = p.length - 2; i < p.length; j = i, i += 2) {
    const xi = p[i];
    const yi = p[i + 1];
    const xj = p[j];
    const yj = p[j + 1];
    if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
};
const U = (...ps: Pred[]): Pred => (x, y) => ps.some((p) => p(x, y));
const D = (a: Pred, ...cut: Pred[]): Pred => (x, y) => a(x, y) && !cut.some((p) => p(x, y));
const I = (a: Pred, b: Pred): Pred => (x, y) => a(x, y) && b(x, y);
const ring = (cx: number, cy: number, r0: number, r1: number): Pred => D(circle(cx, cy, r1), circle(cx, cy, r0));

function starPoly(cx: number, cy: number, R: number, r: number, n: number): Pred {
  const pts: number[] = [];
  for (let k = 0; k < n * 2; k++) {
    const a = -Math.PI / 2 + (k * Math.PI) / n;
    const rad = k % 2 === 0 ? R : r;
    pts.push(cx + Math.cos(a) * rad, cy + Math.sin(a) * rad);
  }
  return poly(...pts);
}

function regular(cx: number, cy: number, R: number, n: number, rot = 0): Pred {
  const pts: number[] = [];
  for (let k = 0; k < n; k++) {
    const a = rot + (k * 2 * Math.PI) / n;
    pts.push(cx + Math.cos(a) * R, cy + Math.sin(a) * R);
  }
  return poly(...pts);
}

function sunRays(cx: number, cy: number, r0: number, r1: number, w: number): Pred[] {
  const out: Pred[] = [];
  for (let k = 0; k < 8; k++) {
    const a = (k * Math.PI) / 4;
    out.push(capsule(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0, cx + Math.cos(a) * r1, cy + Math.sin(a) * r1, w));
  }
  return out;
}

function petals(cx: number, cy: number, d: number, r: number, n: number): Pred[] {
  const out: Pred[] = [];
  for (let k = 0; k < n; k++) {
    const a = -Math.PI / 2 + (k * 2 * Math.PI) / n;
    out.push(circle(cx + Math.cos(a) * d, cy + Math.sin(a) * d, r));
  }
  return out;
}

export interface ShapeDef {
  readonly id: string;
  readonly name: string;
  /** Design-space size; the board keeps this aspect ratio. */
  readonly w: number;
  readonly h: number;
  readonly draw: Pred;
}

const S = (id: string, name: string, w: number, h: number, draw: Pred): ShapeDef => ({ id, name, w, h, draw });

/** Every outline in the game, in the order they first appear. */
export const SHAPES: readonly ShapeDef[] = [
  S('heart', 'Heart', 22, 20, U(circle(6, 6.2, 6), circle(16, 6.2, 6), poly(0.4, 8, 21.6, 8, 11, 20))),
  S('star', 'Star', 24, 23, starPoly(12, 12.6, 12.4, 5.4, 5)),
  S('arrow', 'Arrow', 20, 24, poly(10, 0, 20, 10, 14, 10, 14, 24, 6, 24, 6, 10, 0, 10)),
  S('house', 'House', 22, 22, D(U(poly(11, 0, 22, 10, 0, 10), rect(3, 9, 19, 22), rect(15, 2, 18.5, 7)), rect(9, 15, 13, 22.5))),
  S('fish', 'Fish', 26, 16, D(U(ellipse(11, 8, 10.5, 7.2), poly(18, 8, 26, 0.5, 26, 15.5)), circle(5.5, 6, 1.3))),
  S('mushroom', 'Mushroom', 24, 22, U(D(ellipse(12, 11, 12, 10.5), rect(-1, 11.5, 25, 30)), rrect(7, 10, 17, 22, 2.5))),
  S('apple', 'Apple', 22, 24, D(U(ellipse(7.6, 15, 7.6, 8.4), ellipse(14.4, 15, 7.6, 8.4), rect(9.8, 1.5, 12.4, 8), ellipse(15.6, 4.4, 4.4, 2.3)), circle(11, 6.4, 1.4))),
  S('tree', 'Pine Tree', 20, 24, U(poly(10, 0, 16, 7.5, 4, 7.5), poly(10, 4, 18, 13.5, 2, 13.5), poly(10, 9, 20, 19.5, 0, 19.5), rect(7.8, 19, 12.2, 24))),
  S('moon', 'Moon', 20, 22, D(circle(10.5, 11, 10.5), circle(16, 7.5, 8.6))),
  S('cloud', 'Cloud', 26, 16, U(circle(7.5, 10, 5.6), circle(14, 7, 6.8), circle(20.2, 10, 5.6), rrect(2.5, 9, 23.5, 15.8, 3))),
  S('cat', 'Cat', 22, 21, D(U(circle(11, 12.5, 8.6), poly(2.6, 9, 3.4, 0, 10, 5.4), poly(19.4, 9, 18.6, 0, 12, 5.4)), circle(7.8, 11.5, 1.4), circle(14.2, 11.5, 1.4))),
  S('rocket', 'Rocket', 16, 26, D(U(rrect(4, 6, 12, 20, 3), poly(8, 0, 12.2, 7.5, 3.8, 7.5), poly(4, 12.5, 0, 21.5, 4.2, 19), poly(12, 12.5, 16, 21.5, 11.8, 19), poly(5.6, 19.5, 10.4, 19.5, 8, 26)), circle(8, 10.5, 1.7))),
  S('crown', 'Crown', 24, 18, U(rect(2, 10, 22, 17.5), poly(2, 11, 2, 1.5, 8, 8.5), poly(6.5, 9.5, 12, 0, 17.5, 9.5), poly(22, 11, 22, 1.5, 16, 8.5))),
  S('bell', 'Bell', 20, 22, U(ellipse(10, 7.4, 6, 6.4), poly(4, 7.4, 16, 7.4, 19, 17, 1, 17), rect(0, 16, 20, 18.5), circle(10, 20, 2.2), rect(9, 0, 11, 2))),
  S('umbrella', 'Umbrella', 24, 24, U(D(circle(12, 12, 12), rect(-1, 12.2, 25, 30)), capsule(12, 11, 12, 21, 1.4), capsule(12, 21.6, 8.6, 21.6, 1.4), capsule(8.4, 21.6, 8.4, 19.2, 1.4))),
  S('mug', 'Mug', 24, 20, U(rrect(1.5, 2.5, 17, 20, 2), D(ellipse(17.5, 10.5, 6, 6.2), ellipse(17.5, 10.5, 2.6, 3)))),
  S('key', 'Key', 26, 12, U(ring(6, 6, 2.3, 6), rect(11, 4.4, 26, 7.6), rect(19, 7, 21.6, 11.5), rect(23.4, 7, 26, 10.2))),
  S('bulb', 'Light Bulb', 18, 24, U(circle(9, 8.2, 8.2), poly(4, 13, 14, 13, 12.6, 18, 5.4, 18), rrect(5.4, 17.6, 12.6, 23.5, 1.6))),
  S('note', 'Music Note', 18, 24, U(ellipse(5.2, 20, 5.2, 3.8), rect(8, 2, 10.6, 20), poly(10.6, 1.6, 18, 5.6, 18, 10, 10.6, 6.2))),
  S('ghost', 'Ghost', 20, 22, D(U(circle(10, 9, 9.2), rect(0.8, 9, 19.2, 20.5)), circle(7.2, 21.6, 2.3), circle(12.8, 21.6, 2.3), circle(6.8, 8.8, 1.6), circle(13.2, 8.8, 1.6))),
  S('bird', 'Bird', 24, 18, D(U(ellipse(11, 11.5, 8.5, 6.2), circle(17, 6.2, 4.6), poly(21, 4.8, 24, 6.6, 21, 8.2), poly(4.5, 10, 0, 5.5, 0, 14)), circle(18, 5.2, 1))),
  S('butterfly', 'Butterfly', 24, 20, U(D(U(ellipse(6, 6.4, 6, 6.4), ellipse(18, 6.4, 6, 6.4), ellipse(6.8, 15.6, 4.6, 4.3), ellipse(17.2, 15.6, 4.6, 4.3)), poly(8.6, -1, 15.4, -1, 12, 7.5), circle(-1.4, 12.2, 4.2), circle(25.4, 12.2, 4.2), poly(10, 21, 14, 21, 12, 14)), capsule(12, 4, 12, 18, 1.5))),
  S('flower', 'Flower', 22, 24, U(...petals(11, 8.4, 6.6, 3.3, 5), circle(11, 8.4, 3.1), capsule(11, 12, 11, 24, 1.4), ellipse(15.2, 19, 3.8, 1.9), ellipse(6.8, 17.6, 3.4, 1.7))),
  S('leaf', 'Leaf', 16, 24, U(I(circle(14, 10, 11.4), circle(2, 10, 11.4)), capsule(8, 18, 8, 24, 1.2))),
  S('sun', 'Sun', 24, 24, U(circle(12, 12, 6.6), ...sunRays(12, 12, 8.6, 11.4, 1.5))),
  S('bolt', 'Lightning', 16, 24, poly(9.6, 0, 0.8, 13.8, 7, 13.8, 3.6, 24, 15.4, 9, 9, 9, 14.4, 0)),
  S('gem', 'Diamond', 24, 20, poly(5, 0, 19, 0, 24, 6.2, 12, 20, 0, 6.2)),
  S('shield', 'Shield', 20, 24, poly(0, 3, 10, 0, 20, 3, 20, 12.5, 10, 24, 0, 12.5)),
  S('trophy', 'Trophy', 22, 24, U(I(ellipse(11, 1.5, 8, 11.5), rect(3, 1.5, 19, 13)), D(ellipse(3.6, 5.8, 3.4, 3.8), ellipse(3.6, 5.8, 1.4, 1.8)), D(ellipse(18.4, 5.8, 3.4, 3.8), ellipse(18.4, 5.8, 1.4, 1.8)), rect(9.4, 12, 12.6, 18), rrect(4.6, 18, 17.4, 23, 1.6))),
  S('bottle', 'Bottle', 12, 26, U(rect(4, 0, 8, 3), rect(4.4, 3, 7.6, 8), poly(4.4, 8, 7.6, 8, 11, 12.5, 1, 12.5), rrect(1, 11.5, 11, 26, 2))),
  S('anchor', 'Anchor', 22, 24, U(ring(11, 3.4, 1.3, 3.4), rect(9.8, 6, 12.2, 22.5), rect(5, 8, 17, 10.2), D(I(circle(11, 12, 11), rect(-1, 12, 23, 30)), circle(11, 12, 8.4)), poly(0, 14.5, 4.2, 10.5, 4.2, 15.5), poly(22, 14.5, 17.8, 10.5, 17.8, 15.5))),
  S('plane', 'Airplane', 26, 24, U(capsule(13, 1.5, 13, 22.5, 1.9), poly(13, 7.5, 26, 13.6, 26, 16, 13, 12.8, 0, 16, 0, 13.6), poly(13, 18.5, 19.4, 22.6, 19.4, 24, 13, 22.4, 6.6, 24, 6.6, 22.6))),
  S('boat', 'Sailboat', 22, 24, U(poly(0.5, 18, 21.5, 18, 17, 24, 5, 24), poly(9.8, 0.5, 9.8, 16.5, 1.5, 16.5), poly(12.2, 3, 12.2, 16.5, 20.5, 16.5), rect(9.8, 0, 12.2, 18.5))),
  S('duck', 'Duck', 24, 20, D(U(ellipse(11.5, 14, 10, 6), circle(17, 6.2, 4.6), poly(21, 5, 24, 7, 21, 8.6), poly(2.5, 11, 0, 6, 6.5, 10)), circle(18, 5.4, 1))),
  S('rabbit', 'Rabbit', 18, 26, U(circle(9, 13.4, 6), ellipse(9, 21.6, 8, 4.6), ellipse(6, 5.2, 2.1, 5.6), ellipse(12, 5.2, 2.1, 5.6))),
  S('turtle', 'Turtle', 26, 18, U(D(ellipse(13, 11.5, 9.2, 8.4), rect(-1, 11.8, 27, 30)), rect(3.6, 11, 22.4, 13.6), circle(23.4, 10.6, 3), ellipse(7, 14.4, 2.3, 2.8), ellipse(19, 14.4, 2.3, 2.8), poly(3.8, 11, 0.6, 12.4, 3.8, 13.6))),
  S('penguin', 'Penguin', 20, 24, U(ellipse(10, 15, 7.6, 8.6), circle(10, 6, 5.4), poly(14.4, 5.2, 18.6, 7, 14.4, 8.4), ellipse(2.4, 14.6, 1.8, 5), ellipse(17.6, 14.6, 1.8, 5), ellipse(6.6, 23.3, 2.8, 1.2), ellipse(13.4, 23.3, 2.8, 1.2))),
  S('owl', 'Owl', 20, 24, D(U(ellipse(10, 14, 9.2, 10), poly(1.8, 7, 3.6, 0, 8.4, 5), poly(18.2, 7, 16.4, 0, 11.6, 5)), circle(6.4, 9.6, 2.1), circle(13.6, 9.6, 2.1))),
  S('cactus', 'Cactus', 20, 24, U(capsule(10, 2.6, 10, 21, 3), capsule(3.6, 6, 3.6, 13, 2), capsule(3.6, 13, 8.5, 13, 2), capsule(16.4, 9, 16.4, 15, 2), capsule(16.4, 15, 11.5, 15, 2), rect(4.5, 20, 15.5, 24))),
  S('icecream', 'Ice Cream', 16, 26, U(poly(2, 11, 14, 11, 8, 26), circle(8, 7.4, 6.4), circle(3.6, 10.4, 3.4), circle(12.4, 10.4, 3.4))),
  S('cherries', 'Cherries', 22, 22, U(circle(6, 16.4, 5.2), circle(16, 17, 5.2), capsule(6, 12, 11, 2, 1.1), capsule(16, 13, 11, 2, 1.1), ellipse(14.6, 3, 4.2, 1.9))),
  S('pear', 'Pear', 18, 24, U(circle(9, 16, 8), circle(9, 8.6, 5), poly(4.6, 9.4, 13.4, 9.4, 16.4, 14, 1.6, 14), rect(8.2, 0, 9.8, 4.4))),
  S('gift', 'Gift', 22, 22, U(rect(1, 8, 21, 12.4), rect(2.6, 12, 19.4, 22), D(ellipse(6.8, 4.8, 4.8, 3.6), ellipse(6.8, 4.8, 1.8, 1.4)), D(ellipse(15.2, 4.8, 4.8, 3.6), ellipse(15.2, 4.8, 1.8, 1.4)))),
  S('padlock', 'Padlock', 18, 22, D(U(rrect(0, 9, 18, 22, 2), D(I(circle(9, 8, 7.2), rect(-1, -1, 19, 9.6)), circle(9, 8, 4)), rect(1.8, 7.5, 5, 10), rect(13, 7.5, 16.2, 10)), circle(9, 14.6, 1.7))),
  S('tshirt', 'T-Shirt', 24, 22, poly(7, 0, 10, 2.2, 14, 2.2, 17, 0, 24, 5.2, 21, 10.2, 18, 8.2, 18, 22, 6, 22, 6, 8.2, 3, 10.2, 0, 5.2)),
  S('pumpkin', 'Pumpkin', 24, 20, U(ellipse(7.6, 12, 7.4, 7.8), ellipse(16.4, 12, 7.4, 7.8), ellipse(12, 12, 6.4, 8.4), rect(10.8, 0, 13.6, 5))),
  S('snowman', 'Snowman', 18, 26, U(circle(9, 19.6, 6.2), circle(9, 10.8, 4.6), rect(4.2, 4.6, 13.8, 6.2), rect(6, 0, 12, 5))),
  S('car', 'Car', 26, 16, U(rrect(0, 6, 26, 12.5, 2.2), poly(5.6, 6.4, 9, 0.8, 18, 0.8, 21.4, 6.4), circle(6.2, 13, 3), circle(19.8, 13, 3))),
  S('balloon', 'Hot Air Balloon', 18, 26, U(circle(9, 8.4, 8.4), poly(4.4, 14.6, 13.6, 14.6, 10.6, 18, 7.4, 18), rect(6.4, 21, 11.6, 26), rect(7, 17.6, 8, 21.4), rect(10, 17.6, 11, 21.4))),
  S('paw', 'Paw Print', 22, 22, U(ellipse(11, 15.6, 6.2, 5.2), ellipse(3.8, 8.8, 2.8, 3.4), ellipse(8.6, 4, 2.8, 3.4), ellipse(13.4, 4, 2.8, 3.4), ellipse(18.2, 8.8, 2.8, 3.4))),
  S('spade', 'Spade', 20, 24, U(circle(5.4, 13.2, 5.4), circle(14.6, 13.2, 5.4), poly(0.3, 12, 19.7, 12, 10, 0), poly(10, 14, 14.4, 24, 5.6, 24))),
  S('club', 'Club', 22, 24, U(circle(11, 6, 5.4), circle(5.4, 13.4, 5.4), circle(16.6, 13.4, 5.4), poly(11, 10, 14.8, 24, 7.2, 24))),
  S('pawn', 'Chess Pawn', 16, 24, U(circle(8, 4.6, 4.2), poly(4.6, 8, 11.4, 8, 12.4, 10.4, 3.6, 10.4), poly(5.8, 10, 10.2, 10, 12.4, 19.4, 3.6, 19.4), rrect(1, 19, 15, 24, 1.6))),
  S('lighthouse', 'Lighthouse', 16, 26, U(poly(4.4, 9.4, 11.6, 9.4, 13.6, 26, 2.4, 26), rect(3.4, 6, 12.6, 9.6), poly(3.4, 6.2, 12.6, 6.2, 8, 0.6))),
  S('whale', 'Whale', 26, 16, D(U(ellipse(11.5, 9.6, 11.4, 6.4), poly(20, 8.4, 26, 1.6, 26, 6, 24, 9.6, 26, 13.4, 26, 15.6), capsule(8, 3.6, 8, 1, 0.9)), circle(5, 8.6, 1.1))),
  S('tent', 'Tent', 24, 20, D(poly(12, 0, 24, 20, 0, 20), poly(12, 9, 15.4, 20, 8.6, 20))),
  S('watermelon', 'Watermelon', 24, 14, D(I(circle(12, 0.6, 12.6), rect(-1, 0.6, 25, 14)), circle(8, 4, 0.9), circle(16, 4, 0.9), circle(12, 7.4, 0.9))),
  S('hexagon', 'Hexagon', 24, 21, regular(12, 10.5, 12, 6)),
  S('ring', 'Donut', 22, 22, ring(11, 11, 4.6, 11)),
  S('hourglass', 'Hourglass', 20, 24, U(poly(1, 1, 19, 1, 10, 12.6), poly(10, 11.4, 19, 23, 1, 23), rect(0, 0, 20, 2), rect(0, 22, 20, 24))),
  S('plus', 'Plus', 22, 22, U(rrect(7, 0, 15, 22, 2), rrect(0, 7, 22, 15, 2))),
  S('diamond', 'Rhombus', 20, 24, poly(10, 0, 20, 12, 10, 24, 0, 12)),
  S('octagon', 'Octagon', 22, 22, regular(11, 11, 11.6, 8, Math.PI / 8)),
  S('triangle', 'Triangle', 24, 21, poly(12, 0, 24, 21, 0, 21)),
  S('circle', 'Circle', 22, 22, circle(11, 11, 11)),
];

export const SHAPE_BY_ID: ReadonlyMap<string, ShapeDef> = new Map(SHAPES.map((s) => [s.id, s]));

/** Board size for a shape whose longer side has `long` cells. */
export function shapeSize(def: ShapeDef, long: number): { w: number; h: number } {
  if (def.w >= def.h) return { w: long, h: Math.max(3, Math.round((long * def.h) / def.w)) };
  return { w: Math.max(3, Math.round((long * def.w) / def.h)), h: long };
}

/** Rasterises a shape: a cell is inside when most of its sample points are. */
export function shapeMask(def: ShapeDef | 'rect', w: number, h: number): Uint8Array {
  const m = new Uint8Array(w * h);
  if (def === 'rect') return m.fill(1);
  const offs = [
    [0.5, 0.5],
    [0.25, 0.25],
    [0.75, 0.25],
    [0.25, 0.75],
    [0.75, 0.75],
  ];
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      let hits = 0;
      for (const [ox, oy] of offs) if (def.draw(((x + ox) / w) * def.w, ((y + oy) / h) * def.h)) hits++;
      m[y * w + x] = hits >= 3 ? 1 : 0;
    }
  }
  return m;
}
