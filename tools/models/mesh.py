"""
Granny Dimnight model kit: a tiny mesh builder for low-poly furniture and props, written for Unity's axes
(x right, y up, z forward, left-handed). Triangles are wound so cross(b - a, c - a) points out of the surface, which is
what Unity treats as the front face. Everything is built in metres; materials are given by key (see materials.py).
"""
import math

import numpy as np


def _norm(v):
    v = np.asarray(v, dtype=np.float64)
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


class Mesh:
    def __init__(self):
        self.parts = {}   # material key -> [positions, normals, uvs, triangles]

    def _part(self, mat):
        if mat not in self.parts:
            self.parts[mat] = [[], [], [], []]
        return self.parts[mat]

    # ---- low level -------------------------------------------------------------------------------------------
    def tri_fan(self, pts, normal, mat, uvs=None, smooth_normals=None):
        """A convex polygon (points in order around it, either winding); flat normal unless smooth_normals given."""
        pts = [np.asarray(p, dtype=np.float64) for p in pts]
        if len(pts) < 3:
            return
        n = _norm(normal)
        c = np.cross(pts[1] - pts[0], pts[2] - pts[0])
        if np.linalg.norm(c) < 1e-14:
            # find a non-degenerate corner
            for i in range(1, len(pts) - 1):
                c = np.cross(pts[i] - pts[0], pts[i + 1] - pts[0])
                if np.linalg.norm(c) > 1e-14:
                    break
        order = list(range(len(pts)))
        if np.dot(c, n) < 0:
            order = order[::-1]
        p, nr, uv, tr = self._part(mat)
        base = len(p)
        for k, i in enumerate(order):
            p.append(pts[i])
            nr.append(_norm(smooth_normals[i]) if smooth_normals is not None else n)
            uv.append(uvs[i] if uvs is not None else (0.0, 0.0))
        for k in range(1, len(order) - 1):
            tr.append((base, base + k, base + k + 1))

    def quad(self, a, b, c, d, normal, mat, tile=1.0, uvs=None):
        pts = [a, b, c, d]
        if uvs is None:
            uvs = planar_uv(pts, normal, tile)
        self.tri_fan(pts, normal, mat, uvs)

    def add(self, other, transform=None):
        """Appends another Mesh, optionally through a 4x4 transform (rotation/translation/uniform scale)."""
        for mat, (p, nr, uv, tr) in other.parts.items():
            q = self._part(mat)
            base = len(q[0])
            for v in p:
                v = np.asarray(v)
                if transform is not None:
                    v = (transform[:3, :3] @ v) + transform[:3, 3]
                q[0].append(v)
            for n in nr:
                n = np.asarray(n)
                if transform is not None:
                    n = _norm(transform[:3, :3] @ n)
                q[1].append(n)
            q[2].extend(uv)
            q[3].extend((a + base, b + base, c + base) for a, b, c in tr)

    # ---- primitives ------------------------------------------------------------------------------------------
    def box(self, mn, mx, mat, tile=1.0, skip=(), mats=None):
        """Axis-aligned box. skip: faces to leave out ('-x','+x','-y','+y','-z','+z'); mats: per-face material keys."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        faces = {
            "-x": ([(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)], (-1, 0, 0)),
            "+x": ([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], (1, 0, 0)),
            "-y": ([(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)], (0, -1, 0)),
            "+y": ([(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)], (0, 1, 0)),
            "-z": ([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], (0, 0, -1)),
            "+z": ([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], (0, 0, 1)),
        }
        for k, (pts, n) in faces.items():
            if k in skip:
                continue
            m = (mats or {}).get(k, mat)
            self.quad(*pts, n, m, tile)

    def rod(self, p0, p1, r, mat, sides=6):
        """Thin prism between two points in any direction (antennas, wires, struts)."""
        p0 = np.asarray(p0, float)
        p1 = np.asarray(p1, float)
        ax = p1 - p0
        L = np.linalg.norm(ax)
        if L < 1e-9:
            return
        ax = ax / L
        ref = np.array([0.0, 1.0, 0.0]) if abs(ax[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        u = np.cross(ax, ref)
        u /= np.linalg.norm(u)
        v = np.cross(ax, u)
        ring = [(math.cos(2 * math.pi * i / sides), math.sin(2 * math.pi * i / sides)) for i in range(sides)]
        for i in range(sides):
            c0, s0 = ring[i]
            c1, s1 = ring[(i + 1) % sides]
            n0 = u * c0 + v * s0
            n1 = u * c1 + v * s1
            a, b = p0 + r * n0, p0 + r * n1
            c, d = p1 + r * n1, p1 + r * n0
            self.quad(a, b, c, d, _norm(n0 + n1), mat)
        self.tri_fan([p1 + r * (u * c + v * s) for c, s in ring], ax, mat)
        self.tri_fan([p0 + r * (u * c + v * s) for c, s in ring[::-1]], -ax, mat)

    def bevel_box(self, mn, mx, mat, r=0.01, tile=1.0, skip_bottom=False):
        """Box with chamfered edges (a soft, finished look for furniture)."""
        mn = np.asarray(mn, float)
        mx = np.asarray(mx, float)
        r = float(min(r, *(0.45 * (mx - mn))))
        if r <= 1e-4:
            return self.box(mn, mx, mat, tile)
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        X = (x0, x0 + r, x1 - r, x1)
        Y = (y0, y0 + r, y1 - r, y1)
        Z = (z0, z0 + r, z1 - r, z1)
        # main faces (inset)
        self.quad((X[1], Y[3], Z[1]), (X[1], Y[3], Z[2]), (X[2], Y[3], Z[2]), (X[2], Y[3], Z[1]), (0, 1, 0), mat, tile)
        if not skip_bottom:
            self.quad((X[1], Y[0], Z[1]), (X[2], Y[0], Z[1]), (X[2], Y[0], Z[2]), (X[1], Y[0], Z[2]), (0, -1, 0), mat, tile)
        self.quad((X[0], Y[1], Z[1]), (X[0], Y[1], Z[2]), (X[0], Y[2], Z[2]), (X[0], Y[2], Z[1]), (-1, 0, 0), mat, tile)
        self.quad((X[3], Y[1], Z[1]), (X[3], Y[2], Z[1]), (X[3], Y[2], Z[2]), (X[3], Y[1], Z[2]), (1, 0, 0), mat, tile)
        self.quad((X[1], Y[1], Z[0]), (X[1], Y[2], Z[0]), (X[2], Y[2], Z[0]), (X[2], Y[1], Z[0]), (0, 0, -1), mat, tile)
        self.quad((X[1], Y[1], Z[3]), (X[2], Y[1], Z[3]), (X[2], Y[2], Z[3]), (X[1], Y[2], Z[3]), (0, 0, 1), mat, tile)
        s = 0.7071
        # edge chamfers (12)
        for (ya, yb, ny) in ((Y[2], Y[3], 1), (Y[1], Y[0], -1)):
            if ny < 0 and skip_bottom:
                continue
            self.quad((X[1], yb, Z[1]), (X[0], ya, Z[1]), (X[0], ya, Z[2]), (X[1], yb, Z[2]), (-s, ny * s, 0), mat, tile)
            self.quad((X[2], yb, Z[1]), (X[2], yb, Z[2]), (X[3], ya, Z[2]), (X[3], ya, Z[1]), (s, ny * s, 0), mat, tile)
            self.quad((X[1], yb, Z[1]), (X[2], yb, Z[1]), (X[2], ya, Z[0]), (X[1], ya, Z[0]), (0, ny * s, -s), mat, tile)
            self.quad((X[1], yb, Z[2]), (X[1], ya, Z[3]), (X[2], ya, Z[3]), (X[2], yb, Z[2]), (0, ny * s, s), mat, tile)
        self.quad((X[0], Y[1], Z[1]), (X[1], Y[1], Z[0]), (X[1], Y[2], Z[0]), (X[0], Y[2], Z[1]), (-s, 0, -s), mat, tile)
        self.quad((X[2], Y[1], Z[0]), (X[3], Y[1], Z[1]), (X[3], Y[2], Z[1]), (X[2], Y[2], Z[0]), (s, 0, -s), mat, tile)
        self.quad((X[0], Y[1], Z[2]), (X[0], Y[2], Z[2]), (X[1], Y[2], Z[3]), (X[1], Y[1], Z[3]), (-s, 0, s), mat, tile)
        self.quad((X[3], Y[1], Z[2]), (X[2], Y[1], Z[3]), (X[2], Y[2], Z[3]), (X[3], Y[2], Z[2]), (s, 0, s), mat, tile)
        # corner triangles (8)
        q = 0.577
        for sx, xa, xb in ((-1, X[0], X[1]), (1, X[3], X[2])):
            for sy, ya, yb in ((-1, Y[0], Y[1]), (1, Y[3], Y[2])):
                if sy < 0 and skip_bottom:
                    continue
                for sz, za, zb in ((-1, Z[0], Z[1]), (1, Z[3], Z[2])):
                    self.tri_fan([(xa, yb, zb), (xb, ya, zb), (xb, yb, za)], (sx * q, sy * q, sz * q), mat,
                                 planar_uv([(xa, yb, zb), (xb, ya, zb), (xb, yb, za)], (sx, sy, sz), tile))

    def cylinder(self, center, radius, height, mat, axis="y", segs=12, caps=True, radius2=None, tile=1.0, smooth=True,
                 cap_mat=None, start_angle=0.0):
        """Cylinder or cone frustum standing on `center` (base centre) along +axis."""
        r0, r1 = radius, (radius if radius2 is None else radius2)
        ax = {"x": 0, "y": 1, "z": 2}[axis]
        u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][ax]
        c = np.asarray(center, float)

        def pt(r, ang, h):
            p = c.copy()
            p[u_ax] += r * math.cos(ang)
            p[v_ax] += r * math.sin(ang)
            p[ax] += h
            return p

        circ = 2 * math.pi * max(r0, r1)
        slope = (r0 - r1) / max(height, 1e-9)
        for i in range(segs):
            a0 = start_angle + 2 * math.pi * i / segs
            a1 = start_angle + 2 * math.pi * (i + 1) / segs
            pts = [pt(r0, a0, 0), pt(r0, a1, 0), pt(r1, a1, height), pt(r1, a0, height)]

            def nrm(a):
                n = np.zeros(3)
                n[u_ax] = math.cos(a)
                n[v_ax] = math.sin(a)
                n[ax] = slope
                return n
            mid = (a0 + a1) / 2
            u0, u1 = circ * i / segs / tile, circ * (i + 1) / segs / tile
            uvs = [(u0, 0), (u1, 0), (u1, height / tile), (u0, height / tile)]
            if smooth:
                self.tri_fan(pts, nrm(mid), mat, uvs, smooth_normals=[nrm(a0), nrm(a1), nrm(a1), nrm(a0)])
            else:
                self.tri_fan(pts, nrm(mid), mat, uvs)
        if caps:
            cm = cap_mat or mat
            for r, h, s in ((r0, 0, -1), (r1, height, 1)):
                if r <= 1e-6:
                    continue
                ring = [pt(r, start_angle + 2 * math.pi * i / segs, h) for i in range(segs)]
                n = np.zeros(3)
                n[ax] = s
                self.tri_fan(ring, n, cm, planar_uv(ring, n, tile))

    def sphere(self, center, radius, mat, segs=12, rings=8, tile=1.0, squash=(1.0, 1.0, 1.0), lat_min=-math.pi / 2,
               lat_max=math.pi / 2):
        c = np.asarray(center, float)
        sq = np.asarray(squash, float)

        def pt(la, lo):
            d = np.array([math.cos(la) * math.cos(lo), math.sin(la), math.cos(la) * math.sin(lo)])
            return c + d * radius * sq, _norm(d / np.maximum(sq, 1e-6))
        for j in range(rings):
            la0 = lat_min + (lat_max - lat_min) * j / rings
            la1 = lat_min + (lat_max - lat_min) * (j + 1) / rings
            for i in range(segs):
                lo0 = 2 * math.pi * i / segs
                lo1 = 2 * math.pi * (i + 1) / segs
                corners = [pt(la0, lo0), pt(la0, lo1), pt(la1, lo1), pt(la1, lo0)]
                pts = [p for p, _ in corners]
                ns = [n for _, n in corners]
                uvs = [(i / segs * 2 * math.pi * radius / tile, j / rings * math.pi * radius / tile),
                       ((i + 1) / segs * 2 * math.pi * radius / tile, j / rings * math.pi * radius / tile),
                       ((i + 1) / segs * 2 * math.pi * radius / tile, (j + 1) / rings * math.pi * radius / tile),
                       (i / segs * 2 * math.pi * radius / tile, (j + 1) / rings * math.pi * radius / tile)]
                if np.linalg.norm(pts[0] - pts[1]) < 1e-9:
                    pts, ns, uvs = [pts[0], pts[2], pts[3]], [ns[0], ns[2], ns[3]], [uvs[0], uvs[2], uvs[3]]
                elif np.linalg.norm(pts[2] - pts[3]) < 1e-9:
                    pts, ns, uvs = pts[:3], ns[:3], uvs[:3]
                avg = _norm(sum(ns))
                self.tri_fan(pts, avg, mat, uvs, smooth_normals=ns)

    def lathe(self, profile, center, mat, segs=14, axis="y", tile=1.0, smooth=True, close_top=True, close_bottom=True):
        """Revolves a profile [(radius, height), ...] (bottom to top) around an axis through center."""
        for k in range(len(profile) - 1):
            (ra, ha), (rb, hb) = profile[k], profile[k + 1]
            if abs(hb - ha) < 1e-9 and abs(rb - ra) < 1e-9:
                continue
            sub = Mesh()
            c = np.asarray(center, float).copy()
            ax = {"x": 0, "y": 1, "z": 2}[axis]
            c[ax] += ha
            sub.cylinder(c, ra, hb - ha if abs(hb - ha) > 1e-9 else 1e-6, mat, axis=axis, segs=segs, caps=False,
                         radius2=rb, tile=tile, smooth=smooth)
            self.add(sub)
        ax = {"x": 0, "y": 1, "z": 2}[axis]
        for (r, h), s, ok in ((profile[0], -1, close_bottom), (profile[-1], 1, close_top)):
            if ok and r > 1e-6:
                c = np.asarray(center, float).copy()
                c[ax] += h
                cap = Mesh()
                cap.cylinder(c, r, 1e-6, mat, axis=axis, segs=segs, caps=False)
                n = np.zeros(3)
                n[ax] = s
                u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][ax]
                ring = []
                for i in range(segs):
                    p = c.copy()
                    a = 2 * math.pi * i / segs
                    p[u_ax] += r * math.cos(a)
                    p[v_ax] += r * math.sin(a)
                    ring.append(p)
                self.tri_fan(ring, n, mat, planar_uv(ring, n, tile))

    def torus(self, center, R, r, mat, axis="y", segs=16, tube_segs=6, arc=2 * math.pi, start=0.0):
        ax = {"x": 0, "y": 1, "z": 2}[axis]
        u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][ax]
        c = np.asarray(center, float)

        def pt(a, b):
            ring_dir = np.zeros(3)
            ring_dir[u_ax] = math.cos(a)
            ring_dir[v_ax] = math.sin(a)
            up = np.zeros(3)
            up[ax] = 1
            n = ring_dir * math.cos(b) + up * math.sin(b)
            return c + ring_dir * R + n * r, n
        for i in range(segs):
            a0 = start + arc * i / segs
            a1 = start + arc * (i + 1) / segs
            for j in range(tube_segs):
                b0 = 2 * math.pi * j / tube_segs
                b1 = 2 * math.pi * (j + 1) / tube_segs
                cs = [pt(a0, b0), pt(a1, b0), pt(a1, b1), pt(a0, b1)]
                self.tri_fan([p for p, _ in cs], _norm(sum(n for _, n in cs)), mat, [(0, 0), (1, 0), (1, 1), (0, 1)],
                             smooth_normals=[n for _, n in cs])

    def extrude(self, poly, depth, mat, plane="xy", offset=0.0, tile=1.0, side_mat=None, centered=True):
        """Extrudes a simple polygon [(u, v), ...] (any winding) along the plane's normal axis by depth."""
        ax_u, ax_v, ax_n = {"xy": (0, 1, 2), "xz": (0, 2, 1), "zy": (2, 1, 0)}[plane]
        poly = [tuple(map(float, p)) for p in poly]
        area = sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1] for i in range(len(poly))) / 2
        if area < 0:
            poly = poly[::-1]
        d0 = offset - depth / 2 if centered else offset
        d1 = d0 + depth

        def P(u, v, d):
            p = [0.0, 0.0, 0.0]
            p[ax_u], p[ax_v], p[ax_n] = u, v, d
            return np.array(p)
        tris = ear_clip(poly)
        nf = np.zeros(3)
        nf[ax_n] = 1
        for (i, j, k) in tris:
            a, b, c = poly[i], poly[j], poly[k]
            for d, s in ((d1, 1), (d0, -1)):
                pts = [P(*a, d), P(*b, d), P(*c, d)]
                self.tri_fan(pts, nf * s, mat, planar_uv(pts, nf * s, tile))
        sm = side_mat or mat
        n = len(poly)
        for i in range(n):
            a, b = poly[i], poly[(i + 1) % n]
            e = np.array([b[0] - a[0], b[1] - a[1]])
            out2 = np.array([e[1], -e[0]])
            out = np.zeros(3)
            out[ax_u], out[ax_v] = out2
            pts = [P(*a, d0), P(*b, d0), P(*b, d1), P(*a, d1)]
            self.quad(*pts, _norm(out), sm, tile)

    # ---- output ----------------------------------------------------------------------------------------------
    def vertex_count(self):
        return sum(len(p[0]) for p in self.parts.values())

    def bounds(self):
        allp = [np.asarray(v) for p in self.parts.values() for v in p[0]]
        if not allp:
            return None
        a = np.array(allp)
        return a.min(axis=0), a.max(axis=0)


