import { prepareLevel } from '../game/board';
import { generateLayout } from '../game/generator';
import { unpackLevel } from '../game/geometry';
import { createRng, hashString } from '../game/rng';
import { measure } from '../game/solver';
import type { LevelDef, Tier } from '../game/types';
import { validateLevel } from '../game/validate';
import { PACKED_LEVELS } from './data/packedLevels';
import { designCost, designTarget, tierForLevel } from './tierParams';

/**
 * Daily challenge. The puzzle is a pure function of the local calendar date,
 * so it is the same every time it is opened that day on this device and time
 * zone, and it works fully offline.
 */

const pad = (n: number) => String(n).padStart(2, '0');

/** "YYYY-MM-DD" in the device's local time zone. */
export function localDateKey(date: Date): string {
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

export function parseDateKey(key: string): Date | null {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(key);
  if (!m) return null;
  const d = new Date(Number(m[1]), Number(m[2]) - 1, Number(m[3]));
  return localDateKey(d) === key ? d : null;
}

export function addDays(key: string, days: number): string {
  const d = parseDateKey(key);
  if (!d) throw new Error(`Bad date key ${key}`);
  // Construct by components so daylight-saving shifts cannot skip a day.
  return localDateKey(new Date(d.getFullYear(), d.getMonth(), d.getDate() + days));
}

/** Monday eases in, the weekend is the toughest. */
const WEEKDAY_TIER: readonly Tier[] = ['expert', 'easy', 'normal', 'normal', 'hard', 'hard', 'expert'];

export function dailyTier(key: string): Tier {
  const d = parseDateKey(key);
  return d ? WEEKDAY_TIER[d.getDay()] : 'normal';
}

const CANDIDATES = 6;
const cache = new Map<string, LevelDef>();

export function dailyLevel(key: string): LevelDef {
  const cached = cache.get(key);
  if (cached) return cached;
  const tier = dailyTier(key);
  const target = designTarget(tier, 0.5);
  const base = hashString(`arrow-flow:daily:${key}`);
  let best: LevelDef | null = null;
  let bestCost = Infinity;
  for (let k = 0; k < CANDIDATES; k++) {
    const rng = createRng((base + Math.imul(k, 0x9e3779b1)) >>> 0);
    const arrows = generateLayout(target.options, rng);
    const level: LevelDef = {
      id: `D${key}`,
      number: 0,
      tier,
      width: target.options.width,
      height: target.options.height,
      arrows,
    };
    if (validateLevel(level).length) continue;
    const c = designCost(measure(prepareLevel(level)), target);
    if (c < bestCost) {
      bestCost = c;
      best = level;
    }
  }
  if (!best) {
    // Practically unreachable (layouts are solvable by construction), but never
    // ship an invalid puzzle: fall back to a validated level of the same tier.
    const pool = PACKED_LEVELS.map((_, i) => i + 1).filter((n) => tierForLevel(n) === tier);
    const n = pool[base % pool.length];
    const lvl = unpackLevel(PACKED_LEVELS[n - 1], { id: `D${key}`, number: 0, tier });
    best = lvl;
  }
  cache.set(key, best);
  return best;
}
