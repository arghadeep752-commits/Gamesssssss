"""Ground, water, trees and street furniture of the DANGA map."""
import math
import random

import numpy as np

import layout as LY
from mesh import L, Mesh, norm, v3
from roads import offset_line, resample

TERRAIN_STEP = 6.0


# ================================================================================================= ground
def noise2(x, z, seed=0):
    """Cheap smooth value noise (sum of sines) for texture variation."""
    return (np.sin(x * 0.013 + seed) * np.cos(z * 0.011 + seed * 1.7) + 0.5 * np.sin(x * 0.041 + z * 0.037 + seed * 3.1)
            + 0.25 * np.sin(x * 0.11 - z * 0.093 + seed * 5.3)) / 1.75


def terrain(M, grid):
    """Height-field ground in chunks. Texture layers blend grass / dirt / sand / rock / paddy."""
    H = LY.HALF
    n = int(2 * H / TERRAIN_STEP) + 1
    xs = np.linspace(-H, H, n)
    X, Z = np.meshgrid(xs, xs)                 # [row = z][col = x]
    Y = LY.height(X, Z)
    # flatten under roads and sites (their surfaces float a few cm above)
    rh = grid.sample_height(X, Z)
    has = ~np.isnan(rh)
    Y = np.where(has, rh - 0.12, Y)
    # texture choice
    wet = LY.water_info(X, Z)
    S1 = np.full(X.shape, L["grass"], float)
    S2 = np.full(X.shape, L["ground"], float)
    B = np.clip(0.5 + 0.9 * noise2(X, Z, 1.0), 0, 1) ** 1.5 * 0.85
    kind = np.vectorize(LY.district)(X, Z)
    # towns are dustier, the palace lawns greener
    B = np.where(kind == "core", np.clip(B + 0.15, 0, 1), B)
    B = np.where(kind == "park", B * 0.3, B)
    B = np.where(has, 1.0, B)
    # beach
    cz = np.vectorize(LY.coast_z)(X)
    beach = (Z < cz + 60)
    S1 = np.where(beach, L["sand"], S1)
    S2 = np.where(beach, L["ground"], S2)
    B = np.where(beach, np.clip((Z - (cz + 30)) / 30.0, 0, 1) * 0.7, B)
    # banks of rivers and ponds: mud and stones
    bank = (Y < -0.25) & ~beach
    S1 = np.where(bank, L["ground"], S1)
    S2 = np.where(bank, L["rock"], S2)
    B = np.where(bank, np.clip(-Y / 3.0, 0, 1), B)
    # steep slopes: rock
    gy, gx = np.gradient(Y, TERRAIN_STEP)
    slope = np.hypot(gx, gy)
    steep = slope > 0.45
    S2 = np.where(steep & ~has, L["rock"], S2)
    B = np.where(steep & ~has, np.clip((slope - 0.45) * 2.5, 0, 1), B)
    # paddy fields on flat outskirts
    paddy = (kind == "outskirts") & (slope < 0.05) & ~has & np.isnan(wet) & (noise2(X * 0.6, Z * 0.6, 7.0) > 0.15)
    S1 = np.where(paddy, L["paddy"], S1)
    S2 = np.where(paddy, L["grass"], S2)
    B = np.where(paddy, 0.0, B)
    tint = 0.92 + 0.08 * noise2(X * 1.7, Z * 1.7, 3.0)
    # normals
    nx = -gx
    nz = -gy
    N3 = np.stack([nx, np.ones_like(nx), nz], -1)
    N3 /= np.linalg.norm(N3, axis=-1, keepdims=True)
    # write per chunk
    cs = M.size
    step_per_chunk = int(round(cs / TERRAIN_STEP))
    nchunks = int(math.ceil((2 * H) / cs))
    for ci in range(nchunks):
        for cj in range(nchunks):
            i0, i1 = cj * step_per_chunk, min(n - 1, (cj + 1) * step_per_chunk)
            j0, j1 = ci * step_per_chunk, min(n - 1, (ci + 1) * step_per_chunk)
            if i1 <= i0 or j1 <= j0:
                continue
            sub = (slice(i0, i1 + 1), slice(j0, j1 + 1))
            x = X[sub]
            z = Z[sub]
            P = np.stack([x, Y[sub], z], -1).reshape(-1, 3)
            Nn = N3[sub].reshape(-1, 3)
            UV = np.stack([x / 5.0, z / 5.0], -1).reshape(-1, 2)
            rows, cols = x.shape
            I = []
            for r in range(rows - 1):
                for c in range(cols - 1):
                    a = r * cols + c
                    b = a + 1
                    d = a + cols
                    e = d + 1
                    # (a, d, e) faces up: a=(x,z), d=(x,z+s), e=(x+s,z+s)
                    I += [a, d, e, a, e, b]
            cx, cz2 = float(x.mean()), float(z.mean())
            mt = M.get(cx, cz2, "terrain")
            t = tint[sub].reshape(-1)
            col = np.stack([t * 0.98, t, t * 0.96], -1)
            mt.add(P, Nn, UV, S1[sub].reshape(-1), 1.0, col, 0.0, I, S2=S2[sub].reshape(-1), B=B[sub].reshape(-1))
            mc = M.get(cx, cz2, "coll")
            mc.add(P, Nn, UV, 0, 1.0, (1, 1, 1), 0.0, I)
    return X, Z, Y


