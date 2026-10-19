/**
 * Liquid glass design tokens.
 *
 * Every screen sits on soft pools of colored light. Keys and
 * panels are frosted glass on top of them, and anything "active" (the
 * pending operator, the 2nd key, the f(x) switch) fills with liquid in the
 * theme's accent color.
 */
import React, { createContext, useContext } from 'react';

export type ThemeId = 'lagoon' | 'ember' | 'orchid' | 'graphite';
export type Scheme = 'light' | 'dark';

interface Seed {
  base: string;
  pools: [string, string, string, string];
  poolOpacity: number;
  accent: string;
  accent2: string;
  /** Text on the accent liquid. */
  accentInk: string;
}

interface ThemeSeed {
  name: string;
  dark: Seed;
  light: Seed;
}

export const THEMES: Record<ThemeId, ThemeSeed> = {
  lagoon: {
    name: 'Lagoon',
    dark: {
      base: '#04111A',
      pools: ['#0C8C8C', '#1A4FC4', '#0A5A6E', '#3FB6D8'],
      poolOpacity: 0.62,
      accent: '#52E5D3',
      accent2: '#4C97FF',
      accentInk: '#032421',
    },
    light: {
      base: '#E4EFF1',
      pools: ['#7FDCD2', '#A8C3FF', '#BDEFE6', '#FFD6C4'],
      poolOpacity: 0.78,
      accent: '#0E9C93',
      accent2: '#2F78E8',
      accentInk: '#FFFFFF',
    },
  },
  ember: {
    name: 'Ember',
    dark: {
      base: '#140708',
      pools: ['#A8231C', '#E8681A', '#651A2A', '#F59E4C'],
      poolOpacity: 0.58,
      accent: '#FF9A5C',
      accent2: '#FF527E',
      accentInk: '#2B0A00',
    },
    light: {
      base: '#F6EBE6',
      pools: ['#FFAE96', '#FFD49E', '#F6A3B7', '#FFE6CF'],
      poolOpacity: 0.78,
      accent: '#D9531F',
      accent2: '#DB3A6A',
      accentInk: '#FFFFFF',
    },
  },
  orchid: {
    name: 'Orchid',
    dark: {
      base: '#0C0815',
      pools: ['#6532CC', '#B12A86', '#33278F', '#D383D0'],
      poolOpacity: 0.6,
      accent: '#D7AEFF',
      accent2: '#FF8BD5',
      accentInk: '#22093A',
    },
    light: {
      base: '#F0EBF7',
      pools: ['#D2B6FF', '#FFC1E3', '#B8C2FF', '#F4D8FF'],
      poolOpacity: 0.8,
      accent: '#8446DB',
      accent2: '#D23E8B',
      accentInk: '#FFFFFF',
    },
  },
  graphite: {
    name: 'Graphite',
    dark: {
      base: '#0A0B0D',
      pools: ['#3A414B', '#566170', '#22262C', '#8995A5'],
      poolOpacity: 0.55,
      accent: '#F1F3F5',
      accent2: '#B6C0CB',
      accentInk: '#0B0C0E',
    },
    light: {
      base: '#ECEEF1',
      pools: ['#C6CDD5', '#DCE0E5', '#B3BBC5', '#F6F7F8'],
      poolOpacity: 0.85,
      accent: '#1B1F24',
      accent2: '#4B545F',
      accentInk: '#FFFFFF',
    },
  },
};

export const THEME_ORDER: ThemeId[] = ['lagoon', 'ember', 'orchid', 'graphite'];

