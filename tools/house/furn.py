"""Furniture, kitchen modules, bathroom fittings, lamps, plants and garden items.
Every builder returns a Geo in a local frame: origin on the floor, front facing -y."""
import math
import numpy as np
from hlib import Geo, round_path, rotz, rotx, roty


def rb(g, mn, mx, mat, r=0.0, seg=1, skip=(), bulge=0.0, div=1):
    if r > 0:
        g.rbox(mn, mx, r, mat, seg, skip, bulge, div)
    else:
        g.box(mn, mx, mat, skip=skip)


def sub(g, other, R=None, pivot=(0, 0, 0), offset=(0, 0, 0)):
    """Adds `other` rotated by matrix R about pivot, then offset."""
    if R is not None:
        pv = np.asarray(pivot, float)
        other.transform(R, pv - R @ pv)
    g.add(other, 0.0, offset)
    return g


def bezier(p0, p1, p2, n=10):
    p0, p1, p2 = (np.asarray(p, float) for p in (p0, p1, p2))
    return [(1 - t) ** 2 * p0 + 2 * (1 - t) * t * p1 + t * t * p2 for t in np.linspace(0, 1, n)]


def ring_path(c, r, z, n=24):
    return [(c[0] + r * math.cos(2 * math.pi * i / n), c[1] + r * math.sin(2 * math.pi * i / n), z) for i in range(n + 1)]


# =====================================================================================  living

def sofa(M, length=2.9, depth=0.95, chaise=0.0, chaise_side=1, fabric="sofa"):
    g = Geo()
    f = M[fabric]
    hl, y0, y1, aw = length / 2, -depth / 2, depth / 2, 0.17
    legs = [(-hl + 0.08, y0 + 0.08), (hl - 0.08, y0 + 0.08), (-hl + 0.08, y1 - 0.08), (hl - 0.08, y1 - 0.08)]
    if chaise > 0:
        xc = hl - 0.08 if chaise_side > 0 else -hl + 0.08
        legs.append((xc, y0 - chaise + 0.08))
        legs.append((xc - chaise_side * 0.82, y0 - chaise + 0.08))
    for x, y in legs:
        g.cyl((x, y, 0), 0.016, 0.07, M["metal_black"], seg=10, bottom=False)
    rb(g, (-hl, y0, 0.07), (hl, y1, 0.3), f, 0.03, 2, skip=("nz",))
    g.box((-hl + 0.02, y0 + 0.02, 0.069), (hl - 0.02, y1 - 0.02, 0.07), M["metal_black"])
    for sx in (-1, 1):
        xa, xb = (-hl, -hl + aw) if sx < 0 else (hl - aw, hl)
        ya = y0 - (chaise if (chaise > 0 and sx == chaise_side) else 0.0)
        rb(g, (xa, ya, 0.07), (xb, y1, 0.63), f, 0.065, 2, bulge=0.01, div=2)
    rb(g, (-hl + aw - 0.02, y1 - 0.2, 0.28), (hl - aw + 0.02, y1, 0.74), f, 0.06, 2)
    n = 3 if length > 2.2 else (2 if length > 1.3 else 1)
    inner = length - 2 * aw
    for i in range(n):
        xa = -hl + aw + inner * i / n + 0.006
        xb = -hl + aw + inner * (i + 1) / n - 0.006
        rb(g, (xa, y0 + 0.02, 0.3), (xb, y1 - 0.18, 0.47), f, 0.07, 2, bulge=0.018, div=2)
        back = Geo()
        rb(back, (xa + 0.01, y1 - 0.4, 0.45), (xb - 0.01, y1 - 0.17, 0.92), f, 0.09, 2, bulge=0.035, div=2)
        sub(g, back, rotx(-9), (0, y1 - 0.2, 0.46))
    if chaise > 0:
        xa, xb = (hl - aw - 0.84, hl - aw) if chaise_side > 0 else (-hl + aw, -hl + aw + 0.84)
        rb(g, (xa, y0 - chaise, 0.07), (xb, y0 + 0.05, 0.3), f, 0.03, 2, skip=("nz",))
        rb(g, (xa + 0.006, y0 - chaise + 0.02, 0.3), (xb - 0.006, y0 + 0.01, 0.47), f, 0.07, 2, bulge=0.018, div=2)
        g.collide((xa, y0 - chaise, 0), (xb, y0, 0.6))
    # throw pillows
    for i, (x, col) in enumerate(((-hl + aw + 0.28, "pillow_a"), (hl - aw - 0.28, "pillow_b"), (-hl + aw + 0.62, "pillow_b"))):
        p = Geo()
        rb(p, (-0.22, -0.07, 0.0), (0.22, 0.07, 0.44), M[col], 0.07, 2, bulge=0.035, div=2)
        p.transform(rotx(-16) @ rotz(8 if i % 2 else -10))
        g.add(p, 0.0, (x, y1 - 0.36, 0.47))
    g.collide((-hl, y0, 0), (hl, y1, 0.78))
    return g


def armchair(M, fabric="sofa_alt"):
    g = sofa(M, length=0.95, depth=0.9, fabric=fabric)
    return g


def coffee_table(M, w=1.25, d=0.7, h=0.38):
    g = Geo()
    rb(g, (-w / 2, -d / 2, h - 0.03), (w / 2, d / 2, h), M["marble"], 0.014, 2)
    t = 0.025
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (w / 2 - 0.07), sy * (d / 2 - 0.07)
            rb(g, (x - t / 2, y - t / 2, 0), (x + t / 2, y + t / 2, h - 0.03), M["metal_black"], 0.004, skip=("nz",))
    rb(g, (-w / 2 + 0.06, -d / 2 + 0.06, 0.1), (w / 2 - 0.06, d / 2 - 0.06, 0.12), M["walnut"], 0.004)
    # books + bowl on top
    for i, (bw, bd, bh, m) in enumerate(((0.26, 0.2, 0.03, "book_a"), (0.24, 0.18, 0.025, "book_b"), (0.22, 0.17, 0.02, "book_c"))):
        z = h + sum(x[2] for x in ((0.26, 0.2, 0.03), (0.24, 0.18, 0.025), (0.22, 0.17, 0.02))[:i])
        rb(g, (-w / 2 + 0.12, -0.12, z), (-w / 2 + 0.12 + bw, -0.12 + bd, z + bh), M[m], 0.003)
    g.lathe((0.28, 0.02, h), [(0.0, 0.0), (0.06, 0.0), (0.13, 0.05), (0.14, 0.07), (0.13, 0.07), (0.05, 0.015), (0.0, 0.015)],
            M["ceramic_dark"], seg=24)
    g.collide((-w / 2, -d / 2, 0), (w / 2, d / 2, h))
    return g


def side_table(M, r=0.24, h=0.52):
    g = Geo()
    g.cyl((0, 0, h - 0.025), r, 0.025, M["walnut"], seg=28)
    g.cyl((0, 0, 0), 0.16, 0.02, M["metal_black"], seg=24)
    g.cyl((0, 0, 0.02), 0.022, h - 0.045, M["metal_black"], seg=12, top=False, bottom=False)
    g.collide((-r, -r, 0), (r, r, h))
    return g


def tv_console(M, L=2.2, d=0.42, z0=0.22, h=0.42):
    g = Geo()
    rb(g, (-L / 2, -d, z0), (L / 2, 0, z0 + h), M["walnut"], 0.006, 1)
    n = 4
    for i in range(n):
        xa = -L / 2 + 0.01 + (L - 0.02) * i / n + 0.002
        xb = -L / 2 + 0.01 + (L - 0.02) * (i + 1) / n - 0.002
        rb(g, (xa, -d - 0.018, z0 + 0.012), (xb, -d + 0.001, z0 + h - 0.012), M["walnut"], 0.003)
        g.box((xa + 0.03, -d - 0.0185, z0 + h - 0.05), (xb - 0.03, -d - 0.017, z0 + h - 0.045), M["groove"])
    g.box((-L / 2 + 0.05, -d + 0.05, z0 - 0.005), (L / 2 - 0.05, -0.02, z0), M["lamp_strip"])
    # decor on top: vase + books + speaker
    g.lathe((L / 2 - 0.25, -d / 2, z0 + h), [(0.0, 0.0), (0.06, 0.0), (0.08, 0.12), (0.05, 0.28), (0.035, 0.32), (0.03, 0.32)],
            M["ceramic_white"], seg=20)
    for i, m in enumerate(("book_b", "book_a", "book_c", "book_d")):
        x = -L / 2 + 0.2 + i * 0.035
        rb(g, (x, -d / 2 - 0.1, z0 + h), (x + 0.03, -d / 2 + 0.1, z0 + h + 0.22 + 0.02 * (i % 2)), M[m], 0.002)
    g.collide((-L / 2, -d, z0), (L / 2, 0, z0 + h))
    return g