HILL_RINGS = [1500.0, 2300.0, 3200.0]
HILL_SEG = 72


def _hill_heights():
    """Heights of the distant hill rings: [ring][segment] (the same numbers every build)."""
    rnd = random.Random(3)
    out = []
    for r_i, r in enumerate(HILL_RINGS):
        row = []
        for k in range(HILL_SEG + 1):
            a = 2 * math.pi * k / HILL_SEG
            x, z = r * math.cos(a), r * math.sin(a)
            if z > -700:                                   # hills north, east and west
                h = 40 + 80 * max(0.0, math.sin(a * 3.0 + 1.0)) + 50 * max(0.0, math.cos(a * 5.0)) + rnd.uniform(0, 30)
                if x < -900:
                    h *= 0.25                              # the plains of Bangladesh
                h *= (0.6 + 0.3 * r_i)
            else:
                h = -12.0                                  # under the sea
            row.append(h if r_i > 0 else min(h, 25.0))
        row[-1] = row[0]
        out.append(row)
    return out


def countryside_skirt(M):
    """Paddy fields, river banks and the beach going on past the edge of the map up to the distant hills, so the town
    never ends at a cliff into nothing (seen from the helicopter, the boat or a roof). Drawn like the terrain."""
    m = M.extra("skirt", terrain=True)
    H = LY.HALF
    seg = 240
    fr = np.array([0.0, 0.004, 0.012, 0.03, 0.06, 0.1, 0.15, 0.22, 0.3, 0.4, 0.52, 0.65, 0.8, 1.0])
    A = np.linspace(0.0, 2 * math.pi, seg + 1)
    ca, sa = np.cos(A), np.sin(A)
    r_in = (H - 3.0) / np.maximum(np.abs(ca), np.abs(sa))        # starts just inside the square edge of the map
    R = r_in[None, :] + (HILL_RINGS[0] - r_in[None, :]) * fr[:, None]
    X, Z = R * ca[None, :], R * sa[None, :]
    Y = LY.height(X, Z)
    ring0 = np.array(_hill_heights()[0])
    hr = np.interp(A, np.linspace(0.0, 2 * math.pi, HILL_SEG + 1), ring0)
    t = LY.smooth(1050.0, HILL_RINGS[0], R)
    Y = Y * (1 - t) + hr[None, :] * t
    Y[0] -= 0.1                                                    # tucked under the edge of the terrain
    # texture layers like the terrain: fields, dust, beach, muddy banks
    cz = np.vectorize(LY.coast_z)(X)
    beach = Z < cz + 60
    S1 = np.full(X.shape, L["grass"], float)
    S2 = np.full(X.shape, L["ground"], float)
    B = np.clip(0.5 + 0.9 * noise2(X, Z, 1.0), 0, 1) ** 1.5 * 0.6
    paddy = ~beach & (Y > -0.2) & (R > r_in[None, :] + 25.0) & (noise2(X * 0.6, Z * 0.6, 7.0) > -0.2)
    S1 = np.where(paddy, L["paddy"], S1)
    S2 = np.where(paddy, L["grass"], S2)
    B = np.where(paddy, 0.0, B)
    S1 = np.where(beach, L["sand"], S1)
    S2 = np.where(beach, L["ground"], S2)
    B = np.where(beach, np.clip((Z - (cz + 30)) / 30.0, 0, 1) * 0.7, B)
    bank = (Y < -0.25) & ~beach
    S1 = np.where(bank, L["ground"], S1)
    S2 = np.where(bank, L["rock"], S2)
    B = np.where(bank, np.clip(-Y / 3.0, 0, 1), B)
    tint = (0.92 + 0.08 * noise2(X * 1.7, Z * 1.7, 3.0)) * (1.0 - 0.18 * t)
    col = np.stack([tint * 0.98, tint, tint * 0.96], -1).reshape(-1, 3)
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    UV = np.stack([X / 5.0, Z / 5.0], -1).reshape(-1, 2)
    cols = seg + 1
    I = []
    for r in range(len(fr) - 1):
        for k in range(seg):
            a = r * cols + k
            b, d = a + 1, a + cols
            I += [a, d, d + 1, a, d + 1, b]
    m.add(P, [(0, 1, 0)], UV, S1.reshape(-1), 1.0, col, 0.0, I, S2=S2.reshape(-1), B=B.reshape(-1))
    _fix_up(m)
    _smooth_normals(m)


