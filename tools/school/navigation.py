"""Collision boxes and Ragini's walk grid, worked out from the layout (numpy only).

Godot axes are used for the output: Godot (x, y, z) = Blender (x, z, -y).
"""
import math
from collections import deque

import numpy as np

import architecture
import furniture


def to_godot(bx, by, bz):
    return [round(float(bx), 4), round(float(bz), 4), round(float(-by), 4)]


def furniture_boxes(L):
    """Footprints of the furniture as rotated boxes: (cx, cy, w, d, h, yaw_deg, z0) in Blender axes."""
    out = []
    for f in L["furniture"]:
        fp = furniture.FOOTPRINT.get(f["kind"])
        if not fp:
            continue
        w, d, h, yoff = fp
        a = math.radians(f["yaw"])
        cx = f["x"] - yoff * math.sin(a) * -1.0 * 0 + (-math.sin(a)) * 0.0
        # local (0, yoff) rotated by yaw
        cx = f["x"] + (-math.sin(a)) * yoff
        cy = f["y"] + (math.cos(a)) * yoff
        out.append((cx, cy, w, d, h, f["yaw"], f.get("z", 0.0), f["kind"]))
    return out


def colliders(L):
    """[[gx, gy, gz, sx, sy, sz, yaw_rad], ...] for walls, pillars, the compound wall and the furniture."""
    out = []
    for (x0, x1, y0, y1, z0, z1) in architecture.COLL:
        c = to_godot((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        out.append(c + [round(x1 - x0, 4), round(z1 - z0, 4), round(y1 - y0, 4), 0.0])
    for (cx, cy, w, d, h, yaw, z0, kind) in furniture_boxes(L):
        if kind in ("hand_pump", "neem_tree", "flag_platform"):
            h = max(h, 1.0)
        c = to_godot(cx, cy, z0 + h / 2)
        out.append(c + [round(w, 4), round(h, 4), round(d, 4), round(math.radians(yaw), 5)])
    return out


def grid(L, cell=0.4, radius=0.24):
    """Walkability grid over the building for Ragini. Returns dict with Godot-space origin and rows ('.' / '#')."""
    bx0, by0, bx1, by1 = L["building"]
    nx = int(math.ceil((bx1 - bx0) / cell))
    ny = int(math.ceil((by1 - by0) / cell))
    xs = bx0 + (np.arange(nx) + 0.5) * cell
    ys = by0 + (np.arange(ny) + 0.5) * cell
    X, Y = np.meshgrid(xs, ys, indexing="ij")          # [i, j] -> x index i, y index j
    ok = np.ones_like(X, bool)
    T = L["wall_t"]
    ok &= (X > bx0 + T / 2 + radius) & (X < bx1 - T / 2 - radius) & (Y > by0 + T / 2 + radius) & (Y < by1 - T / 2 - radius)
    for (x0, x1, y0, y1, z0, z1) in architecture.COLL:
        if z0 > 1.0:
            continue
        ok &= ~((X > x0 - radius) & (X < x1 + radius) & (Y > y0 - radius) & (Y < y1 + radius))
    for (cx, cy, w, d, h, yaw, z0, kind) in furniture_boxes(L):
        if z0 > 0.05 and kind in ("teacher_table", "teacher_chair"):
            pass
        a = math.radians(yaw)
        ca, sa = math.cos(a), math.sin(a)
        lx = (X - cx) * ca + (Y - cy) * sa
        ly = -(X - cx) * sa + (Y - cy) * ca
        m = 0.2
        ok &= ~((np.abs(lx) < w / 2 + m) & (np.abs(ly) < d / 2 + m))
    # doorways are always open: carve a strip through each opening
    for dr in L["doors"]:
        if dr["lock"] == "main":
            continue
        x, y = dr["x"], dr["y"]
        for t in np.arange(-0.8, 0.81, cell / 2):
            px, py = (x, y + t) if dr["o"] == "h" else (x + t, y)
            i = int((px - bx0) / cell)
            j = int((py - by0) / cell)
            if 0 <= i < nx and 0 <= j < ny:
                ok[i, j] = True
    return {"cell": cell, "nx": nx, "ny": ny, "x0": bx0, "y0": by0, "ok": ok}


def cell_of(G, bx, by):
    return int((bx - G["x0"]) / G["cell"]), int((by - G["y0"]) / G["cell"])


def reach(G, start):
    ok = G["ok"]
    seen = np.zeros_like(ok)
    q = deque([start])
    if not ok[start]:
        return seen
    seen[start] = True
    while q:
        i, j = q.popleft()
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < ok.shape[0] and 0 <= b < ok.shape[1] and ok[a, b] and not seen[a, b]:
                seen[a, b] = True
                q.append((a, b))
    return seen


def export_grid(G):
    """Rows in Godot order: row r runs along Godot x at Godot z = -(y0 + (ny - 0.5 - r) * cell) ... kept simple:
    'rows[j]' is Blender y index j (Godot z = -y), characters along x."""
    ok = G["ok"]
    rows = ["".join("." if ok[i, j] else "#" for i in range(G["nx"])) for j in range(G["ny"])]
    return {"cell": G["cell"], "nx": G["nx"], "ny": G["ny"], "x0": G["x0"], "y0": G["y0"], "rows": rows}
