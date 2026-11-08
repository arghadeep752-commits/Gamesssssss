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
}
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


def build(L):
    B = Builder(L)
    C, Rr = L["cols"], L["rows"]
    S, T, H = L["cell"], L["wall_t"], L["wall_h"]
    x0, z0 = L["x0"], L["z0"]
    DW, DH = L["door_w"], L["door_h"]
    W_total, D_total = C * S, Rr * S

    # ---------------- floor and ceiling
    for j in range(Rr):
        for i in range(C):
            r = L["region"][j][i]
            kind = L["rooms"][r]["kind"] if r >= 0 else ""
            mat = "floor_stone" if kind in ("pooja", "kitchen") else "floor_wood"
            ax, az = x0 + i * S, z0 + j * S
            B.face(mat, (ax, 0, az), (S, 0, 0), (0, 0, S), (0, 1, 0))
            B.face("ceiling_wood", (ax, H, az), (S, 0, 0), (0, 0, S), (0, -1, 0), cell=1.3)

    # beams across the ceiling every cell
    for i in range(C + 1):
        B.box((x0 + i * S - 0.09, H - 0.2, z0), (x0 + i * S + 0.09, H, z0 + D_total), "trim_wood", skip=("py",))

    # ---------------- walls
    trim_h = 0.13
    for w in L["walls"]:
        if w["o"] == "h":
            mn = (w["a"] - T / 2, 0.0, w["p"] - T / 2)
            mx = (w["b"] + T / 2, H, w["p"] + T / 2)
        else:
            mn = (w["p"] - T / 2, 0.0, w["a"] - T / 2)
            mx = (w["p"] + T / 2, H, w["b"] + T / 2)
        B.wall_box(mn, mx, ends=False)
        # skirting board and chair rail on both faces
        if w["o"] == "h":
            for s in (-1, 1):
                zf = w["p"] + s * T / 2
                za, zb = sorted((zf, zf + s * 0.03))
                B.box((w["a"] - T / 2, 0, za), (w["b"] + T / 2, trim_h, zb), "trim_wood", skip=("ny", "py", "nx", "px"))
                B.box((w["a"] - T / 2, SPLIT_H - 0.04, za), (w["b"] + T / 2, SPLIT_H + 0.04, zb), "trim_wood", skip=("nx", "px"))
        else:
            for s in (-1, 1):
                xf = w["p"] + s * T / 2
                xa, xb = sorted((xf, xf + s * 0.03))
                B.box((xa, 0, w["a"] - T / 2), (xb, trim_h, w["b"] + T / 2), "trim_wood", skip=("ny", "py", "nz", "pz"))
                B.box((xa, SPLIT_H - 0.04, w["a"] - T / 2), (xb, SPLIT_H + 0.04, w["b"] + T / 2), "trim_wood", skip=("nz", "pz"))

    # ---------------- doorways: jambs, lintel, frame, door leaf
    doors = []
    for d in L["doorways"]:
        kind = d["kind"]
        ow = DW if kind != "arch" else DW + 0.45
        oh = DH if kind != "arch" else DH + 0.15
        if kind == "pooja":
            ow, oh = DW + 0.3, DH + 0.2
        c = d["c"]
        lo, hi = c - S / 2 - T / 2, c + S / 2 + T / 2
        for (a, b) in ((lo, c - ow / 2), (c + ow / 2, hi)):
            if d["o"] == "h":
                B.wall_box((a, 0, d["p"] - T / 2), (b, H, d["p"] + T / 2))
            else:
                B.wall_box((d["p"] - T / 2, 0, a), (d["p"] + T / 2, H, b))
        if d["o"] == "h":
            B.wall_box((c - ow / 2, oh, d["p"] - T / 2), (c + ow / 2, H, d["p"] + T / 2), ends=False)
            B.box((c - ow / 2, oh - 0.001, d["p"] - T / 2), (c + ow / 2, oh, d["p"] + T / 2), "trim_wood", skip=("px", "nx", "pz", "nz", "py"))
        else:
            B.wall_box((d["p"] - T / 2, oh, c - ow / 2), (d["p"] + T / 2, H, c + ow / 2), ends=False)
            B.box((d["p"] - T / 2, oh - 0.001, c - ow / 2), (d["p"] + T / 2, oh, c + ow / 2), "trim_wood", skip=("px", "nx", "pz", "nz", "py"))
        # frame
        fw, pr = 0.09, 0.03
        if d["o"] == "h":
            for a, b in ((c - ow / 2 - fw, c - ow / 2), (c + ow / 2, c + ow / 2 + fw)):
                B.box((a, 0, d["p"] - T / 2 - pr), (b, oh + fw, d["p"] + T / 2 + pr), "trim_wood", skip=("ny",))
            B.box((c - ow / 2 - fw, oh, d["p"] - T / 2 - pr), (c + ow / 2 + fw, oh + fw, d["p"] + T / 2 + pr), "trim_wood", skip=("ny",))
        else:
            for a, b in ((c - ow / 2 - fw, c - ow / 2), (c + ow / 2, c + ow / 2 + fw)):
                B.box((d["p"] - T / 2 - pr, 0, a), (d["p"] + T / 2 + pr, oh + fw, b), "trim_wood", skip=("ny",))
            B.box((d["p"] - T / 2 - pr, oh, c - ow / 2 - fw), (d["p"] + T / 2 + pr, oh + fw, c + ow / 2 + fw), "trim_wood", skip=("ny",))
        if kind in ("door", "pooja"):
            leaf_w = ow - 0.03
            leaf_h = oh - 0.02
            th = 0.06 if kind == "door" else 0.09
            hinge_side = -1 if d["id"] % 2 == 0 else 1
            if d["o"] == "h":
                hinge = np.array([c + hinge_side * (ow / 2 - 0.015), 0.0, d["p"]])
            else:
                hinge = np.array([d["p"], 0.0, c + hinge_side * (ow / 2 - 0.015)])
            name = "door_%d" % d["id"] if kind == "door" else "pooja_door"
            o = Obj(name, hinge)
            sgn = -hinge_side
            if d["o"] == "h":
                mn = (hinge[0] + (0 if sgn > 0 else -leaf_w), 0.01, hinge[2] - th / 2)
                mx = (hinge[0] + (leaf_w if sgn > 0 else 0), leaf_h, hinge[2] + th / 2)
            else:
                mn = (hinge[0] - th / 2, 0.01, hinge[2] + (0 if sgn > 0 else -leaf_w))
                mx = (hinge[0] + th / 2, leaf_h, hinge[2] + (leaf_w if sgn > 0 else 0))
            B.box(mn, mx, "door_wood", obj=o)
            # brass handle on both sides
            hx = (mn[0] + mx[0]) / 2
            hz = (mn[2] + mx[2]) / 2
            for s in (-1, 1):
                if d["o"] == "h":
                    cx = hinge[0] + sgn * (leaf_w - 0.12)
                    B.box((cx - 0.02, 0.95, hinge[2] + s * th / 2 - (0.0 if s > 0 else 0.07)), (cx + 0.02, 1.0, hinge[2] + s * th / 2 + (0.07 if s > 0 else 0.0)), "brass", obj=o)
                else:
                    cz = hinge[2] + sgn * (leaf_w - 0.12)
                    B.box((hinge[0] + s * th / 2 - (0.0 if s > 0 else 0.07), 0.95, cz - 0.02), (hinge[0] + s * th / 2 + (0.07 if s > 0 else 0.0), 1.0, cz + 0.02), "brass", obj=o)
            if kind == "pooja":
                for yb in (0.35, leaf_h - 0.35):          # brass bands
                    if d["o"] == "h":
                        B.box((mn[0], yb, mn[2] - 0.006), (mx[0], yb + 0.1, mx[2] + 0.006), "brass", obj=o)
                    else:
                        B.box((mn[0] - 0.006, yb, mn[2]), (mx[0] + 0.006, yb + 0.1, mx[2]), "brass", obj=o)
            B.objs.append(o)
            doors.append(dict(name=name, hinge=hinge.tolist(), o=d["o"], sgn=sgn, kind=kind, width=leaf_w, height=leaf_h, thick=th))

    # ---------------- front door (decor) on the start room's south wall
    st = [r for r in L["rooms"] if r["kind"] == "start"][0]
    fx = x0 + (st["i0"] + 1.5) * S
    fz = z0 + (st["j0"] + st["h"]) * S - T / 2
    B.box((fx - 0.75, 0, fz - 0.07), (fx + 0.75, 2.4, fz), "door_wood", skip=("pz",))
    B.box((fx - 0.83, 0, fz - 0.1), (fx - 0.75, 2.5, fz), "trim_wood", skip=("pz",))
    B.box((fx + 0.75, 0, fz - 0.1), (fx + 0.83, 2.5, fz), "trim_wood", skip=("pz",))
    B.box((fx - 0.83, 2.4, fz - 0.1), (fx + 0.83, 2.5, fz), "trim_wood", skip=("pz",))
    for yb in (0.5, 1.2, 1.9):
        B.box((fx - 0.75, yb, fz - 0.085), (fx + 0.75, yb + 0.1, fz - 0.07), "lantern_metal", skip=("pz",))
    B.box((fx - 0.08, 1.05, fz - 0.14), (fx + 0.08, 1.25, fz - 0.07), "brass", skip=("pz",))   # padlock

    # ---------------- lanterns (hanging from the ceiling)
    for li, l in enumerate(L["lights"]):
        x, y, z = l["pos"]
        o = None
        B.lathe(B.chunk(x, z), "lantern_metal", [(0.001, y + 0.34), (0.06, y + 0.3), (0.12, y + 0.22), (0.13, y + 0.2)], 8)
        B.lathe(B.chunk(x, z), "lantern_glow", [(0.1, y + 0.2), (0.105, y + 0.0), (0.095, y - 0.2)], 8, (x, 0, z)) if False else None
        ch = B.chunk(x, z)
        B.lathe(ch, "lantern_glow", [(0.1, y - 0.2), (0.105, y), (0.1, y + 0.2)], 8, (x, 0, z))
        B.lathe(ch, "lantern_metal", [(0.12, y - 0.2), (0.12, y - 0.24), (0.05, y - 0.26), (0.001, y - 0.26)], 8, (x, 0, z))
        B.lathe(ch, "lantern_metal", [(0.001, y + 0.34), (0.06, y + 0.3), (0.12, y + 0.22), (0.13, y + 0.2)], 8, (x, 0, z))
        B.box((x - 0.008, y + 0.34, z - 0.008), (x + 0.008, H, z + 0.008), "lantern_metal", obj=ch, skip=("ny", "py"))

    # ---------------- ritual item pedestals and the items themselves
    items = []
    for it in L["items"]:
        x, z = it["pos"]
        ped = B.chunk(x, z)
        top = 0.74
        B.box((x - 0.28, top - 0.05, z - 0.28), (x + 0.28, top, z + 0.28), "trim_wood", obj=ped, cell=10.0)
        for lx in (-0.23, 0.23):
            for lz in (-0.23, 0.23):
                B.box((x + lx - 0.03, 0, z + lz - 0.03), (x + lx + 0.03, top - 0.05, z + lz + 0.03), "trim_wood", obj=ped, cell=10.0)
        B.box((x - 0.23, 0.25, z - 0.23), (x + 0.23, 0.29, z + 0.23), "trim_wood", obj=ped, cell=10.0)
        o = Obj("item_" + it["id"], (x, top, z), local=True)
        add_item(B, o, it["id"])
        B.objs.append(o)
        items.append(dict(id=it["id"], name=o.name, pos=[x, top, z]))

    # ---------------- altar in the pooja room
    po = L["pooja"]
    cx, cz = po["center"]
    alt = Obj("altar", (cx, 0.0, cz))
    B.box((cx - 1.0, 0.0, cz - 1.0), (cx + 1.0, 0.18, cz + 1.0), "stone_altar", obj=alt, cell=10.0)
    B.box((cx - 0.75, 0.18, cz - 0.75), (cx + 0.75, 0.36, cz + 0.75), "stone_altar", obj=alt, cell=10.0)
    B.box((cx - 0.55, 0.36, cz - 0.55), (cx + 0.55, 0.50, cz + 0.55), "trim_wood", obj=alt, cell=10.0)
    B.box((cx - 0.57, 0.50, cz - 0.57), (cx + 0.57, 0.515, cz + 0.57), "red_cloth", obj=alt, cell=10.0)
    B.objs.append(alt)

    # ---------------- bring chunk geometry into the object list
    objs = [c for _, c in sorted(B.chunks.items())] + B.objs
    for o in objs:
        o.finish()
    meta = dict(doors=doors, items=items, altar=dict(pos=[cx, 0.515, cz]))
    return objs, meta


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
