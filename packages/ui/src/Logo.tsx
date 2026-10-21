import { memo } from 'react';
import Svg, { Circle, Path } from 'react-native-svg';

/**
 * The DevDarshan mark: a diya glowing inside a temple doorway (the "darshan"
 * glimpse of the divine). Shared geometry with the generated app icons
 * (scripts/assets/brand.mjs).
 */
export const LOGO_PATHS = {
  arch: 'M15 56 V31 C15 23.5 21 19 26 15.5 C29.2 13.2 31 10.5 32 7 C33 10.5 34.8 13.2 38 15.5 C43 19 49 23.5 49 31 V56',
  base: 'M10 56 H54',
  bowl: 'M21 45 H43 C42 50.5 37.5 53 32 53 C26.5 53 22 50.5 21 45 Z',
  flame: 'M32 26.5 C35.9 30.9 37.2 34.4 37.2 37.3 C37.2 40.4 34.9 42.7 32 42.7 C29.1 42.7 26.8 40.4 26.8 37.3 C26.8 34.4 28.1 30.9 32 26.5 Z',
  innerFlame: 'M32 32.6 C33.7 34.7 34.3 36.3 34.3 37.7 C34.3 39.1 33.3 40.2 32 40.2 C30.7 40.2 29.7 39.1 29.7 37.7 C29.7 36.3 30.3 34.7 32 32.6 Z',
} as const;

export interface LogoProps {
  size?: number;
  archColor: string;
  flameColor: string;
  flameCoreColor: string;
}

export const Logo = memo(function Logo({ size = 40, archColor, flameColor, flameCoreColor }: LogoProps) {
  return (
    <Svg width={size} height={size} viewBox="0 0 64 64" accessibilityLabel="DevDarshan">
      <Path d={LOGO_PATHS.arch} fill="none" stroke={archColor} strokeWidth={3.2} strokeLinecap="round" strokeLinejoin="round" />
      <Path d={LOGO_PATHS.base} fill="none" stroke={archColor} strokeWidth={3.2} strokeLinecap="round" />
      <Circle cx={32} cy={4.6} r={1.9} fill={archColor} />
      <Path d={LOGO_PATHS.flame} fill={flameColor} />
      <Path d={LOGO_PATHS.innerFlame} fill={flameCoreColor} />
      <Path d={LOGO_PATHS.bowl} fill={archColor} />
    </Svg>
  );
});
