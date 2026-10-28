import { Platform } from 'react-native';

export const COLORS = {
  background: '#F5F6FA',
  surface: '#FFFFFF',
  surfaceAlt: '#EEF0F6',
  border: '#E1E5EF',
  ink: '#12204A',
  inkSoft: '#56617F',
  muted: '#98A1B8',
  dot: '#C8CEDD',
  arrow: '#14244F',
  hint: '#0E9F87',
  hintSoft: '#D6F3EE',
  error: '#E2484D',
  errorSoft: '#FBE1E2',
  blocker: '#EE8A1E',
  star: '#F4B230',
  starEmpty: '#DCE0EA',
  heart: '#E2484D',
  heartEmpty: '#DCE0EA',
  overlay: 'rgba(14, 22, 48, 0.42)',
  white: '#FFFFFF',
} as const;

export const TIER_COLORS = {
  tutorial: '#5B8DEF',
  easy: '#15A37F',
  normal: '#3F6AD8',
  hard: '#C9761A',
  expert: '#C2414B',
} as const;

export const SPACE = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
export const RADIUS = { sm: 8, md: 14, lg: 20, pill: 999 } as const;

export const FONT = {
  family: Platform.select({ android: 'sans-serif', default: undefined }),
  medium: Platform.select({ android: 'sans-serif-medium', default: undefined }),
} as const;

export const TYPE = {
  display: { fontSize: 34, fontWeight: '800' as const, color: COLORS.ink, letterSpacing: -0.5 },
  title: { fontSize: 22, fontWeight: '700' as const, color: COLORS.ink },
  heading: { fontSize: 17, fontWeight: '700' as const, color: COLORS.ink },
  body: { fontSize: 15, fontWeight: '400' as const, color: COLORS.ink, lineHeight: 22 },
  label: { fontSize: 13, fontWeight: '600' as const, color: COLORS.inkSoft },
  caption: { fontSize: 12, fontWeight: '500' as const, color: COLORS.muted },
} as const;

/** Minimum comfortable touch size (dp). */
export const TOUCH = 44;
