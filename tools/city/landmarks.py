"""Agartala's famous places, modelled from code (Ujjayanta Palace, Jagannath Bari, Gedu Mia's mosque, Neermahal,
Tripura Sundari temple, the railway station, MBB airport, the Akhaura check post ...) and the game's own places
(the gun shop, the clothes shop, your house, the harbour)."""
import math

import numpy as np

import layout as LY
from mesh import L, rect, rot, v3

WHITE = (1.0, 1.0, 0.97)
CREAM = (1.0, 0.95, 0.82)
ORANGE = (1.0, 0.55, 0.16)
RED = (0.78, 0.22, 0.16)
MAROON = (0.55, 0.13, 0.12)
GOLD = (1.0, 0.8, 0.3)
SIGN_ROWS = 16


def sign_uv(row):
    """uv rectangle (bl, br, tr, tl) of one row of a sign layer (row 0 is the top of the picture)."""
    v0 = 1.0 - (row + 1) / SIGN_ROWS
    v1 = 1.0 - row / SIGN_ROWS
    return [(0.0, v0), (1.0, v0), (1.0, v1), (0.0, v1)]


class Site:
    def __init__(self, M, grid, colliders, meta, name):
        self.M, self.grid, self.col, self.meta, self.name = M, grid, colliders, meta, name
        c, yaw, fp = LY.SITES[name]
        self.c = (float(c[0]), float(c[1]))
        self.yaw = float(yaw)        # direction the front faces: 0 = north
        self.fp = fp
        self.y = float(max(0.0, grid.ground(c[0], c[1], fp[0] * 0.6, fp[1] * 0.6, (1, 0)))) if grid else 0.0
        # local frame: x = right as you face the front, z = forward (the way the front faces)
        self.cy, self.sy = math.cos(math.radians(self.yaw)), math.sin(math.radians(self.yaw))

    def W(self, x, z):
        """local -> world. Local +z points the way the front faces (yaw)."""
        return (self.c[0] + x * self.cy + z * self.sy, self.c[1] - x * self.sy + z * self.cy)

    def W3(self, x, y, z):
        p = self.W(x, z)
        return v3(p[0], self.y + y, p[1])

    def mesh(self, x=0.0, z=0.0, group="world"):
        p = self.W(x, z)
        return self.M.get(p[0], p[1], group)

    def box(self, x, y, z, sx, sy, sz, slc, col=(1, 1, 1), tile=(2.5, 2.5), collide=True, faces="nsewt", top=None, emis=0.0, yaw_add=0.0):
        p = self.W(x, z)
        # mesh.box yaw is clockwise seen from above with local +z = north at 0; our local +z = facing yaw -> same rotation
        self.mesh(x, z).box(p[0], self.y + y, p[1], sx, sy, sz, slc, yaw=self.yaw + yaw_add, tile=tile, col=col, faces=faces, top=top, emis=emis)
        if collide:
            self.col.append([p[0], self.y + y, p[1], sx, sy, sz, self.yaw + yaw_add])

    def cyl(self, x, y, z, r, h, slc, col=(1, 1, 1), seg=12, r_top=None, collide=True, tile=(2.0, 2.0)):
        p = self.W(x, z)
        self.mesh(x, z).cylinder(p[0], self.y + y, p[1], r, h, slc, seg=seg, col=col, r_top=r_top, tile=tile)
        if collide and r > 0.3:
            self.col.append([p[0], self.y + y, p[1], r * 1.6, h, r * 1.6, self.yaw])

    def dome(self, x, y, z, r, slc=None, col=WHITE, onion=True, finial=True, seg=16):
        p = self.W(x, z)
        if onion:
            prof = [(r, 0), (r * 1.07, r * 0.3), (r * 1.02, r * 0.62), (r * 0.78, r * 0.95), (r * 0.42, r * 1.25), (r * 0.12, r * 1.5), (0.0, r * 1.62)]
        else:
            prof = [(r * math.cos(a), r * math.sin(a)) for a in np.linspace(0, math.pi / 2, 7)]
            prof[-1] = (0.0, r)
        self.mesh(x, z).lathe(p[0], self.y + y, p[1], prof, slc if slc is not None else L["plaster"], seg=seg, col=col, tile=(1.5, 1.5))
        top = y + (r * 1.62 if onion else r)
        if finial:
            self.mesh(x, z).cylinder(p[0], self.y + top - 0.05, p[1], max(0.05, r * 0.05), r * 0.5, L["metal"], seg=6, col=GOLD, top=False)
            self.mesh(x, z).sphere(p[0], self.y + top + r * 0.25, p[1], max(0.08, r * 0.07), L["metal"], seg=6, rings=4, col=GOLD)

    def ground(self, poly_local, slc, col=(1, 1, 1), lift=0.03, tile=(3.0, 3.0), mark=True):
        poly = [self.W(x, z) for x, z in poly_local]
        cx = sum(p[0] for p in poly) / len(poly)
        cz = sum(p[1] for p in poly) / len(poly)
        self.M.get(cx, cz, "world").polygon(poly, self.y + lift, slc, tile=tile, col=col)
        self.M.get(cx, cz, "coll").polygon(poly, self.y + lift, 0)
        if mark and self.grid:
            self.grid.mark_poly(poly, "site", y=self.y + lift)

    def panel(self, x0, x1, y0, y1, z, slc, uvs=None, emis=0.0, col=(1, 1, 1), side=0.0):
        """Flat panel on a front facing the site's yaw (z = its distance forward)."""
        # a viewer in front of the site looks back along -z, so local +x is on their LEFT
        bl, br = self.W3(x1, y0, z), self.W3(x0, y0, z)
        tr, tl = self.W3(x0, y1, z), self.W3(x1, y1, z)
        self.mesh((x0 + x1) / 2, z).panel(bl, br, tr, tl, slc, uvs=uvs, emis=emis, col=col)

    def sign(self, x0, x1, y0, y1, z, layer, row, emis=0.6, backing=True):
        if backing:
            self.box((x0 + x1) / 2, y0 - 0.08, z - 0.08, (x1 - x0) + 0.2, (y1 - y0) + 0.16, 0.12, L["metal"], col=(0.12, 0.12, 0.14), collide=False)
        self.panel(x0, x1, y0, y1, z + 0.005, L[layer], uvs=sign_uv(row), emis=emis)

    def arcade(self, x0, x1, z, y0, h, n, depth, col=WHITE, slc=None, back=True, floor=True):
        """A veranda: n openings between columns, a lintel band and the wall behind."""
        slc = L["plaster"] if slc is None else slc
        width = x1 - x0
        step = width / n
        for k in range(n + 1):
            xc = x0 + k * step
            self.box(xc, y0, z, 0.55, h, 0.55, slc, col=col, tile=(1.5, 1.5), collide=(k % 2 == 0))
        self.box((x0 + x1) / 2, y0 + h, z - depth / 2 + 0.3, width + 0.6, 0.6, depth + 0.6, slc, col=col, tile=(2.0, 2.0))
        # arch hint: a darker recessed band in each opening's top
        for k in range(n):
            xc = x0 + (k + 0.5) * step
            self.panel(xc - step / 2 + 0.3, xc + step / 2 - 0.3, y0 + h - 0.9, y0 + h - 0.05, z + 0.28, slc, col=tuple(c * 0.82 for c in col),
                       uvs=[(0, 0), (1, 0), (1, 0.4), (0, 0.4)])
        if back:
            self.panel(x0, x1, y0, y0 + h, z - depth + 0.3, slc, col=tuple(c * 0.72 for c in col), uvs=[(0, 0), (width / 2.5, 0), (width / 2.5, h / 2.5), (0, h / 2.5)])
        if floor:
            self.box((x0 + x1) / 2, y0 - 0.25, z - depth / 2 + 0.3, width + 0.6, 0.25, depth + 0.6, L["marble"], col=(1, 1, 1), tile=(1.5, 1.5), collide=False)

    def stairs(self, x, z, w, n, step_h, step_d, slc=None, col=(0.9, 0.9, 0.88), y0=0.0):
        slc = L["concrete"] if slc is None else slc
        for k in range(n):
            self.box(x, y0, z + step_d * (n - 1 - k) + step_d / 2, w, step_h * (k + 1), step_d, slc, col=col, tile=(1.0, 1.0), collide=False)

    def place(self, kind, x, z, **kw):
        p = self.W(x, z)
        self.meta.setdefault("points", []).append(dict(kind=kind, name=self.name, p=[round(p[0], 2), round(self.y + kw.pop("y", 0.0), 2), round(p[1], 2)],
                                                        yaw=round(self.yaw + kw.pop("yaw", 0.0), 1), **kw))


