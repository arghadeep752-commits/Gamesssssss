"""Quick software renders of meshes (numpy + PIL) for checking shapes on a machine without Blender.
Not used by the game build."""
import numpy as np
from PIL import Image


def _bary(n):
    pts = []
    for i in range(n + 1):
        for j in range(n + 1 - i):
            pts.append((i / n, j / n, 1 - i / n - j / n))
    return np.array(pts)


def render(V, T, view="front", size=(700, 1000), zoom=None, center=None, colors=None, bg=(38, 40, 46), samples=None,
           yaw_deg=0.0, pitch_deg=0.0):
    """Orthographic shaded render. view: front (from -Y), back, left (from +X), right (from -X), or yaw/pitch."""
    V = np.asarray(V, float)
    T = np.asarray(T, int)
    yaw = {"front": 0.0, "back": 180.0, "left": -90.0, "right": 90.0, "q": -35.0}.get(view, 0.0) + yaw_deg
    a = np.radians(yaw)
    p = np.radians(pitch_deg)
    # camera basis: screen x, screen y (up), depth (into the screen)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(p), -np.sin(p)], [0, np.sin(p), np.cos(p)]])
    M = Rx @ Rz                                     # camera space: x right, y depth (+ away), z up
    W, H = size
    P = V @ M.T
    if center is None:
        center = (P.min(axis=0) + P.max(axis=0)) / 2
    else:
        center = np.asarray(center, float) @ M.T
    if zoom is None:
        ext = P.max(axis=0) - P.min(axis=0)
        zoom = 0.92 * min(W / max(ext[0], 1e-6), H / max(ext[2], 1e-6))
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, T[:, k], fn)
    vn /= np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)
    # how many samples per triangle: enough to cover each triangle on screen (bucketed by size, rendered bucket by bucket)
    e = np.maximum(np.linalg.norm(P[T[:, 1]] - P[T[:, 0]], axis=1), np.linalg.norm(P[T[:, 2]] - P[T[:, 0]], axis=1)) * zoom
    C = np.asarray(colors, float) if colors is not None else np.tile(np.array([[0.78, 0.74, 0.70]]), (len(V), 1))
    zbuf = np.full((H, W), np.inf)
    img = np.zeros((H, W, 3))
    img[:] = np.array(bg) / 255.0
    L1 = np.array([0.45, -0.75, 0.5])
    L1 /= np.linalg.norm(L1)
    fill = np.array([-0.7, -0.3, 0.1])
    fill /= np.linalg.norm(fill)
    view_d = np.array([0.0, -1.0, 0.0])
    for lo_, hi_, n in ((0, 1.2, 1), (1.2, 2.5, 3), (2.5, 5, 6), (5, 10, 10), (10, 1e9, 16)):
        sel = np.nonzero((e >= lo_) & (e < hi_))[0]
        if len(sel) == 0:
            continue
        B = _bary(samples or n)
        for c0 in range(0, len(sel), 20000):
            Ts = T[sel[c0:c0 + 20000]]
            pts = np.einsum("sk,tkd->tsd", B, P[Ts]).reshape(-1, 3)
            nrm = np.einsum("sk,tkd->tsd", B, vn[Ts]).reshape(-1, 3) @ M.T
            col = np.einsum("sk,tkd->tsd", B, C[Ts]).reshape(-1, 3)
            nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
            sx = ((pts[:, 0] - center[0]) * zoom + W / 2).astype(int)
            sy = (H / 2 - (pts[:, 2] - center[2]) * zoom).astype(int)
            depth = pts[:, 1]
            ok = (sx >= 0) & (sx < W) & (sy >= 0) & (sy < H)
            sx, sy, depth, nrm, col = sx[ok], sy[ok], depth[ok], nrm[ok], col[ok]
            ok = depth < zbuf[sy, sx]
            sx, sy, depth, nrm, col = sx[ok], sy[ok], depth[ok], nrm[ok], col[ok]
            order = np.argsort(-depth)
            sx, sy, depth, nrm, col = sx[order], sy[order], depth[order], nrm[order], col[order]
            diff = np.clip(nrm @ L1, 0, 1)
            diff2 = np.clip(nrm @ fill, 0, 1) * 0.25
            rim = np.clip(1 - np.abs(nrm @ view_d), 0, 1) ** 3 * 0.25
            shade = 0.12 + 0.8 * diff + diff2 + rim
            img[sy, sx] = np.clip(col * shade[:, None], 0, 1)
            zbuf[sy, sx] = depth
    return Image.fromarray((img * 255).astype(np.uint8))


def sheet(images, cols=None):
    cols = cols or len(images)
    rows = (len(images) + cols - 1) // cols
    w = max(i.width for i in images)
    h = max(i.height for i in images)
    out = Image.new("RGB", (w * cols, h * rows), (20, 20, 20))
    for k, im in enumerate(images):
        out.paste(im, ((k % cols) * w, (k // cols) * h))
    return out
