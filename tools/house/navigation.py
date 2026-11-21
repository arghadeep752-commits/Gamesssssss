"""Collision boxes for the furniture and the trader's walk grid over both floors (numpy only).

Grid: 0.4 m cells over the house (x 0..18, y 0..12). Three layers: 0 = ground floor, 1 = first floor, 2 = the stair.
The stair layer covers the stair's footprint; its south end joins the ground floor, its north end the first floor.
Unity space for the game: Unity (x, y, z) = Blender (x, z, y).
"""
import math
from collections import deque

import numpy as np

import layout as LY
import props

CELL = 0.4


def U(x, y, z=0.0):
    """Blender point -> Unity [x, y, z]."""
    return [round(float(x), 4), round(float(z), 4), round(float(y), 4)]


def furniture_boxes(L):
    """(cx, cy, w, d, h, yaw_deg, z0, kind) for every piece with a footprint (Blender axes)."""
    out = []
    for f in L["furniture"]:
        fp = props.FOOTPRINT.get(f["kind"])
        if not fp:
            continue
        w, d, h, yoff = fp
        a = math.radians(f["yaw"])
        cx = f["x"] - math.sin(a) * yoff
        cy = f["y"] + math.cos(a) * yoff
        out.append((cx, cy, w, d, h, f["yaw"], f["z"], f["kind"]))
    return out


def furniture_colliders(L, heights=None):
    """Rotated boxes [ux, uy, uz, sx, sy, sz, rot_x, rot_y] in Unity space. heights: real model heights by kind."""
    out = []
    for (cx, cy, w, d, h, yaw, z0, kind) in furniture_boxes(L):
        if kind in props.NO_COLLIDE:
            continue
        if heights and kind in heights:
            h = heights[kind]
        h = min(max(h, 0.3), 2.3)
        c = U(cx, cy, z0 + h / 2)
        # Blender yaw (counter-clockwise from above) -> Unity yaw (clockwise from above, z mirrored axes) = -yaw
        out.append(c + [round(w, 4), round(h, 4), round(d, 4), 0.0, round(-yaw, 3)])
    return out


