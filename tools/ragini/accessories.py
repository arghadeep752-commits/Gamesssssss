"""Ragini's jewellery and her wooden scale (numpy meshes with UVs).

* bangles     glass and brass bangles on both wrists (a few cracked ones)
* nath        a thin gold nose ring
* mangalsutra black glass beads on a chain with a gold pendant
* payal       silver anklets with little ghungroo bells (you hear them before you see her)
* scale       a two-foot wooden school scale, gripped in her right fist
"""
import math

import numpy as np

V3 = lambda *a: np.array(a, float)      # noqa: E731


def _n(v):
    v = np.asarray(v, float)
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _basis(axis):
    z = _n(axis)
    x = _n(np.cross([0, 0, 1], z)) if abs(z[2]) < 0.95 else _n(np.cross([0, 1, 0], z))
    y = np.cross(z, x)
    return x, y, z


def torus(center, axis, R, r, seg=36, sides=10, sx=1.0, sy=1.0, gap=0.0):
    """Ring around `axis`. gap > 0 leaves a break (a cracked bangle). Returns V, T, UV."""
    x, y, z = _basis(axis)
    V, UV = [], []
    a0, a1 = gap * 0.5, 2 * math.pi - gap * 0.5
    closed = gap <= 0
    n_u = seg if closed else seg + 1
    for i in range(n_u):
        a = a0 + (a1 - a0) * i / (seg if closed else seg)
        c = np.cos(a) * x * R * sx + np.sin(a) * y * R * sy
        radial = _n(np.cos(a) * x * sx + np.sin(a) * y * sy)
        for j in range(sides):
            b = 2 * math.pi * j / sides
            V.append(center + c + radial * math.cos(b) * r + z * math.sin(b) * r)
            UV.append((i / seg, j / sides))
    T = []
    for i in range(seg if closed else seg):
        i2 = (i + 1) % n_u
        for j in range(sides):
            j2 = (j + 1) % sides
            a, b_, c_, d = i * sides + j, i2 * sides + j, i2 * sides + j2, i * sides + j2
            T += [(a, b_, c_), (a, c_, d)]
    return np.array(V), np.array(T), np.array(UV)


def sphere(center, r, seg=8, rings=6):
    V, UV, T = [], [], []
    for i in range(rings + 1):
        th = math.pi * i / rings
        for j in range(seg + 1):
            ph = 2 * math.pi * j / seg
            V.append(center + r * V3(math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), math.cos(th)))
            UV.append((j / seg, i / rings))
    for i in range(rings):
        for j in range(seg):
            a = i * (seg + 1) + j
            b_ = a + seg + 1
            T += [(a, b_, b_ + 1), (a, b_ + 1, a + 1)]
    return np.array(V), np.array(T), np.array(UV)


class Group:
    """Collects meshes with a material slot and a bone per part."""

    def __init__(self):
        self.V, self.T, self.UV, self.M, self.B = [], [], [], [], []
        self.n = 0

    def add(self, mesh, material, bone):
        V, T, UV = mesh
        self.V.append(V)
        self.T.append(T + self.n)
        self.UV.append(UV)
        self.M.append(np.full(len(T), material))
        self.B += [bone] * len(V)
        self.n += len(V)

    def arrays(self):
        return (np.concatenate(self.V), np.concatenate(self.T), np.concatenate(self.UV), np.concatenate(self.M),
                np.array(self.B))


MATERIALS = ["gold", "glass_red", "glass_green", "bead_black", "silver"]


