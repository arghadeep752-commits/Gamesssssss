import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { activeBlockers, freeArrows, inspectCorridor, isComplete, isFree, prepareLevel } from '../src/game/board';
import { generateLayout } from '../src/game/generator';
import { corridorIndices, decodeArrow, encodeArrow, exitDistanceCells, unpackLevel } from '../src/game/geometry';
import { createRng } from '../src/game/rng';
import { nextMove, simulateRemove, solve } from '../src/game/solver';
import type { LevelDef, Tier } from '../src/game/types';
import { bruteForceBlockers, validateLevel } from '../src/game/validate';

const lvl = (w: number, h: number, a: string, tier: Tier = 'easy'): LevelDef =>
  unpackLevel({ w, h, a }, { id: 'T', number: 1, tier });

const cellsOf = (level: LevelDef, idxs: number[]) => idxs.map((i) => `${i % level.width},${Math.floor(i / level.width)}`);

describe('arrow encoding', () => {
  it('decodes tail, path and head direction', () => {
    const a = decodeArrow('12RRD', 0);
    assert.deepEqual(a.cells, [
      { x: 1, y: 2 },
      { x: 2, y: 2 },
      { x: 3, y: 2 },
      { x: 3, y: 3 },
    ]);
    assert.equal(a.dir, 'D');
  });
  it('round-trips through encode', () => {
    for (const t of ['00R', 'a3LLUU', '45DRDRU', '9dUUULLD']) assert.equal(encodeArrow(decodeArrow(t, 0)), t);
  });
  it('rejects malformed tokens', () => {
    assert.throws(() => decodeArrow('1', 0));
    assert.throws(() => decodeArrow('12X', 0));
  });
});

describe('corridors and blocking', () => {
  it('a straight arrow sweeps the cells ahead of its head', () => {
    const level = lvl(5, 3, '01RR'); // (0,1)(1,1)(2,1) -> R
    assert.deepEqual(cellsOf(level, corridorIndices(level.arrows[0], 5, 3)), ['3,1', '4,1']);
  });

  it('an arrow at the edge facing out has an empty corridor', () => {
    const level = lvl(4, 4, '20R'); // (2,0)(3,0) -> R, head on the right edge
    assert.deepEqual(corridorIndices(level.arrows[0], 4, 4), []);
    assert.equal(isFree(prepareLevel(level), [false], 0), true);
  });

  it('a bent arrow sweeps the lane of every cell, not just the head', () => {
    // (0,0)(1,0)(1,1) exiting down: lanes x=0 from y=1 and x=1 from y=2.
    const level = lvl(3, 4, '00RD');
    const got = cellsOf(level, corridorIndices(level.arrows[0], 3, 4)).sort();
    assert.deepEqual(got, ['0,1', '0,2', '0,3', '1,2', '1,3'].sort());
  });

  it('detects a blocker sitting in the corridor', () => {
    // A: row 2 heading right; B: column 3 crossing row 2.
    const level = lvl(4, 5, '02RR 31DD');
    const p = prepareLevel(level);
    const removed = [false, false];
    assert.deepEqual(activeBlockers(p, removed, 0), [1]);
    assert.equal(isFree(p, removed, 0), false);
    assert.equal(isFree(p, removed, 1), true);
    assert.deepEqual(freeArrows(p, removed), [1]);
    // After B leaves, A is free.
    assert.equal(isFree(p, simulateRemove(removed, 1), 0), true);
  });

  it('an arrow behind another one does not block it', () => {
    const level = lvl(5, 1, '00R 30R'); // A (0,0)->(1,0) R ; B (3,0)->(4,0) R
    const p = prepareLevel(level);
    assert.deepEqual(p.blockers[1], []); // B is in front of nothing
    assert.deepEqual(p.blockers[0], [1]); // B sits in A's lane
  });

  it('cells beside the lane do not block', () => {
    const level = lvl(4, 3, '01RR 30D'); // A row 1 -> R ; B (3,0)->(3,1) D stands in A's lane
    const p = prepareLevel(level);
    assert.deepEqual(p.blockers[0], [1]); // (3,1) is in the lane
    const level2 = lvl(4, 3, '01RR 22R'); // B at (2,2)->(3,2), row 2, beside the lane
    assert.deepEqual(prepareLevel(level2).blockers[0], []);
  });

  it('agrees with a naive step-by-step simulation on many random layouts', () => {
    for (let s = 1; s <= 60; s++) {
      const rng = createRng(s);
      const width = 4 + (s % 7);
      const height = 5 + (s % 9);
      const arrows = generateLayout(
        { width, height, targetArrows: 40, minLen: 2, maxLen: 6, turnChance: 0.4, hookChance: 0.1, candidates: 3 },
        rng,
      );
      const level: LevelDef = { id: `R${s}`, number: 1, tier: 'hard', width, height, arrows };
      const p = prepareLevel(level);
      for (const a of arrows) assert.deepEqual([...p.blockers[a.id]], bruteForceBlockers(level, a.id), `seed ${s} arrow ${a.id}`);
    }
  });

  it('refuses overlapping arrows (paths can never cross)', () => {
    const level = lvl(4, 4, '01RR 20DD'); // both use (2,1)
    assert.throws(() => prepareLevel(level), /overlap/);
    assert.ok(validateLevel(level).some((e) => e.includes('overlap')));
  });

  it('inspectCorridor marks blocked cells for the path helper', () => {
    const level = lvl(4, 5, '02RR 31DD');
    const p = prepareLevel(level);
    const info = inspectCorridor(p, [false, false], 0);
    assert.deepEqual(info.blockers, [1]);
    assert.deepEqual(info.cells, [{ x: 3, y: 2, blocked: true }]);
    assert.deepEqual(inspectCorridor(p, [false, true], 0).cells, [{ x: 3, y: 2, blocked: false }]);
  });

  it('computes how far an arrow must travel to leave', () => {
    const level = lvl(5, 4, '01RR 33UU');
    assert.equal(exitDistanceCells(level.arrows[0], 5, 4), 5); // leftmost cell x=0 must pass x=4
    assert.equal(exitDistanceCells(level.arrows[1], 5, 4), 4); // lowest cell y=3 must pass y=0
  });
});

