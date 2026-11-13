"""Ragini's saree, built around her sculpted body (numpy only).

* skirt  - the lower saree: tied at the waist, falling to just above her ankles, with the pleats (chunnat)
           fanned out at the front and a ragged, torn hem
* pallu  - the loose end: across her chest from the right hip, over the left shoulder, hanging down her back

Both are open cloth surfaces with their own UVs (u along the cloth, v across it, 0 = border edge).
"""
import math

import numpy as np

import sdf

V3 = lambda *a: np.array(a, float)      # noqa: E731


def _noise1(n, seed, octaves=((3, 1.0), (7, 0.5), (17, 0.25))):
    """Smooth periodic 1D noise sampled at n points around a circle."""
    rng = np.random.default_rng(seed)
    t = np.linspace(0, 2 * np.pi, n, endpoint=False)
    out = np.zeros(n)
    for f, a in octaves:
        ph = rng.uniform(0, 2 * np.pi)
        out += a * np.sin(f * t + ph)
    return out / sum(a for _, a in octaves)


def support(shapes, z, center=(0.0, 0.01), dirs=None, half=0.32, step=0.004):
    """Support function of the body's cross-section at height z: how far the body reaches in each direction."""
    xs = np.arange(-half, half, step)
    ys = np.arange(-0.25, 0.25, step)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], axis=1)
    d = sdf.eval_points(shapes, P)
    inside = P[d < 0.0][:, :2] - np.asarray(center)
    if len(inside) == 0:
        return np.zeros(len(dirs))
    return (inside @ dirs.T).max(axis=0)


