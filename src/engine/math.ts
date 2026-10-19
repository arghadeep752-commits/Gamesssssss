/**
 * Numeric helpers: error type, precision control, gamma, trigonometry.
 */

export type CalcErrorCode = 'syntax' | 'div0' | 'domain' | 'overflow';

export class CalcError extends Error {
  code: CalcErrorCode;
  constructor(code: CalcErrorCode) {
    super(code);
    this.code = code;
    this.name = 'CalcError';
  }
}

export type AngleMode = 'deg' | 'rad';

/**
 * Rounds to 16 significant digits. Applied after every operation so binary
 * floating point noise (0.1 + 0.2 = 0.30000000000000004) never accumulates,
 * while values that need 16 digits to round-trip (1/3, π) stay exact.
 */
export function round16(x: number): number {
  if (x === 0 || !Number.isFinite(x)) {
    return x === 0 ? 0 : x;
  }
  return Number(x.toPrecision(16));
}

/** Validates a result and applies precision control. */
export function check(x: number): number {
  if (Number.isNaN(x)) {
    throw new CalcError('domain');
  }
  if (!Number.isFinite(x)) {
    throw new CalcError('overflow');
  }
  return round16(x);
}

/** Addition/subtraction that cancels to exactly zero when only noise is left. */
export function addSafe(a: number, b: number): number {
  const r = a + b;
  const scale = Math.max(Math.abs(a), Math.abs(b));
  if (scale > 0 && Math.abs(r) < scale * 2e-15) {
    return 0;
  }
  return check(r);
}

// Lanczos approximation (g = 607/128, 15 terms), accurate to about 1e-15.
const LANCZOS_G = 607 / 128;
const LANCZOS = [
  0.99999999999999709182, 57.156235665862923517, -59.597960355475491248,
  14.136097974741747174, -0.49191381609762019978, 0.33994649984811888699e-4,
  0.46523628927048575665e-4, -0.98374475304879564677e-4,
  0.15808870322491248884e-3, -0.21026444172410488319e-3,
  0.2174396181152126432e-3, -0.16431810653676389022e-3,
  0.84418223983852743293e-4, -0.2619083840158140867e-4,
  0.36899182659531622704e-5,
];

export function gamma(z: number): number {
  if (z < 0.5) {
    // Reflection formula
    return Math.PI / (Math.sin(Math.PI * z) * gamma(1 - z));
  }
  const x0 = z - 1;
  let x = LANCZOS[0];
  for (let i = 1; i < LANCZOS.length; i++) {
    x += LANCZOS[i] / (x0 + i);
  }
  const t = x0 + LANCZOS_G + 0.5;
  // t^(x0+0.5) is split in two so large arguments do not overflow early.
  const half = Math.pow(t, (x0 + 0.5) / 2);
  return Math.sqrt(2 * Math.PI) * half * (Math.exp(-t) * half) * x;
}

export function factorial(n: number): number {
  if (Number.isInteger(n)) {
    if (n < 0) {
      throw new CalcError('domain');
    }
    if (n > 170) {
      throw new CalcError('overflow');
    }
    let r = 1;
    for (let i = 2; i <= n; i++) {
      r *= i;
    }
    return r;
  }
  if (n > 171.6) {
    throw new CalcError('overflow');
  }
  return check(gamma(n + 1));
}

export function power(a: number, b: number): number {
  if (a === 0 && b < 0) {
    throw new CalcError('div0');
  }
  let r = Math.pow(a, b);
  if (Number.isNaN(r) && a < 0) {
    // Real odd roots of negative numbers, e.g. (-8)^(1/3) = -2
    const inv = 1 / b;
    const n = Math.round(inv);
    if (Math.abs(inv - n) < 1e-9 && Math.abs(n) % 2 === 1) {
      r = -Math.pow(-a, b);
    }
  }
  return check(r);
}

const DEG = Math.PI / 180;

function snapTiny(result: number, input: number): number {
  return Math.abs(input) > 1e-10 && Math.abs(result) < 1e-15 ? 0 : result;
}

/** Exact values at multiples of 90° so sin(180°) is 0, not 1.2e-16. */
function exactQuadrant(
  fn: 'sin' | 'cos' | 'tan',
  degrees: number,
): number | null {
  const r = ((degrees % 360) + 360) % 360;
  if (!Number.isInteger(r) || r % 90 !== 0) {
    return null;
  }
  const q = r / 90; // 0..3
  if (fn === 'sin') {
    return [0, 1, 0, -1][q];
  }
  if (fn === 'cos') {
    return [1, 0, -1, 0][q];
  }
  if (q === 1 || q === 3) {
    throw new CalcError('domain');
  }
  return 0;
}

export function trig(
  fn: 'sin' | 'cos' | 'tan',
  x: number,
  angle: AngleMode,
): number {
  if (angle === 'deg') {
    const exact = exactQuadrant(fn, x);
    if (exact !== null) {
      return exact;
    }
  }
  const rad = angle === 'deg' ? x * DEG : x;
  const r =
    fn === 'sin' ? Math.sin(rad) : fn === 'cos' ? Math.cos(rad) : Math.tan(rad);
  return check(snapTiny(r, x));
}

export function inverseTrig(
  fn: 'asin' | 'acos' | 'atan',
  x: number,
  angle: AngleMode,
): number {
  if ((fn === 'asin' || fn === 'acos') && (x < -1 || x > 1)) {
    throw new CalcError('domain');
  }
  const r =
    fn === 'asin' ? Math.asin(x) : fn === 'acos' ? Math.acos(x) : Math.atan(x);
  return check(angle === 'deg' ? r / DEG : r);
}