def tv(M, w=1.45, h=0.83, z0=1.0):
    g = Geo()
    rb(g, (-w / 2, -0.035, z0), (w / 2, 0, z0 + h), M["tv_frame"], 0.006, 1)
    g.box((-w / 2 + 0.008, -0.0355, z0 + 0.008), (w / 2 - 0.008, -0.035, z0 + h - 0.008), M["screen"], skip=("py",))
    rb(g, (-0.5, -0.09, z0 - 0.12), (0.5, -0.01, z0 - 0.05), M["tv_frame"], 0.015, 2)   # soundbar
    return g


def fluted_panel(M, width, height, mat, pitch=0.045, depth=0.022):
    g = Geo()
    g.box((-width / 2, -0.012, 0), (width / 2, 0, height), mat, skip=("py",))
    n = int(width / pitch)
    x0 = -n * pitch / 2
    for i in range(n):
        xa = x0 + i * pitch + 0.004
        rb(g, (xa, -0.012 - depth, 0.0), (xa + pitch - 0.008, -0.011, height), mat, min(0.01, (pitch - 0.008) * 0.45), 1, skip=("py", "nz", "pz"))
    return g


def arc_lamp(M, reach=1.55, h=2.0):
    g = Geo()
    g.cyl((0, 0, 0), 0.17, 0.05, M["marble"], seg=28)
    path = [np.array((0, 0, 0.05)), np.array((0, 0, 1.1))] + bezier((0, 0, 1.1), (0, 0, h + 0.45), (0, -reach, h - 0.05), 14)[1:]
    g.tube(path, 0.011, M["brass"], seg=10)
    end = np.asarray(path[-1])
    g.lathe(end - np.array((0, 0, 0.26)), [(0.2, 0.0), (0.19, 0.06), (0.14, 0.16), (0.07, 0.24), (0.02, 0.26), (0.0, 0.26)],
            M["metal_black"], seg=28)
    g.lathe(end - np.array((0, 0, 0.26)), [(0.0, 0.25), (0.06, 0.235), (0.13, 0.15), (0.18, 0.06), (0.19, 0.002)],
            M["shade_inner"], seg=28)
    g.sphere(end - np.array((0, 0, 0.2)), 0.035, M["bulb"], seg=12, rings=6)
    g.light(end - np.array((0, 0, 0.22)), 22.0, color=(1.0, 0.82, 0.6), radius=0.04)
    g.collide((-0.17, -0.17, 0), (0.17, 0.17, 1.0))
    return g


def rug(M, w, d, mat="rug"):
    g = Geo()
    rb(g, (-w / 2, -d / 2, 0), (w / 2, d / 2, 0.012), M[mat], 0.004, 1, skip=("nz",))
    for face in g.F:
        p = face[0]
        face[3] = np.stack([(p[:, 0] + w / 2) / w, (p[:, 1] + d / 2) / d], 1)
    return g


def leaf_surface(L, Wd, droop=0.25, fold=0.18, broad=0.6):
    def fn(u, v):
        prof = math.sin(math.pi * min(max(u, 0.0), 1.0)) ** 0.75 * (broad + (1 - broad) * u)
        lat = (v - 0.5) * Wd * prof
        return (lat, u * L, -droop * L * u * u + abs(lat) * fold)
    return fn


def plant_fig(M, h=1.75, seed=3, pot_r=0.21):
    g = Geo()
    rng = np.random.default_rng(seed)
    g.lathe((0, 0, 0), [(pot_r * 0.8, 0.0), (pot_r, 0.03), (pot_r * 1.02, 0.38), (pot_r * 0.97, 0.4), (pot_r * 0.9, 0.4), (pot_r * 0.9, 0.36)],
            M["pot"], seg=28, bottom=True)
    g.cyl((0, 0, 0.33), pot_r * 0.9, 0.025, M["soil"], seg=24, bottom=False)
    trunk = [np.array(p) for p in ((0, 0, 0.34), (0.03, 0.01, 0.8), (-0.02, 0.03, 1.2), (0.02, -0.01, h - 0.15))]
    g.tube(trunk, 0.016, M["bark"], seg=8, caps=False)
    for i in range(38):
        t = 0.3 + 0.7 * (i / 38.0) + rng.random() * 0.03
        seg_f = t * (len(trunk) - 1)
        k = min(int(seg_f), len(trunk) - 2)
        base = trunk[k] + (trunk[k + 1] - trunk[k]) * (seg_f - k)
        size = 0.17 + 0.12 * rng.random() * (1.2 - t * 0.4)
        leaf = Geo()
        leaf.surface(leaf_surface(size * 1.25, size * 0.95, droop=0.2 + rng.random() * 0.2), 4, 2, M["leaf"], two_sided=True, thickness=0.003)
        R = rotz(rng.random() * 360) @ rotx(25 + rng.random() * 45)
        leaf.transform(R, base)
        g.add(leaf)
    g.collide((-pot_r, -pot_r, 0), (pot_r, pot_r, 0.45))
    return g


def plant_snake(M, h=0.9, seed=5, pot_r=0.15, pot="pot_dark"):
    g = Geo()
    rng = np.random.default_rng(seed)
    g.lathe((0, 0, 0), [(pot_r, 0.0), (pot_r, 0.32), (pot_r * 0.93, 0.32), (pot_r * 0.93, 0.29)], M[pot], seg=24, bottom=True)
    g.cyl((0, 0, 0.27), pot_r * 0.93, 0.02, M["soil"], seg=20, bottom=False)
    for i in range(13):
        ang = rng.random() * 360
        lean = 4 + rng.random() * 14
        hh = h * (0.55 + 0.45 * rng.random())
        wd = 0.05 + rng.random() * 0.025
        tw = rng.random() * 50 - 25

        def fn(u, v, hh=hh, wd=wd, tw=tw):
            w = wd * math.sin(math.pi * (0.08 + 0.92 * u)) ** 0.5 * (1.0 - 0.6 * u * u)
            a = math.radians(tw * u)
            lat = (v - 0.5) * w
            return (lat * math.cos(a), lat * math.sin(a) + 0.03 * math.sin(u * 3.0), u * hh)
        blade = Geo()
        blade.surface(fn, 6, 1, M["leaf_snake"], two_sided=True, thickness=0.004)
        r = rng.random() * pot_r * 0.6
        blade.transform(rotz(ang) @ rotx(lean), (r * math.cos(math.radians(ang)), r * math.sin(math.radians(ang)), 0.28))
        g.add(blade)
    g.collide((-pot_r, -pot_r, 0), (pot_r, pot_r, 0.4))
    return g


def frame_art(M, w, h, art, depth=0.03, mat="frame_black", mat_px=0.04):
    g = Geo()
    rb(g, (-w / 2, -depth, 0), (w / 2, 0, h), M[mat], 0.004, 1)
    g.box((-w / 2 + 0.02, -depth - 0.001, 0.02), (w / 2 - 0.02, -depth, h - 0.02), M["passepartout"], skip=("py",))
    x0, x1, z0, z1, y = -w / 2 + 0.02 + mat_px, w / 2 - 0.02 - mat_px, 0.02 + mat_px, h - 0.02 - mat_px, -depth - 0.002
    g.face([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], M[art], uv=[(0, 0), (1, 0), (1, 1), (0, 1)])
    return g