def arch_colliders(coll):
    """Architecture boxes (Blender min/max + stair tilt) -> Unity [ux, uy, uz, sx, sy, sz, rot_x, rot_y]."""
    out = []
    for (x0, x1, y0, y1, z0, z1, rx) in coll:
        c = U((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        # Blender rotation about +x by rx (y toward z) is Unity rotation about +x by -rx (Unity z = Blender y)
        out.append(c + [round(x1 - x0, 4), round(z1 - z0, 4), round(y1 - y0, 4), round(-rx, 4), 0.0])
    return out


def _blocked_by_boxes(X, Y, boxes, radius):
    bad = np.zeros_like(X, bool)
    for (cx, cy, w, d, yaw) in boxes:
        a = math.radians(yaw)
        ca, sa = math.cos(a), math.sin(a)
        lx = (X - cx) * ca + (Y - cy) * sa
        ly = -(X - cx) * sa + (Y - cy) * ca
        bad |= (np.abs(lx) < w / 2 + radius) & (np.abs(ly) < d / 2 + radius)
    return bad


def grid(L, coll, radius=0.26):
    nx = int(math.ceil(LY.W / CELL))
    ny = int(math.ceil(LY.D / CELL))
    xs = (np.arange(nx) + 0.5) * CELL
    ys = (np.arange(ny) + 0.5) * CELL
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    layers = {}
    s = LY.STAIR
    for fl in (0, 1):
        ok = np.zeros_like(X, bool)
        for r in LY.ROOMS:
            if r[1] != fl:
                continue
            x0, y0, x1, y1 = r[2]
            ok |= (X > x0) & (X < x1) & (Y > y0) & (Y < y1)
        zf = LY.floor_z(fl)
        # walls and other solid boxes at walking height on this floor
        for (x0, x1, y0, y1, z0, z1, rx) in coll:
            if rx != 0.0:
                continue
            if z1 < zf + 0.3 or z0 > zf + 1.6 or (x1 - x0 > 30):
                continue
            ok &= ~((X > x0 - radius) & (X < x1 + radius) & (Y > y0 - radius) & (Y < y1 + radius))
        boxes = [(cx, cy, w, d, yaw) for (cx, cy, w, d, h, yaw, z0, kind) in furniture_boxes(L)
                 if kind not in props.NO_COLLIDE and abs(z0 - zf) < 1.0]
        ok &= ~_blocked_by_boxes(X, Y, boxes, 0.18)
        # the stair: under it on the ground floor, the void above it upstairs
        ok &= ~((X > s["x0"] - 0.05) & (X < s["x1"] + 0.3) & (Y > s["y0"] - 0.05) & (Y < s["y1"] + (0.05 if fl == 0 else -0.05)))
        # doorways stay open (a strip through each door / arch)
        for d in L["doors"]:
            if d["floor"] != fl or d["kind"] == "main":
                continue
            for tt in np.arange(-0.5, 0.51, CELL / 2):
                px, py = (d["x"], d["y"] + tt) if d["axis"] == "x" else (d["x"] + tt, d["y"])
                i, j = int(px / CELL), int(py / CELL)
                if 0 <= i < nx and 0 <= j < ny:
                    ok[i, j] = True
        for (wfl, ax, c, a, b, t, ops) in LY.WALLS:
            if wfl != fl:
                continue
            for o in ops:
                if o[4] != "arch":
                    continue
                for u in np.arange(o[0] + 0.3, o[1] - 0.29, CELL / 2):
                    for tt in (-0.3, 0.0, 0.3):
                        px, py = (u, c + tt) if ax == "x" else (c + tt, u)
                        i, j = int(px / CELL), int(py / CELL)
                        if 0 <= i < nx and 0 <= j < ny:
                            ok[i, j] = True
        layers[fl] = ok
    # stair layer: the middle of the stair, from the bottom step to the top
    st = np.zeros_like(X, bool)
    st |= (X > s["x0"] + 0.2) & (X < s["x1"] - 0.15) & (Y > s["y0"] - 0.21) & (Y < s["y1"] + 0.21)
    layers[2] = st
    # where the stair meets the floors: bottom row of stair cells <-> ground cells south of it, top row <-> upstairs
    js = [j for j in range(ny) if st[:, j].any()]
    j_lo, j_hi = min(js), max(js)
    links = []
    for i in range(nx):
        if st[i, j_lo] and j_lo - 1 >= 0:
            layers[0][i, j_lo - 1] = True
            links.append({"stair": [i, j_lo], "floor": 0, "cell": [i, j_lo - 1]})
        if st[i, j_hi] and j_hi + 1 < ny:
            layers[1][i, j_hi + 1] = True
            links.append({"stair": [i, j_hi], "floor": 1, "cell": [i, j_hi + 1]})
    return {"cell": CELL, "nx": nx, "ny": ny, "layers": layers, "links": links, "j_lo": j_lo, "j_hi": j_hi}


def cell_z(G, layer, j):
    if layer == 0:
        return 0.0
    if layer == 1:
        return LY.H1
    y = (j + 0.5) * G["cell"]
    return LY.stair_z(y)


def reach(G, layer, start):
    """Cells reachable from (layer, i, j) across all layers -> set."""
    seen = {(layer,) + tuple(start)}
    q = deque([(layer,) + tuple(start)])
    lk = {}
    for l in G["links"]:
        a = (2, l["stair"][0], l["stair"][1])
        b = (l["floor"], l["cell"][0], l["cell"][1])
        lk.setdefault(a, []).append(b)
        lk.setdefault(b, []).append(a)
    while q:
        c = q.popleft()
        L_, i, j = c
        ok = G["layers"][L_]
        nb = [(L_, i + 1, j), (L_, i - 1, j), (L_, i, j + 1), (L_, i, j - 1)] + lk.get(c, [])
        for n in nb:
            l2, a, b = n
            if 0 <= a < G["nx"] and 0 <= b < G["ny"] and G["layers"][l2][a, b] and n not in seen:
                seen.add(n)
                q.append(n)
    return seen


def export(G):
    rows = {}
    for k, ok in G["layers"].items():
        rows[str(k)] = ["".join("." if ok[i, j] else "#" for i in range(G["nx"])) for j in range(G["ny"])]
    stair_h = [round(cell_z(G, 2, j), 4) for j in range(G["ny"])]
    return {"cell": G["cell"], "nx": G["nx"], "ny": G["ny"], "x0": 0.0, "z0": 0.0, "rows": rows, "links": G["links"],
            "stair_h": stair_h, "floor_h": [0.0, LY.H1]}
