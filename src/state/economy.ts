import type { Tier } from '../game/levels';
import { dateKey, parseKey } from './dates';

/** Coins, hints and rewards. All rewards are earned by playing; nothing is sold for money. */
export const START_COINS = 100;
export const START_HINTS = 3;
export const HINT_COST = 60;
export const HINT_PACK = { hints: 3, cost: 150 };
export const REVIVE_COST = 80;
export const CHEST_EVERY = 5;
export const CHEST_COINS = 60;
export const CHEST_HINTS = 1;
export const DAILY_COINS = 50;
export const DAILY_HINTS = 1;
export const LOGIN_REWARDS: readonly number[] = [20, 30, 40, 50, 75, 100, 150];
export const LOGIN_DAY7_HINTS = 2;

const TIER_COINS: Record<Tier, number> = { easy: 10, normal: 15, hard: 25, super: 40 };

export function starsFor(heartsLeft: number, revived: boolean): number {
  if (revived) return 1;
  return Math.max(1, Math.min(3, heartsLeft));
}

export function levelCoins(tier: Tier, stars: number): number {
  return TIER_COINS[tier] + stars * 5;
}

/** Whether today's login reward can be claimed, and which day of the 7-day streak it is. */
export function loginReward(last: string, day: number, today: string): { available: boolean; day: number } {
  if (last === today) return { available: false, day };
  const t = parseKey(today);
  const yesterday = dateKey(new Date(t.getFullYear(), t.getMonth(), t.getDate() - 1));
  const next = last === yesterday ? (day % LOGIN_REWARDS.length) + 1 : 1;
  return { available: true, day: next };
}

export interface Skin {
  readonly id: string;
  readonly name: string;
  readonly price: number;
  /** Arrow colour on the light and dark theme. */
  readonly light: string;
  readonly dark: string;
}

export const SKINS: readonly Skin[] = [
  { id: 'classic', name: 'Classic', price: 0, light: '#1B2233', dark: '#E9ECF3' },
  { id: 'ocean', name: 'Ocean', price: 300, light: '#1E5BB8', dark: '#74A9FF' },
  { id: 'forest', name: 'Forest', price: 400, light: '#1F7A4D', dark: '#5CD69A' },
  { id: 'sunset', name: 'Sunset', price: 500, light: '#C2410C', dark: '#FF9A5C' },
  { id: 'grape', name: 'Grape', price: 650, light: '#6D28D9', dark: '#B794FF' },
  { id: 'rose', name: 'Rose', price: 800, light: '#BE185D', dark: '#FF7EB6' },
  { id: 'lagoon', name: 'Lagoon', price: 1000, light: '#0F766E', dark: '#4FD1C5' },
  { id: 'gold', name: 'Gold', price: 1500, light: '#A16207', dark: '#F5C542' },
];

export function skinById(id: string): Skin {
  return SKINS.find((s) => s.id === id) ?? SKINS[0];
}
