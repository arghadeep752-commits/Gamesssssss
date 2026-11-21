"""Hyper3D (Rodin) models in the house: fitted into the furniture footprints and the item boxes (numpy only).

Rodin models face +Z in glTF, which is -Y in Blender: the same "front = -Y" the code-built pieces use, so a model
is normally only scaled: the height exactly to the footprint, the width and depth as close as its proportions allow
(never spilling more than a few cm past the footprint). A model can be turned with "turn" (degrees) in
tools/rodin/models.json if it comes out facing another way.
"""
import itertools
import json
import os

import numpy as np

import glb
from geo import Geo, rot_z

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
MANIFEST = os.path.join(ROOT, "tools", "rodin", "models.json")
RAW = os.path.join(ROOT, "build", "rodin", "raw")
_CACHE = {}


def manifest():
    return json.load(open(MANIFEST))["models"] if os.path.exists(MANIFEST) else {}


def available(raw_dir=RAW):
    """model name -> manifest entry + 'path' for every model whose .glb is present."""
    out = {}
    for k, v in manifest().items():
        p = os.path.join(raw_dir, "%s__%s.glb" % (k, v["gen"]))
        if os.path.exists(p):
            out[k] = dict(v, path=p)
    return out


def raw(name, entry):
    if name not in _CACHE:
        _CACHE[name] = glb.read(entry["path"])
    return _CACHE[name]


def to_geo(V, F, UV, mat, name="rodin"):
    """Geo with per-corner UVs; vertices split only for UV seams are welded so the model shades smoothly."""
    V = np.asarray(V, float)
    F = np.asarray(F, int)
    UV = np.asarray(UV, float)
    key = np.round(V / 1e-5).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    Fw = inv[F]
    ok = (Fw[:, 0] != Fw[:, 1]) & (Fw[:, 1] != Fw[:, 2]) & (Fw[:, 0] != Fw[:, 2])
    g = Geo(name)
    g.V = [p for p in V[first]]
    g.F = [list(map(int, f)) for f in Fw[ok]]
    g.UV = [[(float(UV[i, 0]), float(UV[i, 1])) for i in f] for f in F[ok]]
    g.M = [mat] * len(g.F)
    return g


def _place(V, w, d, h):
    """Scale V into the footprint box (x -w/2..w/2, y -d/2..d/2, z 0..h): exact height, close width / depth."""
    lo, hi = V.min(0), V.max(0)
    ext = np.maximum(hi - lo, 1e-6)
    sz = h / ext[2]
    s = np.array([w / ext[0], d / ext[1], sz])
    for i, lim in ((0, w), (1, d)):
        s[i] = float(np.clip(s[i], 0.8 * sz, 1.25 * sz))
        if ext[i] * s[i] > lim * 1.05 + 0.02:
            s[i] = (lim * 1.05 + 0.02) / ext[i]
    c = (lo + hi) / 2
    out = (V - c) * s
    out[:, 2] += -out[:, 2].min()
    return out, s


def fit_furniture(model, entry, w, d, h, name):
    """-> (Geo in the piece's own frame, info)."""
    r = raw(model, entry)
    V = r["V"].copy()
    turn = float(entry.get("turn", 0.0))
    if turn:
        V = V @ rot_z(turn).T
    ext = np.ptp(V, axis=0)
    # a long piece (sofa, bed, desk) whose model came out sideways: a quarter turn, only when it clearly is
    if entry.get("auto_turn", True) and not turn:
        fr = w / max(d, 1e-6)
        mr = ext[0] / max(ext[1], 1e-6)
        if (fr > 1.35 and mr < 0.8) or (fr < 0.74 and mr > 1.25):
            V = V @ rot_z(90.0).T
            turn = 90.0
    Vf, s = _place(V, w, d, h)
    g = to_geo(Vf, r["F"], r["UV"], "rodin_" + model, name)
    return g, {"model": model, "turn": turn, "scale": [round(float(x), 4) for x in s], "tris": int(len(r["F"]))}


def _rots24():
    out = []
    for perm in itertools.permutations(range(3)):
        for signs in itertools.product((1, -1), repeat=3):
            M = np.zeros((3, 3))
            for i, (pi, sg) in enumerate(zip(perm, signs)):
                M[i, pi] = sg
            if np.linalg.det(M) > 0:
                out.append(M)
    return out


def orient_to_box(V, dims):
    """The quarter turn (about any axis) whose box best matches the target's proportions."""
    dims = np.maximum(np.asarray(dims, float), 1e-6)
    best = None
    for M in _rots24():
        dd = np.maximum(np.ptp(V @ M.T, axis=0), 1e-6)
        e = np.log(dd) - np.log(dims)
        cost = float(np.sum((e - e.mean()) ** 2)) + 0.03 * (3.0 - float(np.trace(M)))
        if best is None or cost < best[0]:
            best = (cost, M)
    return best[1]


def fit_box(model, entry, dims, name, mode="fit"):
    """A model (an item, a padlock) fitted into a box of size dims standing on z = 0, centred on x / y."""
    r = raw(model, entry)
    dims = np.asarray(dims, float)
    V = r["V"] @ orient_to_box(r["V"], dims).T
    lo, hi = V.min(0), V.max(0)
    ext = np.maximum(hi - lo, 1e-9)
    if mode == "exact":
        V = (V - lo) / ext * dims - np.array([dims[0] / 2, dims[1] / 2, 0.0])
    else:
        s = float(np.min(dims / ext))
        V = (V - (lo + hi) / 2) * s
        V[:, 2] -= V[:, 2].min()
    return to_geo(V, r["F"], r["UV"], "rodin_" + model, name)


def surface_z(g, lx, ly, zmax=1e9):
    """Height of the highest surface of g straight below (lx, ly) and under zmax, or None."""
    V = np.asarray(g.V, float)
    tris = np.array([(f[0], f[i], f[i + 1]) for f in g.F for i in range(1, len(f) - 1)])
    if not len(tris):
        return None
    A, B, C = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    v0, v1 = B[:, :2] - A[:, :2], C[:, :2] - A[:, :2]
    v2 = np.array([lx, ly]) - A[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-12
    den = np.where(ok, den, 1.0)
    b1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
    b2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
    inside = ok & (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)
    if not inside.any():
        return None
    z = A[:, 2] + b1 * (B[:, 2] - A[:, 2]) + b2 * (C[:, 2] - A[:, 2])
    z = z[inside & (z < zmax)]
    return float(z.max()) if len(z) else None
