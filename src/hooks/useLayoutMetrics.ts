/**
 * Sizes the keypad from the window so keys stay large on phones, compact on
 * small screens and never stretch on tablets. The display and the history
 * card get whatever height is left.
 *
 * The result is memoized: the same object comes back until the window, the
 * insets or the scientific switch change, so memoized keypads skip
 * re-rendering on every key press.
 */
import { useMemo } from 'react';
import { useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

interface Insets {
  top: number;
  bottom: number;
  left: number;
  right: number;
}

export interface Metrics {
  landscape: boolean;
  width: number;
  height: number;
  contentWidth: number;
  pad: number;
  topBar: number;
  // basic keys
  keyW: number;
  keyH: number;
  gap: number;
  digitFont: number;
  opFont: number;
  fnFont: number;
  // scientific keys
  sciW: number;
  sciH: number;
  sciGap: number;
  sciFont: number;
  /** Space between the scientific block and the basic keys. */
  blockGap: number;
  /** Height of the open scientific block in portrait, including the gap. */
  sciBlock: number;
  /** Largest expression font that fits the space above the keys. */
  displayFont: number;
  /** False on screens too short for the history card. */
  showHistory: boolean;
  /** Height of everything below the display (keys plus bottom padding). */
  keypadHeight: number;
}

const clamp = (v: number, lo: number, hi: number) =>
  Math.max(lo, Math.min(hi, v));

/** Indicator row, result line and padding around the expression. */
const DISPLAY_CHROME = 84;
const HISTORY_MIN = 68;
const MIN_FONT = 30;
const LINE = 1.18;

/** Bottom padding under the keys. */
export const KEYPAD_PAD = 14;

export function useLayoutMetrics(sciOpen: boolean): Metrics {
  const { width, height } = useWindowDimensions();
  const { top, bottom, left, right } = useSafeAreaInsets();
  return useMemo(
    () => computeMetrics(width, height, { top, bottom, left, right }, sciOpen),
    [width, height, top, bottom, left, right, sciOpen],
  );
}

export function computeMetrics(
  width: number,
  height: number,
  insets: Insets,
  sciOpen: boolean,
): Metrics {
  const innerW = width - insets.left - insets.right;
  const innerH = height - insets.top - insets.bottom;
  const landscape = innerW > innerH * 1.05;

  if (landscape) {
    const contentWidth = Math.min(innerW, 980);
    const pad = 18;
    const gap = 9;
    const blockGap = 16;
    const topBar = 48;
    const display = clamp(innerH * 0.24, 72, 140);
    const colW = (contentWidth - pad * 2 - blockGap - gap * 5) / 7;
    const keyH = clamp(
      (innerH - topBar - display - KEYPAD_PAD - gap * 4) / 5,
      30,
      colW * 0.8,
    );
    const digitFont = clamp(keyH * 0.46, 16, 28);
    const spare = innerH - topBar - KEYPAD_PAD - (keyH * 5 + gap * 4);
    return {
      landscape,
      width,
      height,
      contentWidth,
      pad,
      topBar,
      keyW: colW,
      keyH,
      gap,
      digitFont,
      opFont: digitFont * 1.15,
      fnFont: digitFont * 0.72,
      sciW: colW,
      sciH: keyH,
      sciGap: gap,
      sciFont: clamp(keyH * 0.38, 13, 18),
      blockGap,
      sciBlock: 0,
      displayFont: clamp((spare - 60) / LINE, 22, 46),
      showHistory: false,
      keypadHeight: keyH * 5 + gap * 4 + KEYPAD_PAD,
    };
  }

  const contentWidth = Math.min(innerW, 560);
  const pad = 18;
  const topBar = 60;
  let gap = 12;
  let sciGap = 9;
  let blockGap = 14;
  const keyW = (contentWidth - pad * 2 - gap * 3) / 4;
  const sciW = (contentWidth - pad * 2 - sciGap * 4) / 5;
  let keyH = clamp(keyW * 0.84, 54, 84);
  let sciH = clamp(keyH * 0.58, 36, 48);

  const available = innerH - topBar - KEYPAD_PAD;
  const keys = () =>
    keyH * 5 + gap * 4 + (sciOpen ? sciH * 3 + sciGap * 2 + blockGap : 0);
  // Room the display and history need at the very least.
  const minAbove = DISPLAY_CHROME + MIN_FONT * LINE + HISTORY_MIN;
  if (keys() + minAbove > available) {
    const scale = clamp((available - minAbove) / keys(), 0.6, 1);
    keyH = Math.max(40, keyH * scale);
    sciH = Math.max(28, sciH * scale);
    gap = Math.max(8, gap * scale);
    sciGap = Math.max(6, sciGap * scale);
    blockGap = Math.max(8, blockGap * scale);
  }

  const spare = available - keys() - DISPLAY_CHROME;
  const showHistory = spare - MIN_FONT * LINE >= HISTORY_MIN;
  const cap = sciOpen ? 54 : 66;
  const displayFont = clamp(
    (spare - (showHistory ? HISTORY_MIN : 0)) / LINE,
    MIN_FONT,
    cap,
  );

  const digitFont = clamp(keyH * 0.42, 20, 33);
  return {
    landscape,
    width,
    height,
    contentWidth,
    pad,
    topBar,
    keyW,
    keyH,
    gap,
    digitFont,
    opFont: digitFont * 1.18,
    fnFont: digitFont * 0.68,
    sciW,
    sciH,
    sciGap,
    sciFont: clamp(sciH * 0.42, 13, 18),
    blockGap,
    sciBlock: sciH * 3 + sciGap * 2 + blockGap,
    displayFont,
    showHistory,
    keypadHeight: keys() + KEYPAD_PAD,
  };
}