def jewellery(body, seed=8):
    rng = np.random.default_rng(seed)
    g = Group()
    # bangles: a stack on each wrist, slightly loose, tilted
    for side in ("L", "R"):
        wr = body.marks["wrist." + side]
        el = body.marks["elbow." + side]
        ax = _n(wr - el)
        for k in range(7 if side == "L" else 5):
            c = wr - ax * (0.018 + k * 0.0085) + rng.normal(0, 0.0015, 3)
            tilt = _n(ax + rng.normal(0, 0.12, 3))
            mat = ["glass_red", "glass_red", "gold", "glass_green", "glass_red", "gold", "glass_red"][k % 7]
            gap = 0.5 if rng.random() < 0.18 else 0.0
            g.add(torus(c, tilt, 0.0315 + 0.0012 * k, 0.0021 if mat != "gold" else 0.0026, seg=34, sides=7, gap=gap),
                  MATERIALS.index(mat), "forearm." + side)
    # nath: a gold hoop through the left nostril
    g.add(torus(V3(0.0115, -0.094, 1.552), V3(1, 0.25, 0.1), 0.0105, 0.0009, seg=28, sides=6),
          MATERIALS.index("gold"), "head")
    # mangalsutra: black beads on a curve around the neck down to the chest, gold pendant
    beads = []
    for i in range(42):
        t = i / 41.0
        a = math.pi * (0.15 + 0.7 * t)              # from her left shoulder round the front to the right
        x = 0.075 * math.cos(a)
        drop = math.sin(a) ** 2
        p = V3(x, -0.055 - 0.035 * math.sin(a), 1.395 - 0.085 * drop)
        beads.append(p)
    for p in beads:
        g.add(sphere(p, 0.0032, 6, 4), MATERIALS.index("bead_black"), "chest")
    g.add(sphere(V3(0, -0.098, 1.300), 0.009, 10, 6), MATERIALS.index("gold"), "chest")
    # payal: silver anklets with ghungroo bells
    for side in ("L", "R"):
        an = body.marks["ankle." + side]
        c = an + V3(0, 0.0, -0.032)
        g.add(torus(c, V3(0, 0, 1), 0.041, 0.0024, seg=40, sides=6, sx=1.0, sy=1.12), MATERIALS.index("silver"), "shin." + side)
        for k in range(12):
            a = 2 * math.pi * k / 12
            p = c + V3(math.cos(a) * 0.043, math.sin(a) * 0.047, -0.008)
            g.add(sphere(p, 0.0042, 7, 5), MATERIALS.index("silver"), "shin." + side)
    return g.arrays()


def scale(body, length=0.61, width=0.034, thick=0.0055):
    """A wooden two-foot scale, its handle end in her right fist (UV: u along the scale 0..1, v across)."""
    c = body.marks["grip_c"]
    ax = _n(body.marks["grip_axis"])
    up = _n(body.marks["grip_up"] - ax * float(body.marks["grip_up"] @ ax))
    side = np.cross(ax, up)
    start = c - ax * 0.07                     # a short handle below the little finger, the rest out past the thumb
    # box with bevelled edges: build a 2D bevelled rectangle profile and extrude along the axis
    b = 0.0012
    hw, ht = width / 2, thick / 2
    prof = [(-hw + b, -ht), (hw - b, -ht), (hw, -ht + b), (hw, ht - b), (hw - b, ht), (-hw + b, ht), (-hw, ht - b), (-hw, -ht + b)]
    n_len = 24
    # v of each profile corner: the printed face (4 -> 5) gets v 0.45..0.95, the rest shares the remainder
    pv = [0.0, 0.30, 0.33, 0.40, 0.45, 0.95, 0.97, 0.99, 1.0]
    prof_c = prof + [prof[0]]                 # repeat the first corner so the UV seam is clean
    m = len(prof_c)
    V, UV, T = [], [], []
    for i in range(n_len + 1):
        t = i / n_len
        p0 = start + ax * (length * t)
        for j, (w, h) in enumerate(prof_c):
            V.append(p0 + up * h + side * w)
            UV.append((t, pv[j]))
    for i in range(n_len):
        for j in range(m - 1):
            a, b_, c_, d = i * m + j, (i + 1) * m + j, (i + 1) * m + j + 1, i * m + j + 1
            T += [(a, b_, c_), (a, c_, d)]
    # end caps
    for end, t in ((0, 0.0), (1, 1.0)):
        p0 = start + ax * (length * t)
        ci = len(V)
        V.append(p0)
        UV.append((t, 0.2))
        ring = [end * n_len * m + j for j in range(m - 1)]
        for j in range(m - 1):
            j2 = (j + 1) % (m - 1)
            T.append((ci, ring[j2], ring[j]) if end == 0 else (ci, ring[j], ring[j2]))
    return np.array(V), np.array(T), np.array(UV), {"start": start, "axis": ax, "up": up, "length": length}
