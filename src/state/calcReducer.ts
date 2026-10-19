/**
 * App-level calculator state: the current input plus the tape.
 */
import {
  AngleMode,
  CalcState,
  Notice,
  Token,
  Transition,
  initialState,
  insertValue,
  pressBackspace,
  pressClear,
  pressCloseParen,
  pressConstant,
  pressDecimal,
  pressDigit,
  pressEquals,
  pressExp,
  pressFunction,
  pressOpenParen,
  pressOperator,
  pressPostfix,
  pressPower10,
  pressReciprocal,
  pressRoot,
  toggleSign,
} from '../engine';
import type { KeyId } from './keys';
import { KEYS, readJSON } from './storage';

export const MAX_TAPE = 200;

export interface TapeEntry {
  id: string;
  tokens: Token[];
  result: string;
  at: number;
}

export interface AppState {
  calc: CalcState;
  tape: TapeEntry[];
  /** Increments on every successful "=" (drives the result animation). */
  resultSeq: number;
  notice: { kind: Notice; seq: number } | null;
}

export type Action =
  | { type: 'key'; key: KeyId; angle: AngleMode }
  | { type: 'insert'; value: string }
  | { type: 'clearTape' };

function keyTransition(s: CalcState, key: KeyId, angle: AngleMode): Transition {
  switch (key) {
    case 'add':
      return pressOperator(s, '+');
    case 'sub':
      return pressOperator(s, '-');
    case 'mul':
      return pressOperator(s, '*');
    case 'div':
      return pressOperator(s, '/');
    case 'pow':
      return pressOperator(s, '^');
    case 'dot':
      return pressDecimal(s);
    case 'sign':
      return toggleSign(s);
    case 'eq':
      return pressEquals(s, angle);
    case 'ac':
      return pressClear();
    case 'back':
      return pressBackspace(s);
    case 'pct':
      return pressPostfix(s, '%');
    case 'fact':
      return pressPostfix(s, '!');
    case 'sq':
      return pressPostfix(s, 'sq');
    case 'cube':
      return pressPostfix(s, 'cube');
    case 'lp':
      return pressOpenParen(s);
    case 'rp':
      return pressCloseParen(s);
    case 'inv':
      return pressReciprocal(s);
    case 'sin':
    case 'cos':
    case 'tan':
    case 'asin':
    case 'acos':
    case 'atan':
    case 'ln':
    case 'log':
      return pressFunction(s, key);
    case 'exp':
      return pressExp(s);
    case 'pow10':
      return pressPower10(s);
    case 'sqrt':
    case 'cbrt':
      return pressRoot(s, key);
    case 'pi':
    case 'e':
      return pressConstant(s, key);
    case 'second':
    case 'angle':
      return { state: s }; // handled by the screen
    default:
      return pressDigit(s, key);
  }
}

let idCounter = 0;
const newId = () => `${Date.now().toString(36)}-${(idCounter++).toString(36)}`;

function apply(state: AppState, tr: Transition): AppState {
  let { tape, resultSeq, notice } = state;
  if (tr.entry) {
    tape = [...tape, { id: newId(), ...tr.entry, at: Date.now() }].slice(
      -MAX_TAPE,
    );
  }
  if (
    tr.state.justEvaluated &&
    !state.calc.justEvaluated &&
    tr.state.error === null
  ) {
    resultSeq += 1;
  }
  if (tr.notice) {
    notice = { kind: tr.notice, seq: (notice?.seq ?? 0) + 1 };
  }
  if (
    tr.state === state.calc &&
    tape === state.tape &&
    notice === state.notice
  ) {
    return state;
  }
  return { calc: tr.state, tape, resultSeq, notice };
}

export function reducer(state: AppState, action: Action): AppState {
  switch (action.type) {
    case 'key':
      return apply(state, keyTransition(state.calc, action.key, action.angle));
    case 'insert':
      return apply(state, insertValue(state.calc, action.value));
    case 'clearTape':
      return { ...state, tape: [] };
  }
}

interface SavedSession {
  tokens: Token[];
  justEvaluated: boolean;
}

export function loadAppState(): AppState {
  const session = readJSON<SavedSession | null>(KEYS.session, null);
  const tape = readJSON<TapeEntry[]>(KEYS.tape, []);
  return {
    calc:
      session && Array.isArray(session.tokens)
        ? {
            tokens: session.tokens,
            justEvaluated: !!session.justEvaluated,
            error: null,
          }
        : initialState,
    tape: Array.isArray(tape) ? tape.slice(-MAX_TAPE) : [],
    resultSeq: 0,
    notice: null,
  };
}
