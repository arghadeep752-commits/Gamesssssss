"""Chaya - geometry of the old wooden house, as plain numpy arrays.

build(layout) -> list of Obj. Each Obj has `prims[material] = (P, N, UV, I)` in the object's local space
(Godot / glTF axes: x east, y up, z south; UV in glTF convention, v pointing down; one UV unit = one texture
repeat). tools/build_map.py turns these into Blender meshes (bevel, ambient-occlusion bake, glTF export);
`python3 mazegeo.py layout.json out.glb` writes a plain .glb without Blender, used for quick local previews.
"""
import json
import math
import struct
import sys
import numpy as np

# material -> metres per texture repeat
TILE = {
    "floor_wood": 2.2, "floor_stone": 2.4, "wall_wood": 1.7, "wall_plaster": 2.4, "ceiling_wood": 2.0,
    "trim_wood": 1.0, "door_wood": 1.3, "brass": 0.5, "stone_altar": 1.2, "red_cloth": 0.5, "clay": 0.4,
    "coconut": 0.3, "kumkum_red": 0.3, "camphor_white": 0.3, "copper": 0.5, "leaf_green": 0.3,
    "lantern_glow": 1.0, "lantern_metal": 1.0, "rope": 0.3,
    # the old Indian house: per-room plaster and floors, carved pillars, beams, shutters
    "floor_terracotta": 1.6, "floor_redtile": 1.8, "floor_checker": 1.6, "floor_clay": 2.2,
    "wall_plaster_blue": 2.4, "wall_plaster_yellow": 2.4, "wall_plaster_red": 2.4, "wall_plaster_white": 2.4,
    "beam_wood": 1.4, "pillar_wood": 0.9, "stone_base": 0.9, "shutter_wood": 1.1, "iron": 0.5,
}
FLOOR_OF = {"pooja": "floor_terracotta", "kitchen": "floor_redtile", "hall": "floor_checker", "store": "floor_clay"}
WALL_OF = {"bedroom": "wall_plaster_blue", "hall": "wall_plaster_yellow", "kitchen": "wall_plaster_yellow",
           "pooja": "wall_plaster_red", "store": "wall_plaster_white"}
CHUNK_CELLS = 3
SPLIT_H = 1.05       # wooden wainscot below, plaster above


class Obj:
    def __init__(self, name, origin=(0.0, 0.0, 0.0), local=False):
        self.name = name
        self.origin = np.array(origin, float)
        self.local = local          # geometry already built around (0, 0, 0)
        self.acc = {}

    def add(self, mat, P, N, UV, I):
        a = self.acc.setdefault(mat, [[], [], [], [], 0])
        a[0].append(P)
        a[1].append(N)
        a[2].append(UV)
        a[3].append(I + a[4])
        a[4] += len(P)

    def finish(self):
        self.prims = {}
        for mat, (P, N, UV, I, _) in self.acc.items():
            off = np.zeros(3) if self.local else self.origin
            self.prims[mat] = (np.concatenate(P) - off, np.concatenate(N), np.concatenate(UV),
                               np.concatenate(I).astype(np.int32))
        return self


def uv_for(P, n, tile):
    ax = int(np.argmax(np.abs(n)))
    if ax == 1:
        return np.stack([P[:, 0], P[:, 2]], 1) / tile
    if ax == 0:
        return np.stack([P[:, 2] * (1 if n[0] > 0 else -1), -P[:, 1]], 1) / tile
    return np.stack([P[:, 0] * (1 if n[2] < 0 else -1), -P[:, 1]], 1) / tile