def books_row(M, x0, x1, y0, depth, z, seed, max_h=0.3):
    g = Geo()
    rng = np.random.default_rng(seed)
    x = x0
    names = ("book_a", "book_b", "book_c", "book_d", "book_e")
    while x < x1 - 0.03:
        w = 0.018 + rng.random() * 0.03
        if x + w > x1:
            break
        hh = max_h * (0.65 + rng.random() * 0.35)
        dd = depth * (0.75 + rng.random() * 0.25)
        if rng.random() < 0.08:
            x += 0.05 + rng.random() * 0.06
            continue
        g.box((x, y0, z), (x + w, y0 + dd, z + hh), M[names[int(rng.integers(0, 5))]], skip=("nz",))
        x += w + 0.002
    return g


def bookshelf(M, w=1.6, h=2.2, d=0.35, seed=7, mat="oak"):
    g = Geo()
    t = 0.025
    m = M[mat]
    rb(g, (-w / 2, 0, 0), (-w / 2 + t, d, h), m, 0.003)
    rb(g, (w / 2 - t, 0, 0), (w / 2, d, h), m, 0.003)
    g.box((-w / 2 + t, d - 0.01, 0), (w / 2 - t, d, h), m)
    shelves = 6
    for i in range(shelves):
        z = 0.06 + (h - 0.06 - t) * i / (shelves - 1)
        rb(g, (-w / 2 + t, 0.0, z), (w / 2 - t, d - 0.01, z + t), m, 0.003)
        if i < shelves - 1:
            gap = (h - 0.06 - t) / (shelves - 1) - t
            g.add(books_row(M, -w / 2 + t + 0.02, w / 2 - t - (0.35 if i % 2 else 0.05), 0.02, d - 0.05, z + t, seed + i,
                            max_h=min(0.32, gap - 0.03)))
            if i % 2:
                g.lathe((w / 2 - t - 0.17, d * 0.5, z + t), [(0.0, 0.0), (0.05, 0.0), (0.07, 0.08), (0.04, 0.18), (0.03, 0.18)],
                        M["ceramic_white" if i % 4 == 1 else "ceramic_dark"], seg=16)
    g.collide((-w / 2, 0, 0), (w / 2, d, h))
    return g


# =====================================================================================  dining

def dining_table(M, L=2.0, W=1.0, h=0.76):
    g = Geo()
    rb(g, (-L / 2, -W / 2, h - 0.04), (L / 2, W / 2, h), M["oak"], 0.01, 2)
    rb(g, (-L / 2 + 0.1, -W / 2 + 0.08, h - 0.12), (L / 2 - 0.1, W / 2 - 0.08, h - 0.04), M["oak"], 0.004, skip=("pz",))
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.cyl((sx * (L / 2 - 0.13), sy * (W / 2 - 0.11), 0), 0.02, h - 0.04, M["oak"], seg=12, r2=0.032, top=False)
    # table runner, bowl and candles
    g.box((-0.5, -0.17, h), (0.5, 0.17, h + 0.003), M["linen"], skip=("nz",))
    g.lathe((0, 0, h + 0.003), [(0.0, 0.0), (0.07, 0.0), (0.16, 0.06), (0.17, 0.08), (0.16, 0.08), (0.06, 0.012), (0.0, 0.012)],
            M["ceramic_white"], seg=28)
    for i, (x, y) in enumerate(((0.06, 0.0), (-0.04, 0.05), (-0.03, -0.06))):
        g.sphere((x, y, h + 0.06), 0.045, M["fruit_a" if i != 1 else "fruit_b"], seg=12, rings=8)
    g.collide((-L / 2, -W / 2, 0), (L / 2, W / 2, h))
    return g


def dining_chair(M, fabric="chair"):
    g = Geo()
    sh = 0.47
    for x, y in ((-0.2, -0.19), (0.2, -0.19), (-0.2, 0.19), (0.2, 0.19)):
        g.cyl((x, y, 0), 0.013, sh - 0.05, M["walnut"], seg=10, r2=0.018, top=False)
    rb(g, (-0.235, -0.235, sh - 0.065), (0.235, 0.225, sh), M[fabric], 0.03, 2, bulge=0.012, div=2)
    back = Geo()
    rb(back, (-0.22, 0.19, sh + 0.08), (0.22, 0.24, sh + 0.4), M[fabric], 0.025, 2, bulge=0.008, div=2)
    for x in (-0.19, 0.19):
        back.tube([(x, 0.2, sh - 0.03), (x, 0.215, sh + 0.12)], 0.012, M["walnut"], seg=8)
    sub(g, back, rotx(-10), (0, 0.2, sh))
    g.collide((-0.24, -0.24, 0), (0.24, 0.26, 0.86))
    return g


def pendant_linear(M, L=1.3, drop=0.75, ceiling=3.0):
    g = Geo()
    z = ceiling - drop
    rb(g, (-L / 2, -0.035, z), (L / 2, 0.035, z + 0.05), M["metal_black"], 0.008, 2)
    g.box((-L / 2 + 0.02, -0.025, z - 0.001), (L / 2 - 0.02, 0.025, z), M["lamp"], skip=("pz",))
    for x in (-L / 2 + 0.15, L / 2 - 0.15):
        g.tube([(x, 0, z + 0.05), (x, 0, ceiling)], 0.0025, M["metal_black"], seg=6, caps=False)
        g.cyl((x, 0, ceiling - 0.02), 0.045, 0.02, M["metal_black"], seg=16, bottom=True, top=False)
    for x in (-L / 3, 0.0, L / 3):
        g.light((x, 0, z - 0.06), 14.0, color=(1.0, 0.84, 0.64), radius=0.03, kind="spot", spot=120.0)
    return g


def pendant_dome(M, r=0.18, drop=0.85, ceiling=3.0, outer="metal_black", inner="brass"):
    g = Geo()
    z = ceiling - drop
    prof_out = [(r, 0.0), (r * 0.98, 0.04), (r * 0.8, 0.13), (r * 0.45, 0.2), (0.035, 0.22), (0.0, 0.22)]
    g.lathe((0, 0, z), prof_out, M[outer], seg=32)
    g.lathe((0, 0, z), [(0.0, 0.215), (0.03, 0.212), (r * 0.44, 0.195), (r * 0.78, 0.125), (r * 0.96, 0.04), (r * 0.98, 0.002)], M[inner], seg=32)
    g.sphere((0, 0, z + 0.08), 0.04, M["bulb"], seg=12, rings=6)
    g.tube([(0, 0, z + 0.22), (0, 0, ceiling)], 0.003, M["metal_black"], seg=6, caps=False)
    g.cyl((0, 0, ceiling - 0.02), 0.05, 0.02, M[outer], seg=16, top=False)
    g.light((0, 0, z + 0.04), 18.0, color=(1.0, 0.82, 0.6), radius=0.03, kind="spot", spot=140.0)
    return g


def sideboard(M, L=1.8, d=0.45, h=0.78):
    g = Geo()
    for x in (-L / 2 + 0.06, L / 2 - 0.06):
        for y in (-d + 0.06, -0.06):
            g.cyl((x, y, 0), 0.015, 0.14, M["metal_black"], seg=8, bottom=False)
    rb(g, (-L / 2, -d, 0.14), (L / 2, 0, h), M["walnut"], 0.006)
    g.add(fluted_panel(M, L - 0.04, h - 0.18, M["walnut"], pitch=0.03, depth=0.012), 0.0, (0, -d + 0.0, 0.16))
    g.collide((-L / 2, -d, 0), (L / 2, 0, h))
    return g


# =====================================================================================  kitchen

