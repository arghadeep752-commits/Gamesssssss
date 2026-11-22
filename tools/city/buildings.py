"""Ordinary buildings of Agartala: shop-houses with shutters and sign boards on the busy roads, painted concrete homes
with balconies, chajja sun shades, parapets and black water tanks, tin-roofed houses on the outskirts."""
import math
import random

import numpy as np

import layout as LY
from mesh import L, rot, v3
from roads import offset_line, resample

PALETTE = [  # paint colours seen on Agartala houses (linear-ish multipliers over a white plaster photo)
    (1.00, 0.97, 0.88), (0.98, 0.92, 0.75), (1.0, 0.88, 0.72), (0.95, 0.80, 0.70), (0.86, 0.92, 0.80), (0.80, 0.88, 0.92),
    (0.98, 0.85, 0.85), (0.92, 0.92, 0.92), (1.0, 0.95, 0.65), (0.85, 0.95, 0.95), (0.95, 0.75, 0.55), (0.80, 0.85, 0.70),
    (0.75, 0.82, 0.95), (1.0, 1.0, 1.0), (0.93, 0.86, 0.93),
]
AWNING = [(0.85, 0.15, 0.12), (0.12, 0.35, 0.75), (0.15, 0.55, 0.25), (0.9, 0.6, 0.1), (0.5, 0.2, 0.6)]
SIGN_ROWS = 16          # the "signs" layer: 16 boards, one per row (rows 0-11 are shop names)


class Building:
    def __init__(self, cx, cz, w, d, yaw, floors, style, seed, base_y):
        self.cx, self.cz, self.w, self.d, self.yaw = cx, cz, w, d, yaw
        self.floors, self.style, self.seed, self.y = floors, style, seed, base_y
        self.height = 0.0


def fh(i, style):
    return 3.5 if (i == 0 and style == "shop") else 3.05


