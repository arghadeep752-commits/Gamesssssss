/**
 * Engine tests: every scenario is driven through the same key handlers the
 * keypad uses, then checked on the result and on the displayed text.
 */
import {
  AngleMode,
  CalcState,
  Grouping,
  Transition,
  expressionText,
  formatCanonical,
  formatUnsigned,
  groupInteger,
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
  toCanonical,
  toggleSign,
} from '../src/engine';

interface Run {
  state: CalcState;
  entries: { text: string; result: string }[];
  notices: string[];
}

function run(
  keys: string,
  angle: AngleMode = 'deg',
  start: CalcState = initialState,
): Run {
  let state = start;
  const entries: Run['entries'] = [];
  const notices: string[] = [];
  for (const k of keys.split(' ').filter(Boolean)) {
    let tr: Transition;
    if (/^[0-9]$/.test(k)) {
      tr = pressDigit(state, k);
    } else {
      switch (k) {
        case '.':
          tr = pressDecimal(state);
          break;
        case '+':
        case '-':
        case '*':
        case '/':
        case '^':
          tr = pressOperator(state, k);
          break;
        case '%':
        case '!':
        case 'sq':
        case 'cube':
          tr = pressPostfix(state, k);
          break;
        case 'sin':
        case 'cos':
        case 'tan':
        case 'asin':
        case 'acos':
        case 'atan':
        case 'ln':
        case 'log':
          tr = pressFunction(state, k);
          break;
        case 'sqrt':
        case 'cbrt':
          tr = pressRoot(state, k);
          break;
        case 'pi':
        case 'e':
          tr = pressConstant(state, k);
          break;
        case '(':
          tr = pressOpenParen(state);
          break;
        case ')':
          tr = pressCloseParen(state);
          break;
        case 'inv':
          tr = pressReciprocal(state);
          break;
        case '±':
          tr = toggleSign(state);
          break;
        case '⌫':
          tr = pressBackspace(state);
          break;
        case 'AC':
          tr = pressClear();
          break;
        case '10x':
          tr = pressPower10(state);
          break;
        case 'ex':
          tr = pressExp(state);
          break;
        case '=':
          tr = pressEquals(state, angle);
          break;
        default:
          throw new Error(`Unknown key ${k}`);
      }
    }
    state = tr.state;
    if (tr.entry) {
      entries.push({
        text: expressionText(tr.entry.tokens, 'intl').text,
        result: tr.entry.result,
      });
    }
    if (tr.notice) {
      notices.push(tr.notice);
    }
  }
  return { state, entries, notices };
}

/** Canonical result after the keys (which should end with "="). */
function result(keys: string, angle: AngleMode = 'deg'): string {
  const { state } = run(keys, angle);
  if (state.error) {
    return `error:${state.error}`;
  }
  return state.tokens
    .map(tk => (tk.t === 'neg' ? '-' : tk.t === 'num' ? tk.v : '?'))
    .join('');
}

function shown(keys: string, grouping: Grouping = 'intl'): string {
  const { state } = run(keys);
  const { text, ghost } = expressionText(state.tokens, grouping);
  return ghost ? `${text}[${ghost}]` : text;
}

describe('arithmetic', () => {
  test.each([
    ['1 2 * 7 + 3 =', '87'],
    ['2 + 3 * 4 =', '14'],
    ['( 2 + 3 ) * 4 =', '20'],
    ['1 0 / 4 =', '2.5'],
    ['7 - 1 0 =', '-3'],
    ['2 ^ 3 ^ 2 =', '512'],
    ['- 2 ^ 2 =', '-4'],
    ['2 ^ - 2 =', '0.25'],
    ['2 pi =', '6.28318530717959'],
    ['2 ( 3 ) =', '6'],
    ['2 sqrt 9 =', '6'],
    ['( 2 + 3 =', '5'],
    ['5 + =', '5'],
  ])('%s → %s', (keys, expected) => {
    expect(result(keys)).toBe(expected);
  });
});

describe('floating point noise is hidden', () => {
  test.each([
    ['0 . 1 + 0 . 2 =', '0.3'],
    ['0 . 1 + 0 . 2 - 0 . 3 =', '0'],
    ['1 / 3 * 3 =', '1'],
    ['1 . 1 * 1 . 1 =', '1.21'],
    ['4 . 3 5 * 1 0 0 =', '435'],
    ['sqrt 2 sq =', '2'],
    ['sqrt 2 sq - 2 =', '0'],
  ])('%s → %s', (keys, expected) => {
    expect(result(keys)).toBe(expected);
  });
});

describe('percent works like a desk calculator', () => {
  test.each([
    ['2 0 0 + 1 0 % =', '220'],
    ['2 0 0 - 1 0 % =', '180'],
    ['2 0 0 * 1 0 % =', '20'],
    ['2 0 0 / 1 0 % =', '2000'],
    ['5 0 % =', '0.5'],
    ['1 0 % + 5 =', '5.1'],
  ])('%s → %s', (keys, expected) => {
    expect(result(keys)).toBe(expected);
  });
});