class Builder:
    def __init__(self, L):
        self.L = L
        self.chunks = {}
        self.objs = []
        self.x0, self.z0 = L["x0"], L["z0"]
        self.cs = L["cell"] * CHUNK_CELLS

    def chunk(self, x, z):
        key = (int((x - self.x0) // self.cs), int((z - self.z0) // self.cs))
        if key not in self.chunks:
            o = Obj("chunk_%d_%d" % key)
            self.chunks[key] = o
        return self.chunks[key]

    def face(self, mat, a, U, V, normal, obj=None, cell=0.65, tile=None):
        """A rectangle a + s*U + t*V facing `normal`, subdivided into ~`cell` sized quads."""
        a, U, V = np.asarray(a, float), np.asarray(U, float), np.asarray(V, float)
        n = np.asarray(normal, float)
        if np.dot(np.cross(U, V), n) < 0:
            U, V = V, U
        lu, lv = np.linalg.norm(U), np.linalg.norm(V)
        if lu < 1e-5 or lv < 1e-5:
            return
        nu = max(1, int(math.ceil(lu / cell - 1e-6)))
        nv = max(1, int(math.ceil(lv / cell - 1e-6)))
        tile = tile or TILE[mat]
        for j in range(nv):
            for i in range(nu):
                p0 = a + U * (i / nu) + V * (j / nv)
                p1 = a + U * ((i + 1) / nu) + V * (j / nv)
                p2 = a + U * ((i + 1) / nu) + V * ((j + 1) / nv)
                p3 = a + U * (i / nu) + V * ((j + 1) / nv)
                P = np.array([p0, p1, p2, p3])
                o = obj if obj is not None else self.chunk(*((p0 + p2) * 0.5)[[0, 2]])
                o.add(mat, P, np.tile(n / np.linalg.norm(n), (4, 1)), uv_for(P, n, tile),
                      np.array([0, 1, 2, 0, 2, 3]))

    def box(self, mn, mx, mats, obj=None, skip=(), cell=0.65):
        """Axis aligned box. mats: a material or dict keyed px nx py ny pz nz (+ 'default')."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        if x1 - x0 < 1e-5 or y1 - y0 < 1e-5 or z1 - z0 < 1e-5:
            return
        if isinstance(mats, str) and mats != "wall_wood":
            cell = max(cell, 2.6)         # trim, doors, furniture: no need for AO-sized quads

        def m(k):
            return mats.get(k, mats.get("default")) if isinstance(mats, dict) else mats
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        if "px" not in skip and m("px"): self.face(m("px"), (x1, y0, z0), (0, 0, dz), (0, dy, 0), (1, 0, 0), obj, cell)
        if "nx" not in skip and m("nx"): self.face(m("nx"), (x0, y0, z0), (0, 0, dz), (0, dy, 0), (-1, 0, 0), obj, cell)
        if "pz" not in skip and m("pz"): self.face(m("pz"), (x0, y0, z1), (dx, 0, 0), (0, dy, 0), (0, 0, 1), obj, cell)
        if "nz" not in skip and m("nz"): self.face(m("nz"), (x0, y0, z0), (dx, 0, 0), (0, dy, 0), (0, 0, -1), obj, cell)
        if "py" not in skip and m("py"): self.face(m("py"), (x0, y1, z0), (dx, 0, 0), (0, 0, dz), (0, 1, 0), obj, cell)
        if "ny" not in skip and m("ny"): self.face(m("ny"), (x0, y0, z0), (dx, 0, 0), (0, 0, dz), (0, -1, 0), obj, cell)

    def wall_box(self, mn, mx, bottom_mat="wall_wood", top_mat="wall_plaster", top_from=0.0, end_mat="trim_wood",
                 ends=True, undersize=False):
        """A wall piece: wooden wainscot up to SPLIT_H, plaster above; end faces (door jambs) in trim wood."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        along_x = (x1 - x0) >= (z1 - z0)
        sides = ("nz", "pz") if along_x else ("nx", "px")
        ends_k = ("nx", "px") if along_x else ("nz", "pz")
        for s in sides:
            lo_top = max(y0, SPLIT_H)
            if y0 < SPLIT_H:
                self.box(mn, (x1, min(y1, SPLIT_H), z1), {k: (bottom_mat if k == s else None) for k in
                                                          ("px", "nx", "pz", "nz", "py", "ny")})
            if y1 > lo_top:
                self.box((x0, lo_top, z0), mx, {k: (top_mat if k == s else None) for k in
                                                ("px", "nx", "pz", "nz", "py", "ny")})
        if ends:
            for e in ends_k:
                self.box(mn, mx, {k: (end_mat if k == e else None) for k in ("px", "nx", "pz", "nz", "py", "ny")})

    def lathe(self, obj, mat, profile, seg=14, center=(0, 0, 0), yaw=0.0, flip=False, closed_top=False):
        """Surface of revolution around the y axis from a (radius, height) profile, smooth normals."""
        pr = np.array(profile, float)
        cx, cy, cz = center
        n = len(pr)
        # outward normal in (r, y): rotate tangent
        tan = np.gradient(pr, axis=0)
        nrm = np.stack([tan[:, 1], -tan[:, 0]], 1)
        nl = np.linalg.norm(nrm, axis=1, keepdims=True)
        nrm = nrm / np.maximum(nl, 1e-9)
        if flip:
            nrm = -nrm
        th = np.linspace(0, 2 * math.pi, seg + 1) + math.radians(yaw)
        P = np.zeros((n, seg + 1, 3))
        N = np.zeros((n, seg + 1, 3))
        for k in range(n):
            P[k, :, 0] = cx + pr[k, 0] * np.cos(th)
            P[k, :, 1] = cy + pr[k, 1]
            P[k, :, 2] = cz + pr[k, 0] * np.sin(th)
            N[k, :, 0] = nrm[k, 0] * np.cos(th)
            N[k, :, 1] = nrm[k, 1]
            N[k, :, 2] = nrm[k, 0] * np.sin(th)
        UV = np.zeros((n, seg + 1, 2))
        UV[..., 0] = np.linspace(0, 1, seg + 1)[None, :] * (2 * math.pi * float(pr[:, 0].max())) / TILE[mat]
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pr, axis=0), axis=1))])
        UV[..., 1] = arc[:, None] / TILE[mat]
        idx = np.arange(n * (seg + 1)).reshape(n, seg + 1)
        tris = []
        for k in range(n - 1):
            for i in range(seg):
                a, b, c, d = idx[k, i], idx[k, i + 1], idx[k + 1, i + 1], idx[k + 1, i]
                tris += [(a, b, c), (a, c, d)]
        tris = np.array(tris)
        Pf, Nf = P.reshape(-1, 3), N.reshape(-1, 3)
        gn = np.cross(Pf[tris[:, 1]] - Pf[tris[:, 0]], Pf[tris[:, 2]] - Pf[tris[:, 0]])
        an = Nf[tris].sum(1)
        bad = np.einsum("ij,ij->i", gn, an) < 0
        tris[bad] = tris[bad][:, [0, 2, 1]]
        keep = np.linalg.norm(gn, axis=1) > 1e-12          # drop degenerate triangles at the axis
        obj.add(mat, Pf, Nf, UV.reshape(-1, 2), tris[keep].reshape(-1))

    def sphere(self, obj, mat, center, r, ry=None, seg=14, rings=8):
        ry = ry or r
        prof = [(r * math.sin(math.pi * k / rings), -ry * math.cos(math.pi * k / rings)) for k in range(rings + 1)]
        prof[0] = (0.0, prof[0][1])
        prof[-1] = (0.0, prof[-1][1])
        self.lathe(obj, mat, [(max(p[0], 1e-4), p[1] + ry) for p in prof], seg, (center[0], center[1] - ry, center[2]))

    def quad(self, obj, mat, P, normal):
        """One quad (4 corners in order round the edge) facing `normal`."""
        P = np.asarray(P, float)
        n = np.asarray(normal, float)
        n = n / max(np.linalg.norm(n), 1e-9)
        if np.dot(np.cross(P[1] - P[0], P[2] - P[0]), n) < 0:
            P = P[::-1].copy()
        obj.add(mat, P, np.tile(n, (4, 1)), uv_for(P, n, TILE[mat]), np.array([0, 1, 2, 0, 2, 3]))

    def box_un(self, obj, orient, u0, u1, y0, y1, n0, n1, mat, skip=()):
        """Box given along a wall: u = along the wall, n = across it (orient 'h': u = x, n = z; 'v': u = z, n = x)."""
        u0, u1 = sorted((u0, u1))
        n0, n1 = sorted((n0, n1))
        if orient == "h":
            self.box((u0, y0, n0), (u1, y1, n1), mat, obj=obj, skip=skip, cell=10.0)
        else:
            m = {"px": "pz", "nx": "nz", "pz": "px", "nz": "nx", "py": "py", "ny": "ny"}
            self.box((n0, y0, u0), (n1, y1, u1), mat, obj=obj, skip=tuple(m[s] for s in skip), cell=10.0)

    def stud(self, obj, orient, u, y, n_face, s, r=0.016):
        """A domed brass stud on a door, its base on the face at n_face, bulging towards s (+1/-1)."""
        prof = [(r, 0.0), (r * 0.92, r * 0.35), (r * 0.7, r * 0.7), (r * 0.38, r * 0.93), (0.0005, r)]
        P, N, UV, I = _lathe_arrays(prof, 6, "brass")
        # lathe axis is +y; turn it to point along the door normal
        if orient == "h":
            R = np.array([[1, 0, 0], [0, 0, -s], [0, s, 0]], float)      # y -> s*z
            c = np.array([u, y, n_face])
        else:
            R = np.array([[0, s, 0], [-s, 0, 0], [0, 0, 1]], float)      # y -> s*x
            c = np.array([n_face, y, u])
        obj.add("brass", P @ R.T + c, N @ R.T, UV, I)

    def tilted_box(self, obj, mat, center, size, yaw=0.0, pitch=0.0):
        """Small rotated box (camphor cubes, leaves, chains)."""
        sx, sy, sz = size
        cy, sy_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
        R = np.array([[cy, 0, sy_], [0, 1, 0], [-sy_, 0, cy]]) @ np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
        h = np.array([sx, sy, sz]) / 2
        for ax, sgn in ((0, 1), (0, -1), (1, 1), (1, -1), (2, 1), (2, -1)):
            nrm = np.zeros(3)
            nrm[ax] = sgn
            u, v = [i for i in range(3) if i != ax]
            U = np.zeros(3); U[u] = h[u] * 2
            V = np.zeros(3); V[v] = h[v] * 2
            a = -h + (nrm * h * (1 + sgn) / 1.0 if False else 0)
            a = np.array([-h[0], -h[1], -h[2]])
            a[ax] = h[ax] * sgn
            self.face(mat, np.asarray(center) + R @ a, R @ U, R @ V, R @ nrm, obj, cell=10.0)