def build_one(M, b, colliders, rnd):
    """Write one building into the chunk meshes."""
    mesh = M.get(b.cx, b.cz, "world")
    yaw = b.yaw
    hx, hz = b.w / 2, b.d / 2
    cosy, siny = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))

    def W(x, z):                       # local (x right along the front, z backwards from the front) -> world
        return (b.cx + x * cosy + z * siny, b.cz - x * siny + z * cosy)

    def W3(x, y, z):
        p = W(x, z)
        return v3(p[0], y, p[1])
    tint = PALETTE[rnd.randrange(len(PALETTE))]
    weather = rnd.random()
    wall = L["plaster"] if weather < 0.55 else L["plaster_old"]
    if b.style == "modern":
        wall = L["facade2"] if rnd.random() < 0.6 else L["concrete"]
        tint = (1, 1, 1)
    elif b.style == "brick":
        wall = L["facade1"] if rnd.random() < 0.5 else L["brick"]
        tint = (1, 1, 1)
    y0 = b.y
    # plinth down into the ground
    mesh.box(b.cx, y0 - 0.8, b.cz, b.w + 0.2, 0.8 + 0.25, b.d + 0.2, L["concrete"], yaw=yaw, tile=(2.0, 1.0), col=(0.75, 0.75, 0.72), faces="nsew")
    y = y0 + 0.25
    floors = b.floors
    tin = b.style == "tin"
    # the front is the local -z side (it faces the road); corners counter-clockwise seen from above
    front = [(-hx, -hz), (hx, -hz)]
    corners = [(-hx, -hz), (hx, -hz), (hx, hz), (-hx, hz)]
    total = y
    for f in range(floors):
        h = fh(f, b.style)
        total += h
    top = total
    # walls of the whole height (tiled per floor in v so windows line up)
    for i in range(4):
        p0, p1 = W(*corners[i]), W(*corners[(i + 1) % 4])
        mesh.wall(p0, p1, y, top, wall, tile=(3.0, 3.05) if wall in (L["facade1"], L["facade2"]) else (2.6, 2.6), col=tint, ao_bottom=0.72)
    bay = 3.4 if b.style != "tin" else 3.0
    nb = max(1, int(b.w / bay))
    bw = b.w / nb
    if wall in (L["facade1"], L["facade2"]):
        nb = 0                          # the photo already has windows
    # ---------------------------------------------------------------- front details per floor
    yy = y
    sign_used = False
    for f in range(floors):
        h = fh(f, b.style)
        for k in range(nb):
            x0 = -hx + k * bw
            xc = x0 + bw / 2
            if f == 0 and b.style == "shop":
                # rolling shutter (left half of the layer) or an open shop (right half)
                open_shop = rnd.random() < 0.55
                u0 = 0.5 if open_shop else 0.0
                p = [W3(x0 + 0.25, yy + 0.05, -hz - 0.04), W3(x0 + bw - 0.25, yy + 0.05, -hz - 0.04),
                     W3(x0 + bw - 0.25, yy + 2.6, -hz - 0.04), W3(x0 + 0.25, yy + 2.6, -hz - 0.04)]
                mesh.panel(p[0], p[1], p[2], p[3], L["shopfront"], uvs=[(u0, 0), (u0 + 0.5, 0), (u0 + 0.5, 1), (u0, 1)], ao=(0.8, 0.8, 1, 1),
                           emis=0.35 if open_shop else 0.0)
                # sign board
                si = rnd.randrange(12)
                v0, v1 = 1.0 - (si + 1) / SIGN_ROWS, 1.0 - si / SIGN_ROWS
                q = [W3(x0 + 0.1, yy + 2.75, -hz - 0.12), W3(x0 + bw - 0.1, yy + 2.75, -hz - 0.12),
                     W3(x0 + bw - 0.1, yy + 3.35, -hz - 0.12), W3(x0 + 0.1, yy + 3.35, -hz - 0.12)]
                mesh.panel(q[0], q[1], q[2], q[3], L["signs"], uvs=[(0.0, v0), (1.0, v0), (1.0, v1), (0.0, v1)], emis=0.5)
                sign_used = True
                # awning
                if rnd.random() < 0.5:
                    ac = AWNING[rnd.randrange(len(AWNING))]
                    a = [W3(x0 + 0.15, yy + 2.65, -hz), W3(x0 + bw - 0.15, yy + 2.65, -hz), W3(x0 + bw - 0.15, yy + 2.35, -hz - 1.1),
                         W3(x0 + 0.15, yy + 2.35, -hz - 1.1)]
                    mesh.quad(a[0], a[3], a[2], a[1], L["fabric"], tile=(1.0, 1.0), col=ac)
                    mesh.quad(a[0], a[1], a[2], a[3], L["fabric"], tile=(1.0, 1.0), col=tuple(c * 0.6 for c in ac))
            else:
                # window with an iron grill and a chajja sun shade above it
                if tin and k % 2 == 1:
                    continue
                wwid = min(1.5, bw - 0.9)
                wy0, wy1 = yy + 0.9, yy + 0.9 + 1.35
                p = [W3(xc - wwid / 2, wy0, -hz - 0.03), W3(xc + wwid / 2, wy0, -hz - 0.03), W3(xc + wwid / 2, wy1, -hz - 0.03), W3(xc - wwid / 2, wy1, -hz - 0.03)]
                variant = rnd.randrange(4) / 4.0
                lit = 0.6 if rnd.random() < 0.3 else 0.0
                mesh.panel(p[0], p[1], p[2], p[3], L["window"], uvs=[(variant, 0), (variant + 0.25, 0), (variant + 0.25, 1), (variant, 1)], emis=lit)
                if not tin:
                    # chajja: a thin concrete shade (its top and its front edge)
                    a0, a1 = W3(xc - wwid / 2 - 0.25, wy1 + 0.2, -hz), W3(xc + wwid / 2 + 0.25, wy1 + 0.2, -hz)
                    b1, b0 = W3(xc + wwid / 2 + 0.25, wy1 + 0.2, -hz - 0.6), W3(xc - wwid / 2 - 0.25, wy1 + 0.2, -hz - 0.6)
                    mesh.panel(b0, b1, a1, a0, L["concrete"], col=tint, tile=(2, 2))
                    mesh.panel(b0 - v3(0, 0.09, 0), b1 - v3(0, 0.09, 0), b1, b0, L["concrete"], col=tuple(c * 0.85 for c in tint), tile=(2, 2))
        # balcony on some upper floors
        if f >= 1 and not tin and nb >= 2 and rnd.random() < 0.35:
            bx0, bx1 = -hx + 0.4, hx - 0.4
            cx_, cz_ = W(0, -hz - 0.55)
            mesh.box(cx_, yy - 0.15, cz_, bx1 - bx0, 0.15, 1.1, L["concrete"], yaw=yaw, tile=(2, 2), col=tint)
            # railing: a low wall or steel bars
            cx2, cz2 = W(0, -hz - 1.07)
            if rnd.random() < 0.7:
                mesh.box(cx2, yy, cz2, bx1 - bx0, 0.95, 0.06, L["plaster"], yaw=yaw, tile=(2.6, 2.6), col=tint, faces="nsewt")
            else:
                mesh.box(cx2, yy + 0.9, cz2, bx1 - bx0, 0.06, 0.06, L["metal"], yaw=yaw, col=(0.25, 0.25, 0.28), faces="nst")
                for xr in (bx0, 0.0, bx1):
                    px, pz = W(xr, -hz - 1.07)
                    mesh.box(px, yy, pz, 0.05, 0.9, 0.05, L["metal"], yaw=yaw, col=(0.25, 0.25, 0.28), faces="ns")
        yy += h
        # floor line band
        if f < floors - 1 and not tin:
            cx_, cz_ = W(0, 0)
            mesh.box(cx_, yy - 0.12, cz_, b.w + 0.12, 0.18, b.d + 0.12, L["concrete"], yaw=yaw, tile=(2, 2), col=tuple(c * 0.92 for c in tint), faces="nsew")
    # side windows (cheap: every other bay, upper floors only)
    if nb and not tin and b.d > 8:
        for side in (-1, 1):
            nsb = max(1, int(b.d / 4.5))
            for f in range(1, floors):
                yb = y + sum(fh(i, b.style) for i in range(f))
                for k in range(0, nsb, 2):
                    zc = -hz + (k + 0.5) * b.d / nsb
                    xw = side * (hx + 0.03)
                    p = [W3(xw, yb + 0.9, zc - 0.6 * side), W3(xw, yb + 0.9, zc + 0.6 * side), W3(xw, yb + 2.2, zc + 0.6 * side), W3(xw, yb + 2.2, zc - 0.6 * side)]
                    variant = rnd.randrange(4) / 4.0
                    mesh.panel(p[0], p[1], p[2], p[3], L["window"], uvs=[(variant, 0), (variant + 0.25, 0), (variant + 0.25, 1), (variant, 1)])
    # ---------------------------------------------------------------- roof
    if tin:
        # gable roof of corrugated tin over the whole house
        ov = 0.45
        ridge = top + 1.3
        a = W3(-hx - ov, top - 0.1, -hz - ov)
        bb = W3(hx + ov, top - 0.1, -hz - ov)
        c = W3(hx + ov, ridge, 0)
        d = W3(-hx - ov, ridge, 0)
        e = W3(hx + ov, top - 0.1, hz + ov)
        f_ = W3(-hx - ov, top - 0.1, hz + ov)
        rc = (0.85, 0.82, 0.8) if rnd.random() < 0.6 else (0.75, 0.45, 0.35)
        mesh.quad(a, d, c, bb, L["roof_tin"], tile=(1.2, 2.0), col=rc)      # front slope (faces up and forward)
        mesh.quad(e, c, d, f_, L["roof_tin"], tile=(1.2, 2.0), col=rc)      # back slope
        mesh.quad(a, bb, c, d, L["roof_tin"], tile=(1.2, 2.0), col=tuple(x * 0.5 for x in rc))   # underside (eaves)
        mesh.quad(e, f_, d, c, L["roof_tin"], tile=(1.2, 2.0), col=tuple(x * 0.5 for x in rc))
        # gable triangles
        for s in (-1, 1):
            out = W3(s * (hx + 1), top, 0) - W3(0, top, 0)
            mesh.tri(W3(s * hx, top, -hz), W3(s * hx, top, hz), W3(s * hx, ridge - 0.25, 0), wall,
                     uvs=((0, 0), (b.d / 2.6, 0), (b.d / 5.2, 0.5)), col=tint, outward=out)
        b.height = ridge - y0
    else:
        # flat roof: slab, parapet, water tank, sometimes a stair room
        cx_, cz_ = W(0, 0)
        mesh.box(cx_, top, cz_, b.w, 0.05, b.d, L["concrete"], yaw=yaw, tile=(3, 3), col=(0.8, 0.8, 0.78), faces="t")
        ph = 0.85
        for i in range(4):
            p0, p1 = corners[i], corners[(i + 1) % 4]
            mx, mz = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
            length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            ia = i % 2 == 0
            sx, sz = (length + 0.15, 0.15) if ia else (0.15, length + 0.15)
            wx, wz = W(mx, mz)
            mesh.box(wx, top, wz, sx, ph, sz, wall, yaw=yaw, tile=(2.6, 2.6), col=tint, ao_bottom=0.85)
        if rnd.random() < 0.85:
            tx, tz = W(rnd.uniform(-hx + 1.2, hx - 1.2), rnd.uniform(-hz + 1.5, hz - 1.2))
            mesh.box(tx, top, tz, 1.4, 0.6, 1.4, L["concrete"], tile=(2, 2), col=(0.7, 0.7, 0.7), faces="nsew")
            mesh.cylinder(tx, top + 0.6, tz, 0.65, 1.25, L["metal"], seg=8, col=(0.08, 0.08, 0.09), tile=(1, 1))
        if floors >= 2 and rnd.random() < 0.5 and b.w > 7 and b.d > 8:
            sx_, sz_ = W(hx - 1.8, hz - 2.0)
            mesh.box(sx_, top, sz_, 2.6, 2.6, 3.0, wall, yaw=yaw, tile=(2.6, 2.6), col=tint)
        b.height = top + ph - y0
    colliders.append([b.cx, y0 - 0.5, b.cz, b.w, b.height + 0.5, b.d, yaw])


