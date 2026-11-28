import { type Arrow, type Dir, type Level } from './engine';
import { generateLevel, type GenParams } from './generator';
import { LEVEL_PACK } from './levelPack';
import { hashString, mulberry32 } from './rng';
import { SHAPE_BY_ID, SHAPES, shapeSize, type ShapeDef } from './shapes';

/**
 * Level curve. Levels 1..LEVEL_PACK.length ship pre-built (picked as the hardest
 * of several candidates when the pack was made); later levels are generated on
 * the device with the same rules. Level n is the same puzzle on every phone.
 */
export type Tier = 'easy' | 'normal' | 'hard' | 'super';

export const TIER_LABEL: Record<Tier, string> = {
  easy: 'Easy',
  normal: 'Normal',
  hard: 'Hard',
  super: 'Super Hard',
};

export interface LevelInfo {
  readonly level: Level;
  readonly tier: Tier;
  /** Outline id ('rect' for the plain tutorial boards). */
  readonly shape: string;
  readonly shapeName: string;
}

export interface LevelSpec {
  readonly tier: Tier;
  readonly shape: string;
  readonly params: GenParams;
}

export const MAX_LONG = 36;

const TUTORIAL: readonly [number, number][] = [
  [3, 3],
  [4, 4],
  [5, 5],
];

export function levelTier(n: number): Tier {
  if (n <= TUTORIAL.length) return 'easy';
  if (n % 10 === 0) return 'super';
  if (n % 5 === 0) return 'hard';
  return 'normal';
}

export function shapeForLevel(n: number): ShapeDef {
  return SHAPES[(n - TUTORIAL.length - 1) % SHAPES.length];
}

export function levelSpec(n: number): LevelSpec {
  const level = Math.max(1, Math.floor(n));
  const tier = levelTier(level);
  if (level <= TUTORIAL.length) {
    const [w, h] = TUTORIAL[level - 1];
    return {
      tier,
      shape: 'rect',
      params: { w, h, shape: 'rect', minLen: 2, maxLen: 3, bend: 0.3, fill: level === 1 ? 0.75 : 0.95, maxRuns: 3 },
    };
  }
  const shape = shapeForLevel(level);
  // Pictures need resolution to read clearly, so boards start fairly large and grow.
  const base =
    level <= 4
      ? 16
      : level <= 9
        ? 18
        : level <= 20
          ? 20
          : level <= 40
            ? 22
            : level <= 70
              ? 24
              : level <= 110
                ? 26
                : level <= 170
                  ? 28
                  : 30;
  const extra = tier === 'super' ? 6 : tier === 'hard' ? 3 : 0;
  const long = Math.min(MAX_LONG, base + extra);
  const { w, h } = shapeSize(shape, long);
  const lenBoost = tier === 'super' ? 4 : tier === 'hard' ? 2 : 0;
  const runBoost = tier === 'super' ? 2 : tier === 'hard' ? 1 : 0;
  return {
    tier,
    shape: shape.id,
    params: {
      w,
      h,
      shape,
      minLen: 3,
      maxLen: Math.min(16, 6 + Math.floor(level / 30) + lenBoost),
      bend: Math.min(0.58, 0.34 + level * 0.003),
      fill: 0.99,
      maxRuns: Math.min(13, 4 + Math.floor(level / 20) + runBoost),
    },
  };
}

export function levelSeed(n: number): number {
  return hashString(`arrowflow:v3:level:${n}`);
}

/* ------------------------------------------------------------------ */
/* Pack format                                                         */
/* ------------------------------------------------------------------ */
// One level per string: "w,h,shapeId,tier,maskHex,arrows"
// arrows are joined by "."; each is its tail cell (2 base-36 chars) followed by
// runs of (direction letter u/r/d/l, run length in base 36).

const DIR_CHARS = 'urdl';
const TIER_CHARS: Record<Tier, string> = { easy: 'e', normal: 'n', hard: 'h', super: 's' };
const CHAR_TIER: Record<string, Tier> = { e: 'easy', n: 'normal', h: 'hard', s: 'super' };

