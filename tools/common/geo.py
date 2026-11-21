"""Small mesh-building kit for the school (numpy only, so shapes can be checked without Blender).

A Geo collects vertices, faces (quads/triangles/ngons as index lists), per-corner UVs and a material name per
face. UVs are in metres divided by the texture's real-world size, so photographed surfaces tile at true scale.
Boxes share their corner vertices (Blender's bevel modifier can round their edges).
"""
import math

import numpy as np

# real-world size (metres) one texture repeat covers, per material
TEX_M = {
    "plaster": 2.0, "plaster_ext": 2.5, "ceiling": 2.5, "floor_cement": 2.0, "floor_terrazzo": 1.5, "floor_tiles": 1.0,
    "floor_kota": 1.6, "floor_veranda": 1.2, "dado_green": 1.6, "dado_blue": 1.6, "dado_red": 1.6, "dado_brown": 1.6,
    "dado_tiles": 0.9, "wood": 0.9, "wood_dark": 0.9, "wood_painted_blue": 1.2, "wood_painted_green": 1.2,
    "wood_old": 1.0, "metal_green": 1.0, "metal_grey": 1.0, "rust": 0.8, "chalkboard": 2.0, "brick": 1.6,
    "ground_dirt": 3.0, "ground_court": 3.0, "plinth": 1.5, "roof": 3.0, "concrete": 2.0, "fabric_mat": 0.8,
    "sack": 0.7, "steel": 0.6, "aluminium": 0.5, "brass": 0.4, "ceramic": 0.6, "glass": 1.0, "bark": 1.2,
    "paper": 0.3, "cardboard": 0.5, "default": 1.0,
}


def tex_m(mat):
    return TEX_M.get(mat, TEX_M.get(mat.split(".")[0], 1.0))