describe('scientific functions', () => {
  test.each([
    ['sin 3 0 =', 'deg', '0.5'],
    ['sin 1 8 0 =', 'deg', '0'],
    ['cos 9 0 =', 'deg', '0'],
    ['cos 6 0 =', 'deg', '0.5'],
    ['tan 4 5 =', 'deg', '1'],
    ['asin 0 . 5 =', 'deg', '30'],
    ['acos 0 =', 'deg', '90'],
    ['sin pi =', 'rad', '0'],
    ['cos pi =', 'rad', '-1'],
    ['ln e =', 'deg', '1'],
    ['log 1 0 0 0 =', 'deg', '3'],
    ['5 ! =', 'deg', '120'],
    ['0 ! =', 'deg', '1'],
    ['0 . 5 ! =', 'deg', '0.886226925452758'],
    ['9 sq =', 'deg', '81'],
    ['2 cube =', 'deg', '8'],
    ['8 inv =', 'deg', '0.125'],
    ['cbrt 2 7 =', 'deg', '3'],
    ['cbrt - 8 =', 'deg', '-2'],
    ['( - 8 ) ^ ( 1 / 3 ) =', 'deg', '-2'],
    ['10x 3 =', 'deg', '1000'],
    ['ex 1 =', 'deg', '2.71828182845905'],
  ] as const)('%s (%s) → %s', (keys, angle, expected) => {
    expect(result(keys, angle)).toBe(expected);
  });
});

describe('errors', () => {
  test.each([
    ['5 / 0 =', 'div0'],
    ['0 inv =', 'div0'],
    ['sqrt - 4 =', 'domain'],
    ['tan 9 0 =', 'domain'],
    ['log 0 =', 'domain'],
    ['asin 2 =', 'domain'],
    ['( - 3 ) ! =', 'domain'],
    ['1 7 1 ! =', 'overflow'],
    ['1 0 ^ 4 0 0 =', 'overflow'],
    ['sin =', 'syntax'],
  ])('%s → %s', (keys, code) => {
    expect(result(keys)).toBe(`error:${code}`);
  });

  test('the expression is kept for editing after an error', () => {
    const { state } = run('5 / 0 =');
    expect(expressionText(state.tokens, 'intl').text).toBe('5 ÷ 0');
    const next = run('⌫ 2 =', 'deg', state);
    expect(next.state.tokens).toEqual([{ t: 'num', v: '2.5' }]);
  });
});

describe('very large and very small results', () => {
  test('large values switch to exponent form', () => {
    expect(result('9 9 9 9 9 9 9 9 9 9 * 9 9 9 9 9 9 9 9 9 9 =')).toBe(
      '9.999999998E19',
    );
    expect(formatCanonical('9.999999998E19', 'intl')).toBe('9.999999998×10¹⁹');
  });

  test('small values switch to exponent form', () => {
    expect(result('1 / 3 0 0 0 0 0 0 0 0 0 0 =')).toBe('3.33333333333333E-11');
    expect(formatCanonical('3.33333333333333E-11', 'intl')).toBe(
      '3.33333333333333×10⁻¹¹',
    );
  });

  test('exponent-form results are atomic when editing', () => {
    const big = '9 9 9 9 9 9 9 9 9 9 * 9 9 9 9 9 9 9 9 9 9 =';
    expect(shown(`${big} sqrt 2`)).toBe('√9.999999998×10¹⁹ × 2');
    expect(shown(`${big} + 1 ⌫ ⌫ ⌫`)).toBe('');
  });

  test('an exponent result followed by x² is parenthesised on screen', () => {
    expect(shown('9 9 9 9 9 9 9 9 9 9 * 9 9 9 9 9 9 9 9 9 9 = sq')).toBe(
      '(9.999999998×10¹⁹)²',
    );
  });
});

describe('editing', () => {
  test.each([
    ['1 2 3 ⌫', '12'],
    ['1 . 5 ⌫ ⌫', '1'],
    ['. 5', '0.5'],
    ['0 0 7', '7'],
    ['5 + *', '5 ×'],
    ['5 * -', '5 × −'],
    ['5 * - +', '5 +'],
    ['5 + -', '5 −'],
    ['( ( 2', '((2[))]'],
    [')', ''],
    ['2 )', '2'],
    ['pi 2', 'π × 2'],
    ['2 pi', '2π'],
    ['2 cbrt 8', '2 × ³√8'],
    ['sin 3 0', 'sin(30[)]'],
    ['asin 1', 'arcsin(1[)]'],
    ['1 2 . . 5', '12.5'],
    ['AC', ''],
  ])('%s shows "%s"', (keys, expected) => {
    expect(shown(keys)).toBe(expected);
  });

  test('digit limit', () => {
    const { state, notices } = run('1 2 3 4 5 6 7 8 9 0 1 2 3 4 5 6');
    expect(state.tokens).toEqual([{ t: 'num', v: '123456789012345' }]);
    expect(notices).toContain('max-digits');
  });
});