def base_run(M, units, depth=0.6, height=0.9, top=True, top_over=(0.0, 0.0), front="cab_low", sink=None, hob=None,
             back_splash=False, end_panels=(False, False), waterfall=(False, False), seat_over=0.0, plinth=True):
    """Kitchen base cabinets along +x from 0, fronts at y=0 facing -y, wall side at y=depth.
    units: list of (width, kind) with kind in drawers, doors, door, sink, hob, oven, blank.
    sink / hob: unit index hosting a sink or hob."""
    g = Geo()
    L = sum(w for w, k in units)
    pz = 0.1 if plinth else 0.0
    ct = 0.03
    zc = height - ct
    fm = M[front]
    if plinth:
        g.box((0.0, 0.06, 0.0), (L, depth - 0.02, pz), M["plinth"], skip=("nz", "py"))
    g.box((0.0, 0.0, pz), (L, depth - 0.02, zc), M["carcass"], skip=("py", "nz"))
    x = 0.0
    gap = 0.003
    for i, (w, kind) in enumerate(units):
        xa, xb = x + gap, x + w - gap
        z0, z1 = pz + gap, zc - gap
        if kind in ("drawers", "hob"):
            hs = [0.22, 0.27, 0.27] if kind == "drawers" else [0.2, 0.34, 0.24]
            total = z1 - z0
            hs = [total * hh / sum(hs) for hh in hs]
            zz = z1
            for hh in hs:
                rb(g, (xa, -0.019, zz - hh + gap), (xb, 0.0, zz), fm, 0.002)
                g.tube([(xa + 0.05, -0.034, zz - 0.045), (xb - 0.05, -0.034, zz - 0.045)], 0.006, M["handle_black"], seg=8)
                for xh in (xa + 0.06, xb - 0.06):
                    g.tube([(xh, -0.019, zz - 0.045), (xh, -0.034, zz - 0.045)], 0.004, M["handle_black"], seg=6, caps=False)
                zz -= hh
        elif kind in ("doors", "door", "sink"):
            nd = 2 if (kind in ("doors", "sink") and w > 0.55) else 1
            for d in range(nd):
                da = xa + (xb - xa) * d / nd + (gap if d > 0 else 0.0)
                db = xa + (xb - xa) * (d + 1) / nd - (gap if d < nd - 1 else 0.0)
                rb(g, (da, -0.019, z0), (db, 0.0, z1), fm, 0.002)
                hx = db - 0.04 if (d == 0 and nd == 2) or (nd == 1 and i % 2 == 0) else da + 0.04
                if nd == 2:
                    hx = db - 0.04 if d == 0 else da + 0.04
                g.tube([(hx, -0.034, z1 - 0.06), (hx, -0.034, z1 - 0.26)], 0.006, M["handle_black"], seg=8)
                for zh in (z1 - 0.07, z1 - 0.25):
                    g.tube([(hx, -0.019, zh), (hx, -0.034, zh)], 0.004, M["handle_black"], seg=6, caps=False)
        elif kind == "oven":
            rb(g, (xa, -0.019, z1 - 0.6), (xb, 0.0, z1), M["black_glass"], 0.003)
            g.box((xa + 0.05, -0.0195, z1 - 0.48), (xb - 0.05, -0.019, z1 - 0.14), M["oven_window"], skip=("py",))
            g.tube([(xa + 0.07, -0.05, z1 - 0.06), (xb - 0.07, -0.05, z1 - 0.06)], 0.009, M["steel"], seg=10)
            for xh in (xa + 0.08, xb - 0.08):
                g.tube([(xh, -0.019, z1 - 0.06), (xh, -0.05, z1 - 0.06)], 0.005, M["steel"], seg=6, caps=False)
            rb(g, (xa, -0.019, z0), (xb, 0.0, z1 - 0.6 - gap), fm, 0.002)
        else:
            rb(g, (xa, -0.019, z0), (xb, 0.0, z1), fm, 0.002)
        x += w
    if top:
        x0, x1 = -top_over[0], L + top_over[1]
        ty0 = -0.03
        ty1 = depth + seat_over
        holes = []
        if sink is not None:
            sx = sum(w for w, k in units[:sink])
            sw = units[sink][0]
            holes.append((sx + 0.06, 0.08, sx + sw - 0.06, 0.08 + 0.42, "sink"))
        if hob is not None:
            hx = sum(w for w, k in units[:hob])
            hw = units[hob][0]
            holes.append((hx + (hw - 0.75) / 2, 0.05, hx + (hw + 0.75) / 2, 0.55, "hob"))
        sinks = [h for h in holes if h[4] == "sink"]
        # countertop pieces around the sink hole
        pieces = [(x0, ty0, x1, ty1)]
        for hx0, hy0, hx1, hy1, k in sinks:
            new = []
            for (a0, b0, a1, b1) in pieces:
                if hx0 >= a1 or hx1 <= a0:
                    new.append((a0, b0, a1, b1))
                    continue
                new += [(a0, b0, hx0, b1), (hx1, b0, a1, b1), (hx0, b0, hx1, hy0), (hx0, hy1, hx1, b1)]
            pieces = new
        for (a0, b0, a1, b1) in pieces:
            if a1 - a0 > 1e-4 and b1 - b0 > 1e-4:
                g.box((a0, b0, zc), (a1, b1, height), M["quartz"], skip=())
        for hx0, hy0, hx1, hy1, k in sinks:
            d = 0.21
            sm = M["sink"]
            g.grid((hx0, hy0, zc - d), (hx1 - hx0, 0, 0), (0, hy1 - hy0, 0), sm)
            g.grid((hx0, hy0, zc - d), (0, hy1 - hy0, 0), (0, 0, d), sm)   # facing +x
            g.grid((hx1, hy1, zc - d), (0, -(hy1 - hy0), 0), (0, 0, d), sm)
            g.grid((hx1, hy0, zc - d), (-(hx1 - hx0), 0, 0), (0, 0, d), sm)  # facing +y
            g.grid((hx0, hy1, zc - d), (hx1 - hx0, 0, 0), (0, 0, d), sm)
            cx, cy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
            g.cyl((cx, cy, zc - d), 0.045, 0.002, M["steel"], seg=16, bottom=False)
            g.cyl((cx, cy, zc - d + 0.002), 0.02, 0.001, M["drain"], seg=12, bottom=False)
            # gooseneck faucet
            fx, fy = cx, hy1 + 0.07
            g.cyl((fx, fy, height), 0.03, 0.02, M["chrome"], seg=16, bottom=False)
            path = [np.array((fx, fy, height + 0.02)), np.array((fx, fy, height + 0.3))] + \
                bezier((fx, fy, height + 0.3), (fx, fy, height + 0.46), (fx, fy - 0.2, height + 0.4), 9)[1:] + \
                [np.array((fx, fy - 0.21, height + 0.3))]
            g.tube(path, 0.014, M["chrome"], seg=12)
            g.tube([(fx + 0.03, fy, height + 0.2), (fx + 0.09, fy + 0.0, height + 0.24)], 0.007, M["chrome"], seg=8)
        for hx0, hy0, hx1, hy1, k in holes:
            if k != "hob":
                continue
            rb(g, (hx0, hy0, height), (hx1, hy1, height + 0.006), M["hob_glass"], 0.004, 1, skip=("nz",))
            for bx, by, br in ((0.18, 0.15, 0.05), (0.57, 0.15, 0.04), (0.18, 0.37, 0.04), (0.57, 0.37, 0.055)):
                cx, cy = hx0 + bx, hy0 + by
                g.cyl((cx, cy, height + 0.006), br, 0.018, M["burner"], seg=20, bottom=False)
                g.cyl((cx, cy, height + 0.024), br * 0.65, 0.008, M["metal_black"], seg=16, bottom=False)
            for gx0 in (hx0 + 0.03, hx0 + 0.39):
                gx1 = gx0 + 0.33
                for t in range(3):
                    yy = hy0 + 0.05 + t * 0.2
                    g.box((gx0, yy - 0.005, height + 0.03), (gx1, yy + 0.005, height + 0.045), M["cast_iron"])
                for xx in (gx0 + 0.02, gx0 + 0.165, gx1 - 0.02):
                    g.box((xx - 0.005, hy0 + 0.045, height + 0.03), (xx + 0.005, hy1 - 0.045, height + 0.045), M["cast_iron"])
            for kx in (0.12, 0.26, 0.5, 0.64):
                g.cyl((hx0 + kx, hy0 - 0.001 + 0.0, height + 0.006), 0.018, 0.022, M["metal_black"], seg=14, bottom=False)
        for side, flag in ((0, waterfall[0]), (1, waterfall[1])):
            if flag:
                xw = x0 if side == 0 else x1
                xa, xb = (xw - ct, xw) if side == 0 else (xw, xw + ct)
                g.box((xa, ty0, 0.0), (xb, ty1, height), M["quartz"], skip=("nz",))
        if back_splash:
            g.box((x0, depth - 0.015, height), (x1, depth, height + 0.1), M["quartz"])
    g.collide((-top_over[0], 0.0, 0.0), (L + top_over[1], depth, height))
    if seat_over > 0:
        pass
    return g


