"""Signed-distance sculpting kit - numpy only, so it runs inside Blender's own Python and on a dev machine.

Every body part, fold and dent is a signed distance field blended into the others with a smooth minimum, so
muscles, joints and faces flow into each other like clay instead of reading as separate geometric parts.
A list of shapes is sampled on a voxel grid and meshed with Surface Nets; each vertex is then snapped onto
the exact surface with a Newton step along the field gradient, which gives clean, accurate high-poly meshes.

Coordinates are Blender's: metres, +Z up.
"""
import math

import numpy as np


# ------------------------------------------------------------------------------------------------ frames
def frame(fwd, up_hint=(0.0, 0.0, 1.0)):
    """Rotation matrix whose columns are (side, up, fwd) local axes: local z runs along `fwd`."""
    f = np.asarray(fwd, float)
    f = f / np.linalg.norm(f)
    u = np.asarray(up_hint, float)
    if abs(float(np.dot(u, f))) > 0.98:
        u = np.array([1.0, 0.0, 0.0]) if abs(f[0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    s = np.cross(u, f)
    s /= np.linalg.norm(s)
    u = np.cross(f, s)
    return np.stack([s, u, f], axis=1)


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], float)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], float)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], float)


# ------------------------------------------------------------------------------------------------ shapes
class Shape:
    """One sculpting stroke. op: 'add' (smooth union), 'sub' (smooth carve), 'int' (smooth intersect)."""

    def __init__(self, kind, op="add", k=0.01, bone=None, group="body", tag="", **p):
        self.kind, self.op, self.k, self.bone, self.group, self.tag = kind, op, float(k), bone, group, tag
        self.p = {key: (np.asarray(v, float) if isinstance(v, (list, tuple, np.ndarray)) else v) for key, v in p.items()}
        if kind in ("ell", "box", "torus") and "R" not in self.p:
            self.p["R"] = np.eye(3)

    # -- distance
    def dist(self, P):
        p = self.p
        if self.kind == "sphere":
            return np.linalg.norm(P - p["c"], axis=1) - p["r"]
        if self.kind == "cone":
            return sd_round_cone(P, p["a"], p["b"], float(p["r1"]), float(p["r2"]))
        if self.kind == "ell":
            return sd_ellipsoid(P, p["c"], p["r"], p["R"])
        if self.kind == "box":
            return sd_round_box(P, p["c"], p["h"], p["R"], float(p.get("rad", 0.0)))
        if self.kind == "torus":
            return sd_torus(P, p["c"], p["R"], float(p["ra"]), float(p["rb"]), p.get("sx", 1.0), p.get("sy", 1.0))
        if self.kind == "plane":              # half space below the plane through c with normal n
            return (P - p["c"]) @ (p["n"] / np.linalg.norm(p["n"]))
        raise ValueError(self.kind)

    # -- conservative bounds of the shape itself
    def bounds(self):
        p = self.p
        if self.kind == "sphere":
            r = float(p["r"])
            return p["c"] - r, p["c"] + r
        if self.kind == "cone":
            r = max(float(p["r1"]), float(p["r2"]))
            return np.minimum(p["a"], p["b"]) - r, np.maximum(p["a"], p["b"]) + r
        if self.kind == "ell":
            ext = np.sqrt(((p["R"] * p["r"][None, :]) ** 2).sum(axis=1))
            return p["c"] - ext, p["c"] + ext
        if self.kind == "box":
            ext = np.abs(p["R"]) @ p["h"]
            return p["c"] - ext, p["c"] + ext
        if self.kind == "torus":
            e = (float(p["ra"]) * max(float(p.get("sx", 1.0)), float(p.get("sy", 1.0))) + float(p["rb"])) * 1.05
            return p["c"] - e, p["c"] + e
        if self.kind == "plane":
            return np.full(3, -1e3), np.full(3, 1e3)
        raise ValueError(self.kind)


