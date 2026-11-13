"""Ragini's hair: long, loose, matted black hair with a centre parting, grown as strand cards over her
sculpted head (numpy only). Each strand starts on the scalp, follows the skull, falls with gravity and is kept
off the head, shoulders and back by the body's distance field. A few strands hang over her face.

Returns card geometry plus a strand texture (RGBA, drawn here - no images used).
"""
import math

import numpy as np

import sdf

V3 = lambda *a: np.array(a, float)      # noqa: E731


def _n(v):
    return v / max(float(np.linalg.norm(v)), 1e-12)


def scalp_points(head_shapes, n, rng, top):
    """Points on the scalp above the hairline (rejection sampling on a sphere, projected onto the skull)."""
    c = V3(0, 0.018, 1.612)
    out = []
    tries = 0
    while len(out) < n and tries < 200000:
        tries += 1
        d = _n(rng.standard_normal(3))
        p = c + d * 0.11
        # hairline: high forehead in front, above the ears at the sides, down to the nape at the back
        front = -d[1]
        side = abs(d[0])
        z = p[2]
        if front > 0.55 and z < 1.668:
            continue
        if side > 0.62 and front > -0.2 and z < 1.615:
            continue
        if d[1] > 0.0 and z < 1.545:
            continue
        if z < 1.53:
            continue
        out.append(p)
    P = np.array(out)
    for _ in range(8):
        dd = sdf.eval_points(head_shapes, P)
        g = sdf.gradient(head_shapes, P)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        P = P - g * dd[:, None]
    return P


def grow_all(coll, roots, dirs, lengths, seg, rng, clear0, clear1, curl, gravity):
    """Grow many strands at once (vectorised): returns a list of (n_i, 3) polylines."""
    N = len(roots)
    n_seg = int(np.ceil(lengths.max() / seg))
    p = roots.copy()
    d = dirs / np.linalg.norm(dirs, axis=1, keepdims=True)
    wob = rng.uniform(0, 6.28, (N, 3))
    out = [p.copy()]
    for i in range(n_seg):
        t = np.minimum(1.0, (i * seg) / np.maximum(lengths, 1e-6))
        noise = np.stack([np.sin(i * 0.7 + wob[:, 0]), np.sin(i * 0.55 + wob[:, 1]), 0.3 * np.sin(i * 0.4 + wob[:, 2])], axis=1)
        d = d * (1.0 - gravity[:, None] * 0.35) + np.array([0, 0, -1.0]) * gravity[:, None] * 0.35 + noise * (curl[:, None] * 0.12)
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        p = p + d * seg
        clear = clear0 + (clear1 - clear0) * np.minimum(1.0, t * 1.6)
        for _ in range(3):
            v = sdf.eval_points(coll, p)
            bad = v < clear
            if not bad.any():
                break
            g = sdf.gradient(coll, p[bad])
            gn = np.linalg.norm(g, axis=1, keepdims=True)
            g = np.where(gn > 1e-6, g / np.maximum(gn, 1e-9), np.array([[0, 1.0, 0]]))
            p[bad] = p[bad] + g * (clear[bad] - v[bad])[:, None]
        out.append(p.copy())
    allp = np.stack(out, axis=1)                       # (N, n_seg + 1, 3)
    res = []
    for k in range(N):
        n = int(np.ceil(lengths[k] / seg)) + 1
        res.append(allp[k, :max(n, 3)])
    return res