def _smooth_normals(m):
    """Vertex normals from the triangles (the skirt is one smooth sheet)."""
    a = m.arrays()
    if a is None or "N" not in a:
        return
    P, I = a["P"], a["I"].reshape(-1, 3)
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    N = np.zeros_like(P)
    for j in range(3):
        np.add.at(N, I[:, j], fn)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-9
    N[N[:, 1] < 0] *= -1
    m.N = [N]


def distant_hills(M):
    """A ring of low hills beyond the edge of the map, so the world does not end in a void (north and east), flat
    Bangladesh plains to the west, the open sea to the south."""
    m = M.extra("distant")
    rings = HILL_RINGS
    seg = HILL_SEG
    heights = _hill_heights()
    P, UV, I, C = [], [], [], []
    for r_i, r in enumerate(rings):
        for k in range(seg + 1):
            a = 2 * math.pi * k / seg
            x, z = r * math.cos(a), r * math.sin(a)
            P.append((x, heights[r_i][k], z))
            UV.append((k / 4.0, r_i))
            C.append((0.55 + 0.1 * r_i, 0.6 + 0.08 * r_i, 0.55 + 0.12 * r_i))
    cols = seg + 1
    for r_i in range(len(rings) - 1):
        for k in range(seg):
            a = r_i * cols + k
            b = a + 1
            d = a + cols
            e = d + 1
            I += [a, d, e, a, e, b]
    Parr = np.array(P)
    m.add(Parr, [(0, 1, 0)], UV, L["grass"], 1.0, np.array(C), 0.0, I)


