/**
 * Number formatting for display.
 *
 * "Canonical" strings are what the engine stores and re-parses: plain ASCII,
 * up to 15 significant digits, no grouping, "E" for exponents
 * (e.g. "-1234.5", "1.5E25", "2E-12").
 *
 * Display strings use a true minus sign, digit grouping and ×10ⁿ notation.
 */

export type Grouping = 'intl' | 'indian' | 'none';

const MINUS = '−';
const SUPERSCRIPT: Record<string, string> = {
  '0': '⁰',
  '1': '¹',
  '2': '²',
  '3': '³',
  '4': '⁴',
  '5': '⁵',
  '6': '⁶',
  '7': '⁷',
  '8': '⁸',
  '9': '⁹',
  '-': '⁻',
};

function trimZeros(s: string): string {
  if (!s.includes('.')) {
    return s;
  }
  return s.replace(/0+$/, '').replace(/\.$/, '');
}

/** Up to 15 significant digits; exponent form for very large/small values. */
export function toCanonical(x: number): string {
  if (x === 0 || Object.is(x, -0)) {
    return '0';
  }
  const abs = Math.abs(x);
  if (abs >= 1e15 || abs < 1e-9) {
    const [m, e] = x.toExponential(14).split('e');
    return `${trimZeros(m)}E${parseInt(e, 10)}`;
  }
  const digitsBefore = Math.floor(Math.log10(abs)) + 1;
  const decimals = Math.min(20, Math.max(0, 15 - digitsBefore));
  const s = trimZeros(x.toFixed(decimals));
  return s === '-0' ? '0' : s;
}

export function groupInteger(int: string, grouping: Grouping): string {
  if (grouping === 'none' || int.length <= 3) {
    return int;
  }
  if (grouping === 'intl') {
    return int.replace(/\B(?=(\d{3})+(?!\d))/g, ',');
  }
  // Indian: last three digits, then pairs (12,34,567)
  const head = int.slice(0, -3);
  const tail = int.slice(-3);
  return `${head.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${tail}`;
}

function superscript(exp: string): string {
  return exp
    .split('')
    .map(c => SUPERSCRIPT[c] ?? c)
    .join('');
}

/**
 * Formats an unsigned number string as typed or stored ("1234.50", "1.5E-7")
 * with grouping and ×10ⁿ notation. Keeps typed trailing zeros and points.
 */
export function formatUnsigned(v: string, grouping: Grouping): string {
  const [mantissa, exp] = v.split('E');
  const dot = mantissa.indexOf('.');
  const int = dot === -1 ? mantissa : mantissa.slice(0, dot);
  const frac = dot === -1 ? '' : mantissa.slice(dot);
  let out = groupInteger(int, grouping) + frac;
  if (exp !== undefined) {
    out += exp === '' || exp === '-' ? 'E' + exp : `×10${superscript(exp)}`;
  }
  return out;
}

/** Display string for a canonical value ("-1234.5" -> "−1,234.5"). */
export function formatCanonical(canonical: string, grouping: Grouping): string {
  const negative = canonical.startsWith('-');
  const body = formatUnsigned(
    negative ? canonical.slice(1) : canonical,
    grouping,
  );
  return negative ? MINUS + body : body;
}

export function formatNumber(x: number, grouping: Grouping): string {
  return formatCanonical(toCanonical(x), grouping);
}

/** Plain text for the clipboard: no grouping, ASCII exponent. */
export function plainText(canonical: string): string {
  return canonical.replace('E', 'e');
}
