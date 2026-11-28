import type { Level } from './engine';
import { generateLevel, type GenParams } from './generator';
import { hashString, mulberry32 } from './rng';
import { FANCY_SHAPES, type Shape } from './shapes';

/**
 * Endless level curve. Level n always produces the same puzzle on every device,
 * so progress never depends on stored level data.
 */
const SIZES: readonly (readonly [number, number, number])[] = [
  // [last level of the band, columns, rows]
  [1, 3, 3],
  [2, 3, 4],
  [3, 4, 4],
  [5, 4, 5],
  [7, 5, 5],
  [10, 5, 6],
  [14, 6, 6],
  [19, 6, 7],
  [25, 7, 8],
  [33, 8, 9],
  [45, 8, 10],
  [60, 9, 11],
  [80, 10, 12],
  [120, 10, 13],
  [Number.POSITIVE_INFINITY, 11, 14],
];

export const MAX_COLS = 12;
export const MAX_ROWS = 15;

export function levelParams(n: number): GenParams {
  const level = Math.max(1, Math.floor(n));
  const band = SIZES.find((s) => level <= s[0]) ?? SIZES[SIZES.length - 1];
  let w = band[1];
  let h = band[2];
  let shape: Shape = 'rect';
  if (level >= 12 && level % 3 === 0) {
    shape = FANCY_SHAPES[hashString(`shape:${level}`) % FANCY_SHAPES.length];
    w = Math.min(MAX_COLS, w + 1);
    h = Math.min(MAX_ROWS, h + 1);
  }
  const boss = level >= 20 && level % 10 === 0;
  if (boss) {
    w = Math.min(MAX_COLS, w + 1);
    h = Math.min(MAX_ROWS, h + 1);
  }
  const maxLen = level <= 5 ? 3 : level <= 15 ? 4 : level <= 30 ? 5 : level <= 60 ? 6 : 7;
  return {
    w,
    h,
    shape,
    minLen: level <= 3 ? 2 : 3,
    maxLen: maxLen + (boss ? 2 : 0),
    bend: Math.min(0.5, 0.22 + level * 0.004),
    fill: level <= 2 ? 0.7 : 0.96,
    maxRuns: level < 10 ? 3 : level < 30 ? 5 : 7,
  };
}

export function levelSeed(n: number): number {
  return hashString(`arrowflow:level:${n}`);
}

const cache = new Map<string, Level>();

function cached(key: string, make: () => Level): Level {
  let lvl = cache.get(key);
  if (!lvl) {
    lvl = make();
    if (cache.size > 12) cache.delete(cache.keys().next().value as string);
    cache.set(key, lvl);
  }
  return lvl;
}

export function getLevel(n: number): Level {
  return cached(`L${n}`, () => generateLevel(levelParams(n), levelSeed(n)));
}

/** Daily puzzles: harder toward the weekend, with a random outline. */
export function dailyParams(dateKey: string): GenParams {
  const rng = mulberry32(hashString(`arrowflow:dayparams:${dateKey}`));
  const [y, m, d] = dateKey.split('-').map(Number);
  const weekday = new Date(y, m - 1, d).getDay(); // 0 = Sunday
  const hard = weekday === 0 ? 4 : weekday === 6 ? 3 : Math.max(0, weekday - 2); // Mon..Fri 0..3
  const shapes: Shape[] = ['rect', 'rect', ...FANCY_SHAPES];
  const shape = shapes[Math.floor(rng() * shapes.length)];
  const extra = shape === 'rect' ? 0 : 1;
  return {
    w: 7 + Math.min(3, hard) + extra,
    h: 9 + hard + extra,
    shape,
    minLen: 3,
    maxLen: 5 + Math.min(2, hard),
    bend: 0.38 + hard * 0.03,
    fill: 0.96,
    maxRuns: 6,
  };
}

export function getDaily(dateKey: string): Level {
  return cached(`D${dateKey}`, () => generateLevel(dailyParams(dateKey), hashString(`arrowflow:day:${dateKey}`)));
}