# ================================================================================================= water
def water(M):
    """River ribbon, ponds, the lake (in chunks) and the sea (one big separate mesh)."""
    # river
    pts = resample(LY.RIVER, 12.0)
    halfw = LY.RIVER_W / 2 + 8
    for i in range(0, len(pts) - 1, 4):
        seg = pts[i:i + 5]
        if len(seg) < 2:
            continue
        cx, cz = seg[len(seg) // 2]
        m = M.get(cx, cz, "water")
        m.strip(seg, 2 * halfw, LY.RIVER_LEVEL, 0, tile=(20, 20), u_along=False, col=(0.35, 0.45, 0.3))
    # ponds
    for name, c, size, rad, lv in LY.PONDS:
        poly = _round_rect(c, (size[0] + 4, size[1] + 4), rad + 2)
        M.get(c[0], c[1], "water").polygon(poly, lv, 0, tile=(20, 20), col=(0.3, 0.42, 0.32))
    # the lake: an ellipse split in four quarters so each part lands in a few chunks
    name, c, r, lv = LY.LAKE
    for q in range(8):
        a0, a1 = q * math.pi / 4, (q + 1) * math.pi / 4
        poly = [c] + [(c[0] + (r[0] + 4) * math.cos(a), c[1] + (r[1] + 4) * math.sin(a)) for a in np.linspace(a0, a1, 7)]
        mx = sum(p[0] for p in poly) / len(poly)
        mz = sum(p[1] for p in poly) / len(poly)
        M.get(mx, mz, "water").polygon(poly, lv, 0, tile=(20, 20), col=(0.25, 0.4, 0.45))
    # the sea: a fan of strips from the coast out to the horizon
    m = M.extra("sea")
    xs = np.linspace(-6000, 6000, 121)
    zs_out = [-1200, -1600, -2400, -4000, -8000]
    P, I, C, UV = [], [], [], []
    cols = len(xs)
    for k, x in enumerate(xs):
        zc = LY.coast_z(x) + 25.0
        P.append((x, LY.SEA_LEVEL, zc))
        C.append((0.0, 0.0, 0.0))
    for zz in zs_out:
        for x in xs:
            P.append((x, LY.SEA_LEVEL, float(zz)))
            C.append((1.0, 1.0, 1.0))
    nrow = 1 + len(zs_out)
    for r in range(nrow - 1):
        for k in range(cols - 1):
            a = r * cols + k
            b = a + 1
            d = a + cols
            e = d + 1
            # rows go south (z decreasing): (a, b, e) faces up?  a=(x,z0) b=(x+,z0) e=(x+,z1<z0)
            I += [a, b, e, a, e, d]
    Parr = np.array(P)
    UV = Parr[:, [0, 2]] / 30.0
    # depth hint in the colour: 0 at the shore, 1 far out
    m.add(Parr, [(0, 1, 0)], UV, 0, 1.0, np.array(C), 0.0, I)
    _fix_up(m)


def _fix_up(m):
    """Make every triangle of a flat mesh face up (cheap safety for hand-built water grids)."""
    a = m.arrays()
    if a is None:
        return
    P, I = a["P"], a["I"].reshape(-1, 3)
    n = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    flip = n[:, 1] < 0
    I[flip] = I[flip][:, [0, 2, 1]]
    m.I = [I.reshape(-1)]


def _round_rect(c, size, rad, seg=4):
    hx, hz = size[0] / 2 - rad, size[1] / 2 - rad
    pts = []
    for qx, qz, a0 in ((hx, -hz, -90), (hx, hz, 0), (-hx, hz, 90), (-hx, -hz, 180)):
        for k in range(seg + 1):
            a = math.radians(a0 + 90 * k / seg)
            pts.append((c[0] + qx + rad * math.cos(a), c[1] + qz + rad * math.sin(a)))
    return pts            # counter-clockwise


# ================================================================================================= trees
def palm(M, x, y, z, rnd, kind="coconut"):
    """Coconut or areca palm: tapered, slightly bent trunk and a crown of pinnate fronds."""
    mw = M.get(x, z, "world")
    mf = M.get(x, z, "foliage")
    if kind == "coconut":
        h = rnd.uniform(8.0, 13.0)
        r0, r1 = 0.24, 0.16
        nf, flen = rnd.randint(10, 13), rnd.uniform(3.6, 4.6)
        lean = rnd.uniform(0.5, 1.8)
    else:
        h = rnd.uniform(9.0, 14.0)
        r0, r1 = 0.12, 0.09
        nf, flen = rnd.randint(6, 8), rnd.uniform(2.2, 2.8)
        lean = rnd.uniform(0.0, 0.4)
    la = rnd.uniform(0, 2 * math.pi)
    lx, lz = math.cos(la), math.sin(la)
    rings = 3
    for k in range(rings):
        t0, t1 = k / rings, (k + 1) / rings
        b0 = lean * t0 * t0
        b1 = lean * t1 * t1
        cx0, cz0 = x + lx * b0, z + lz * b0
        cx1, cz1 = x + lx * b1, z + lz * b1
        mw.cylinder((cx0 + cx1) / 2, y + t0 * h, (cz0 + cz1) / 2, r0 + (r1 - r0) * t0, h / rings + 0.02, L["bark"], seg=5,
                    r_top=r0 + (r1 - r0) * t1, top=False, tile=(1.0, 1.5), col=(0.75, 0.68, 0.6))
    top = v3(x + lx * lean, y + h, z + lz * lean)
    tint = (0.85, 0.95, 0.75) if kind == "coconut" else (0.8, 1.0, 0.7)
    for i in range(nf):
        a = 2 * math.pi * i / nf + rnd.uniform(-0.2, 0.2)
        droop = rnd.uniform(0.25, 0.7)
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        side = np.array([-d[2], 0.0, d[0]])
        p0 = top
        p1 = top + d * flen * 0.5 + np.array([0, (0.3 - droop * 0.25) * flen, 0])
        p2 = top + d * flen + np.array([0, (0.3 - droop) * flen, 0])
        w = flen * 0.24
        tilt = np.array([0, -0.15 * w, 0])
        # one bent blade in two pieces (the frond picture has the leaflets on both sides of the rib)
        mf.quad(p0 - side * w * 0.6, p1 - side * w + tilt, p1 + side * w + tilt, p0 + side * w * 0.6, L["palmleaf"],
                uvs=[(0, 0), (0, 0.5), (1, 0.5), (1, 0)], col=tint)
        mf.quad(p1 - side * w + tilt, p2 - side * w * 0.5 + tilt, p2 + side * w * 0.5 + tilt, p1 + side * w + tilt, L["palmleaf"],
                uvs=[(0, 0.5), (0, 1), (1, 1), (1, 0.5)], col=tint)
    return h


def banana(M, x, y, z, rnd):
    mw = M.get(x, z, "world")
    mf = M.get(x, z, "foliage")
    h = rnd.uniform(2.2, 3.4)
    mw.cylinder(x, y, z, 0.13, h, L["bark"], seg=6, r_top=0.09, top=False, col=(0.6, 0.7, 0.4), tile=(1, 1))
    top = v3(x, y + h, z)
    for i in range(rnd.randint(6, 9)):
        a = 2 * math.pi * i / 7 + rnd.uniform(-0.3, 0.3)
        d = np.array([math.cos(a), 0.0, math.sin(a)])
        side = np.array([-d[2], 0.0, d[0]])
        length = rnd.uniform(1.6, 2.4)
        up = rnd.uniform(0.3, 1.0)
        p0 = top + np.array([0, -0.1, 0])
        p1 = top + d * length * 0.55 + np.array([0, up * 0.6, 0])
        p2 = top + d * length + np.array([0, up * 0.2 - 0.3, 0])
        w = 0.45
        for (pa, pb, va, vb) in ((p0, p1, 0.0, 0.55), (p1, p2, 0.55, 1.0)):
            mf.quad(pa - side * w, pb - side * w, pb + side * w, pa + side * w, L["bananaleaf"],
                    uvs=[(0, va), (0, vb), (1, vb), (1, va)], col=(0.9, 1.0, 0.8))


def broadleaf(M, x, y, z, rnd, big=False):
    """Mango / rain tree: trunk, a few limbs and a canopy of crossed leaf-cluster cards."""
    mw = M.get(x, z, "world")
    mf = M.get(x, z, "foliage")
    h = rnd.uniform(5.5, 8.0) * (1.4 if big else 1.0)
    r = rnd.uniform(2.6, 3.8) * (1.4 if big else 1.0)
    trunk_h = h * 0.45
    mw.cylinder(x, y, z, 0.28 * (1.3 if big else 1.0), trunk_h + 0.6, L["bark"], seg=7, r_top=0.18, top=False, tile=(1.2, 1.5),
                col=(0.7, 0.62, 0.55))
    cy = y + trunk_h + r * 0.55
    n = 6 if not big else 9
    tint = rnd.choice([(0.8, 0.95, 0.7), (0.75, 0.9, 0.62), (0.9, 1.0, 0.75)])
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0.2, 0.75) * r
        px, pz = x + math.cos(a) * rr, z + math.sin(a) * rr
        py = cy + rnd.uniform(-0.5, 0.6) * r * 0.6
        s = rnd.uniform(1.6, 2.4) * (r / 3.0)
        rot_a = rnd.uniform(0, math.pi)
        for k in range(2):
            b = rot_a + k * math.pi / 2
            dx, dz = math.cos(b) * s, math.sin(b) * s
            p0 = v3(px - dx, py - s * 0.8, pz - dz)
            p1 = v3(px + dx, py - s * 0.8, pz + dz)
            p2 = v3(px + dx, py + s * 0.8, pz + dz)
            p3 = v3(px - dx, py + s * 0.8, pz - dz)
            mf.quad(p0, p1, p2, p3, L["leaves"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], col=tint)
        # a horizontal card helps from above
        if i % 2 == 0:
            q = [v3(px - s, py + 0.2, pz - s), v3(px - s, py + 0.2, pz + s), v3(px + s, py + 0.2, pz + s), v3(px + s, py + 0.2, pz - s)]
            mf.quad(q[0], q[1], q[2], q[3], L["leaves"], uvs=[(0, 0), (0, 1), (1, 1), (1, 0)], col=tint)
    return h, r