export function encodeLevel(info: LevelInfo): string {
  const { level } = info;
  let hex = '';
  for (let i = 0; i < level.mask.length; i += 4) {
    let v = 0;
    for (let b = 0; b < 4; b++) if (level.mask[i + b]) v |= 8 >> b;
    hex += v.toString(16);
  }
  const arrows = level.arrows
    .map((a) => {
      let s = a.cells[0].toString(36).padStart(2, '0');
      let k = 1;
      while (k < a.cells.length) {
        const d = stepDir(level.w, a.cells[k - 1], a.cells[k]);
        let len = 1;
        while (k + len < a.cells.length && stepDir(level.w, a.cells[k + len - 1], a.cells[k + len]) === d) len++;
        s += DIR_CHARS[d] + len.toString(36);
        k += len;
      }
      return s;
    })
    .join('.');
  return `${level.w},${level.h},${info.shape},${TIER_CHARS[info.tier]},${hex},${arrows}`;
}

function stepDir(w: number, a: number, b: number): Dir {
  const d = b - a;
  return (d === -w ? 0 : d === 1 ? 1 : d === w ? 2 : 3) as Dir;
}

export function decodeLevel(text: string): LevelInfo {
  const [ws, hs, shape, tierC, hex, body] = text.split(',');
  const w = Number(ws);
  const h = Number(hs);
  const mask = new Uint8Array(w * h);
  for (let i = 0; i < hex.length; i++) {
    const v = parseInt(hex[i], 16);
    for (let b = 0; b < 4; b++) {
      const idx = i * 4 + b;
      if (idx < mask.length) mask[idx] = v & (8 >> b) ? 1 : 0;
    }
  }
  const dx = [-w, 1, w, -1];
  const arrows: Arrow[] = body
    ? body.split('.').map((s, id) => {
        let c = parseInt(s.slice(0, 2), 36);
        const cells = [c];
        let dir: Dir = 0;
        for (let i = 2; i + 1 < s.length; i += 2) {
          dir = DIR_CHARS.indexOf(s[i]) as Dir;
          const len = parseInt(s[i + 1], 36);
          for (let k = 0; k < len; k++) {
            c += dx[dir];
            cells.push(c);
          }
        }
        return { id, cells, dir };
      })
    : [];
  const def = SHAPE_BY_ID.get(shape);
  return { level: { w, h, mask, arrows }, tier: CHAR_TIER[tierC] ?? 'normal', shape, shapeName: def ? def.name : 'Grid' };
}

/* ------------------------------------------------------------------ */
/* Access                                                              */
/* ------------------------------------------------------------------ */

const cache = new Map<string, LevelInfo>();

function cached(key: string, make: () => LevelInfo): LevelInfo {
  let v = cache.get(key);
  if (!v) {
    v = make();
    if (cache.size > 10) cache.delete(cache.keys().next().value as string);
    cache.set(key, v);
  }
  return v;
}

/** Builds level n from its spec (used by the pack builder and after the pack ends). */
export function buildLevel(n: number, tries = 2): LevelInfo {
  const spec = levelSpec(n);
  const level = generateLevel(spec.params, levelSeed(n), tries);
  const def = SHAPE_BY_ID.get(spec.shape);
  return { level, tier: spec.tier, shape: spec.shape, shapeName: def ? def.name : 'Grid' };
}

export function getLevel(n: number): LevelInfo {
  return cached(`L${n}`, () => (n >= 1 && n <= LEVEL_PACK.length ? decodeLevel(LEVEL_PACK[n - 1]) : buildLevel(n)));
}

/** Daily puzzles: big shaped boards, harder toward the weekend. */
export function dailySpec(dateKey: string): LevelSpec {
  const rng = mulberry32(hashString(`arrowflow:v3:dayparams:${dateKey}`));
  const [y, m, d] = dateKey.split('-').map(Number);
  const weekday = new Date(y, m - 1, d).getDay(); // 0 = Sunday
  const hard = weekday === 0 ? 4 : weekday === 6 ? 3 : Math.max(0, weekday - 2); // Mon..Fri 0..3
  const shape = SHAPES[Math.floor(rng() * SHAPES.length)];
  const long = 22 + hard * 2;
  const { w, h } = shapeSize(shape, long);
  return {
    tier: hard >= 3 ? 'super' : hard >= 1 ? 'hard' : 'normal',
    shape: shape.id,
    params: { w, h, shape, minLen: 3, maxLen: 7 + hard, bend: 0.45, fill: 0.99, maxRuns: 6 + hard },
  };
}

export function getDaily(dateKey: string): LevelInfo {
  return cached(`D${dateKey}`, () => {
    const spec = dailySpec(dateKey);
    const level = generateLevel(spec.params, hashString(`arrowflow:v3:day:${dateKey}`), 1);
    const def = SHAPE_BY_ID.get(spec.shape);
    return { level, tier: spec.tier, shape: spec.shape, shapeName: def ? def.name : 'Grid' };
  });
}
