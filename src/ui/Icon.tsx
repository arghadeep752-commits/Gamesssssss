import React, { memo } from 'react';
import Svg, { Circle, Path, Rect } from 'react-native-svg';

import { palette } from '../theme/tokens';

/** Hand-drawn 24px icon set, 1.6px strokes with round joins. */
export type IconName =
  | 'flash' | 'flash-off' | 'flash-auto' | 'torch' | 'timer' | 'grid' | 'settings' | 'flip'
  | 'close' | 'check' | 'back' | 'chevron' | 'undo' | 'redo' | 'compare' | 'crop' | 'rotate'
  | 'flipH' | 'flipV' | 'trash' | 'share' | 'heart' | 'heart-fill' | 'info' | 'play' | 'pause'
  | 'volume' | 'mute' | 'speed' | 'stabilize' | 'macro' | 'look' | 'adjust' | 'sun' | 'lock'
  | 'plus' | 'minus' | 'gallery' | 'export' | 'more' | 'video' | 'photo' | 'level' | 'peaking'
  | 'zebra' | 'trim' | 'storage' | 'shield' | 'doc' | 'chip';

type Props = { name: IconName; size?: number; color?: string; strokeWidth?: number };

function IconImpl({ name, size = 24, color = palette.ink, strokeWidth = 1.6 }: Props) {
  const s = { stroke: color, strokeWidth, strokeLinecap: 'round' as const, strokeLinejoin: 'round' as const, fill: 'none' };
  const f = { fill: color };
  let body: React.ReactNode;
  switch (name) {
    case 'flash':
      body = <Path d="M13.2 2.8 5.8 13.2h5.6l-1.2 8 7.6-10.6h-5.7z" {...s} />;
      break;
    case 'flash-off':
      body = (
        <>
          <Path d="M13.2 2.8 5.8 13.2h5.6l-1.2 8 7.6-10.6h-5.7z" {...s} />
          <Path d="M4 4l16 16" {...s} />
        </>
      );
      break;
    case 'flash-auto':
      body = (
        <>
          <Path d="M10.6 2.8 4 12.2h5l-1 7.2 6.4-9h-5z" {...s} />
          <Path d="M15.6 20.5l2.4-6.3 2.4 6.3M16.4 18.6h3.2" {...s} />
        </>
      );
      break;
    case 'torch':
      body = <Path d="M8 3h8v3.5l-2 3V21h-4V9.5l-2-3zM12 12.5v2.5M8 6.5h8" {...s} />;
      break;
    case 'timer':
      body = (
        <>
          <Circle cx={12} cy={13.5} r={7.5} {...s} />
          <Path d="M12 13.5V9.5M10 2.8h4M12 2.8V6M18.3 6.7l1.4-1.4" {...s} />
        </>
      );
      break;
    case 'grid':
      body = <Path d="M4 4h16v16H4zM9.33 4v16M14.67 4v16M4 9.33h16M4 14.67h16" {...s} />;
      break;
    case 'settings':
      body = (
        <>
          <Path d="M4 7h8.5M17.5 7H20M4 12h3M11 12h9M4 17h10.5M18.5 17H20" {...s} />
          <Circle cx={15} cy={7} r={2.2} {...s} />
          <Circle cx={9} cy={12} r={2.2} {...s} />
          <Circle cx={16.5} cy={17} r={2.2} {...s} />
        </>
      );
      break;
    case 'flip':
      body = (
        <>
          <Path d="M19.5 9A8 8 0 0 0 5.2 7.2M4.5 15a8 8 0 0 0 14.3 1.8" {...s} />
          <Path d="M19.8 4.5V9h-4.5M4.2 19.5V15h4.5" {...s} />
        </>
      );
      break;
    case 'close':
      body = <Path d="M6 6l12 12M18 6 6 18" {...s} />;
      break;
    case 'check':
      body = <Path d="M5 12.5l4.5 4.5L19 7.5" {...s} />;
      break;
    case 'back':
      body = <Path d="M15 5l-7 7 7 7" {...s} />;
      break;
    case 'chevron':
      body = <Path d="M9.5 5.5 16 12l-6.5 6.5" {...s} />;
      break;
    case 'undo':
      body = <Path d="M4.5 9h10a5 5 0 0 1 0 10H9M8.5 5l-4 4 4 4" {...s} />;
      break;
    case 'redo':
      body = <Path d="M19.5 9h-10a5 5 0 0 0 0 10H15M15.5 5l4 4-4 4" {...s} />;
      break;
    case 'compare':
      body = (
        <>
          <Rect x={4} y={4} width={16} height={16} rx={2} {...s} />
          <Path d="M12 2.5v19" {...s} />
          <Path d="M4.8 4.8 12 12M4.8 10.2 12 17.4" {...s} strokeWidth={strokeWidth * 0.7} />
        </>
      );
      break;
    case 'crop':
      body = <Path d="M7 3v14h14M3 7h14v14" {...s} />;
      break;
    case 'rotate':
      body = <Path d="M4.5 12.5A7.5 7.5 0 1 0 7 6.6M4.3 3.8v4.4h4.4" {...s} />;
      break;
    case 'flipH':
      body = <Path d="M12 3v18M8.5 7.5 3.5 17h5zM15.5 7.5l5 9.5h-5z" {...s} />;
      break;
    case 'flipV':
      body = <Path d="M3 12h18M7.5 8.5 17 3.5v5zM7.5 15.5l9.5 5v-5z" {...s} />;
      break;
    case 'trash':
      body = <Path d="M4 7h16M9.5 7V4h5v3M6 7l1 13h10l1-13M10.2 11v5.5M13.8 11v5.5" {...s} />;
      break;
    case 'share':
      body = <Path d="M12 3.5v11M8 7.5l4-4 4 4M5.5 11.5V20h13v-8.5" {...s} />;
      break;
    case 'heart':
      body = <Path d="M12 19.5s-7-4.3-7-9.8A4 4 0 0 1 12 7.2a4 4 0 0 1 7 2.5c0 5.5-7 9.8-7 9.8z" {...s} />;
      break;
    case 'heart-fill':
      body = <Path d="M12 19.5s-7-4.3-7-9.8A4 4 0 0 1 12 7.2a4 4 0 0 1 7 2.5c0 5.5-7 9.8-7 9.8z" {...s} {...f} />;
      break;
    case 'info':
      body = (
        <>
          <Circle cx={12} cy={12} r={8.5} {...s} />
          <Path d="M12 11v5.5" {...s} />
          <Circle cx={12} cy={7.8} r={0.9} {...f} />
        </>
      );
      break;
    case 'play':
      body = <Path d="M8 5.5v13l10.5-6.5z" {...f} />;
      break;
    case 'pause':
      body = (
        <>
          <Rect x={7} y={5} width={3.2} height={14} rx={1} {...f} />
          <Rect x={13.8} y={5} width={3.2} height={14} rx={1} {...f} />
        </>
      );
      break;
    case 'volume':
      body = <Path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4zM15.5 9.2a4 4 0 0 1 0 5.6M18 6.8a7.4 7.4 0 0 1 0 10.4" {...s} />;
      break;
    case 'mute':
      body = <Path d="M4 9.5h3.5L12 6v12l-4.5-3.5H4zM15.5 9.5l5 5M20.5 9.5l-5 5" {...s} />;
      break;
    case 'speed':
      body = <Path d="M4.6 17.5a8 8 0 1 1 14.8 0M12 13.5l4.2-4.2" {...s} />;
      break;
    case 'stabilize':
      body = (
        <>
          <Rect x={3} y={5.5} width={18} height={13} rx={2} {...s} />
          <Path d="M6.5 12h2.2l1.4-2.4 3 4.8 1.4-2.4h3" {...s} />
        </>
      );
      break;
    case 'macro':
      body = <Path d="M12 13.5a3.8 3.8 0 0 1-3.8-3.8C8.2 7.3 12 3.8 12 3.8s3.8 3.5 3.8 5.9a3.8 3.8 0 0 1-3.8 3.8zM12 13.5V21M12 18c-1.8-2.4-4.6-2.6-5.8-2M12 18c1.8-2.4 4.6-2.6 5.8-2" {...s} />;
      break;
    case 'look':
      body = (
        <>
          <Circle cx={9} cy={9.5} r={5} {...s} />
          <Circle cx={15} cy={9.5} r={5} {...s} />
          <Circle cx={12} cy={14.8} r={5} {...s} />
        </>
      );
      break;
    case 'adjust':
      body = (
        <>
          <Circle cx={12} cy={12} r={8.5} {...s} />
          <Path d="M12 3.5a8.5 8.5 0 0 1 0 17z" {...f} />
        </>
      );
      break;
    case 'sun':
      body = (
        <>
          <Circle cx={12} cy={12} r={3.6} {...s} />
          <Path d="M12 2.8v2.4M12 18.8v2.4M2.8 12h2.4M18.8 12h2.4M5.5 5.5l1.7 1.7M16.8 16.8l1.7 1.7M5.5 18.5l1.7-1.7M16.8 7.2l1.7-1.7" {...s} />
        </>
      );
      break;
    case 'lock':
      body = (
        <>
          <Rect x={5} y={10.5} width={14} height={9.5} rx={2} {...s} />
          <Path d="M8.2 10.5V8a3.8 3.8 0 0 1 7.6 0v2.5" {...s} />
        </>
      );
      break;
    case 'plus':
      body = <Path d="M12 5v14M5 12h14" {...s} />;
      break;
    case 'minus':
      body = <Path d="M5 12h14" {...s} />;
      break;
    case 'gallery':
      body = (
        <>
          <Rect x={3} y={5} width={18} height={14} rx={2} {...s} />
          <Path d="M3.5 16.5l5-5 4 4 2.5-2.5 5 5" {...s} />
          <Circle cx={16} cy={9.2} r={1.4} {...s} />
        </>
      );
      break;
    case 'export':
      body = <Path d="M12 4v11M8 11l4 4 4-4M5 19.5h14" {...s} />;
      break;
    case 'more':
      body = (
        <>
          <Circle cx={6} cy={12} r={1.3} {...f} />
          <Circle cx={12} cy={12} r={1.3} {...f} />
          <Circle cx={18} cy={12} r={1.3} {...f} />
        </>
      );
      break;
    case 'video':
      body = <Path d="M3.5 7.5h11v9h-11zM14.5 10.5l6-3.2v9.4l-6-3.2" {...s} />;
      break;
    case 'photo':
      body = (
        <>
          <Path d="M4 8.5h3l1.5-2.2h7L17 8.5h3V19H4z" {...s} />
          <Circle cx={12} cy={13.5} r={3.3} {...s} />
        </>
      );
      break;
    case 'level':
      body = (
        <>
          <Path d="M3 12h6M15 12h6" {...s} />
          <Circle cx={12} cy={12} r={1.6} {...s} />
        </>
      );
      break;
    case 'peaking':
      body = (
        <>
          <Circle cx={12} cy={12} r={3.2} {...s} />
          <Path d="M12 2.8v3.4M12 17.8v3.4M2.8 12h3.4M17.8 12h3.4" {...s} />
        </>
      );
      break;
    case 'zebra':
      body = (
        <>
          <Rect x={4} y={4} width={16} height={16} rx={2} {...s} />
          <Path d="M4.6 13.4 13.4 4.6M4.6 19.4 19.4 4.6M10.6 19.4l8.8-8.8" {...s} />
        </>
      );
      break;
    case 'trim':
      body = <Path d="M6 4v16M18 4v16M6 8h12M6 16h12" {...s} />;
      break;
    case 'storage':
      body = (
        <>
          <Rect x={4} y={4} width={16} height={16} rx={2} {...s} />
          <Path d="M4 14h16M8 17h.01" {...s} />
        </>
      );
      break;
    case 'shield':
      body = <Path d="M12 3.5 5 6v5.5c0 4.6 3 8 7 9 4-1 7-4.4 7-9V6z" {...s} />;
      break;
    case 'doc':
      body = <Path d="M7 3.5h7l4 4v13H7zM14 3.5v4h4M9.5 12h6M9.5 15.5h6" {...s} />;
      break;
    case 'chip':
      body = (
        <>
          <Rect x={6.5} y={6.5} width={11} height={11} rx={1.5} {...s} />
          <Path d="M9.5 3.5v3M14.5 3.5v3M9.5 17.5v3M14.5 17.5v3M3.5 9.5h3M3.5 14.5h3M17.5 9.5h3M17.5 14.5h3" {...s} />
        </>
      );
      break;
    default:
      body = null;
  }
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      {body}
    </Svg>
  );
}

export const Icon = memo(IconImpl);