def wall_run(M, units, depth=0.35, height=0.72, front="cab_up", glass=(), led=True):
    """Wall cabinets along +x from 0; front at y=0, wall at y=depth; z from 0 (bottom) to height."""
    g = Geo()
    L = sum(w for w, k in units)
    g.box((0, 0, 0), (L, depth - 0.01, height), M["carcass"], skip=("py",))
    gap = 0.003
    x = 0.0
    for i, (w, kind) in enumerate(units):
        xa, xb = x + gap, x + w - gap
        nd = 2 if w > 0.55 else 1
        for d in range(nd):
            da = xa + (xb - xa) * d / nd + (gap if d > 0 else 0.0)
            db = xa + (xb - xa) * (d + 1) / nd - (gap if d < nd - 1 else 0.0)
            if i in glass:
                for lo, hi in (((da, -0.019, gap), (da + 0.05, 0, height - gap)), ((db - 0.05, -0.019, gap), (db, 0, height - gap)),
                               ((da + 0.05, -0.019, gap), (db - 0.05, 0, gap + 0.05)), ((da + 0.05, -0.019, height - gap - 0.05), (db - 0.05, 0, height - gap))):
                    rb(g, lo, hi, M[front], 0.002)
                g.box((da + 0.05, -0.012, gap + 0.05), (db - 0.05, -0.011, height - gap - 0.05), M["glass_tint"], skip=("py",))
            else:
                rb(g, (da, -0.019, gap), (db, 0.0, height - gap), M[front], 0.002)
            hx = db - 0.035 if (d == 0 and nd == 2) or (nd == 1 and i % 2 == 0) else da + 0.035
            if nd == 2:
                hx = db - 0.035 if d == 0 else da + 0.035
            g.tube([(hx, -0.03, 0.04), (hx, -0.03, 0.2)], 0.005, M["handle_black"], seg=8)
            for zh in (0.05, 0.19):
                g.tube([(hx, -0.019, zh), (hx, -0.03, zh)], 0.0035, M["handle_black"], seg=6, caps=False)
        x += w
    if led:
        g.box((0.02, 0.02, -0.004), (L - 0.02, 0.05, 0.0), M["lamp_strip"], skip=("pz",))
        n = max(1, int(L / 0.7))
        for i in range(n):
            g.light(((i + 0.5) * L / n, 0.06, -0.03), 6.0, color=(1.0, 0.9, 0.75), radius=0.02, kind="spot", spot=150.0)
    return g


def hood(M, w=0.9, d=0.5, z0=1.95, ceiling=3.0):
    g = Geo()
    rb(g, (-w / 2, -d, z0), (w / 2, 0.0, z0 + 0.09), M["steel"], 0.006, 1)
    g.box((-w / 2 + 0.02, -d - 0.001, z0 + 0.02), (w / 2 - 0.02, -d, z0 + 0.075), M["black_glass"], skip=("py",))
    g.prism([(-w / 2, -d), (w / 2, -d), (w / 2, 0), (-w / 2, 0)][::1], z0 + 0.09, z0 + 0.09, M["steel"], top=False, bottom=False)
    rb(g, (-0.16, -0.27, z0 + 0.09), (0.16, 0.0, ceiling), M["steel"], 0.004, 1, skip=("py", "pz"))
    g.box((-w / 2 + 0.03, -d + 0.03, z0 - 0.001), (w / 2 - 0.03, -0.03, z0), M["filter"], skip=("pz",))
    for x in (-0.2, 0.2):
        g.face([(x + 0.03 * math.cos(t), -d / 2 + 0.03 * math.sin(t), z0 - 0.002) for t in
                [2 * math.pi * i / 12 for i in reversed(range(12))]], M["lamp"])
        g.light((x, -d / 2, z0 - 0.05), 5.0, color=(1.0, 0.9, 0.78), radius=0.02, kind="spot", spot=100.0)
    return g


def tall_unit(M, w=0.6, h=2.3, d=0.6, kind="oven", front="cab_low"):
    g = Geo()
    rb(g, (0, 0, 0.1), (w, d - 0.02, h), M["carcass"], 0.0, skip=("py",))
    g.box((0, 0.06, 0), (w, d - 0.02, 0.1), M["plinth"], skip=("nz", "py"))
    gap = 0.003
    if kind == "oven":
        zo0, zo1 = 0.85, 1.45
        rb(g, (gap, -0.019, zo0), (w - gap, 0.0, zo1), M["black_glass"], 0.003)
        g.box((0.05, -0.0195, zo0 + 0.08), (w - 0.05, -0.019, zo1 - 0.14), M["oven_window"], skip=("py",))
        g.tube([(0.07, -0.05, zo1 - 0.06), (w - 0.07, -0.05, zo1 - 0.06)], 0.009, M["steel"], seg=10)
        for xh in (0.08, w - 0.08):
            g.tube([(xh, -0.019, zo1 - 0.06), (xh, -0.05, zo1 - 0.06)], 0.005, M["steel"], seg=6, caps=False)
        zm0, zm1 = 1.48, 1.86
        rb(g, (gap, -0.019, zm0), (w - gap, 0.0, zm1), M["black_glass"], 0.003)
        g.box((0.04, -0.0195, zm0 + 0.06), (w - 0.18, -0.019, zm1 - 0.06), M["oven_window"], skip=("py",))
        g.box((w - 0.14, -0.0195, zm0 + 0.25), (w - 0.05, -0.019, zm1 - 0.05), M["display"], skip=("py",))
        rb(g, (gap, -0.019, 0.1 + gap), (w - gap, 0.0, zo0 - gap), M[front], 0.002)
        rb(g, (gap, -0.019, zm1 + gap), (w - gap, 0.0, h - gap), M[front], 0.002)
        for z0, z1 in ((0.1, zo0), (zm1, h)):
            g.tube([(0.05, -0.034, z1 - 0.06 if z1 < h else z0 + 0.06), (w - 0.05, -0.034, z1 - 0.06 if z1 < h else z0 + 0.06)],
                   0.006, M["handle_black"], seg=8)
    else:
        rb(g, (gap, -0.019, 0.1 + gap), (w - gap, 0.0, h - gap), M[front], 0.002)
        g.tube([(0.04, -0.034, 0.9), (0.04, -0.034, 1.5)], 0.006, M["handle_black"], seg=8)
    g.collide((0, 0, 0), (w, d, h))
    return g


