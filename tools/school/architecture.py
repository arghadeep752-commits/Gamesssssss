"""The school building itself, from the layout (numpy only): walls with their door and window openings, painted
dados, floors, ceilings, the veranda's pillars and beams, the roof with its parapet, the yard and compound wall,
door frames, door leaves, windows with iron grills, the planked main door and its padlock.

Output: {chunk name: Geo} for static geometry (one chunk per room / area so each gets its own baked lightmap),
plus dynamic pieces (door leaves, planks, padlock) with their pivots.
"""
import math

import numpy as np

from geo import Geo, rot_z

DADO_H = 1.2
PLINTH_H = 0.45


def inside(rect, x, y, m=0.0):
    return rect[0] - m <= x <= rect[2] + m and rect[1] - m <= y <= rect[3] + m


def space_at(L, x, y):
    """Which space a point is in: a room name, 'veranda', 'court' or 'outside'."""
    for r in L["rooms"]:
        if inside(r["rect"], x, y):
            return r["name"]
    if inside(L["court"], x, y):
        return "court"
    if inside(L["veranda"], x, y):
        return "veranda"
    if inside(L["building"], x, y):
        return "veranda"
    return "outside"


def room_by_name(L, name):
    for r in L["rooms"]:
        if r["name"] == name:
            return r
    return None


def face_mats(L, space, z0, z1):
    """Material of a wall face that looks into `space`, for the band z0..z1."""
    zc = (z0 + z1) / 2
    if space == "outside":
        return "plinth" if zc < PLINTH_H else "plaster_ext"
    if space in ("veranda", "court"):
        return "dado_red" if zc < DADO_H else "plaster"
    r = room_by_name(L, space)
    dado = r["dado"] if r else "dado_green"
    if dado == "dado_tiles":
        return "dado_tiles" if zc < 1.8 else "plaster"
    return dado if zc < DADO_H else "plaster"


def chunk_of(L, space):
    return space if space not in ("court",) else "veranda"


COLL = []          # blocking boxes in Blender axes: (x0, x1, y0, y1, z0, z1)


def wall_box(chunks, L, x0, x1, y0, y1, z0, z1, skip_top=True):
    """An axis box of wall; each face goes to the chunk of the space it faces, with the right paint."""
    COLL.append((x0, x1, y0, y1, z0, z1))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    faces = [
        ((-1, 0), [(x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)]),
        ((1, 0), [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)]),
        ((0, -1), [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)]),
        ((0, 1), [(x0, y1, z0), (x0, y1, z1), (x1, y1, z1), (x1, y1, z0)]),
    ]
    for (nx, ny), quad in faces:
        if (nx != 0 and x1 - x0 < 1e-4) or (ny != 0 and y1 - y0 < 1e-4):
            continue
        px = (x1 if nx > 0 else x0 if nx < 0 else cx) + nx * 0.3
        py = (y1 if ny > 0 else y0 if ny < 0 else cy) + ny * 0.3
        sp = space_at(L, px, py)
        # split the face at the dado line / plinth so each band gets its own paint
        cuts = [z0, z1]
        for zc in (PLINTH_H, DADO_H, 1.8):
            if z0 < zc < z1:
                cuts.append(zc)
        cuts = sorted(cuts)
        g = chunks.setdefault(chunk_of(L, sp), Geo(chunk_of(L, sp)))
        for a, b in zip(cuts[:-1], cuts[1:]):
            q = [(p[0], p[1], a if p[2] == z0 else b) for p in quad]
            g.quad(*q, face_mats(L, sp, a, b))
    if not skip_top:
        g = chunks.setdefault("roof", Geo("roof"))
        g.quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1), "plaster_ext")


