"""Procedural modelling toolkit for the DANGA map (pure numpy, Unity space: X east, Y up, Z north, left-handed).

A triangle (a, b, c) faces the side its normal cross(b - a, c - a) points to (Unity's convention).
Every vertex carries:
  pos (3), nrm (3), uv (2, texture repeats), slice (texture-array layer), ao (0..1), col (rgb tint, 1 = none), emis (0..1)
Terrain vertices also carry a second layer + blend weight (slice2, blend).
"""
import math

import numpy as np

# texture-array layers (tools/city/textures.py builds them in this order)
LAYERS = ["asphalt", "asphalt_old", "paving", "curb", "concrete", "plaster", "plaster_old", "brick", "roof_tin", "roof_tiles",
          "grass", "ground", "sand", "rock", "wood", "metal", "marble", "tiles", "bark", "fabric", "facade1", "facade2",
          "window", "shopfront", "signs", "signs2", "markings", "paddy", "leaves", "palmleaf", "bananaleaf", "fern", "white", "glass"]
L = {n: i for i, n in enumerate(LAYERS)}


def v3(*a):
    return np.array(a, dtype=np.float64)


def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class Mesh:
    """Growable vertex/index buffers for one material group."""

    def __init__(self, terrain=False):
        self.P, self.N, self.UV, self.S, self.AO, self.C, self.E = [], [], [], [], [], [], []
        self.S2, self.B = [], []
        self.I = []
        self.n = 0
        self.terrain = terrain

    # ------------------------------------------------------------------ raw
    def add(self, P, N, UV, slc, ao=1.0, col=(1, 1, 1), emis=0.0, I=None, S2=None, B=None):
        P = np.asarray(P, np.float64).reshape(-1, 3)
        k = len(P)
        N = np.asarray(N, np.float64).reshape(-1, 3)
        if len(N) == 1:
            N = np.repeat(N, k, 0)
        UV = np.asarray(UV, np.float64).reshape(-1, 2)
        self.P.append(P)
        self.N.append(N)
        self.UV.append(UV)
        self.S.append(np.broadcast_to(np.asarray(slc, np.float64), (k,)).copy())
        self.AO.append(np.broadcast_to(np.asarray(ao, np.float64), (k,)).copy())
        col = np.asarray(col, np.float64)
        self.C.append(np.broadcast_to(col, (k, 3)).copy() if col.ndim == 1 else col.reshape(k, 3))
        self.E.append(np.broadcast_to(np.asarray(emis, np.float64), (k,)).copy())
        if self.terrain:
            self.S2.append(np.broadcast_to(np.asarray(S2 if S2 is not None else slc, np.float64), (k,)).copy())
            self.B.append(np.broadcast_to(np.asarray(B if B is not None else 0.0, np.float64), (k,)).copy())
        if I is not None:
            self.I.append(np.asarray(I, np.int64).reshape(-1) + self.n)
        self.n += k
        return self.n - k

    def arrays(self):
        if not self.P:
            return None
        out = dict(P=np.vstack(self.P), N=np.vstack(self.N), UV=np.vstack(self.UV), S=np.concatenate(self.S),
                   AO=np.concatenate(self.AO), C=np.vstack(self.C), E=np.concatenate(self.E),
                   I=np.concatenate(self.I) if self.I else np.zeros(0, np.int64))
        if self.terrain:
            out["S2"] = np.concatenate(self.S2)
            out["B"] = np.concatenate(self.B)
        return out

    def tri_count(self):
        return sum(len(i) for i in self.I) // 3

    # ------------------------------------------------------------------ primitives
    def quad(self, a, b, c, d, slc, uvs=None, ao=(1, 1, 1, 1), col=(1, 1, 1), emis=0.0, tile=None, flip=False):
        """Planar quad a-b-c-d (front side = cross(b - a, c - a)). uvs: 4 uv pairs, or tile=(su, sv) metres per repeat."""
        a, b, c, d = (np.asarray(x, np.float64) for x in (a, b, c, d))
        n = norm(np.cross(b - a, c - a))
        if flip:
            n = -n
        if uvs is None:
            su, sv = tile if tile else (2.5, 2.5)
            w = np.linalg.norm(b - a)
            h = np.linalg.norm(d - a)
            uvs = [(0, 0), (w / su, 0), (w / su, h / sv), (0, h / sv)]
        I = [0, 1, 2, 0, 2, 3] if not flip else [0, 2, 1, 0, 3, 2]
        return self.add([a, b, c, d], [n], uvs, slc, np.asarray(ao, np.float64), col, emis, I)

    def panel(self, bl, br, tr, tl, slc, uvs=None, ao=(1, 1, 1, 1), col=(1, 1, 1), emis=0.0, tile=(2.5, 2.5)):
        """Quad given as the viewer sees it from its front: bottom-left, bottom-right, top-right, top-left."""
        bl, br, tr, tl = (np.asarray(x, np.float64) for x in (bl, br, tr, tl))
        if uvs is None:
            w = float(np.linalg.norm(br - bl))
            h = float(np.linalg.norm(tl - bl))
            uvs = [(0, 0), (w / tile[0], 0), (w / tile[0], h / tile[1]), (0, h / tile[1])]
        # Unity's front face is clockwise as the viewer sees it: bl -> tl -> tr -> br
        return self.quad(bl, tl, tr, br, slc, uvs=[uvs[0], uvs[3], uvs[2], uvs[1]], ao=(ao[0], ao[3], ao[2], ao[1]), col=col, emis=emis)

    def tri(self, a, b, c, slc, uvs=((0, 0), (1, 0), (0.5, 1)), col=(1, 1, 1), ao=1.0, outward=None):
        """Triangle; if `outward` (a direction) is given the triangle is turned to face it."""
        a, b, c = (np.asarray(x, np.float64) for x in (a, b, c))
        n = np.cross(b - a, c - a)
        if outward is not None and float(np.dot(n, outward)) < 0:
            b, c = c, b
            uvs = (uvs[0], uvs[2], uvs[1])
            n = -n
        n = norm(n)
        return self.add([a, b, c], [n], list(uvs), slc, ao, col, 0.0, [0, 1, 2])

    def wall(self, p0, p1, y0, y1, slc, tile=(2.5, 2.5), col=(1, 1, 1), ao_bottom=0.75, ao_top=1.0, u0=0.0, v0=None, emis=0.0):
        """Vertical wall from p0 to p1 (xz) facing to the right of p0->p1 (the outside when walking around a footprint
        counter-clockwise seen from above)."""
        p0 = np.asarray(p0, np.float64)
        p1 = np.asarray(p1, np.float64)
        a, b = v3(p0[0], y0, p0[1]), v3(p1[0], y0, p1[1])
        c, d = v3(p1[0], y1, p1[1]), v3(p0[0], y1, p0[1])
        w = float(np.linalg.norm(p1 - p0))
        su, sv = tile
        vv0 = (y0 / sv) if v0 is None else v0
        uvs = [(u0, vv0), (u0 + w / su, vv0), (u0 + w / su, vv0 + (y1 - y0) / sv), (u0, vv0 + (y1 - y0) / sv)]
        # outward normal = right of p0->p1 when seen from above: (dz, -dx)
        return self.quad(a, d, c, b, slc, uvs=[uvs[0], uvs[3], uvs[2], uvs[1]], ao=(ao_bottom, ao_top, ao_top, ao_bottom), col=col, emis=emis)

    def box(self, cx, cy, cz, sx, sy, sz, slc, yaw=0.0, tile=(2.5, 2.5), col=(1, 1, 1), top=None, bottom=False, ao_bottom=0.8,
            faces="nsewt", emis=0.0, top_col=None):
        """Box centred at (cx, cz) with its base at cy, size sx (along local x) x sy (height) x sz, rotated by yaw
        (degrees, clockwise seen from above). top: texture layer for the top face (default slc)."""
        hx, hz = sx / 2.0, sz / 2.0
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

        def P(x, z):
            return (cx + x * c + z * s, cz - x * s + z * c)
        # corners counter-clockwise seen from above: (-x,-z) -> (+x,-z) -> (+x,+z) -> (-x,+z)
        q = [P(-hx, -hz), P(hx, -hz), P(hx, hz), P(-hx, hz)]
        y0, y1 = cy, cy + sy
        names = ["s", "e", "n", "w"]
        for i in range(4):
            if names[i] in faces:
                self.wall(q[i], q[(i + 1) % 4], y0, y1, slc, tile, col, ao_bottom, 1.0, emis=emis)
        if "t" in faces:
            a, b, cc, d = (v3(p[0], y1, p[1]) for p in q)
            tl = top if top is not None else slc
            # counter-clockwise corners seen from above: (a, d, c) faces up
            self.quad(a, d, cc, b, tl, tile=tile, col=top_col if top_col is not None else col)
        if bottom:
            a, b, cc, d = (v3(p[0], y0, p[1]) for p in q)
            self.quad(a, b, cc, d, slc, tile=tile, col=col)

    def prism(self, poly, y0, y1, slc, tile=(2.5, 2.5), col=(1, 1, 1), top=None, top_col=None, walls=True, cap=True, ao_bottom=0.8):
        """Extrude a simple polygon (xz) from y0 to y1 (walls face outwards whatever the polygon's orientation)."""
        poly = [np.asarray(p, np.float64) for p in ccw(poly)]
        n = len(poly)
        if walls:
            u = 0.0
            for i in range(n):
                p0, p1 = poly[i], poly[(i + 1) % n]
                self.wall(p0, p1, y0, y1, slc, tile, col, ao_bottom, 1.0, u0=u)
                u += float(np.linalg.norm(p1 - p0)) / tile[0]
        if cap:
            self.polygon(poly, y1, top if top is not None else slc, tile, top_col if top_col is not None else col)

    def polygon(self, poly, y, slc, tile=(2.5, 2.5), col=(1, 1, 1), up=True, ao=1.0, emis=0.0):
        """Flat polygon at height y (ear clipping), facing up (or down)."""
        poly = [np.asarray(p, np.float64) for p in poly]
        tris = triangulate(poly)
        P = np.array([[p[0], y, p[1]] for p in poly])
        UV = np.array([[p[0] / tile[0], p[1] / tile[1]] for p in poly])
        I = []
        for a, b, c in tris:
            # triangulate() returns clockwise-from-above triangles = facing up
            I += [a, b, c] if up else [a, c, b]
        return self.add(P, [(0, 1 if up else -1, 0)], UV, slc, ao, col, emis, I)

    def cylinder(self, cx, cy, cz, r, h, slc, seg=12, tile=(2.0, 2.0), col=(1, 1, 1), top=True, r_top=None, top_slc=None, ao_bottom=0.85,
                 emis=0.0, a0=0.0, a1=360.0):
        rt = r if r_top is None else r_top
        P, N, UV, I = [], [], [], []
        circ = 2 * math.pi * r
        full = abs(a1 - a0) >= 359.9
        nseg = seg
        for i in range(nseg + 1):
            a = math.radians(a0 + (a1 - a0) * i / nseg)
            ca, sa = math.cos(a), math.sin(a)
            slope = (r - rt) / max(h, 1e-6)
            nn = norm(v3(ca, slope, sa))
            P += [(cx + r * ca, cy, cz + r * sa), (cx + rt * ca, cy + h, cz + rt * sa)]
            N += [nn, nn]
            u = circ * i / nseg / tile[0]
            UV += [(u, cy / tile[1]), (u, (cy + h) / tile[1])]
        for i in range(nseg):
            k = 2 * i
            # outward faces: the angle grows counter-clockwise seen from above (x -> z) -> wind accordingly
            I += [k, k + 1, k + 3, k, k + 3, k + 2]
        base = self.add(P, N, UV, slc, np.tile([ao_bottom, 1.0], nseg + 1), col, emis, I)
        if top and rt > 0.01 and full:
            ring = [(cx + rt * math.cos(math.radians(a0 + 360.0 * i / seg)), cz + rt * math.sin(math.radians(a0 + 360.0 * i / seg))) for i in range(seg)]
            self.polygon(ring[::-1], cy + h, top_slc if top_slc is not None else slc, tile, col)
        return base

    def lathe(self, cx, cy, cz, profile, slc, seg=16, tile=(2.0, 2.0), col=(1, 1, 1), emis=0.0):
        """Surface of revolution: profile = [(radius, height), ...] from bottom to top."""
        P, N, UV, I = [], [], [], []
        m = len(profile)
        vlen = [0.0]
        for j in range(1, m):
            vlen.append(vlen[-1] + math.hypot(profile[j][0] - profile[j - 1][0], profile[j][1] - profile[j - 1][1]))
        for i in range(seg + 1):
            a = 2 * math.pi * i / seg
            ca, sa = math.cos(a), math.sin(a)
            for j, (r, y) in enumerate(profile):
                P.append((cx + r * ca, cy + y, cz + r * sa))
                # normal from the profile tangent
                j0, j1 = max(0, j - 1), min(m - 1, j + 1)
                dr = profile[j1][0] - profile[j0][0]
                dy = profile[j1][1] - profile[j0][1]
                nn = norm(v3(dy * ca, -dr, dy * sa))
                if r < 1e-4:
                    nn = v3(0, 1 if j == m - 1 else -1, 0)
                N.append(nn)
                UV.append((2 * math.pi * max(r, 0.3) * i / seg / tile[0], vlen[j] / tile[1]))
        for i in range(seg):
            for j in range(m - 1):
                a = i * m + j
                b = (i + 1) * m + j
                I += [a, a + 1, b + 1, a, b + 1, b]
        return self.add(P, N, UV, slc, 1.0, col, emis, I)

    def strip(self, pts, widths, y, slc, tile=(4.0, 4.0), col=(1, 1, 1), offset=0.0, ao=1.0, u_along=True, heights=None):
        """Flat ribbon along a polyline (xz). widths: scalar or per point. offset shifts the ribbon sideways (to the
        left of the travel direction for positive values)."""
        pts = [np.asarray(p, np.float64) for p in pts]
        n = len(pts)
        if n < 2:
            return
        W = np.broadcast_to(np.asarray(widths, np.float64), (n,))
        P, UV, I = [], [], []
        dist = 0.0
        for i in range(n):
            if i == 0:
                d = pts[1] - pts[0]
            elif i == n - 1:
                d = pts[-1] - pts[-2]
            else:
                d = norm(pts[i + 1] - pts[i]) + norm(pts[i] - pts[i - 1])
            d = norm(d)
            left = np.array([-d[1], d[0]])
            if i > 0:
                dist += float(np.linalg.norm(pts[i] - pts[i - 1]))
            c = pts[i] + left * offset
            yy = y if heights is None else heights[i]
            pl = c + left * W[i] / 2
            pr = c - left * W[i] / 2
            P += [(pl[0], yy, pl[1]), (pr[0], yy, pr[1])]
            if u_along:
                UV += [(0.0, dist / tile[1]), (W[i] / tile[0], dist / tile[1])]
            else:
                UV += [(pl[0] / tile[0], pl[1] / tile[1]), (pr[0] / tile[0], pr[1] / tile[1])]
        for i in range(n - 1):
            k = 2 * i
            # left-right pairs travelling forward: (L0, L1, R1) faces up in Unity space
            I += [k, k + 2, k + 3, k, k + 3, k + 1]
        self.add(P, [(0, 1, 0)], UV, slc, ao, col, 0.0, I)

    def sphere(self, cx, cy, cz, r, slc, seg=10, rings=6, col=(1, 1, 1), squash=1.0):
        prof = [(r * math.sin(math.pi * j / rings), cy * 0 + r * squash * (1 - math.cos(math.pi * j / rings)) - r * squash) for j in range(rings + 1)]
        prof = [(max(p[0], 0.0), p[1]) for p in prof]
        return self.lathe(cx, cy + r * squash, cz, prof, slc, seg, col=col)