def planar_uv(pts, normal, tile=1.0):
    n = np.abs(np.asarray(normal, float))
    if n[1] >= n[0] and n[1] >= n[2]:
        return [(p[0] / tile, p[2] / tile) for p in pts]
    if n[0] >= n[2]:
        return [(p[2] / tile, p[1] / tile) for p in pts]
    return [(p[0] / tile, p[1] / tile) for p in pts]


def ear_clip(poly):
    """Triangulates a simple counter-clockwise polygon; returns index triples."""
    idx = list(range(len(poly)))
    out = []

    def area2(a, b, c):
        return (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])

    def inside(p, a, b, c):
        d1, d2, d3 = area2(p, a, b), area2(p, b, c), area2(p, c, a)
        return d1 >= -1e-12 and d2 >= -1e-12 and d3 >= -1e-12
    guard = 0
    while len(idx) > 3 and guard < 10000:
        guard += 1
        n = len(idx)
        for k in range(n):
            i, j, l = idx[(k - 1) % n], idx[k], idx[(k + 1) % n]
            a, b, c = poly[i], poly[j], poly[l]
            if area2(a, b, c) <= 1e-12:
                continue
            if any(inside(poly[m], a, b, c) for m in idx if m not in (i, j, l)):
                continue
            out.append((i, j, l))
            idx.pop(k)
            break
        else:
            break
    if len(idx) == 3:
        out.append(tuple(idx))
    return out


def rot_y(deg):
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 2], m[2, 0], m[2, 2] = math.cos(a), math.sin(a), -math.sin(a), math.cos(a)
    return m


def rot_x(deg):
    a = math.radians(deg)
    m = np.eye(4)
    m[1, 1], m[1, 2], m[2, 1], m[2, 2] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def rot_z(deg):
    a = math.radians(deg)
    m = np.eye(4)
    m[0, 0], m[0, 1], m[1, 0], m[1, 1] = math.cos(a), -math.sin(a), math.sin(a), math.cos(a)
    return m


def translate(x, y, z):
    m = np.eye(4)
    m[:3, 3] = (x, y, z)
    return m
