import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { RULES, STAR_RULES, type GameRules } from '../src/config/gameConfig';
import { prepareLevel } from '../src/game/board';
import { unpackLevel } from '../src/game/geometry';
import { isBetter, makeResult, penaltyFor, starsFor } from '../src/game/scoring';
import {
  newSession,
  requestHint,
  restart,
  restoreSession,
  scanArrow,
  snapshotSession,
  tapArrow,
  undo,
  type SessionState,
} from '../src/game/session';
import type { Tier } from '../src/game/types';

// Chain: arrow 0 blocks 2, arrow 2 blocks 1, arrow 3 is independent.
const prep = (tier: Tier = 'easy') =>
  prepareLevel(unpackLevel({ w: 4, h: 5, a: '20R 01RR 33UU 24LL' }, { id: 'L099', number: 99, tier }));

describe('tapping arrows', () => {
  it('removes a free arrow and counts the move', () => {
    const p = prep();
    const s0 = newSession(p, RULES);
    const { state, outcome } = tapArrow(p, s0, 0, RULES);
    assert.deepEqual(outcome, { kind: 'removed', arrowId: 0, completed: false });
    assert.equal(state.removed[0], true);
    assert.equal(state.moves, 1);
    assert.deepEqual(state.history, [0]);
    assert.equal(s0.removed[0], false, 'previous state is not mutated');
  });

  it('a blocked tap leaves the arrow, counts a mistake and costs a heart', () => {
    const p = prep();
    const { state, outcome } = tapArrow(p, newSession(p, RULES), 1, RULES);
    assert.equal(outcome.kind, 'blocked');
    if (outcome.kind === 'blocked') {
      assert.deepEqual(outcome.blockers, [2]);
      assert.equal(outcome.lifeLost, true);
    }
    assert.equal(state.removed[1], false);
    assert.equal(state.mistakes, 1);
    assert.equal(state.livesLeft, RULES.lives - 1);
  });

  it('runs out of hearts into game over, and then ignores taps', () => {
    const p = prep();
    let s = newSession(p, RULES);
    for (let i = 0; i < RULES.lives; i++) s = tapArrow(p, s, 1, RULES).state;
    assert.equal(s.status, 'lost');
    assert.equal(s.livesLeft, 0);
    assert.deepEqual(tapArrow(p, s, 0, RULES).outcome, { kind: 'ignored' });
  });

  it('tutorial blocked taps count as mistakes but never cost hearts', () => {
    const p = prep('tutorial');
    let s = newSession(p, RULES);
    for (let i = 0; i < 5; i++) s = tapArrow(p, s, 1, RULES).state;
    assert.equal(s.mistakes, 5);
    assert.equal(s.livesLeft, RULES.lives);
    assert.equal(s.status, 'playing');
  });

  it('heart loss can be switched off in the rules', () => {
    const p = prep();
    const rules: GameRules = { ...RULES, blockedTapCostsLife: false };
    const s = tapArrow(p, newSession(p, rules), 1, rules).state;
    assert.equal(s.livesLeft, rules.lives);
    assert.equal(s.mistakes, 1);
  });

  it('ignores removed or unknown arrows (no double moves)', () => {
    const p = prep();
    const s1 = tapArrow(p, newSession(p, RULES), 0, RULES).state;
    assert.deepEqual(tapArrow(p, s1, 0, RULES).outcome, { kind: 'ignored' });
    assert.deepEqual(tapArrow(p, s1, 99, RULES).outcome, { kind: 'ignored' });
    assert.equal(tapArrow(p, s1, 0, RULES).state, s1);
  });

  it('completes exactly once when the last arrow leaves', () => {
    const p = prep();
    let s: SessionState = newSession(p, RULES);
    const outcomes = [0, 3, 2, 1].map((id) => {
      const r = tapArrow(p, s, id, RULES);
      s = r.state;
      return r.outcome;
    });
    assert.deepEqual(outcomes[3], { kind: 'removed', arrowId: 1, completed: true });
    assert.equal(outcomes.filter((o) => o.kind === 'removed' && o.completed).length, 1);
    assert.equal(s.status, 'won');
    assert.deepEqual(tapArrow(p, s, 1, RULES).outcome, { kind: 'ignored' });
  });
});

describe('undo and restart', () => {
  it('undo restores the previous board but keeps mistakes and lost hearts', () => {
    const p = prep();
    let s = newSession(p, RULES);
    s = tapArrow(p, s, 1, RULES).state; // mistake
    s = tapArrow(p, s, 0, RULES).state;
    s = tapArrow(p, s, 2, RULES).state;
    const u = undo(s);
    assert.equal(u.restored, 2);
    assert.deepEqual(u.state.removed, [true, false, false, false]);
    assert.deepEqual(u.state.history, [0]);
    assert.equal(u.state.mistakes, 1);
    assert.equal(u.state.livesLeft, RULES.lives - 1);
    assert.equal(u.state.moves, 2, 'moves are not refunded');
    assert.equal(undo(undo(u.state).state).restored, null, 'nothing left to undo');
  });

  it('restart resets the attempt to the original layout', () => {
    const p = prep();
    let s = newSession(p, RULES);
    s = tapArrow(p, s, 0, RULES).state;
    s = tapArrow(p, s, 1, RULES).state;
    const r = restart(p, RULES);
    assert.deepEqual(r.removed, [false, false, false, false]);
    assert.equal(r.moves + r.mistakes + r.hintsUsed, 0);
    assert.equal(r.livesLeft, RULES.lives);
  });
});