export interface Palette {
  id: ThemeId;
  scheme: Scheme;
  base: string;
  pools: string[];
  poolOpacity: number;
  ink: string;
  inkMuted: string;
  inkFaint: string;
  accent: string;
  accent2: string;
  accentInk: string;
  /** Accent used as text on glass (operator symbols). */
  accentText: string;
  /** Gradient used for the "=" key and theme swatches. */
  liquidGradient: string;
  /** Vertical gradient for rising liquid; starts exactly at `accent` so it meets the wave crest without a seam. */
  liquidColumn: string;
  /**
   * Glass fills. Each is a single gradient layer: the translucent tint with
   * the top-light sheen already composited in, so a key paints once instead
   * of twice (fill rate is what low-end GPUs run out of first).
   */
  glassDigit: string;
  glassFn: string;
  glassOp: string;
  glassSci: string;
  glassBorder: string;
  /** Top-light sheen, for surfaces that layer it over their own fill. */
  sheen: string;
  /** Overlay shown while a key is pressed. */
  pressGlow: string;
  eqShadow: string;
  /** History card fill (single layer, like the glass fills). */
  card: string;
  cardBorder: string;
  /** Opaque settings sheet color, and the same with the sheen baked in. */
  sheet: string;
  sheetFill: string;
  sheetBorder: string;
  backdrop: string;
  segment: string;
  segmentOn: string;
  divider: string;
  toast: string;
  toastText: string;
  danger: string;
}