def _lathe_arrays(profile, seg, mat):
    o = Obj("tmp", local=True)
    Builder.lathe(None, o, mat, profile, seg)
    o.finish()
    return o.prims[mat]


def door_dress(B, o, orient, u0, u1, y0, y1, n0, n1, studs=(2, 4), kind="door"):
    """Traditional panelled leaf: raised frame (stiles and rails) on both faces and rows of brass studs."""
    fw, pr = 0.085, 0.014
    for nf, s in ((min(n0, n1), -1), (max(n0, n1), 1)):
        na, nb = nf, nf + s * pr
        B.box_un(o, orient, u0, u0 + fw, y0, y1, na, nb, "trim_wood")
        B.box_un(o, orient, u1 - fw, u1, y0, y1, na, nb, "trim_wood")
        for yy in (y0, y0 + (y1 - y0) * 0.42, y1 - fw):
            B.box_un(o, orient, u0 + fw, u1 - fw, yy, yy + fw, na, nb, "trim_wood")
        cols, rows = studs
        for ci in range(cols):
            uu = u0 + fw + (u1 - u0 - 2 * fw) * (ci + 0.5) / cols
            for ri in range(rows):
                yy = y0 + 0.25 + (y1 - y0 - 0.5) * ri / max(1, rows - 1)
                B.stud(o, orient, uu, yy, nb, s)
        if kind == "pooja":                     # brass bands across the pooja door
            for yb in (0.35, y1 - 0.45):
                B.box_un(o, orient, u0, u1, yb, yb + 0.08, nb, nb + s * 0.006, "brass")


