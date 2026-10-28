import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { DAILY_REWARD, RULES } from '../src/config/gameConfig';
import { prepareLevel } from '../src/game/board';
import { newSession, tapArrow, type SessionState } from '../src/game/session';
import type { LevelDef } from '../src/game/types';
import { dailyLevel } from '../src/levels/daily';
import { getLevel, LEVEL_COUNT } from '../src/levels/index';
import { ACHIEVEMENTS, deriveStats } from '../src/state/achievements';
import {
  completeDaily,
  completeLevel,
  currentStreak,
  markDailyPlayed,
  setPlayerName,
  setSaveUnfinished,
  setSession,
  spendHint,
} from '../src/state/progress';
import { defaultSave, normalizeSave, parseSaveText, SAVE_VERSION, type SaveData } from '../src/state/saveSchema';

const NOW = 1_800_000_000_000;

/** Plays a level to the end using the solver order, with optional mistakes and hints. */
function play(level: LevelDef, opts: { mistakes?: number; hints?: number } = {}): SessionState {
  const p = prepareLevel(level);
  let s = newSession(p, { ...RULES, blockedTapCostsLife: false });
  for (let i = 0; i < (opts.mistakes ?? 0); i++) s = { ...s, mistakes: s.mistakes + 1 };
  s = { ...s, hintsUsed: opts.hints ?? 0 };
  while (s.status === 'playing') {
    const id = s.removed.findIndex((r, i) => !r && p.blockers[i].every((b) => s.removed[b]));
    s = tapArrow(p, s, id, RULES).state;
  }
  return s;
}

describe('save schema', () => {
  it('starts from safe defaults', () => {
    const d = defaultSave(NOW);
    assert.equal(d.version, SAVE_VERSION);
    assert.equal(d.progress.unlockedUpTo, 1);
    assert.equal(d.economy.hints, RULES.startingHints);
    assert.deepEqual(d.progress.best, {});
  });

  it('round-trips through JSON', () => {
    let save = defaultSave(NOW);
    save = completeLevel(save, getLevel(1), play(getLevel(1)), LEVEL_COUNT, NOW).save;
    const back = parseSaveText(JSON.stringify(save), LEVEL_COUNT, NOW + 5);
    assert.deepEqual(back, save);
  });

  it('recovers from corrupted text', () => {
    assert.equal(parseSaveText('{not json', LEVEL_COUNT, NOW), null);
    assert.equal(parseSaveText('[]', LEVEL_COUNT, NOW), null);
    assert.equal(parseSaveText(null, LEVEL_COUNT, NOW), null);
  });

  it('keeps valid parts and repairs invalid ones', () => {
    const fixed = normalizeSave(
      {
        version: 1,
        profile: { name: '   ' },
        progress: {
          unlockedUpTo: 5000,
          currentLevel: -3,
          best: {
            L002: { stars: 3, moves: 3, mistakes: 0, hints: 0 },
            L003: { stars: 7, moves: 1, mistakes: 0, hints: 0 },
            L999: { stars: 3, moves: 1, mistakes: 0, hints: 0 },
            junk: 1,
          },
        },
        economy: { hints: -4, claimed: ['L005', 'L005', 42, 'x'] },
        settings: { sfx: 'yes', music: true },
        daily: { records: { 'bad-key': {}, '2026-10-01': { completed: true, best: { stars: 2, moves: 9, mistakes: 1, hints: 0 } } } },
      },
      LEVEL_COUNT,
      NOW,
    );
    assert.equal(fixed.profile.name, 'Guest');
    assert.deepEqual(Object.keys(fixed.progress.best), ['L002']);
    assert.equal(fixed.progress.best.L002.noHintClear, true);
    assert.equal(fixed.progress.unlockedUpTo, 3, 'cleared level 2 keeps level 3 open');
    assert.equal(fixed.progress.currentLevel, 3);
    assert.equal(fixed.economy.hints, RULES.startingHints);
    assert.deepEqual(fixed.economy.claimed, ['L005']);
    assert.equal(fixed.settings.sfx, true);
    assert.equal(fixed.settings.music, true);
    assert.deepEqual(Object.keys(fixed.daily.records), ['2026-10-01']);
  });

  it('migrates a pre-versioning save', () => {
    const migrated = normalizeSave({ progress: { unlockedUpTo: 4 }, economy: { hints: 9 } }, LEVEL_COUNT, NOW);
    assert.equal(migrated.version, SAVE_VERSION);
    assert.equal(migrated.progress.unlockedUpTo, 4);
    assert.equal(migrated.economy.hints, 9);
  });

  it('drops unfinished puzzles when the player opts out', () => {
    const session = { levelId: 'L001', levelNumber: 1, dailyKey: null, history: [0], moves: 1, mistakes: 0, hintsUsed: 0, undosUsed: 0, livesLeft: 3, scansLeft: 3 };
    let save = setSession(defaultSave(NOW), session);
    assert.deepEqual(save.session, session);
    save = setSaveUnfinished(save, false);
    assert.equal(save.session, null);
    assert.equal(setSession(save, session).session, null);
  });

  it('sanitises the player name', () => {
    assert.equal(setPlayerName(defaultSave(NOW), '  Arjun   the   Great  ').profile.name, 'Arjun the Great');
    assert.equal(setPlayerName(defaultSave(NOW), '   ').profile.name, 'Guest');
    assert.equal(setPlayerName(defaultSave(NOW), 'x'.repeat(50)).profile.name.length, 20);
  });
});

