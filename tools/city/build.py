#!/usr/bin/env python3
"""Builds the DANGA map (Agartala) from code.

    python3 tools/city/build.py --assets DOWNLOADS --out UNITY_PROJECT [--npz build/city]

Runs in plain Python (numpy, Pillow, scipy) and is also driven by tools/city/blender_build.py, which assembles the very
same geometry in Blender, saves city.blend and renders previews. Writes into the Unity project:
  Assets/Game/City/chunks.bytes      every 128 m chunk: world / foliage / water / terrain meshes + its collision mesh
  Assets/Game/City/extras.bytes      the sea and the distant hills
  Assets/Game/City/colliders.bytes   boxes for buildings, monuments, walls, trees, lamps
  Assets/Game/City/Layers/NN_name.png (+ _n normal maps)  the texture-array layers
  Assets/Game/City/map.png           the minimap / pause-map picture
  Assets/Game/City/lightmap.png      ground shadows
  Assets/Resources/city_meta.json    traffic lanes, footpaths, places, districts, lamps ...
"""
import argparse
import json
import math
import os
import struct
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import buildings  # noqa: E402
import landmarks  # noqa: E402
import layout as LY  # noqa: E402
import nature  # noqa: E402
import textures  # noqa: E402
from mesh import LAYERS, Mesh  # noqa: E402
from roads import Roads  # noqa: E402

CHUNK = 128.0
GROUPS = {"world": 0, "foliage": 1, "water": 2, "terrain": 3, "coll": 4}
KIND = {"road": 1, "building": 2, "site": 3, "rail": 4, "tree": 5, "water": 6}


def log(*a):
    print("[city]", *a, flush=True)


