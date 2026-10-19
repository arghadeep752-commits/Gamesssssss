/**
 * Token model for calculator input.
 *
 * Input is built key by key, so the engine works on a token list instead of
 * re-parsing a string. That keeps editing (backspace, sign toggle, reuse of
 * results) exact and removes any ambiguity between, say, "2e" and "2E5".
 */

export type BinaryOp = '+' | '-' | '*' | '/' | '^';
export type FnName =
  | 'sin'
  | 'cos'
  | 'tan'
  | 'asin'
  | 'acos'
  | 'atan'
  | 'ln'
  | 'log';
export type PreName = 'sqrt' | 'cbrt';
export type ConstName = 'pi' | 'e';
export type PostName = '%' | '!' | 'sq' | 'cube';

export type Token =
  | { t: 'num'; v: string } // "12", "12.", "0.5", "1.5E-7"
  | { t: 'op'; v: BinaryOp }
  | { t: 'neg' } // unary minus
  | { t: 'lp' } // "("
  | { t: 'rp' } // ")"
  | { t: 'fn'; v: FnName } // a function name with its own opening parenthesis
  | { t: 'pre'; v: PreName } // prefix root, applies to the next operand
  | { t: 'const'; v: ConstName }
  | { t: 'post'; v: PostName };

export const num = (v: string): Token => ({ t: 'num', v });
export const op = (v: BinaryOp): Token => ({ t: 'op', v });

/** True when the token can end an operand (a value is complete up to here). */
export function endsOperand(tk: Token | undefined): boolean {
  if (!tk) {
    return false;
  }
  if (tk.t === 'num') {
    return !/E-?$/.test(tk.v);
  }
  return tk.t === 'const' || tk.t === 'rp' || tk.t === 'post';
}

/** True when the token can start an operand (used for implicit multiplication). */
export function startsOperand(tk: Token | undefined): boolean {
  if (!tk) {
    return false;
  }
  return (
    tk.t === 'num' ||
    tk.t === 'const' ||
    tk.t === 'lp' ||
    tk.t === 'fn' ||
    tk.t === 'pre'
  );
}

/** Number of "(" (including function openers) not yet closed. */
export function openParens(tokens: Token[]): number {
  let depth = 0;
  for (const tk of tokens) {
    if (tk.t === 'lp' || tk.t === 'fn') {
      depth++;
    } else if (tk.t === 'rp' && depth > 0) {
      depth--;
    }
  }
  return depth;
}

/** Count of digits in a number token (mantissa only). */
export function digitCount(v: string): number {
  const mantissa = v.split('E')[0];
  return mantissa.replace(/[^0-9]/g, '').length;
}

/** Tokens for a canonical number string, e.g. "-12.5" -> [neg, num(12.5)]. */
export function valueTokens(canonical: string): Token[] {
  if (canonical.startsWith('-')) {
    return [{ t: 'neg' }, num(canonical.slice(1))];
  }
  return [num(canonical)];
}

/**
 * Index where the trailing operand starts, or -1 if the token list does not
 * end with a complete operand. Includes prefix roots and postfix operators,
 * e.g. for "2+√9²" the operand is "√9²".
 */
export function lastOperandStart(tokens: Token[]): number {
  let i = tokens.length - 1;
  if (!endsOperand(tokens[i])) {
    return -1;
  }
  while (i >= 0 && tokens[i].t === 'post') {
    i--;
  }
  if (i < 0) {
    return -1;
  }
  const core = tokens[i];
  if (core.t === 'rp') {
    let depth = 0;
    for (; i >= 0; i--) {
      const tk = tokens[i];
      if (tk.t === 'rp') {
        depth++;
      } else if (tk.t === 'lp' || tk.t === 'fn') {
        depth--;
        if (depth === 0) {
          break;
        }
      }
    }
    if (i < 0) {
      return -1;
    }
  } else if (core.t !== 'num' && core.t !== 'const') {
    return -1;
  }
  while (i > 0 && tokens[i - 1].t === 'pre') {
    i--;
  }
  return i;
}
