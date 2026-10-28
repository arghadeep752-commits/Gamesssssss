import { RULES } from '../config/gameConfig';
import type { LevelResult } from '../game/scoring';
import type { SessionSnapshot } from '../game/session';

/**
 * Versioned save format. Everything the player owns lives in one small JSON
 * object. normalizeSave() never throws: it keeps every valid part of whatever
 * it is given and falls back to safe defaults for the rest, so a damaged or
 * hand-edited save can never crash the game.
 */
export const SAVE_VERSION = 1;
export const MAX_DAILY_RECORDS = 60;
export const MAX_NAME_LENGTH = 20;

export interface BestResult extends LevelResult {
  /** True if the level has ever been cleared without using a hint. */
  readonly noHintClear: boolean;
}

export interface DailyRecord {
  readonly played: boolean;
  readonly completed: boolean;
  readonly best: LevelResult | null;
  readonly rewardClaimed: boolean;
}

export interface Settings {
  readonly sfx: boolean;
  readonly music: boolean;
  readonly vibration: boolean;
  readonly reducedEffects: boolean;
}

export interface PrivacyPrefs {
  /** Keep an unfinished puzzle on the device so it can be resumed. */
  readonly saveUnfinished: boolean;
}

export interface SessionSave extends SessionSnapshot {
  /** Level number, or 0 for a daily puzzle. */
  readonly levelNumber: number;
  /** For daily puzzles: the date key. */
  readonly dailyKey: string | null;
}

export interface SaveData {
  readonly version: number;
  readonly createdAt: number;
  readonly profile: { readonly name: string };
  readonly progress: {
    /** Highest level number the player may open. */
    readonly unlockedUpTo: number;
    /** Level the Continue button opens. */
    readonly currentLevel: number;
    readonly best: Readonly<Record<string, BestResult>>;
  };
  readonly economy: {
    readonly hints: number;
    /** Reward keys already granted, e.g. "L005". Prevents duplicate rewards. */
    readonly claimed: readonly string[];
  };
  readonly daily: {
    readonly records: Readonly<Record<string, DailyRecord>>;
    readonly completedCount: number;
    readonly streak: number;
    readonly bestStreak: number;
    readonly lastCompleted: string | null;
  };
  readonly stats: {
    readonly hintsUsed: number;
    readonly clears: number;
    readonly arrowsCleared: number;
    readonly mistakes: number;
  };
  /** Achievement id -> unlock time (ms since epoch). */
  readonly achievements: Readonly<Record<string, number>>;
  readonly settings: Settings;
  readonly privacy: PrivacyPrefs;
  readonly onboardingDone: boolean;
  readonly session: SessionSave | null;
}

export const DEFAULT_SETTINGS: Settings = { sfx: true, music: false, vibration: true, reducedEffects: false };

export function defaultSave(now: number): SaveData {
  return {
    version: SAVE_VERSION,
    createdAt: now,
    profile: { name: 'Guest' },
    progress: { unlockedUpTo: 1, currentLevel: 1, best: {} },
    economy: { hints: RULES.startingHints, claimed: [] },
    daily: { records: {}, completedCount: 0, streak: 0, bestStreak: 0, lastCompleted: null },
    stats: { hintsUsed: 0, clears: 0, arrowsCleared: 0, mistakes: 0 },
    achievements: {},
    settings: DEFAULT_SETTINGS,
    privacy: { saveUnfinished: true },
    onboardingDone: false,
    session: null,
  };
}

// ---------------------------------------------------------------- helpers

type Obj = Record<string, unknown>;
const isObj = (v: unknown): v is Obj => typeof v === 'object' && v !== null && !Array.isArray(v);
const int = (v: unknown, min: number, max: number, fallback: number): number =>
  typeof v === 'number' && Number.isInteger(v) && v >= min && v <= max ? v : fallback;
const bool = (v: unknown, fallback: boolean): boolean => (typeof v === 'boolean' ? v : fallback);
const DATE_KEY = /^\d{4}-\d{2}-\d{2}$/;
const LEVEL_KEY = /^L\d{3}$/;

function levelResult(v: unknown): LevelResult | null {
  if (!isObj(v)) return null;
  const stars = v.stars;
  if (stars !== 1 && stars !== 2 && stars !== 3) return null;
  const moves = int(v.moves, 0, 1e6, -1);
  const mistakes = int(v.mistakes, 0, 1e6, -1);
  const hints = int(v.hints, 0, 1e6, -1);
  if (moves < 0 || mistakes < 0 || hints < 0) return null;
  return { stars, moves, mistakes, hints };
}

function sessionSave(v: unknown, levelCount: number): SessionSave | null {
  if (!isObj(v)) return null;
  const levelNumber = int(v.levelNumber, 0, levelCount, -1);
  if (levelNumber < 0 || typeof v.levelId !== 'string') return null;
  const dailyKey = typeof v.dailyKey === 'string' && DATE_KEY.test(v.dailyKey) ? v.dailyKey : null;
  if (levelNumber === 0 && !dailyKey) return null;
  if (!Array.isArray(v.history) || !v.history.every((x) => Number.isInteger(x))) return null;
  // Remaining field checks happen in restoreSession(), which replays every move.
  return {
    levelId: v.levelId,
    levelNumber,
    dailyKey,
    history: v.history as number[],
    moves: int(v.moves, 0, 1e6, 0),
    mistakes: int(v.mistakes, 0, 1e6, 0),
    hintsUsed: int(v.hintsUsed, 0, 1e6, 0),
    undosUsed: int(v.undosUsed, 0, 1e6, 0),
    livesLeft: int(v.livesLeft, 0, RULES.lives, 0),
    scansLeft: int(v.scansLeft, 0, RULES.scansPerLevel, 0),
  };
}