describe('removal and completion', () => {
  it('clears the board only when every arrow is removed', () => {
    const level = lvl(4, 5, '20R 01RR 33UU 24LL');
    const p = prepareLevel(level);
    let removed = level.arrows.map(() => false);
    assert.equal(isComplete(removed), false);
    for (const id of [0, 3, 2, 1]) {
      assert.equal(isFree(p, removed, id), true, `arrow ${id} should be free`);
      removed = simulateRemove(removed, id);
    }
    assert.equal(isComplete(removed), true);
  });
});

describe('solver', () => {
  it('solves a chain in dependency order', () => {
    const level = lvl(4, 5, '20R 01RR 33UU 24LL');
    const p = prepareLevel(level);
    const res = solve(p, level.arrows.map(() => false));
    assert.equal(res.solvable, true);
    assert.ok(res.order.indexOf(0) < res.order.indexOf(2));
    assert.ok(res.order.indexOf(2) < res.order.indexOf(1));
    assert.equal(res.rounds, 3);
  });

  it('detects an impossible cycle', () => {
    // A (0,0)->(1,0) exits right into B; B (2,0)->(2,1)->(1,1) exits left through A's row.
    const level = lvl(3, 2, '00R 20DL');
    const p = prepareLevel(level);
    assert.deepEqual(p.blockers[0], [1]);
    assert.deepEqual(p.blockers[1], [0]);
    const res = solve(p, [false, false]);
    assert.equal(res.solvable, false);
    assert.deepEqual(res.stuck, [0, 1]);
    assert.deepEqual(nextMove(p, [false, false]), { kind: 'unsolvable', stuck: [0, 1] });
    assert.ok(validateLevel(level).some((e) => e.includes('unsolvable')));
  });

  it('hints are always legal and pick the most useful free arrow', () => {
    // Arrow 0 (2,0)->(3,0) blocks arrow 2, which blocks arrow 1; arrow 3 blocks nothing.
    const level = lvl(4, 5, '20R 01RR 33UU 24LL');
    const p = prepareLevel(level);
    assert.deepEqual(nextMove(p, [false, false, false, false]), { kind: 'move', arrowId: 0 });
    assert.deepEqual(nextMove(p, [true, true, true, true]), { kind: 'complete' });
  });

  it('any order of free moves finishes a solvable level (no dead ends)', () => {
    for (let s = 1; s <= 40; s++) {
      const arrows = generateLayout(
        { width: 8, height: 10, targetArrows: 30, minLen: 2, maxLen: 5, turnChance: 0.3, candidates: 4 },
        createRng(1000 + s),
      );
      const level: LevelDef = { id: `S${s}`, number: 1, tier: 'normal', width: 8, height: 10, arrows };
      const p = prepareLevel(level);
      const rng = createRng(s);
      let removed = arrows.map(() => false);
      for (let step = 0; step < arrows.length; step++) {
        const free = freeArrows(p, removed);
        assert.ok(free.length > 0, `seed ${s}: stuck at step ${step}`);
        const hint = nextMove(p, removed);
        assert.equal(hint.kind, 'move');
        if (hint.kind === 'move') assert.ok(free.includes(hint.arrowId));
        removed = simulateRemove(removed, rng.pick(free));
      }
      assert.equal(isComplete(removed), true);
    }
  });
});

describe('generator', () => {
  it('is deterministic for a seed', () => {
    const opts = { width: 7, height: 9, targetArrows: 20, minLen: 2, maxLen: 5, turnChance: 0.3, candidates: 4 };
    const a = generateLayout(opts, createRng(42)).map(encodeArrow).join(' ');
    const b = generateLayout(opts, createRng(42)).map(encodeArrow).join(' ');
    assert.equal(a, b);
  });
  it('only produces valid, solvable layouts', () => {
    for (let s = 0; s < 50; s++) {
      const arrows = generateLayout(
        { width: 9, height: 12, targetArrows: 40, minLen: 2, maxLen: 7, turnChance: 0.4, hookChance: 0.1, candidates: 6, fillGaps: true },
        createRng(s * 31 + 7),
      );
      const level: LevelDef = { id: `G${s}`, number: 1, tier: 'expert', width: 9, height: 12, arrows };
      assert.deepEqual(validateLevel(level), []);
    }
  });
});