def build(body, seed=21, n_cards=320, face_strands=6):
    rng = np.random.default_rng(seed)
    head_shapes = [s for s in body.shapes if s.bone in ("head", "jaw", "neck")]
    coll = [s for s in body.shapes if s.bone in ("head", "jaw", "neck", "chest", "spine", "clavicle.L", "clavicle.R",
                                                  "upper_arm.L", "upper_arm.R", "hips")]
    roots = scalp_points(head_shapes, n_cards, rng, body.marks.get("head_top"))
    dirs, lengths = [], []
    for r in roots:
        side = 1.0 if r[0] >= 0 else -1.0
        if abs(r[0]) < 0.004:
            side = float(rng.choice([-1.0, 1.0]))
        out = _n(r - V3(0, 0.018, 1.60))
        backness = float(np.clip((r[1] - 0.0) / 0.07, 0.0, 1.0))     # 0 = top/front, 1 = back of the head
        top_dir = V3(side * 0.9, 0.25 * (1 if r[1] > -0.02 else -0.3), -0.35)
        back_dir = V3(side * 0.18, 0.55, -0.8)
        dirs.append(_n(top_dir * (1 - backness) + back_dir * backness + out * 0.2))
        lengths.append(rng.uniform(0.55, 0.80) if r[1] > 0.02 else rng.uniform(0.42, 0.62))
    N = len(roots)
    polys = grow_all(coll, roots, np.array(dirs), np.array(lengths), 0.026, rng,
                     clear0=0.003 + rng.uniform(0, 0.004, N), clear1=rng.uniform(0.012, 0.04, N),
                     curl=rng.uniform(0.15, 0.45, N), gravity=rng.uniform(0.45, 0.7, N))
    strands = [(P, rng.uniform(0.016, 0.03), int(rng.integers(0, 4))) for P in polys]
    # strands falling over her face (one eye half hidden)
    fr, fd, fl = [], [], []
    for k in range(face_strands):
        x = rng.choice([-1.0, 1.0]) * rng.uniform(0.022, 0.05)      # beside the face, over one eye or a cheek
        r = V3(x * 0.8, -0.05, 1.685)
        for _ in range(6):
            dd = sdf.eval_points(head_shapes, r[None, :])
            g = sdf.gradient(head_shapes, r[None, :])
            r = r - _n(g[0]) * dd[0]
        fr.append(r)
        fd.append(_n(V3(x * 4.0, -0.55, -0.85)))
        fl.append(rng.uniform(0.30, 0.48))
    M = len(fr)
    polys = grow_all(coll, np.array(fr), np.array(fd), np.array(fl), 0.022, rng, clear0=np.full(M, 0.004),
                     clear1=np.full(M, 0.022), curl=np.full(M, 0.3), gravity=np.full(M, 0.75))
    strands += [(P, rng.uniform(0.012, 0.02), int(rng.integers(0, 4))) for P in polys]
    return cards(body, strands)


def cards(body, strands):
    V, UV, T, W, ROOT = [], [], [], [], []
    for (P, width, tile) in strands:
        n = len(P)
        base = len(V)
        tang = np.gradient(P, axis=0)
        tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)
        L = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        total = L[-1]
        for i in range(n):
            out = _n(P[i] - V3(0, 0.02, 1.45 if P[i][2] < 1.5 else 1.60))
            side = np.cross(tang[i], out)
            side = _n(side) if np.linalg.norm(side) > 1e-6 else V3(1, 0, 0)
            w = width * (0.75 + 0.5 * min(1.0, L[i] / 0.12)) * (1.0 - 0.6 * (L[i] / total) ** 2)
            for j, sgn in enumerate((-0.5, 0.5)):
                V.append(P[i] + side * w * sgn)
                UV.append(((tile + (j * 0.96 + 0.02)) / 4.0, L[i] / 0.8))
                ROOT.append(L[i])
        for i in range(n - 1):
            a = base + 2 * i
            T.append((a, a + 1, a + 3))
            T.append((a, a + 3, a + 2))
    return np.array(V), np.array(T), np.array(UV), np.array(ROOT)


def texture(w=512, h=1024, seed=4):
    """Strand texture: 4 tiles side by side, each a lock of matted black hair (RGBA float array)."""
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 4))
    tw = w // 4
    yy = np.arange(h)[:, None] / h
    for t in range(4):
        x0 = t * tw
        col = np.zeros((h, tw, 4))
        xs = np.arange(tw)[None, :]
        for k in range(70):
            cx = rng.uniform(0.08, 0.92) * tw
            amp = rng.uniform(0.5, 3.5)
            freq = rng.uniform(2, 9)
            ph = rng.uniform(0, 6.28)
            length = rng.uniform(0.55, 1.0)
            wdt = rng.uniform(0.5, 1.2)
            x = cx + amp * np.sin(yy * freq * 6.28 + ph) + (yy * rng.uniform(-4, 4))
            dist = np.abs(xs - x)
            a = np.clip(1.0 - dist / wdt, 0, 1) * (yy < length) * np.clip((length - yy) / 0.08, 0, 1)
            shade = rng.uniform(0.008, 0.05)
            grey = rng.random() < 0.06
            c = np.array([shade * 1.05, shade, shade * 0.95]) if not grey else np.array([0.32, 0.31, 0.3])
            m = a > col[:, :, 3]
            for ch in range(3):
                col[:, :, ch] = np.where(m, c[ch], col[:, :, ch])
            col[:, :, 3] = np.maximum(col[:, :, 3], a)
        # thinner towards the tips, a few stray hairs
        col[:, :, 3] *= np.clip(1.15 - yy * 0.35, 0, 1)
        img[:, x0:x0 + tw] = col
    return img
