import { unpackLevel } from '../game/geometry';
import type { LevelDef } from '../game/types';
import { PACKED_LEVELS } from './data/packedLevels';
import { tierForLevel } from './tierParams';

export const LEVEL_COUNT = PACKED_LEVELS.length;

export function levelId(levelNumber: number): string {
  return `L${String(levelNumber).padStart(3, '0')}`;
}

const cache = new Map<number, LevelDef>();

/** Decodes a level on first use and keeps it; decoding is a few microseconds. */
export function getLevel(levelNumber: number): LevelDef {
  if (!Number.isInteger(levelNumber) || levelNumber < 1 || levelNumber > LEVEL_COUNT) {
    throw new Error(`No level ${levelNumber}`);
  }
  let level = cache.get(levelNumber);
  if (!level) {
    level = unpackLevel(PACKED_LEVELS[levelNumber - 1], {
      id: levelId(levelNumber),
      number: levelNumber,
      tier: tierForLevel(levelNumber),
    });
    cache.set(levelNumber, level);
  }
  return level;
}

export function levelNumberFromId(id: string): number | null {
  const m = /^L(\d{3})$/.exec(id);
  if (!m) return null;
  const n = parseInt(m[1], 10);
  return n >= 1 && n <= LEVEL_COUNT ? n : null;
}
