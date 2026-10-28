/**
 * Release check for shipped levels. Run with:  npm run levels:validate
 * Exits non-zero if any level is invalid, duplicated, or out of tier order,
 * and also validates the next 400 daily puzzles.
 */
import { prepareLevel } from '../src/game/board';
import { encodeArrow } from '../src/game/geometry';
import { measure } from '../src/game/solver';
import { validateLevel } from '../src/game/validate';
import { addDays, dailyLevel, localDateKey } from '../src/levels/daily';
import { getLevel, LEVEL_COUNT } from '../src/levels/index';
import { tierForLevel } from '../src/levels/tierParams';

const problems: string[] = [];
const seen = new Map<string, number>();

if (LEVEL_COUNT < 100) problems.push(`Only ${LEVEL_COUNT} levels shipped; at least 100 are required`);

for (let n = 1; n <= LEVEL_COUNT; n++) {
  const level = getLevel(n);
  if (level.tier !== tierForLevel(n)) problems.push(`Level ${n}: tier ${level.tier} should be ${tierForLevel(n)}`);
  for (const e of validateLevel(level)) problems.push(e);
  const key = `${level.width}x${level.height}:${level.arrows.map(encodeArrow).join(' ')}`;
  const dup = seen.get(key);
  if (dup) problems.push(`Level ${n} duplicates level ${dup}`);
  seen.set(key, n);
}

// Average difficulty must rise from tier to tier.
const tiers = ['tutorial', 'easy', 'normal', 'hard', 'expert'] as const;
let prevArrows = 0;
let prevDepth = 0;
for (const tier of tiers) {
  const nums = Array.from({ length: LEVEL_COUNT }, (_, i) => i + 1).filter((n) => tierForLevel(n) === tier);
  const ms = nums.map((n) => measure(prepareLevel(getLevel(n))));
  const arrows = ms.reduce((s, m) => s + m.arrows, 0) / ms.length;
  const depth = ms.reduce((s, m) => s + m.rounds, 0) / ms.length;
  console.log(`${tier.padEnd(9)} levels ${nums[0]}-${nums[nums.length - 1]}  avg arrows ${arrows.toFixed(1)}  avg depth ${depth.toFixed(1)}`);
  if (arrows <= prevArrows || depth <= prevDepth) problems.push(`Tier ${tier} is not harder than the tier before it`);
  prevArrows = arrows;
  prevDepth = depth;
}

const start = localDateKey(new Date(2026, 0, 1));
for (let i = 0; i < 400; i++) {
  const key = addDays(start, i);
  for (const e of validateLevel(dailyLevel(key))) problems.push(`Daily ${key}: ${e}`);
}

if (problems.length) {
  console.error(`\n${problems.length} problem(s):\n${problems.join('\n')}`);
  process.exit(1);
}
console.log(`\nAll ${LEVEL_COUNT} levels and 400 daily puzzles are valid, distinct and solvable.`);