def rot_z(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def rot_x(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def rot_y(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def _box_uv(p, n, m):
    """World-space box projection for a corner at p on a face with normal n."""
    an = np.abs(n)
    if an[2] >= an[0] and an[2] >= an[1]:
        return (p[0] / m, p[1] / m)
    if an[0] >= an[1]:
        return (p[1] / m, p[2] / m)
    return (p[0] / m, p[2] / m)


class Geo:
    def __init__(self, name="geo"):
        self.name = name
        self.V = []
        self.F = []          # list of index lists
        self.UV = []         # per face: list of (u, v)
        self.M = []          # per face material name
        self.parts = {}      # optional tags

    # --------------------------------------------------------------------------- low level
    def vert(self, p):
        self.V.append(np.asarray(p, float))
        return len(self.V) - 1

    def face(self, idx, mat, uvs=None, local_uv=None):
        P = [self.V[i] for i in idx]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(P) > 3:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-12 else np.array([0, 0, 1.0])
        if uvs is None:
            m = tex_m(mat)
            uvs = [_box_uv(p if local_uv is None else local_uv(p), n, m) for p in P]
        self.F.append(list(idx))
        self.UV.append(list(uvs))
        self.M.append(mat)
        return len(self.F) - 1

    def merge(self, other, T=None, R=None):
        off = len(self.V)
        for p in other.V:
            q = np.asarray(p, float)
            if R is not None:
                q = R @ q
            if T is not None:
                q = q + np.asarray(T, float)
            self.V.append(q)
        for f, uv, m in zip(other.F, other.UV, other.M):
            self.F.append([i + off for i in f])
            self.UV.append(list(uv))
            self.M.append(m)

    # --------------------------------------------------------------------------- primitives
    def box(self, c, size, mat, R=None, mats=None, uv_world=True):
        """Axis box (optionally rotated by R about its centre). mats: optional per-face materials
        in the order -x, +x, -y, +y, -z, +z. Returns the vertex indices."""
        c = np.asarray(c, float)
        h = np.asarray(size, float) / 2
        R = np.eye(3) if R is None else R
        corners = []
        for sz in (-1, 1):
            for sy in (-1, 1):
                for sx in (-1, 1):
                    corners.append(c + R @ (h * np.array([sx, sy, sz])))
        i = [self.vert(p) for p in corners]
        # corner index = (sx>0) + 2*(sy>0) + 4*(sz>0)
        faces = [
            [i[0], i[4], i[6], i[2]],   # -x
            [i[1], i[3], i[7], i[5]],   # +x
            [i[0], i[1], i[5], i[4]],   # -y
            [i[2], i[6], i[7], i[3]],   # +y
            [i[0], i[2], i[3], i[1]],   # -z
            [i[4], i[5], i[7], i[6]],   # +z
        ]
        for k, f in enumerate(faces):
            self.face(f, mats[k] if mats else mat)
        return i

    def quad(self, a, b, c, d, mat, uvs=None):
        idx = [self.vert(a), self.vert(b), self.vert(c), self.vert(d)]
        return self.face(idx, mat, uvs)

    def cyl(self, p0, p1, r0, mat, seg=16, r1=None, caps=True, uv_m=None):
        """Cylinder / truncated cone between two points."""
        p0 = np.asarray(p0, float)
        p1 = np.asarray(p1, float)
        r1 = r0 if r1 is None else r1
        ax = p1 - p0
        L = np.linalg.norm(ax)
        z = ax / max(L, 1e-12)
        x = np.cross([0, 0, 1], z)
        if np.linalg.norm(x) < 1e-6:
            x = np.array([1.0, 0, 0])
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        m = uv_m or tex_m(mat)
        ring0, ring1 = [], []
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            d = math.cos(a) * x + math.sin(a) * y
            ring0.append(self.vert(p0 + d * r0))
            ring1.append(self.vert(p1 + d * r1))
        circ = 2 * math.pi * max(r0, r1)
        for k in range(seg):
            u0, u1 = k / seg * circ / m, (k + 1) / seg * circ / m
            self.face([ring0[k], ring0[k + 1], ring1[k + 1], ring1[k]], mat, [(u0, 0), (u1, 0), (u1, L / m), (u0, L / m)])
        if caps:
            for ring, p, r, flip in ((ring0, p0, r0, True), (ring1, p1, r1, False)):
                if r <= 1e-6:
                    continue
                idx = ring[:-1]
                uvs = [((self.V[i] - p) @ x / m, (self.V[i] - p) @ y / m) for i in idx]
                if flip:
                    idx = idx[::-1]
                    uvs = uvs[::-1]
                self.face(idx, mat, uvs)
        return ring0, ring1

    def lathe(self, profile, c, mat, seg=24, axis=None, uv_m=None):
        """Surface of revolution: profile [(radius, height), ...] bottom to top around +Z (or `axis` rotation)."""
        c = np.asarray(c, float)
        R = np.eye(3) if axis is None else axis
        m = uv_m or tex_m(mat)
        rings = []
        for (r, h) in profile:
            ring = []
            for k in range(seg + 1):
                a = 2 * math.pi * k / seg
                ring.append(self.vert(c + R @ np.array([math.cos(a) * r, math.sin(a) * r, h])))
            rings.append(ring)
        # arc length along the profile for v
        acc = [0.0]
        for i in range(1, len(profile)):
            dr = profile[i][0] - profile[i - 1][0]
            dh = profile[i][1] - profile[i - 1][1]
            acc.append(acc[-1] + math.hypot(dr, dh))
        circ = 2 * math.pi * max(p[0] for p in profile)
        for i in range(len(rings) - 1):
            for k in range(seg):
                u0, u1 = k / seg * circ / m, (k + 1) / seg * circ / m
                self.face([rings[i][k], rings[i][k + 1], rings[i + 1][k + 1], rings[i + 1][k]], mat,
                          [(u0, acc[i] / m), (u1, acc[i] / m), (u1, acc[i + 1] / m), (u0, acc[i + 1] / m)])
        return rings

    def prism(self, poly, z0, z1, mat, R=None, T=None, side_mat=None, cap=True):
        """Extrude a 2D polygon (x, y list, counter-clockwise) from z0 to z1, then rotate/translate."""
        R = np.eye(3) if R is None else R
        T = np.zeros(3) if T is None else np.asarray(T, float)
        n = len(poly)
        lo = [self.vert(T + R @ np.array([x, y, z0])) for x, y in poly]
        hi = [self.vert(T + R @ np.array([x, y, z1])) for x, y in poly]
        sm = side_mat or mat
        for k in range(n):
            k2 = (k + 1) % n
            self.face([lo[k], lo[k2], hi[k2], hi[k]], sm)
        if cap:
            self.face(lo[::-1], mat)
            self.face(hi, mat)
        return lo, hi

    def transform(self, R=None, T=None, start=0):
        for i in range(start, len(self.V)):
            q = self.V[i]
            if R is not None:
                q = R @ q
            if T is not None:
                q = q + np.asarray(T, float)
            self.V[i] = q

    # --------------------------------------------------------------------------- export
    def arrays(self):
        """Triangulated arrays for previews: V (n,3), T (m,3), material per triangle."""
        V = np.array(self.V) if self.V else np.zeros((0, 3))
        T, M = [], []
        for f, m in zip(self.F, self.M):
            for k in range(1, len(f) - 1):
                T.append((f[0], f[k], f[k + 1]))
                M.append(m)
        return V, np.array(T, dtype=np.int64).reshape(-1, 3), M

    def __len__(self):
        return len(self.F)
