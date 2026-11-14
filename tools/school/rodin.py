"""Hyper3D (Rodin) models in place of the code-built furniture.

Each Rodin model listed in rodin_models.json replaces one furniture kind everywhere it is used. The model is
turned to face the same way as the code-built piece (front = -Y in the piece's own frame, which is also where
Rodin puts the front of its models), then scaled into the code-built piece's bounding box: the height exactly
(table tops, almirah height and wall fittings stay where the game expects them), the width and depth as closely
as the model's own proportions allow, never spilling more than a few cm past the footprint. Numpy only, so the
same fit runs in Blender (build) and in plain Python (previews).
"""
import json
import os

import numpy as np

from geo import Geo, rot_x, rot_y, rot_z
import glb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MANIFEST = os.path.join(HERE, "rodin_models.json")
RAW = os.path.join(ROOT, "build", "rodin", "raw")


def available(raw_dir=RAW):
    """kind -> manifest entry (+ 'path') for every Rodin model whose .glb is present."""
    if not os.path.exists(MANIFEST):
        return {}
    out = {}
    for k, v in json.load(open(MANIFEST))["models"].items():
        p = os.path.join(raw_dir, "%s__%s.glb" % (k, v["gen"]))
        if os.path.exists(p):
            out[k] = dict(v, path=p)
    return out


def _all_points(g, parts):
    P = [np.asarray(g.V, float)] if len(g.V) else []
    for _n, (pg, off) in parts.items():
        if len(pg.V):
            P.append(np.asarray(pg.V, float) + np.asarray(off, float))
    return np.vstack(P)


def _sample(V, F, n=6000, seed=1):
    """Points spread over the triangle surfaces (area weighted)."""
    rng = np.random.default_rng(seed)
    T = V[F[:, :3]]
    a = 0.5 * np.linalg.norm(np.cross(T[:, 1] - T[:, 0], T[:, 2] - T[:, 0]), axis=1)
    if a.sum() <= 0:
        return V
    idx = rng.choice(len(F), size=n, p=a / a.sum())
    r1, r2 = rng.random(n), rng.random(n)
    s = np.sqrt(r1)
    return (1 - s)[:, None] * T[idx, 0] + (s * (1 - r2))[:, None] * T[idx, 1] + (s * r2)[:, None] * T[idx, 2]


def _ref_samples(g, parts, n=6000):
    pts = []
    for G, off in [(g, (0, 0, 0))] + [(pg, o) for (pg, o) in parts.values()]:
        if not len(G.V):
            continue
        V = np.asarray(G.V, float) + np.asarray(off, float)
        tris = []
        for f in G.F:
            for i in range(1, len(f) - 1):
                tris.append((f[0], f[i], f[i + 1]))
        if tris:
            pts.append(_sample(V, np.array(tris), n))
    return np.vstack(pts)


def _occ(P, lo, hi, res=22):
    d = np.maximum(hi - lo, 1e-6)
    ijk = np.floor((P - lo) / d * res).astype(int)
    ijk = ijk[np.all((ijk >= 0) & (ijk < res), axis=1)]
    g = np.zeros((res, res, res), bool)
    g[ijk[:, 0], ijk[:, 1], ijk[:, 2]] = True
    # 1-voxel dilation: the two surfaces never sit on exactly the same voxels
    d2 = g.copy()
    for ax in range(3):
        d2 |= np.roll(g, 1, ax) | np.roll(g, -1, ax)
    return d2


def _place(V, rlo, rhi, kind=""):
    """Scale V (already turned) into the reference box [rlo, rhi]: exact height, close width/depth."""
    lo, hi = V.min(0), V.max(0)
    d = np.maximum(hi - lo, 1e-6)
    rd = rhi - rlo
    sz = rd[2] / d[2]
    s = rd / d
    s[2] = sz
    for i in (0, 1):
        s[i] = float(np.clip(s[i], 0.75 * sz, 1.33 * sz))
        if d[i] * s[i] > rd[i] * 1.06 + 0.02:            # never spill past the footprint
            s[i] = (rd[i] * 1.06 + 0.02) / d[i]
    c = (lo + hi) / 2
    out = (V - c) * s
    rc = (rlo + rhi) / 2
    out[:, 0] += rc[0]
    out[:, 1] += rc[1]
    out[:, 2] += rlo[2] - out[:, 2].min()
    return out


def crop_slab(raw, half):
    """Keep only the triangles within +-half of the model's middle plane facing -Y (drops stands and feet)."""
    V, F = raw["V"], raw["F"]
    y0 = float(np.median(V[:, 1]))
    keep = np.abs(V[F].mean(1)[:, 1] - y0) <= half
    used = np.unique(F[keep])
    remap = -np.ones(len(V), int)
    remap[used] = np.arange(len(used))
    return dict(raw, V=V[used], UV=raw["UV"][used], F=remap[F[keep]])


