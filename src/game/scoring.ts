import type { StarRules } from '../config/gameConfig';

export interface LevelResult {
  readonly stars: 1 | 2 | 3;
  readonly moves: number;
  readonly mistakes: number;
  readonly hints: number;
}

export interface ResultInput {
  readonly arrowCount: number;
  readonly moves: number;
  readonly mistakes: number;
  readonly hints: number;
}

export function penaltyFor(input: ResultInput, rules: StarRules): number {
  const extraMoves = Math.max(0, input.moves - input.arrowCount);
  return (
    input.mistakes * rules.mistakeWeight +
    input.hints * rules.hintWeight +
    Math.floor(extraMoves * rules.extraMoveWeight)
  );
}

export function starsFor(input: ResultInput, rules: StarRules): 1 | 2 | 3 {
  const p = penaltyFor(input, rules);
  if (p <= rules.threeStarMax) return 3;
  if (p <= rules.twoStarMax) return 2;
  return 1;
}

export function makeResult(input: ResultInput, rules: StarRules): LevelResult {
  return { stars: starsFor(input, rules), moves: input.moves, mistakes: input.mistakes, hints: input.hints };
}

/**
 * Strict "better than" ordering: more stars, then fewer mistakes, then fewer
 * hints, then fewer moves. Equal results are not better, so replaying a level
 * never overwrites an equal best.
 */
export function isBetter(candidate: LevelResult, previous: LevelResult | undefined): boolean {
  if (!previous) return true;
  if (candidate.stars !== previous.stars) return candidate.stars > previous.stars;
  if (candidate.mistakes !== previous.mistakes) return candidate.mistakes < previous.mistakes;
  if (candidate.hints !== previous.hints) return candidate.hints < previous.hints;
  return candidate.moves < previous.moves;
}
