import type { GameRules } from '../config/gameConfig';
import { activeBlockers, inspectCorridor, isComplete, isFree, initialRemoved, type CorridorInspection, type PreparedLevel } from './board';
import { nextMove } from './solver';

/**
 * One attempt at one level. Pure data + pure functions: the screen keeps the
 * current SessionState and swaps it for whatever these functions return.
 *
 * The authoritative state changes the moment a move is validated. Animation is
 * purely visual and lives in the UI (IDLE -> MOVING -> REMOVED), so a player who
 * taps quickly is never blocked by an arrow that has already been released.
 */
export type SessionStatus = 'playing' | 'won' | 'lost';

export interface SessionState {
  readonly levelId: string;
  readonly removed: readonly boolean[];
  /** Removal order; Undo pops from the end. Never longer than the arrow count. */
  readonly history: readonly number[];
  readonly moves: number;
  readonly mistakes: number;
  readonly hintsUsed: number;
  readonly undosUsed: number;
  readonly livesLeft: number;
  readonly scansLeft: number;
  readonly status: SessionStatus;
  /** Arrow currently highlighted by a hint, if any. */
  readonly hintArrow: number | null;
}

export function newSession(prepared: PreparedLevel, rules: GameRules): SessionState {
  return {
    levelId: prepared.level.id,
    removed: initialRemoved(prepared),
    history: [],
    moves: 0,
    mistakes: 0,
    hintsUsed: 0,
    undosUsed: 0,
    livesLeft: rules.lives,
    scansLeft: rules.scansPerLevel,
    status: 'playing',
    hintArrow: null,
  };
}

export type TapOutcome =
  | { kind: 'ignored' }
  | { kind: 'removed'; arrowId: number; completed: boolean }
  | { kind: 'blocked'; arrowId: number; blockers: readonly number[]; lifeLost: boolean; gameOver: boolean };

export function livesApply(prepared: PreparedLevel, rules: GameRules): boolean {
  return rules.blockedTapCostsLife && !rules.forgivingTiers.includes(prepared.level.tier);
}

export function tapArrow(
  prepared: PreparedLevel,
  state: SessionState,
  arrowId: number,
  rules: GameRules,
): { state: SessionState; outcome: TapOutcome } {
  if (state.status !== 'playing') return { state, outcome: { kind: 'ignored' } };
  if (arrowId < 0 || arrowId >= state.removed.length || state.removed[arrowId]) {
    return { state, outcome: { kind: 'ignored' } };
  }
  if (isFree(prepared, state.removed, arrowId)) {
    const removed = state.removed.slice();
    removed[arrowId] = true;
    const completed = isComplete(removed);
    const next: SessionState = {
      ...state,
      removed,
      history: [...state.history, arrowId],
      moves: state.moves + 1,
      status: completed ? 'won' : 'playing',
      hintArrow: state.hintArrow === arrowId ? null : state.hintArrow,
    };
    return { state: next, outcome: { kind: 'removed', arrowId, completed } };
  }
  const blockers = activeBlockers(prepared, state.removed, arrowId);
  const lifeLost = livesApply(prepared, rules);
  const livesLeft = lifeLost ? Math.max(0, state.livesLeft - 1) : state.livesLeft;
  const gameOver = lifeLost && livesLeft === 0;
  const next: SessionState = {
    ...state,
    mistakes: state.mistakes + 1,
    livesLeft,
    status: gameOver ? 'lost' : 'playing',
  };
  return { state: next, outcome: { kind: 'blocked', arrowId, blockers, lifeLost, gameOver } };
}

/** Puts the most recently removed arrow back. Mistakes and lives are not refunded. */
export function undo(state: SessionState): { state: SessionState; restored: number | null } {
  if (state.status !== 'playing' || state.history.length === 0) return { state, restored: null };
  const restored = state.history[state.history.length - 1];
  const removed = state.removed.slice();
  removed[restored] = false;
  return {
    state: {
      ...state,
      removed,
      history: state.history.slice(0, -1),
      undosUsed: state.undosUsed + 1,
      hintArrow: null,
    },
    restored,
  };
}

/** Fresh attempt at the same level. Permanent progress is stored elsewhere and untouched. */
export function restart(prepared: PreparedLevel, rules: GameRules): SessionState {
  return newSession(prepared, rules);
}