def build(L):
    B = Builder(L)
    C, Rr = L["cols"], L["rows"]
    S, T, H = L["cell"], L["wall_t"], L["wall_h"]
    x0, z0 = L["x0"], L["z0"]
    DW, DH = L["door_w"], L["door_h"]
    W_total, D_total = C * S, Rr * S
    edges = set((min(a, b), max(a, b)) for a, b in L["edges"])

    def kind_at(i, j):
        if 0 <= i < C and 0 <= j < Rr:
            r = L["region"][j][i]
            return L["rooms"][r]["kind"] if r >= 0 else "corridor"
        return None

    def wall_mat(kind):
        return WALL_OF.get(kind, "wall_plaster")

    # ---------------- floor and ceiling (each room has its own floor: terracotta pooja room, red-tiled kitchen,
    # chequered hall, beaten-clay store, old planks elsewhere)
    for j in range(Rr):
        for i in range(C):
            mat = FLOOR_OF.get(kind_at(i, j), "floor_wood")
            ax, az = x0 + i * S, z0 + j * S
            B.face(mat, (ax, 0, az), (S, 0, 0), (0, 0, S), (0, 1, 0))
            B.face("ceiling_wood", (ax, H, az), (S, 0, 0), (0, 0, S), (0, -1, 0), cell=1.3)

    # timber ceiling: heavy beams both ways on the grid, joists between them
    for i in range(C + 1):
        B.box((x0 + i * S - 0.1, H - 0.24, z0), (x0 + i * S + 0.1, H, z0 + D_total), "beam_wood", skip=("py",))
    for j in range(Rr + 1):
        B.box((x0, H - 0.2, z0 + j * S - 0.08), (x0 + W_total, H, z0 + j * S + 0.08), "beam_wood", skip=("py",))
    for i in range(C):
        for k in (1, 2, 3):
            x = x0 + i * S + k * S / 4.0
            B.box((x - 0.035, H - 0.09, z0), (x + 0.035, H, z0 + D_total), "beam_wood", skip=("py",))

    # ---------------- walls: wooden wainscot, then lime plaster coloured by the room on that side
    trim_h = 0.13

    def side_faces(o, p, a, b, y0, y1, side, kind):
        """One face of a wall piece. o: 'h' (wall along x at z=p) or 'v' (along z at x=p); side -1/+1."""
        if kind is None:
            return                                   # outside the house: never seen
        f = p + side * T / 2
        nrm = (0, 0, side) if o == "h" else (side, 0, 0)

        def F(mat, ya, yb):
            if yb - ya < 1e-4:
                return
            if o == "h":
                B.face(mat, (a, ya, f), (b - a, 0, 0), (0, yb - ya, 0), nrm)
            else:
                B.face(mat, (f, ya, a), (0, 0, b - a), (0, yb - ya, 0), nrm)
        F("wall_wood", y0, min(y1, SPLIT_H))
        F(wall_mat(kind), max(y0, SPLIT_H), y1)
        orient = o
        inward = ("pz" if side < 0 else "nz") if o == "h" else ("px" if side < 0 else "nx")
        ends = ("nx", "px") if o == "h" else ("nz", "pz")
        if y0 <= 0.0:
            B.box_un(B.chunk(*(((a + b) / 2, f) if o == "h" else (f, (a + b) / 2))), orient,
                     a, b, 0.0, trim_h, f, f + side * 0.03, "trim_wood", skip=("ny", inward) + ends)
        if y0 < SPLIT_H < y1:
            B.box_un(B.chunk(*(((a + b) / 2, f) if o == "h" else (f, (a + b) / 2))), orient,
                     a, b, SPLIT_H - 0.04, SPLIT_H + 0.04, f, f + side * 0.03, "trim_wood", skip=(inward,) + ends)

    def wall_piece(o, p, a, b, y0, y1, kneg, kpos, jambs=False):
        side_faces(o, p, a, b, y0, y1, -1, kneg)
        side_faces(o, p, a, b, y0, y1, 1, kpos)
        if jambs:
            for e in (a, b):
                if o == "h":
                    B.face("trim_wood", (e, y0, p - T / 2), (0, 0, T), (0, y1 - y0, 0), (1 if e == b else -1, 0, 0))
                else:
                    B.face("trim_wood", (p - T / 2, y0, e), (T, 0, 0), (0, y1 - y0, 0), (0, 0, 1 if e == b else -1))

    wall_segments = []          # (o, line index, cell index, side kinds) for windows and pictures
    for w in L["walls"]:
        if w["o"] == "h":
            j = int(round((w["p"] - z0) / S))
            ia, ib = int(round((w["a"] - x0) / S)), int(round((w["b"] - x0) / S))
            for i in range(ia, ib):
                a = x0 + i * S - (T / 2 if i == ia else 0.0)
                b = x0 + (i + 1) * S + (T / 2 if i == ib - 1 else 0.0)
                kn, kp = kind_at(i, j - 1), kind_at(i, j)
                wall_piece("h", w["p"], a, b, 0.0, H, kn, kp)
                wall_segments.append(("h", w["p"], x0 + (i + 0.5) * S, kn, kp, (i, j - 1), (i, j)))
        else:
            i = int(round((w["p"] - x0) / S))
            ja, jb = int(round((w["a"] - z0) / S)), int(round((w["b"] - z0) / S))
            for j in range(ja, jb):
                a = z0 + j * S - (T / 2 if j == ja else 0.0)
                b = z0 + (j + 1) * S + (T / 2 if j == jb - 1 else 0.0)
                kn, kp = kind_at(i - 1, j), kind_at(i, j)
                wall_piece("v", w["p"], a, b, 0.0, H, kn, kp)
                wall_segments.append(("v", w["p"], z0 + (j + 0.5) * S, kn, kp, (i - 1, j), (i, j)))

    # ---------------- doorways: jambs, lintel, carved frame, panelled studded door leaf or a cusped arch
    doors = []
    for d in L["doorways"]:
        kind = d["kind"]
        ow = DW if kind != "arch" else DW + 0.45
        oh = DH if kind != "arch" else DH + 0.15
        if kind == "pooja":
            ow, oh = DW + 0.3, DH + 0.2
        c = d["c"]
        o_ = d["o"]
        p = d["p"]
        kn, kp = kind_at(*d["cells"][0]), kind_at(*d["cells"][1])
        lo, hi = c - S / 2 - T / 2, c + S / 2 + T / 2
        wall_piece(o_, p, lo, c - ow / 2, 0.0, H, kn, kp, jambs=True)
        wall_piece(o_, p, c + ow / 2, hi, 0.0, H, kn, kp, jambs=True)
        wall_piece(o_, p, c - ow / 2, c + ow / 2, oh, H, kn, kp)
        ch = B.chunk(*((c, p) if o_ == "h" else (p, c)))
        if o_ == "h":
            B.face("trim_wood", (c - ow / 2, oh, p - T / 2), (ow, 0, 0), (0, 0, T), (0, -1, 0), obj=ch, cell=10.0)
        else:
            B.face("trim_wood", (p - T / 2, oh, c - ow / 2), (T, 0, 0), (0, 0, ow), (0, -1, 0), obj=ch, cell=10.0)
        # frame: thick carved posts and a heavier lintel
        fw, pr = 0.11, 0.035
        for ua, ub in ((c - ow / 2 - fw, c - ow / 2), (c + ow / 2, c + ow / 2 + fw)):
            B.box_un(ch, o_, ua, ub, 0.0, oh + fw, p - T / 2 - pr, p + T / 2 + pr, "pillar_wood", skip=("ny",))
            B.box_un(ch, o_, ua - 0.02, ub + 0.02, 0.0, 0.16, p - T / 2 - pr - 0.02, p + T / 2 + pr + 0.02, "pillar_wood", skip=("ny",))
        B.box_un(ch, o_, c - ow / 2 - fw - 0.06, c + ow / 2 + fw + 0.06, oh, oh + fw + 0.05, p - T / 2 - pr - 0.01,
                 p + T / 2 + pr + 0.01, "pillar_wood", skip=())
        if kind == "arch":
            # a cusped (multifoil) arch in carved wood fills the top of the opening
            rise, cusp, lobes, n = 0.5, 0.07, 5, 30
            half = ow / 2
            pts = []
            for k in range(n + 1):
                u = -1.0 + 2.0 * k / n
                base = (oh - rise) + rise * math.sqrt(max(0.0, 1.0 - u * u))
                fr = ((u + 1.0) / 2.0 * lobes) % 1.0
                pts.append((c + u * half, base - cusp * (1.0 - math.sin(math.pi * fr))))
            nf, nb = p - T / 2 - 0.012, p + T / 2 + 0.012

            def P3(u, y, nn):
                return (u, y, nn) if o_ == "h" else (nn, y, u)
            nvec = (0, 0, 1) if o_ == "h" else (1, 0, 0)
            for k in range(n):
                (ua, ya), (ub, yb) = pts[k], pts[k + 1]
                for nn, sg in ((nf, -1), (nb, 1)):
                    B.quad(ch, "pillar_wood", [P3(ua, ya, nn), P3(ub, yb, nn), P3(ub, oh, nn), P3(ua, oh, nn)],
                           tuple(sg * v for v in nvec))
                du, dy = ub - ua, yb - ya
                ln = math.hypot(du, dy) or 1.0
                nu_, ny_ = dy / ln, -du / ln
                B.quad(ch, "pillar_wood", [P3(ua, ya, nf), P3(ub, yb, nf), P3(ub, yb, nb), P3(ua, ya, nb)],
                       P3(nu_, ny_, 0.0) if o_ == "h" else (0.0, ny_, nu_))
        if kind in ("door", "pooja"):
            leaf_w = ow - 0.03
            leaf_h = oh - 0.02
            th = 0.06 if kind == "door" else 0.09
            hinge_side = -1 if d["id"] % 2 == 0 else 1
            if o_ == "h":
                hinge = np.array([c + hinge_side * (ow / 2 - 0.015), 0.0, p])
            else:
                hinge = np.array([p, 0.0, c + hinge_side * (ow / 2 - 0.015)])
            name = "door_%d" % d["id"] if kind == "door" else "pooja_door"
            o = Obj(name, hinge)
            sgn = -hinge_side
            hu = hinge[0] if o_ == "h" else hinge[2]
            hn = hinge[2] if o_ == "h" else hinge[0]
            u0, u1 = sorted((hu, hu + sgn * leaf_w))
            B.box_un(o, o_, u0, u1, 0.01, leaf_h, hn - th / 2, hn + th / 2, "door_wood")
            door_dress(B, o, o_, u0, u1, 0.01, leaf_h, hn - th / 2, hn + th / 2,
                       studs=(2, 4) if kind == "door" else (3, 5), kind=kind)
            # ring handle (kundi) on both sides
            hx = hu + sgn * (leaf_w - 0.14)
            for s in (-1, 1):
                nf = hn + s * (th / 2 + 0.014)
                B.box_un(o, o_, hx - 0.03, hx + 0.03, 0.96, 1.04, nf, nf + s * 0.012, "brass")
                B.box_un(o, o_, hx - 0.008, hx + 0.008, 0.9, 0.97, nf + s * 0.012, nf + s * 0.024, "brass")
            B.objs.append(o)
            doors.append(dict(name=name, hinge=hinge.tolist(), o=o_, sgn=sgn, kind=kind, width=leaf_w, height=leaf_h, thick=th))

    # ---------------- the front door of the house (locked for ever) on the start room's south wall
    st = [r for r in L["rooms"] if r["kind"] == "start"][0]
    fx = x0 + (st["i0"] + 1.5) * S
    fz = z0 + (st["j0"] + st["h"]) * S - T / 2
    fo = B.chunk(fx, fz - 0.5)
    B.box_un(fo, "h", fx - 0.86, fx - 0.76, 0.0, 2.62, fz - 0.12, fz, "pillar_wood")
    B.box_un(fo, "h", fx + 0.76, fx + 0.86, 0.0, 2.62, fz - 0.12, fz, "pillar_wood")
    B.box_un(fo, "h", fx - 0.95, fx + 0.95, 2.5, 2.7, fz - 0.14, fz, "pillar_wood")
    B.box_un(fo, "h", fx - 0.76, fx + 0.76, 0.0, 2.5, fz - 0.03, fz, "trim_wood")
    for (ua, ub) in ((fx - 0.75, fx - 0.005), (fx + 0.005, fx + 0.75)):
        B.box_un(fo, "h", ua, ub, 0.01, 2.48, fz - 0.09, fz - 0.03, "door_wood")
        door_dress(B, fo, "h", ua, ub, 0.01, 2.48, fz - 0.09, fz - 0.03, studs=(3, 6))
    for yb in (0.55, 1.95):                                  # iron straps, chain and padlock
        B.box_un(fo, "h", fx - 0.74, fx + 0.74, yb, yb + 0.07, fz - 0.115, fz - 0.104, "iron")
    for k in range(7):
        B.tilted_box(fo, "iron", (fx - 0.15 + k * 0.05, 1.18 - 0.03 * math.sin(k / 6 * math.pi), fz - 0.13), (0.05, 0.022, 0.012), yaw=0, pitch=0)
    B.box((fx - 0.05, 1.0, fz - 0.15), (fx + 0.05, 1.12, fz - 0.12), "brass", obj=fo, cell=10.0)

    # ---------------- shuttered windows (closed for ever) on the outer walls of corridors and the start room
    win_n = 0
    windows = []
    for (o_, p, uc, kn, kp, cn, cp) in wall_segments:
        if (kn is None) == (kp is None):
            continue                                     # only outer walls
        k_in, side = (kp, 1) if kn is None else (kn, -1)
        if k_in not in ("corridor", "start"):
            continue
        win_n += 1
        if win_n % 2 == 0:
            continue
        f = p + side * T / 2
        windows.append((uc, f) if o_ == "h" else (f, uc))
        wo = B.chunk(*((uc, f) if o_ == "h" else (f, uc)))
        w2, ya, yb = 0.47, 1.0, 2.1
        B.box_un(wo, o_, uc - w2 - 0.09, uc + w2 + 0.09, ya - 0.08, ya, f, f + side * 0.12, "pillar_wood")      # sill
        B.box_un(wo, o_, uc - w2 - 0.08, uc - w2, ya, yb, f, f + side * 0.06, "trim_wood")
        B.box_un(wo, o_, uc + w2, uc + w2 + 0.08, ya, yb, f, f + side * 0.06, "trim_wood")
        B.box_un(wo, o_, uc - w2 - 0.12, uc + w2 + 0.12, yb, yb + 0.12, f, f + side * 0.08, "pillar_wood")     # lintel
        for ua, ub in ((uc - w2, uc - 0.004), (uc + 0.004, uc + w2)):
            B.box_un(wo, o_, ua, ub, ya, yb, f, f + side * 0.035, "shutter_wood")
            B.box_un(wo, o_, ua + 0.03, ub - 0.03, ya + 0.48, ya + 0.53, f + side * 0.035, f + side * 0.045, "iron")
        B.box_un(wo, o_, uc - 0.07, uc + 0.07, 1.48, 1.52, f + side * 0.035, f + side * 0.05, "iron")         # latch

    # ---------------- lanterns (simple ones; build_map.py swaps in real scanned hurricane lanterns)
    for li, l in enumerate(L["lights"]):
        x, y, z = l["pos"]
        ch = Obj("lamp_%d" % li, (x, 0.0, z))
        B.lathe(ch, "lantern_glow", [(0.1, y - 0.2), (0.105, y), (0.1, y + 0.2)], 8, (x, 0, z))
        B.lathe(ch, "lantern_metal", [(0.12, y - 0.2), (0.12, y - 0.24), (0.05, y - 0.26), (0.001, y - 0.26)], 8, (x, 0, z))
        B.lathe(ch, "lantern_metal", [(0.001, y + 0.34), (0.06, y + 0.3), (0.12, y + 0.22), (0.13, y + 0.2)], 8, (x, 0, z))
        B.box((x - 0.008, y + 0.34, z - 0.008), (x + 0.008, H, z + 0.008), "lantern_metal", obj=ch, skip=("ny", "py"))
        B.objs.append(ch)

    # ---------------- carved wooden pillars where four open cells meet (halls, the pooja mandapa, wide corridors)
    pillars = []
    region = L["region"]
    for gj in range(1, Rr):
        for gi in range(1, C):
            cells = [(gi - 1, gj - 1), (gi, gj - 1), (gi - 1, gj), (gi, gj)]
            idx = [cj * C + ci for ci, cj in cells]
            pairs = [(idx[0], idx[1]), (idx[2], idx[3]), (idx[0], idx[2]), (idx[1], idx[3])]
            if not all((min(a, b), max(a, b)) in edges for a, b in pairs):
                continue
            regs = {region[cj][ci] for ci, cj in cells}
            if len(regs) != 1:
                continue
            if kind_at(gi, gj) == "start":
                continue
            px, pz = x0 + gi * S, z0 + gj * S
            pillar(B, px, pz, H)
            pillars.append([round(px, 3), round(pz, 3)])

    # ---------------- ritual item pedestals (simple; build_map.py swaps in scanned wooden stands) and the items
    items = []
    for it in L["items"]:
        x, z = it["pos"]
        ped = Obj("pedestal_" + it["id"], (x, 0.0, z))
        top = 0.74
        B.box((x - 0.28, top - 0.05, z - 0.28), (x + 0.28, top, z + 0.28), "trim_wood", obj=ped, cell=10.0)
        for lx in (-0.23, 0.23):
            for lz in (-0.23, 0.23):
                B.box((x + lx - 0.03, 0, z + lz - 0.03), (x + lx + 0.03, top - 0.05, z + lz + 0.03), "trim_wood", obj=ped, cell=10.0)
        B.box((x - 0.23, 0.25, z - 0.23), (x + 0.23, 0.29, z + 0.23), "trim_wood", obj=ped, cell=10.0)
        B.objs.append(ped)
        o = Obj("item_" + it["id"], (x, top, z), local=True)
        add_item(B, o, it["id"])
        B.objs.append(o)
        items.append(dict(id=it["id"], name=o.name, pos=[x, top, z], face=it.get("face", [0, 1]), ped=[0.56, 0.56]))

    # ---------------- altar in the pooja room
    po = L["pooja"]
    cx, cz = po["center"]
    alt = Obj("altar", (cx, 0.0, cz))
    B.box((cx - 1.0, 0.0, cz - 1.0), (cx + 1.0, 0.18, cz + 1.0), "stone_altar", obj=alt, cell=10.0)
    B.box((cx - 0.75, 0.18, cz - 0.75), (cx + 0.75, 0.36, cz + 0.75), "stone_altar", obj=alt, cell=10.0)
    B.box((cx - 0.55, 0.36, cz - 0.55), (cx + 0.55, 0.50, cz + 0.55), "pillar_wood", obj=alt, cell=10.0)
    B.box((cx - 0.57, 0.50, cz - 0.57), (cx + 0.57, 0.515, cz + 0.57), "red_cloth", obj=alt, cell=10.0)
    B.objs.append(alt)

    # ---------------- spots for framed paintings: room walls with nothing in front of them
    frames = []
    busy = [tuple(pp["pos"]) for pp in L.get("props", [])] + [tuple(it["pos"]) for it in L["items"]] + windows
    for (o_, p, uc, kn, kp, cn, cp) in wall_segments:
        for k_in, side in ((kn, -1), (kp, 1)):
            if k_in not in ("hall", "bedroom", "study", "start", "corridor"):
                continue
            f = p + side * T / 2
            pos = (uc, f) if o_ == "h" else (f, uc)
            if any(math.hypot(pos[0] - bx, pos[1] - bz) < 1.25 for bx, bz in busy):
                continue
            if any(math.hypot(pos[0] - fr["pos"][0], pos[1] - fr["pos"][2]) < 7.0 for fr in frames):
                continue
            nrm = [0.0, float(side)] if o_ == "h" else [float(side), 0.0]
            frames.append(dict(pos=[round(pos[0], 3), 1.72, round(pos[1], 3)], n=nrm, kind=k_in))

    # ---------------- bring chunk geometry into the object list
    objs = [c for _, c in sorted(B.chunks.items())] + B.objs
    for o in objs:
        o.finish()
    meta = dict(doors=doors, items=items, altar=dict(pos=[cx, 0.515, cz]), pillars=pillars, frames=frames)
    return objs, meta


