/**
 * Key handling as pure state transitions, so every rule is unit-testable.
 *
 * After "=" the result stays on screen as the new expression:
 *   - digits, constants and "(" start a new calculation;
 *   - operators and postfix keys (%, !, x², x³) continue from the result;
 *   - functions and roots wrap the result (sin → sin(result).
 */
import { evaluate, hasOperation } from './evaluate';
import { toCanonical } from './format';
import { AngleMode, CalcError, CalcErrorCode } from './math';
import {
  BinaryOp,
  ConstName,
  FnName,
  PostName,
  PreName,
  Token,
  digitCount,
  endsOperand,
  lastOperandStart,
  num,
  op,
  openParens,
  valueTokens,
} from './tokens';

export const MAX_DIGITS = 15;
export const MAX_TOKENS = 120;

export interface CalcState {
  tokens: Token[];
  /** The tokens hold the result of the last "=". */
  justEvaluated: boolean;
  /** Error from the last "=", shown until the next key. */
  error: CalcErrorCode | null;
}

export const initialState: CalcState = {
  tokens: [],
  justEvaluated: false,
  error: null,
};

export type Notice = 'max-digits' | 'max-length';

export interface Transition {
  state: CalcState;
  /** Set when "=" produced a result worth printing on the tape. */
  entry?: { tokens: Token[]; result: string };
  notice?: Notice;
}

const same = (state: CalcState): Transition => ({ state });

function next(tokens: Token[], justEvaluated = false): Transition {
  return { state: { tokens, justEvaluated, error: null } };
}

/** Removes a dangling "." or exponent marker from a trailing number. */
function tidy(tokens: Token[]): Token[] {
  const last = tokens[tokens.length - 1];
  if (last?.t === 'num' && /(\.|E-?)$/.test(last.v)) {
    const v = last.v.replace(/(\.|E-?)$/, '');
    return v === '' ? tokens.slice(0, -1) : [...tokens.slice(0, -1), num(v)];
  }
  return tokens;
}

function tooLong(tokens: Token[]): boolean {
  return tokens.length >= MAX_TOKENS;
}

export function pressDigit(s: CalcState, d: string): Transition {
  if (s.justEvaluated) {
    return next([num(d)]);
  }
  const tokens = s.tokens;
  const last = tokens[tokens.length - 1];
  if (last?.t === 'num') {
    if (last.v.includes('E')) {
      // Exponent-form numbers only come from results and are not extended.
      return tooLong(tokens)
        ? { state: s, notice: 'max-length' }
        : next([...tokens, op('*'), num(d)]);
    }
    if (digitCount(last.v) >= MAX_DIGITS) {
      return { state: s, notice: 'max-digits' };
    }
    const v = last.v === '0' ? d : last.v + d;
    return next([...tokens.slice(0, -1), num(v)]);
  }
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  if (endsOperand(last)) {
    return next([...tokens, op('*'), num(d)]);
  }
  return next([...tokens, num(d)]);
}

export function pressDecimal(s: CalcState): Transition {
  if (s.justEvaluated) {
    return next([num('0.')]);
  }
  const tokens = s.tokens;
  const last = tokens[tokens.length - 1];
  if (last?.t === 'num') {
    if (last.v.includes('.') || last.v.includes('E')) {
      return same(s);
    }
    return next([...tokens.slice(0, -1), num(last.v + '.')]);
  }
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  if (endsOperand(last)) {
    return next([...tokens, op('*'), num('0.')]);
  }
  return next([...tokens, num('0.')]);
}

export function pressOperator(s: CalcState, o: BinaryOp): Transition {
  let tokens = o === '^' ? resultOperand(s) : tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  let last = tokens[tokens.length - 1];

  if (last === undefined) {
    return o === '-' ? next([{ t: 'neg' }]) : next([num('0'), op(o)]);
  }
  if (last.t === 'neg') {
    if (o === '-') {
      return same(s);
    }
    // "5 × −" then "+" becomes "5 +"
    tokens = tokens.slice(0, -1);
    last = tokens[tokens.length - 1];
    if (last === undefined) {
      return next([]);
    }
    if (last.t === 'op') {
      return next([...tokens.slice(0, -1), op(o)]);
    }
    return next(tokens);
  }
  if (last.t === 'op') {
    if (o === '-' && last.v !== '+' && last.v !== '-') {
      return next([...tokens, { t: 'neg' }]); // 5 × −3, 2^−1
    }
    return next([...tokens.slice(0, -1), op(o)]);
  }
  if (last.t === 'lp' || last.t === 'fn' || last.t === 'pre') {
    return o === '-' ? next([...tokens, { t: 'neg' }]) : same(s);
  }
  return next([...tokens, op(o)]);
}

