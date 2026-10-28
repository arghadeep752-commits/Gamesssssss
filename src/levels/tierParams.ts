import type { GeneratorOptions } from '../game/generator';
import type { Tier } from '../game/types';

/**
 * Level-design curve. `t` runs from 0 (first level of the tier) to 1 (last).
 * Used by the offline level builder (scripts/build-levels.ts) and by the daily
 * challenge, so both follow the same difficulty ladder.
 */
export interface DesignTarget {
  readonly options: GeneratorOptions;
  /** Preferred arrow count. */
  readonly arrows: number;
  /** Preferred chain depth (greedy rounds). */
  readonly rounds: number;
  /** Preferred share of arrows that are free at the start (lower is harder). */
  readonly freeShare: number;
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const round = (v: number) => Math.round(v);

export function designTarget(tier: Tier, t: number): DesignTarget {
  const k = Math.min(1, Math.max(0, t));
  switch (tier) {
    case 'tutorial':
      return {
        options: {
          width: round(lerp(4, 5, k)),
          height: round(lerp(5, 7, k)),
          targetArrows: round(lerp(4, 9, k)),
          minLen: 2,
          maxLen: 3,
          turnChance: k < 0.5 ? 0 : 0.15,
          candidates: 2,
          depthWeight: 1,
        },
        arrows: round(lerp(4, 8, k)),
        rounds: round(lerp(2, 3, k)),
        freeShare: lerp(0.6, 0.5, k),
      };
    case 'easy':
      return {
        options: {
          width: round(lerp(5, 6, k)),
          height: round(lerp(7, 8, k)),
          targetArrows: round(lerp(10, 16, k)),
          minLen: 2,
          maxLen: 4,
          turnChance: 0.25,
          candidates: 3,
          depthWeight: 1,
          fillGaps: true,
        },
        arrows: round(lerp(9, 14, k)),
        rounds: round(lerp(3, 4, k)),
        freeShare: lerp(0.5, 0.42, k),
      };
    case 'normal':
      return {
        options: {
          width: round(lerp(6, 8, k)),
          height: round(lerp(8, 10, k)),
          targetArrows: round(lerp(16, 26, k)),
          minLen: 2,
          maxLen: 5,
          turnChance: 0.3,
          hookChance: 0.03,
          candidates: 4,
          depthWeight: 2,
          fillGaps: true,
          maxFailures: 250,
        },
        arrows: round(lerp(14, 22, k)),
        rounds: round(lerp(4, 6, k)),
        freeShare: lerp(0.45, 0.38, k),
      };
    case 'hard':
      return {
        options: {
          width: round(lerp(8, 9, k)),
          height: round(lerp(10, 12, k)),
          targetArrows: round(lerp(26, 34, k)),
          minLen: 2,
          maxLen: 6,
          turnChance: 0.35,
          hookChance: 0.05,
          candidates: 6,
          depthWeight: 2,
          fillGaps: true,
          maxFailures: 300,
        },
        arrows: round(lerp(22, 28, k)),
        rounds: round(lerp(6, 8, k)),
        freeShare: lerp(0.4, 0.34, k),
      };
    case 'expert':
      return {
        options: {
          width: round(lerp(9, 10, k)),
          height: round(lerp(12, 14, k)),
          targetArrows: round(lerp(34, 44, k)),
          minLen: 2,
          maxLen: 7,
          turnChance: 0.4,
          hookChance: 0.08,
          candidates: 8,
          depthWeight: 3,
          fillGaps: true,
          maxFailures: 400,
        },
        arrows: round(lerp(27, 34, k)),
        rounds: round(lerp(8, 11, k)),
        freeShare: lerp(0.36, 0.3, k),
      };
  }
}

export function tierForLevel(levelNumber: number): Tier {
  if (levelNumber <= 10) return 'tutorial';
  if (levelNumber <= 25) return 'easy';
  if (levelNumber <= 50) return 'normal';
  if (levelNumber <= 75) return 'hard';
  return 'expert';
}

/** Position of a level inside its tier, from 0 to 1. */
export function tierProgress(levelNumber: number): number {
  const ranges: Record<Tier, [number, number]> = {
    tutorial: [1, 10],
    easy: [11, 25],
    normal: [26, 50],
    hard: [51, 75],
    expert: [76, 100],
  };
  const [a, b] = ranges[tierForLevel(levelNumber)];
  if (levelNumber > 100) return 1;
  return (levelNumber - a) / (b - a);
}

export interface MetricsLike {
  readonly arrows: number;
  readonly initialFree: number;
  readonly rounds: number;
  readonly fill: number;
}

/** Distance from the design curve; lower is a closer match. */
export function designCost(m: MetricsLike, target: DesignTarget): number {
  const freeShare = m.initialFree / Math.max(1, m.arrows);
  let c = Math.abs(m.arrows - target.arrows) + 2.5 * Math.abs(m.rounds - target.rounds);
  c += 20 * Math.abs(freeShare - target.freeShare);
  if (m.fill < 0.6) c += (0.6 - m.fill) * 30;
  return c;
}