def pillar(B, x, z, H):
    """A turned and carved teak pillar on a stone plinth, with a capital and bracket arms up into the beams."""
    o = B.chunk(x, z)
    B.box((x - 0.2, 0.0, z - 0.2), (x + 0.2, 0.2, z + 0.2), "stone_base", obj=o, skip=("ny",), cell=10.0)
    B.box((x - 0.155, 0.2, z - 0.155), (x + 0.155, 0.3, z + 0.155), "pillar_wood", obj=o, skip=("ny",), cell=10.0)
    prof = [(0.125, 0.3), (0.135, 0.33), (0.1, 0.38), (0.092, 0.5), (0.115, 0.56), (0.132, 0.62), (0.115, 0.68),
            (0.088, 0.74), (0.085, 0.9), (0.08, 1.55), (0.092, 1.62), (0.112, 1.68), (0.092, 1.74), (0.08, 1.8),
            (0.078, 2.22), (0.098, 2.3), (0.128, 2.38), (0.138, 2.43), (0.12, 2.47)]
    B.lathe(o, "pillar_wood", prof, seg=12, center=(x, 0, z))
    B.box((x - 0.16, 2.46, z - 0.16), (x + 0.16, 2.6, z + 0.16), "pillar_wood", obj=o, cell=10.0)
    top = H - 0.24
    for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        for (ln, ya, yb, wd) in ((0.3, 2.6, (2.6 + top) / 2, 0.15), (0.5, (2.6 + top) / 2, top, 0.13)):
            if dx:
                B.box((x + min(0, dx * ln), ya, z - wd / 2), (x + max(0, dx * ln), yb, z + wd / 2), "pillar_wood", obj=o, cell=10.0)
            else:
                B.box((x - wd / 2, ya, z + min(0, dz * ln)), (x + wd / 2, yb, z + max(0, dz * ln)), "pillar_wood", obj=o, cell=10.0)