def skirt(body, n_theta=112, n_rings=44, seed=3):
    shapes = [s for s in body.shapes if s.bounds()[0][2] < 1.12]        # hips, belly, legs
    th = np.linspace(0, 2 * np.pi, n_theta, endpoint=False)
    # theta = 0 points straight forward (-Y), increasing towards her left (+X)
    dirs = np.stack([np.sin(th), -np.cos(th)], axis=1)
    c = np.array([0.0, 0.012])
    waist_z = 1.000 - 0.022 * np.cos(th)                                 # lower in front, higher at the back
    hem_base = 0.118
    hem = hem_base + 0.022 * _noise1(n_theta, seed) + 0.012 * _noise1(n_theta, seed + 1, ((23, 1.0), (41, 0.6)))
    # a few torn tongues of cloth hanging lower
    rng = np.random.default_rng(seed)
    for _ in range(5):
        k = rng.integers(0, n_theta)
        w = rng.integers(2, 5)
        for j in range(-w, w + 1):
            hem[(k + j) % n_theta] -= 0.03 * (1 - abs(j) / (w + 1)) * rng.uniform(0.5, 1.0)
    t_rings = np.linspace(0.0, 1.0, n_rings) ** 1.35                     # denser near the waist
    zs_probe = np.linspace(1.0, 0.13, 30)
    sup = np.array([support(shapes, z, c, dirs) for z in zs_probe])      # (30, n_theta)
    sup = np.maximum(sup, 0.03)
    widest = sup.max(axis=0)                                             # the hips
    V = np.zeros((n_rings, n_theta + 1, 3))
    UV = np.zeros((n_rings, n_theta + 1, 2))
    fold_seed = np.random.default_rng(seed + 7)
    folds = sum(a * np.sin(f * th + fold_seed.uniform(0, 6.28)) for f, a in ((5, 1.0), (9, 0.6), (14, 0.35), (22, 0.2)))
    folds /= 2.15
    for ri, t in enumerate(t_rings):
        z = waist_z + (hem - waist_z) * t
        # body support at this height (interpolated)
        r = np.array([np.interp(z[j], zs_probe[::-1], sup[::-1, j]) for j in range(n_theta)])
        below_hips = np.clip((0.92 - z) / 0.6, 0.0, 1.0)
        r = np.maximum(r, widest * (1.0 - 0.06 * below_hips) * np.clip((1.0 - z) / 0.08 + 0.2, 0.0, 1.0))
        r = np.maximum(r, sup[0])
        r = r + 0.011 + 0.03 * t ** 1.6                                  # cloth offset + gentle flare
        # circular smoothing: cloth bridges the dip between the legs
        k = 5
        rp = np.concatenate([r[-k:], r, r[:k]])
        r = np.convolve(rp, np.ones(2 * k + 1) / (2 * k + 1), mode="same")[k:-k]
        # front pleats (chunnat): a fan of 9 folds, deeper towards the hem
        phi = np.angle(np.exp(1j * th))                                  # -pi..pi, 0 = front
        half = 0.22 + 0.26 * t
        u = (phi + half) / (2 * half)
        inside = (u > 0) & (u < 1)
        tri = 1.0 - np.abs(2.0 * ((u * 9.0) % 1.0) - 1.0)
        pleat = (0.004 + 0.02 * t ** 0.8) * (tri ** 1.5) * inside * np.sin(np.clip(u, 0, 1) * np.pi) ** 0.3
        r = r + pleat + folds * (0.002 + 0.01 * t ** 1.5) * (1 - inside)
        x = np.sin(th) * r + c[0]
        y = -np.cos(th) * r + c[1]
        V[ri, :n_theta] = np.stack([x, y, z], axis=1)
        V[ri, n_theta] = V[ri, 0]
    # UVs: u around (arc length), v up from the hem (border at v = 0)
    for ri in range(n_rings):
        seg = np.linalg.norm(np.diff(V[ri, :, :2], axis=0), axis=1)
        arc = np.concatenate([[0], np.cumsum(seg)])
        UV[ri, :, 0] = arc / max(arc[-1], 1e-6)
    hem_z = np.concatenate([hem, hem[:1]])
    waist = np.concatenate([waist_z, waist_z[:1]])
    UV[:, :, 1] = (V[:, :, 2] - hem_z[None, :]) / (waist - hem_z)[None, :]
    # faces
    idx = np.arange(n_rings * (n_theta + 1)).reshape(n_rings, n_theta + 1)
    a = idx[:-1, :-1].ravel()
    b = idx[:-1, 1:].ravel()
    c2 = idx[1:, 1:].ravel()
    d = idx[1:, :-1].ravel()
    T = np.concatenate([np.stack([a, d, c2], 1), np.stack([a, c2, b], 1)])
    return V.reshape(-1, 3), T, UV.reshape(-1, 2), {"waist_z": waist_z, "hem": hem, "n_theta": n_theta, "n_rings": n_rings}


def _project(shapes, P, offset):
    """Put points onto the body surface (Newton), then lift them by `offset` along the normal."""
    for _ in range(6):
        d = sdf.eval_points(shapes, P)
        g = sdf.gradient(shapes, P)
        g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
        P = P - g * d[:, None]
    g = sdf.gradient(shapes, P)
    gn = np.linalg.norm(g, axis=1, keepdims=True)
    g = np.where(gn > 0.3, g / np.maximum(gn, 1e-9), 0.0)
    # far from the body (no field there): face straight out of her front or back
    fb = np.where(P[:, 1:2] > 0.02, 1.0, -1.0) * np.array([[0.0, 1.0, 0.0]])
    g = np.where(gn > 0.3, g, fb)
    off = np.asarray(offset, float)
    if off.ndim == 1:
        off = off[:, None]
    return P + g * off, g


