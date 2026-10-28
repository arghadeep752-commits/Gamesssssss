/**
 * Core puzzle types. Everything in src/game is pure TypeScript with no React
 * or React Native imports, so it runs identically in the app, in tests and in
 * the offline level tools.
 *
 * GEOMETRY RULES (shared by gameplay, hints, the path helper and the solver)
 * ------------------------------------------------------------------------
 * - The board is a W x H grid of cells. x grows to the right, y grows down.
 * - An arrow is an ordered list of orthogonally adjacent cells. cells[0] is the
 *   tail, cells[cells.length - 1] is the head. An arrow has at least 2 cells.
 * - The exit direction is the direction of the final step (tail -> head), so the
 *   arrowhead always continues its last segment.
 * - Each cell holds at most one arrow. Arrows never cross or share cells, so
 *   there are no intersections to resolve.
 * - An arrow leaves by rigid translation: its whole shape slides, unchanged, in
 *   its exit direction until it is off the board.
 * - The exit corridor of an arrow is every cell that any of its cells passes
 *   through on the way out: for each cell c, the cells c + k*dir for k >= 1 that
 *   are still on the board, minus the arrow's own cells.
 * - An arrow is blocked when at least one other ACTIVE arrow occupies a cell in
 *   its corridor. Otherwise it is free and may leave.
 * - Removing arrows only ever empties cells, so a free arrow stays free. The
 *   "blocks" relation is therefore fixed by the starting layout, and a level is
 *   solvable exactly when that relation has no cycle.
 */

export type Direction = 'U' | 'D' | 'L' | 'R';

export interface Cell {
  readonly x: number;
  readonly y: number;
}

export interface ArrowDef {
  /** Unique within its level; equal to its index in the level's arrow list. */
  readonly id: number;
  /** Ordered path cells, tail first, head last. */
  readonly cells: readonly Cell[];
  /** Exit direction, always equal to the direction of the final step. */
  readonly dir: Direction;
}

export type Tier = 'tutorial' | 'easy' | 'normal' | 'hard' | 'expert';

export interface LevelDef {
  /** Stable key used for saves, e.g. "L001" or "D2026-10-28". */
  readonly id: string;
  /** 1-based level number for display (0 for daily puzzles). */
  readonly number: number;
  readonly tier: Tier;
  readonly width: number;
  readonly height: number;
  readonly arrows: readonly ArrowDef[];
}

/** Compact on-disk form: "w h" plus one token per arrow (see geometry.decodeArrow). */
export interface PackedLevel {
  readonly w: number;
  readonly h: number;
  /** Space separated arrow tokens. */
  readonly a: string;
}
