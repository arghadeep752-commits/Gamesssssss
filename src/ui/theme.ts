import { createContext, useContext } from 'react';

export interface Palette {
  readonly dark: boolean;
  readonly bg: string;
  readonly surface: string;
  readonly surfaceAlt: string;
  readonly border: string;
  readonly ink: string;
  readonly text: string;
  readonly sub: string;
  readonly faint: string;
  readonly dot: string;
  readonly accent: string;
  readonly accentSoft: string;
  readonly onAccent: string;
  readonly hint: string;
  readonly error: string;
  readonly heart: string;
  readonly heartEmpty: string;
  readonly success: string;
  readonly gold: string;
  readonly goldSoft: string;
  readonly scrim: string;
}

export const LIGHT: Palette = {
  dark: false,
  bg: '#F3F4F8',
  surface: '#FFFFFF',
  surfaceAlt: '#E9EBF2',
  border: '#DDE0E9',
  ink: '#1B2233',
  text: '#1B2233',
  sub: '#6B7385',
  faint: '#A3AABA',
  dot: '#C6CBD7',
  accent: '#3B6CF6',
  accentSoft: '#DCE5FE',
  onAccent: '#FFFFFF',
  hint: '#3B6CF6',
  error: '#EE4537',
  heart: '#EE4537',
  heartEmpty: '#D7DAE3',
  success: '#1FAF6B',
  gold: '#F2B01E',
  goldSoft: '#FCEFC9',
  scrim: 'rgba(15,19,30,0.45)',
};

export const DARK: Palette = {
  dark: true,
  bg: '#0F1218',
  surface: '#191D26',
  surfaceAlt: '#232835',
  border: '#2C3242',
  ink: '#E9ECF3',
  text: '#E9ECF3',
  sub: '#9098AB',
  faint: '#5D6577',
  dot: '#3A4152',
  accent: '#5C86FF',
  accentSoft: '#22305A',
  onAccent: '#FFFFFF',
  hint: '#6E95FF',
  error: '#FF5A4C',
  heart: '#FF5A4C',
  heartEmpty: '#363C4C',
  success: '#2CC27C',
  gold: '#F5BD3A',
  goldSoft: '#3D3420',
  scrim: 'rgba(0,0,0,0.6)',
};

export const ThemeContext = createContext<Palette>(LIGHT);

export function useTheme(): Palette {
  return useContext(ThemeContext);
}

export const RADIUS = { sm: 10, md: 16, lg: 22, xl: 28, pill: 999 } as const;
export const SPACE = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24, xxl: 32 } as const;