export type HintOutcome =
  | { kind: 'shown'; arrowId: number; consumed: boolean }
  | { kind: 'none'; reason: 'not-playing' | 'complete' | 'unsolvable' };

/**
 * Highlights a correct next move. Consumes a hint only when a new arrow gets
 * highlighted; asking again while the same hint is still on screen is free.
 * Inventory checks happen in the caller, which owns the persistent hint count.
 */
export function requestHint(prepared: PreparedLevel, state: SessionState): { state: SessionState; outcome: HintOutcome } {
  if (state.status !== 'playing') return { state, outcome: { kind: 'none', reason: 'not-playing' } };
  if (state.hintArrow !== null && !state.removed[state.hintArrow] && isFree(prepared, state.removed, state.hintArrow)) {
    return { state, outcome: { kind: 'shown', arrowId: state.hintArrow, consumed: false } };
  }
  const move = nextMove(prepared, state.removed);
  if (move.kind === 'complete') return { state, outcome: { kind: 'none', reason: 'complete' } };
  if (move.kind === 'unsolvable') return { state, outcome: { kind: 'none', reason: 'unsolvable' } };
  return {
    state: { ...state, hintsUsed: state.hintsUsed + 1, hintArrow: move.arrowId },
    outcome: { kind: 'shown', arrowId: move.arrowId, consumed: true },
  };
}

export function clearHint(state: SessionState): SessionState {
  return state.hintArrow === null ? state : { ...state, hintArrow: null };
}

/** Path helper: shows an arrow's corridor and what blocks it. Uses one scan charge. */
export function scanArrow(
  prepared: PreparedLevel,
  state: SessionState,
  arrowId: number,
): { state: SessionState; inspection: CorridorInspection | null } {
  if (state.status !== 'playing' || state.scansLeft <= 0) return { state, inspection: null };
  if (arrowId < 0 || arrowId >= state.removed.length || state.removed[arrowId]) {
    return { state, inspection: null };
  }
  return {
    state: { ...state, scansLeft: state.scansLeft - 1 },
    inspection: inspectCorridor(prepared, state.removed, arrowId),
  };
}

/** Compact form persisted while a level is in progress. */
export interface SessionSnapshot {
  levelId: string;
  history: number[];
  moves: number;
  mistakes: number;
  hintsUsed: number;
  undosUsed: number;
  livesLeft: number;
  scansLeft: number;
}

export function snapshotSession(state: SessionState): SessionSnapshot {
  return {
    levelId: state.levelId,
    history: state.history.slice(),
    moves: state.moves,
    mistakes: state.mistakes,
    hintsUsed: state.hintsUsed,
    undosUsed: state.undosUsed,
    livesLeft: state.livesLeft,
    scansLeft: state.scansLeft,
  };
}

/**
 * Rebuilds a session from a snapshot by replaying every move through the engine.
 * Returns null if anything is inconsistent, so a damaged save can never put
 * the board into an impossible state.
 */
export function restoreSession(
  prepared: PreparedLevel,
  snap: SessionSnapshot,
  rules: GameRules,
): SessionState | null {
  if (snap.levelId !== prepared.level.id) return null;
  const n = prepared.level.arrows.length;
  const intOk = (v: unknown, min: number, max: number) =>
    typeof v === 'number' && Number.isInteger(v) && v >= min && v <= max;
  if (!Array.isArray(snap.history) || snap.history.length >= n) return null;
  if (!intOk(snap.livesLeft, 1, rules.lives) || !intOk(snap.scansLeft, 0, rules.scansPerLevel)) return null;
  if (!intOk(snap.mistakes, 0, 1e6) || !intOk(snap.hintsUsed, 0, 1e6) || !intOk(snap.undosUsed, 0, 1e6)) return null;
  if (!intOk(snap.moves, snap.history.length, 1e6)) return null;
  const removed = initialRemoved(prepared);
  for (const id of snap.history) {
    if (!intOk(id, 0, n - 1) || removed[id] || !isFree(prepared, removed, id)) return null;
    removed[id] = true;
  }
  return {
    levelId: snap.levelId,
    removed,
    history: snap.history.slice(),
    moves: snap.moves,
    mistakes: snap.mistakes,
    hintsUsed: snap.hintsUsed,
    undosUsed: snap.undosUsed,
    livesLeft: snap.livesLeft,
    scansLeft: snap.scansLeft,
    status: 'playing',
    hintArrow: null,
  };
}
