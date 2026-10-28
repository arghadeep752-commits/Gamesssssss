import type { Tier } from '../game/types';

/**
 * Tunable game rules. Everything here is plain data so rules stay
 * deterministic and testable.
 */
export interface GameRules {
  /** Hearts at the start of every attempt. */
  readonly lives: number;
  /**
   * Deliberate rule: tapping a blocked arrow costs a heart. Hearts are the
   * game's only failure condition, so without this rule they would be decorative.
   */
  readonly blockedTapCostsLife: boolean;
  /** Tiers where blocked taps are still counted as mistakes but never cost hearts. */
  readonly forgivingTiers: readonly Tier[];
  /** Path helper ("Scan") uses per attempt. */
  readonly scansPerLevel: number;
  /** Hints a brand-new player starts with. */
  readonly startingHints: number;
  /** Upper bound on stored hints, so rewards cannot grow forever. */
  readonly maxHints: number;
  /** Hints granted the first time a level whose number is a multiple of this is cleared. */
  readonly milestoneEvery: number;
  readonly milestoneHints: number;
}

export const RULES: GameRules = {
  lives: 3,
  blockedTapCostsLife: true,
  forgivingTiers: ['tutorial'],
  scansPerLevel: 3,
  startingHints: 5,
  maxHints: 99,
  milestoneEvery: 5,
  milestoneHints: 1,
};

/**
 * Stars. Penalty = mistakes*mistakeWeight + hints*hintWeight
 *                + floor(extraMoves * extraMoveWeight)
 * where extraMoves = moves beyond the arrow count (only possible through Undo).
 */
export interface StarRules {
  readonly mistakeWeight: number;
  readonly hintWeight: number;
  readonly extraMoveWeight: number;
  /** Highest penalty that still earns 3 stars. */
  readonly threeStarMax: number;
  /** Highest penalty that still earns 2 stars. Anything above earns 1 star. */
  readonly twoStarMax: number;
}

export const STAR_RULES: StarRules = {
  mistakeWeight: 1,
  hintWeight: 1,
  extraMoveWeight: 0.5,
  threeStarMax: 0,
  twoStarMax: 2,
};

/** Daily challenge rewards (hints), claimed once per date. */
export const DAILY_REWARD: Readonly<Record<Tier, number>> = {
  tutorial: 1,
  easy: 1,
  normal: 1,
  hard: 2,
  expert: 3,
};

export const TIER_LABEL: Readonly<Record<Tier, string>> = {
  tutorial: 'Tutorial',
  easy: 'Easy',
  normal: 'Normal',
  hard: 'Hard',
  expert: 'Expert',
};

/** Timing for animations, in milliseconds. */
export const TIMING = {
  exitBase: 250,
  exitPerCell: 14,
  exitMax: 400,
  shake: 200,
  hintPulse: 700,
  pathHelperVisible: 2200,
} as const;