def add_item(B, o, kind):
    """Ritual objects, modelled from lathe profiles (origin = bottom centre)."""
    if kind == "kalash":
        B.lathe(o, "brass", [(0.001, 0.0), (0.05, 0.0), (0.085, 0.012), (0.12, 0.05), (0.14, 0.11), (0.135, 0.17),
                             (0.1, 0.225), (0.07, 0.255), (0.072, 0.275), (0.1, 0.295), (0.105, 0.3), (0.092, 0.298),
                             (0.06, 0.285)], 16, (0, 0, 0))
        B.sphere(o, "coconut", (0, 0.335, 0), 0.062, 0.075)
        for k in range(7):
            yaw = k * 360.0 / 7
            B.tilted_box(o, "leaf_green", (0.075 * math.cos(math.radians(yaw)), 0.33, 0.075 * math.sin(math.radians(yaw))),
                         (0.012, 0.16, 0.05), yaw=-yaw, pitch=-20)
    elif kind == "diya":
        B.lathe(o, "clay", [(0.001, 0.0), (0.03, 0.0), (0.055, 0.012), (0.082, 0.035), (0.092, 0.058), (0.085, 0.066),
                            (0.072, 0.055), (0.05, 0.04), (0.001, 0.034)], 16, (0, 0, 0))
        B.lathe(o, "clay", [(0.001, 0.034), (0.012, 0.034), (0.012, 0.075), (0.001, 0.08)], 6, (0, 0, 0))
    elif kind == "coconut":
        B.sphere(o, "coconut", (0, 0.1, 0), 0.085, 0.105, seg=16, rings=10)
        B.sphere(o, "coconut", (0.0, 0.165, 0.0), 0.03, 0.015, seg=10, rings=4)
    elif kind == "kumkum":
        B.lathe(o, "brass", [(0.001, 0.0), (0.04, 0.0), (0.06, 0.02), (0.075, 0.05), (0.07, 0.055), (0.055, 0.04)], 16, (0, 0, 0))
        B.lathe(o, "kumkum_red", [(0.001, 0.058), (0.04, 0.05), (0.058, 0.045)], 16, (0, 0, 0))
    elif kind == "kapoor":
        B.lathe(o, "brass", [(0.001, 0.0), (0.09, 0.0), (0.14, 0.012), (0.155, 0.03), (0.15, 0.034), (0.13, 0.02), (0.001, 0.016)], 20, (0, 0, 0))
        for k, (px, pz) in enumerate(((0.0, 0.0), (0.05, 0.03), (-0.04, 0.05), (0.02, -0.05))):
            B.tilted_box(o, "camphor_white", (px, 0.04, pz), (0.035, 0.03, 0.035), yaw=k * 27, pitch=0)
    elif kind == "gangajal":
        B.lathe(o, "copper", [(0.001, 0.0), (0.045, 0.0), (0.075, 0.015), (0.098, 0.055), (0.1, 0.1), (0.085, 0.145),
                              (0.05, 0.175), (0.036, 0.195), (0.04, 0.215), (0.052, 0.225), (0.05, 0.23), (0.034, 0.222)], 16, (0, 0, 0))
        B.lathe(o, "copper", [(0.001, 0.23), (0.04, 0.226), (0.045, 0.235), (0.02, 0.255), (0.001, 0.262)], 12, (0, 0, 0))


