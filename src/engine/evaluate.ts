/**
 * Recursive-descent evaluator over tokens.
 *
 * Grammar (highest binding last):
 *   expr      := term (('+' | '-') term)*
 *   term      := unary (('*' | '/') unary | <implicit ×> unary)*
 *   unary     := '−' unary | root unary | power
 *   power     := postfixed ('^' unary)?          right-associative
 *   postfixed := primary ('%' | '!' | '²' | '³')*
 *   primary   := number | constant | '(' expr ')' | fn '(' expr ')'
 *
 * Missing closing parentheses at the end are closed automatically.
 * "a + b%" and "a − b%" mean "a plus/minus b percent of a", like a desk
 * calculator; everywhere else b% is b/100.
 */
import {
  AngleMode,
  CalcError,
  addSafe,
  check,
  factorial,
  inverseTrig,
  power,
  trig,
} from './math';
import { FnName, PostName, PreName, Token, startsOperand } from './tokens';

interface Val {
  v: number;
  /** The value is a bare percentage (eligible for "a + b%" semantics). */
  pct: boolean;
}

function applyFn(fn: FnName, x: number, angle: AngleMode): number {
  switch (fn) {
    case 'sin':
    case 'cos':
    case 'tan':
      return trig(fn, x, angle);
    case 'asin':
    case 'acos':
    case 'atan':
      return inverseTrig(fn, x, angle);
    case 'ln':
      if (x <= 0) {
        throw new CalcError('domain');
      }
      return check(Math.log(x));
    case 'log':
      if (x <= 0) {
        throw new CalcError('domain');
      }
      return check(Math.log10(x));
  }
}

function applyPre(p: PreName, x: number): number {
  if (p === 'sqrt') {
    if (x < 0) {
      throw new CalcError('domain');
    }
    return check(Math.sqrt(x));
  }
  return check(Math.cbrt(x));
}

function applyPost(p: PostName, x: number): Val {
  switch (p) {
    case '%':
      return { v: check(x / 100), pct: true };
    case '!':
      return { v: factorial(x), pct: false };
    case 'sq':
      return { v: check(x * x), pct: false };
    case 'cube':
      return { v: check(x * x * x), pct: false };
  }
}

class Parser {
  private i = 0;
  constructor(
    private readonly tk: Token[],
    private readonly angle: AngleMode,
  ) {}

  run(): number {
    if (this.tk.length === 0) {
      throw new CalcError('syntax');
    }
    const r = this.expr();
    if (this.i < this.tk.length) {
      throw new CalcError('syntax');
    }
    return r.v;
  }

  private peek(): Token | undefined {
    return this.tk[this.i];
  }

  private expr(): Val {
    let left = this.term();
    for (;;) {
      const p = this.peek();
      if (!p || p.t !== 'op' || (p.v !== '+' && p.v !== '-')) {
        return left;
      }
      this.i++;
      const right = this.term();
      const delta = right.pct ? check(left.v * right.v) : right.v;
      left = { v: addSafe(left.v, p.v === '+' ? delta : -delta), pct: false };
    }
  }

  private term(): Val {
    let left = this.unary();
    for (;;) {
      const p = this.peek();
      if (p && p.t === 'op' && (p.v === '*' || p.v === '/')) {
        this.i++;
        const right = this.unary();
        if (p.v === '/') {
          if (right.v === 0) {
            throw new CalcError('div0');
          }
          left = { v: check(left.v / right.v), pct: false };
        } else {
          left = { v: check(left.v * right.v), pct: false };
        }
      } else if (startsOperand(p)) {
        // Implicit multiplication: 2π, 3(4+1), 2sin(30)
        const right = this.unary();
        left = { v: check(left.v * right.v), pct: false };
      } else {
        return left;
      }
    }
  }

  private unary(): Val {
    const p = this.peek();
    if (p?.t === 'neg') {
      this.i++;
      const r = this.unary();
      return { v: r.v === 0 ? 0 : -r.v, pct: r.pct };
    }
    if (p?.t === 'pre') {
      this.i++;
      const r = this.unary();
      return { v: applyPre(p.v, r.v), pct: false };
    }
    return this.power();
  }

  private power(): Val {
    const base = this.postfixed();
    const p = this.peek();
    if (p?.t === 'op' && p.v === '^') {
      this.i++;
      const exponent = this.unary();
      return { v: power(base.v, exponent.v), pct: false };
    }
    return base;
  }

  private postfixed(): Val {
    let r = this.primary();
    for (let p = this.peek(); p?.t === 'post'; p = this.peek()) {
      this.i++;
      r = applyPost(p.v, r.v);
    }
    return r;
  }

  private primary(): Val {
    const p = this.tk[this.i++];
    if (!p) {
      throw new CalcError('syntax');
    }
    switch (p.t) {
      case 'num': {
        const v = Number(p.v);
        if (Number.isNaN(v)) {
          throw new CalcError('syntax');
        }
        return { v: check(v), pct: false };
      }
      case 'const':
        return { v: p.v === 'pi' ? Math.PI : Math.E, pct: false };
      case 'lp': {
        const r = this.expr();
        this.closeParen();
        return { v: r.v, pct: false };
      }
      case 'fn': {
        const r = this.expr();
        this.closeParen();
        return { v: applyFn(p.v, r.v, this.angle), pct: false };
      }
      default:
        throw new CalcError('syntax');
    }
  }

  private closeParen() {
    const p = this.peek();
    if (p?.t === 'rp') {
      this.i++;
    } else if (p !== undefined) {
      throw new CalcError('syntax');
    }
    // End of input: the parenthesis closes automatically.
  }
}

/**
 * Drops a trailing binary operator (and a dangling decimal point/exponent)
 * so "12 × 7 +" can still be evaluated as "12 × 7".
 */
export function trimForEval(tokens: Token[]): Token[] {
  const out = tokens.slice();
  while (out.length > 0) {
    const last = out[out.length - 1];
    if (last.t === 'op') {
      out.pop();
    } else if (last.t === 'num' && /(\.|E-?)$/.test(last.v)) {
      const v = last.v.replace(/(\.|E-?)$/, '');
      if (v === '') {
        out.pop();
      } else {
        out[out.length - 1] = { t: 'num', v };
      }
    } else {
      break;
    }
  }
  return out;
}

export function evaluate(tokens: Token[], angle: AngleMode): number {
  return new Parser(trimForEval(tokens), angle).run();
}

/** True when the tokens are more than a lone number (worth previewing). */
export function hasOperation(tokens: Token[]): boolean {
  return (
    tokens.some(tk => tk.t !== 'num' && tk.t !== 'neg') ||
    tokens.filter(tk => tk.t === 'num').length > 1
  );
}
