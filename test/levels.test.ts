import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { prepareLevel } from '../src/game/board';
import { encodeArrow } from '../src/game/geometry';
import { measure } from '../src/game/solver';
import { validateLevel } from '../src/game/validate';
import { addDays, dailyLevel, dailyTier, localDateKey, parseDateKey } from '../src/levels/daily';
import { getLevel, LEVEL_COUNT, levelId, levelNumberFromId } from '../src/levels/index';
import { tierForLevel } from '../src/levels/tierParams';

describe('shipped levels', () => {
  it('ships at least 100 levels', () => {
    assert.ok(LEVEL_COUNT >= 100);
  });

  it('every level is valid and solvable', () => {
    for (let n = 1; n <= LEVEL_COUNT; n++) assert.deepEqual(validateLevel(getLevel(n)), [], `level ${n}`);
  });

  it('levels are distinct', () => {
    const keys = new Set<string>();
    for (let n = 1; n <= LEVEL_COUNT; n++) {
      const l = getLevel(n);
      keys.add(`${l.width}x${l.height}:${l.arrows.map(encodeArrow).join(' ')}`);
    }
    assert.equal(keys.size, LEVEL_COUNT);
  });

  it('follows the tier ranges', () => {
    assert.equal(getLevel(1).tier, 'tutorial');
    assert.equal(getLevel(10).tier, 'tutorial');
    assert.equal(getLevel(11).tier, 'easy');
    assert.equal(getLevel(26).tier, 'normal');
    assert.equal(getLevel(51).tier, 'hard');
    assert.equal(getLevel(76).tier, 'expert');
    assert.equal(getLevel(100).tier, 'expert');
    for (let n = 1; n <= LEVEL_COUNT; n++) assert.equal(getLevel(n).tier, tierForLevel(n));
  });

  it('gets harder: expert levels are bigger and deeper than tutorial levels', () => {
    const avg = (from: number, to: number, f: (m: ReturnType<typeof measure>) => number) => {
      let s = 0;
      for (let n = from; n <= to; n++) s += f(measure(prepareLevel(getLevel(n))));
      return s / (to - from + 1);
    };
    assert.ok(avg(76, 100, (m) => m.arrows) > avg(1, 10, (m) => m.arrows) * 3);
    assert.ok(avg(76, 100, (m) => m.rounds) > avg(1, 10, (m) => m.rounds) * 2);
    assert.ok(avg(1, 5, (m) => m.bentArrows) === 0, 'first tutorial levels use straight arrows only');
  });

  it('maps ids both ways', () => {
    assert.equal(levelId(7), 'L007');
    assert.equal(levelNumberFromId('L007'), 7);
    assert.equal(levelNumberFromId('L000'), null);
    assert.equal(levelNumberFromId('nope'), null);
    assert.throws(() => getLevel(0));
    assert.throws(() => getLevel(LEVEL_COUNT + 1));
  });
});

describe('daily challenge', () => {
  it('formats local date keys', () => {
    assert.equal(localDateKey(new Date(2026, 9, 28, 23, 59)), '2026-10-28');
    assert.equal(localDateKey(new Date(2026, 0, 5, 0, 0)), '2026-01-05');
  });

  it('steps across month, year and leap days', () => {
    assert.equal(addDays('2026-10-31', 1), '2026-11-01');
    assert.equal(addDays('2026-12-31', 1), '2027-01-01');
    assert.equal(addDays('2028-02-28', 1), '2028-02-29');
    assert.equal(addDays('2026-03-01', -1), '2026-02-28');
    assert.equal(parseDateKey('2026-02-30'), null);
  });

  it('is deterministic for a date', () => {
    const a = dailyLevel('2026-10-28').arrows.map(encodeArrow).join(' ');
    const b = dailyLevel('2026-10-28').arrows.map(encodeArrow).join(' ');
    assert.equal(a, b);
    assert.notEqual(a, dailyLevel('2026-10-29').arrows.map(encodeArrow).join(' '));
  });

  it('produces valid puzzles with the weekday difficulty', () => {
    // 2026-10-26 is a Monday.
    assert.equal(dailyTier('2026-10-26'), 'easy');
    assert.equal(dailyTier('2026-10-31'), 'expert');
    for (let i = 0; i < 30; i++) {
      const key = addDays('2026-10-01', i);
      const level = dailyLevel(key);
      assert.equal(level.tier, dailyTier(key));
      assert.equal(level.id, `D${key}`);
      assert.deepEqual(validateLevel(level), [], key);
    }
  });
});