# ------------------------------------------------------------------------------------------------ occupancy grid
class Grid:
    def __init__(self, cell=2.0):
        self.cell = cell
        self.n = int(round(2 * LY.HALF / cell))
        self.occ = np.zeros((self.n, self.n), np.uint8)          # [row = z index from south][col = x]
        self.h = np.full((self.n, self.n), np.nan, np.float32)    # surface height of roads / sites
        g = (np.arange(self.n) + 0.5) * cell - LY.HALF
        self.gx, self.gz = np.meshgrid(g, g)
        wet = ~np.isnan(LY.water_info(self.gx, self.gz))
        low = LY.height(self.gx, self.gz) < -0.25
        self.occ[wet | low] = KIND["water"]

    def idx(self, x, z):
        return int((x + LY.HALF) / self.cell), int((z + LY.HALF) / self.cell)

    def _bbox(self, xs, zs, pad=0.0):
        i0 = max(0, int((min(xs) - pad + LY.HALF) / self.cell))
        i1 = min(self.n, int((max(xs) + pad + LY.HALF) / self.cell) + 1)
        j0 = max(0, int((min(zs) - pad + LY.HALF) / self.cell))
        j1 = min(self.n, int((max(zs) + pad + LY.HALF) / self.cell) + 1)
        return i0, i1, j0, j1

    def mark_line(self, pts, width, kind, heights=None):
        pts = [np.asarray(p, float) for p in pts]
        for k in range(len(pts) - 1):
            a, b = pts[k], pts[k + 1]
            i0, i1, j0, j1 = self._bbox([a[0], b[0]], [a[1], b[1]], width / 2 + self.cell)
            if i1 <= i0 or j1 <= j0:
                continue
            GX = self.gx[j0:j1, i0:i1]
            GZ = self.gz[j0:j1, i0:i1]
            d = b - a
            L2 = float(d @ d)
            t = np.clip(((GX - a[0]) * d[0] + (GZ - a[1]) * d[1]) / max(L2, 1e-9), 0, 1)
            dist = np.hypot(GX - (a[0] + t * d[0]), GZ - (a[1] + t * d[1]))
            m = dist <= width / 2
            sub = self.occ[j0:j1, i0:i1]
            sub[m & (sub != KIND["water"])] = KIND[kind]
            if heights is not None:
                hh = heights[k] + (heights[k + 1] - heights[k]) * t
                hs = self.h[j0:j1, i0:i1]
                hs[m] = np.where(np.isnan(hs[m]), hh[m], np.maximum(hs[m], hh[m]))
                sub[m] = KIND[kind]

    def _poly_mask(self, poly, i0, i1, j0, j1):
        from matplotlib.path import Path
        pts = np.stack([self.gx[j0:j1, i0:i1].ravel(), self.gz[j0:j1, i0:i1].ravel()], -1)
        return Path(np.asarray(poly, float)).contains_points(pts).reshape(j1 - j0, i1 - i0)

    def mark_poly(self, poly, kind, y=None):
        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        i0, i1, j0, j1 = self._bbox(xs, zs, self.cell)
        if i1 <= i0 or j1 <= j0:
            return
        m = self._poly_mask(poly, i0, i1, j0, j1)
        sub = self.occ[j0:j1, i0:i1]
        sub[m] = KIND[kind]
        if y is not None:
            hs = self.h[j0:j1, i0:i1]
            hs[m] = y

    def _rect_poly(self, cx, cz, w, d, dvec):
        dv = np.asarray(dvec, float)
        dv = dv / (np.linalg.norm(dv) + 1e-12)
        lf = np.array([-dv[1], dv[0]])
        c = np.array([cx, cz])
        return [tuple(c - dv * w / 2 - lf * d / 2), tuple(c + dv * w / 2 - lf * d / 2), tuple(c + dv * w / 2 + lf * d / 2), tuple(c - dv * w / 2 + lf * d / 2)]

    def mark_rect(self, cx, cz, w, d, dvec, kind):
        self.mark_poly(self._rect_poly(cx, cz, w, d, dvec), kind)

    def reserve_poly(self, poly):
        """Keep the free cells of an area free of town buildings (the way from a gate to the road); roads stay roads."""
        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        i0, i1, j0, j1 = self._bbox(xs, zs, self.cell)
        if i1 <= i0 or j1 <= j0:
            return
        m = self._poly_mask(poly, i0, i1, j0, j1)
        sub = self.occ[j0:j1, i0:i1]
        sub[m & (sub == 0)] = KIND["site"]

    def rect_free(self, cx, cz, w, d, dvec):
        if abs(cx) > LY.HALF - 30 or abs(cz) > LY.HALF - 30:
            return False
        poly = self._rect_poly(cx, cz, w, d, dvec)
        xs = [p[0] for p in poly]
        zs = [p[1] for p in poly]
        i0, i1, j0, j1 = self._bbox(xs, zs, 0.0)
        if i1 <= i0 or j1 <= j0:
            return False
        m = self._poly_mask(poly, i0, i1, j0, j1)
        return not np.any(self.occ[j0:j1, i0:i1][m] != 0)

    def free_point(self, x, z, r):
        i, j = self.idx(x, z)
        k = max(1, int(r / self.cell))
        if i - k < 0 or j - k < 0 or i + k >= self.n or j + k >= self.n:
            return False
        return not np.any(self.occ[j - k:j + k + 1, i - k:i + k + 1] != 0)

    def ground(self, cx, cz, w, d, dvec):
        poly = self._rect_poly(cx, cz, w, d, dvec)
        xs = np.array([p[0] for p in poly] + [cx])
        zs = np.array([p[1] for p in poly] + [cz])
        return float(np.max(LY.height(xs, zs)))

    def sample_height(self, X, Z):
        i = np.clip(((X + LY.HALF) / self.cell).astype(int), 0, self.n - 1)
        j = np.clip(((Z + LY.HALF) / self.cell).astype(int), 0, self.n - 1)
        # a little dilation so the ground also sinks right at the edges of roads
        h = self.h
        out = h[j, i]
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nb = h[np.clip(j + dj, 0, self.n - 1), np.clip(i + di, 0, self.n - 1)]
            out = np.where(np.isnan(out), nb, out)
        return out