def sd_round_cone(P, a, b, r1, r2):
    """Exact distance to a cone capped by two spheres (Inigo Quilez)."""
    ba = b - a
    l2 = float(ba @ ba)
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = P - a
    y = pa @ ba
    z = y - l2
    t = pa * l2 - y[:, None] * ba[None, :]
    x2 = np.einsum("ij,ij->i", t, t)
    y2 = y * y * l2
    z2 = z * z * l2
    k = math.copysign(rr * rr, rr) * x2
    d = (np.sqrt(np.maximum(x2 * a2 * il2, 0.0)) + y * rr) * il2 - r1
    m1 = np.sign(z) * a2 * z2 > k
    m2 = (np.sign(y) * a2 * y2 < k) & ~m1
    d[m1] = np.sqrt(x2[m1] + z2[m1]) * il2 - r2
    d[m2] = np.sqrt(x2[m2] + y2[m2]) * il2 - r1
    return d


def sd_ellipsoid(P, c, r, R):
    q = (P - c) @ R
    k0 = np.linalg.norm(q / r, axis=1)
    k1 = np.linalg.norm(q / (r * r), axis=1)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-12)


def sd_round_box(P, c, h, R, rad):
    q = np.abs((P - c) @ R) - (h - rad)
    return np.linalg.norm(np.maximum(q, 0.0), axis=1) + np.minimum(q.max(axis=1), 0.0) - rad


def sd_torus(P, c, R, ra, rb, sx=1.0, sy=1.0):
    """Ring in the local x/y plane (local z = axis); sx/sy stretch it into an oval (approximate distance)."""
    q = (P - c) @ R
    qx, qy = q[:, 0] / sx, q[:, 1] / sy
    s = min(sx, sy)
    ring = np.sqrt(qx * qx + qy * qy) - ra
    return np.sqrt((ring * s) ** 2 + q[:, 2] ** 2) - rb


def smin(a, b, k):
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def combine(d, di, op, k):
    if op == "add":
        return smin(d, di, k)
    if op == "sub":
        return smax(d, -di, k)
    if op == "int":
        return smax(d, di, k)
    raise ValueError(op)


# ------------------------------------------------------------------------------------------------ evaluation
FAR = 0.08


def eval_points(shapes, P, far=FAR):
    """Field value at arbitrary points (N, 3)."""
    P = np.asarray(P, float)
    d = np.full(len(P), far)
    for s in shapes:
        lo, hi = s.bounds()
        m = s.k + far * 0.5
        sel = np.all((P >= lo - m) & (P <= hi + m), axis=1)
        if s.op == "int":
            sel[:] = True
        if not sel.any():
            continue
        idx = np.nonzero(sel)[0]
        d[idx] = combine(d[idx], s.dist(P[idx]), s.op, s.k)
    return d


def gradient(shapes, P, eps=4e-4):
    g = np.zeros_like(P)
    for i in range(3):
        o = np.zeros(3)
        o[i] = eps
        g[:, i] = (eval_points(shapes, P + o) - eval_points(shapes, P - o)) / (2 * eps)
    return g


def eval_grid(shapes, lo, hi, h, far=FAR, log=None):
    """Sample the field on a regular grid -> (F float32 (nx, ny, nz), origin)."""
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    n = np.ceil((hi - lo) / h).astype(int) + 1
    F = np.full(tuple(n), far, np.float32)
    for si, s in enumerate(shapes):
        blo, bhi = s.bounds()
        m = s.k + 2.5 * h
        if s.op == "int":
            i0, i1 = np.zeros(3, int), n.copy()
        else:
            i0 = np.clip(np.floor((blo - m - lo) / h).astype(int), 0, n)
            i1 = np.clip(np.ceil((bhi + m - lo) / h).astype(int) + 1, 0, n)
        if np.any(i1 <= i0):
            continue
        # slab by slab along z keeps the temporary arrays small
        xs = lo[0] + np.arange(i0[0], i1[0]) * h
        ys = lo[1] + np.arange(i0[1], i1[1]) * h
        X, Y = np.meshgrid(xs, ys, indexing="ij")
        X = X.ravel()
        Y = Y.ravel()
        for kk in range(i0[2], i1[2]):
            P = np.empty((len(X), 3))
            P[:, 0] = X
            P[:, 1] = Y
            P[:, 2] = lo[2] + kk * h
            blk = F[i0[0]:i1[0], i0[1]:i1[1], kk].astype(np.float64).ravel()
            blk = combine(blk, s.dist(P), s.op, s.k)
            F[i0[0]:i1[0], i0[1]:i1[1], kk] = blk.reshape(i1[0] - i0[0], i1[1] - i0[1])
        if log and si % 20 == 0:
            log("  sdf %d/%d" % (si + 1, len(shapes)))
    return F, lo


