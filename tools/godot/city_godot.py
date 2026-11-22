"""Writes the generated city for the Godot game (called by tools/city/build.py --godot DIR).

The city generator works in a left-handed frame (x east, z north, like Unity). Godot is right-handed with -Z as
"forward", so everything goes out mirrored on z (z -> -z, yaw -> -yaw; the index order stays, since both engines
treat clockwise triangles as front faces): north becomes Godot's -Z and the town looks exactly the same.

    DIR/city/chunks/IX_IZ.bin  one Variant blob per 128 m chunk: [[group, mesh arrays or collision faces], ...]
    DIR/city/chunks.json       the chunk list
    DIR/city/extras.bin     {name: mesh arrays} for the sea, the distant hills, the countryside skirt
    DIR/city/colliders.bin  PackedFloat32Array, 7 floats per box: cx, cy(base), cz, sx, sy, sz, yaw(deg)
    DIR/city/water.bin      {"n", "cell", "sea", "levels": PackedByteArray of int16 cm (-32768 = dry)}, row = z index
    DIR/city/meta.json      lanes, footpaths, places, zones, lamps, objects ... in Godot coordinates
"""
import json
import os

import numpy as np

from gvariant import BYTES, COLORS, I32, V2, V3, encode

GROUP_IDS = {"world": 0, "foliage": 1, "water": 2, "terrain": 3, "coll": 4}
ARRAY_MAX = 13          # Mesh.ARRAY_MAX in Godot 4


def _mirror_mesh(a, coll=False):
    P = np.asarray(a["P"], np.float32).copy()
    P[:, 2] *= -1
    # Unity's front faces are clockwise in a left-handed frame, Godot's clockwise in a right-handed one: after the
    # z mirror the same index order already faces the right way
    I = np.asarray(a["I"], np.int64).reshape(-1, 3)
    if coll:
        return P, I
    N = np.asarray(a["N"], np.float32).copy()
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    N[:, 2] *= -1
    return P, I, N


def mesh_arrays(a):
    """Mesh.add_surface_from_arrays() input: vertex, normal, colour (tint + night glow in alpha), uv, uv2 (layers)."""
    P, I, N = _mirror_mesh(a)
    C = np.zeros((len(P), 4), np.float32)
    C[:, :3] = np.clip(a["C"], 0, 1)
    C[:, 3] = np.clip(a["E"], 0, 1)
    # texture layers, ambient occlusion and blend go in UV2 as whole numbers (exact in floats, read in the vertex
    # shader): x = layer + 256 * second layer, y = 256 * ao (0..255) + blend (0..255)
    S = np.clip(np.round(a["S"]), 0, 255)
    S2 = np.clip(np.round(a["S2"]), 0, 255) if "S2" in a else S
    AO = np.clip(np.round(a["AO"] * 255), 0, 255)
    B = np.clip(np.round(a["B"] * 255), 0, 255) if "B" in a else np.zeros(len(P))
    UV2 = np.stack([S + 256.0 * S2, 256.0 * AO + B], -1)
    arr = [None] * ARRAY_MAX
    arr[0] = V3(P)
    arr[1] = V3(N)
    arr[3] = COLORS(C)
    UV = np.asarray(a["UV"], np.float32).copy()
    UV[:, 1] = 1.0 - UV[:, 1]                 # Unity's textures start at the bottom row, Godot's at the top
    arr[4] = V2(UV)
    arr[5] = V2(UV2)
    arr[12] = I32(I.reshape(-1))
    return arr


def coll_faces(a):
    P, I = _mirror_mesh(a, coll=True)
    return V3(P[I.reshape(-1)])


def write_chunks(M, city_dir, groups_order):
    """One file per chunk (the game reads each whole, no seeking inside a compressed APK) and an index."""
    keys = sorted(set((k[0], k[1]) for k in M.m))
    out = os.path.join(city_dir, "chunks")
    os.makedirs(out, exist_ok=True)
    index = []
    total = 0
    for ix, iz in keys:
        surf = []
        for g in groups_order:
            m = M.m.get((ix, iz, g))
            if m is None or m.n == 0 or not m.I:
                continue
            a = m.arrays()
            surf.append([GROUP_IDS[g], coll_faces(a) if g == "coll" else mesh_arrays(a)])
        b = encode(surf)
        with open(os.path.join(out, "%d_%d.bin" % (ix, iz)), "wb") as f:
            f.write(b)
        index.append([ix, iz])
        total += len(b)
    with open(os.path.join(city_dir, "chunks.json"), "w") as f:
        json.dump({"size": float(M.size), "chunks": index}, f)
    return len(index), total


