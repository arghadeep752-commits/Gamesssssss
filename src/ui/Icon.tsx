import { memo } from 'react';
import Svg, { Circle, Path } from 'react-native-svg';

/** Original line icons on a 24-unit grid; one Path per icon keeps them light. */
export const ICON_PATHS = {
  back: 'M15 18l-6-6 6-6',
  chevronLeft: 'M14.5 6l-6 6 6 6',
  chevronRight: 'M9.5 6l6 6-6 6',
  heart:
    'M12 20.5s-7.4-4.5-9.4-9C1.2 8.2 3.2 4.6 6.7 4.6c2.1 0 3.6 1.2 5.3 3.1 1.7-1.9 3.2-3.1 5.3-3.1 3.5 0 5.5 3.6 4.1 6.9-2 4.5-9.4 9-9.4 9z',
  bulb: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2v.2h5.2v-.2c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z',
  restart: 'M3.5 12a8.5 8.5 0 1 0 2.6-6.1M3.5 3.5v5h5',
  home: 'M3.5 11L12 4l8.5 7M6 9.5V20h12V9.5',
  calendar: 'M4 6h16v14H4zM4 10.5h16M8.5 3v5M15.5 3v5',
  trophy: 'M8 4h8v5a4 4 0 0 1-8 0zM8 6H5.2a3 3 0 0 0 3 4M16 6h2.8a3 3 0 0 1-3 4M12 13v4M8.5 20.5h7M10 17h4v3.5h-4z',
  gear:
    'M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6zM19.2 13.2l1.7 1.3-1.9 3.3-2-.8c-.5.4-1.1.8-1.8 1l-.3 2.1h-3.8l-.3-2.1c-.7-.2-1.3-.6-1.8-1l-2 .8-1.9-3.3 1.7-1.3a7 7 0 0 1 0-2.4L3.1 9.5 5 6.2l2 .8c.5-.4 1.1-.8 1.8-1l.3-2.1h3.8l.3 2.1c.7.2 1.3.6 1.8 1l2-.8 1.9 3.3-1.7 1.3a7 7 0 0 1 0 2.4z',
  lock: 'M6.5 11h11v9h-11zM8.5 11V8.3a3.5 3.5 0 0 1 7 0V11',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  close: 'M6 6l12 12M18 6L6 18',
  help: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.6 9.4a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1.1.9-1.1 1.6v.6M12 16.9v.2',
  trash: 'M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13',
  play: 'M8 5.2v13.6L19 12z',
  star: 'M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4-4.7-4.4 6.4-.8z',
  sound: 'M4 9.5h3.5L12 5.5v13l-4.5-4H4zM15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11',
  music: 'M9 18.5V6l10-2.5v12.5M9 18.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zM19 16a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z',
  vibrate: 'M8.5 4h7v16h-7zM4.5 8.5v7M19.5 8.5v7',
  moon: 'M20 14.6A8.2 8.2 0 0 1 9.4 4a8.2 8.2 0 1 0 10.6 10.6z',
  flame: 'M12 3c.9 3 4.5 5 4.5 9.5a4.5 4.5 0 0 1-9 0c0-2.2 1.1-3.6 2.2-4.5.1 2 .9 3 2 3.2-.4-3 .1-5.5.3-8.2z',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z',
  plus: 'M12 5v14M5 12h14',
  minus: 'M5 12h14',
  grid: 'M9 4v16M15 4v16M4 9h16M4 15h16',
  timer: 'M12 21a8 8 0 1 0 0-16 8 8 0 0 0 0 16zM12 9v4.5l3 1.8M9.5 2.5h5',
  arrowUR: 'M7 17L17 7M9 7h8v8',
  chest: 'M3 10h18v10H3zM3 10l2.2-5h13.6L21 10M10 13.5h4',
  palette:
    'M12 3a9 9 0 0 0 0 18c1.2 0 2-.8 2-1.8 0-.5-.2-.9-.5-1.2-.3-.3-.5-.7-.5-1.2 0-1 .8-1.8 1.8-1.8H17a4 4 0 0 0 4-4c0-4.4-4-8-9-8zM7.5 12.2v.1M10.5 8v.1M15 8v.1',
  shield: 'M12 3l7 3v5.8c0 4.4-3 7.6-7 9.2-4-1.6-7-4.8-7-9.2V6z',
  doc: 'M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v6M12 7.6v.2',
  shapes: 'M4 4h7v7H4zM13 13h7v7h-7zM16.5 3.5l4 6.5h-8zM7.5 13a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7z',
  mail: 'M3 6h18v12H3zM3 6.5l9 7 9-7',
  thin: 'M4 7h16M4 12h16M4 17h16',
} as const;

export type IconName = keyof typeof ICON_PATHS;

const FILLABLE: ReadonlySet<IconName> = new Set<IconName>(['heart', 'star', 'play', 'trophy', 'moon', 'sparkle', 'flame', 'shield']);

interface Props {
  name: IconName;
  size?: number;
  color: string;
  /** Solid instead of outlined (heart, star, play, trophy, moon, sparkle, flame). */
  filled?: boolean;
  strokeWidth?: number;
}

/** Gold coin (two circles), used wherever coins are shown. */
export const CoinIcon = memo(function CoinIcon({ size = 20 }: { size?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" pointerEvents="none">
      <Circle cx={12} cy={12} r={10} fill="#F2B01E" />
      <Circle cx={12} cy={12} r={6.4} fill="none" stroke="#C98A06" strokeWidth={2} />
      <Circle cx={9.2} cy={8.6} r={1.6} fill="#FFE08A" />
    </Svg>
  );
});

export const Icon = memo(function Icon({ name, size = 24, color, filled = false, strokeWidth = 2 }: Props) {
  const solid = filled && FILLABLE.has(name);
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" pointerEvents="none">
      <Path
        d={ICON_PATHS[name]}
        stroke={color}
        strokeWidth={solid ? strokeWidth * 0.5 : strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill={solid ? color : 'none'}
      />
    </Svg>
  );
});