def roof_y(b):
    return b.y + 0.25 + sum(fh(i, b.style) for i in range(b.floors))


def place_lots(roads, grid, M, colliders, seed=7, objects=None):
    """Line every road with buildings, as tightly as the place calls for. 'objects' collects the spots for the
    Hyper3D shop-houses and street props (placed by the game)."""
    rnd = random.Random(seed)
    out = []
    objects = objects if objects is not None else []
    for c in roads.chains:
        if not c.get("trimmed") or c.get("surface") is None:
            continue
        rp, ys = c["surface"]
        cls = c["cls"]
        w, ww = LY.ROAD_W[cls], LY.WALK_W[cls]
        dense = resample(rp, 1.0)
        n = len(dense)
        if n < 6:
            continue
        for side in (1, -1):
            i = 2
            while i < n - 3:
                p = np.asarray(dense[i], float)
                q = np.asarray(dense[min(n - 1, i + 1)], float)
                dvec = q - p
                dl = float(np.linalg.norm(dvec))
                if dl < 1e-6:
                    i += 1
                    continue
                dvec /= dl
                left = np.array([-dvec[1], dvec[0]])
                kind = LY.district(p[0], p[1])
                if kind in ("none", "beach", "park"):
                    i += 8
                    continue
                if kind == "core":
                    lw, gap, setback, depth = rnd.uniform(6.0, 11.0), rnd.choice([0.0, 0.0, 0.3, 1.0]), 0.4, rnd.uniform(10, 16)
                    floors = rnd.choice([2, 3, 3, 4, 4, 5]) if cls == "A" else rnd.choice([1, 2, 2, 3, 3, 4])
                    style = "shop" if cls in ("A", "B") or rnd.random() < 0.4 else "house"
                    if cls == "A" and rnd.random() < 0.07:
                        style, floors, lw = "modern", rnd.choice([4, 5, 6]), rnd.uniform(14, 20)
                elif kind == "town":
                    lw, gap, setback, depth = rnd.uniform(7.0, 12.0), rnd.uniform(1.5, 5.0), rnd.uniform(1.5, 4.0), rnd.uniform(9, 14)
                    floors = rnd.choice([1, 2, 2, 2, 3])
                    style = rnd.choice(["house", "house", "house", "tin", "shop" if cls != "C" else "house", "brick"])
                    if style == "tin":
                        floors = 1
                else:
                    if rnd.random() < 0.45:
                        i += int(rnd.uniform(10, 30))
                        continue
                    lw, gap, setback, depth = rnd.uniform(6.5, 10.0), rnd.uniform(5.0, 14.0), rnd.uniform(3.0, 7.0), rnd.uniform(7, 11)
                    floors = 1 if rnd.random() < 0.7 else 2
                    style = "tin" if floors == 1 else "house"
                cart = kind == "core" and style == "shop" and cls != "A" and rnd.random() < 0.10
                stop = kind == "core" and cls == "A" and rnd.random() < 0.04
                if cart or stop:
                    setback = 2.6
                front_off = w / 2 + ww + setback
                # the lot: front edge centred lw/2 ahead
                fc = p + dvec * (lw / 2) + left * side * front_off
                ok = False
                for dd in (depth, depth * 0.75, 7.0):
                    ctr = fc + left * side * (dd / 2)
                    if grid.rect_free(ctr[0], ctr[1], lw, dd, dvec):
                        depth = dd
                        ok = True
                        break
                if not ok or depth < 6.5:
                    i += 3
                    continue
                ctr = fc + left * side * (depth / 2)
                # facing the road: the building's front (local -z) points towards the road
                face = -left * side
                yaw = math.degrees(math.atan2(face[0], face[1])) + 180.0      # local -z is the front
                base = grid.ground(ctr[0], ctr[1], lw, depth, dvec)
                front_yaw = math.degrees(math.atan2(face[0], face[1]))          # +z towards the road (the Hyper3D models)
                if cart or stop:
                    sp = fc - left * side * 1.3
                    objects.append({"m": "bus_stop" if stop else rnd.choice(["chai_stall", "food_cart", "fruit_cart", "chai_stall"]),
                                    "p": [round(float(sp[0]), 2), round(float(base), 2), round(float(sp[1]), 2)], "yaw": round(front_yaw, 1)})
                if kind == "core" and cls in ("A", "B") and style == "shop" and lw >= 7.5 and rnd.random() < 0.22:
                    # a spot for one of the Hyper3D Indian shop-houses (the game fills it)
                    objects.append({"slot": 1, "p": [round(float(ctr[0]), 2), round(float(base), 2), round(float(ctr[1]), 2)],
                                    "yaw": round(front_yaw, 1), "w": round(lw, 2), "d": round(depth, 2), "floors": floors})
                    grid.mark_rect(ctr[0], ctr[1], lw + 0.6, depth + 0.6, dvec, "building")
                    i += int(math.ceil(lw + gap))
                    continue
                bobj = Building(float(ctr[0]), float(ctr[1]), lw, depth, yaw, floors, style, rnd.random(), base)
                build_one(M, bobj, colliders, rnd)
                grid.mark_rect(ctr[0], ctr[1], lw + 0.6, depth + 0.6, dvec, "building")
                out.append(bobj)
                roof_tank(objects, bobj, rnd)
                i += int(math.ceil(lw + gap))
    out += fill_blocks(grid, M, colliders, rnd, objects)
    return out


