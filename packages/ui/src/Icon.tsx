import { memo } from 'react';
import Svg, { Circle, G, Line, Path, Polygon, Polyline, Rect } from 'react-native-svg';

/**
 * Line icons drawn with react-native-svg (geometry from the MIT-licensed Feather
 * set), so the app ships no icon font. 24×24 grid, round caps, 1.8 stroke.
 */

type Primitive =
  | { p: string }
  | { c: [number, number, number] }
  | { l: [number, number, number, number] }
  | { pl: string }
  | { pg: string }
  | { r: [number, number, number, number, number?] };

const ICONS = {
  home: [{ p: 'M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z' }, { pl: '9 22 9 12 15 12 15 22' }],
  grid: [{ r: [3, 3, 7, 7, 1.5] }, { r: [14, 3, 7, 7, 1.5] }, { r: [14, 14, 7, 7, 1.5] }, { r: [3, 14, 7, 7, 1.5] }],
  heart: [
    {
      p: 'M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z',
    },
  ],
  user: [{ p: 'M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2' }, { c: [12, 7, 4] }],
  users: [
    { p: 'M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2' },
    { c: [9, 7, 4] },
    { p: 'M23 21v-2a4 4 0 0 0-3-3.87' },
    { p: 'M16 3.13a4 4 0 0 1 0 7.75' },
  ],
  search: [{ c: [11, 11, 7.5] }, { l: [21, 21, 16.65, 16.65] }],
  x: [{ l: [18, 6, 6, 18] }, { l: [6, 6, 18, 18] }],
  arrowLeft: [{ l: [19, 12, 5, 12] }, { pl: '12 19 5 12 12 5' }],
  arrowUp: [{ l: [12, 19, 12, 5] }, { pl: '5 12 12 5 19 12' }],
  arrowDown: [{ l: [12, 5, 12, 19] }, { pl: '19 12 12 19 5 12' }],
  chevronRight: [{ pl: '9 18 15 12 9 6' }],
  chevronLeft: [{ pl: '15 18 9 12 15 6' }],
  chevronDown: [{ pl: '6 9 12 15 18 9' }],
  chevronUp: [{ pl: '18 15 12 9 6 15' }],
  download: [{ p: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' }, { pl: '7 10 12 15 17 10' }, { l: [12, 15, 12, 3] }],
  upload: [{ p: 'M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4' }, { pl: '17 8 12 3 7 8' }, { l: [12, 3, 12, 15] }],
  share: [
    { c: [18, 5, 3] },
    { c: [6, 12, 3] },
    { c: [18, 19, 3] },
    { l: [8.59, 13.51, 15.42, 17.49] },
    { l: [15.41, 6.51, 8.59, 10.49] },
  ],
  message: [
    {
      p: 'M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z',
    },
  ],
  image: [{ r: [3, 3, 18, 18, 2] }, { c: [8.5, 8.5, 1.5] }, { pl: '21 15 16 10 5 21' }],
  smartphone: [{ r: [5, 2, 14, 20, 2] }, { l: [12, 18, 12.01, 18] }],
  lock: [{ r: [3, 11, 18, 11, 2] }, { p: 'M7 11V7a5 5 0 0 1 10 0v4' }],
  layers: [{ pg: '12 2 2 7 12 12 22 7 12 2' }, { pl: '2 17 12 22 22 17' }, { pl: '2 12 12 17 22 12' }],
  check: [{ pl: '20 6 9 17 4 12' }],
  checkCircle: [{ p: 'M22 11.08V12a10 10 0 1 1-5.93-9.14' }, { pl: '22 4 12 14.01 9 11.01' }],
  plus: [{ l: [12, 5, 12, 19] }, { l: [5, 12, 19, 12] }],
  trash: [
    { pl: '3 6 5 6 21 6' },
    { p: 'M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2' },
    { l: [10, 11, 10, 17] },
    { l: [14, 11, 14, 17] },
  ],
  edit: [{ p: 'M12 20h9' }, { p: 'M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z' }],
  star: [{ pg: '12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2' }],
  eye: [{ p: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z' }, { c: [12, 12, 3] }],
  eyeOff: [
    {
      p: 'M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24',
    },
    { l: [1, 1, 23, 23] },
  ],
  refresh: [
    { pl: '23 4 23 10 17 10' },
    { pl: '1 20 1 14 7 14' },
    { p: 'M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15' },
  ],
  logOut: [{ p: 'M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4' }, { pl: '16 17 21 12 16 7' }, { l: [21, 12, 9, 12] }],
  logIn: [{ p: 'M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4' }, { pl: '10 17 15 12 10 7' }, { l: [15, 12, 3, 12] }],
  wifiOff: [
    { l: [1, 1, 23, 23] },
    { p: 'M16.72 11.06A10.94 10.94 0 0 1 19 12.55' },
    { p: 'M5 12.55a10.94 10.94 0 0 1 5.17-2.39' },
    { p: 'M10.71 5.05A16 16 0 0 1 22.58 9' },
    { p: 'M1.42 9a15.91 15.91 0 0 1 4.7-2.88' },
    { p: 'M8.53 16.11a6 6 0 0 1 6.95 0' },
    { l: [12, 20, 12.01, 20] },
  ],
  alert: [{ c: [12, 12, 10] }, { l: [12, 8, 12, 12] }, { l: [12, 16, 12.01, 16] }],
  info: [{ c: [12, 12, 10] }, { l: [12, 16, 12, 12] }, { l: [12, 8, 12.01, 8] }],
  shield: [{ p: 'M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z' }],
  sun: [
    { c: [12, 12, 5] },
    { l: [12, 1, 12, 3] },
    { l: [12, 21, 12, 23] },
    { l: [4.22, 4.22, 5.64, 5.64] },
    { l: [18.36, 18.36, 19.78, 19.78] },
    { l: [1, 12, 3, 12] },
    { l: [21, 12, 23, 12] },
    { l: [4.22, 19.78, 5.64, 18.36] },
    { l: [18.36, 5.64, 19.78, 4.22] },
  ],
  moon: [{ p: 'M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z' }],
  externalLink: [{ p: 'M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6' }, { pl: '15 3 21 3 21 9' }, { l: [10, 14, 21, 3] }],
  mail: [{ p: 'M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z' }, { pl: '22 6 12 13 2 6' }],
  fileText: [
    { p: 'M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z' },
    { pl: '14 2 14 8 20 8' },
    { l: [16, 13, 8, 13] },
    { l: [16, 17, 8, 17] },
  ],
  folder: [{ p: 'M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z' }],
  barChart: [{ l: [18, 20, 18, 10] }, { l: [12, 20, 12, 4] }, { l: [6, 20, 6, 14] }],
  clock: [{ c: [12, 12, 10] }, { pl: '12 6 12 12 16 14' }],
  sliders: [
    { l: [4, 21, 4, 14] },
    { l: [4, 10, 4, 3] },
    { l: [12, 21, 12, 12] },
    { l: [12, 8, 12, 3] },
    { l: [20, 21, 20, 16] },
    { l: [20, 12, 20, 3] },
    { l: [1, 14, 7, 14] },
    { l: [9, 8, 15, 8] },
    { l: [17, 16, 23, 16] },
  ],
  tag: [{ p: 'M20.59 13.41l-7.17 7.17a2 2 0 0 1-2.83 0L2 12V2h10l8.59 8.59a2 2 0 0 1 0 2.82z' }, { l: [7, 7, 7.01, 7] }],
  filter: [{ pg: '22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3' }],
  moreVertical: [{ c: [12, 12, 1] }, { c: [12, 5, 1] }, { c: [12, 19, 1] }],
  trash2: [{ pl: '3 6 5 6 21 6' }, { p: 'M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6' }],
} satisfies Record<string, Primitive[]>;

export type IconName = keyof typeof ICONS;

export interface IconProps {
  name: IconName;
  size?: number;
  color: string;
  strokeWidth?: number;
  /** Fill colour, e.g. a solid heart for "liked". */
  fill?: string;
}

function renderPrimitive(prim: Primitive, index: number) {
  if ('p' in prim) return <Path key={index} d={prim.p} />;
  if ('c' in prim) return <Circle key={index} cx={prim.c[0]} cy={prim.c[1]} r={prim.c[2]} />;
  if ('l' in prim) return <Line key={index} x1={prim.l[0]} y1={prim.l[1]} x2={prim.l[2]} y2={prim.l[3]} />;
  if ('pl' in prim) return <Polyline key={index} points={prim.pl} />;
  if ('pg' in prim) return <Polygon key={index} points={prim.pg} />;
  const [x, y, w, h, rx] = prim.r;
  return <Rect key={index} x={x} y={y} width={w} height={h} rx={rx ?? 0} />;
}

export const Icon = memo(function Icon({ name, size = 22, color, strokeWidth = 1.8, fill = 'none' }: IconProps) {
  const prims: Primitive[] = ICONS[name];
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24">
      <G fill={fill} stroke={color} strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round">
        {prims.map(renderPrimitive)}
      </G>
    </Svg>
  );
});
