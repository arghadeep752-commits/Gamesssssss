import { isComplete, isFree, prepareLevel, type PreparedLevel } from './board';
import { DIR_VECTORS, inBounds, stepDirection } from './geometry';
import { simulateRemove, solve } from './solver';
import type { LevelDef } from './types';

export const MAX_GRID = 36;

/**
 * Independent, deliberately naive blocking check: slide every cell of the arrow
 * one step at a time and record which other arrows it would touch. Used only to
 * cross-check the corridor-based engine during validation and tests.
 */
export function bruteForceBlockers(level: LevelDef, id: number): number[] {
  const arrow = level.arrows[id];
  const owner = new Map<string, number>();
  for (const a of level.arrows) for (const c of a.cells) owner.set(`${c.x},${c.y}`, a.id);
  const v = DIR_VECTORS[arrow.dir];
  const hit = new Set<number>();
  for (let k = 1; k <= Math.max(level.width, level.height); k++) {
    for (const c of arrow.cells) {
      const x = c.x + v.x * k;
      const y = c.y + v.y * k;
      if (!inBounds(x, y, level.width, level.height)) continue;
      const o = owner.get(`${x},${y}`);
      if (o !== undefined && o !== id) hit.add(o);
    }
  }
  return Array.from(hit).sort((a, b) => a - b);
}

/** Returns a list of problems; an empty list means the level is valid and solvable. */
export function validateLevel(level: LevelDef): string[] {
  const errors: string[] = [];
  const tag = `Level ${level.id}`;
  if (!Number.isInteger(level.width) || !Number.isInteger(level.height)) {
    errors.push(`${tag}: grid size must be integers`);
    return errors;
  }
  if (level.width < 2 || level.height < 2 || level.width > MAX_GRID || level.height > MAX_GRID) {
    errors.push(`${tag}: grid ${level.width}x${level.height} is out of range`);
    return errors;
  }
  if (level.arrows.length === 0) errors.push(`${tag}: has no arrows`);

  const ids = new Set<number>();
  level.arrows.forEach((arrow, index) => {
    if (ids.has(arrow.id)) errors.push(`${tag}: duplicate arrow id ${arrow.id}`);
    ids.add(arrow.id);
    if (arrow.id !== index) errors.push(`${tag}: arrow id ${arrow.id} does not match its index ${index}`);
    if (arrow.cells.length < 2) errors.push(`${tag}: arrow ${arrow.id} is shorter than 2 cells`);
    const seen = new Set<string>();
    arrow.cells.forEach((c, i) => {
      if (!Number.isInteger(c.x) || !Number.isInteger(c.y)) {
        errors.push(`${tag}: arrow ${arrow.id} has a non-integer cell`);
      }
      if (!inBounds(c.x, c.y, level.width, level.height)) {
        errors.push(`${tag}: arrow ${arrow.id} cell (${c.x},${c.y}) is off the board`);
      }
      const key = `${c.x},${c.y}`;
      if (seen.has(key)) errors.push(`${tag}: arrow ${arrow.id} crosses itself at ${key}`);
      seen.add(key);
      if (i > 0 && !stepDirection(arrow.cells[i - 1], c)) {
        errors.push(`${tag}: arrow ${arrow.id} has a gap before (${c.x},${c.y})`);
      }
    });
    if (arrow.cells.length >= 2) {
      const last = stepDirection(arrow.cells[arrow.cells.length - 2], arrow.cells[arrow.cells.length - 1]);
      if (last !== arrow.dir) {
        errors.push(`${tag}: arrow ${arrow.id} head points ${arrow.dir} but its last segment goes ${last}`);
      }
    }
  });
  if (errors.length) return errors;

  let prepared: PreparedLevel;
  try {
    prepared = prepareLevel(level);
  } catch (e) {
    errors.push(e instanceof Error ? e.message : String(e));
    return errors;
  }

  // Blocking detection must agree with the naive simulation.
  for (const arrow of level.arrows) {
    const fast = prepared.blockers[arrow.id].join(',');
    const slow = bruteForceBlockers(level, arrow.id).join(',');
    if (fast !== slow) {
      errors.push(`${tag}: blocking mismatch for arrow ${arrow.id}: engine [${fast}] vs simulation [${slow}]`);
    }
  }

  // Solvability, then replay the solution move by move through the engine rules.
  const result = solve(prepared, level.arrows.map(() => false));
  if (!result.solvable) {
    errors.push(`${tag}: unsolvable, arrows stuck in a cycle: ${result.stuck.join(', ')}`);
    return errors;
  }
  let removed: boolean[] = level.arrows.map(() => false);
  for (const id of result.order) {
    if (!isFree(prepared, removed, id)) {
      errors.push(`${tag}: solution step ${id} is not a legal move`);
      return errors;
    }
    removed = simulateRemove(removed, id);
  }
  if (!isComplete(removed)) errors.push(`${tag}: replaying the solution does not clear the board`);
  return errors;
}