def bamboo(M, x, y, z, rnd):
    mw = M.get(x, z, "world")
    mf = M.get(x, z, "foliage")
    n = rnd.randint(5, 8)
    for i in range(n):
        a = rnd.uniform(0, 2 * math.pi)
        rr = rnd.uniform(0.0, 1.2)
        px, pz = x + math.cos(a) * rr, z + math.sin(a) * rr
        h = rnd.uniform(6.0, 10.0)
        mw.cylinder(px, y, pz, 0.05, h, L["bark"], seg=4, top=False, col=(0.55, 0.65, 0.3), tile=(0.5, 2.0))
        for k in range(1):
            b = rnd.uniform(0, math.pi)
            s = rnd.uniform(1.2, 1.8)
            dx, dz = math.cos(b) * s, math.sin(b) * s
            yy = y + h - s * 0.6 - k * 1.5
            mf.quad(v3(px - dx, yy - s, pz - dz), v3(px + dx, yy - s, pz + dz), v3(px + dx, yy + s, pz + dz), v3(px - dx, yy + s, pz - dz),
                    L["leaves"], uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], col=(0.85, 1.0, 0.65))


def bush(M, x, y, z, rnd):
    mf = M.get(x, z, "foliage")
    s = rnd.uniform(0.6, 1.1)
    for k in range(2):
        b = rnd.uniform(0, math.pi) + k * math.pi / 2
        dx, dz = math.cos(b) * s, math.sin(b) * s
        mf.quad(v3(x - dx, y, z - dz), v3(x + dx, y, z + dz), v3(x + dx, y + s * 1.4, z + dz), v3(x - dx, y + s * 1.4, z - dz), L["fern"],
                uvs=[(0, 0), (1, 0), (1, 1), (0, 1)], col=(0.85, 1.0, 0.8))


