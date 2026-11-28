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
import { arrowGeom, hitTest, makeFlight } from '../src/game/geometry';
import { getDaily, getLevel, levelParams } from '../src/game/levels';
import { shapeMask } from '../src/game/shapes';

const rectMask = (w: number, h: number) => shapeMask('rect', w, h);

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

test('the first 400 levels are valid, solvable and deterministic', () => {
  for (let n = 1; n <= 400; n++) {
    const lvl = getLevel(n);
    assert.deepEqual(validateLevel(lvl), [], `level ${n}`);
    assert.ok(lvl.arrows.length >= 2, `level ${n} has ${lvl.arrows.length} arrows`);
    const p = levelParams(n);
    assert.equal(lvl.w, p.w);
    assert.equal(lvl.h, p.h);
  }
  // Regenerating gives the identical puzzle.
  assert.deepEqual(JSON.stringify(getLevel(77).arrows), JSON.stringify(getLevel(77).arrows));
});

test('a year of daily puzzles is valid', () => {
  const start = new Date(2026, 0, 1);
  for (let i = 0; i < 366; i++) {
    const d = new Date(start.getFullYear(), start.getMonth(), start.getDate() + i);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
    const lvl = getDaily(key);
    assert.deepEqual(validateLevel(lvl), [], key);
    assert.ok(lvl.arrows.length >= 8, `${key}: ${lvl.arrows.length} arrows`);
  }
});

test('hit testing maps touches to arrows with tolerance', () => {
  const lvl = getLevel(30);
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
  const lvl = getLevel(40);
  const size = 28;
  for (const a of lvl.arrows) {
    const g = arrowGeom(lvl, a, size);
    const f = makeFlight(g, size, 10, 20, lvl.w * size + 20, lvl.h * size + 40, 'exit', 0);
    // Tail position at the end of the flight:
    const tx = f.hx + f.dx * (f.travel - f.len);
    const ty = f.hy + f.dy * (f.travel - f.len);
    const outside = tx < 0 || ty < 0 || tx > lvl.w * size + 20 || ty > lvl.h * size + 40;
    assert.ok(outside, `arrow ${a.id} tail stays visible`);
    assert.ok(f.n >= 3 && f.n - 1 <= 12, `arrow ${a.id} has ${f.n - 1} runs`);
    assert.ok(f.cum[f.n - 1] >= f.travel + f.len, 'trajectory long enough');
  }
});
