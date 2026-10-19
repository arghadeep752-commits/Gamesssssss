/**
 * Keypad definition: identity, label, style and spoken name of every key.
 */
import type { AngleMode } from '../engine';

export type KeyId =
  | '0'
  | '1'
  | '2'
  | '3'
  | '4'
  | '5'
  | '6'
  | '7'
  | '8'
  | '9'
  | 'dot'
  | 'sign'
  | 'add'
  | 'sub'
  | 'mul'
  | 'div'
  | 'eq'
  | 'ac'
  | 'back'
  | 'pct'
  | 'second'
  | 'angle'
  | 'lp'
  | 'rp'
  | 'inv'
  | 'fact'
  | 'pow'
  | 'sin'
  | 'cos'
  | 'tan'
  | 'asin'
  | 'acos'
  | 'atan'
  | 'ln'
  | 'exp'
  | 'log'
  | 'pow10'
  | 'sqrt'
  | 'cbrt'
  | 'sq'
  | 'cube'
  | 'pi'
  | 'e';

export type KeyKind = 'digit' | 'fn' | 'op' | 'eq' | 'sci';

/** Label with optional superscript after (xʸ) or before (³√). */
export interface KeyLabel {
  text: string;
  sup?: string;
  pre?: string;
  icon?: 'backspace';
}

export interface KeySpec {
  id: KeyId;
  kind: KeyKind;
  label: KeyLabel;
  a11y: string;
}

const k = (
  id: KeyId,
  kind: KeyKind,
  label: KeyLabel | string,
  a11y: string,
): KeySpec => ({
  id,
  kind,
  label: typeof label === 'string' ? { text: label } : label,
  a11y,
});

const digit = (d: KeyId) => k(d, 'digit', d, d);

export const BASIC_ROWS: KeySpec[][] = [
  [
    k('ac', 'fn', 'AC', 'Clear'),
    k('back', 'fn', { text: '', icon: 'backspace' }, 'Delete'),
    k('pct', 'fn', '%', 'Percent'),
    k('div', 'op', '÷', 'Divide'),
  ],
  [digit('7'), digit('8'), digit('9'), k('mul', 'op', '×', 'Multiply')],
  [digit('4'), digit('5'), digit('6'), k('sub', 'op', '−', 'Minus')],
  [digit('1'), digit('2'), digit('3'), k('add', 'op', '+', 'Plus')],
  [
    k('sign', 'digit', '±', 'Change sign'),
    digit('0'),
    k('dot', 'digit', '.', 'Decimal point'),
    k('eq', 'eq', '=', 'Equals'),
  ],
];

/** Scientific key for a slot, depending on the 2nd and angle states. */
function buildSciKey(
  slot: SciSlot,
  second: boolean,
  angle: AngleMode,
): KeySpec {
  switch (slot) {
    case 'second':
      return k(
        'second',
        'sci',
        '2nd',
        second ? 'Second functions on' : 'Second functions',
      );
    case 'angle':
      return k(
        'angle',
        'sci',
        angle === 'deg' ? 'DEG' : 'RAD',
        angle === 'deg'
          ? 'Degrees, switch to radians'
          : 'Radians, switch to degrees',
      );
    case 'lp':
      return k('lp', 'sci', '(', 'Open parenthesis');
    case 'rp':
      return k('rp', 'sci', ')', 'Close parenthesis');
    case 'inv':
      return k('inv', 'sci', '1/x', 'Reciprocal');
    case 'fact':
      return k('fact', 'sci', 'x!', 'Factorial');
    case 'pow':
      return k('pow', 'sci', { text: 'x', sup: 'y' }, 'Power');
    case 'sin':
      return second
        ? k('asin', 'sci', { text: 'sin', sup: '−1' }, 'Inverse sine')
        : k('sin', 'sci', 'sin', 'Sine');
    case 'cos':
      return second
        ? k('acos', 'sci', { text: 'cos', sup: '−1' }, 'Inverse cosine')
        : k('cos', 'sci', 'cos', 'Cosine');
    case 'tan':
      return second
        ? k('atan', 'sci', { text: 'tan', sup: '−1' }, 'Inverse tangent')
        : k('tan', 'sci', 'tan', 'Tangent');
    case 'ln':
      return second
        ? k('exp', 'sci', { text: 'e', sup: 'x' }, 'e to the power of')
        : k('ln', 'sci', 'ln', 'Natural logarithm');
    case 'log':
      return second
        ? k('pow10', 'sci', { text: '10', sup: 'x' }, '10 to the power of')
        : k('log', 'sci', 'log', 'Logarithm');
    case 'sqrt':
      return second
        ? k('cbrt', 'sci', { text: '√', pre: '3' }, 'Cube root')
        : k('sqrt', 'sci', '√', 'Square root');
    case 'sq':
      return second
        ? k('cube', 'sci', { text: 'x', sup: '3' }, 'Cube')
        : k('sq', 'sci', { text: 'x', sup: '2' }, 'Square');
    case 'pi':
      return second
        ? k('e', 'sci', 'e', 'Euler’s number')
        : k('pi', 'sci', 'π', 'Pi');
  }
}

export type SciSlot =
  | 'second'
  | 'angle'
  | 'lp'
  | 'rp'
  | 'inv'
  | 'sin'
  | 'cos'
  | 'tan'
  | 'pi'
  | 'fact'
  | 'ln'
  | 'log'
  | 'sqrt'
  | 'sq'
  | 'pow';

/** Portrait: three rows of five above the basic keys. */
export const SCI_PORTRAIT: SciSlot[][] = [
  ['second', 'angle', 'lp', 'rp', 'inv'],
  ['sin', 'cos', 'tan', 'pi', 'fact'],
  ['ln', 'log', 'sqrt', 'sq', 'pow'],
];

/** Landscape: five rows of three beside the basic keys. */
export const SCI_LANDSCAPE: SciSlot[][] = [
  ['second', 'angle', 'inv'],
  ['lp', 'rp', 'fact'],
  ['sin', 'cos', 'tan'],
  ['ln', 'log', 'pi'],
  ['sqrt', 'sq', 'pow'],
];

const sciCache = new Map<string, KeySpec>();

/**
 * Cached so a key keeps the same spec object between renders and its
 * memoized component only re-renders when its label really changes.
 */
export function sciKey(
  slot: SciSlot,
  second: boolean,
  angle: AngleMode,
): KeySpec {
  const id = `${slot}|${second ? 1 : 0}|${angle}`;
  let spec = sciCache.get(id);
  if (!spec) {
    spec = buildSciKey(slot, second, angle);
    sciCache.set(id, spec);
  }
  return spec;
}
