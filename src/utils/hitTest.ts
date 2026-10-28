/**
 * Maps a touch point on the board to an arrow id using the same cell grid the
 * engine uses. A touch inside an arrow's cell selects it; a touch on an empty
 * cell selects the nearest neighbouring arrow cell within `slop` cells, which
 * gives thin arrows a generous invisible hit area without ever reaching across
 * another arrow's cell. Returns -1 when nothing is close enough.
 */
export function hitTest(
  occupancy: Int16Array,
  width: number,
  height: number,
  removed: readonly boolean[],
  x: number,
  y: number,
  cell: number,
  slop = 0.85,
): number {
  if (cell <= 0) return -1;
  const cx = Math.floor(x / cell);
  const cy = Math.floor(y / cell);
  if (cx >= 0 && cy >= 0 && cx < width && cy < height) {
    const id = occupancy[cy * width + cx];
    if (id >= 0 && !removed[id]) return id;
  }
  let best = -1;
  let bestD = (slop * cell) ** 2;
  for (let dy = -1; dy <= 1; dy++) {
    for (let dx = -1; dx <= 1; dx++) {
      if (!dx && !dy) continue;
      const nx = cx + dx;
      const ny = cy + dy;
      if (nx < 0 || ny < 0 || nx >= width || ny >= height) continue;
      const id = occupancy[ny * width + nx];
      if (id < 0 || removed[id]) continue;
      const ddx = (nx + 0.5) * cell - x;
      const ddy = (ny + 0.5) * cell - y;
      const d = ddx * ddx + ddy * ddy;
      if (d < bestD) {
        bestD = d;
        best = id;
      }
    }
  }
  return best;
}

/** Largest whole-pixel cell size that fits the grid inside the available area. */
export function fitCellSize(
  areaWidth: number,
  areaHeight: number,
  cols: number,
  rows: number,
  padding = 8,
  maxCell = 64,
): number {
  if (areaWidth <= 0 || areaHeight <= 0) return 0;
  const c = Math.floor(Math.min((areaWidth - padding * 2) / cols, (areaHeight - padding * 2) / rows));
  return Math.max(12, Math.min(maxCell, c));
}
