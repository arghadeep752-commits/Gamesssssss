import { Platform, type TextStyle } from 'react-native';

/**
 * Camero Plus palette: true black for the viewfinder, warm graphite for panels and a single
 * accent taken from tungsten light (about 3200 K). Recording uses its own red.
 */
export const palette = {
  black: '#000000',
  graphite: '#151413',
  panel: '#1C1A19',
  smoke: '#262321',
  rule: '#34302D',
  ink: '#F7F5F2',
  ash: '#A39E97',
  iron: '#6E6964',
  tally: '#F0453A',
  scrim: 'rgba(0,0,0,0.42)',
  scrimStrong: 'rgba(0,0,0,0.66)',
} as const;

export const accents = {
  tungsten: { label: 'Tungsten', color: '#FFB46B' },
  daylight: { label: 'Daylight', color: '#CFE3FF' },
  sodium: { label: 'Sodium', color: '#FF9447' },
  signal: { label: 'Signal', color: '#9FE3B8' },
} as const;

export type AccentKey = keyof typeof accents;

export const fonts = {
  regular: 'Inter-Regular',
  medium: 'Inter-Medium',
  semibold: 'Inter-SemiBold',
  display: 'InterDisplay-SemiBold',
  displayMedium: 'InterDisplay-Medium',
} as const;

const numeric: TextStyle['fontVariant'] = ['tabular-nums'];

export const type = {
  title: { fontFamily: fonts.display, fontSize: 28, lineHeight: 34, letterSpacing: -0.4 },
  heading: { fontFamily: fonts.displayMedium, fontSize: 20, lineHeight: 26, letterSpacing: -0.2 },
  body: { fontFamily: fonts.regular, fontSize: 15, lineHeight: 21 },
  bodyStrong: { fontFamily: fonts.medium, fontSize: 15, lineHeight: 21 },
  label: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 17 },
  caption: { fontFamily: fonts.regular, fontSize: 12, lineHeight: 16 },
  mode: { fontFamily: fonts.medium, fontSize: 14, lineHeight: 18, letterSpacing: 0.1 },
  readout: { fontFamily: fonts.medium, fontSize: 13, lineHeight: 16, fontVariant: numeric, letterSpacing: 0.2 },
  readoutLarge: { fontFamily: fonts.semibold, fontSize: 17, lineHeight: 20, fontVariant: numeric },
  countdown: { fontFamily: fonts.displayMedium, fontSize: 96, lineHeight: 104, fontVariant: numeric },
} satisfies Record<string, TextStyle>;

export const space = { xxs: 2, xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;

export const radius = { sm: 6, md: 10, lg: 18 } as const;

export const hairline = Platform.select({ android: 0.75, default: 0.5 }) ?? 0.5;