/**
 * Upgrades older save shapes step by step. Version 1 is the first shipped
 * format; add a step here (e.g. 1 -> 2) whenever the shape changes.
 */
const MIGRATIONS: Record<number, (old: Obj) => Obj> = {
  // 0: saves written before versioning existed carried no version field.
  0: (old) => ({ ...old, version: 1 }),
};

export function migrate(input: Obj): Obj {
  let data = input;
  let version = typeof data.version === 'number' ? data.version : 0;
  while (version < SAVE_VERSION && MIGRATIONS[version]) {
    data = MIGRATIONS[version](data);
    version = typeof data.version === 'number' ? data.version : version + 1;
  }
  return data;
}

export function normalizeSave(input: unknown, levelCount: number, now: number): SaveData {
  const d = defaultSave(now);
  if (!isObj(input)) return d;
  const raw = migrate(input);

  const profile = isObj(raw.profile) ? raw.profile : {};
  const name =
    typeof profile.name === 'string' && profile.name.trim().length
      ? profile.name.trim().slice(0, MAX_NAME_LENGTH)
      : d.profile.name;

  const progress = isObj(raw.progress) ? raw.progress : {};
  const best: Record<string, BestResult> = {};
  if (isObj(progress.best)) {
    for (const [key, value] of Object.entries(progress.best)) {
      if (!LEVEL_KEY.test(key)) continue;
      const n = parseInt(key.slice(1), 10);
      if (n < 1 || n > levelCount) continue;
      const r = levelResult(value);
      if (r) best[key] = { ...r, noHintClear: bool(isObj(value) ? value.noHintClear : false, r.hints === 0) };
    }
  }
  // Never lock a level the player has already cleared.
  let highestCleared = 0;
  for (const key of Object.keys(best)) highestCleared = Math.max(highestCleared, parseInt(key.slice(1), 10));
  const unlockedUpTo = Math.min(
    levelCount,
    Math.max(int(progress.unlockedUpTo, 1, levelCount, 1), highestCleared + 1, 1),
  );
  const currentLevel = Math.min(unlockedUpTo, int(progress.currentLevel, 1, levelCount, unlockedUpTo));

  const economy = isObj(raw.economy) ? raw.economy : {};
  const claimed = Array.isArray(economy.claimed)
    ? Array.from(new Set(economy.claimed.filter((k): k is string => typeof k === 'string' && LEVEL_KEY.test(k))))
    : [];

  const daily = isObj(raw.daily) ? raw.daily : {};
  const records: Record<string, DailyRecord> = {};
  if (isObj(daily.records)) {
    const keys = Object.keys(daily.records).filter((k) => DATE_KEY.test(k)).sort().slice(-MAX_DAILY_RECORDS);
    for (const k of keys) {
      const rec = (daily.records as Obj)[k];
      if (!isObj(rec)) continue;
      const completed = bool(rec.completed, false);
      records[k] = {
        played: bool(rec.played, completed),
        completed,
        best: completed ? levelResult(rec.best) : null,
        rewardClaimed: bool(rec.rewardClaimed, false),
      };
    }
  }
  const lastCompleted = typeof daily.lastCompleted === 'string' && DATE_KEY.test(daily.lastCompleted) ? daily.lastCompleted : null;
  const streak = int(daily.streak, 0, 100000, 0);

  const stats = isObj(raw.stats) ? raw.stats : {};
  const achievements: Record<string, number> = {};
  if (isObj(raw.achievements)) {
    for (const [k, v] of Object.entries(raw.achievements)) {
      if (typeof v === 'number' && Number.isFinite(v) && v > 0) achievements[k] = v;
    }
  }
  const settings = isObj(raw.settings) ? raw.settings : {};
  const privacy = isObj(raw.privacy) ? raw.privacy : {};

  return {
    version: SAVE_VERSION,
    createdAt: typeof raw.createdAt === 'number' && raw.createdAt > 0 ? raw.createdAt : now,
    profile: { name },
    progress: { unlockedUpTo, currentLevel, best },
    economy: { hints: int(economy.hints, 0, RULES.maxHints, d.economy.hints), claimed },
    daily: {
      records,
      completedCount: int(daily.completedCount, 0, 100000, 0),
      streak,
      bestStreak: Math.max(streak, int(daily.bestStreak, 0, 100000, 0)),
      lastCompleted,
    },
    stats: {
      hintsUsed: int(stats.hintsUsed, 0, 1e9, 0),
      clears: int(stats.clears, 0, 1e9, 0),
      arrowsCleared: int(stats.arrowsCleared, 0, 1e9, 0),
      mistakes: int(stats.mistakes, 0, 1e9, 0),
    },
    achievements,
    settings: {
      sfx: bool(settings.sfx, d.settings.sfx),
      music: bool(settings.music, d.settings.music),
      vibration: bool(settings.vibration, d.settings.vibration),
      reducedEffects: bool(settings.reducedEffects, d.settings.reducedEffects),
    },
    privacy: { saveUnfinished: bool(privacy.saveUnfinished, true) },
    onboardingDone: bool(raw.onboardingDone, false),
    session: bool(privacy.saveUnfinished, true) ? sessionSave(raw.session, levelCount) : null,
  };
}

/** Parses stored JSON. Returns null when the text is not usable at all. */
export function parseSaveText(text: string | null, levelCount: number, now: number): SaveData | null {
  if (!text) return null;
  try {
    const parsed: unknown = JSON.parse(text);
    if (!isObj(parsed)) return null;
    return normalizeSave(parsed, levelCount, now);
  } catch {
    return null;
  }
}