def surface_nets(F, origin, h):
    """Naive Surface Nets: one vertex per cell that straddles the surface, one quad per crossing grid edge.
    Returns (verts (N, 3), tris (M, 3)) with outward winding (field < 0 is inside)."""
    s = F < 0.0
    nx, ny, nz = F.shape
    corners = [s[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i in (0, 1) for j in (0, 1) for k in (0, 1)]
    any_in = np.zeros(corners[0].shape, bool)
    all_in = np.ones(corners[0].shape, bool)
    for c in corners:
        any_in |= c
        all_in &= c
    active = any_in & ~all_in
    del corners, any_in, all_in
    nv = int(active.sum())
    idx = np.full(active.shape, -1, np.int64)
    idx[active] = np.arange(nv)
    cdims = np.array(active.shape)
    tris = []
    acc_ci, acc_pt = [], []
    for axis in range(3):
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[axis] = slice(0, F.shape[axis] - 1)
        sl1[axis] = slice(1, F.shape[axis])
        f0 = F[tuple(sl0)]
        f1 = F[tuple(sl1)]
        ch = (f0 < 0.0) != (f1 < 0.0)
        e = np.argwhere(ch)                                         # edge start grid indices
        a0 = f0[ch].astype(np.float64)
        a1 = f1[ch].astype(np.float64)
        t = a0 / (a0 - a1)
        pt = e.astype(np.float64)
        pt[:, axis] += t
        inside_low = a0 < 0.0
        o1, o2 = [ax for ax in range(3) if ax != axis]
        # the four cells around the edge
        cells = []
        for d1, d2 in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            c = e.copy()
            c[:, o1] += d1
            c[:, o2] += d2
            cells.append(c)
        for c in cells:
            ok = np.all((c >= 0) & (c < cdims), axis=1)
            ci = idx[c[ok, 0], c[ok, 1], c[ok, 2]]
            good = ci >= 0
            acc_ci.append(ci[good])
            acc_pt.append(pt[ok][good])
        # quads only for edges with all four cells inside the grid
        ok = np.ones(len(e), bool)
        q = []
        for c in cells:
            ok &= np.all((c >= 0) & (c < cdims), axis=1)
        for c in cells:
            q.append(idx[c[:, 0].clip(0, cdims[0] - 1), c[:, 1].clip(0, cdims[1] - 1), c[:, 2].clip(0, cdims[2] - 1)])
        q = np.stack(q, axis=1)
        ok &= np.all(q >= 0, axis=1)
        q = q[ok]
        il = inside_low[ok]
        # winding: (o1, o2) order gives +axis normal for x (y,z), y (z,x)?, z (x,y)
        flip = axis == 1                                            # for y the cyclic order of (o1, o2) = (x, z) is reversed
        want_pos = il if not flip else ~il
        qq = np.where(want_pos[:, None], q, q[:, ::-1])
        tris.append(np.concatenate([qq[:, [0, 1, 2]], qq[:, [0, 2, 3]]], axis=0))
    ci = np.concatenate(acc_ci) if acc_ci else np.zeros(0, np.int64)
    pt = np.concatenate(acc_pt) if acc_pt else np.zeros((0, 3))
    cnt = np.bincount(ci, minlength=nv).astype(np.float64)
    acc = np.stack([np.bincount(ci, weights=pt[:, d], minlength=nv) for d in range(3)], axis=1)
    cell_pos = np.argwhere(active).astype(np.float64)
    vg = np.where(cnt[:, None] > 0, acc / np.maximum(cnt[:, None], 1.0), cell_pos + 0.5)
    verts = np.asarray(origin, float) + vg * h
    tris = np.concatenate(tris, axis=0) if tris else np.zeros((0, 3), np.int64)
    return verts, tris.astype(np.int64)


def snap(shapes, V, iters=2):
    """Newton steps onto the zero surface."""
    for _ in range(iters):
        d = eval_points(shapes, V)
        g = gradient(shapes, V)
        gg = np.maximum((g * g).sum(axis=1), 1e-9)
        step = (d / gg)[:, None] * g
        n = np.linalg.norm(step, axis=1)
        lim = 0.004
        step *= np.minimum(1.0, lim / np.maximum(n, 1e-12))[:, None]
        V = V - step
    return V


def normals(shapes, V):
    g = gradient(shapes, V)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def compact(V, T):
    """Drop unused vertices and degenerate triangles."""
    T = T[(T[:, 0] != T[:, 1]) & (T[:, 1] != T[:, 2]) & (T[:, 0] != T[:, 2])]
    used = np.unique(T)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[T]


def largest_parts(V, T, keep=1, min_tris=0):
    """Keep the biggest connected pieces (removes stray specks)."""
    n = len(V)
    parent = np.arange(n)

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    # union-find over edges (vectorised-ish: iterate until stable using min labels)
    lab = np.arange(n)
    e = np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]], axis=0)
    for _ in range(200):
        a = lab[e[:, 0]]
        b = lab[e[:, 1]]
        m = np.minimum(a, b)
        new = lab.copy()
        np.minimum.at(new, e[:, 0], m)
        np.minimum.at(new, e[:, 1], m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    tl = lab[T[:, 0]]
    ids, counts = np.unique(tl, return_counts=True)
    order = np.argsort(-counts)
    keep_ids = set(int(ids[i]) for i in order[:keep] if counts[i] >= min_tris)
    m = np.array([int(x) in keep_ids for x in tl])
    return compact(V, T[m])


def mesh_from_shapes(shapes, lo, hi, h, log=None, snap_iters=2, keep=1):
    F, origin = eval_grid(shapes, lo, hi, h, log=log)
    V, T = surface_nets(F, origin, h)
    del F
    V, T = compact(V, T)
    if keep:
        V, T = largest_parts(V, T, keep=keep)
    if snap_iters:
        V = snap(shapes, V, snap_iters)
    return V, T


def bone_weights(shapes, V, tau=0.012, top=4):
    """Skin weights from the sculpt itself: each vertex follows the bones of the shapes it is closest to,
    blended softly where shapes merge (joints get natural two-bone blends)."""
    bones = sorted(set(s.bone for s in shapes if s.bone and s.op == "add"))
    bi = {b: i for i, b in enumerate(bones)}
    best = np.full(len(V), 1e9)
    per = []
    for s in shapes:
        if s.op != "add" or not s.bone:
            continue
        d = np.full(len(V), 1e9)
        lo, hi = s.bounds()
        sel = np.all((V >= lo - 0.06) & (V <= hi + 0.06), axis=1)
        if sel.any():
            d[sel] = s.dist(V[sel])
        per.append((bi[s.bone], d))
        best = np.minimum(best, d)
    W = np.zeros((len(V), len(bones)))
    for b, d in per:
        w = np.exp(-np.clip(d - best, 0.0, 40 * tau) / tau)
        W[:, b] = np.maximum(W[:, b], w)
    # keep the strongest `top` influences
    if W.shape[1] > top:
        cut = np.sort(W, axis=1)[:, -top][:, None]
        W = np.where(W >= cut, W, 0.0)
    W /= np.maximum(W.sum(axis=1, keepdims=True), 1e-12)
    return bones, W