# ------------------------------------------------------------------------------------------------ chunked meshes
class Chunks:
    def __init__(self, size=CHUNK):
        self.size = size
        self.m = {}
        self.extras = {}

    def key(self, x, z):
        n = int(math.ceil(2 * LY.HALF / self.size))
        ix = int((x + LY.HALF) // self.size)
        iz = int((z + LY.HALF) // self.size)
        return max(0, min(n - 1, ix)), max(0, min(n - 1, iz))

    def get(self, x, z, group):
        k = self.key(x, z) + (group,)
        if k not in self.m:
            self.m[k] = Mesh(terrain=(group == "terrain"))
        return self.m[k]

    def extra(self, name, terrain=False):
        if name not in self.extras:
            self.extras[name] = Mesh(terrain=terrain)
        return self.extras[name]


# ------------------------------------------------------------------------------------------------ writing
VERT = np.dtype([("p", "<f4", 3), ("n", "i1", 4), ("c", "u1", 4), ("uv", "<f4", 2), ("x", "u1", 4)])   # 32 bytes


def pack(a, coll=False):
    nv = len(a["P"])
    if coll:
        return struct.pack("<i", nv) + a["P"].astype("<f4").tobytes() + struct.pack("<i", len(a["I"])) + a["I"].astype("<i4").tobytes()
    v = np.zeros(nv, VERT)
    v["p"] = a["P"]
    n = a["N"] / (np.linalg.norm(a["N"], axis=1, keepdims=True) + 1e-9)
    v["n"][:, :3] = np.clip(np.round(n * 127), -127, 127).astype(np.int8)
    v["c"][:, :3] = np.clip(np.round(a["C"] * 255), 0, 255).astype(np.uint8)
    v["c"][:, 3] = np.clip(np.round(a["E"] * 255), 0, 255).astype(np.uint8)
    v["uv"] = a["UV"]
    v["x"][:, 0] = np.clip(np.round(a["S"]), 0, 255).astype(np.uint8)
    v["x"][:, 1] = np.clip(np.round(a["AO"] * 255), 0, 255).astype(np.uint8)
    if "S2" in a:
        v["x"][:, 2] = np.clip(np.round(a["S2"]), 0, 255).astype(np.uint8)
        v["x"][:, 3] = np.clip(np.round(a["B"] * 255), 0, 255).astype(np.uint8)
    else:
        v["x"][:, 2] = v["x"][:, 0]
    mn = a["P"].min(0)
    mx = a["P"].max(0)
    small = nv < 65535
    idx = a["I"].astype("<u2" if small else "<i4").tobytes()
    if small and len(a["I"]) % 2 == 1:
        idx += b"\0\0"                       # keep 4-byte alignment
    return (struct.pack("<i", nv) + struct.pack("<6f", *mn, *mx) + v.tobytes() + struct.pack("<ii", len(a["I"]), 2 if small else 4) + idx)


def write_chunks(M, path):
    keys = sorted(set((k[0], k[1]) for k in M.m))
    out = [struct.pack("<iiffi", 0x31434744, 1, M.size, LY.HALF, len(keys))]
    stats = {g: [0, 0] for g in GROUPS}
    for ix, iz in keys:
        groups = [(g, M.m[(ix, iz, g)]) for g in GROUPS if (ix, iz, g) in M.m]
        groups = [(g, m) for g, m in groups if m.n > 0 and m.I]
        out.append(struct.pack("<iii", ix, iz, len(groups)))
        for g, m in groups:
            a = m.arrays()
            out.append(struct.pack("<i", GROUPS[g]))
            out.append(pack(a, coll=(g == "coll")))
            stats[g][0] += len(a["P"])
            stats[g][1] += len(a["I"]) // 3
    data = b"".join(out)
    with open(path, "wb") as f:
        f.write(data)
    return stats, len(data)


def write_extras(M, path):
    out = [struct.pack("<ii", 0x31584744, len(M.extras))]
    for name, m in M.extras.items():
        a = m.arrays()
        b = name.encode()
        out.append(struct.pack("<i", len(b)) + b + pack(a))
    with open(path, "wb") as f:
        f.write(b"".join(out))


def write_colliders(cols, path):
    arr = np.asarray(cols, np.float32).reshape(-1, 7)
    with open(path, "wb") as f:
        f.write(struct.pack("<ii", 0x314C4344, len(arr)))
        f.write(arr.astype("<f4").tobytes())
    return len(arr)


# ------------------------------------------------------------------------------------------------ main
def generate(assets):
    t0 = time.time()
    meta = {"points": []}
    colliders = []
    M = Chunks()
    grid = Grid()
    g = LY.build_graph()
    log("road graph: %d junctions, %d pieces (%.1fs)" % (len(g.nodes), len(g.edges), time.time() - t0))
    roads = Roads(g, grid).build(M)
    colliders += roads.colliders
    log("roads: %d chains, %d lanes, %d footpaths, %d bridges (%.1fs)" % (len(roads.chains), len(roads.lanes), len(roads.walks),
                                                                           len(roads.bridges), time.time() - t0))
    landmarks.build_all(M, grid, colliders, meta)
    log("landmarks done (%.1fs)" % (time.time() - t0))
    objects = meta.setdefault("objects", [])
    blds = buildings.place_lots(roads, grid, M, colliders, objects=objects)
    log("hyper3d spots: %d shop-house slots, %d props" % (sum(1 for o in objects if o.get("slot")), sum(1 for o in objects if not o.get("slot"))))
    log("buildings: %d (%.1fs)" % (len(blds), time.time() - t0))
    lamps = nature.street_lamps(M, roads, colliders, meta)
    nature.electric_poles(M, roads, colliders)
    trees, shade = nature.plant_trees(M, grid, colliders)
    log("trees: %d, lamps: %d (%.1fs)" % (len(trees), len(lamps), time.time() - t0))
    nature.terrain(M, grid)
    nature.water(M)
    nature.distant_hills(M)
    nature.countryside_skirt(M)
    log("terrain and water (%.1fs)" % (time.time() - t0))
    return dict(M=M, grid=grid, roads=roads, meta=meta, colliders=colliders, buildings=blds, trees=trees, shade=shade)


def make_meta(res):
    roads, meta = res["roads"], res["meta"]
    zones = [{"name": n, "c": [c[0], c[1]], "r": r} for n, c, r in LY.ZONES]
    lms = [p for p in meta["points"] if p["kind"] == "landmark"]
    pts = [p for p in meta["points"] if p["kind"] != "landmark"]
    out = {
        "half": LY.HALF, "chunk": CHUNK, "sea_level": LY.SEA_LEVEL, "river_level": LY.RIVER_LEVEL, "pond_level": LY.POND_LEVEL,
        "lake_level": LY.LAKE_LEVEL, "sun": {"azimuth": 150.0, "elevation": 52.0}, "layers": LAYERS,
        "lanes": roads.lanes, "walks": roads.walks, "walk_links": roads.walk_links, "junctions": getattr(roads, "junctions", []),
        "bridges": roads.bridges, "points": pts, "landmarks": lms, "zones": zones, "lamps": meta.get("lamps", []),
        "objects": meta.get("objects", []),
        "ponds": [{"name": n, "c": list(c), "size": list(s), "r": r, "level": lv} for n, c, s, r, lv in LY.PONDS],
        "lake": {"c": list(LY.LAKE[1]), "r": list(LY.LAKE[2]), "level": LY.LAKE_LEVEL},
        "river": {"pts": [list(p) for p in LY.RIVER], "w": LY.RIVER_W, "level": LY.RIVER_LEVEL},
        "roads": [{"name": c["road"], "cls": c["cls"], "pts": [[round(p[0], 1), round(p[1], 1)] for p in c["pts"]]} for c in roads.chains],
    }
    return out


def water_grid(path, cell=4.0):
    """Water surface level on a 4 m grid (NaN = dry) for boats and swimming: int16 centimetres, -32768 = dry."""
    n = int(2 * LY.HALF / cell)
    g = (np.arange(n) + 0.5) * cell - LY.HALF
    X, Z = np.meshgrid(g, g)
    w = LY.water_info(X, Z)
    h = LY.height(X, Z)
    lv = np.where(np.isnan(w) | (h > w - 0.3), -32768, np.round(w * 100)).astype("<i2")
    with open(path, "wb") as f:
        f.write(struct.pack("<iif", 0x31574744, n, cell))
        f.write(lv.tobytes())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--assets", required=True, help="downloaded assets (tex/, leaves/, fonts/)")
    ap.add_argument("--out", required=True, help="Unity project root")
    ap.add_argument("--preview", default="", help="folder for preview pictures")
    a = ap.parse_args()
    t0 = time.time()
    res = generate(a.assets)
    city = os.path.join(a.out, "Assets", "Game", "City")
    os.makedirs(os.path.join(city, "Layers"), exist_ok=True)
    os.makedirs(os.path.join(a.out, "Assets", "Resources"), exist_ok=True)
    stats, size = write_chunks(res["M"], os.path.join(city, "chunks.bytes"))
    write_extras(res["M"], os.path.join(city, "extras.bytes"))
    nc = write_colliders(res["colliders"], os.path.join(city, "colliders.bytes"))
    water_grid(os.path.join(city, "water.bytes"))
    log("chunks.bytes %.1f MB; %s; colliders %d" % (size / 1e6, ", ".join("%s %dv/%dt" % (g, s[0], s[1]) for g, s in stats.items()), nc))
    meta = make_meta(res)
    with open(os.path.join(a.out, "Assets", "Resources", "city_meta.json"), "w") as f:
        json.dump(meta, f, separators=(",", ":"))
    rep = textures.build_layers(os.path.join(a.assets, "tex"), os.path.join(a.assets, "leaves"), os.path.join(a.assets, "fonts"),
                                os.path.join(city, "Layers"))
    for r in rep:
        log(r)
    textures.map_picture(res["roads"], res["grid"], res["buildings"], os.path.join(city, "map.png"))
    textures.light_map(res["colliders"], res["shade"], os.path.join(city, "lightmap.png"))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        from PIL import Image
        Image.open(os.path.join(city, "map.png")).resize((1024, 1024)).save(os.path.join(a.preview, "preview_map.png"))
        Image.open(os.path.join(city, "lightmap.png")).resize((1024, 1024)).save(os.path.join(a.preview, "preview_lightmap.png"))
    log("done in %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