describe('sign toggle', () => {
  test.each([
    ['± 5', '−5'],
    ['5 ±', '−5'],
    ['5 ± ±', '5'],
    ['5 + 3 ±', '5 + (−3[)]'],
    ['5 + 3 ± ±', '5 + 3'],
    ['5 * 3 ±', '5 × −3'],
    ['5 * 3 ± ±', '5 × 3'],
    ['2 ^ 3 ±', '2^−3'],
    ['sin 3 0 ±', 'sin(−30[)]'],
    ['5 + ±', '5 + (−[)]'],
    ['5 + ± ±', '5 +'],
  ])('%s shows "%s"', (keys, expected) => {
    expect(shown(keys)).toBe(expected);
  });

  test('5 + (−3 evaluates to 2', () => {
    expect(result('5 + 3 ± =')).toBe('2');
  });
});

describe('continuing after a result', () => {
  test.each([
    ['2 + 3 = 4', '4'],
    ['2 + 3 = + 1', '5 + 1'],
    ['2 + 3 = sq', '5²'],
    ['5 - 8 = sq', '(−3)²'],
    ['5 - 8 = ^', '(−3)^'],
    ['3 0 = sin', 'sin(30[)]'],
    ['9 = sqrt', '√9'],
    ['5 - 8 = inv', '1 ÷ −3'],
    ['5 - 8 = ±', '3'],
    ['2 + 3 = .', '0.'],
    ['2 + 3 = ⌫', ''],
  ])('%s shows "%s"', (keys, expected) => {
    expect(shown(keys)).toBe(expected);
  });

  test('squaring a negative result gives a positive number', () => {
    expect(result('5 - 8 = sq =')).toBe('9');
  });

  test('pressing = again does nothing', () => {
    const { entries } = run('2 + 3 = =');
    expect(entries).toHaveLength(1);
  });
});

describe('tape entries', () => {
  test('auto-closed parentheses are printed', () => {
    const { entries } = run('sin 3 0 =');
    expect(entries).toEqual([{ text: 'sin(30)', result: '0.5' }]);
  });

  test('a lone number is not printed', () => {
    expect(run('4 2 =').entries).toHaveLength(0);
    expect(run('- 4 2 =').entries).toHaveLength(0);
    expect(run('5 + =').entries).toHaveLength(0);
  });

  test('reusing a tape value', () => {
    const after = run('5 +').state;
    const { state } = insertValue(after, '-3');
    expect(expressionText(state.tokens, 'intl').text).toBe('5 + (−3)');
    const fresh = insertValue(initialState, '42').state;
    expect(fresh.tokens).toEqual([{ t: 'num', v: '42' }]);
    const implicit = insertValue(run('2').state, '3').state;
    expect(expressionText(implicit.tokens, 'intl').text).toBe('2 × 3');
  });
});

describe('formatting', () => {
  test.each([
    [0.1 + 0.2, '0.3'],
    [1e21, '1E21'],
    [-1234.5, '-1234.5'],
    [2 / 3, '0.666666666666667'],
    [123456789.123456789, '123456789.123457'],
    [-0, '0'],
    [0.000001234, '0.000001234'],
  ])('toCanonical(%p) = %s', (x, expected) => {
    expect(toCanonical(x)).toBe(expected);
  });

  test.each([
    ['123456789', 'intl', '123,456,789'],
    ['123456789', 'indian', '12,34,56,789'],
    ['12345', 'indian', '12,345'],
    ['123', 'indian', '123'],
    ['1234567', 'none', '1234567'],
  ] as const)('groupInteger(%s, %s) = %s', (int, grouping, expected) => {
    expect(groupInteger(int, grouping)).toBe(expected);
  });

  test('display formatting', () => {
    expect(formatCanonical('-1234.5', 'intl')).toBe('−1,234.5');
    expect(formatCanonical('1.5E25', 'intl')).toBe('1.5×10²⁵');
    expect(formatCanonical('2E-12', 'intl')).toBe('2×10⁻¹²');
    expect(formatUnsigned('1234.50', 'intl')).toBe('1,234.50');
    expect(shown('1 2 3 4 5 6 7', 'indian')).toBe('12,34,567');
  });

  test('1/x wraps only the last operand', () => {
    expect(shown('2 + 8 inv')).toBe('2 + (1 ÷ 8)');
    expect(result('2 + 8 inv =')).toBe('2.125');
  });
});