describe('level progress', () => {
  it('unlocks the next level and records the best result', () => {
    const out = completeLevel(defaultSave(NOW), getLevel(1), play(getLevel(1)), LEVEL_COUNT, NOW);
    assert.equal(out.firstClear, true);
    assert.equal(out.newBest, true);
    assert.equal(out.result.stars, 3);
    assert.equal(out.save.progress.unlockedUpTo, 2);
    assert.equal(out.save.progress.best.L001.stars, 3);
  });

  it('a worse replay never erases the best result', () => {
    let save = completeLevel(defaultSave(NOW), getLevel(2), play(getLevel(2)), LEVEL_COUNT, NOW).save;
    const replay = completeLevel(save, getLevel(2), play(getLevel(2), { mistakes: 4 }), LEVEL_COUNT, NOW);
    assert.equal(replay.newBest, false);
    assert.equal(replay.firstClear, false);
    assert.equal(replay.save.progress.best.L002.stars, 3);
    save = replay.save;
    assert.equal(save.progress.unlockedUpTo, 3);
  });

  it('a better replay replaces the best result', () => {
    const first = completeLevel(defaultSave(NOW), getLevel(2), play(getLevel(2), { mistakes: 3 }), LEVEL_COUNT, NOW);
    assert.equal(first.result.stars, 1);
    const second = completeLevel(first.save, getLevel(2), play(getLevel(2)), LEVEL_COUNT, NOW);
    assert.equal(second.newBest, true);
    assert.equal(second.save.progress.best.L002.stars, 3);
  });

  it('grants the milestone reward only once', () => {
    const level5 = getLevel(5);
    const a = completeLevel(defaultSave(NOW), level5, play(level5), LEVEL_COUNT, NOW);
    assert.equal(a.rewardHints, RULES.milestoneHints);
    assert.equal(a.save.economy.hints, RULES.startingHints + RULES.milestoneHints);
    const b = completeLevel(a.save, level5, play(level5), LEVEL_COUNT, NOW);
    assert.equal(b.rewardHints, 0);
    assert.equal(b.save.economy.hints, a.save.economy.hints);
    const c = completeLevel(defaultSave(NOW), getLevel(4), play(getLevel(4)), LEVEL_COUNT, NOW);
    assert.equal(c.rewardHints, 0);
  });

  it('remembers a hint-free clear even if a later best used a hint', () => {
    const lvl = getLevel(3);
    const a = completeLevel(defaultSave(NOW), lvl, play(lvl, { mistakes: 2 }), LEVEL_COUNT, NOW);
    assert.equal(a.save.progress.best.L003.noHintClear, true);
    const b = completeLevel(a.save, lvl, play(lvl, { hints: 1 }), LEVEL_COUNT, NOW);
    assert.equal(b.newBest, true);
    assert.equal(b.save.progress.best.L003.hints, 1);
    assert.equal(b.save.progress.best.L003.noHintClear, true);
  });

  it('spends hints and never goes below zero', () => {
    let save: SaveData | null = { ...defaultSave(NOW), economy: { hints: 1, claimed: [] } };
    save = spendHint(save);
    assert.equal(save?.economy.hints, 0);
    assert.equal(save?.stats.hintsUsed, 1);
    assert.equal(spendHint(save!), null);
  });

  it('unlocks achievements from real progress', () => {
    let save = defaultSave(NOW);
    for (let n = 1; n <= 10; n++) save = completeLevel(save, getLevel(n), play(getLevel(n)), LEVEL_COUNT, NOW).save;
    assert.ok(save.achievements.first_puzzle);
    assert.ok(save.achievements.levels_10);
    assert.ok(save.achievements.no_hint_10);
    assert.equal(save.achievements.levels_25, undefined);
    const stats = deriveStats(save);
    assert.equal(stats.completedLevels, 10);
    assert.equal(stats.totalStars, 30);
    assert.equal(ACHIEVEMENTS.find((a) => a.id === 'levels_25')!.progress(save, stats), 10);
  });
});

describe('daily progress', () => {
  it('rewards once per date and tracks completion', () => {
    const key = '2026-10-28';
    const level = dailyLevel(key);
    let save = markDailyPlayed(defaultSave(NOW), key);
    assert.equal(save.daily.records[key].played, true);
    assert.equal(save.daily.records[key].completed, false);
    const a = completeDaily(save, key, level, play(level), NOW);
    assert.equal(a.rewardHints, DAILY_REWARD[level.tier]);
    assert.equal(a.save.daily.completedCount, 1);
    assert.equal(a.save.daily.records[key].rewardClaimed, true);
    const b = completeDaily(a.save, key, level, play(level), NOW);
    assert.equal(b.rewardHints, 0);
    assert.equal(b.save.economy.hints, a.save.economy.hints);
    assert.equal(b.save.daily.completedCount, 1);
    save = b.save;
    assert.ok(save.achievements.daily_1);
  });

  it('builds a streak on consecutive days and resets after a gap', () => {
    let save = defaultSave(NOW);
    for (const key of ['2026-10-01', '2026-10-02', '2026-10-03']) {
      save = completeDaily(save, key, dailyLevel(key), play(dailyLevel(key)), NOW).save;
    }
    assert.equal(save.daily.streak, 3);
    assert.equal(save.daily.bestStreak, 3);
    assert.ok(save.achievements.streak_3);
    assert.equal(currentStreak(save, '2026-10-04'), 3, 'still alive the next day');
    assert.equal(currentStreak(save, '2026-10-05'), 0, 'broken after a missed day');
    save = completeDaily(save, '2026-10-06', dailyLevel('2026-10-06'), play(dailyLevel('2026-10-06')), NOW).save;
    assert.equal(save.daily.streak, 1);
    assert.equal(save.daily.bestStreak, 3);
  });
});