def fridge(M, w=0.9, h=1.85, d=0.68):
    g = Geo()
    rb(g, (0.005, 0.02, 0.0), (w - 0.005, d, h), M["steel_dark"], 0.01, 1)
    gap = 0.004
    zf = 0.62
    rb(g, (0.005, -0.04, zf + gap), (w / 2 - gap / 2, 0.02, h - 0.005), M["steel"], 0.012, 2)
    rb(g, (w / 2 + gap / 2, -0.04, zf + gap), (w - 0.005, 0.02, h - 0.005), M["steel"], 0.012, 2)
    rb(g, (0.005, -0.04, 0.05), (w - 0.005, 0.02, zf - gap), M["steel"], 0.012, 2)
    for x in (w / 2 - 0.05, w / 2 + 0.05):
        g.tube([(x, -0.04, zf + 0.25), (x, -0.075, zf + 0.25)], 0.008, M["steel"], seg=8, caps=False)
        g.tube([(x, -0.04, h - 0.25), (x, -0.075, h - 0.25)], 0.008, M["steel"], seg=8, caps=False)
        g.tube([(x, -0.075, zf + 0.2), (x, -0.075, h - 0.2)], 0.012, M["steel"], seg=10)
    g.tube([(0.15, -0.075, zf - 0.08), (w - 0.15, -0.075, zf - 0.08)], 0.012, M["steel"], seg=10)
    for x in (0.2, w - 0.2):
        g.tube([(x, -0.04, zf - 0.08), (x, -0.075, zf - 0.08)], 0.008, M["steel"], seg=8, caps=False)
    g.box((0.12, -0.041, 1.3), (0.26, -0.04, 1.42), M["display"], skip=("py",))
    g.box((0.0, 0.0, 0.0), (w, d, 0.05), M["plinth"], skip=("nz",))
    g.collide((0, -0.04, 0), (w, d, h))
    return g


def bar_stool(M, h=0.66):
    g = Geo()
    for a in (45, 135, 225, 315):
        ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
        g.tube([(ca * 0.2, sa * 0.2, 0.0), (ca * 0.13, sa * 0.13, h - 0.04)], 0.011, M["metal_black"], seg=8)
    g.tube(ring_path((0, 0), 0.165, 0.26, 24), 0.008, M["metal_black"], seg=8, caps=False)
    g.cyl((0, 0, h - 0.045), 0.17, 0.02, M["metal_black"], seg=24)
    rb(g, (-0.19, -0.19, h - 0.03), (0.19, 0.19, h + 0.04), M["leather"], 0.05, 2, bulge=0.01, div=2)
    g.collide((-0.2, -0.2, 0), (0.2, 0.2, h))
    return g


def kitchen_props(M):
    """Kettle, canisters, chopping board and a small herb pot for the counter (local frame on the counter)."""
    g = Geo()
    g.lathe((0, 0, 0), [(0.0, 0.0), (0.085, 0.0), (0.09, 0.02), (0.08, 0.16), (0.05, 0.2), (0.0, 0.205)], M["steel"], seg=24)
    g.tube(round_path([(0.06, 0, 0.17), (0.09, 0, 0.22), (0.16, 0, 0.2), (0.15, 0, 0.06)], 0.03, 3), 0.01, M["metal_black"], seg=8)
    g.tube([(-0.07, 0, 0.12), (-0.12, 0, 0.17)], 0.012, M["steel"], seg=10)
    for i, (h, m) in enumerate(((0.2, "ceramic_white"), (0.16, "ceramic_white"), (0.12, "ceramic_white"))):
        x = 0.28 + i * 0.13
        g.cyl((x, 0.02, 0), 0.055, h, M[m], seg=20)
        g.cyl((x, 0.02, h), 0.057, 0.025, M["oak"], seg=20)
    rb(g, (-0.55, -0.08, 0), (-0.2, 0.15, 0.022), M["oak"], 0.008)
    return g


# =====================================================================================  bedroom

def bed(M, w=1.8, l=2.1, linen="duvet", throw="throw"):
    g = Geo()
    hw = w / 2
    # platform
    rb(g, (-hw - 0.04, -l, 0.08), (hw + 0.04, 0.0, 0.32), M["walnut"], 0.01, 1)
    g.box((-hw + 0.08, -l + 0.08, 0.0), (hw - 0.08, -0.08, 0.08), M["plinth"], skip=("nz",))
    # mattress
    rb(g, (-hw, -l + 0.02, 0.32), (hw, -0.02, 0.56), M["mattress"], 0.06, 2)
    # duvet: covers 2/3 of the bed, draped over the sides
    rb(g, (-hw - 0.03, -l - 0.01, 0.4), (hw + 0.03, -0.55, 0.6), M[linen], 0.08, 2, bulge=0.015, div=3)
    rb(g, (-hw - 0.035, -0.75, 0.45), (hw + 0.035, -0.52, 0.61), M[linen], 0.08, 2, bulge=0.02, div=2)
    rb(g, (-hw - 0.04, -l - 0.02, 0.47), (hw + 0.04, -l + 0.42, 0.63), M[throw], 0.06, 2, bulge=0.01, div=2)
    # pillows leaning on the headboard
    pw = (w - 0.1) / 2
    for i in range(2):
        x = -hw + 0.05 + pw * (i + 0.5)
        for j, (dep, m) in enumerate(((0.0, "pillow"), (0.13, "pillow_b"))):
            p = Geo()
            rb(p, (-pw / 2 + 0.02, -0.08, 0.0), (pw / 2 - 0.02, 0.08, 0.48 - j * 0.08), M[m], 0.08, 2, bulge=0.04, div=2)
            p.transform(rotx(-24 - j * 8) @ rotz((i - 0.5) * 4))
            g.add(p, 0.0, (x, -0.16 - dep, 0.55))
    g.collide((-hw - 0.04, -l - 0.02, 0), (hw + 0.04, 0, 0.62))
    return g


def headboard(M, w=2.6, h=1.25, z0=0.25, mat="headboard", channels=9):
    g = Geo()
    rb(g, (-w / 2, -0.03, z0), (w / 2, 0.0, z0 + h), M["walnut"], 0.006, 1)
    cw = (w - 0.1) / channels
    for i in range(channels):
        x = -w / 2 + 0.05 + i * cw
        rb(g, (x + 0.004, -0.11, z0 + 0.05), (x + cw - 0.004, -0.03, z0 + h - 0.05), M[mat], 0.035, 1, bulge=0.012, div=2, skip=("py",))
    return g


def nightstand(M, w=0.5, d=0.4, h=0.5):
    g = Geo()
    for x in (-w / 2 + 0.04, w / 2 - 0.04):
        for y in (-d + 0.04, -0.04):
            g.cyl((x, y, 0), 0.012, 0.14, M["metal_black"], seg=8, bottom=False)
    rb(g, (-w / 2, -d, 0.14), (w / 2, 0.0, h), M["walnut"], 0.006)
    for z0, z1 in ((0.15, 0.32), (0.325, h - 0.01)):
        rb(g, (-w / 2 + 0.01, -d - 0.016, z0), (w / 2 - 0.01, -d + 0.001, z1), M["oak"], 0.003)
        g.box((-0.06, -d - 0.019, (z0 + z1) / 2 - 0.006), (0.06, -d - 0.016, (z0 + z1) / 2 + 0.006), M["brass"])
    g.collide((-w / 2, -d, 0), (w / 2, 0, h))
    return g


def table_lamp(M, h=0.55):
    g = Geo()
    g.lathe((0, 0, 0), [(0.0, 0.0), (0.07, 0.0), (0.1, 0.06), (0.09, 0.18), (0.05, 0.27), (0.02, 0.3), (0.012, 0.32)],
            M["ceramic_dark"], seg=24)
    g.cyl((0, 0, 0.32), 0.006, 0.08, M["brass"], seg=8, bottom=False)
    zs = 0.3
    for side in (1,):
        g.lathe((0, 0, zs), [(0.17, 0.0), (0.13, 0.22)], M["shade"], seg=28)
        g.lathe((0, 0, zs), [(0.128, 0.22), (0.168, 0.0)], M["shade_inner"], seg=28)
    g.sphere((0, 0, zs + 0.1), 0.035, M["bulb"], seg=12, rings=6)
    g.light((0, 0, zs + 0.1), 9.0, color=(1.0, 0.8, 0.58), radius=0.04)
    return g


def wardrobe(M, w=2.4, h=2.5, d=0.6, front="wardrobe", doors=4):
    g = Geo()
    g.box((0.0, 0.0, 0.0), (w, d, h), M["carcass"], skip=("py", "ny"))
    g.box((0.0, 0.05, 0.0), (w, d, 0.08), M["plinth"], skip=("nz", "py"))
    gap = 0.003
    for i in range(doors):
        xa = w * i / doors + gap
        xb = w * (i + 1) / doors - gap
        rb(g, (xa, -0.02, 0.08 + gap), (xb, 0.0, h - gap), M[front], 0.002)
        hx = xb - 0.04 if i % 2 == 0 else xa + 0.04
        g.box((hx - 0.006, -0.04, 0.85), (hx + 0.006, -0.02, 1.55), M["handle_black"])
    g.collide((0, -0.02, 0), (w, d, h))
    return g