# ================================================================================================= the palace
def ujjayanta_palace(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Ujjayanta Palace")
    s.y = 0.0
    W = 120.0                          # half-length of the front
    # plinth / terrace
    s.ground([(-W - 8, -20), (W + 8, -20), (W + 8, 18), (-W - 8, 18)], L["marble"], col=(1, 1, 1), lift=0.04)
    s.box(0, 0, -3, 2 * W + 6, 1.2, 26, L["marble"], col=(0.95, 0.93, 0.88), tile=(2.0, 1.2))
    base = 1.2
    # main two-storey block behind the verandas (local +z = forward, towards the garden)
    s.box(0, base, -5, 2 * W, 12.0, 18, L["plaster"], col=WHITE, tile=(3.0, 3.0))
    # two storeys of verandas along the front
    for floor in range(2):
        y0 = base + floor * 6.0
        for side in (-1, 1):
            s.arcade(22 if side > 0 else -W + 2, W - 2 if side > 0 else -22, 7.0, y0, 5.2, 12, 3.0, col=WHITE, floor=(floor == 0))
    # balustrade on top
    s.box(0, base + 12.0, 6.6, 2 * W, 1.0, 0.5, L["plaster"], col=WHITE, tile=(2, 2))
    s.box(0, base + 12.0, -13.8, 2 * W, 1.0, 0.5, L["plaster"], col=WHITE, tile=(2, 2))
    # central tower (four storeys) with the great dome (86 ft = 26 m above the ground)
    s.box(0, base, -2, 40, 15.0, 22, L["plaster"], col=WHITE, tile=(3, 3))
    s.arcade(-18, 18, 11.0, base, 6.0, 6, 2.0, col=WHITE)
    s.box(0, base + 15.0, -3, 22, 4.5, 16, L["plaster"], col=WHITE)
    s.cyl(0, base + 19.5, -3, 6.5, 1.2, L["plaster"], col=WHITE, seg=16)
    s.dome(0, base + 20.7, -3, 5.8, col=WHITE)
    # the two side towers with smaller domes
    for side in (-1, 1):
        x = side * 70
        s.box(x, base, -4, 16, 15.5, 20, L["plaster"], col=WHITE)
        s.cyl(x, base + 15.5, -4, 4.5, 1.0, L["plaster"], col=WHITE, seg=14)
        s.dome(x, base + 16.5, -4, 4.0, col=WHITE)
        # corner chhatris
        for cx in (x - 6.5, x + 6.5):
            for cz in (-12.5, 4.5):
                for px in (-0.8, 0.8):
                    for pz in (-0.8, 0.8):
                        s.box(cx + px, base + 15.5, cz + pz, 0.25, 2.0, 0.25, L["plaster"], col=WHITE, collide=False)
                s.dome(cx, base + 17.5, cz, 1.2, col=WHITE, finial=False, seg=10)
        # end pavilions
        s.box(side * (W - 4), base, -4, 12, 13.5, 22, L["plaster"], col=WHITE)
        s.dome(side * (W - 4), base + 13.5, -4, 3.0, col=WHITE, seg=12)
    # grand front steps and the porch
    for xx in (-7, -2.5, 2.5, 7):
        s.cyl(xx, base, 14.0, 0.55, 7.5, L["plaster"], col=WHITE, seg=10)
    s.box(0, base + 7.5, 13.0, 18, 1.0, 4, L["plaster"], col=WHITE)
    s.sign(-9, 9, base + 8.6, base + 10.4, 15.1, "signs2", 5, emis=0.2, backing=False)
    s.stairs(0, 15.5, 16, 5, 0.24, 0.6, slc=L["marble"], col=(1, 1, 1))
    s.place("museum", 0, 20, label="Tripura State Museum")
    s.place("landmark", 0, 40, label="Ujjayanta Palace", radius=130)
    return s


def mughal_garden(M, grid, col, meta):
    """The garden between the two palace ponds: lawns, paths, a long pool with fountains, flower beds."""
    s = Site(M, grid, col, meta, "Mughal Garden")
    s.y = 0.0
    # local frame faces south: z forward = towards Post Office Chowmuhani
    s.ground([(-48, -80), (48, -80), (48, 75), (-48, 75)], L["grass"], col=(0.95, 1.0, 0.95), lift=0.03, tile=(4, 4))
    s.ground([(-6, -80), (6, -80), (6, 75), (-6, 75)], L["marble"], lift=0.05, tile=(2, 2))
    s.ground([(-48, -6), (48, -6), (48, 6), (-48, 6)], L["marble"], lift=0.05, tile=(2, 2))
    # long pool with fountains along the axis
    m = s.mesh(0, 0, "water")
    poly = [s.W(x, z) for x, z in [(-3.2, -60), (3.2, -60), (3.2, 55), (-3.2, 55)]]
    m.polygon(poly, s.y + 0.32, 0, tile=(4, 4), col=(0.5, 0.75, 0.85))
    for side in (-1, 1):
        s.box(side * 3.5, 0.0, -2.5, 0.5, 0.45, 115, L["marble"], col=(0.95, 0.95, 0.92), collide=False)
    for z in range(-50, 55, 15):
        s.cyl(0, 0.3, z, 0.6, 0.5, L["marble"], col=(0.95, 0.95, 0.92), seg=8, collide=False)
        s.place("fountain", 0, z, y=0.8)
    # flower beds
    beds = [(-27, -45), (27, -45), (-27, -20), (27, -20), (-27, 25), (27, 25), (-27, 50), (27, 50)]
    for bx, bz in beds:
        s.box(bx, 0.0, bz, 30, 0.35, 14, L["curb"], col=(0.8, 0.8, 0.78), collide=False, faces="nsew")
        s.ground([(bx - 14.6, bz - 6.6), (bx + 14.6, bz - 6.6), (bx + 14.6, bz + 6.6), (bx - 14.6, bz + 6.6)], L["fern"], col=(1.0, 0.85, 0.9), lift=0.36, mark=False)
    return s


def palace_compound(M, grid, col, meta):
    """Railings around the palace compound, with gates on the south road."""
    pts = [(-252, -142), (252, -142), (252, 202), (-252, 202)]
    gates = [(-15, 15), (-200, -185), (185, 200)]
    for i in range(4):
        a, b = np.array(pts[i], float), np.array(pts[(i + 1) % 4], float)
        length = float(np.linalg.norm(b - a))
        d = (b - a) / length
        t = 0.0
        while t < length:
            seg = min(12.0, length - t)
            p0 = a + d * t
            p1 = a + d * (t + seg)
            mid = (p0 + p1) / 2
            gap = i == 0 and any(lo <= mid[0] <= hi for lo, hi in gates)
            if not gap:
                yaw = math.degrees(math.atan2(d[0], d[1]))
                m = M.get(mid[0], mid[1], "world")
                m.box(mid[0], 0.0, mid[1], 0.35, 0.7, seg, L["plaster"], yaw=yaw, col=WHITE, tile=(1.5, 1.5))
                m.box(mid[0], 0.7, mid[1], 0.06, 1.1, seg, L["metal"], yaw=yaw, col=(0.15, 0.15, 0.15), faces="ew")
                m.box(p0[0], 0.0, p0[1], 0.6, 2.0, 0.6, L["plaster"], yaw=yaw, col=WHITE)
                col.append([float(mid[0]), 0.0, float(mid[1]), 0.4, 1.8, seg, yaw])
            t += seg
    # gate pillars at the main gate
    for gx in (-15, 15):
        m = M.get(gx, -142, "world")
        m.box(gx, 0.0, -142, 1.6, 5.0, 1.6, L["plaster"], col=WHITE)
        m.lathe(gx, 5.0, -142, [(0.9, 0), (0.95, 0.4), (0.6, 1.0), (0.0, 1.4)], L["plaster"], seg=10, col=WHITE)
        col.append([gx, 0.0, -142, 1.6, 5.0, 1.6, 0.0])


# ================================================================================================= temples, mosque
def jagannath_temple(M, grid, col, meta):
    """Octagonal four-storey temple, bright orange, with pyramidal cones on its pillars."""
    s = Site(M, grid, col, meta, "Jagannath Temple")
    s.ground(rect(0, 0, 56, 56), L["tiles"], lift=0.04)
    s.box(0, 0, 0, 30, 1.4, 30, L["plaster"], col=(0.95, 0.9, 0.85), tile=(2, 1.4))
    y = 1.4
    radii = [12.0, 9.0, 6.6, 4.6]
    hs = [6.0, 5.0, 4.2, 3.6]
    for k, (r, h) in enumerate(zip(radii, hs)):
        s.cyl(0, y, 0, r, h, L["plaster"], col=ORANGE, seg=8, tile=(2.5, 2.5))
        s.cyl(0, y + h, 0, r + 0.6, 0.5, L["plaster"], col=(1.0, 0.9, 0.75), seg=8)
        # cones on the eight corners
        for i in range(8):
            a = math.radians(22.5 + 45 * i)
            px, pz = (r + 0.2) * math.cos(a), (r + 0.2) * math.sin(a)
            s.cyl(px, y + h + 0.5, pz, 0.7, 2.2 - k * 0.3, L["plaster"], col=ORANGE, seg=6, r_top=0.02, collide=False)
        y += h + 0.5
    s.cyl(0, y, 0, 3.0, 2.5, L["plaster"], col=ORANGE, seg=8, r_top=0.4)
    s.dome(0, y + 2.4, 0, 0.8, col=GOLD, onion=True, finial=True, seg=8)
    s.stairs(0, 15.0, 8, 4, 0.35, 0.6)
    s.place("landmark", 0, 20, label="Jagannath Bari", radius=30)
    return s


def shikhara_temple(M, grid, col, meta, name, colr, size=10.0):
    s = Site(M, grid, col, meta, name)
    s.ground(rect(0, 0, size * 3, size * 3), L["tiles"], lift=0.04)
    s.box(0, 0, 0, size * 1.6, 1.0, size * 1.6, L["marble"], col=(0.95, 0.95, 0.92))
    s.box(0, 1.0, 0, size, size * 0.6, size, L["plaster"], col=colr)
    y = 1.0 + size * 0.6
    w = size * 0.9
    for k in range(5):
        s.box(0, y, 0, w, size * 0.22, w, L["plaster"], col=colr)
        y += size * 0.22
        w *= 0.8
    s.cyl(0, y, 0, w * 0.7, size * 0.6, L["plaster"], col=colr, seg=8, r_top=0.15)
    s.dome(0, y + size * 0.6, 0, max(0.4, size * 0.07), col=GOLD, seg=8)
    s.box(0, 1.0, size * 0.62, size * 0.5, size * 0.45, size * 0.3, L["plaster"], col=colr)
    s.stairs(0, size * 0.8, size * 0.4, 3, 0.33, 0.5)
    s.place("landmark", 0, size, label=name, radius=size * 2)
    return s


def gedu_mia_mosque(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Gedu Mia Mosque")
    s.ground(rect(0, 0, 86, 76), L["marble"], lift=0.04)
    s.box(0, 0, -6, 46, 1.0, 26, L["marble"], col=(1, 1, 1))
    s.box(0, 1.0, -6, 44, 9.0, 24, L["plaster"], col=WHITE)
    s.arcade(-21, 21, 6.4, 1.0, 6.0, 7, 2.0, col=WHITE)
    for x in (-14, 0, 14):
        r = 6.0 if x == 0 else 4.2
        s.cyl(x, 10.0, -6, r * 0.9, 1.4, L["plaster"], col=WHITE, seg=14)
        s.dome(x, 11.4, -6, r * 0.85, col=WHITE)
    for x in (-24, 24):
        for z in (6.5, -18.5):
            s.cyl(x, 1.0, z, 1.3, 20.0, L["plaster"], col=WHITE, seg=10)
            s.cyl(x, 14.0, z, 1.9, 0.5, L["plaster"], col=WHITE, seg=10)
            s.cyl(x, 21.0, z, 1.0, 2.0, L["plaster"], col=WHITE, seg=8)
            s.dome(x, 23.0, z, 1.1, col=WHITE, seg=8)
    # courtyard wall and gate
    for side in (-1, 1):
        s.box(side * 42, 0, 0, 0.5, 2.2, 74, L["plaster"], col=WHITE)
    s.box(0, 0, 37.5, 84, 2.2, 0.5, L["plaster"], col=WHITE, faces="nsewt")
    s.box(0, 0, -37.5, 84, 2.2, 0.5, L["plaster"], col=WHITE)
    s.sign(-10, 10, 2.4, 3.6, 37.8, "signs2", 15, emis=0.2)
    s.place("landmark", 0, 20, label="Gedu Mia Mosque", radius=40)
    return s


def tripura_sundari_temple(M, grid, col, meta):
    """Ek-ratna Bengali temple: a square sanctum with a curved roof and one tower, on the hill top."""
    s = Site(M, grid, col, meta, "Tripura Sundari Temple")
    s.y = float(LY.height(np.array([s.c[0]]), np.array([s.c[1]]))[0])
    s.ground(rect(0, 0, 50, 50), L["tiles"], lift=0.05)
    s.box(0, 0, 0, 20, 1.5, 20, L["brick"], col=(1, 1, 1), tile=(2, 1))
    s.box(0, 1.5, 0, 14, 7.0, 14, L["plaster"], col=MAROON)
    # curved bangla roof: a slightly domed square cap
    p = s.W(0, 0)
    s.mesh().lathe(p[0], s.y + 8.5, p[1], [(9.8, 0), (9.6, 0.6), (8.5, 1.4), (6.0, 2.2), (3.2, 2.7), (0.0, 2.9)], L["plaster"], seg=4,
                   col=(0.95, 0.92, 0.88))
    s.box(0, 10.8, 0, 5.0, 4.5, 5.0, L["plaster"], col=MAROON)
    s.cyl(0, 15.3, 0, 3.0, 0.6, L["plaster"], col=WHITE, seg=8)
    s.dome(0, 15.9, 0, 2.4, col=WHITE, onion=False)
    s.cyl(0, 18.2, 0, 0.12, 2.5, L["metal"], col=GOLD, seg=6, collide=False)
    s.arcade(-5.5, 5.5, 7.4, 1.5, 4.0, 3, 1.2, col=MAROON)
    s.stairs(0, 10.5, 6, 5, 0.3, 0.7)
    s.place("landmark", 0, 18, label="Tripura Sundari Temple", radius=40)
    return s


def chaturdash_temple(M, grid, col, meta):
    s = shikhara_temple(M, grid, col, meta, "Chaturdash Devta Temple", WHITE, size=11.0)
    return s


def neermahal(M, grid, col, meta):
    """The water palace of Rudrasagar lake: red-brown and white, domes and chhatris, standing in the water."""
    s = Site(M, grid, col, meta, "Neermahal")
    s.y = LY.LAKE_LEVEL + 0.6
    # stone platform rising from the lake bed
    s.box(0, -6.0, 0, 128, 6.0, 64, L["concrete"], col=(0.75, 0.7, 0.62), tile=(3, 2))
    s.ground(rect(0, 0, 126, 62), L["tiles"], lift=0.02, mark=False)
    # two wings joined by a long gallery (western = the royal palace, eastern = the theatre)
    for side, w, h in ((-1, 44, 9.0), (1, 36, 7.0)):
        cx = side * 36
        s.box(cx, 0, 0, w, h, 34, L["plaster"], col=(0.82, 0.38, 0.28))
        s.box(cx, h, 0, w + 1.0, 0.8, 35, L["plaster"], col=WHITE)
        s.arcade(cx - w / 2 + 1, cx + w / 2 - 1, 17.4, 0.0, h - 2.0, 6, 2.0, col=(0.9, 0.85, 0.78))
        for dx in (-w / 2 + 3, w / 2 - 3):
            for dz in (-14, 14):
                for px in (-1.1, 1.1):
                    for pz in (-1.1, 1.1):
                        s.box(cx + dx + px, h + 0.8, dz + pz, 0.3, 2.4, 0.3, L["plaster"], col=WHITE, collide=False)
                s.dome(cx + dx, h + 3.2, dz, 1.7, col=WHITE, finial=False, seg=10)
        s.cyl(cx, h + 0.8, 0, 5.0, 3.0, L["plaster"], col=(0.82, 0.38, 0.28), seg=12)
        s.dome(cx, h + 3.8, 0, 4.5, col=WHITE, seg=14)
    s.box(0, 0, 0, 30, 5.5, 14, L["plaster"], col=(0.85, 0.42, 0.3))
    s.arcade(-14, 14, 7.2, 0.0, 4.5, 6, 1.5, col=WHITE)
    s.box(0, 5.5, 0, 31, 0.6, 15, L["plaster"], col=WHITE)
    # landing steps for boats on the east side
    s.stairs(0, 32.0, 10, 4, 0.2, 0.8, y0=-0.8)
    s.place("boat", 6, 42, yaw=0, y=-0.6)
    s.place("landmark", 0, 0, label="Neermahal", radius=70)
    return s


def chhatri(s, x, y, z, size, colr=WHITE):
    for px in (-size, size):
        for pz in (-size, size):
            s.box(x + px, y, z + pz, 0.3, size * 2.2, 0.3, L["plaster"], col=colr, collide=False)
    s.box(x, y + size * 2.2, z, size * 2.4, 0.3, size * 2.4, L["plaster"], col=colr, collide=False)
    s.dome(x, y + size * 2.5, z, size, col=colr, finial=False, seg=10)


# ================================================================================================= civic places
def kunjaban_palace(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Kunjaban Palace")
    s.y = float(LY.height(np.array([s.c[0]]), np.array([s.c[1]]))[0])
    s.ground(rect(0, 0, 90, 60), L["grass"], lift=0.03, tile=(4, 4))
    s.box(0, 0, 0, 56, 0.8, 24, L["marble"], col=(0.95, 0.95, 0.92))
    s.box(0, 0.8, 0, 54, 9.5, 22, L["plaster"], col=WHITE)
    s.arcade(-26, 26, 11.2, 0.8, 4.2, 10, 2.5, col=WHITE)
    for xx in (-6, -2, 2, 6):
        s.cyl(xx, 0.8, 13.5, 0.5, 8.0, L["plaster"], col=WHITE, seg=10)
    s.box(0, 8.8, 13.0, 15, 1.5, 4.5, L["plaster"], col=WHITE)
    s.box(0, 10.3, 0, 54, 0.8, 22, L["plaster"], col=WHITE)
    s.place("landmark", 0, 20, label="Kunjaban Palace (Raj Bhavan)", radius=40)
    return s


def generic_block(M, grid, col, meta, name, w, d, floors, wall, colr, sign=None, front_glass=False):
    s = Site(M, grid, col, meta, name)
    s.ground(rect(0, 0, s.fp[0], s.fp[1]), L["paving"], lift=0.04, tile=(2, 2))
    h = floors * 3.6
    s.box(0, 0, 0, w, h, d, wall, col=colr, tile=(3.0, 3.6) if wall in (L["facade1"], L["facade2"]) else (2.6, 2.6))
    s.box(0, h, 0, w + 0.3, 0.9, d + 0.3, L["plaster"], col=colr, faces="nsew")
    if sign is not None:
        layer, row = sign
        s.sign(-w * 0.35, w * 0.35, h - 2.6, h - 0.6, d / 2 + 0.06, layer, row, emis=0.8)
    if not front_glass and wall not in (L["facade1"], L["facade2"]):
        for f in range(floors):
            n = int(w / 3.4)
            for k in range(n):
                x = -w / 2 + (k + 0.5) * w / n
                s.panel(x - 0.75, x + 0.75, f * 3.6 + 1.0, f * 3.6 + 2.4, d / 2 + 0.03, L["window"], uvs=[(0, 0), (0.25, 0), (0.25, 1), (0, 1)])
    s.box(0, 0, d / 2 + 1.0, 4.0, 3.2, 2.0, L["plaster"], col=colr, faces="ewt")
    s.panel(-1.6, 1.6, 0.0, 2.8, d / 2 + 0.03, L["glass"], col=(0.8, 0.85, 0.9))
    return s


def hospital(M, grid, col, meta):
    s = generic_block(M, grid, col, meta, "AGMC Hospital", 80, 28, 5, L["plaster"], (0.95, 0.97, 1.0), sign=("signs", 14))
    s.box(0, 0, 20, 14, 0.4, 8, L["concrete"], col=(0.9, 0.9, 0.9), collide=False)
    s.place("hospital", 0, 21, label="AGMC Hospital")
    s.place("landmark", 0, 21, label="AGMC & GB Pant Hospital", radius=40)
    return s


def police_station(M, grid, col, meta):
    s = generic_block(M, grid, col, meta, "West Agartala Police Station", 34, 18, 2, L["plaster"], (0.85, 0.9, 1.0), sign=("signs", 15))
    s.cyl(-14, 0, 12, 0.08, 9.0, L["metal"], col=(0.9, 0.9, 0.9), seg=6, collide=False)
    s.place("police", 0, 12, label="Police Station")
    s.place("vehicle", 10, 12, model="police_jeep", yaw=90)
    s.place("landmark", 0, 14, label="West Agartala Police Station", radius=25)
    return s


def city_centre(M, grid, col, meta):
    s = generic_block(M, grid, col, meta, "City Centre", 70, 46, 4, L["facade2"], (1, 1, 1), sign=("signs2", 3), front_glass=True)
    s.place("landmark", 0, 26, label="City Centre Mall", radius=40)
    return s


def mbb_college(M, grid, col, meta):
    s = Site(M, grid, col, meta, "MBB College")
    s.y = float(LY.height(np.array([s.c[0]]), np.array([s.c[1]]))[0])
    s.ground(rect(0, 0, 90, 60), L["grass"], lift=0.03, tile=(4, 4))
    s.box(0, 0, 0, 70, 8.0, 18, L["brick"], col=(1, 1, 1), tile=(2.4, 1.2))
    s.arcade(-33, 33, 9.2, 0.0, 3.6, 14, 1.2, col=(0.95, 0.92, 0.85))
    s.box(0, 0, 3, 18, 12.0, 24, L["brick"], col=(1, 1, 1), tile=(2.4, 1.2))
    s.box(0, 12.0, 3, 19, 1.5, 25, L["plaster"], col=CREAM)
    s.sign(-8, 8, 9.0, 10.6, 15.06, "signs2", 6, emis=0.2)
    s.place("landmark", 0, 20, label="MBB College", radius=40)
    return s


def malancha_niwas(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Malancha Niwas")
    s.ground(rect(0, 0, 36, 26), L["grass"], lift=0.03)
    s.box(0, 0, 0, 18, 4.0, 10, L["wood"], col=(0.85, 0.75, 0.6))
    s.box(0, 4.0, 0, 20, 0.3, 12, L["roof_tin"], col=(0.6, 0.3, 0.25))
    s.place("landmark", 0, 8, label="Malancha Niwas (Tagore's house)", radius=20)
    return s


def heritage_park(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Heritage Park")
    s.ground(rect(0, 0, 200, 120), L["grass"], lift=0.03, tile=(4, 4))
    for z in (-40, 0, 40):
        s.ground(rect(0, z, 190, 4), L["paving"], lift=0.05, mark=False)
    s.ground(rect(0, 0, 4, 116), L["paving"], lift=0.05, mark=False)
    # miniatures of Tripura's monuments
    chhatri(s, -60, 0.0, -20, 1.5, (0.82, 0.38, 0.28))
    chhatri(s, -30, 0.0, 30, 1.2, WHITE)
    s.box(40, 0, -25, 10, 2.5, 6, L["plaster"], col=WHITE)
    s.dome(40, 2.5, -25, 1.8, col=WHITE, seg=10)
    s.box(70, 0, 30, 6, 4.0, 6, L["rock"], col=(0.8, 0.8, 0.75))
    s.box(0, 0, -55, 10, 4.5, 2, L["plaster"], col=CREAM)
    s.sign(-4.2, 4.2, 3.0, 4.2, -53.9, "signs2", 7, emis=0.3, backing=False)
    s.place("landmark", 0, 0, label="Heritage Park", radius=90)
    return s


def rabindra_kanan(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Rabindra Kanan")
    s.ground(rect(0, 0, 150, 100), L["grass"], lift=0.03, tile=(4, 4))
    s.ground(rect(0, 0, 146, 3.5), L["paving"], lift=0.05, mark=False)
    s.ground(rect(0, 0, 3.5, 96), L["paving"], lift=0.05, mark=False)
    s.box(0, 0, -48, 8, 4.0, 1.5, L["plaster"], col=CREAM)
    s.sign(-3.5, 3.5, 2.6, 3.6, -47.2, "signs2", 12, emis=0.3, backing=False)
    for x in (-40, 40):
        for z in (-30, 30):
            s.box(x, 0, z, 2.2, 0.45, 0.6, L["wood"], col=(0.7, 0.5, 0.35), collide=False)
    s.place("landmark", 0, 0, label="Rabindra Kanan", radius=60)
    return s


def maidan(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Swami Vivekananda Maidan")
    s.ground(rect(0, 0, 118, 64), L["grass"], col=(0.92, 0.95, 0.85), lift=0.03, tile=(5, 5))
    for side in (-1, 1):
        x = side * 52
        for z in (-3.6, 3.6):
            s.box(x, 0, z, 0.12, 2.4, 0.12, L["white"], col=WHITE, collide=False)
        s.box(x, 2.4, 0, 0.12, 0.12, 7.3, L["white"], col=WHITE, collide=False)
    s.place("landmark", 0, 0, label="Swami Vivekananda Maidan", radius=60)
    return s


# ================================================================================================= transport
def railway_station(M, grid, col, meta):
    """Palace-style station building (it was designed after Ujjayanta Palace), platforms, tracks and a train."""
    s = Site(M, grid, col, meta, "Agartala Railway Station")
    s.ground(rect(0, 20, 170, 40), L["paving"], lift=0.04, tile=(2, 2))          # plaza in front (north)
    s.box(0, 0, -4, 140, 1.0, 26, L["marble"], col=(0.95, 0.93, 0.9))
    s.box(0, 1.0, -4, 136, 10.0, 22, L["plaster"], col=CREAM)
    s.arcade(-64, -10, 7.4, 1.0, 5.0, 9, 2.0, col=WHITE)
    s.arcade(10, 64, 7.4, 1.0, 5.0, 9, 2.0, col=WHITE)
    s.box(0, 1.0, -2, 26, 15.0, 22, L["plaster"], col=WHITE)
    s.cyl(0, 16.0, -2, 5.0, 1.0, L["plaster"], col=WHITE, seg=14)
    s.dome(0, 17.0, -2, 4.4, col=WHITE)
    for x in (-45, 45):
        s.box(x, 11.0, -4, 10, 3.0, 10, L["plaster"], col=WHITE)
        s.dome(x, 14.0, -4, 2.8, col=WHITE, seg=12)
    s.sign(-10, 10, 11.0, 13.4, 9.08, "signs2", 0, emis=0.5)
    s.place("landmark", 0, 20, label="Agartala Railway Station", radius=80)
    s.place("taxi_rank", 30, 22, yaw=90)
    # platforms with shelters between the building and the tracks (south)
    for k, z in enumerate((-35.5,)):
        s.box(0, 0, z, 200, 1.0, 7, L["concrete"], col=(0.85, 0.85, 0.82), tile=(2, 1))
        for x in range(-90, 91, 12):
            s.box(x, 1.0, z, 0.3, 3.6, 0.3, L["metal"], col=(0.3, 0.32, 0.35), collide=False)
        s.box(0, 4.6, z, 200, 0.15, 8, L["roof_tin"], col=(0.6, 0.65, 0.7), collide=False)
    return s


def railway(M, grid, col, meta):
    """The track east-west south of the station (with a parked passenger train)."""
    z = LY.RAIL_Z
    x0, x1 = LY.RAIL_X
    x = x0
    while x < x1:
        seg = min(40.0, x1 - x)
        cx = x + seg / 2
        m = M.get(cx, z, "world")
        y = float(max(0.0, LY.height(np.array([cx]), np.array([z]))[0]))
        for dz in (-5.0, 5.0):                         # two lines
            m.box(cx, y, z + dz, seg, 0.35, 4.2, L["rock"], col=(0.7, 0.68, 0.65), tile=(2, 2))
            for r in (-0.75, 0.75):
                m.box(cx, y + 0.35, z + dz + r, seg, 0.16, 0.08, L["metal"], col=(0.45, 0.42, 0.4), faces="nsewt")
            # sleepers drawn as a stripe texture would be cheaper; a few slabs per segment
            for k in range(int(seg / 2.5)):
                m.box(x + 1.25 + k * 2.5, y + 0.33, z + dz, 0.25, 0.06, 2.4, L["concrete"], col=(0.6, 0.58, 0.55), faces="t")
        if grid:
            grid.mark_rect(cx, z, seg, 16, (1, 0), "rail")
        x += seg
    # the train at the platform: blue coaches
    for k in range(6):
        cx = 120 + k * 22.5
        tz = z + 5
        m = M.get(cx, tz, "world")
        m.box(cx, 0.9, tz, 22.0, 3.2, 3.1, L["metal"], col=(0.12, 0.22, 0.55), tile=(1.5, 1.0))
        m.box(cx, 4.1, tz, 21.6, 0.4, 2.8, L["metal"], col=(0.6, 0.6, 0.62), faces="nsewt")
        for w in range(8):
            wx = cx - 9 + w * 2.6
            for side in (-1, 1):
                pz = tz + side * 1.56
                m.box(wx, 2.4, pz, 1.2, 0.8, 0.02, L["glass"], col=(0.3, 0.35, 0.4), faces="nsew")
        col.append([cx, 0.9, tz, 22.0, 3.6, 3.1, 0.0])


def airport(M, grid, col, meta):
    s = Site(M, grid, col, meta, "MBB Airport")
    s.y = 0.0
    s.ground(rect(0, 18, 200, 26), L["paving"], lift=0.04)                      # kerb side in front
    s.box(0, 0, 0, 140, 11.0, 40, L["facade2"], col=(1, 1, 1), tile=(3.0, 3.66))
    # curved roof: a lathe-free trick - a row of slanted panels
    for k in range(-7, 7):
        x = k * 10 + 5
        s.box(x, 11.0, 0, 10.2, 1.4, 44, L["metal"], col=(0.75, 0.78, 0.82), collide=False)
    s.box(0, 0, 22, 40, 6.0, 6, L["glass"], col=(0.6, 0.75, 0.85), faces="nsewt", collide=False)
    s.sign(-25, 25, 7.2, 9.8, 20.1, "signs2", 1, emis=0.6)
    # control tower
    s.cyl(-90, 0, -10, 3.0, 26.0, L["concrete"], col=(0.92, 0.92, 0.9), seg=12)
    s.cyl(-90, 26.0, -10, 6.0, 4.0, L["glass"], col=(0.3, 0.5, 0.6), seg=12)
    s.cyl(-90, 30.0, -10, 6.3, 0.6, L["metal"], col=(0.8, 0.8, 0.8), seg=12)
    s.place("landmark", 0, 30, label="Maharaja Bir Bikram Airport", radius=120)
    # apron and runway (behind the terminal, to the north)
    apron = [s.W(x, z) for x, z in [(-260, -30), (260, -30), (260, -110), (-260, -110)]]
    cx, cz = sum(p[0] for p in apron) / 4, sum(p[1] for p in apron) / 4
    for k in range(4):
        x0 = -260 + k * 130
        poly = [s.W(x, z) for x, z in [(x0, -30), (x0 + 130, -30), (x0 + 130, -110), (x0, -110)]]
        px = sum(p[0] for p in poly) / 4
        pz = sum(p[1] for p in poly) / 4
        M.get(px, pz, "world").polygon(poly, 0.05, L["concrete"], tile=(6, 6), col=(0.9, 0.9, 0.88))
        M.get(px, pz, "coll").polygon(poly, 0.05, 0)
        if grid:
            grid.mark_poly(poly, "site", y=0.05)
    rz = 990.0
    for k in range(14):
        x0 = -700 + k * 100
        poly = [(x0, rz - 23), (x0 + 100, rz - 23), (x0 + 100, rz + 23), (x0, rz + 23)]
        m = M.get(x0 + 50, rz, "world")
        m.polygon(poly, 0.06, L["asphalt"], tile=(10, 10), col=(0.75, 0.75, 0.75))
        M.get(x0 + 50, rz, "coll").polygon(poly, 0.06, 0)
        for d in range(0, 100, 30):
            m.polygon([(x0 + d, rz - 0.5), (x0 + d + 18, rz - 0.5), (x0 + d + 18, rz + 0.5), (x0 + d, rz + 0.5)], 0.075, L["markings"], tile=(1, 1))
        for e in (-21.5, 21.5):
            m.polygon([(x0, rz + e - 0.4), (x0 + 100, rz + e - 0.4), (x0 + 100, rz + e + 0.4), (x0, rz + e + 0.4)], 0.075, L["markings"], tile=(1, 1))
        if grid:
            grid.mark_poly(poly, "site", y=0.06)
    # taxiway from the apron to the runway
    poly = [(-15, 938), (15, 938), (15, 968), (-15, 968)]
    M.get(0, 952, "world").polygon(poly, 0.06, L["asphalt"], tile=(10, 10))
    M.get(0, 952, "coll").polygon(poly, 0.06, 0)
    s.place("vehicle", 120, -70, model="helicopter", yaw=180)
    s.place("runway", 0, -100, label="Runway")
    return s


def helipad(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Helipad")
    s.y = 0.0
    s.ground(rect(0, 0, 36, 36), L["concrete"], lift=0.06, col=(0.8, 0.8, 0.8))
    p = s.W(0, 0)
    m = s.mesh()
    m.cylinder(p[0], 0.07, p[1], 13.0, 0.02, L["markings"], seg=24, col=(1.0, 0.9, 0.2), top=False)
    # the big H
    for x0, x1, z0, z1 in ((-5, -3, -6, 6), (3, 5, -6, 6), (-3, 3, -1, 1)):
        m.polygon([s.W(x0, z0), s.W(x1, z0), s.W(x1, z1), s.W(x0, z1)], 0.08, L["markings"], tile=(1, 1))
    s.place("vehicle", 0, 0, model="helicopter", yaw=0, y=0.1)
    s.place("helipad", 0, 0)
    return s


def checkpost(M, grid, col, meta):
    """Akhaura Integrated Check Post on the Bangladesh border."""
    s = Site(M, grid, col, meta, "Akhaura Check Post")
    s.y = 0.0
    # local +z faces east (yaw 90): the gate spans the road (local x = north-south)
    for x in (-11, 11):
        s.box(x, 0, 0, 3.0, 11.0, 4.0, L["plaster"], col=CREAM)
    s.box(0, 9.0, 0, 25, 3.0, 4.0, L["plaster"], col=CREAM)
    s.sign(-8, 8, 9.4, 11.6, 2.08, "signs2", 2, emis=0.4)
    for x in (-13.5, 13.5):
        s.box(x, 0, 6, 3.0, 2.8, 3.0, L["plaster"], col=(0.9, 0.95, 0.9))
        s.cyl(x, 2.8, 6, 2.0, 0.3, L["roof_tin"], col=(0.3, 0.4, 0.3), seg=8)
    # flags
    for x in (-16, 16):
        s.cyl(x, 0, 12, 0.08, 10.0, L["metal"], col=(0.9, 0.9, 0.9), seg=6, collide=False)
    # barrier arm
    s.box(-2.5, 1.0, 10, 9, 0.18, 0.18, L["markings"], col=(1.0, 0.2, 0.2), collide=False)
    # the border fence along the west edge
    x_f = -1078.0
    z = -LY.HALF + 250
    while z < LY.HALF:
        m = M.get(x_f, z + 10, "world")
        m.box(x_f, 0.0, z + 10, 0.3, 3.2, 20.0, L["metal"], col=(0.35, 0.36, 0.33), faces="ewt", tile=(1, 1))
        m.box(x_f, 0.0, z, 0.25, 3.6, 0.25, L["concrete"], col=(0.7, 0.7, 0.68))
        if not (20 < z + 10 < 60):
            col.append([x_f, -1.0, z + 10, 0.6, 6.0, 20.0, 0.0])
        z += 20.0
    col.append([-1090.0, -1.0, 40.0, 4.0, 8.0, 40.0, 0.0])     # the road beyond the gate is closed
    s.place("landmark", 0, 10, label="Akhaura Check Post (Bangladesh border)", radius=50)
    return s


def harbour(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Harbour")
    s.y = 0.0
    # quay on land and two piers into the sea (local +z = south, the sea side)
    s.ground(rect(0, -24, 160, 20), L["concrete"], lift=0.05, col=(0.82, 0.8, 0.78))
    for x in (-40, 30):
        s.box(x, -4.0, 20, 10, 4.4, 70, L["concrete"], col=(0.7, 0.68, 0.65), tile=(2, 2))
        s.ground(rect(x, 20, 10, 70), L["wood"], lift=0.42, col=(0.75, 0.62, 0.5), mark=False)
        for k in range(6):
            s.cyl(x + 4.6, 0.4, -10 + k * 12, 0.25, 0.7, L["metal"], col=(0.2, 0.2, 0.2), seg=6, collide=False)
        s.place("boat", x + 9.0, 25, yaw=180, y=LY.SEA_LEVEL + 0.4)
        s.place("boat", x - 9.0, 40, yaw=0, y=LY.SEA_LEVEL + 0.4)
    # warehouses
    for k, x in enumerate((-55, 0, 55)):
        s.box(x, 0, -30, 34, 8.0, 16, L["roof_tin"], col=(0.6 + 0.1 * k, 0.65, 0.7), tile=(1.2, 2.0))
    s.sign(-12, 12, 6.0, 7.5, -21.9, "signs2", 8, emis=0.3)
    s.place("landmark", 0, 0, label="Agartala Harbour", radius=80)
    return s


def lighthouse(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Lighthouse")
    s.y = float(max(LY.SEA_LEVEL + 0.5, LY.height(np.array([s.c[0]]), np.array([s.c[1]]))[0]))
    s.box(0, -3.0, 0, 16, 3.2, 16, L["rock"], col=(0.75, 0.72, 0.68))
    for k in range(6):
        s.cyl(0, k * 4.0, 0, 3.0 - k * 0.25, 4.0, L["plaster"], col=WHITE if k % 2 == 0 else (0.85, 0.12, 0.1), seg=14, r_top=2.75 - k * 0.25)
    s.cyl(0, 24.0, 0, 2.0, 2.6, L["glass"], col=(1.0, 0.95, 0.7), seg=12)
    p = s.W(0, 0)
    s.mesh().lathe(p[0], s.y + 26.6, p[1], [(2.4, 0), (1.8, 0.8), (0.0, 1.8)], L["metal"], seg=12, col=(0.2, 0.2, 0.22))
    s.place("lamp_big", 0, 0, y=25.2)
    s.place("landmark", 0, 0, label="Lighthouse", radius=30)
    return s


def bazaar(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Battala Bazaar")
    s.ground(rect(0, 0, 60, 40), L["paving"], lift=0.04, col=(0.85, 0.82, 0.78))
    k = 0
    for x in range(-24, 25, 8):
        for z in (-12, 0, 12):
            colr = [(0.85, 0.2, 0.15), (0.15, 0.35, 0.8), (0.2, 0.6, 0.3), (0.95, 0.6, 0.1)][k % 4]
            s.box(x, 0, z, 4.0, 0.9, 2.0, L["wood"], col=(0.75, 0.6, 0.45), collide=True)
            for px in (-2.0, 2.0):
                for pz in (-1.4, 1.4):
                    s.box(x + px, 0, z + pz, 0.08, 2.4, 0.08, L["wood"], col=(0.5, 0.4, 0.3), collide=False)
            s.box(x, 2.4, z, 4.6, 0.05, 3.4, L["fabric"], col=colr, collide=False, faces="nsewt")
            s.box(x, 0.9, z, 3.6, 0.35, 1.6, L["fern"], col=(1.0, 0.9, 0.6), collide=False, faces="nsewt")
            k += 1
    s.sign(-10, 10, 3.2, 4.4, 20.2, "signs2", 10, emis=0.3)
    s.place("crowd", 0, 0, radius=25)
    s.place("landmark", 0, 0, label="Battala Bazaar", radius=40)
    return s


def motor_stand(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Motor Stand")
    s.ground(rect(0, 0, 70, 40), L["concrete"], lift=0.04, col=(0.8, 0.8, 0.78))
    s.box(0, 0, -16, 50, 0.3, 6, L["concrete"], col=(0.85, 0.85, 0.82), collide=False)
    for x in range(-24, 25, 6):
        s.box(x, 0.3, -18, 0.2, 3.0, 0.2, L["metal"], col=(0.3, 0.3, 0.35), collide=False)
    s.box(0, 3.3, -16, 52, 0.15, 7, L["roof_tin"], col=(0.3, 0.45, 0.65), collide=False)
    s.sign(-8, 8, 3.5, 4.7, -12.4, "signs2", 11, emis=0.3)
    for k, x in enumerate((-22, 0, 22)):
        s.place("vehicle", x, 2, model="bus", yaw=90, parked=True)
    s.place("vehicle", -28, 14, model="auto_rickshaw", yaw=0, parked=True)
    s.place("vehicle", -24, 14, model="e_rickshaw", yaw=0, parked=True)
    s.place("landmark", 0, 0, label="Motor Stand", radius=40)
    return s


def ghat(M, grid, col, meta):
    s = Site(M, grid, col, meta, "Ghat")
    s.y = 0.0
    for k in range(10):
        s.box(0, -0.3 * (k + 1), 2.0 + k * 1.2, 22, 0.3, 1.2, L["concrete"], col=(0.75, 0.73, 0.7), collide=False)
    s.place("boat", 0, 22, yaw=90, y=LY.RIVER_LEVEL + 0.4)
    s.place("landmark", 0, 8, label="Battala Ghat", radius=20)
    return s


# ================================================================================================= your places
def gun_shop(M, grid, col, meta):
    s = generic_block(M, grid, col, meta, "Danga Arms", 18, 12, 2, L["brick"], (1, 1, 1), sign=("signs", 12))
    s.place("gunshop", 0, 7.5, label="Danga Arms (Gun Shop)")
    s.place("landmark", 0, 8, label="Danga Arms", radius=15, icon="gun")
    return s


def clothes_shop(M, grid, col, meta):
    s = generic_block(M, grid, col, meta, "Fashion Point", 16, 12, 2, L["plaster"], (1.0, 0.85, 0.9), sign=("signs", 13))
    s.panel(-7, 7, 0.2, 3.0, 6.04, L["shopfront"], uvs=[(0.5, 0), (1.0, 0), (1.0, 1), (0.5, 1)], emis=0.4)
    s.place("clothes", 0, 7.5, label="Fashion Point (Clothes)")
    s.place("landmark", 0, 8, label="Fashion Point", radius=15, icon="shirt")
    return s


def player_house(M, grid, col, meta):
    """Your two-storey house in Krishnanagar: cream and orange, balcony, gate, compound wall, parking."""
    s = Site(M, grid, col, meta, "Player House")
    s.ground(rect(0, 0, 24, 26), L["tiles"], lift=0.05, col=(0.9, 0.88, 0.85))
    s.box(0, 0, -3, 12, 3.3, 11, L["plaster"], col=(1.0, 0.93, 0.78))
    s.box(0, 3.3, -3, 12.4, 0.25, 11.4, L["concrete"], col=(0.95, 0.6, 0.3))
    s.box(0, 3.55, -3, 12, 3.1, 11, L["plaster"], col=(1.0, 0.93, 0.78))
    s.box(0, 6.65, -3, 12.6, 0.3, 11.6, L["concrete"], col=(0.95, 0.6, 0.3))
    s.box(0, 3.3, 3.2, 10, 0.18, 1.6, L["concrete"], col=(0.95, 0.6, 0.3))
    s.box(0, 3.5, 3.95, 10, 0.95, 0.1, L["metal"], col=(0.2, 0.2, 0.22), faces="nsewt")
    for f, y in ((0, 0.9), (1, 4.4)):
        for x in (-3.5, 3.5):
            s.panel(x - 0.8, x + 0.8, y, y + 1.4, 2.53, L["window"], uvs=[(0.25, 0), (0.5, 0), (0.5, 1), (0.25, 1)], emis=0.5)
    s.panel(-0.8, 0.8, 0.0, 2.4, 2.53, L["wood"], col=(0.55, 0.3, 0.18))
    s.cyl(3, 6.95, -6, 0.65, 1.25, L["metal"], col=(0.08, 0.08, 0.09), seg=10)
    # compound wall with a gate on the lane (front = north)
    for x0, x1 in ((-12, -3), (3, 12)):
        s.box((x0 + x1) / 2, 0, 12.7, x1 - x0, 1.6, 0.25, L["plaster"], col=(0.95, 0.6, 0.3))
    for side in (-1, 1):
        s.box(side * 12, 0, 0, 0.25, 1.6, 25.5, L["plaster"], col=(0.95, 0.6, 0.3))
    s.box(0, 0, -12.7, 24, 1.6, 0.25, L["plaster"], col=(0.95, 0.6, 0.3))
    s.box(0, 1.0, 12.7, 6, 0.06, 0.06, L["metal"], col=(0.2, 0.2, 0.2), collide=False)
    s.place("house", 0, 4.5, label="Your House")
    s.place("vehicle", 6.5, 8, model="motorbike", yaw=180, parked=True, owned=True)
    s.place("spawn", 0, 9, yaw=0)
    s.place("landmark", 0, 6, label="Your House", radius=12, icon="house")
    return s


def lake_jetty(M, grid, col, meta):
    x0, z0 = -338.0, -640.0
    m = M.get(x0 - 12, z0, "world")
    m.box(x0 - 14, LY.LAKE_LEVEL - 2.0, z0, 30, 2.5, 4, L["concrete"], col=(0.7, 0.68, 0.65))
    m.polygon([(x0 - 29, z0 - 2), (x0 + 1, z0 - 2), (x0 + 1, z0 + 2), (x0 - 29, z0 + 2)], LY.LAKE_LEVEL + 0.52, L["wood"], tile=(1, 3),
              col=(0.75, 0.62, 0.5))
    M.get(x0 - 12, z0, "coll").polygon([(x0 - 29, z0 - 2), (x0 + 1, z0 - 2), (x0 + 1, z0 + 2), (x0 - 29, z0 + 2)], LY.LAKE_LEVEL + 0.52, 0)
    meta.setdefault("points", []).append(dict(kind="boat", name="Rudrasagar Jetty", p=[x0 - 26, LY.LAKE_LEVEL + 0.4, z0 + 5], yaw=270.0))
    meta["points"].append(dict(kind="landmark", name="Rudrasagar Jetty", p=[x0 - 10, 0.0, z0], yaw=0.0, label="Rudrasagar Lake", radius=200))


BUILDERS = [lake_jetty, ujjayanta_palace, mughal_garden, palace_compound, jagannath_temple,
            lambda M, g, c, m: shikhara_temple(M, g, c, m, "Lakshmi Narayan Temple", CREAM, 9.0),
            lambda M, g, c, m: shikhara_temple(M, g, c, m, "Ummaneshwar Temple", WHITE, 6.0),
            gedu_mia_mosque, tripura_sundari_temple, chaturdash_temple, neermahal, kunjaban_palace, hospital, police_station,
            city_centre, mbb_college, malancha_niwas, heritage_park, rabindra_kanan, maidan, railway_station, railway, airport,
            helipad, checkpost, harbour, lighthouse, bazaar, motor_stand, ghat, gun_shop, clothes_shop, player_house]


def build_all(M, grid, colliders, meta):
    for fn in BUILDERS:
        fn(M, grid, colliders, meta)
