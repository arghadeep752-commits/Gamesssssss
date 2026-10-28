import { memo } from 'react';
import Svg, { Path } from 'react-native-svg';
import { COLORS } from '../config/theme';

/** Original line icons on a 24-unit grid; one Path per icon keeps them light. */
const PATHS = {
  back: 'M15 18l-6-6 6-6',
  chevron: 'M9 6l6 6-6 6',
  pause: 'M9 5v14M15 5v14',
  heart: 'M12 20.5s-7.4-4.5-9.4-9C1.2 8.2 3.2 4.6 6.7 4.6c2.1 0 3.6 1.2 5.3 3.1 1.7-1.9 3.2-3.1 5.3-3.1 3.5 0 5.5 3.6 4.1 6.9-2 4.5-9.4 9-9.4 9z',
  star: 'M12 2.8l2.8 5.9 6.4.8-4.7 4.4 1.2 6.4L12 17.2l-5.7 3.1 1.2-6.4-4.7-4.4 6.4-.8z',
  bulb: 'M9 18h6M10 21h4M12 3a6 6 0 0 0-3.6 10.8c.6.5 1 1.2 1 2v.2h5.2v-.2c0-.8.4-1.5 1-2A6 6 0 0 0 12 3z',
  undo: 'M9 14L4 9l5-5M4 9h10.5a5.5 5.5 0 0 1 0 11H11',
  restart: 'M3.5 12a8.5 8.5 0 1 0 2.6-6.1M3.5 3.5v5h5',
  scan: 'M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12zM12 9.2a2.8 2.8 0 1 1 0 5.6 2.8 2.8 0 0 1 0-5.6z',
  home: 'M3 11l9-7 9 7M5.5 9.5V20h13V9.5',
  calendar: 'M4 6h16v14H4zM4 10.5h16M8.5 3v5M15.5 3v5',
  user: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4.5 20.5c1.4-3.7 4.3-5.6 7.5-5.6s6.1 1.9 7.5 5.6',
  sliders: 'M4 7h9M17 7h3M15 5v4M4 12h3M11 12h9M9 10v4M4 17h11M19 17h1M17 15v4',
  lock: 'M6.5 11h11v9h-11zM8.5 11V8.3a3.5 3.5 0 0 1 7 0V11',
  check: 'M5 12.5l4.5 4.5L19 7.5',
  close: 'M6 6l12 12M18 6L6 18',
  trophy: 'M8 4h8v5a4 4 0 0 1-8 0zM8 6H5.2a3 3 0 0 0 3 4M16 6h2.8a3 3 0 0 1-3 4M12 13v4M8.5 20.5h7M10 17h4v3.5h-4z',
  help: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM9.6 9.4a2.5 2.5 0 1 1 3.5 2.3c-.6.3-1.1.9-1.1 1.6v.6M12 16.9v.2',
  info: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18zM12 11v6M12 7.6v.2',
  shield: 'M12 3l7 3v5.8c0 4.4-3 7.6-7 9.2-4-1.6-7-4.8-7-9.2V6z',
  doc: 'M7 3h7l4 4v14H7zM14 3v4h4M10 12h5M10 16h5',
  trash: 'M4 7h16M9 7V4h6v3M6.5 7l1 13h9l1-13',
  flame: 'M12 3c.9 3 4.5 5 4.5 9.5a4.5 4.5 0 0 1-9 0c0-2.2 1.1-3.6 2.2-4.5.1 2 .9 3 2 3.2-.4-3 .1-5.5.3-8.2z',
  grid: 'M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z',
  play: 'M8 5.2v13.6L19 12z',
  edit: 'M4.5 19.5h4l10.3-10.3-4-4L4.5 15.5zM13.5 6.5l4 4',
  medal: 'M8 3h8l-2.2 5.5M8 3l2.2 5.5M12 21a5.5 5.5 0 1 0 0-11 5.5 5.5 0 0 0 0 11zM12 13.2v4.6',
  sound: 'M4 9.5h3.5L12 5.5v13l-4.5-4H4zM15.5 9a4 4 0 0 1 0 6M18 6.5a7.5 7.5 0 0 1 0 11',
  music: 'M9 18.5V6l10-2.5v12.5M9 18.5a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0zM19 16a2.5 2.5 0 1 1-5 0 2.5 2.5 0 0 1 5 0z',
  vibrate: 'M8.5 4h7v16h-7zM4.5 8.5v7M19.5 8.5v7',
  sparkle: 'M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z',
} as const;

export type IconName = keyof typeof PATHS;

const FILLED: ReadonlySet<IconName> = new Set<IconName>(['heart', 'star', 'play']);

interface Props {
  name: IconName;
  size?: number;
  color?: string;
  /** Draw solid instead of outlined (supported by heart, star, play). */
  filled?: boolean;
  strokeWidth?: number;
}

export const Icon = memo(function Icon({ name, size = 24, color = COLORS.ink, filled, strokeWidth = 2 }: Props) {
  const solid = filled ?? false;
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" pointerEvents="none">
      <Path
        d={PATHS[name]}
        stroke={solid && FILLED.has(name) ? 'none' : color}
        strokeWidth={strokeWidth}
        strokeLinecap="round"
        strokeLinejoin="round"
        fill={solid && FILLED.has(name) ? color : 'none'}
      />
    </Svg>
  );
});