def build(L):
    del COLL[:]
    T = L["wall_t"]
    H = L["ceil_h"]
    chunks = {}
    dyn = {}
    h_lines = [(w["p"], w["a"], w["b"]) for w in L["walls"] if w["o"] == "h"]

    def touches_h(x, y):
        return any(abs(p - y) < 1e-6 and a - 1e-6 <= x <= b + 1e-6 for (p, a, b) in h_lines)

    # ------------------------------------------------------------------ walls
    for w in L["walls"]:
        o, p, a, b = w["o"], w["p"], w["a"], w["b"]
        if o == "h":
            a2, b2 = a - T / 2, b + T / 2
        else:
            a2 = a + T / 2 if touches_h(p, a) else a
            b2 = b - T / 2 if touches_h(p, b) else b
        ops = sorted(w["openings"], key=lambda op: op["c"])
        cur = a2
        pieces = []
        for op in ops:
            o0, o1 = op["c"] - op["w"] / 2, op["c"] + op["w"] / 2
            if o0 > cur:
                pieces.append((cur, o0, 0.0, H))
            if op["z1"] < H:
                pieces.append((o0, o1, op["z1"], H))          # lintel
            if op["z0"] > 0:
                pieces.append((o0, o1, 0.0, op["z0"]))        # sill
            cur = o1
        if cur < b2:
            pieces.append((cur, b2, 0.0, H))
        for (s0, s1, z0, z1) in pieces:
            if o == "h":
                wall_box(chunks, L, s0, s1, p - T / 2, p + T / 2, z0, z1)
            else:
                wall_box(chunks, L, p - T / 2, p + T / 2, s0, s1, z0, z1)
    # ------------------------------------------------------------------ floors and ceilings
    for r in L["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        g = chunks.setdefault(r["name"], Geo(r["name"]))
        g.quad((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), r["floor"])
        g.quad((x0, y0, H), (x0, y1, H), (x1, y1, H), (x1, y0, H), "ceiling")
        # dark skirting line and a dusty floor edge are in the dado paint; door thresholds:
    vx0, vy0, vx1, vy1 = L["veranda"]
    cx0, cy0, cx1, cy1 = L["court"]
    g = chunks.setdefault("veranda", Geo("veranda"))
    strips = [(vx0, vy0, vx1, cy0), (vx0, cy1, vx1, vy1), (vx0, cy0, cx0, cy1), (cx1, cy0, vx1, cy1)]
    for (x0, y0, x1, y1) in strips:
        g.quad((x0, y0, 0), (x1, y0, 0), (x1, y1, 0), (x0, y1, 0), "floor_veranda")
        g.quad((x0, y0, H), (x0, y1, H), (x1, y1, H), (x1, y0, H), "ceiling")
    g.quad((cx0, cy0, 0.0), (cx1, cy0, 0.0), (cx1, cy1, 0.0), (cx0, cy1, 0.0), "ground_court")
    # courtyard curb
    for (x0, y0, x1, y1) in ((cx0, cy0 - 0.12, cx1, cy0), (cx0, cy1, cx1, cy1 + 0.12), (cx0 - 0.12, cy0, cx0, cy1), (cx1, cy0, cx1 + 0.12, cy1)):
        g.box(((x0 + x1) / 2, (y0 + y1) / 2, 0.04), (x1 - x0, y1 - y0, 0.08), "concrete")
    # ------------------------------------------------------------------ veranda pillars and the beam round the courtyard
    for (px, py) in L["pillars"]:
        COLL.append((px - 0.25, px + 0.25, py - 0.25, py + 0.25, 0.0, H))
        g.box((px, py, 0.15), (0.5, 0.5, 0.3), "plinth")
        g.box((px, py, (H - 0.35) / 2 + 0.15), (0.36, 0.36, H - 0.35 - 0.3), "plaster")
        g.box((px, py, H - 0.41), (0.46, 0.46, 0.12), "plaster")
    for (x0, y0, x1, y1) in ((cx0, cy0, cx1, cy0), (cx0, cy1, cx1, cy1), (cx0, cy0, cx0, cy1), (cx1, cy0, cx1, cy1)):
        if y0 == y1:
            g.box(((x0 + x1) / 2, y0, H - 0.175 + 0.1), (x1 - x0 + 0.36, 0.34, 0.55), "plaster")
        else:
            g.box((x0, (y0 + y1) / 2, H - 0.175 + 0.1), (0.34, y1 - y0, 0.55), "plaster")
    # ------------------------------------------------------------------ roof slab and parapets
    bx0, by0, bx1, by1 = L["building"]
    rf = chunks.setdefault("roof", Geo("roof"))
    S = H + 0.2
    m = T / 2
    for (x0, y0, x1, y1) in ((bx0 - m, by0 - m, bx1 + m, cy0), (bx0 - m, cy1, bx1 + m, by1 + m), (bx0 - m, cy0, cx0, cy1), (cx1, cy0, bx1 + m, cy1)):
        rf.quad((x0, y0, S), (x1, y0, S), (x1, y1, S), (x0, y1, S), "roof")
    # slab edges: outer perimeter and round the courtyard opening (the eave)
    for (a, b) in (((bx0 - m, by0 - m), (bx1 + m, by0 - m)), ((bx1 + m, by0 - m), (bx1 + m, by1 + m)),
                   ((bx1 + m, by1 + m), (bx0 - m, by1 + m)), ((bx0 - m, by1 + m), (bx0 - m, by0 - m))):
        rf.quad((a[0], a[1], H), (b[0], b[1], H), (b[0], b[1], S), (a[0], a[1], S), "plaster_ext")
    for (a, b) in (((cx0, cy0), (cx0, cy1)), ((cx0, cy1), (cx1, cy1)), ((cx1, cy1), (cx1, cy0)), ((cx1, cy0), (cx0, cy0))):
        rf.quad((a[0], a[1], H), (b[0], b[1], H), (b[0], b[1], S), (a[0], a[1], S), "plaster_ext")
    for (x0, y0, x1, y1) in ((bx0 - m, by0 - m, bx1 + m, by0 - m + 0.15), (bx0 - m, by1 + m - 0.15, bx1 + m, by1 + m),
                             (bx0 - m, by0 - m, bx0 - m + 0.15, by1 + m), (bx1 + m - 0.15, by0 - m, bx1 + m, by1 + m),
                             (cx0, cy0, cx1, cy0 + 0.15), (cx0, cy1 - 0.15, cx1, cy1), (cx0, cy0, cx0 + 0.15, cy1), (cx1 - 0.15, cy0, cx1, cy1)):
        rf.box(((x0 + x1) / 2, (y0 + y1) / 2, S + 0.35), (x1 - x0, y1 - y0, 0.7), "plaster_ext")
    # ------------------------------------------------------------------ the yard outside, compound wall
    yd = chunks.setdefault("yard", Geo("yard"))
    yx0, yy0, yx1, yy1 = L["yard"]
    yd.quad((-40, -40, -0.02), (40, -40, -0.02), (40, 40, -0.02), (-40, 40, -0.02), "ground_dirt")
    yd.quad((yx0, yy0, 0.0), (yx1, yy0, 0.0), (yx1, by0, 0.0), (yx0, by0, 0.0), "ground_dirt")
    # a path of old bricks from the gate to the main door
    yd.quad((-1.2, yy0, 0.012), (1.2, yy0, 0.012), (1.2, by0, 0.012), (-1.2, by0, 0.012), "brick_path")
    runs = [((yx0, yy0), (-2.25, yy0)), ((2.25, yy0), (yx1, yy0)), ((yx0, yy0), (yx0, by0)), ((yx1, yy0), (yx1, by0)),
            ((yx0, by0), (bx0, by0)), ((bx1, by0), (yx1, by0))]
    for (a, b) in runs:
        L_ = math.hypot(b[0] - a[0], b[1] - a[1])
        c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
        horiz = abs(b[1] - a[1]) < 1e-6
        size = (L_ + 0.23, 0.23, 1.9) if horiz else (0.23, L_ + 0.23, 1.9)
        yd.box((c[0], c[1], 0.95), size, "plaster_ext")
        COLL.append((c[0] - size[0] / 2, c[0] + size[0] / 2, c[1] - size[1] / 2, c[1] + size[1] / 2, 0.0, 2.0))
        yd.box((c[0], c[1], 1.93), (size[0] + 0.06 if horiz else 0.3, size[1] + 0.06 if not horiz else 0.3, 0.06), "concrete")
        n = int(L_ / 3.0)
        for k in range(n + 1):
            t = k / max(1, n)
            yd.box((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, 1.0), (0.38, 0.38, 2.0), "plaster_ext")
    # ------------------------------------------------------------------ door frames, leaves, the main door
    for d in L["doors"]:
        x, y, o, wdt, hgt = d["x"], d["y"], d["o"], d["w"], d["h"]
        sp_a = space_at(L, x + (0.3 if o == "v" else 0), y + (0.3 if o == "h" else 0))
        g = chunks.setdefault(chunk_of(L, d["room"]), Geo(d["room"]))
        R = np.eye(3) if o == "h" else rot_z(90)
        fr = Geo()
        if d["kind"] != "arch":
            fr.box((-wdt / 2 - 0.04, 0, hgt / 2), (0.08, T + 0.02, hgt), "wood_dark")
            fr.box((wdt / 2 + 0.04, 0, hgt / 2), (0.08, T + 0.02, hgt), "wood_dark")
            fr.box((0, 0, hgt + 0.04), (wdt + 0.16, T + 0.02, 0.08), "wood_dark")
        else:
            fr.box((0, 0, hgt + 0.06), (wdt + 0.3, T + 0.06, 0.12), "plaster")
        g.merge(fr, R=R, T=(x, y, 0))
        if d["kind"] == "arch":
            continue
        ix, iy = d["into"]
        leaves = 2 if d["kind"] in ("main", "door2") else 1
        lw = wdt / leaves
        for k in range(leaves):
            leaf = Geo(d["name"] + ("_%d" % k if leaves > 1 else ""))
            sgn = 1 if k == 0 else -1              # leaf 0 hinges at the left jamb (-u), leaf 1 at the right (+u)
            cxl = sgn * lw / 2
            paint = "wood_painted_blue" if d["kind"] != "main" else "wood_door_main"
            leaf.box((cxl, 0, (hgt - 0.02) / 2), (lw - 0.01, 0.045, hgt - 0.02), paint)
            # raised panels both sides
            for zc, ph in ((hgt * 0.27, hgt * 0.38), (hgt * 0.72, hgt * 0.38)):
                for s in (-1, 1):
                    leaf.box((cxl, s * 0.026, zc), (lw - 0.16, 0.012, ph), paint)
            hx = sgn * (lw - 0.09)
            for s in (-1, 1):
                leaf.box((hx, s * 0.04, 1.0), (0.025, 0.03, 0.14), "steel")       # handle / kunda
            pivot_u = -sgn * 0.0 + (-wdt / 2 if k == 0 else wdt / 2)
            # pivot in world coordinates and the leaf in pivot space (u along the wall)
            if o == "h":
                piv = (x + pivot_u, y, 0.0)
                Rl = np.eye(3)
            else:
                piv = (x, y + pivot_u, 0.0)
                Rl = rot_z(90)
            leaf.transform(R=Rl)
            dyn[leaf.name] = {"geo": leaf, "pivot": piv, "door": d["name"], "leaf": k, "into": d["into"], "o": o}
        if d["kind"] == "main":
            # three planks nailed across both leaves, and the padlock on its hasp
            for k, zc in enumerate((0.75, 1.35, 1.95)):
                pl = Geo("plank_%d" % k)
                ang = (-7, 5, -4)[k]
                pl.box((0, 0, 0), (wdt + 0.55, 0.035, 0.17), "wood_plank", R=np.array([[math.cos(math.radians(ang)), 0, -math.sin(math.radians(ang))], [0, 1, 0], [math.sin(math.radians(ang)), 0, math.cos(math.radians(ang))]]))
                for sx in (-1, 1):
                    for sz in (-1, 1):
                        pl.cyl((sx * (wdt / 2 + 0.18), -0.018, sz * 0.045), (sx * (wdt / 2 + 0.18), -0.03, sz * 0.045), 0.008, "rust", seg=6)
                dyn[pl.name] = {"geo": pl, "pivot": (x, y - 0.06 * -iy, zc), "plank": k}
            lock = Geo("padlock")
            lock.box((0, 0, 0), (0.075, 0.03, 0.065), "brass")
            lock.cyl((-0.025, 0, 0.03), (-0.025, 0, 0.075), 0.007, "steel", seg=8)
            lock.cyl((0.025, 0, 0.03), (0.025, 0, 0.075), 0.007, "steel", seg=8)
            lock.cyl((-0.025, 0, 0.075), (0.025, 0, 0.075), 0.007, "steel", seg=8)
            lock.box((0, -0.016, 0.005), (0.012, 0.004, 0.02), "metal_black")
            dyn["padlock"] = {"geo": lock, "pivot": (x, y - 0.075 * -iy, 1.12), "lock": True}
            hasp = Geo("hasp")
            hasp.box((-0.07, 0, 0.1), (0.16, 0.012, 0.04), "rust")
            hasp.box((0.07, 0, 0.1), (0.16, 0.012, 0.04), "rust")
            dyn["hasp"] = {"geo": hasp, "pivot": (x, y - 0.035 * -iy, 1.0), "lock": True}
    # ------------------------------------------------------------------ windows: frames, iron bars, broken panes, shutters
    for wi, wn in enumerate(L["windows"]):
        x, y, o, wdt = wn["x"], wn["y"], wn["o"], wn["w"]
        z0, z1 = 0.9, 0.9 + 1.45
        g = chunks.setdefault(chunk_of(L, wn["room"]), Geo(wn["room"]))
        R = np.eye(3) if o == "h" else rot_z(90)
        f = Geo()
        for (c, s) in (((-wdt / 2 + 0.04, 0, (z0 + z1) / 2), (0.08, 0.12, z1 - z0)), ((wdt / 2 - 0.04, 0, (z0 + z1) / 2), (0.08, 0.12, z1 - z0)),
                       ((0, 0, z1 - 0.04), (wdt, 0.12, 0.08)), ((0, 0, z0 + 0.04), (wdt, 0.12, 0.08)), ((0, 0, (z0 + z1) / 2), (0.06, 0.1, z1 - z0))):
            f.box(c, s, "wood_painted_green")
        n = max(4, int(wdt / 0.12))
        for k in range(n):
            u = -wdt / 2 + 0.09 + k * (wdt - 0.18) / (n - 1)
            f.cyl((u, 0.0, z0 + 0.08), (u, 0.0, z1 - 0.08), 0.008, "rust", seg=6, caps=False)
        f.box((0, 0, z0 + 0.5), (wdt - 0.12, 0.016, 0.02), "rust")
        f.box((0, 0, z1 - 0.5), (wdt - 0.12, 0.016, 0.02), "rust")
        # glass: some panes broken out
        rng = np.random.default_rng(wi)
        for side in (-1, 1):
            if rng.random() < 0.55:
                f.box((side * wdt / 4, 0.03, (z0 + z1) / 2), (wdt / 2 - 0.1, 0.004, z1 - z0 - 0.16), "glass_dirty")
        g.merge(f, R=R, T=(x, y, 0))
    return chunks, dyn
