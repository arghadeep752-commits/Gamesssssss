import assert from 'node:assert/strict';
import { test } from 'node:test';
import {
  bestHint,
  buildOccupancy,
  firstBlocker,
  freeArrows,
  type Level,
  solve,
  validateLevel,
} from '../src/game/engine';
import { arrowGeom, hitTest, makeFlight, MAX_RUNS } from '../src/game/geometry';
import { LEVEL_PACK } from '../src/game/levelPack';
import { buildLevel, decodeLevel, encodeLevel, getDaily, getLevel, levelSpec } from '../src/game/levels';
import { SHAPES, shapeMask, shapeSize } from '../src/game/shapes';

const rectMask = (w: number, h: number) => shapeMask('rect', w, h);
const runs = (cells: readonly number[]) => {
  let r = 1;
  for (let i = 2; i < cells.length; i++) if (cells[i] - cells[i - 1] !== cells[i - 1] - cells[i - 2]) r++;
  return r;
};

test('an arrow is blocked only by arrows in front of its head', () => {
  // 3x3: arrow 0 points right along the middle row, arrow 1 stands in column 2.
  const level: Level = {
    w: 3,
    h: 3,
    mask: rectMask(3, 3),
    arrows: [
      { id: 0, cells: [3, 4], dir: 1 },
      { id: 1, cells: [2, 5, 8], dir: 2 },
    ],
  };
  const occ = buildOccupancy(level);
  assert.deepEqual(firstBlocker(level, occ, level.arrows[0]), { id: 1, gap: 0 });
  assert.equal(firstBlocker(level, occ, level.arrows[1]), null);
  assert.deepEqual(freeArrows(level, occ, [0, 0]), [1]);
  assert.deepEqual(solve(level), [1, 0]);
  assert.equal(bestHint(level, occ, [0, 0]), 1);
  assert.deepEqual(validateLevel(level), []);
});

test('mutual blocking is detected as unsolvable', () => {
  const level: Level = {
    w: 4,
    h: 1,
    mask: rectMask(4, 1),
    arrows: [
      { id: 0, cells: [0, 1], dir: 1 },
      { id: 1, cells: [3, 2], dir: 3 },
    ],
  };
  assert.equal(solve(level), null);
  assert.ok(validateLevel(level).includes('unsolvable'));
});

test('every packed level is valid, solvable and matches its spec', () => {
  assert.equal(LEVEL_PACK.length, 300);
  for (let n = 1; n <= LEVEL_PACK.length; n++) {
    const info = getLevel(n);
    assert.deepEqual(validateLevel(info.level), [], `level ${n}`);
    assert.ok(info.level.arrows.length >= 2, `level ${n} has ${info.level.arrows.length} arrows`);
    const spec = levelSpec(n);
    assert.equal(info.level.w, spec.params.w, `level ${n} width`);
    assert.equal(info.level.h, spec.params.h, `level ${n} height`);
    assert.equal(info.tier, spec.tier, `level ${n} tier`);
    for (const a of info.level.arrows) assert.ok(runs(a.cells) + 1 <= MAX_RUNS, `level ${n} arrow ${a.id} too twisty`);
  }
});

test('levels after the pack are generated on the fly, valid and repeatable', () => {
  for (const n of [301, 302, 315, 350, 500]) {
    const a = buildLevel(n);
    assert.deepEqual(validateLevel(a.level), [], `level ${n}`);
    assert.equal(JSON.stringify(a.level.arrows), JSON.stringify(buildLevel(n).level.arrows));
    for (const arrow of a.level.arrows) assert.ok(runs(arrow.cells) + 1 <= MAX_RUNS);
  }
});

test('pack encoding round-trips', () => {
  const info = buildLevel(123);
  const back = decodeLevel(encodeLevel(info));
  assert.equal(JSON.stringify(back.level.arrows), JSON.stringify(info.level.arrows));
  assert.deepEqual(Array.from(back.level.mask), Array.from(info.level.mask));
  assert.equal(back.shape, info.shape);
  assert.equal(back.tier, info.tier);
});

test('every shape rasterises to a usable board', () => {
  const ids = new Set<string>();
  for (const s of SHAPES) {
    assert.ok(!ids.has(s.id), `duplicate shape ${s.id}`);
    ids.add(s.id);
    for (const long of [9, 16, 28]) {
      const { w, h } = shapeSize(s, long);
      const m = shapeMask(s, w, h);
      const n = m.reduce((a, b) => a + b, 0);
      assert.ok(n >= w * h * 0.2, `${s.id} at ${long}: only ${n} cells`);
    }
  }
});

test('a year of daily puzzles is valid', () => {
  const start = new Date(2026, 0, 1);
  for (let i = 0; i < 366; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const lvl = getDaily(key).level;
    assert.deepEqual(validateLevel(lvl), [], key);
    assert.ok(lvl.arrows.length >= 8, `${key}: ${lvl.arrows.length} arrows`);
    for (const a of lvl.arrows) assert.ok(runs(a.cells) + 1 <= MAX_RUNS, `${key} arrow too twisty`);
  }
});

test('hit testing maps touches to arrows with tolerance', () => {
  const lvl = getLevel(30).level;
  const occ = buildOccupancy(lvl);
  const size = 30;
  const a = lvl.arrows[0];
  const cell = a.cells[0];
  const x = (cell % lvl.w) + 0.5;
  const y = Math.floor(cell / lvl.w) + 0.5;
  assert.equal(hitTest(lvl, occ, x * size, y * size, size), 0);
  assert.equal(hitTest(lvl, occ, -500, -500, size), -1);
});

test('exit flights travel past the edge of the play area', () => {
  const lvl = getLevel(40).level;
  const size = 28;
  for (const a of lvl.arrows) {
    const g = arrowGeom(lvl, a, size);
    const f = makeFlight(g, size, 10, 20, lvl.w * size + 20, lvl.h * size + 40, 'exit', 0);
    // Tail position at the end of the flight:
    const tx = f.hx + f.dx * (f.travel - f.len);
    const ty = f.hy + f.dy * (f.travel - f.len);
    const outside = tx < 0 || ty < 0 || tx > lvl.w * size + 20 || ty > lvl.h * size + 40;
    assert.ok(outside, `arrow ${a.id} tail stays visible`);
    assert.ok(f.n >= 3 && f.n - 1 <= MAX_RUNS, `arrow ${a.id} has ${f.n - 1} runs`);
    assert.ok(f.cum[f.n - 1] >= f.travel + f.len, 'trajectory long enough');
  }
});
