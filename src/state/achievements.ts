import type { SaveData } from './saveSchema';

/**
 * Achievements are computed from real saved data only, so the numbers shown
 * on the profile can never drift from what the player actually did.
 */
export interface DerivedStats {
  readonly completedLevels: number;
  readonly totalStars: number;
  readonly threeStarLevels: number;
  readonly noHintLevels: number;
  readonly expertCleared: number;
}

export function deriveStats(save: SaveData): DerivedStats {
  let completedLevels = 0;
  let totalStars = 0;
  let threeStarLevels = 0;
  let noHintLevels = 0;
  let expertCleared = 0;
  for (const [key, r] of Object.entries(save.progress.best)) {
    completedLevels++;
    totalStars += r.stars;
    if (r.stars === 3) threeStarLevels++;
    if (r.noHintClear) noHintLevels++;
    if (parseInt(key.slice(1), 10) >= 76) expertCleared++;
  }
  return { completedLevels, totalStars, threeStarLevels, noHintLevels, expertCleared };
}

export interface AchievementDef {
  readonly id: string;
  readonly title: string;
  readonly description: string;
  readonly target: number;
  readonly progress: (save: SaveData, stats: DerivedStats) => number;
}

export const ACHIEVEMENTS: readonly AchievementDef[] = [
  { id: 'first_puzzle', title: 'First Puzzle', description: 'Clear your first level', target: 1, progress: (_, s) => s.completedLevels },
  { id: 'levels_10', title: 'Getting the Flow', description: 'Clear 10 levels', target: 10, progress: (_, s) => s.completedLevels },
  { id: 'levels_25', title: 'Pathfinder', description: 'Clear 25 levels', target: 25, progress: (_, s) => s.completedLevels },
  { id: 'levels_50', title: 'Halfway There', description: 'Clear 50 levels', target: 50, progress: (_, s) => s.completedLevels },
  { id: 'levels_100', title: 'Arrow Master', description: 'Clear all 100 levels', target: 100, progress: (_, s) => s.completedLevels },
  { id: 'stars_25', title: 'Star Collector', description: 'Earn 3 stars on 25 levels', target: 25, progress: (_, s) => s.threeStarLevels },
  { id: 'no_hint_10', title: 'On My Own', description: 'Clear 10 levels without a hint', target: 10, progress: (_, s) => s.noHintLevels },
  { id: 'expert_1', title: 'Into the Deep', description: 'Clear an Expert level', target: 1, progress: (_, s) => s.expertCleared },
  { id: 'daily_1', title: 'Daily Habit', description: 'Complete a Daily Challenge', target: 1, progress: (save) => save.daily.completedCount },
  { id: 'daily_7', title: 'Week of Flow', description: 'Complete 7 Daily Challenges', target: 7, progress: (save) => save.daily.completedCount },
  { id: 'streak_3', title: 'On a Roll', description: 'Reach a 3-day daily streak', target: 3, progress: (save) => save.daily.bestStreak },
];

/** Unlocks any achievement whose target is now met. Returns the new save and what was unlocked. */
export function evaluateAchievements(save: SaveData, now: number): { save: SaveData; unlocked: AchievementDef[] } {
  const stats = deriveStats(save);
  const unlocked: AchievementDef[] = [];
  const next: Record<string, number> = { ...save.achievements };
  for (const a of ACHIEVEMENTS) {
    if (next[a.id]) continue;
    if (a.progress(save, stats) >= a.target) {
      next[a.id] = now;
      unlocked.push(a);
    }
  }
  if (!unlocked.length) return { save, unlocked };
  return { save: { ...save, achievements: next }, unlocked };
}
