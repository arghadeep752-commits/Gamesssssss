import { memo } from 'react';
import Svg, { Path, Rect } from 'react-native-svg';
import { COLORS } from '../config/theme';

/**
 * Original Arrow Flow mark: two interlocking arrows on a navy tile. The same
 * drawing is exported as the launcher icon by scripts/make-icons.mjs.
 */
export const LOGO_PATHS = {
  tile: { x: 0, y: 0, size: 64, radius: 16 },
  bodyA: 'M17 47V22h21',
  headA: 'M48 22l-9.5-6v12z',
  bodyB: 'M47 47H30V38',
  headB: 'M30 29l-6 9.5h12z',
} as const;

export const Logo = memo(function Logo({ size = 72 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 64 64" accessibilityLabel="Arrow Flow logo">
      <Rect x={0} y={0} width={64} height={64} rx={16} ry={16} fill={COLORS.ink} />
      <Path d={LOGO_PATHS.bodyA} stroke={COLORS.white} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d={LOGO_PATHS.headA} fill={COLORS.white} stroke={COLORS.white} strokeWidth={2} strokeLinejoin="round" />
      <Path d={LOGO_PATHS.bodyB} stroke={COLORS.hint} strokeWidth={5} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d={LOGO_PATHS.headB} fill={COLORS.hint} stroke={COLORS.hint} strokeWidth={2} strokeLinejoin="round" />
    </Svg>
  );
});
