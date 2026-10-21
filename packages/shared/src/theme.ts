/**
 * DevDarshan design tokens.
 *
 * Warm ivory surfaces, a deep saffron (muted bhagwa) accent used sparingly, deep
 * forest green as the secondary accent, charcoal text and a muted gold for small
 * flourishes. The admin app swaps the accents (green first) so the two apps feel
 * related but are never confused with each other.
 *
 * Contrast: every text colour on its background meets WCAG AA (4.5:1) and the
 * primary colours meet AA for white or near-black button labels.
 */

export type ColorScheme = 'light' | 'dark';
export type AppAccent = 'user' | 'admin';

export interface Palette {
  background: string;
  surface: string;
  surfaceAlt: string;
  surfaceRaised: string;
  border: string;
  borderStrong: string;
  text: string;
  textMuted: string;
  textSubtle: string;
  textInverse: string;
  primary: string;
  primaryPressed: string;
  onPrimary: string;
  primarySoft: string;
  onPrimarySoft: string;
  secondary: string;
  onSecondary: string;
  secondarySoft: string;
  onSecondarySoft: string;
  gold: string;
  goldSoft: string;
  danger: string;
  dangerSoft: string;
  success: string;
  successSoft: string;
  warning: string;
  warningSoft: string;
  overlay: string;
  scrim: string;
  skeletonBase: string;
  skeletonHighlight: string;
  tabBar: string;
  tabBarBorder: string;
  imageBackdrop: string;
  previewBackground: string;
  previewText: string;
  heart: string;
}

const saffronLight = {
  primary: '#B9581A',
  primaryPressed: '#9E4A15',
  onPrimary: '#FFFFFF',
  primarySoft: '#F8E6D3',
  onPrimarySoft: '#8A4113',
};

const greenLight = {
  primary: '#2E5B43',
  primaryPressed: '#244A36',
  onPrimary: '#FFFFFF',
  primarySoft: '#E1ECE4',
  onPrimarySoft: '#244A36',
};

const saffronDark = {
  primary: '#E3893F',
  primaryPressed: '#C9742F',
  onPrimary: '#1A120B',
  primarySoft: '#3A2617',
  onPrimarySoft: '#F0B98A',
};

const greenDark = {
  primary: '#7DB394',
  primaryPressed: '#689F80',
  onPrimary: '#0E1A13',
  primarySoft: '#1B2A21',
  onPrimarySoft: '#A9D3BA',
};

const neutralsLight = {
  background: '#FAF6EF',
  surface: '#FFFDF9',
  surfaceAlt: '#F3ECE0',
  surfaceRaised: '#FFFFFF',
  border: '#E8DFD0',
  borderStrong: '#D8CBB6',
  text: '#2A2520',
  textMuted: '#6B6157',
  textSubtle: '#8F8476',
  textInverse: '#FFFDF9',
  gold: '#A8822F',
  goldSoft: '#F2E8D0',
  danger: '#B3261E',
  dangerSoft: '#F9E3E1',
  success: '#2E7D4F',
  successSoft: '#E2F1E7',
  warning: '#A86A12',
  warningSoft: '#FBEED6',
  overlay: 'rgba(24, 20, 16, 0.55)',
  scrim: 'rgba(24, 20, 16, 0.35)',
  skeletonBase: '#EEE6D8',
  skeletonHighlight: '#F7F1E7',
  tabBar: '#FFFDF9',
  tabBarBorder: '#ECE3D4',
  imageBackdrop: '#EFE7DA',
  previewBackground: '#0F0D0B',
  previewText: '#F7F1E7',
  heart: '#C2412D',
};