def write_extras(M, path):
    out = {}
    for name, m in M.extras.items():
        a = m.arrays()
        if a is not None and len(a["I"]):
            out[name] = mesh_arrays(a)
    with open(path, "wb") as f:
        f.write(encode(out))


def write_colliders(cols, path):
    arr = np.asarray(cols, np.float32).reshape(-1, 7).copy()
    arr[:, 2] *= -1
    arr[:, 6] *= -1
    from gvariant import F32
    with open(path, "wb") as f:
        f.write(encode(F32(arr)))
    return len(arr)


def write_water(LY, path, cell=4.0):
    n = int(2 * LY.HALF / cell)
    g = (np.arange(n) + 0.5) * cell - LY.HALF
    X, Z = np.meshgrid(g, g)                 # row j: generator z = g[j]
    w = LY.water_info(X, Z)
    h = LY.height(X, Z)
    lv = np.where(np.isnan(w) | (h > w - 0.3), -32768, np.round(w * 100)).astype("<i2")
    lv = lv[::-1]                            # row j in Godot = Godot z index (z_godot = -z)
    with open(path, "wb") as f:
        f.write(encode({"n": n, "cell": float(cell), "sea": float(LY.SEA_LEVEL), "levels": BYTES(np.frombuffer(lv.tobytes(), np.uint8))}))


# ------------------------------------------------------------------------------------------------ meta
def _p3(p):
    return [round(float(p[0]), 2), round(float(p[1]), 2), round(-float(p[2]), 2)]


def _p2(p):
    return [round(float(p[0]), 2), round(-float(p[1]), 2)]


def convert_meta(meta):
    m = dict(meta)
    for k in ("lanes", "walks"):
        m[k] = [dict(l, pts=[_p3(p) for p in l["pts"]]) for l in meta.get(k, [])]
    m["junctions"] = [dict(j, p=_p3(j["p"])) for j in meta.get("junctions", [])]
    m["bridges"] = [dict(b, p0=_p3(b["p0"]), p1=_p3(b["p1"])) for b in meta.get("bridges", [])]
    for k in ("points", "landmarks", "objects"):
        out = []
        for o in meta.get(k, []):
            o = dict(o)
            if "p" in o:
                o["p"] = _p3(o["p"])
            if "yaw" in o:
                o["yaw"] = round(-float(o["yaw"]), 1)
            out.append(o)
        m[k] = out
    m["lamps"] = [_p3(p) for p in meta.get("lamps", [])]
    m["zones"] = [dict(z, c=_p2(z["c"])) for z in meta.get("zones", [])]
    m["ponds"] = [dict(p, c=_p2(p["c"])) for p in meta.get("ponds", [])]
    if "lake" in meta:
        m["lake"] = dict(meta["lake"], c=_p2(meta["lake"]["c"]))
    if "river" in meta:
        m["river"] = dict(meta["river"], pts=[_p2(p) for p in meta["river"]["pts"]])
    m["roads"] = [dict(r, pts=[_p2(p) for p in r["pts"]]) for r in meta.get("roads", [])]
    if "sun" in meta:
        # the generator's azimuth is measured from north towards east; the same compass direction in Godot
        m["sun"] = dict(meta["sun"])
    m["frame"] = "godot"
    return m


def write_all(res, out_dir, LY, groups_order, meta):
    city = os.path.join(out_dir, "city")
    os.makedirs(city, exist_ok=True)
    n, size = write_chunks(res["M"], city, groups_order)
    write_extras(res["M"], os.path.join(city, "extras.bin"))
    nc = write_colliders(res["colliders"], os.path.join(city, "colliders.bin"))
    write_water(LY, os.path.join(city, "water.bin"))
    with open(os.path.join(city, "meta.json"), "w") as f:
        json.dump(convert_meta(meta), f, separators=(",", ":"))
    return "godot: %d chunks, %.1f MB, %d colliders" % (n, size / 1e6, nc)
