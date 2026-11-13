import type { EditTransform } from '../../modules/camero-engine';

export type Rect = { x: number; y: number; w: number; h: number };

export const FULL: Rect = { x: 0, y: 0, w: 1, h: 1 };
export const IDENTITY: EditTransform = { rotation: 0, flipH: false, flipV: false, crop: FULL };

const eps = 1e-4;

export function isFullCrop(c: Rect): boolean {
  return Math.abs(c.x) < eps && Math.abs(c.y) < eps && Math.abs(c.w - 1) < eps && Math.abs(c.h - 1) < eps;
}

export function isIdentity(t: EditTransform): boolean {
  return t.rotation % 360 === 0 && !t.flipH && !t.flipV && isFullCrop(t.crop);
}

/**
 * Turns the picture a quarter turn clockwise as the user sees it. The crop rectangle is in the
 * coordinates of what the user sees, so it turns with the picture; a mirror becomes the other
 * mirror after a quarter turn.
 */
export function rotateClockwise(t: EditTransform): EditTransform {
  const c = t.crop;
  return {
    rotation: (((t.rotation + 90) % 360) as EditTransform['rotation']),
    flipH: t.flipV,
    flipV: t.flipH,
    crop: { x: 1 - c.y - c.h, y: c.x, w: c.h, h: c.w },
  };
}

export function mirror(t: EditTransform): EditTransform {
  const c = t.crop;
  return { ...t, flipH: !t.flipH, crop: { ...c, x: 1 - c.x - c.w } };
}

/** Largest centred crop with the given width/height ratio in normalized frame units. */
export function cropForRatio(normalizedRatio: number): Rect {
  if (normalizedRatio >= 1) {
    const h = 1 / normalizedRatio;
    return { x: 0, y: (1 - h) / 2, w: 1, h };
  }
  const w = normalizedRatio;
  return { x: (1 - w) / 2, y: 0, w, h: 1 };
}

/** Output pixel size for a displayed source of srcW x srcH. */
export function outputSize(srcW: number, srcH: number, t: EditTransform): { width: number; height: number } {
  const turned = t.rotation === 90 || t.rotation === 270;
  const w = (turned ? srcH : srcW) * t.crop.w;
  const h = (turned ? srcW : srcH) * t.crop.h;
  return { width: Math.max(2, Math.round(w / 2) * 2), height: Math.max(2, Math.round(h / 2) * 2) };
}

export function transformJson(t: EditTransform): string {
  return JSON.stringify(t);
}
