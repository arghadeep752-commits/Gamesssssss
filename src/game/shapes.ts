/** Board outlines. Cells outside the mask stay empty and show no dot. */
export type Shape = 'rect' | 'rounded' | 'circle' | 'diamond' | 'heart' | 'plus' | 'hex' | 'ring' | 'hourglass';

export const FANCY_SHAPES: readonly Shape[] = ['rounded', 'circle', 'diamond', 'heart', 'plus', 'hex', 'ring', 'hourglass'];

export function shapeMask(shape: Shape, w: number, h: number): Uint8Array {
  const m = new Uint8Array(w * h);
  const cx = (w - 1) / 2;
  const cy = (h - 1) / 2;
  for (let y = 0; y < h; y++) {
    for (let x = 0; x < w; x++) {
      const nx = (x - cx) / (w / 2); // roughly -1..1
      const ny = (y - cy) / (h / 2);
      let on = true;
      switch (shape) {
        case 'rect':
          on = true;
          break;
        case 'rounded': {
          const corner = (x === 0 || x === w - 1) && (y === 0 || y === h - 1);
          on = !corner;
          break;
        }
        case 'circle':
          on = nx * nx + ny * ny <= 1.02;
          break;
        case 'diamond':
          on = Math.abs(nx) + Math.abs(ny) <= 1.12;
          break;
        case 'heart': {
          // Classic implicit heart curve, flipped so the point is at the bottom.
          const X = nx * 1.25;
          const Y = -ny * 1.3 + 0.25;
          const v = X * X + Y * Y - 1;
          on = v * v * v - X * X * Y * Y * Y <= 0.02;
          break;
        }
        case 'plus': {
          const bx = Math.abs(nx) <= 0.42;
          const by = Math.abs(ny) <= 0.42;
          on = bx || by;
          break;
        }
        case 'hex':
          on = Math.abs(ny) <= 1 && Math.abs(nx) + Math.abs(ny) * 0.55 <= 1.05;
          break;
        case 'ring': {
          const r = nx * nx + ny * ny;
          on = r <= 1.02 && r >= 0.16;
          break;
        }
        case 'hourglass':
          on = Math.abs(nx) <= Math.abs(ny) * 0.75 + 0.38;
          break;
      }
      m[y * w + x] = on ? 1 : 0;
    }
  }
  return m;
}