def pallu(body, n_len=46, n_wid=14, seed=5):
    """Across the chest from her right hip, over the left shoulder, down her back to the knees."""
    torso = [s for s in body.shapes if s.bone in ("hips", "spine", "chest", "neck", "clavicle.L", "upper_arm.L")
             and s.bounds()[0][2] > 0.6]
    sh = body.bones["upper_arm.L"][0]
    # centre line (rough), then projected onto the body; s runs 0 (hip) -> 1 (back hem)
    ctrl = np.array([
        [-0.115, -0.085, 0.985],
        [-0.075, -0.110, 1.100],
        [-0.010, -0.120, 1.215],
        [0.060, -0.095, 1.315],
        [0.115, -0.045, 1.405],
        [0.135, 0.020, 1.430],
        [0.130, 0.085, 1.385],
        [0.100, 0.120, 1.250],
        [0.080, 0.135, 1.050],
        [0.068, 0.140, 0.820],
        [0.060, 0.140, 0.560],
    ])
    s_ctrl = np.linspace(0, 1, len(ctrl))
    s = np.linspace(0, 1, n_len)
    C = np.stack([np.interp(s, s_ctrl, ctrl[:, i]) for i in range(3)], axis=1)
    # smooth the polyline a little
    for _ in range(3):
        C[1:-1] = 0.25 * C[:-2] + 0.5 * C[1:-1] + 0.25 * C[2:]
    over_body = C[:, 2] > 1.17                    # part lying on the chest/shoulder/back
    # width: wide at the hip, folded narrow over the shoulder, spread out down the back
    wid = np.interp(s, [0, 0.2, 0.45, 0.55, 0.7, 1.0], [0.30, 0.24, 0.13, 0.12, 0.26, 0.34])
    tang = np.gradient(C, axis=0)
    tang /= np.linalg.norm(tang, axis=1, keepdims=True)
    Cp, nrm = _project(torso, C.copy(), 0.012)
    V = np.zeros((n_len, n_wid, 3))
    UV = np.zeros((n_len, n_wid, 2))
    rng = np.random.default_rng(seed)
    acc = 0.0
    lengths = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(C, axis=0), axis=1))])
    for i in range(n_len):
        n = nrm[i]
        side = np.cross(tang[i], n)
        side /= np.linalg.norm(side)
        w = np.linspace(-0.5, 0.5, n_wid) * wid[i]
        P = Cp[i][None, :] + side[None, :] * w[:, None]
        if C[i, 2] > 1.12 or s[i] < 0.35:
            P, nn = _project(torso, P, 0.010 + 0.006 * np.abs(np.linspace(-1, 1, n_wid)))
        else:
            nn = np.tile(n, (n_wid, 1))
        # hanging part: the cloth falls straight down from the shoulder blades instead of hugging the waist
        if s[i] > 0.62:
            yb = 0.115 + 0.03 * (s[i] - 0.62) / 0.38
            P[:, 1] = np.maximum(P[:, 1], yb + 0.01 * np.cos(np.linspace(0, np.pi, n_wid)))
        # folds across the width: pleated over the shoulder, soft waves elsewhere
        k = np.linspace(0, 1, n_wid)
        if 0.38 < s[i] < 0.62:
            amp, freq = 0.006, 5.0
        else:
            amp, freq = 0.004 + 0.012 * max(0.0, s[i] - 0.62), 2.5
        fold = amp * np.sin(k * freq * 2 * np.pi + s[i] * 3.0)
        P = P + nn * fold[:, None]
        V[i] = P
        UV[i, :, 0] = lengths[i]
        UV[i, :, 1] = k
    UV[:, :, 0] /= lengths[-1]
    # ragged loose end at the bottom of the back
    tear = 0.03 * np.abs(rng.standard_normal(n_wid))
    V[-1, :, 2] -= tear
    idx = np.arange(n_len * n_wid).reshape(n_len, n_wid)
    a = idx[:-1, :-1].ravel()
    b = idx[:-1, 1:].ravel()
    c = idx[1:, 1:].ravel()
    d = idx[1:, :-1].ravel()
    T = np.concatenate([np.stack([a, b, c], 1), np.stack([a, c, d], 1)])
    return V.reshape(-1, 3), T, UV.reshape(-1, 2)
