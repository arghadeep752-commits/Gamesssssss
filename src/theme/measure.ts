/**
 * Text width estimates for Geist Light with tabular figures (advance widths
 * in em, measured from the font files). Used to size the display text
 * without a layout pass.
 */
const EM: Record<string, number> = {
  ' ': 0.25,
  ',': 0.188,
  '.': 0.187,
  '+': 0.558,
  '−': 0.52,
  '×': 0.485,
  '÷': 0.533,
  '(': 0.252,
  ')': 0.252,
  '%': 0.76,
  '!': 0.198,
  '²': 0.347,
  '³': 0.33,
  π: 0.641,
  e: 0.557,
  E: 0.593,
  '^': 0.407,
  a: 0.547,
  c: 0.541,
  g: 0.586,
  i: 0.229,
  l: 0.257,
  n: 0.573,
  o: 0.565,
  r: 0.367,
  s: 0.516,
  t: 0.379,
  '√': 0.651,
  '⁰': 0.386,
  '¹': 0.23,
  '⁴': 0.324,
  '⁵': 0.342,
  '⁶': 0.363,
  '⁷': 0.295,
  '⁸': 0.347,
  '⁹': 0.363,
  '⁻': 0.4,
  '=': 0.533,
};

/** Digits (tabular) and anything unlisted are 0.6 em wide. */
export function textWidthEm(text: string, letterSpacingEm = 0): number {
  let w = 0;
  for (const ch of text) {
    w += (EM[ch] ?? 0.6) + letterSpacingEm;
  }
  return w;
}

/** Largest font size in [min, max] (2 px steps) that fits the width. */
export function fitFontSize(
  text: string,
  width: number,
  max: number,
  min: number,
  letterSpacingEm = 0,
): number {
  if (width <= 0) {
    return max;
  }
  const em = textWidthEm(text, letterSpacingEm) * 1.03 + 0.12;
  const size = Math.floor(width / em / 2) * 2;
  return Math.max(min, Math.min(max, size));
}
