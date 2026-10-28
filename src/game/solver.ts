import { activeCount, freeArrows, isFree, type PreparedLevel, type RemovedFlags } from './board';

/**
 * Solver.
 *
 * Because removing an arrow only empties cells, an arrow that is free stays free
 * no matter what else is removed. That makes the puzzle "confluent": any order
 * of free moves reaches the same end state, so a greedy pass that keeps removing
 * free arrows decides solvability exactly. There are no dead ends, and any free
 * arrow is always a correct next move. The solver is O(arrows + blocker links).
 */

export function simulateRemove(removed: RemovedFlags, id: number): boolean[] {
  const next = removed.slice();
  next[id] = true;
  return next;
}

export interface SolveResult {
  readonly solvable: boolean;
  /** A complete removal order from the given state (empty if unsolvable). */
  readonly order: readonly number[];
  /** Number of greedy rounds (all free arrows removed per round). Measures chain depth. */
  readonly rounds: number;
  /** Arrows left when the greedy pass got stuck (they form or depend on a cycle). */
  readonly stuck: readonly number[];
}

export function solve(prepared: PreparedLevel, removed: RemovedFlags): SolveResult {
  const n = prepared.level.arrows.length;
  // Count of active blockers per active arrow.
  const pending = new Int32Array(n);
  for (let id = 0; id < n; id++) {
    if (removed[id]) continue;
    let c = 0;
    for (const b of prepared.blockers[id]) if (!removed[b]) c++;
    pending[id] = c;
  }
  let frontier: number[] = [];
  for (let id = 0; id < n; id++) if (!removed[id] && pending[id] === 0) frontier.push(id);

  const order: number[] = [];
  const done = removed.slice();
  let rounds = 0;
  while (frontier.length) {
    rounds++;
    const next: number[] = [];
    for (const id of frontier) {
      order.push(id);
      done[id] = true;
    }
    for (const id of frontier) {
      for (const dep of prepared.dependents[id]) {
        if (done[dep]) continue;
        pending[dep]--;
        if (pending[dep] === 0) next.push(dep);
      }
    }
    next.sort((a, b) => a - b);
    frontier = next;
  }
  const stuck: number[] = [];
  for (let id = 0; id < n; id++) if (!done[id]) stuck.push(id);
  const solvable = stuck.length === 0;
  return { solvable, order: solvable ? order : [], rounds, stuck };
}

export function isSolvable(prepared: PreparedLevel, removed: RemovedFlags): boolean {
  return solve(prepared, removed).solvable;
}

export type HintResult =
  | { kind: 'move'; arrowId: number }
  | { kind: 'complete' }
  | { kind: 'unsolvable'; stuck: readonly number[] };

/**
 * Deterministic hint. Picks the free arrow that currently holds up the most
 * other active arrows (so the hint is useful, not just legal); ties go to the
 * lowest id. Never returns a blocked arrow and never picks at random.
 */
export function nextMove(prepared: PreparedLevel, removed: RemovedFlags): HintResult {
  if (activeCount(removed) === 0) return { kind: 'complete' };
  const free = freeArrows(prepared, removed);
  if (free.length === 0) return { kind: 'unsolvable', stuck: solve(prepared, removed).stuck };
  let best = free[0];
  let bestScore = -1;
  for (const id of free) {
    let score = 0;
    for (const dep of prepared.dependents[id]) if (!removed[dep]) score++;
    if (score > bestScore) {
      best = id;
      bestScore = score;
    }
  }
  // Defensive: the chosen arrow must be free under the engine's own rule.
  if (!isFree(prepared, removed, best)) return { kind: 'unsolvable', stuck: [] };
  return { kind: 'move', arrowId: best };
}

export interface LevelMetrics {
  readonly arrows: number;
  readonly cells: number;
  readonly fill: number;
  readonly initialFree: number;
  readonly rounds: number;
  readonly links: number;
  readonly longestChain: number;
  readonly bentArrows: number;
  readonly maxLength: number;
}

/** Difficulty measurements used by the level tools. */
export function measure(prepared: PreparedLevel): LevelMetrics {
  const { level } = prepared;
  const n = level.arrows.length;
  const removed = level.arrows.map(() => false);
  const res = solve(prepared, removed);
  let links = 0;
  for (const b of prepared.blockers) links += b.length;
  // Longest chain = longest path in the blocks DAG, computed along the solve order.
  const chain = new Int32Array(n).fill(1);
  for (const id of res.order) {
    for (const b of prepared.blockers[id]) {
      if (chain[b] + 1 > chain[id]) chain[id] = chain[b] + 1;
    }
  }
  let longestChain = 0;
  for (let i = 0; i < n; i++) if (chain[i] > longestChain) longestChain = chain[i];
  let cells = 0;
  let bent = 0;
  let maxLength = 0;
  for (const a of level.arrows) {
    cells += a.cells.length;
    if (a.cells.length > maxLength) maxLength = a.cells.length;
    const xs = new Set(a.cells.map((c) => c.x));
    const ys = new Set(a.cells.map((c) => c.y));
    if (xs.size > 1 && ys.size > 1) bent++;
  }
  return {
    arrows: n,
    cells,
    fill: cells / (level.width * level.height),
    initialFree: freeArrows(prepared, removed).length,
    rounds: res.rounds,
    links,
    longestChain,
    bentArrows: bent,
    maxLength,
  };
}