def plant_trees(M, grid, colliders, seed=11):
    """Trees wherever nothing else stands: denser outside the town, coconut and areca palms everywhere."""
    rnd = random.Random(seed)
    H = LY.HALF
    trees = []
    step = 9.0
    for gx in np.arange(-H + 20, H - 20, step):
        for gz in np.arange(-H + 20, H - 20, step):
            x = gx + rnd.uniform(-3.5, 3.5)
            z = gz + rnd.uniform(-3.5, 3.5)
            kind = LY.district(x, z)
            dens = {"core": 0.04, "town": 0.12, "outskirts": 0.22, "beach": 0.10, "park": 0.07, "none": 0.2}[kind]
            if rnd.random() > dens:
                continue
            if not grid.free_point(x, z, 2.5):
                continue
            y = float(LY.height(np.array([x]), np.array([z]))[0])
            if y < -0.2:
                continue
            r = rnd.random()
            if kind == "beach":
                t = "coconut"
            elif kind == "outskirts":
                t = "areca" if r < 0.3 else "coconut" if r < 0.5 else "bamboo" if r < 0.65 else "banana" if r < 0.78 else "broad"
            else:
                t = "coconut" if r < 0.35 else "areca" if r < 0.5 else "banana" if r < 0.65 else "broad" if r < 0.95 else "bamboo"
            trees.append((t, x, y, z))
            grid.mark_rect(x, z, 3.0, 3.0, (1, 0), "tree")
    # trees along the big roads and in the parks are placed by plant_avenues / the landmarks
    shade = []
    for t, x, y, z in trees:
        if t in ("coconut", "areca"):
            h = palm(M, x, y, z, rnd, t)
            colliders.append([x, y, z, 0.5, 4.0, 0.5, 0.0])
            shade.append((x, z, 2.2, 0.25))
        elif t == "banana":
            banana(M, x, y, z, rnd)
            shade.append((x, z, 1.5, 0.2))
        elif t == "bamboo":
            bamboo(M, x, y, z, rnd)
            colliders.append([x, y, z, 2.0, 6.0, 2.0, 0.0])
            shade.append((x, z, 2.5, 0.35))
        else:
            big = rnd.random() < 0.2
            h, r = broadleaf(M, x, y, z, rnd, big)
            colliders.append([x, y, z, 0.7, 3.5, 0.7, 0.0])
            shade.append((x, z, r, 0.45))
        if rnd.random() < 0.35:
            bush(M, x + rnd.uniform(-3, 3), y, z + rnd.uniform(-3, 3), rnd)
    edge_trees(M, rnd)
    return trees, shade


