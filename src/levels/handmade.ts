import type { PackedLevel } from '../game/types';

/**
 * Hand-authored opening levels that teach the rules one at a time.
 * Token format is documented in src/game/geometry.ts (decodeArrow).
 *
 * 1: two free arrows - just tap.
 * 2: one arrow blocks another - clear the blocker first.
 * 3: a chain of three, plus a free arrow.
 */
export const HANDMADE_LEVELS: readonly PackedLevel[] = [
  { w: 4, h: 5, a: '13UU 21DD' },
  { w: 4, h: 5, a: '02RR 31DD 14L' },
  { w: 4, h: 5, a: '20R 01RR 33UU 24LL' },
];
