import { cellIndex, corridorIndices, inBounds } from './geometry';
import type { LevelDef } from './types';

/**
 * Precomputed, immutable lookup data for one level. Built once when a level is
 * loaded; every tap, hint and solver step afterwards is a cheap array lookup.
 */
export interface PreparedLevel {
  readonly level: LevelDef;
  /** Cell index -> arrow id, or -1 for an empty cell. */
  readonly occupancy: Int16Array;
  /** For each arrow, the cell indices of its exit corridor. */
  readonly corridors: readonly (readonly number[])[];
  /** For each arrow, the ids of arrows sitting in its corridor in the start layout. */
  readonly blockers: readonly (readonly number[])[];
  /** For each arrow, the ids of arrows whose corridor it sits in (the reverse relation). */
  readonly dependents: readonly (readonly number[])[];
}

/** removed[id] === true once an arrow has left the board. */
export type RemovedFlags = readonly boolean[];

export function prepareLevel(level: LevelDef): PreparedLevel {
  const { width, height, arrows } = level;
  const occupancy = new Int16Array(width * height).fill(-1);
  for (const arrow of arrows) {
    for (const c of arrow.cells) {
      if (!inBounds(c.x, c.y, width, height)) {
        throw new Error(`Level ${level.id}: arrow ${arrow.id} leaves the board at (${c.x},${c.y})`);
      }
      const idx = cellIndex(c.x, c.y, width);
      if (occupancy[idx] !== -1) {
        throw new Error(
          `Level ${level.id}: arrows ${occupancy[idx]} and ${arrow.id} overlap at (${c.x},${c.y})`,
        );
      }
      occupancy[idx] = arrow.id;
    }
  }

  const corridors: number[][] = [];
  const blockers: number[][] = [];
  const dependents: number[][] = arrows.map(() => []);
  for (const arrow of arrows) {
    const corridor = corridorIndices(arrow, width, height);
    corridors.push(corridor);
    const set = new Set<number>();
    for (const idx of corridor) {
      const other = occupancy[idx];
      if (other !== -1 && other !== arrow.id) set.add(other);
    }
    const list = Array.from(set).sort((a, b) => a - b);
    blockers.push(list);
    for (const b of list) dependents[b].push(arrow.id);
  }
  return { level, occupancy, corridors, blockers, dependents };
}

export function initialRemoved(prepared: PreparedLevel): boolean[] {
  return prepared.level.arrows.map(() => false);
}

/** Active arrows currently standing in this arrow's corridor. */
export function activeBlockers(prepared: PreparedLevel, removed: RemovedFlags, id: number): number[] {
  const out: number[] = [];
  for (const b of prepared.blockers[id]) if (!removed[b]) out.push(b);
  return out;
}

export function isFree(prepared: PreparedLevel, removed: RemovedFlags, id: number): boolean {
  if (removed[id]) return false;
  for (const b of prepared.blockers[id]) if (!removed[b]) return false;
  return true;
}

/** All active arrows that can leave right now, in ascending id order. */
export function freeArrows(prepared: PreparedLevel, removed: RemovedFlags): number[] {
  const out: number[] = [];
  for (let id = 0; id < prepared.level.arrows.length; id++) {
    if (isFree(prepared, removed, id)) out.push(id);
  }
  return out;
}

export function activeCount(removed: RemovedFlags): number {
  let n = 0;
  for (const r of removed) if (!r) n++;
  return n;
}

export function isComplete(removed: RemovedFlags): boolean {
  return removed.length > 0 && removed.every(Boolean);
}

export interface CorridorInspection {
  /** Corridor cells, in order, as {x, y}. */
  readonly cells: readonly { x: number; y: number; blocked: boolean }[];
  /** Active arrows standing in the corridor. */
  readonly blockers: readonly number[];
}

/** Used by the path helper and hint overlay: the corridor plus which cells are blocked now. */
export function inspectCorridor(
  prepared: PreparedLevel,
  removed: RemovedFlags,
  id: number,
): CorridorInspection {
  const { width } = prepared.level;
  const cells = prepared.corridors[id].map((idx) => {
    const occ = prepared.occupancy[idx];
    return { x: idx % width, y: Math.floor(idx / width), blocked: occ !== -1 && !removed[occ] };
  });
  return { cells, blockers: activeBlockers(prepared, removed, id) };
}