def roof_tank(objects, b, rnd):
    """The black water tank on Indian roofs."""
    if b.style in ("tin", "modern") or rnd.random() > 0.16:
        return
    lx, lz = rnd.uniform(-b.w / 2 + 1.2, b.w / 2 - 1.2), rnd.uniform(-b.d / 2 + 1.2, b.d / 2 - 1.2)
    c, s = math.cos(math.radians(b.yaw)), math.sin(math.radians(b.yaw))
    objects.append({"m": "water_tank", "p": [round(b.cx + lx * c + lz * s, 2), round(roof_y(b) + 0.02, 2), round(b.cz - lx * s + lz * c, 2)],
                    "yaw": round(rnd.uniform(0, 360), 1)})


def fill_blocks(grid, M, colliders, rnd, objects):
    """Houses in the middle of the blocks too, like the crowded lanes of an Indian town (a few gaps stay open)."""
    out = []
    H = LY.HALF - 45
    step = 11.0
    z = -H
    while z < H:
        x = -H
        while x < H:
            px, pz = x + rnd.uniform(-2, 2), z + rnd.uniform(-2, 2)
            kind = LY.district(px, pz)
            if kind in ("core", "town") and rnd.random() < (0.55 if kind == "core" else 0.35):
                lw, dd = rnd.uniform(7.5, 10.5), rnd.uniform(7.5, 10.5)
                yaw = rnd.choice([0.0, 90.0, 180.0, 270.0])
                dvec = np.array([math.cos(math.radians(yaw)), -math.sin(math.radians(yaw))])
                if grid.rect_free(px, pz, lw + 1.4, dd + 1.4, dvec):
                    floors = rnd.choice([2, 2, 3, 3, 4]) if kind == "core" else rnd.choice([1, 2, 2, 3])
                    style = rnd.choice(["house", "house", "brick", "house", "tin" if kind == "town" else "house"])
                    if style == "tin":
                        floors = 1
                    base = grid.ground(px, pz, lw, dd, dvec)
                    b = Building(float(px), float(pz), lw, dd, yaw, floors, style, rnd.random(), base)
                    build_one(M, b, colliders, rnd)
                    grid.mark_rect(px, pz, lw + 0.6, dd + 0.6, dvec, "building")
                    out.append(b)
                    roof_tank(objects, b, rnd)
            x += step
        z += step
    return out