describe('hints and the path helper', () => {
  it('a hint highlights a free arrow and is consumed once', () => {
    const p = prep();
    const s0 = newSession(p, RULES);
    const h1 = requestHint(p, s0);
    assert.deepEqual(h1.outcome, { kind: 'shown', arrowId: 0, consumed: true });
    assert.equal(h1.state.hintsUsed, 1);
    const h2 = requestHint(p, h1.state);
    assert.deepEqual(h2.outcome, { kind: 'shown', arrowId: 0, consumed: false });
    assert.equal(h2.state.hintsUsed, 1);
    // Following the hint clears it; the next hint is a new arrow.
    const s = tapArrow(p, h2.state, 0, RULES).state;
    assert.equal(s.hintArrow, null);
    const h3 = requestHint(p, s);
    assert.equal(h3.outcome.kind, 'shown');
    if (h3.outcome.kind === 'shown') assert.ok([2, 3].includes(h3.outcome.arrowId));
  });

  it('scan shows the corridor and blockers, using one charge', () => {
    const p = prep();
    const s0 = newSession(p, RULES);
    const r = scanArrow(p, s0, 1);
    assert.equal(r.state.scansLeft, RULES.scansPerLevel - 1);
    assert.deepEqual(r.inspection?.blockers, [2]);
    let s = s0;
    for (let i = 0; i < RULES.scansPerLevel; i++) s = scanArrow(p, s, 1).state;
    assert.equal(scanArrow(p, s, 1).inspection, null, 'no charges left');
  });
});

describe('session snapshots', () => {
  it('round-trips a game in progress', () => {
    const p = prep();
    let s = newSession(p, RULES);
    s = tapArrow(p, s, 0, RULES).state;
    s = tapArrow(p, s, 1, RULES).state;
    const restored = restoreSession(p, snapshotSession(s), RULES);
    assert.ok(restored);
    assert.deepEqual(restored!.removed, s.removed);
    assert.equal(restored!.mistakes, 1);
    assert.equal(restored!.livesLeft, s.livesLeft);
  });

  it('rejects snapshots that replay an illegal move or wrong level', () => {
    const p = prep();
    const good = snapshotSession(tapArrow(p, newSession(p, RULES), 0, RULES).state);
    assert.equal(restoreSession(p, { ...good, history: [1] }, RULES), null);
    assert.equal(restoreSession(p, { ...good, history: [0, 0] }, RULES), null);
    assert.equal(restoreSession(p, { ...good, levelId: 'L001' }, RULES), null);
    assert.equal(restoreSession(p, { ...good, livesLeft: 0 }, RULES), null);
    assert.equal(restoreSession(p, { ...good, moves: 0 }, RULES), null);
  });
});

describe('stars', () => {
  it('awards stars from mistakes, hints and extra moves', () => {
    const base = { arrowCount: 10, moves: 10, mistakes: 0, hints: 0 };
    assert.equal(starsFor(base, STAR_RULES), 3);
    assert.equal(starsFor({ ...base, mistakes: 1 }, STAR_RULES), 2);
    assert.equal(starsFor({ ...base, mistakes: 1, hints: 1 }, STAR_RULES), 2);
    assert.equal(starsFor({ ...base, mistakes: 2, hints: 1 }, STAR_RULES), 1);
    assert.equal(penaltyFor({ ...base, moves: 13 }, STAR_RULES), 1);
    assert.equal(starsFor({ ...base, moves: 11 }, STAR_RULES), 3, 'one undo-replay is free');
  });

  it('compares results deterministically', () => {
    const r = (stars: 1 | 2 | 3, mistakes: number, hints = 0, moves = 10) => ({ stars, mistakes, hints, moves });
    assert.equal(isBetter(r(3, 0), undefined), true);
    assert.equal(isBetter(r(2, 1), r(3, 0)), false);
    assert.equal(isBetter(r(3, 0), r(2, 1)), true);
    assert.equal(isBetter(r(2, 0, 1), r(2, 1, 0)), true);
    assert.equal(isBetter(r(2, 1, 0), r(2, 1, 1)), true);
    assert.equal(isBetter(r(3, 0, 0, 10), r(3, 0, 0, 10)), false, 'equal is not better');
    assert.equal(makeResult({ arrowCount: 4, moves: 4, mistakes: 0, hints: 0 }, STAR_RULES).stars, 3);
  });
});