export function hexToRgb(hex: string): [number, number, number] {
  const h = hex.replace('#', '');
  const n = parseInt(
    h.length === 3
      ? h
          .split('')
          .map(c => c + c)
          .join('')
      : h,
    16,
  );
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export function alpha(hex: string, a: number): string {
  const [r, g, b] = hexToRgb(hex);
  return `rgba(${r}, ${g}, ${b}, ${a})`;
}

/** Linear mix of two hex colors, t = 0 gives a, t = 1 gives b. */
export function mix(a: string, b: string, t: number): string {
  const ca = hexToRgb(a);
  const cb = hexToRgb(b);
  const c = ca.map((v, i) => Math.round(v + (cb[i] - v) * t));
  return `#${c.map(v => v.toString(16).padStart(2, '0')).join('')}`;
}

/** Sheen as [position %, white alpha] stops, top to bottom. */
type SheenStops = ReadonlyArray<readonly [number, number]>;

const SHEEN_DARK: SheenStops = [
  [0, 0.13],
  [50, 0.02],
  [100, 0.05],
];
const SHEEN_LIGHT: SheenStops = [
  [0, 0.5],
  [55, 0],
  [100, 0],
];

const round3 = (v: number) => Math.round(v * 1000) / 1000;

function sheenGradient(stops: SheenStops): string {
  const parts = stops.map(([at, a]) => `rgba(255, 255, 255, ${a}) ${at}%`);
  return `linear-gradient(180deg, ${parts.join(', ')})`;
}

/**
 * One gradient equal to the white sheen painted over a fill of `color` at
 * `fillAlpha` (source-over at every stop), so the pair costs a single layer.
 */
export function glassFill(
  color: string,
  fillAlpha: number,
  stops: SheenStops,
): string {
  const rgb = hexToRgb(color);
  const parts = stops.map(([at, sheen]) => {
    const a = sheen + fillAlpha * (1 - sheen);
    // Share of the fill color in the result; the rest is the white sheen.
    const k = a === 0 ? 1 : (fillAlpha * (1 - sheen)) / a;
    const [r, g, b] = rgb.map(c => Math.round(255 + (c - 255) * k));
    return `rgba(${r}, ${g}, ${b}, ${round3(a)}) ${at}%`;
  });
  return `linear-gradient(180deg, ${parts.join(', ')})`;
}

export function buildPalette(id: ThemeId, scheme: Scheme): Palette {
  const s = THEMES[id][scheme];
  const liquidGradient = `linear-gradient(135deg, ${s.accent} 0%, ${s.accent2} 100%)`;
  const liquidColumn = `linear-gradient(180deg, ${s.accent} 0%, ${s.accent2} 100%)`;
  if (scheme === 'dark') {
    const sheet = mix(s.base, '#26313B', 0.6);
    return {
      id,
      scheme,
      base: s.base,
      pools: s.pools,
      poolOpacity: s.poolOpacity,
      ink: '#F3F6F8',
      inkMuted: 'rgba(243, 246, 248, 0.64)',
      inkFaint: 'rgba(243, 246, 248, 0.38)',
      accent: s.accent,
      accent2: s.accent2,
      accentInk: s.accentInk,
      accentText: s.accent,
      liquidGradient,
      liquidColumn,
      glassDigit: glassFill('#FFFFFF', 0.075, SHEEN_DARK),
      glassFn: glassFill('#FFFFFF', 0.17, SHEEN_DARK),
      glassOp: glassFill(s.accent, 0.15, SHEEN_DARK),
      glassSci: glassFill('#FFFFFF', 0.055, SHEEN_DARK),
      glassBorder: 'rgba(255, 255, 255, 0.13)',
      sheen: sheenGradient(SHEEN_DARK),
      pressGlow: 'rgba(255, 255, 255, 0.14)',
      eqShadow: `0px 12px 26px -12px ${alpha(s.accent2, 0.7)}`,
      card: glassFill('#FFFFFF', 0.045, SHEEN_DARK),
      cardBorder: 'rgba(255, 255, 255, 0.09)',
      sheet,
      sheetFill: glassFill(sheet, 1, SHEEN_DARK),
      sheetBorder: 'rgba(255, 255, 255, 0.10)',
      backdrop: 'rgba(0, 0, 0, 0.5)',
      segment: 'rgba(255, 255, 255, 0.06)',
      segmentOn: 'rgba(255, 255, 255, 0.16)',
      divider: 'rgba(255, 255, 255, 0.08)',
      toast: alpha(mix(s.base, '#3A4652', 0.6), 0.96),
      toastText: '#F3F6F8',
      danger: '#FF8A80',
    };
  }
  const sheet = mix(s.base, '#FFFFFF', 0.72);
  return {
    id,
    scheme,
    base: s.base,
    pools: s.pools,
    poolOpacity: s.poolOpacity,
    ink: '#0E1820',
    inkMuted: 'rgba(14, 24, 32, 0.6)',
    inkFaint: 'rgba(14, 24, 32, 0.36)',
    accent: s.accent,
    accent2: s.accent2,
    accentInk: s.accentInk,
    accentText: mix(s.accent, '#000000', 0.12),
    liquidGradient,
    liquidColumn,
    glassDigit: glassFill('#FFFFFF', 0.62, SHEEN_LIGHT),
    glassFn: glassFill('#FFFFFF', 0.32, SHEEN_LIGHT),
    glassOp: glassFill(s.accent, 0.12, SHEEN_LIGHT),
    glassSci: glassFill('#FFFFFF', 0.42, SHEEN_LIGHT),
    glassBorder: 'rgba(255, 255, 255, 0.9)',
    sheen: sheenGradient(SHEEN_LIGHT),
    pressGlow: 'rgba(14, 24, 32, 0.07)',
    eqShadow: `0px 12px 24px -12px ${alpha(s.accent, 0.5)}`,
    card: glassFill('#FFFFFF', 0.36, SHEEN_LIGHT),
    cardBorder: 'rgba(255, 255, 255, 0.75)',
    sheet,
    sheetFill: glassFill(sheet, 1, SHEEN_LIGHT),
    sheetBorder: 'rgba(255, 255, 255, 0.9)',
    backdrop: 'rgba(10, 20, 28, 0.32)',
    segment: 'rgba(14, 24, 32, 0.06)',
    segmentOn: '#FFFFFF',
    divider: 'rgba(14, 24, 32, 0.08)',
    toast: 'rgba(255, 255, 255, 0.96)',
    toastText: '#0E1820',
    danger: '#C4362C',
  };
}

/**
 * Font files live in android/app/src/main/assets/fonts
 * (Geist by Vercel, SIL Open Font License 1.1).
 */
export const fonts = {
  light: 'Geist-Light',
  regular: 'Geist-Regular',
  medium: 'Geist-Medium',
  semibold: 'Geist-SemiBold',
};

const ThemeContext = createContext<Palette>(buildPalette('lagoon', 'dark'));

export function ThemeProvider({
  palette,
  children,
}: {
  palette: Palette;
  children: React.ReactNode;
}) {
  return (
    <ThemeContext.Provider value={palette}>{children}</ThemeContext.Provider>
  );
}

export function usePalette(): Palette {
  return useContext(ThemeContext);
}
