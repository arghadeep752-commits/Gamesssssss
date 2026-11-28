import { memo, useMemo } from 'react';
import Svg, { Path } from 'react-native-svg';
import { SHAPE_BY_ID, shapeMask, shapeSize } from '../game/shapes';

/** Pixel-style silhouette of a board outline (collection cards, win screen). */
export const ShapeThumb = memo(function ShapeThumb({
  shape,
  size,
  color,
  opacity = 1,
}: {
  shape: string;
  size: number;
  color: string;
  opacity?: number;
}) {
  const d = useMemo(() => {
    const def = SHAPE_BY_ID.get(shape);
    if (!def) return '';
    const { w, h } = shapeSize(def, 14);
    const m = shapeMask(def, w, h);
    const c = size / Math.max(w, h);
    const ox = (size - w * c) / 2;
    const oy = (size - h * c) / 2;
    const g = Math.max(0.6, c * 0.12);
    let out = '';
    for (let y = 0; y < h; y++) {
      for (let x = 0; x < w; x++) {
        if (!m[y * w + x]) continue;
        const px = (ox + x * c + g / 2).toFixed(1);
        const py = (oy + y * c + g / 2).toFixed(1);
        const s = (c - g).toFixed(1);
        out += `M${px} ${py}h${s}v${s}h-${s}z`;
      }
    }
    return out;
  }, [shape, size]);
  if (!d) return null;
  return (
    <Svg width={size} height={size} pointerEvents="none">
      <Path d={d} fill={color} opacity={opacity} />
    </Svg>
  );
});
