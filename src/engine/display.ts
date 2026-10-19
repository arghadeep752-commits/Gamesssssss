/**
 * Turns tokens into the text shown on the display and on the tape.
 */
import { Grouping, formatUnsigned } from './format';
import { Token, openParens } from './tokens';

const OP_TEXT: Record<string, string> = {
  '+': ' + ',
  '-': ' − ',
  '*': ' × ',
  '/': ' ÷ ',
  '^': '^',
};

const FN_TEXT: Record<string, string> = {
  sin: 'sin(',
  cos: 'cos(',
  tan: 'tan(',
  asin: 'arcsin(',
  acos: 'arccos(',
  atan: 'arctan(',
  ln: 'ln(',
  log: 'log(',
};

const POST_TEXT: Record<string, string> = {
  '%': '%',
  '!': '!',
  sq: '²',
  cube: '³',
};

export function tokenText(tk: Token, grouping: Grouping): string {
  switch (tk.t) {
    case 'num':
      return formatUnsigned(tk.v, grouping);
    case 'op':
      return OP_TEXT[tk.v];
    case 'neg':
      return '−';
    case 'lp':
      return '(';
    case 'rp':
      return ')';
    case 'fn':
      return FN_TEXT[tk.v];
    case 'pre':
      return tk.v === 'sqrt' ? '√' : '³√';
    case 'const':
      return tk.v === 'pi' ? 'π' : 'e';
    case 'post':
      return POST_TEXT[tk.v];
  }
}

export interface ExpressionText {
  text: string;
  /** Closing parentheses the engine will add automatically. */
  ghost: string;
}

export function expressionText(
  tokens: Token[],
  grouping: Grouping,
): ExpressionText {
  let text = '';
  tokens.forEach((tk, i) => {
    let part = tokenText(tk, grouping);
    if (tk.t === 'num' && tk.v.includes('E')) {
      const next = tokens[i + 1];
      // "1.5×10²⁵" followed by "²" or "^" would read ambiguously.
      if (next && (next.t === 'post' || (next.t === 'op' && next.v === '^'))) {
        part = `(${part})`;
      }
    }
    text += part;
  });
  return { text: text.trim(), ghost: ')'.repeat(openParens(tokens)) };
}

/** Full expression including auto-closed parentheses (for the tape). */
export function closedExpressionText(
  tokens: Token[],
  grouping: Grouping,
): string {
  const { text, ghost } = expressionText(tokens, grouping);
  return text + ghost;
}

/** Spoken form for screen readers. */
export function spokenExpression(tokens: Token[], grouping: Grouping): string {
  return closedExpressionText(tokens, grouping)
    .replace(/×/g, ' times ')
    .replace(/÷/g, ' divided by ')
    .replace(/−/g, ' minus ')
    .replace(/\+/g, ' plus ')
    .replace(/π/g, ' pi ')
    .replace(/√/g, ' square root of ')
    .replace(/\^/g, ' to the power of ')
    .replace(/\s+/g, ' ')
    .trim();
}