const neutralsDark = {
  background: '#141210',
  surface: '#1C1916',
  surfaceAlt: '#24201C',
  surfaceRaised: '#221E1A',
  border: '#2F2A24',
  borderStrong: '#3D362E',
  text: '#F2ECE3',
  textMuted: '#B8AE9F',
  textSubtle: '#958A7C',
  textInverse: '#141210',
  gold: '#D1AE62',
  goldSoft: '#2E2618',
  danger: '#F2766B',
  dangerSoft: '#3A1D1A',
  success: '#6CC08E',
  successSoft: '#183021',
  warning: '#E2A54B',
  warningSoft: '#352812',
  overlay: 'rgba(0, 0, 0, 0.6)',
  scrim: 'rgba(0, 0, 0, 0.45)',
  skeletonBase: '#24201C',
  skeletonHighlight: '#2E2924',
  tabBar: '#1A1714',
  tabBarBorder: '#2A2520',
  imageBackdrop: '#221E1A',
  previewBackground: '#0B0A09',
  previewText: '#F7F1E7',
  heart: '#F07A64',
};

export const palettes: Readonly<Record<AppAccent, Readonly<Record<ColorScheme, Palette>>>> = {
  user: {
    light: {
      ...neutralsLight,
      ...saffronLight,
      secondary: greenLight.primary,
      onSecondary: greenLight.onPrimary,
      secondarySoft: greenLight.primarySoft,
      onSecondarySoft: greenLight.onPrimarySoft,
    },
    dark: {
      ...neutralsDark,
      ...saffronDark,
      secondary: greenDark.primary,
      onSecondary: greenDark.onPrimary,
      secondarySoft: greenDark.primarySoft,
      onSecondarySoft: greenDark.onPrimarySoft,
    },
  },
  admin: {
    light: {
      ...neutralsLight,
      ...greenLight,
      secondary: saffronLight.primary,
      onSecondary: saffronLight.onPrimary,
      secondarySoft: saffronLight.primarySoft,
      onSecondarySoft: saffronLight.onPrimarySoft,
    },
    dark: {
      ...neutralsDark,
      ...greenDark,
      secondary: saffronDark.primary,
      onSecondary: saffronDark.onPrimary,
      secondarySoft: saffronDark.primarySoft,
      onSecondarySoft: saffronDark.onPrimarySoft,
    },
  },
};

export const spacing = {
  xxs: 2,
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  xxl: 24,
  xxxl: 32,
} as const;

export const radii = {
  xs: 6,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 20,
  pill: 999,
} as const;

export type FontWeight = '400' | '500' | '600' | '700';

export interface TypeStyle {
  fontSize: number;
  lineHeight: number;
  fontWeight: FontWeight;
  letterSpacing?: number;
  /** 'serif' maps to Noto Serif on Android; undefined uses the system sans (Roboto + Noto Sans Devanagari). */
  fontFamily?: 'serif';
}

/** System fonts only (no bundled font files). Line heights leave room for Devanagari matras. */
export const typeScale = {
  brand: { fontSize: 21, lineHeight: 28, fontWeight: '600', fontFamily: 'serif', letterSpacing: 0.2 },
  display: { fontSize: 26, lineHeight: 34, fontWeight: '600', fontFamily: 'serif' },
  title: { fontSize: 20, lineHeight: 28, fontWeight: '600', fontFamily: 'serif' },
  heading: { fontSize: 17, lineHeight: 24, fontWeight: '600' },
  subheading: { fontSize: 15, lineHeight: 22, fontWeight: '600' },
  body: { fontSize: 15, lineHeight: 22, fontWeight: '400' },
  bodyStrong: { fontSize: 15, lineHeight: 22, fontWeight: '600' },
  label: { fontSize: 13, lineHeight: 18, fontWeight: '500', letterSpacing: 0.1 },
  caption: { fontSize: 12, lineHeight: 17, fontWeight: '400' },
  overline: { fontSize: 11, lineHeight: 15, fontWeight: '600', letterSpacing: 0.8 },
} as const satisfies Record<string, TypeStyle>;

export type TypeVariant = keyof typeof typeScale;

export const motion = {
  fast: 140,
  normal: 220,
  slow: 320,
} as const;