# ===================================================================== plain .glb writer (local preview only)

def write_glb(objs, path, extra_nodes=None):
    mats = sorted({m for o in objs for m in o.prims})
    blob = bytearray()
    views, accs, meshes, nodes = [], [], [], []

    def add(data, target, comp, count, typ, mn=None, mx=None):
        while len(blob) % 4:
            blob.append(0)
        views.append(dict(buffer=0, byteOffset=len(blob), byteLength=len(data), target=target))
        blob.extend(data)
        a = dict(bufferView=len(views) - 1, componentType=comp, count=count, type=typ)
        if mn is not None:
            a["min"], a["max"] = mn, mx
        accs.append(a)
        return len(accs) - 1

    for o in objs:
        prims = []
        for m, (P, N, UV, I) in o.prims.items():
            ia = add(I.astype("<u4").tobytes(), 34963, 5125, len(I), "SCALAR")
            pa = add(P.astype("<f4").tobytes(), 34962, 5126, len(P), "VEC3", P.min(0).tolist(), P.max(0).tolist())
            na = add(N.astype("<f4").tobytes(), 34962, 5126, len(N), "VEC3")
            ua = add(UV.astype("<f4").tobytes(), 34962, 5126, len(UV), "VEC2")
            ca = add(np.ones((len(P), 4), "<f4").tobytes(), 34962, 5126, len(P), "VEC4")
            prims.append(dict(attributes=dict(POSITION=pa, NORMAL=na, TEXCOORD_0=ua, COLOR_0=ca), indices=ia,
                              material=mats.index(m)))
        meshes.append(dict(name=o.name, primitives=prims))
        nodes.append(dict(name=o.name, mesh=len(meshes) - 1, translation=[float(v) for v in o.origin]))
    gltf = dict(asset=dict(version="2.0", generator="chaya-dev"), scene=0, scenes=[dict(nodes=list(range(len(nodes))))],
                nodes=nodes, meshes=meshes, accessors=accs, bufferViews=views, buffers=[dict(byteLength=len(blob))],
                materials=[dict(name=m, pbrMetallicRoughness=dict(baseColorFactor=[0.6, 0.6, 0.6, 1], metallicFactor=0, roughnessFactor=1)) for m in mats])
    js = json.dumps(gltf, separators=(",", ":")).encode()
    js += b" " * ((4 - len(js) % 4) % 4)
    while len(blob) % 4:
        blob.append(0)
    out = b"glTF" + struct.pack("<II", 2, 12 + 8 + len(js) + 8 + len(blob))
    out += struct.pack("<I", len(js)) + b"JSON" + js + struct.pack("<I", len(blob)) + b"BIN\x00" + bytes(blob)
    with open(path, "wb") as f:
        f.write(out)


if __name__ == "__main__":
    L = json.load(open(sys.argv[1]))
    objs, meta = build(L)
    tri = sum(len(i) // 3 for o in objs for (_, _, _, i) in o.prims.values())
    print("objects %d, triangles %d, materials %s" % (len(objs), tri, sorted({m for o in objs for m in o.prims})))
    if len(sys.argv) > 2:
        write_glb(objs, sys.argv[2])
        json.dump(meta, open(sys.argv[2] + ".meta.json", "w"))
        print("wrote", sys.argv[2])
