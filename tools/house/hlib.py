"""
Core of the procedural house generator: registries, procedural textures, materials, mesh primitives
and the exporter. Pure Python + numpy, so it runs both on its own (local preview) and inside Blender.

Coordinates are Blender's: x east, y north, z up, in metres. Faces are counter-clockwise seen from
the front. The exporter converts to Unity (x, z, y) and flips the triangle winding.
"""
import math
import os
import json
import struct
import zlib
import numpy as np

MATS = {}         # material name -> properties
OBJECTS = []      # emitted pieces of geometry
COLLIDERS = []    # static box colliders
DOORS = []        # hinged doors
LIGHTS = []       # lamps used for the light bake
ROOMS = []        # named volumes (patrol points, exposure, reflection probes)
VIEWS = []        # camera viewpoints (Blender renders and in-game test screenshots)
INFO = {}         # spawn points etc.
OUT = "out"
TEX = os.path.join(OUT, "Textures")


def log(*a):
    print("[HOUSE]", *a, flush=True)


def set_output(path):
    global OUT, TEX
    OUT = path
    TEX = os.path.join(path, "Textures")
    os.makedirs(TEX, exist_ok=True)


# =====================================================================================  PNG + noise

def write_png(path, rgb):
    a = (np.clip(np.asarray(rgb, np.float32), 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
    h, w = a.shape[:2]
    raw = np.zeros((h, w * 3 + 1), np.uint8)
    raw[:, 1:] = a.reshape(h, w * 3)

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    png = (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
           + chunk(b"IDAT", zlib.compress(raw.tobytes(), 6)) + chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def vnoise(n, cells, seed, octaves=1, persistence=0.5, stretch=(1.0, 1.0)):
    """Tileable value noise in [0, 1], shape (n, n). stretch=(sx, sy) gives elongated features."""
    out = np.zeros((n, n), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        cx = max(1, int(round(cells * stretch[0] * (2 ** o))))
        cy = max(1, int(round(cells * stretch[1] * (2 ** o))))
        rng = np.random.default_rng(seed * 7919 + o * 104729 + 17)
        g = rng.random((cy, cx)).astype(np.float32)
        fx = (np.arange(n) + 0.5) / n * cx
        fy = (np.arange(n) + 0.5) / n * cy
        x0 = np.floor(fx).astype(int)
        y0 = np.floor(fy).astype(int)
        tx = fx - x0
        ty = fy - y0
        tx = tx * tx * (3 - 2 * tx)
        ty = ty * ty * (3 - 2 * ty)
        x0 %= cx
        y0 %= cy
        x1 = (x0 + 1) % cx
        y1 = (y0 + 1) % cy
        a = g[np.ix_(y0, x0)] * (1 - tx[None, :]) + g[np.ix_(y0, x1)] * tx[None, :]
        b = g[np.ix_(y1, x0)] * (1 - tx[None, :]) + g[np.ix_(y1, x1)] * tx[None, :]
        out += (a * (1 - ty[:, None]) + b * ty[:, None]) * amp
        tot += amp
        amp *= persistence
    return out / tot


def coords(n):
    v = (np.arange(n) + 0.5) / n
    return np.meshgrid(v, v)          # u = column, v = row (row 0 is the top of the image)


def height_to_normal(h, strength):
    du = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5 * strength
    dv = -(np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5 * strength
    nrm = np.stack([-du, -dv, np.ones_like(h)], axis=-1)
    nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
    return nrm * 0.5 + 0.5


def lines(t, count, half_px, n):
    """1 on thin lines at multiples of 1/count of the texture, 0 elsewhere (anti-aliased)."""
    p = (t * count) % 1.0
    d = np.minimum(p, 1.0 - p) * n / count
    return np.clip(half_px + 0.5 - d, 0.0, 1.0)


def col(c):
    return np.asarray(c, np.float32)[None, None, :]


def save_tex(name, rgb, height=None, strength=2.0):
    write_png(os.path.join(TEX, name + ".png"), rgb)
    nname = None
    if height is not None:
        nname = name + "_n"
        write_png(os.path.join(TEX, nname + ".png"), height_to_normal(height.astype(np.float32), strength))
    return (name, nname)


# =====================================================================================  textures

def tex_paint(name, color, n=256, seed=1, amount=0.035):
    g = vnoise(n, 4, seed, 4) * 0.7 + vnoise(n, 48, seed + 1, 2) * 0.3
    rgb = col(color) * (1.0 + (g[..., None] - 0.5) * amount * 2)
    return save_tex(name, rgb, vnoise(n, 64, seed + 2, 2), 0.6)


def tex_render(name, color, n=512, seed=3):
    big = vnoise(n, 3, seed, 4)
    grain = vnoise(n, 96, seed + 1, 2)
    stain = np.clip((vnoise(n, 2, seed + 2, 3) - 0.55) * 2.5, 0, 1)
    g = 1.0 + (big - 0.5) * 0.08 + (grain - 0.5) * 0.08 - stain * 0.06
    return save_tex(name, col(color) * g[..., None], grain * 0.8 + big * 0.2, 1.5)


def marble_field(n, seed, scale=2.2, angle=0.6):
    u, v = coords(n)
    t = vnoise(n, 3, seed, 6, 0.55)
    t2 = vnoise(n, 6, seed + 1, 5, 0.55)
    s = np.sin((u * scale + v * scale * angle + t * 4.2) * math.pi)
    veins = np.exp(-np.abs(s) * 10.0)
    s2 = np.sin((u * scale * 3.1 - v * scale * 1.7 + t2 * 6.0) * math.pi)
    fine = np.exp(-np.abs(s2) * 26.0) * 0.6
    cloud = vnoise(n, 4, seed + 2, 5)
    return np.clip(veins + fine, 0, 1), cloud


def tex_marble_tiles(name, base, vein, tiles=2, n=1024, seed=11, grout=(0.80, 0.79, 0.77), grout_px=1.2, vein_amount=0.75):
    big = 2 * n
    veins, cloud = marble_field(big, seed)
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n, 3), np.float32)
    t = n // tiles
    for j in range(tiles):
        for i in range(tiles):
            ox, oy = rng.integers(0, big - t, 2)
            vv = veins[oy:oy + t, ox:ox + t]
            cc = cloud[oy:oy + t, ox:ox + t]
            if rng.random() < 0.5:
                vv, cc = vv.T, cc.T
            shade = 1.0 + (rng.random() - 0.5) * 0.03
            w = (vv * vein_amount)[..., None]
            tile = (col(base) * (0.975 + (cc[..., None] - 0.5) * 0.06)) * (1 - w) + col(vein) * w
            out[j * t:(j + 1) * t, i * t:(i + 1) * t] = tile * shade
    u, v = coords(n)
    g = np.maximum(lines(u, tiles, grout_px, n), lines(v, tiles, grout_px, n))[..., None]
    out = out * (1 - g) + col(grout) * g
    return save_tex(name, out, 1.0 - g[..., 0], 2.5)


def tex_slab(name, base, vein, n=1024, seed=21, vein_amount=0.8, scale=1.6):
    veins, cloud = marble_field(n, seed, scale=scale, angle=0.35)
    w = (veins * vein_amount)[..., None]
    rgb = (col(base) * (0.98 + (cloud[..., None] - 0.5) * 0.05)) * (1 - w) + col(vein) * w
    return save_tex(name, rgb)


def tex_planks(name, color, n=1024, planks=8, rows=2, seed=31, contrast=1.0, gap=(0.18, 0.13, 0.09)):
    u, v = coords(n)
    rng = np.random.default_rng(seed)
    c = np.floor(u * planks).astype(int)
    offs = rng.random(planks)
    vv = (v + offs[c]) % 1.0
    r = np.floor(vv * rows).astype(int)
    pid = c * 7 + r
    tone = rng.random(64)[pid % 64]
    hue = rng.random(64)[(pid * 3) % 64]
    lu = (u * planks) % 1.0
    warp = vnoise(n, 4, seed + 1, 3, stretch=(2.0, 0.5))
    rings = np.sin((lu * 6.0 + warp * 5.0 + pid * 1.37) * math.pi) * 0.5 + 0.5
    fibre = vnoise(n, 48, seed + 2, 2, stretch=(4.0, 0.12))
    knots = np.clip((vnoise(n, 10, seed + 3, 2) - 0.8) * 6, 0, 1) * contrast
    g = 0.5 + (tone - 0.5) * 0.22 * contrast + (rings - 0.5) * 0.14 * contrast + (fibre - 0.5) * 0.16 - knots * 0.2
    base = col(color) * (1 + (hue[..., None] - 0.5) * np.array([0.06, 0.02, -0.04], np.float32))
    rgb = np.clip(base * 2.0 * g[..., None], 0, 1)
    gu = lines(u, planks, 0.9, n)
    fv = (vv * rows) % 1.0
    gv = np.clip(1.0 - np.minimum(fv, 1 - fv) * n / rows, 0, 1)
    gl = np.maximum(gu, gv)[..., None]
    rgb = rgb * (1 - gl) + col(gap) * gl
    return save_tex(name, rgb, (1 - gl[..., 0]) + fibre * 0.08, 3.0)


def tex_veneer(name, color, n=512, seed=41, vertical=True, contrast=1.0):
    u, v = coords(n)
    a = u if vertical else v
    st = (3.0, 0.25) if vertical else (0.25, 3.0)
    warp = vnoise(n, 3, seed, 4, stretch=st)
    rings = np.sin((a * 14 + warp * 5.5) * math.pi) * 0.5 + 0.5
    fibre = vnoise(n, 64, seed + 1, 2, stretch=((4.0, 0.1) if vertical else (0.1, 4.0)))
    big = vnoise(n, 2, seed + 2, 2)
    g = 0.5 + (rings - 0.5) * 0.16 * contrast + (fibre - 0.5) * 0.14 + (big - 0.5) * 0.08
    return save_tex(name, np.clip(col(color) * 2.0 * g[..., None], 0, 1), fibre * 0.3 + rings * 0.1, 1.5)


def tex_fabric(name, color, n=512, seed=51, weave=128, heather=0.08):
    u, v = coords(n)
    wa = np.sin(u * weave * 2 * math.pi) * 0.5 + 0.5
    wb = np.sin(v * weave * 2 * math.pi) * 0.5 + 0.5
    chk = (np.floor(u * weave) + np.floor(v * weave)) % 2
    w = np.where(chk > 0, wa, wb)
    fuzz = vnoise(n, 96, seed, 2)
    big = vnoise(n, 3, seed + 1, 3)
    g = 1.0 + (w - 0.5) * 0.1 + (fuzz - 0.5) * heather * 2 + (big - 0.5) * 0.05
    return save_tex(name, np.clip(col(color) * g[..., None], 0, 1), w * 0.6 + fuzz * 0.4, 2.0)


def tex_brushed(name, color, n=256, seed=61):
    st = vnoise(n, 2, seed, 3, stretch=(0.04, 48))
    g = 1.0 + (st - 0.5) * 0.12
    return save_tex(name, np.clip(col(color) * g[..., None], 0, 1))


def tex_ledgestone(name, n=1024, rows=12, seed=71):
    u, v = coords(n)
    rng = np.random.default_rng(seed)
    r = np.floor(v * rows).astype(int)
    lv = (v * rows) % 1.0
    out = np.zeros((n, n, 3), np.float32)
    height = np.zeros((n, n), np.float32)
    noise = vnoise(n, 24, seed + 1, 4)
    for row in range(rows):
        mask_r = r == row
        cuts = np.sort(rng.random(int(rng.integers(3, 6))))
        uu = (u + rng.random()) % 1.0
        sid = np.searchsorted(cuts, uu)                     # 0..len(cuts)
        k = len(cuts)
        sid = np.where(sid >= k, 0, sid)                    # the last piece wraps onto the first stone
        tone = rng.random(k) * 0.5 + 0.35
        warm = rng.random(k)
        depth = rng.random(k)
        t = tone[sid]
        base = np.stack([t * (0.96 + warm[sid] * 0.1), t * 0.93, t * (0.86 - warm[sid] * 0.06)], -1)
        dist_cut = np.min(np.abs(uu[..., None] - cuts[None, None, :]), axis=-1)
        dist_cut = np.minimum(dist_cut, np.min(np.abs(uu[..., None] - 1.0 - cuts[None, None, :]), axis=-1))
        dist_cut = np.minimum(dist_cut, np.min(np.abs(uu[..., None] + 1.0 - cuts[None, None, :]), axis=-1))
        du = dist_cut * n
        dv = np.minimum(lv, 1 - lv) * n / rows
        joint = np.clip(1.0 - np.minimum(du, dv) / 3.0, 0, 1)
        stone = base * (0.85 + noise[..., None] * 0.3) * (1 - joint[..., None] * 0.8)
        out = np.where(mask_r[..., None], stone, out)
        height = np.where(mask_r, (1 - joint) * (0.6 + depth[sid] * 0.4) + noise * 0.15, height)
    return save_tex(name, out, height, 5.0)


def tex_pavers(name, color, n=1024, rows=8, cols=4, seed=81):
    u, v = coords(n)
    rng = np.random.default_rng(seed)
    r = np.floor(v * rows).astype(int)
    uu = (u + (r % 2) * 0.5 / cols) % 1.0
    c = np.floor(uu * cols).astype(int)
    tone = rng.random((rows + 1, cols + 1))[r, c]
    noise = vnoise(n, 32, seed + 1, 3)
    g = 0.86 + tone * 0.22 + (noise - 0.5) * 0.14
    j = np.maximum(lines(uu, cols, 1.8, n), lines(v, rows, 1.8, n))[..., None]
    rgb = col(color) * g[..., None] * (1 - j * 0.55)
    return save_tex(name, rgb, (1 - j[..., 0]) * 0.8 + noise * 0.2, 3.0)


def tex_grass(name, n=1024, seed=91):
    a = vnoise(n, 5, seed, 4)
    b = vnoise(n, 120, seed + 1, 2)
    blades = vnoise(n, 260, seed + 2, 1, stretch=(1, 3))
    g = a * 0.45 + b * 0.3 + blades * 0.25
    rgb = np.stack([0.16 + g * 0.16, 0.30 + g * 0.22, 0.08 + g * 0.08], -1)
    dry = np.clip((vnoise(n, 3, seed + 3, 3) - 0.6) * 2.5, 0, 1)[..., None] * 0.7
    rgb = rgb * (1 - dry) + np.array([0.40, 0.39, 0.21], np.float32) * (0.75 + g[..., None] * 0.4) * dry
    return save_tex(name, rgb, blades * 0.6 + b * 0.4, 3.0)


def tex_boards(name, color, n=512, boards=6, seed=101, gap_px=1.5, horizontal=False):
    u, v = coords(n)
    rng = np.random.default_rng(seed)
    b = np.floor(u * boards).astype(int)
    tone = rng.random(boards + 1)[b]
    warp = vnoise(n, 2, seed + 1, 4, stretch=(0.3, 5))
    grain = np.sin((v * 30 + warp * 5 + b * 2.3) * math.pi) * 0.5 + 0.5
    g = 0.5 + (tone - 0.5) * 0.18 + (grain - 0.5) * 0.12 + (warp - 0.5) * 0.08
    gap = lines(u, boards, gap_px, n)[..., None]
    rgb = np.clip(col(color) * 2.0 * g[..., None], 0, 1) * (1 - gap * 0.85)
    h = 1 - gap[..., 0]
    if horizontal:
        rgb = np.ascontiguousarray(rgb.transpose(1, 0, 2))
        h = np.ascontiguousarray(h.T)
    return save_tex(name, rgb, h, 4.0)


def tex_foliage(name, color, n=512, seed=171):
    a = vnoise(n, 40, seed, 3)
    b = vnoise(n, 90, seed + 1, 2)
    leaves = np.clip((b - 0.45) * 3, 0, 1)
    g = 0.55 + (a - 0.5) * 0.5 + leaves * 0.35
    rgb = col(color) * g[..., None] * np.array([1.0, 1.05, 0.9], np.float32)
    return save_tex(name, np.clip(rgb, 0, 1), a * 0.5 + leaves * 0.5, 3.0)


def tex_subway(name, color, n=512, cols=4, rows=8, seed=111):
    u, v = coords(n)
    r = np.floor(v * rows).astype(int)
    uu = (u + (r % 2) * 0.5 / cols) % 1.0
    c = np.floor(uu * cols).astype(int)
    rng = np.random.default_rng(seed)
    tone = rng.random((rows + 1, cols + 1))[r, c] * 0.04
    g = 0.98 + tone + (vnoise(n, 16, seed + 1, 2) - 0.5) * 0.03
    j = np.maximum(lines(uu, cols, 1.4, n), lines(v, rows, 1.4, n))[..., None]
    rgb = col(color) * g[..., None] * (1 - j) + 0.66 * j
    lu = (uu * cols) % 1.0
    lv = (v * rows) % 1.0
    bevel = np.minimum(np.minimum(lu, 1 - lu) * n / cols, np.minimum(lv, 1 - lv) * n / rows)
    return save_tex(name, rgb, np.clip(bevel / 5.0, 0, 1), 3.0)


def tex_concrete(name, color, n=512, seed=121, rough=1.0):
    a = vnoise(n, 5, seed, 5)
    b = vnoise(n, 90, seed + 1, 2)
    pores = (vnoise(n, 180, seed + 2, 1) > 0.84).astype(np.float32) * 0.12
    g = 1.0 + ((a - 0.5) * 0.18 + (b - 0.5) * 0.1) * rough - pores
    return save_tex(name, col(color) * g[..., None], a * 0.5 + b * 0.5 - pores, 1.5)


def tex_asphalt(name, n=512, seed=131):
    a = vnoise(n, 6, seed, 4)
    b = vnoise(n, 200, seed + 1, 1)
    stones = (b > 0.7).astype(np.float32) * (b - 0.7) * 1.6
    g = 0.2 + (a - 0.5) * 0.05 + stones * 0.25 + (vnoise(n, 120, seed + 2, 1) - 0.5) * 0.06
    rgb = np.stack([g, g * 0.99, g * 0.97], -1)
    return save_tex(name, rgb, b, 2.0)


def tex_rug(name, n=512, seed=141):
    u, v = coords(n)
    border = np.minimum(np.minimum(u, 1 - u), np.minimum(v, 1 - v))
    lattice = np.abs(((u * 5) % 1.0) - 0.5) + np.abs(((v * 3) % 1.0) - 0.5)
    pat = np.where(border < 0.05, 0.0, np.where(border < 0.065, 1.0, np.where(np.abs(lattice - 0.42) < 0.035, 0.8, 0.12)))
    fuzz = vnoise(n, 128, seed, 2)
    big = vnoise(n, 4, seed + 1, 3)
    c1 = col((0.80, 0.77, 0.71))
    c2 = col((0.31, 0.33, 0.36))
    rgb = (c1 * (1 - pat[..., None]) + c2 * pat[..., None]) * (0.9 + fuzz[..., None] * 0.15 + (big[..., None] - 0.5) * 0.06)
    return save_tex(name, rgb, fuzz, 2.0)


def tex_art(name, palette, n=512, seed=151, style=0):
    u, v = coords(n)
    rng = np.random.default_rng(seed)
    pal = [np.asarray(c, np.float32) for c in palette]
    rgb = np.zeros((n, n, 3), np.float32) + pal[0]
    if style == 0:      # soft colour fields
        for k in range(1, len(pal)):
            cx, cy = rng.random(2)
            rad = 0.15 + rng.random() * 0.3
            d = np.sqrt((u - cx) ** 2 + ((v - cy) * 1.2) ** 2)
            w = np.clip(1.0 - d / rad, 0, 1) ** 1.5
            w = w * (0.75 + vnoise(n, 6, seed + k, 3) * 0.5)
            rgb = rgb * (1 - w[..., None]) + pal[k] * w[..., None]
    elif style == 1:    # horizon bands
        warp = vnoise(n, 3, seed, 4)
        bands = np.clip(v + (warp - 0.5) * 0.12, 0, 0.999) * (len(pal) - 1)
        i0 = np.floor(bands).astype(int)
        f = (bands - i0)[..., None]
        f = f * f * (3 - 2 * f)
        P = np.stack(pal)
        rgb = P[i0] * (1 - f) + P[np.minimum(i0 + 1, len(pal) - 1)] * f
    else:               # brush strokes
        for k in range(18):
            cx, cy = rng.random(2)
            ang = rng.random() * math.pi
            length, width = 0.2 + rng.random() * 0.4, 0.015 + rng.random() * 0.05
            dx, dy = u - cx, v - cy
            a = dx * math.cos(ang) + dy * math.sin(ang)
            b = -dx * math.sin(ang) + dy * math.cos(ang)
            w = np.clip(1 - np.abs(a) / length, 0, 1) * np.clip(1 - np.abs(b) / width, 0, 1)
            w = np.clip(w * 3, 0, 1) * (0.6 + vnoise(n, 40, seed + k, 1) * 0.4)
            rgb = rgb * (1 - w[..., None]) + pal[1 + k % (len(pal) - 1)] * w[..., None]
    grain = vnoise(n, 160, seed + 99, 1)
    rgb = rgb * (0.96 + grain[..., None] * 0.06)
    return save_tex(name, np.clip(rgb, 0, 1))


def tex_leaf(name, color, n=256, seed=161):
    u, v = coords(n)
    vein = np.exp(-np.abs(u - 0.5) * 120) * 0.25
    side = np.exp(-np.abs(np.sin((v * 9 + np.abs(u - 0.5) * 6) * math.pi)) * 18) * 0.1
    g = 1.0 + (vnoise(n, 12, seed, 3) - 0.5) * 0.15 + vein + side
    return save_tex(name, np.clip(col(color) * g[..., None], 0, 1))


# =====================================================================================  materials

def material(name, color=(0.8, 0.8, 0.8), tex=None, rough=0.6, metal=0.0, tile=1.0, normal_strength=1.0,
             emission=None, emission_strength=0.0, alpha=1.0, kind="opaque", baked=True):
    """Registers a material once; returns its name. Colours are sRGB. tile = metres per texture repeat."""
    if name not in MATS:
        MATS[name] = dict(name=name, color=[float(c) for c in color],
                          albedo=tex[0] if tex else None, normal=tex[1] if tex else None,
                          smoothness=float(1.0 - rough), metallic=float(metal), tile=float(tile),
                          normalStrength=float(normal_strength),
                          emission=[float(c) for c in (emission if emission is not None else (0, 0, 0))],
                          emissionStrength=float(emission_strength), alpha=float(alpha), kind=kind, baked=bool(baked))
    return name


# =====================================================================================  geometry

def newell(p):
    q = np.roll(p, -1, axis=0)
    return np.array([np.sum((p[:, 1] - q[:, 1]) * (p[:, 2] + q[:, 2])),
                     np.sum((p[:, 2] - q[:, 2]) * (p[:, 0] + q[:, 0])),
                     np.sum((p[:, 0] - q[:, 0]) * (p[:, 1] + q[:, 1]))])


def uv_project(p, n):
    """Box projection in metres, oriented so textures read upright and unmirrored from the front."""
    ax = int(np.argmax(np.abs(n)))
    s = 1.0 if n[ax] >= 0 else -1.0
    if ax == 2:
        return np.stack([p[:, 0] * s, p[:, 1]], 1)
    if ax == 0:
        return np.stack([p[:, 1] * s, p[:, 2]], 1)
    return np.stack([-p[:, 0] * s, p[:, 2]], 1)


def rotz(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def rotx(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def roty(deg):
    a = math.radians(deg)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


class Geo:
    """A bag of polygons (each with its material, optional per-corner normals and UVs) plus colliders."""

    def __init__(self):
        self.F = []
        self.boxes = []
        self.lights = []

    # ---------------------------------------------------------------- basics
    def face(self, pts, mat, nrm=None, uv=None):
        p = np.asarray(pts, float)
        if len(p) < 3:
            return
        n = newell(p)
        if np.dot(n, n) < 1e-14:
            return
        self.F.append([p, None if nrm is None else np.asarray(nrm, float), mat, None if uv is None else np.asarray(uv, float)])

    def grid(self, o, du, dv, mat, cell=None):
        o, du, dv = np.asarray(o, float), np.asarray(du, float), np.asarray(dv, float)
        nu = max(1, int(math.ceil(np.linalg.norm(du) / cell - 1e-6))) if cell else 1
        nv = max(1, int(math.ceil(np.linalg.norm(dv) / cell - 1e-6))) if cell else 1
        for j in range(nv):
            for i in range(nu):
                a = o + du * (i / nu) + dv * (j / nv)
                b = o + du * ((i + 1) / nu) + dv * (j / nv)
                c = o + du * ((i + 1) / nu) + dv * ((j + 1) / nv)
                d = o + du * (i / nu) + dv * ((j + 1) / nv)
                self.face((a, b, c, d), mat)

    def box(self, mn, mx, mat, cell=None, skip=()):
        """Axis-aligned box. mat is a material or a dict keyed px nx py ny pz nz (and 'default')."""
        x0, y0, z0 = mn
        x1, y1, z1 = mx
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        if dx <= 1e-6 or dy <= 1e-6 or dz <= 1e-6:
            return

        def m(k):
            return mat.get(k, mat.get("default")) if isinstance(mat, dict) else mat
        if "px" not in skip: self.grid((x1, y0, z0), (0, dy, 0), (0, 0, dz), m("px"), cell)
        if "nx" not in skip: self.grid((x0, y1, z0), (0, -dy, 0), (0, 0, dz), m("nx"), cell)
        if "py" not in skip: self.grid((x1, y1, z0), (-dx, 0, 0), (0, 0, dz), m("py"), cell)
        if "ny" not in skip: self.grid((x0, y0, z0), (dx, 0, 0), (0, 0, dz), m("ny"), cell)
        if "pz" not in skip: self.grid((x0, y0, z1), (dx, 0, 0), (0, dy, 0), m("pz"), cell)
        if "nz" not in skip: self.grid((x0, y1, z0), (dx, 0, 0), (0, -dy, 0), m("nz"), cell)

    def rbox(self, mn, mx, r, mat, seg=1, skip=(), bulge=0.0, div=1):
        """Box with rounded edges and corners (exact smooth normals). bulge puffs the faces out (cushions)."""
        mn = np.asarray(mn, float)
        mx = np.asarray(mx, float)
        size = mx - mn
        if np.min(size) <= 1e-6:
            return
        r = min(r, 0.499 * float(np.min(size)))
        if r < 1e-4:
            self.box(mn, mx, mat, skip=skip)
            return
        imn, imx = mn + r, mx - r
        tk = [math.tan(math.radians(45.0 * k / seg)) for k in range(seg + 1)]

        def axis(a, d):
            lo = [imn[a] - r * t for t in reversed(tk)]
            mid = [imn[a] + (imx[a] - imn[a]) * j / d for j in range(1, d)]
            hi = [imx[a] + r * t for t in tk]
            return lo + mid + hi

        names = {(0, 1): "px", (0, -1): "nx", (1, 1): "py", (1, -1): "ny", (2, 1): "pz", (2, -1): "nz"}
        for a in range(3):
            b, c = (a + 1) % 3, (a + 2) % 3
            for s in (1, -1):
                key = names[(a, s)]
                if key in skip:
                    continue
                fm = mat.get(key, mat.get("default")) if isinstance(mat, dict) else mat
                d = div if bulge > 0 else 1
                cb, cc = axis(b, d), axis(c, d)
                nb, nc = len(cb), len(cc)
                gb_, gc_ = np.meshgrid(np.array(cb), np.array(cc), indexing="ij")
                p = np.zeros((nb, nc, 3))
                p[..., a] = mx[a] if s > 0 else mn[a]
                p[..., b] = gb_
                p[..., c] = gc_
                q = np.clip(p, imn, imx)
                dd = p - q
                nrm = dd / np.linalg.norm(dd, axis=-1, keepdims=True)
                pos = q + nrm * r
                if bulge > 0:
                    hb = max(1e-6, (imx[b] - imn[b]) * 0.5)
                    hc = max(1e-6, (imx[c] - imn[c]) * 0.5)
                    u = (p[..., b] - (imx[b] + imn[b]) * 0.5) / hb
                    w = (p[..., c] - (imx[c] + imn[c]) * 0.5) / hc
                    inside = (np.abs(u) < 1) & (np.abs(w) < 1)
                    f = np.where(inside, (1 - u * u) * (1 - w * w), 0.0)
                    pos[..., a] += s * bulge * f
                    gb = np.where(inside, bulge * (-2 * u / hb) * (1 - w * w), 0.0)
                    gc = np.where(inside, bulge * (-2 * w / hc) * (1 - u * u), 0.0)
                    nn = np.zeros_like(nrm)
                    nn[..., a] = s
                    nn[..., b] = -gb
                    nn[..., c] = -gc
                    nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
                    nrm = np.where(inside[..., None], nn, nrm)
                ax_n = np.zeros(3)
                ax_n[a] = s
                for i in range(nb - 1):
                    for j in range(nc - 1):
                        idx = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                        if s < 0:
                            idx.reverse()
                        pts = np.array([pos[k] for k in idx])
                        if np.dot(newell(pts), newell(pts)) < 1e-14:
                            continue
                        self.F.append([pts, np.array([nrm[k] for k in idx]), fm, uv_project(pts, ax_n)])

    def cyl(self, c, r, h, mat, seg=24, top=True, bottom=True, r2=None, cap_mat=None):
        """Vertical cylinder (or cone when r2 is given) standing on centre c."""
        cx, cy, z0 = c
        r2 = r if r2 is None else r2
        angs = [2 * math.pi * i / seg for i in range(seg)]
        slope = (r - r2) / h if h > 0 else 0.0
        ring0 = [(cx + r * math.cos(t), cy + r * math.sin(t), z0) for t in angs]
        ring1 = [(cx + r2 * math.cos(t), cy + r2 * math.sin(t), z0 + h) for t in angs]
        nr = [np.array((math.cos(t), math.sin(t), slope)) / math.sqrt(1 + slope * slope) for t in angs]
        circ = 2 * math.pi * max(r, r2)
        for i in range(seg):
            j = (i + 1) % seg
            u0, u1 = circ * i / seg, circ * (i + 1) / seg
            if r2 < 1e-6:
                self.face((ring0[i], ring0[j], ring1[i]), mat, (nr[i], nr[j], nr[i]))
            else:
                self.face((ring0[i], ring0[j], ring1[j], ring1[i]), mat, (nr[i], nr[j], nr[j], nr[i]),
                          ((u0, z0), (u1, z0), (u1, z0 + h), (u0, z0 + h)))
        if bottom and r > 1e-5:
            self.face(list(reversed(ring0)), cap_mat or mat)
        if top and r2 > 1e-5:
            self.face(ring1, cap_mat or mat)

    def lathe(self, c, profile, mat, seg=28, top=False, bottom=False, crease=40.0):
        """Revolves [(radius, z), ...] (bottom to top) around a vertical axis through c."""
        cx, cy, cz = c
        prof = [(float(r), float(z)) for r, z in profile]
        k = len(prof)
        segn = []
        for i in range(k - 1):
            dr, dz = prof[i + 1][0] - prof[i][0], prof[i + 1][1] - prof[i][1]
            ln = math.hypot(dr, dz) or 1.0
            segn.append((dz / ln, -dr / ln))        # outward normal in (radial, z)
        cosc = math.cos(math.radians(crease))

        def vn(i, s):
            n0 = segn[s]
            other = s - 1 if i == s else s + 1
            if 0 <= other < len(segn):
                n1 = segn[other]
                if n0[0] * n1[0] + n0[1] * n1[1] > cosc:
                    a = (n0[0] + n1[0], n0[1] + n1[1])
                    ln = math.hypot(*a) or 1.0
                    return (a[0] / ln, a[1] / ln)
            return n0
        angs = [2 * math.pi * i / seg for i in range(seg)]
        length = 0.0
        for s in range(k - 1):
            (ra, za), (rb, zb) = prof[s], prof[s + 1]
            if abs(ra) < 1e-6 and abs(rb) < 1e-6:
                continue
            na, nb = vn(s, s), vn(s + 1, s)
            seglen = math.hypot(rb - ra, zb - za)
            for i in range(seg):
                j = (i + 1) % seg
                ti, tj = angs[i], angs[j]
                pa_i = (cx + ra * math.cos(ti), cy + ra * math.sin(ti), cz + za)
                pa_j = (cx + ra * math.cos(tj), cy + ra * math.sin(tj), cz + za)
                pb_j = (cx + rb * math.cos(tj), cy + rb * math.sin(tj), cz + zb)
                pb_i = (cx + rb * math.cos(ti), cy + rb * math.sin(ti), cz + zb)
                nrm = [(na[0] * math.cos(ti), na[0] * math.sin(ti), na[1]), (na[0] * math.cos(tj), na[0] * math.sin(tj), na[1]),
                       (nb[0] * math.cos(tj), nb[0] * math.sin(tj), nb[1]), (nb[0] * math.cos(ti), nb[0] * math.sin(ti), nb[1])]
                circ = 2 * math.pi * max(ra, rb, 0.01)
                u0, u1 = circ * i / seg, circ * (i + 1) / seg
                uv = ((u0, length), (u1, length), (u1, length + seglen), (u0, length + seglen))
                if abs(ra) < 1e-6:
                    self.face((pa_i, pb_j, pb_i), mat, (nrm[0], nrm[2], nrm[3]), (uv[0], uv[2], uv[3]))
                elif abs(rb) < 1e-6:
                    self.face((pa_i, pa_j, pb_i), mat, (nrm[0], nrm[1], nrm[3]), (uv[0], uv[1], uv[3]))
                else:
                    self.face((pa_i, pa_j, pb_j, pb_i), mat, nrm, uv)
            length += seglen
        if bottom and prof[0][0] > 1e-5:
            r, z = prof[0]
            self.face([(cx + r * math.cos(t), cy + r * math.sin(t), cz + z) for t in reversed(angs)], mat)
        if top and prof[-1][0] > 1e-5:
            r, z = prof[-1]
            self.face([(cx + r * math.cos(t), cy + r * math.sin(t), cz + z) for t in angs], mat)

    def tube(self, path, r, mat, seg=12, caps=True):
        """Sweeps a circle of radius r along a polyline (smooth normals)."""
        P = [np.asarray(p, float) for p in path]
        k = len(P)
        if k < 2:
            return
        T = []
        for i in range(k):
            a = P[min(i + 1, k - 1)] - P[max(i - 1, 0)]
            T.append(a / (np.linalg.norm(a) or 1.0))
        ref = np.array((0.0, 0.0, 1.0)) if abs(T[0][2]) < 0.9 else np.array((1.0, 0.0, 0.0))
        Nv = np.cross(ref, T[0])
        Nv /= np.linalg.norm(Nv)
        frames = []
        for i in range(k):
            if i > 0:
                Nv = Nv - T[i] * np.dot(Nv, T[i])
                ln = np.linalg.norm(Nv)
                if ln < 1e-9:
                    Nv = np.cross(ref, T[i])
                    ln = np.linalg.norm(Nv) or 1.0
                Nv = Nv / ln
            frames.append((Nv.copy(), np.cross(T[i], Nv)))
        rings, nrms = [], []
        for i in range(k):
            Nn, B = frames[i]
            ring, nr = [], []
            for s in range(seg):
                t = 2 * math.pi * s / seg
                d = Nn * math.cos(t) + B * math.sin(t)
                ring.append(P[i] + d * r)
                nr.append(d)
            rings.append(ring)
            nrms.append(nr)
        dist = 0.0
        for i in range(k - 1):
            seglen = float(np.linalg.norm(P[i + 1] - P[i]))
            for s in range(seg):
                t = (s + 1) % seg
                u0, u1 = 2 * math.pi * r * s / seg, 2 * math.pi * r * (s + 1) / seg
                self.face((rings[i][s], rings[i + 1][s], rings[i + 1][t], rings[i][t]), mat,
                          (nrms[i][s], nrms[i + 1][s], nrms[i + 1][t], nrms[i][t]),
                          ((dist, u0), (dist + seglen, u0), (dist + seglen, u1), (dist, u1)))
            dist += seglen
        if caps:
            self.face(list(reversed(rings[0])), mat)
            self.face(rings[-1], mat)

    def sphere(self, c, r, mat, seg=16, rings=8, scale=(1.0, 1.0, 1.0), zmin=-1.0):
        c = np.asarray(c, float)
        sc = np.asarray(scale, float)
        V, Nn = [], []
        for i in range(rings + 1):
            th = math.pi * i / rings
            row, nrow = [], []
            for j in range(seg):
                ph = 2 * math.pi * j / seg
                d = np.array((math.sin(th) * math.cos(ph), math.sin(th) * math.sin(ph), -math.cos(th)))
                row.append(c + d * r * sc)
                n = d / sc
                nrow.append(n / np.linalg.norm(n))
            V.append(row)
            Nn.append(nrow)
        for i in range(rings):
            if -math.cos(math.pi * (i + 1) / rings) < zmin:
                continue
            for j in range(seg):
                k = (j + 1) % seg
                if i == 0:
                    self.face((V[0][j], V[1][k], V[1][j]), mat, (Nn[0][j], Nn[1][k], Nn[1][j]))
                elif i == rings - 1:
                    self.face((V[i][j], V[i][k], V[i + 1][j]), mat, (Nn[i][j], Nn[i][k], Nn[i + 1][j]))
                else:
                    self.face((V[i][j], V[i][k], V[i + 1][k], V[i + 1][j]), mat, (Nn[i][j], Nn[i][k], Nn[i + 1][k], Nn[i + 1][j]))

    def surface(self, fn, nu, nv, mat, two_sided=False, thickness=0.0):
        """Parametric surface fn(u, v) -> point, u, v in [0, 1]; normals from finite differences."""
        P = np.array([[fn(i / nu, j / nv) for j in range(nv + 1)] for i in range(nu + 1)], float)
        du = np.gradient(P, axis=0)
        dv = np.gradient(P, axis=1)
        Nn = np.cross(du, dv)
        Nn /= np.maximum(np.linalg.norm(Nn, axis=-1, keepdims=True), 1e-12)
        for side in ((1, -1) if two_sided else (1,)):
            Q = P + Nn * thickness * 0.5 * side if thickness > 0 else P
            for i in range(nu):
                for j in range(nv):
                    idx = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
                    if side < 0:
                        idx.reverse()
                    self.face([Q[a] for a in idx], mat, [Nn[a] * side for a in idx])

    def prism(self, poly, z0, z1, mat, top=True, bottom=True, side_mat=None):
        """Vertical extrusion of a convex CCW polygon [(x, y), ...]."""
        k = len(poly)
        for i in range(k):
            (xa, ya), (xb, yb) = poly[i], poly[(i + 1) % k]
            self.face(((xa, ya, z0), (xb, yb, z0), (xb, yb, z1), (xa, ya, z1)), side_mat or mat)
        if top:
            self.face([(x, y, z1) for x, y in poly], mat)
        if bottom:
            self.face([(x, y, z0) for x, y in reversed(poly)], mat)

    # ---------------------------------------------------------------- composition
    def collide(self, mn, mx, layer=0, rot=None):
        mn, mx = np.asarray(mn, float), np.asarray(mx, float)
        self.boxes.append(((mn + mx) * 0.5, mx - mn, None if rot is None else np.asarray(rot, float), layer))

    def collide_obb(self, center, size, rot, layer=0):
        self.boxes.append((np.asarray(center, float), np.asarray(size, float), np.asarray(rot, float), layer))

    def add(self, other, yaw=0.0, offset=(0.0, 0.0, 0.0), boxes=True):
        R = rotz(yaw) if yaw else None
        o = np.asarray(offset, float)
        for p, n, m, uv in other.F:
            if R is not None:
                if uv is None:                      # keep the texture aligned with the object, not the world
                    fn = newell(p)
                    uv = uv_project(p, fn / np.linalg.norm(fn))
                p = p @ R.T
                n = None if n is None else n @ R.T
            self.F.append([p + o, n, m, uv])
        if boxes:
            for c, s, rot, layer in other.boxes:
                if R is not None:
                    c = R @ c
                    rot = R if rot is None else R @ rot
                self.boxes.append((c + o, s, rot, layer))
        for l in other.lights:
            l = dict(l)
            p = np.asarray(l["pos"], float)
            l["pos"] = tuple((R @ p if R is not None else p) + o)
            if "dir" in l and R is not None:
                l["dir"] = tuple(R @ np.asarray(l["dir"], float))
            self.lights.append(l)
        return self

    def transform(self, M, offset=(0.0, 0.0, 0.0)):
        """Applies a linear map (e.g. a non-uniform scale) in place; normals use the inverse transpose."""
        M = np.asarray(M, float)
        Nm = np.linalg.inv(M).T
        o = np.asarray(offset, float)
        for f in self.F:
            if f[3] is None:
                fn = newell(f[0])
                f[3] = uv_project(f[0], fn / np.linalg.norm(fn))
            f[0] = f[0] @ M.T + o
            if f[1] is not None:
                n = f[1] @ Nm.T
                f[1] = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            if np.linalg.det(M) < 0:
                f[0] = f[0][::-1].copy()
                if f[1] is not None:
                    f[1] = f[1][::-1].copy()
                f[3] = f[3][::-1].copy()
        return self

    def light(self, pos, power, color=(1.0, 0.85, 0.66), radius=0.04, kind="point", **kw):
        d = dict(pos=tuple(pos), power=power, color=color, radius=radius, kind=kind)
        d.update(kw)
        self.lights.append(d)


def place(dst, item, x=0.0, y=0.0, z=0.0, yaw=0.0):
    dst.add(item, yaw, (x, y, z))


def emit(geo, name, group, bake=True, dynamic=False, origin=None, render=True, collide=True):
    LIGHTS.extend(geo.lights)
    if collide:
        COLLIDERS.extend(geo.boxes)
    if geo.F:
        OBJECTS.append(dict(name=name, group=group, geo=geo, bake=bake, dynamic=dynamic,
                            origin=None if origin is None else np.asarray(origin, float), render=render))


def round_path(points, radius, steps=4):
    """Rounds the corners of a polyline (quadratic Bezier fillets)."""
    P = [np.asarray(p, float) for p in points]
    if len(P) < 3:
        return P
    out = [P[0]]
    for i in range(1, len(P) - 1):
        a, b, c = P[i - 1], P[i], P[i + 1]
        da, dc = a - b, c - b
        la, lc = np.linalg.norm(da), np.linalg.norm(dc)
        rr = min(radius, la * 0.5, lc * 0.5)
        p0 = b + da / la * rr
        p2 = b + dc / lc * rr
        for k in range(steps + 1):
            t = k / steps
            out.append((1 - t) ** 2 * p0 + 2 * (1 - t) * t * b + t * t * p2)
    out.append(P[-1])
    return out


# =====================================================================================  export

def to_unity(v):
    v = np.asarray(v, float)
    return v[..., [0, 2, 1]]


def quat_from_matrix(m):
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        w, x, y, z = 0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = math.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w, x, y, z = (m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = math.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w, x, y, z = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = math.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w, x, y, z = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s
    return [x, y, z, w]


def unity_rotation(rot):
    """Blender rotation matrix -> Unity quaternion [x, y, z, w] (Unity rotations are left-handed)."""
    if rot is None:
        return [0.0, 0.0, 0.0, 1.0]
    S = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])
    m = S @ rot @ S
    x, y, z, w = quat_from_matrix(m)
    # a proper rotation matrix in Unity's coordinates; Unity's quaternion maths is the standard one
    return [x, y, z, w]


def unity_yaw(direction):
    d = np.asarray(direction, float)
    return math.degrees(math.atan2(d[0], d[1]))


def merged_objects():
    """Static pieces of the same group become one object; dynamic ones stay separate."""
    groups, order, out = {}, [], []
    for o in OBJECTS:
        if o["dynamic"] or not o["bake"] or not o["render"]:
            out.append(o)
            continue
        key = o["group"].split("_")[0] if o["group"].startswith(("GF_", "FF_")) else ("Exterior" if o["group"] in ("Garden", "Ground", "Roof") else o["group"])
        if key not in groups:
            g = dict(name=key, group=key, geo=Geo(), bake=True, dynamic=False, origin=None, render=True)
            groups[key] = g
            order.append(g)
        groups[key]["geo"].F.extend(o["geo"].F)
    return order + out


def object_arrays(geo):
    """Corner arrays in a fixed order (shared by the Blender backend and the exporter)."""
    F = geo.F
    sizes = np.array([len(f[0]) for f in F], np.int32)
    total = int(sizes.sum())
    P = np.empty((total, 3))
    N = np.empty((total, 3))
    UV = np.empty((total, 2))
    mats, mindex = [], {}
    fm = np.empty(len(F), np.int32)
    off = 0
    for i, (p, n, m, uv) in enumerate(F):
        k = len(p)
        fn = newell(p)
        fn = fn / np.linalg.norm(fn)
        P[off:off + k] = p
        if n is None:
            N[off:off + k] = fn
        else:
            ln = np.linalg.norm(n, axis=1, keepdims=True)
            N[off:off + k] = n / np.maximum(ln, 1e-12)
        UV[off:off + k] = uv if uv is not None else uv_project(p, fn)
        if m not in mindex:
            mindex[m] = len(mats)
            mats.append(m)
        fm[i] = mindex[m]
        off += k
    return P, N, UV, sizes, fm, mats


def triangulate(sizes):
    """Fan triangulation; returns (tri corner indices (T, 3), face index per triangle)."""
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    tris, faces = [], []
    for k in np.unique(sizes):
        sel = np.nonzero(sizes == k)[0]
        st = starts[sel]
        for i in range(1, k - 1):
            tris.append(np.stack([st, st + i, st + i + 1], 1))
            faces.append(sel)
    tri = np.concatenate(tris)
    fac = np.concatenate(faces)
    order = np.argsort(fac, kind="stable")
    return tri[order], fac[order]


def smooth_light(P, N, L, sizes, iterations=1, sigma=0.12):
    """Merges the bake samples of corners that share a position and normal, then an edge-preserving blur
    over the surface removes the remaining sampling noise."""
    key = np.concatenate([np.round(P * 500.0), np.round(N * 20.0)], 1).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    g = int(inv.max()) + 1
    cnt = np.bincount(inv, minlength=g).astype(float)
    acc = np.zeros((g, 3))
    np.add.at(acc, inv, L)
    val = acc / cnt[:, None]
    gn = np.zeros((g, 3))
    np.add.at(gn, inv, N)
    gn /= np.maximum(np.linalg.norm(gn, axis=1, keepdims=True), 1e-9)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    ea, eb = [], []
    for k in np.unique(sizes):
        st = starts[sizes == k]
        for i in range(k):
            ea.append(inv[st + i])
            eb.append(inv[st + (i + 1) % k])
    ea = np.concatenate(ea)
    eb = np.concatenate(eb)
    ok = (ea != eb) & (np.sum(gn[ea] * gn[eb], 1) > 0.9)
    ea, eb = ea[ok], eb[ok]
    pairs = np.unique(np.stack([np.minimum(ea, eb), np.maximum(ea, eb)], 1), axis=0)
    ea, eb = pairs[:, 0], pairs[:, 1]
    for _ in range(iterations):
        la = val[ea].mean(1)
        lb = val[eb].mean(1)
        rel = (la - lb) / (np.maximum(la + lb, 1e-4) * sigma)
        w = np.exp(-rel * rel)
        acc = val.copy()
        wsum = np.ones(g)
        np.add.at(acc, ea, val[eb] * w[:, None])
        np.add.at(acc, eb, val[ea] * w[:, None])
        np.add.at(wsum, ea, w)
        np.add.at(wsum, eb, w)
        val = acc / wsum[:, None]
    return val[inv]


def _wstr(f, s):
    b = s.encode("utf-8")
    f.write(struct.pack("<i", len(b)))
    f.write(b)


def export(objects, light=None, extra=None):
    """Writes House.bytes (meshes in Unity coordinates) and house.json (everything else)."""
    path = os.path.join(OUT, "House.bytes")
    total_v = total_t = 0
    with open(path, "wb") as f:
        f.write(b"HSE1")
        f.write(struct.pack("<ii", 1, len(objects)))
        for oi, o in enumerate(objects):
            P, N, UV, sizes, fm, mats = object_arrays(o["geo"])
            if light is not None and oi in light:
                L = np.asarray(light[oi], float)
            else:
                L = np.clip(0.55 + 0.35 * N[:, 2], 0.2, 1.0)[:, None].repeat(3, 1)
            origin = o["origin"] if o["origin"] is not None else np.zeros(3)
            Pu = to_unity(P - origin)
            Nu = to_unity(N)
            data = np.concatenate([Pu, Nu, UV, L], 1).astype(np.float32)
            q = np.concatenate([np.round(Pu * 1e4), np.round(Nu * 1e3), np.round(UV * 1e4), np.round(L * 1e3)], 1).astype(np.int64)
            _, first, inv = np.unique(q, axis=0, return_index=True, return_inverse=True)
            inv = inv.reshape(-1)
            V = data[first]
            tri, tface = triangulate(sizes)
            tri = inv[tri][:, [0, 2, 1]]                   # Unity winding
            flags = (1 if o["bake"] else 0) | (2 if o["dynamic"] else 0) | (4 if o["render"] else 0)
            _wstr(f, o["name"])
            _wstr(f, o["group"])
            f.write(struct.pack("<i", flags))
            f.write(struct.pack("<3f", *to_unity(origin)))
            f.write(struct.pack("<i", len(V)))
            f.write(np.ascontiguousarray(V[:, 0:3]).tobytes())
            f.write(np.ascontiguousarray(V[:, 3:6]).tobytes())
            f.write(np.ascontiguousarray(V[:, 6:8]).tobytes())
            f.write(np.ascontiguousarray(V[:, 8:11]).tobytes())
            f.write(struct.pack("<i", len(mats)))
            tm = fm[tface]
            for mi, m in enumerate(mats):
                idx = tri[tm == mi].reshape(-1).astype(np.int32)
                _wstr(f, m)
                f.write(struct.pack("<i", len(idx)))
                f.write(idx.tobytes())
            total_v += len(V)
            total_t += len(tri)
    log("exported %d objects, %d vertices, %d triangles -> %s (%.1f MB)" % (
        len(objects), total_v, total_t, path, os.path.getsize(path) / 1e6))

    def U(v):
        return [round(float(x), 4) for x in to_unity(v)]
    man = dict(version=1)
    man["materials"] = [dict(m) for m in MATS.values()]
    man["colliders"] = [dict(c=U(c), s=[round(float(x), 4) for x in to_unity(s)], q=[round(x, 6) for x in unity_rotation(r)], layer=int(l))
                        for c, s, r, l in COLLIDERS]
    man["doors"] = [dict(name=d["name"], obj=d["obj"], hinge=U(d["hinge"]), latch=U(d["latch"]), outside=U(d["outside"]),
                         focus=U(d["focus"]), width=d["width"], height=d["height"], angle=d.get("angle", 95.0))
                    for d in DOORS]
    man["rooms"] = []
    for r in ROOMS:
        a, b = U(r["min"]), U(r["max"])
        man["rooms"].append(dict(name=r["name"], level=r["level"], min=[min(a[i], b[i]) for i in range(3)],
                                 max=[max(a[i], b[i]) for i in range(3)], patrol=bool(r.get("patrol", True)),
                                 reflection=bool(r.get("reflection", True)), interior=bool(r.get("interior", True))))
    man["views"] = []
    for v in VIEWS:
        d = np.asarray(v["target"], float) - np.asarray(v["eye"], float)
        d /= np.linalg.norm(d)
        man["views"].append(dict(name=v["name"], pos=U(v["eye"]), yaw=round(unity_yaw(d), 3),
                                 pitch=round(-math.degrees(math.asin(max(-1.0, min(1.0, d[2])))), 3),
                                 fov=v.get("fov", 62.0)))
    for k, v in INFO.items():
        man[k] = v
    if extra:
        man.update(extra)
    with open(os.path.join(OUT, "house.json"), "w") as f:
        json.dump(man, f, separators=(",", ":"))
    log("manifest: %d materials, %d colliders, %d doors, %d rooms, %d views" % (
        len(man["materials"]), len(man["colliders"]), len(man["doors"]), len(man["rooms"]), len(man["views"])))