def edge_trees(M, rnd):
    """Groves just past the edge of the map (scenery only, no collision): the town fades into Tripura's
    village greenery instead of ending at an empty field."""
    H = LY.HALF
    step = 15.0
    n = 0
    for gx in np.arange(-H - 240, H + 240, step):
        for gz in np.arange(-H - 240, H + 240, step):
            x = float(gx + rnd.uniform(-5, 5))
            z = float(gz + rnd.uniform(-5, 5))
            out = max(abs(x), abs(z)) - H           # metres past the edge
            if out < 6 or out > 240:
                continue
            if z < LY.coast_z(x) + 45:               # beach and sea
                continue
            if rnd.random() > 0.42 - out * 0.0012:
                continue
            y = float(LY.height(np.array([x]), np.array([z]))[0])
            if y < -0.2:                             # river banks
                continue
            r = rnd.random()
            if r < 0.3:
                palm(M, x, y, z, rnd, "coconut")
            elif r < 0.42:
                palm(M, x, y, z, rnd, "areca")
            elif r < 0.55:
                bamboo(M, x, y, z, rnd)
            else:
                broadleaf(M, x, y, z, rnd, rnd.random() < 0.3)
            n += 1
    print("[city] edge groves: %d trees" % n)


# ================================================================================================= street furniture
def street_lamps(M, roads, colliders, meta, seed=5):
    rnd = random.Random(seed)
    lamps = []
    for c in roads.chains:
        if not c.get("surface") or c["cls"] == "C":
            continue
        rp, ys = c["surface"]
        w = LY.ROAD_W[c["cls"]]
        dense = resample(rp, 1.0)
        n = len(dense)
        spacing = 36
        for k, i in enumerate(range(6, n - 6, spacing)):
            p = np.asarray(dense[i], float)
            q = np.asarray(dense[i + 1], float)
            d = norm(q - p)
            left = np.array([-d[1], d[0]])
            side = 1 if k % 2 == 0 else -1
            base = p + left * side * (w / 2 + 0.6)
            y = float(np.interp(i, np.linspace(0, n - 1, len(ys)), ys)) + 0.16
            m = M.get(base[0], base[1], "world")
            m.cylinder(base[0], y, base[1], 0.1, 8.0, L["metal"], seg=6, r_top=0.07, top=False, col=(0.55, 0.57, 0.6), tile=(1, 2))
            arm_end = base - left * side * 1.8
            mid = (base + arm_end) / 2
            yaw = math.degrees(math.atan2(left[0], left[1]))
            m.box(mid[0], y + 7.8, mid[1], 0.08, 0.08, 1.9, L["metal"], yaw=yaw, col=(0.55, 0.57, 0.6))
            m.box(arm_end[0], y + 7.65, arm_end[1], 0.35, 0.18, 0.7, L["white"], yaw=yaw, col=(1.0, 0.95, 0.85), emis=1.0)
            colliders.append([float(base[0]), y, float(base[1]), 0.3, 8.0, 0.3, 0.0])
            lamps.append([round(float(arm_end[0]), 2), round(y + 7.55, 2), round(float(arm_end[1]), 2)])
    meta["lamps"] = lamps
    return lamps


def electric_poles(M, roads, colliders, seed=9):
    """Concrete electric poles with cross arms along the lanes (every Indian street has them)."""
    for c in roads.chains:
        if not c.get("surface") or c["cls"] != "C":
            continue
        rp, ys = c["surface"]
        w = LY.ROAD_W["C"]
        dense = resample(rp, 1.0)
        n = len(dense)
        for i in range(10, n - 10, 40):
            p = np.asarray(dense[i], float)
            q = np.asarray(dense[i + 1], float)
            d = norm(q - p)
            left = np.array([-d[1], d[0]])
            base = p + left * (w / 2 + LY.WALK_W["C"] + 0.3)
            y = float(np.interp(i, np.linspace(0, n - 1, len(ys)), ys))
            m = M.get(base[0], base[1], "world")
            yaw = math.degrees(math.atan2(d[0], d[1]))
            m.box(base[0], y, base[1], 0.22, 7.5, 0.22, L["concrete"], yaw=yaw, col=(0.75, 0.75, 0.72), tile=(1, 2))
            m.box(base[0], y + 6.8, base[1], 1.4, 0.1, 0.1, L["metal"], yaw=yaw + 90, col=(0.3, 0.3, 0.3))
            colliders.append([float(base[0]), y, float(base[1]), 0.3, 7.5, 0.3, 0.0])