def fit(kind, raw, ref_g, ref_parts, yaw_fix=0.0, turn=None):
    """-> (V fitted in the piece's own frame, chosen quarter turn, scores)."""
    V0 = raw["V"]
    F = raw["F"]
    refP = _all_points(ref_g, ref_parts)
    rlo, rhi = refP.min(0), refP.max(0)
    ref_occ = _occ(_ref_samples(ref_g, ref_parts), rlo - 0.02, rhi + 0.02)
    scores = []
    for k in range(4):
        Vk = V0 @ rot_z(90.0 * k).T
        Vf = _place(Vk, rlo, rhi, kind)
        o = _occ(_sample(Vf, F), rlo - 0.02, rhi + 0.02)
        inter = np.logical_and(o, ref_occ).sum()
        union = np.logical_or(o, ref_occ).sum()
        scores.append(inter / max(union, 1))
    k = 0
    # Rodin puts the front of a model where the code-built pieces have theirs (-Y); only turn it when another
    # quarter turn matches the code-built shape clearly better
    kb = int(np.argmax(scores))
    if scores[kb] > scores[0] * 1.12 + 0.02:
        k = kb
    ang = (90.0 * k if turn is None else float(turn)) + float(yaw_fix)
    Vf = _place(V0 @ rot_z(ang).T, rlo, rhi, kind)
    return Vf, ang, scores


def _upright(V):
    """Turn a fan so its downrod points up: the axis is the direction with the most lopsided spread of vertices."""
    best = (2, 0.0)
    for ax in range(3):
        c = V[:, ax]
        sk = float(np.mean(((c - c.mean()) / (c.std() + 1e-9)) ** 3))
        if abs(sk) > abs(best[1]):
            best = (ax, sk)
    ax, sk = best
    R = {(2, 1): np.eye(3), (2, -1): rot_x(180), (1, 1): rot_x(90), (1, -1): rot_x(-90),
         (0, 1): rot_y(-90), (0, -1): rot_y(90)}[(ax, 1 if sk > 0 else -1)]
    return V @ R.T


def fit_fan(raw, ref_g, ref_parts):
    """The whole Rodin fan becomes the turning part: upright, centred on its own axis, canopy at the ceiling,
    scaled evenly so the blades reach as far as the code-built fan's."""
    V = _upright(raw["V"].copy())
    refP = _all_points(ref_g, ref_parts)
    rlo, rhi = refP.min(0), refP.max(0)
    h = float(np.ptp(V[:, 2]))
    top = V[:, 2] > V[:, 2].max() - 0.12 * h
    axis = V[top, :2].mean(0)
    V[:, :2] -= axis
    r = np.sqrt((V[:, :2] ** 2).sum(1)).max()
    rr = np.sqrt((refP[:, :2] ** 2).sum(1)).max()
    s = rr / max(r, 1e-6)
    V *= s
    V[:, 2] += rhi[2] - V[:, 2].max()
    return V


def to_geo(V, F, UV, mat, name="rodin"):
    g = Geo(name)
    g.V = [p for p in np.asarray(V, float)]
    g.F = [list(map(int, f)) for f in F]
    UV = np.asarray(UV, float)
    g.UV = [[(float(UV[i, 0]), float(UV[i, 1])) for i in f] for f in F]
    g.M = [mat] * len(F)
    return g


def load(kind, entry, furn_fn):
    """-> (geo, parts, info) ready to replace furniture.FURN[kind]() in the build."""
    raw = glb.read(entry["path"])
    ref_g, ref_parts = furn_fn()
    mat = "rodin_" + kind
    if kind == "fan":
        Vf = fit_fan(raw, ref_g, ref_parts)
        off = np.asarray(ref_parts["rotor"][1], float)
        rotor = to_geo(Vf - off, raw["F"], raw["UV"], mat, "fan_rotor")
        return Geo("fan"), {"rotor": (rotor, tuple(off))}, {"yaw": 0.0, "scores": [], "tris": len(raw["F"]), "raw": raw}
    if entry.get("slab"):
        raw = crop_slab(raw, float(entry["slab"]))
    Vf, ang, scores = fit(kind, raw, ref_g, ref_parts, entry.get("yaw", 0.0), entry.get("turn"))
    g = to_geo(Vf, raw["F"], raw["UV"], mat, kind)
    return g, {}, {"yaw": ang, "scores": [round(float(s), 3) for s in scores], "tris": len(raw["F"]), "raw": raw}
