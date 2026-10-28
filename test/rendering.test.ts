import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { prepareLevel } from '../src/game/board';
import { unpackLevel } from '../src/game/geometry';
import { getLevel, LEVEL_COUNT } from '../src/levels';
import { arrowGeometry, exitDurationMs, gridDotsPath } from '../src/utils/arrowPath';
import { fitCellSize, hitTest } from '../src/utils/hitTest';

const level = unpackLevel({ w: 4, h: 5, a: '02RR 31DD 14L' }, { id: 'T', number: 1, tier: 'easy' });
const p = prepareLevel(level);
const none = [false, false, false];

describe('hit testing matches the engine grid', () => {
  const cell = 40;
  it('selects the arrow whose cell was touched', () => {
    assert.equal(hitTest(p.occupancy, 4, 5, none, 20, 100, cell), 0); // (0,2)
    assert.equal(hitTest(p.occupancy, 4, 5, none, 135, 60, cell), 1); // (3,1)
    assert.equal(hitTest(p.occupancy, 4, 5, none, 10, 170, cell), 2); // (0,4)
  });
  it('gives thin arrows a forgiving margin from empty neighbouring cells', () => {
    // (1,1) is empty; touch near its bottom edge, just above arrow 0 at (1,2).
    assert.equal(hitTest(p.occupancy, 4, 5, none, 60, 78, cell), 0);
  });
  it('ignores touches far from any arrow and removed arrows', () => {
    assert.equal(hitTest(p.occupancy, 4, 5, none, 60, 20, cell), -1); // centre of empty (1,0)
    assert.equal(hitTest(p.occupancy, 4, 5, [true, false, false], 20, 100, cell), -1);
    assert.equal(hitTest(p.occupancy, 4, 5, none, -50, -50, cell), -1);
  });
});

describe('drawing geometry', () => {
  it('keeps every arrow inside its own cells', () => {
    for (let n = 1; n <= LEVEL_COUNT; n += 7) {
      const lvl = getLevel(n);
      for (const a of lvl.arrows) {
        const g = arrowGeometry(a, 30, lvl.width, lvl.height);
        assert.ok(g.left >= 0 && g.top >= 0);
        assert.ok(g.left + g.width <= lvl.width * 30 + 1e-9);
        assert.ok(g.top + g.height <= lvl.height * 30 + 1e-9);
        const nums = (g.body + g.head).match(/-?\d+(\.\d+)?/g)!.map(Number);
        for (let i = 0; i < nums.length; i += 2) {
          assert.ok(nums[i] >= 0 && nums[i] <= g.width, `x out of box in level ${n}`);
          assert.ok(nums[i + 1] >= 0 && nums[i + 1] <= g.height, `y out of box in level ${n}`);
        }
      }
    }
  });
  it('travels far enough to leave the board', () => {
    const g = arrowGeometry(level.arrows[0], 40, 4, 5); // (0..2, 2) heading right
    assert.equal(g.dx, 1);
    assert.ok(g.left + g.exitDistance >= 4 * 40);
  });
  it('keeps exit animations between 250 and 400 ms', () => {
    assert.equal(exitDurationMs(1, 250, 14, 400), 264);
    assert.equal(exitDurationMs(30, 250, 14, 400), 400);
    assert.equal(exitDurationMs(0, 250, 14, 400), 250);
  });
  it('draws the grid as one path with a dot per cell', () => {
    assert.equal((gridDotsPath(4, 5, 20).match(/M/g) ?? []).length, 20);
  });
  it('fits the board to small and large screens', () => {
    assert.equal(fitCellSize(360, 500, 10, 14), 34);
    assert.equal(fitCellSize(1200, 2000, 4, 5), 64, 'capped on big screens');
    assert.equal(fitCellSize(0, 500, 4, 5), 0, 'not measured yet');
  });
});