def desk(M, w=1.4, d=0.65, h=0.75):
    g = Geo()
    rb(g, (-w / 2, -d, h - 0.03), (w / 2, 0, h), M["oak"], 0.006, 1)
    for sx in (-1, 1):
        x = sx * (w / 2 - 0.05)
        g.box((x - 0.015, -d + 0.04, 0.0), (x + 0.015, -0.04, 0.03), M["metal_black"])
        g.box((x - 0.015, -d / 2 - 0.015, 0.0), (x + 0.015, -d / 2 + 0.015, h - 0.03), M["metal_black"])
        g.box((x - 0.015, -d + 0.04, h - 0.06), (x + 0.015, -0.04, h - 0.03), M["metal_black"])
    # laptop + lamp + mug
    rb(g, (-0.18, -0.42, h), (0.18, -0.18, h + 0.012), M["aluminium"], 0.006)
    lid = Geo()
    rb(lid, (-0.18, -0.006, 0.0), (0.18, 0.0, 0.24), M["aluminium"], 0.006)
    lid.box((-0.165, -0.0065, 0.015), (0.165, -0.006, 0.225), M["screen_on"], skip=("py",))
    lid.transform(rotx(-12))
    g.add(lid, 0.0, (0, -0.18, h + 0.012))
    g.cyl((0.32, -0.3, h), 0.04, 0.09, M["ceramic_white"], seg=16)
    g.collide((-w / 2, -d, 0), (w / 2, 0, h))
    return g


def office_chair(M):
    g = Geo()
    for a in range(5):
        ang = math.radians(90 + a * 72)
        g.tube([(0, 0, 0.1), (0.3 * math.cos(ang), 0.3 * math.sin(ang), 0.07)], 0.016, M["metal_black"], seg=8)
        g.sphere((0.3 * math.cos(ang), 0.3 * math.sin(ang), 0.03), 0.028, M["metal_black"], seg=8, rings=5)
    g.cyl((0, 0, 0.1), 0.025, 0.32, M["chrome"], seg=12)
    rb(g, (-0.25, -0.24, 0.42), (0.25, 0.24, 0.5), M["fabric_dark"], 0.035, 2, bulge=0.01, div=2)
    back = Geo()
    rb(back, (-0.23, 0.2, 0.58), (0.23, 0.26, 1.08), M["mesh"], 0.04, 2)
    back.tube([(0, 0.24, 0.45), (0, 0.26, 0.62)], 0.018, M["metal_black"], seg=8)
    sub(g, back, rotx(-8), (0, 0.22, 0.5))
    g.collide((-0.3, -0.3, 0), (0.3, 0.3, 1.0))
    return g


def curtain(M, width, height, mat="curtain", folds=None, depth=0.06, seed=1):
    """Pleated curtain hanging in the xz plane from z=height down to 0 (front faces -y)."""
    g = Geo()
    folds = folds or max(3, int(width / 0.12))
    rng = np.random.default_rng(seed)
    phase = rng.random() * 6.28

    def fn(u, v):
        x = (u - 0.5) * width
        y = -depth * 0.5 * (1 + math.sin(u * folds * 2 * math.pi + phase)) * (0.7 + 0.3 * v)
        return (x, y, v * height)
    g.surface(fn, folds * 4, 3, M[mat], two_sided=True, thickness=0.004)
    return g


def curtain_rod(M, width):
    g = Geo()
    g.tube([(-width / 2, 0, 0), (width / 2, 0, 0)], 0.012, M["metal_black"], seg=10)
    for x in (-width / 2, width / 2):
        g.sphere((x, 0, 0), 0.02, M["metal_black"], seg=10, rings=6)
    return g


# =====================================================================================  bathroom

def wc(M):
    g = Geo()
    bowl = Geo()
    bowl.lathe((0, 0, 0), [(0.0, 0.0), (0.12, 0.0), (0.17, 0.1), (0.19, 0.25), (0.185, 0.28), (0.14, 0.285), (0.1, 0.2), (0.0, 0.17)],
               M["ceramic_white"], seg=28)
    bowl.transform(np.diag((1.0, 1.35, 1.0)))
    g.add(bowl, 0.0, (0, -0.28, 0.12))
    rb(g, (-0.165, -0.24, 0.14), (0.165, 0.0, 0.41), M["ceramic_white"], 0.07, 2, skip=("py",))
    seat = Geo()
    seat.lathe((0, 0, 0), [(0.0, 0.0), (0.185, 0.0), (0.19, 0.012), (0.185, 0.03), (0.0, 0.03)], M["ceramic_white"], seg=28)
    seat.transform(np.diag((1.0, 1.35, 1.0)))
    g.add(seat, 0.0, (0, -0.28, 0.405))
    # concealed cistern: flush plate on the wall
    rb(g, (-0.12, -0.012, 0.95), (0.12, 0.0, 1.11), M["chrome"], 0.006)
    g.box((-0.11, -0.013, 0.96), (-0.005, -0.012, 1.1), M["white_gloss"], skip=("py",))
    g.box((0.005, -0.013, 0.96), (0.11, -0.012, 1.1), M["white_gloss"], skip=("py",))
    g.collide((-0.2, -0.55, 0), (0.2, 0.0, 0.45))
    return g


def vanity(M, w=1.0, d=0.5, z0=0.35, h=0.5, basin=True, mirror_h=0.8, mirror=True):
    g = Geo()
    rb(g, (-w / 2, -d, z0), (w / 2, 0.0, z0 + h - 0.02), M["walnut"], 0.004)
    for i in range(2):
        xa, xb = -w / 2 + 0.005 + (w - 0.01) * i / 2 + 0.002, -w / 2 + 0.005 + (w - 0.01) * (i + 1) / 2 - 0.002
        rb(g, (xa, -d - 0.016, z0 + 0.01), (xb, -d + 0.001, z0 + h - 0.04), M["walnut"], 0.003)
        g.box((xa + 0.04 if i else xb - 0.2, -d - 0.019, z0 + h - 0.09), (xa + 0.2 if i else xb - 0.04, -d - 0.016, z0 + h - 0.08), M["brass"])
    rb(g, (-w / 2 - 0.01, -d - 0.02, z0 + h - 0.02), (w / 2 + 0.01, 0.0, z0 + h + 0.01), M["quartz"], 0.004)
    top = z0 + h + 0.01
    if basin:
        g.lathe((0, -d / 2 - 0.01, top), [(0.0, 0.0), (0.09, 0.0), (0.18, 0.03), (0.2, 0.13), (0.19, 0.135), (0.17, 0.04), (0.06, 0.015), (0.0, 0.015)],
                M["ceramic_white"], seg=32)
        g.cyl((0, -d / 2 - 0.01, top + 0.015), 0.022, 0.002, M["chrome"], seg=12, bottom=False)
        fx, fy = 0.0, -0.06
        g.cyl((fx, fy, top), 0.025, 0.24, M["chrome"], seg=16)
        g.tube([(fx, fy, top + 0.22), (fx, fy - 0.16, top + 0.22)], 0.013, M["chrome"], seg=12)
        g.tube([(fx, fy, top + 0.245), (fx + 0.0, fy - 0.07, top + 0.27)], 0.006, M["chrome"], seg=8)
    if mirror:
        mz = top + 0.25
        rb(g, (-w / 2 + 0.05, -0.025, mz), (w / 2 - 0.05, 0.0, mz + mirror_h), M["metal_black"], 0.006)
        g.box((-w / 2 + 0.065, -0.026, mz + 0.015), (w / 2 - 0.065, -0.025, mz + mirror_h - 0.015), M["mirror"], skip=("py",))
        g.box((-w / 2 + 0.07, -0.004, mz - 0.01), (w / 2 - 0.07, 0.0, mz), M["lamp_strip"], skip=("pz", "py"))
        g.light((0, -0.12, mz + mirror_h + 0.05), 10.0, color=(1.0, 0.9, 0.78), radius=0.05)
    g.collide((-w / 2, -d - 0.02, 0.0), (w / 2, 0, top))
    return g