/** A result with a sign (or other prefix) is parenthesised before "^" or a postfix. */
function resultOperand(s: CalcState): Token[] {
  const tokens = tidy(s.tokens);
  return s.justEvaluated && tokens.length > 1
    ? [{ t: 'lp' }, ...tokens, { t: 'rp' }]
    : tokens;
}

export function pressPostfix(s: CalcState, p: PostName): Transition {
  const tokens = resultOperand(s);
  const last = tokens[tokens.length - 1];
  if (!endsOperand(last)) {
    return same(s);
  }
  if (p === '%' && last?.t === 'post' && last.v === '%') {
    return same(s);
  }
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  return next([...tokens, { t: 'post', v: p }]);
}

export function pressFunction(s: CalcState, fn: FnName): Transition {
  if (s.justEvaluated) {
    return next([{ t: 'fn', v: fn }, ...s.tokens]);
  }
  const tokens = tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  return next([...tokens, { t: 'fn', v: fn }]);
}

export function pressRoot(s: CalcState, p: PreName): Transition {
  if (s.justEvaluated) {
    const body =
      s.tokens.length > 1
        ? [{ t: 'lp' } as Token, ...s.tokens, { t: 'rp' } as Token]
        : s.tokens;
    return next([{ t: 'pre', v: p }, ...body]);
  }
  const tokens = tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  const last = tokens[tokens.length - 1];
  // "2³√8" would be ambiguous, so the multiplication is written out.
  if (p === 'cbrt' && endsOperand(last)) {
    return next([...tokens, op('*'), { t: 'pre', v: p }]);
  }
  return next([...tokens, { t: 'pre', v: p }]);
}

export function pressConstant(s: CalcState, c: ConstName): Transition {
  if (s.justEvaluated) {
    return next([{ t: 'const', v: c }]);
  }
  const tokens = tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  const last = tokens[tokens.length - 1];
  if (last?.t === 'const' || last?.t === 'post') {
    return next([...tokens, op('*'), { t: 'const', v: c }]);
  }
  return next([...tokens, { t: 'const', v: c }]);
}

export function pressPower10(s: CalcState): Transition {
  if (s.justEvaluated) {
    return next([num('10'), op('^'), ...s.tokens]);
  }
  const base = tidy(s.tokens);
  if (tooLong(base)) {
    return { state: s, notice: 'max-length' };
  }
  const prefix = endsOperand(base[base.length - 1]) ? [op('*')] : [];
  return next([...base, ...prefix, num('10'), op('^')]);
}

export function pressExp(s: CalcState): Transition {
  if (s.justEvaluated) {
    return next([{ t: 'const', v: 'e' }, op('^'), ...s.tokens]);
  }
  const base = tidy(s.tokens);
  if (tooLong(base)) {
    return { state: s, notice: 'max-length' };
  }
  const prefix =
    base[base.length - 1]?.t === 'const' || base[base.length - 1]?.t === 'post'
      ? [op('*')]
      : [];
  return next([...base, ...prefix, { t: 'const', v: 'e' }, op('^')]);
}

export function pressOpenParen(s: CalcState): Transition {
  if (s.justEvaluated) {
    return next([{ t: 'lp' }]);
  }
  const tokens = tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  return next([...tokens, { t: 'lp' }]);
}

export function pressCloseParen(s: CalcState): Transition {
  const tokens = tidy(s.tokens);
  if (openParens(tokens) === 0 || !endsOperand(tokens[tokens.length - 1])) {
    return same(s);
  }
  return next([...tokens, { t: 'rp' }]);
}

/** 1/x: wraps the trailing operand as (1 ÷ x). */
export function pressReciprocal(s: CalcState): Transition {
  const tokens = tidy(s.tokens);
  const start = lastOperandStart(tokens);
  if (start === -1) {
    return same(s);
  }
  // A leading minus belongs to the operand: −8 → 1 ÷ −8
  const operand = tokens.slice(start);
  const head = tokens.slice(0, start);
  if (
    head.length === 0 ||
    (s.justEvaluated && head.every(tk => tk.t === 'neg'))
  ) {
    return next([num('1'), op('/'), ...head, ...operand]);
  }
  return next([
    ...head,
    { t: 'lp' },
    num('1'),
    op('/'),
    ...operand,
    { t: 'rp' },
  ]);
}

