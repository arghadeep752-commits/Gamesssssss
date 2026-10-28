import { DAILY_REWARD, RULES, STAR_RULES } from '../config/gameConfig';
import { isBetter, makeResult, type LevelResult } from '../game/scoring';
import type { SessionState } from '../game/session';
import type { LevelDef } from '../game/types';
import { addDays } from '../levels/daily';
import { evaluateAchievements, type AchievementDef } from './achievements';
import { MAX_DAILY_RECORDS, MAX_NAME_LENGTH, type BestResult, type DailyRecord, type SaveData, type SessionSave, type Settings } from './saveSchema';

/**
 * Pure save transitions. Each takes the current save and returns a new one;
 * persistence happens in the store. Rewards are keyed so they can be granted
 * at most once, however often a completion is reported.
 */

export interface CompletionOutcome {
  readonly save: SaveData;
  readonly result: LevelResult;
  readonly firstClear: boolean;
  readonly newBest: boolean;
  readonly rewardHints: number;
  readonly unlocked: readonly AchievementDef[];
}

const clampHints = (n: number) => Math.max(0, Math.min(RULES.maxHints, n));

export function completeLevel(
  save: SaveData,
  level: LevelDef,
  session: SessionState,
  levelCount: number,
  now: number,
): CompletionOutcome {
  const result = makeResult(
    { arrowCount: level.arrows.length, moves: session.moves, mistakes: session.mistakes, hints: session.hintsUsed },
    STAR_RULES,
  );
  const prev = save.progress.best[level.id];
  const firstClear = !prev;
  const newBest = isBetter(result, prev);
  const noHintClear = (prev?.noHintClear ?? false) || session.hintsUsed === 0;
  const best: BestResult = newBest ? { ...result, noHintClear } : { ...prev!, noHintClear };

  let rewardHints = 0;
  let claimed = save.economy.claimed;
  if (level.number % RULES.milestoneEvery === 0 && !claimed.includes(level.id)) {
    rewardHints = RULES.milestoneHints;
    claimed = [...claimed, level.id];
  }
  const nextLevel = Math.min(levelCount, level.number + 1);
  let next: SaveData = {
    ...save,
    progress: {
      unlockedUpTo: Math.max(save.progress.unlockedUpTo, nextLevel),
      currentLevel: Math.max(save.progress.currentLevel, nextLevel),
      best: { ...save.progress.best, [level.id]: best },
    },
    economy: { hints: clampHints(save.economy.hints + rewardHints), claimed },
    stats: {
      ...save.stats,
      clears: save.stats.clears + 1,
      arrowsCleared: save.stats.arrowsCleared + level.arrows.length,
      mistakes: save.stats.mistakes + session.mistakes,
    },
    onboardingDone: true,
    session: null,
  };
  const ev = evaluateAchievements(next, now);
  next = ev.save;
  return { save: next, result, firstClear, newBest, rewardHints, unlocked: ev.unlocked };
}

function trimRecords(records: Record<string, DailyRecord>): Record<string, DailyRecord> {
  const keys = Object.keys(records).sort();
  if (keys.length <= MAX_DAILY_RECORDS) return records;
  const out: Record<string, DailyRecord> = {};
  for (const k of keys.slice(-MAX_DAILY_RECORDS)) out[k] = records[k];
  return out;
}

export function markDailyPlayed(save: SaveData, key: string): SaveData {
  const rec = save.daily.records[key];
  if (rec?.played) return save;
  const updated: DailyRecord = rec
    ? { ...rec, played: true }
    : { played: true, completed: false, best: null, rewardClaimed: false };
  return { ...save, daily: { ...save.daily, records: trimRecords({ ...save.daily.records, [key]: updated }) } };
}

export function completeDaily(
  save: SaveData,
  key: string,
  level: LevelDef,
  session: SessionState,
  now: number,
): CompletionOutcome {
  const result = makeResult(
    { arrowCount: level.arrows.length, moves: session.moves, mistakes: session.mistakes, hints: session.hintsUsed },
    STAR_RULES,
  );
  const prev = save.daily.records[key];
  const firstClear = !prev?.completed;
  const newBest = isBetter(result, prev?.best ?? undefined);
  const rewardHints = prev?.rewardClaimed ? 0 : DAILY_REWARD[level.tier];
  const record: DailyRecord = {
    played: true,
    completed: true,
    best: newBest ? result : (prev?.best ?? result),
    rewardClaimed: true,
  };
  let { streak, bestStreak, lastCompleted, completedCount } = save.daily;
  if (firstClear) {
    completedCount += 1;
    if (lastCompleted && addDays(key, -1) === lastCompleted) {
      streak += 1;
    } else if (!lastCompleted || lastCompleted < key) {
      // A gap of more than one day (or the very first daily) starts a new streak.
      streak = 1;
    }
    if (!lastCompleted || key > lastCompleted) lastCompleted = key;
    bestStreak = Math.max(bestStreak, streak);
  }
  let next: SaveData = {
    ...save,
    economy: { ...save.economy, hints: clampHints(save.economy.hints + rewardHints) },
    daily: {
      records: trimRecords({ ...save.daily.records, [key]: record }),
      completedCount,
      streak,
      bestStreak,
      lastCompleted,
    },
    stats: {
      ...save.stats,
      clears: save.stats.clears + 1,
      arrowsCleared: save.stats.arrowsCleared + level.arrows.length,
      mistakes: save.stats.mistakes + session.mistakes,
    },
    session: null,
  };
  const ev = evaluateAchievements(next, now);
  next = ev.save;
  return { save: next, result, firstClear, newBest, rewardHints, unlocked: ev.unlocked };
}

/** Streak shown to the player: it only counts while today or yesterday was completed. */
export function currentStreak(save: SaveData, todayKey: string): number {
  const last = save.daily.lastCompleted;
  if (!last) return 0;
  if (last === todayKey || last === addDays(todayKey, -1)) return save.daily.streak;
  return 0;
}

export function spendHint(save: SaveData): SaveData | null {
  if (save.economy.hints <= 0) return null;
  return {
    ...save,
    economy: { ...save.economy, hints: save.economy.hints - 1 },
    stats: { ...save.stats, hintsUsed: save.stats.hintsUsed + 1 },
  };
}

export function setSession(save: SaveData, session: SessionSave | null): SaveData {
  if (session && !save.privacy.saveUnfinished) return save.session ? { ...save, session: null } : save;
  return { ...save, session };
}

export function setCurrentLevel(save: SaveData, levelNumber: number): SaveData {
  if (levelNumber < 1 || levelNumber > save.progress.unlockedUpTo) return save;
  return { ...save, progress: { ...save.progress, currentLevel: levelNumber } };
}

export function updateSettings(save: SaveData, patch: Partial<Settings>): SaveData {
  return { ...save, settings: { ...save.settings, ...patch } };
}

export function setSaveUnfinished(save: SaveData, value: boolean): SaveData {
  return { ...save, privacy: { saveUnfinished: value }, session: value ? save.session : null };
}

export function setPlayerName(save: SaveData, name: string): SaveData {
  const clean = name.replace(/\s+/g, ' ').trim().slice(0, MAX_NAME_LENGTH);
  return { ...save, profile: { name: clean.length ? clean : 'Guest' } };
}

export function completeOnboarding(save: SaveData): SaveData {
  return save.onboardingDone ? save : { ...save, onboardingDone: true };
}