def shower(M, w=1.2, d=1.0, h=2.0):
    """Walk-in shower: glass panel along the open side (x from -w/2 to -w/2+0.9 at y=-d), rain head, mixer.
    Returns (fittings, glass)."""
    g = Geo()
    gl = Geo()
    for side in (-1, 1):
        y = -d + side * 0.005
        nn = (0, side, 0)
        pts = [(-w / 2, y, 0.01), (-w / 2 + 0.9, y, 0.01), (-w / 2 + 0.9, y, h), (-w / 2, y, h)]
        if side < 0:
            pts = pts[::-1]
        gl.face(pts, M["glass_rail"])
    g.box((-w / 2, -d - 0.012, 0.0), (-w / 2 + 0.9, -d + 0.012, 0.012), M["steel"])
    g.box((-w / 2 + 0.88, -d - 0.008, 0.0), (-w / 2 + 0.9, -d + 0.008, h), M["metal_black"])
    g.tube([(-w / 2 + 0.9, -d, h - 0.01), (-w / 2 + 0.9, 0.0, h - 0.01)], 0.008, M["metal_black"], seg=8)
    rb(g, (-0.15, -0.45, h + 0.16), (0.15, -0.15, h + 0.175), M["metal_black"], 0.01)
    g.tube([(0, -0.3, h + 0.175), (0, -0.3, h + 0.24), (0, 0.0, h + 0.24)], 0.01, M["metal_black"], seg=8)
    g.tube([(0.2, 0.0, 1.1), (0.2, -0.04, 1.1)], 0.035, M["metal_black"], seg=16)
    g.tube([(0.2, -0.04, 1.1), (0.2, -0.1, 1.1)], 0.01, M["metal_black"], seg=8)
    rb(g, (-0.05, -d / 2 - 0.3, 0.001), (0.05, -d / 2 + 0.3, 0.004), M["steel"], 0.002, skip=("nz",))
    gl.collide((-w / 2, -d - 0.03, 0), (-w / 2 + 0.9, -d + 0.03, h), layer=1)
    return g, gl


def towel_rail(M, w=0.6, z=1.0):
    g = Geo()
    for x in (-w / 2, w / 2):
        g.tube([(x, 0.0, z), (x, -0.08, z)], 0.008, M["metal_black"], seg=8)
    g.tube([(-w / 2, -0.08, z), (w / 2, -0.08, z)], 0.01, M["metal_black"], seg=8)
    rb(g, (-w / 2 + 0.06, -0.1, z - 0.5), (w / 2 - 0.06, -0.06, z + 0.012), M["towel"], 0.012, 2, bulge=0.004, div=2)
    return g


# =====================================================================================  outdoor

def tree(M, h=5.0, seed=11, crown=1.6):
    g = Geo()
    rng = np.random.default_rng(seed)
    trunk = [np.array((0, 0, 0)), np.array((0.05, 0.02, h * 0.3)), np.array((-0.03, 0.06, h * 0.55)), np.array((0.04, 0.0, h * 0.72))]
    g.tube(trunk, 0.11, M["bark"], seg=10, caps=False)
    for i in range(5):
        a = rng.random() * 2 * math.pi
        z = h * (0.45 + 0.08 * i)
        g.tube([(0, 0, z), (math.cos(a) * crown * 0.5, math.sin(a) * crown * 0.5, z + 0.6)], 0.04, M["bark"], seg=6)
    for i in range(12):
        a = rng.random() * 2 * math.pi
        r = rng.random() ** 0.5 * crown * 0.7
        c = (math.cos(a) * r, math.sin(a) * r, h * 0.7 + (rng.random() - 0.3) * crown * 0.8)
        s = crown * (0.45 + rng.random() * 0.35)
        g.sphere(c, s, M["foliage"], seg=10, rings=7, scale=(1.0, 1.0, 0.8))
    g.collide((-0.15, -0.15, 0), (0.15, 0.15, 2.5))
    return g


def hedge(M, L, w=0.6, h=1.0, seed=3):
    g = Geo()
    rb(g, (0, -w / 2, 0), (L, w / 2, h), M["hedge"], min(0.18, h * 0.3, w * 0.4), 2, skip=("nz",))
    g.collide((0, -w / 2, 0), (L, w / 2, h))
    return g


def shrub(M, r=0.45, seed=5):
    g = Geo()
    rng = np.random.default_rng(seed)
    for i in range(4):
        a = rng.random() * 2 * math.pi
        c = (math.cos(a) * r * 0.35, math.sin(a) * r * 0.35, r * (0.55 + rng.random() * 0.2))
        g.sphere(c, r * (0.6 + rng.random() * 0.25), M["hedge"], seg=10, rings=6, zmin=-0.3)
    return g


def planter(M, L=1.2, w=0.45, h=0.5, plant=True, seed=9):
    g = Geo()
    rb(g, (-L / 2, -w / 2, 0), (L / 2, w / 2, h), M["concrete_planter"], 0.01, 1, skip=("nz",))
    g.box((-L / 2 + 0.04, -w / 2 + 0.04, h - 0.06), (L / 2 - 0.04, w / 2 - 0.04, h - 0.05), M["soil"], skip=("nz",))
    if plant:
        rng = np.random.default_rng(seed)
        for i in range(int(L / 0.35)):
            x = -L / 2 + 0.2 + i * 0.35 + rng.random() * 0.05
            g.add(shrub(M, 0.22 + rng.random() * 0.06, seed + i), 0.0, (x, 0, h - 0.12))
    g.collide((-L / 2, -w / 2, 0), (L / 2, w / 2, h))
    return g


def bollard(M, h=0.6):
    g = Geo()
    g.cyl((0, 0, 0), 0.07, h, M["metal_black"], seg=16)
    g.cyl((0, 0, h - 0.12), 0.0705, 0.06, M["lamp"], seg=16, top=False, bottom=False)
    return g


def wall_light(M):
    g = Geo()
    rb(g, (-0.05, -0.08, -0.12), (0.05, 0.0, 0.12), M["metal_black"], 0.01, 1)
    g.box((-0.035, -0.081, -0.122), (0.035, -0.01, -0.12), M["lamp"], skip=("pz",))
    g.box((-0.035, -0.081, 0.12), (0.035, -0.01, 0.122), M["lamp"], skip=("nz",))
    g.light((0, -0.15, -0.2), 9.0, color=(1.0, 0.82, 0.6), radius=0.03, kind="spot", spot=90.0, dir=(0, 0, -1))
    return g


def lounger(M):
    g = Geo()
    rb(g, (-0.33, -1.0, 0.0), (0.33, 0.9, 0.3), M["teak"], 0.02, 1)
    rb(g, (-0.3, -0.97, 0.3), (0.3, 0.35, 0.38), M["cushion_out"], 0.04, 2, bulge=0.01, div=2)
    back = Geo()
    rb(back, (-0.3, 0.0, 0.0), (0.3, 0.6, 0.08), M["cushion_out"], 0.04, 2, bulge=0.012, div=2)
    back.transform(rotx(45))
    g.add(back, 0.0, (0, 0.3, 0.32))
    g.collide((-0.33, -1.0, 0), (0.33, 0.9, 0.6))
    return g


def gate_slats(M, L, h, slat=0.1, gap=0.02):
    g = Geo()
    n = int(h / (slat + gap))
    for i in range(n):
        z = 0.05 + i * (slat + gap)
        rb(g, (0, -0.025, z), (L, 0.025, z + slat), M["gate"], 0.004)
    for x in (0.0, L - 0.05):
        g.box((x, -0.035, 0.0), (x + 0.05, 0.035, h), M["metal_black"])
    g.collide((0, -0.04, 0), (L, 0.04, h))
    return g