/** ± toggles the sign of the trailing operand. */
export function toggleSign(s: CalcState): Transition {
  const tokens = tidy(s.tokens);
  if (s.justEvaluated) {
    if (tokens[0]?.t === 'neg' && lastOperandStart(tokens) === 1) {
      return next(tokens.slice(1), true);
    }
    return next([{ t: 'neg' }, ...tokens], true);
  }
  const last = tokens[tokens.length - 1];
  if (last === undefined) {
    return next([{ t: 'neg' }]);
  }
  if (last.t === 'neg') {
    const without = tokens.slice(0, -1);
    // Also drop a "(" that was opened only for the minus sign.
    if (
      without[without.length - 1]?.t === 'lp' &&
      without[without.length - 2]?.t === 'op'
    ) {
      return next(without.slice(0, -1));
    }
    return next(without);
  }
  if (
    last.t === 'op' ||
    last.t === 'lp' ||
    last.t === 'fn' ||
    last.t === 'pre'
  ) {
    if (last.t === 'op' && (last.v === '+' || last.v === '-')) {
      return next([...tokens, { t: 'lp' }, { t: 'neg' }]);
    }
    return next([...tokens, { t: 'neg' }]);
  }
  const start = lastOperandStart(tokens);
  if (start === -1) {
    return same(s);
  }
  const before = tokens[start - 1];
  if (before?.t === 'neg') {
    const beforeNeg = tokens[start - 2];
    const parenOpenedForSign =
      beforeNeg?.t === 'lp' &&
      tokens[start - 3]?.t === 'op' &&
      openParens(tokens) > 0;
    if (parenOpenedForSign) {
      return next([...tokens.slice(0, start - 2), ...tokens.slice(start)]);
    }
    return next([...tokens.slice(0, start - 1), ...tokens.slice(start)]);
  }
  if (before === undefined || before.t === 'lp' || before.t === 'fn') {
    return next([
      ...tokens.slice(0, start),
      { t: 'neg' },
      ...tokens.slice(start),
    ]);
  }
  if (before.t === 'op' && (before.v === '+' || before.v === '-')) {
    return next([
      ...tokens.slice(0, start),
      { t: 'lp' },
      { t: 'neg' },
      ...tokens.slice(start),
    ]);
  }
  return next([
    ...tokens.slice(0, start),
    { t: 'neg' },
    ...tokens.slice(start),
  ]);
}

export function pressBackspace(s: CalcState): Transition {
  const tokens = s.tokens;
  const last = tokens[tokens.length - 1];
  if (last === undefined) {
    return same(s);
  }
  if (last.t === 'num') {
    if (last.v.includes('E')) {
      return next(tokens.slice(0, -1)); // a result in exponent form is removed whole
    }
    const v = last.v.slice(0, -1);
    return next(
      v === '' ? tokens.slice(0, -1) : [...tokens.slice(0, -1), num(v)],
    );
  }
  return next(tokens.slice(0, -1));
}

export function pressClear(): Transition {
  return { state: initialState };
}

export function pressEquals(s: CalcState, angle: AngleMode): Transition {
  const tokens = tidy(s.tokens);
  if (tokens.length === 0 || s.justEvaluated) {
    return same(s);
  }
  try {
    const value = evaluate(tokens, angle);
    const result = toCanonical(value);
    const lone = !hasOperation(trimTrailingOps(tokens));
    const closed: Token[] = [...trimTrailingOps(tokens)];
    for (let i = openParens(closed); i > 0; i--) {
      closed.push({ t: 'rp' });
    }
    return {
      state: { tokens: valueTokens(result), justEvaluated: true, error: null },
      entry: lone ? undefined : { tokens: closed, result },
    };
  } catch (e) {
    const code = e instanceof CalcError ? e.code : 'syntax';
    return { state: { tokens: s.tokens, justEvaluated: false, error: code } };
  }
}

function trimTrailingOps(tokens: Token[]): Token[] {
  let end = tokens.length;
  while (end > 0 && tokens[end - 1].t === 'op') {
    end--;
  }
  return tokens.slice(0, end);
}

/** Inserts a stored result (from the tape) as an operand. */
export function insertValue(s: CalcState, canonical: string): Transition {
  const value = valueTokens(canonical);
  if (s.justEvaluated || s.tokens.length === 0) {
    return next(value);
  }
  const tokens = tidy(s.tokens);
  if (tooLong(tokens)) {
    return { state: s, notice: 'max-length' };
  }
  const last = tokens[tokens.length - 1];
  if (endsOperand(last)) {
    const wrapped =
      value.length > 1
        ? [{ t: 'lp' } as Token, ...value, { t: 'rp' } as Token]
        : value;
    return next([...tokens, op('*'), ...wrapped]);
  }
  if (
    last?.t === 'op' &&
    value.length > 1 &&
    (last.v === '+' || last.v === '-')
  ) {
    return next([...tokens, { t: 'lp' }, ...value, { t: 'rp' }]);
  }
  if (last?.t === 'neg' && value.length > 1) {
    return next([...tokens, { t: 'lp' }, ...value, { t: 'rp' }]);
  }
  return next([...tokens, ...value]);
}

/** Error messages written for the display. */
export const ERROR_TEXT: Record<CalcErrorCode, string> = {
  div0: 'Can’t divide by zero',
  domain: 'Undefined for this input',
  overflow: 'Result is too large',
  syntax: 'Check the expression',
};