def triangulate(poly):
    """Ear clipping for a simple polygon given clockwise seen from above (xz). Returns index triples, each also
    clockwise seen from above (= facing up in Unity)."""
    n = len(poly)
    if n < 3:
        return []
    pts = [np.asarray(p, np.float64) for p in poly]
    # signed area: positive for counter-clockwise in (x, z) maths orientation; we want clockwise seen from above.
    # Seen from above in Unity, +X right and +Z up on screen -> standard maths orientation; clockwise = negative area.
    area = 0.0
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        area += a[0] * b[1] - b[0] * a[1]
    idx = list(range(n))
    if area > 0:
        idx.reverse()       # make it clockwise

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    out = []
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        found = False
        m = len(idx)
        for k in range(m):
            i0, i1, i2 = idx[(k - 1) % m], idx[k], idx[(k + 1) % m]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) >= -1e-12:      # not convex for a clockwise polygon
                continue
            ok = True
            for j in idx:
                if j in (i0, i1, i2):
                    continue
                p = pts[j]
                if cross(a, b, p) < 0 and cross(b, c, p) < 0 and cross(c, a, p) < 0:
                    ok = False
                    break
            if ok:
                out.append((i0, i1, i2))
                idx.pop(k)
                found = True
                break
        if not found:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    # clockwise in maths orientation (negative area) -> in Unity seen from above: (a, b, c) with cross(b-a, c-a).y > 0
    res = []
    for a, b, c in out:
        A, B, C = pts[a], pts[b], pts[c]
        ny = (B[1] - A[1]) * (C[0] - A[0]) - (B[0] - A[0]) * (C[1] - A[1])   # y of cross((bx,0,bz),(cx,0,cz)) = bz*cx - bx*cz
        res.append((a, b, c) if ny > 0 else (a, c, b))
    return res


def rot(p, yaw, origin=(0.0, 0.0)):
    """Rotate xz point p by yaw degrees clockwise seen from above around origin."""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    x, z = p[0] - origin[0], p[1] - origin[1]
    return (origin[0] + x * c + z * s, origin[1] - x * s + z * c)


def rect(cx, cz, sx, sz, yaw=0.0):
    """Counter-clockwise (seen from above) rectangle corners."""
    hx, hz = sx / 2, sz / 2
    return [rot((cx - hx, cz - hz), yaw, (cx, cz)), rot((cx + hx, cz - hz), yaw, (cx, cz)),
            rot((cx + hx, cz + hz), yaw, (cx, cz)), rot((cx - hx, cz + hz), yaw, (cx, cz))]


def area(poly):
    """Signed area in the (x, z) plane: positive = counter-clockwise seen from above."""
    a = 0.0
    n = len(poly)
    for i in range(n):
        x0, z0 = poly[i][0], poly[i][1]
        x1, z1 = poly[(i + 1) % n][0], poly[(i + 1) % n][1]
        a += x0 * z1 - x1 * z0
    return a / 2.0


def ccw(poly):
    return list(poly) if area(poly) >= 0 else list(poly)[::-1]
