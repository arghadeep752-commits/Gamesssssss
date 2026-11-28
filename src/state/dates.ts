/** Local-calendar date helpers. Keys look like 2026-11-28 and months like 2026-11. */
const pad = (n: number) => String(n).padStart(2, '0');

export function dateKey(d: Date): string {
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

export function todayKey(): string {
  return dateKey(new Date());
}

export function monthKeyOf(key: string): string {
  return key.slice(0, 7);
}

export function parseKey(key: string): Date {
  const [y, m, d] = key.split('-').map(Number);
  return new Date(y, (m || 1) - 1, d || 1);
}

export function daysInMonth(year: number, month0: number): number {
  return new Date(year, month0 + 1, 0).getDate();
}

export function addMonths(monthKey: string, delta: number): string {
  const [y, m] = monthKey.split('-').map(Number);
  const d = new Date(y, m - 1 + delta, 1);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`;
}

export const MONTHS = [
  'January',
  'February',
  'March',
  'April',
  'May',
  'June',
  'July',
  'August',
  'September',
  'October',
  'November',
  'December',
];
export const MONTHS_SHORT = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export function monthTitle(monthKey: string): string {
  const [y, m] = monthKey.split('-').map(Number);
  return `${MONTHS[m - 1]} ${y}`;
}

export function prettyDate(key: string): string {
  const d = parseKey(key);
  return `${MONTHS_SHORT[d.getMonth()]} ${d.getDate()}, ${d.getFullYear()}`;
}

/** How many days of a month count toward its trophy, and how many are done. */
export function monthProgress(monthKey: string, done: Readonly<Record<string, number>>): { total: number; done: number } {
  const [y, m] = monthKey.split('-').map(Number);
  const total = daysInMonth(y, m - 1);
  let n = 0;
  for (let d = 1; d <= total; d++) if (done[`${monthKey}-${pad(d)}`]) n++;
  return { total, done: n };
}
