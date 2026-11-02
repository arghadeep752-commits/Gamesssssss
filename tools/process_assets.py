#!/usr/bin/env python3
"""Builds every art and audio file Night Class uses.

* PBR texture sets from the Poly Haven downloads (tools/fetch_assets.py); a procedural
  set is generated for any slot that failed to download.
* Decals (chalkboard, posters, note, map, clock, keypad, cake, drawings), particle
  textures, UI sprites and icons, item icons, the teacher's face and glasses, the app icon.
* All sound effects and loops, synthesized.

Usage: python3 tools/process_assets.py <sources_dir> <project_dir>
Writes <project_dir>/Assets/Art/...
"""
import math
import os
import shutil
import sys
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import ndimage, signal

SRC = sys.argv[1] if len(sys.argv) > 1 else "SourceAssets"
PROJ = sys.argv[2] if len(sys.argv) > 2 else "."
ART = os.path.join(PROJ, "Assets", "Art")
RNG = np.random.default_rng(20261102)


def out(*p):
    path = os.path.join(ART, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def src(*p):
    return os.path.join(SRC, *p)


def log(*a):
    print("[assets]", *a, flush=True)


# ============================================================================ image helpers
def load_rgb(path, size=None):
    im = Image.open(path).convert("RGB")
    if size and im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def load_gray(path, size=None):
    im = Image.open(path)
    if im.mode in ("I;16", "I;16B", "I"):
        a = np.asarray(im).astype(np.float32)
        a = a / (65535.0 if a.max() > 255 else 255.0)
        im = Image.fromarray((a * 255).astype(np.uint8), "L")
    im = im.convert("L")
    if size and im.size != (size, size):
        im = im.resize((size, size), Image.LANCZOS)
    return np.asarray(im).astype(np.float32) / 255.0


def save_rgb(a, path, quality=90):
    im = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), "RGB")
    if path.endswith(".jpg"):
        im.save(path, quality=quality, subsampling=0)
    else:
        im.save(path)


def save_rgba(a, path):
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(path)


def tnoise(size, sigma, seed, aspect=(1.0, 1.0)):
    """Tileable smooth noise in [0,1]."""
    r = np.random.default_rng(seed).random((size, size))
    n = ndimage.gaussian_filter(r, (sigma * aspect[0], sigma * aspect[1]), mode="wrap")
    return (n - n.min()) / max(n.max() - n.min(), 1e-6)


def fbm(size, seed, octaves=((48, 0.5), (16, 0.3), (5, 0.15), (1.5, 0.05)), aspect=(1.0, 1.0)):
    acc = np.zeros((size, size), np.float32)
    for i, (s, w) in enumerate(octaves):
        acc += tnoise(size, s, seed + i * 17, aspect) * w
    return (acc - acc.min()) / max(acc.max() - acc.min(), 1e-6)


def h2n(h, strength):
    """Height map -> OpenGL-style tangent normal map (wraps)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.dstack([-dx, dy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    return n * 0.5 + 0.5


def lerp(a, b, t):
    return a + (b - a) * t


def col(c):
    return np.array(c, np.float32) / 255.0


FONT_FALLBACK = ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                 "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]


def font(name, size):
    for p in [src("fonts", name)] + FONT_FALLBACK:
        if os.path.exists(p) and os.path.getsize(p) > 10000:
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                pass
    return ImageFont.load_default()


def text_center(d, xy, txt, f, fill, anchor="mm", **kw):
    d.text(xy, txt, font=f, fill=fill, anchor=anchor, **kw)


# ============================================================================ textures
TEX = 1024
MASK = 512


def write_set(slot, albedo, height=None, normal=None, rough=None, ao=None, metal=None, nstrength=2.0):
    save_rgb(albedo, out("Tex", f"{slot}_albedo.jpg"))
    if normal is None:
        normal = h2n(height, nstrength)
    save_rgb(normal, out("Tex", f"{slot}_normal.png"))
    s = albedo.shape[0]
    rough = rough if rough is not None else np.full((s, s), 0.7, np.float32)
    ao = ao if ao is not None else np.ones((s, s), np.float32)
    metal = metal if metal is not None else np.zeros((s, s), np.float32)
    mask = np.dstack([metal, ao, np.zeros_like(ao), 1.0 - rough])
    im = Image.fromarray(np.clip(mask * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").resize((MASK, MASK), Image.LANCZOS)
    im.save(out("Tex", f"{slot}_mask.png"))


def from_download(slot, d=None):
    d = d or src(slot)
    if not os.path.isdir(d):
        return False
    files = {os.path.splitext(f)[0]: os.path.join(d, f) for f in os.listdir(d) if os.path.getsize(os.path.join(d, f)) > 1000}
    if "diff" not in files or "nor" not in files:
        return False
    try:
        alb = load_rgb(files["diff"], TEX)
        nrm = load_rgb(files["nor"], TEX)
        n = TEX
        rough = ao = metal = None
        if "arm" in files:
            arm = load_rgb(files["arm"], n)
            ao, rough, metal = arm[..., 0], arm[..., 1], arm[..., 2]
        if "rough" in files:
            rough = load_gray(files["rough"], n)
        if "ao" in files:
            ao = load_gray(files["ao"], n)
        if "metal" in files:
            metal = load_gray(files["metal"], n)
        if ao is not None:
            ao = 0.35 + 0.65 * ao   # keep the baked AO gentle under dim lights
        write_set(slot, alb, normal=nrm, rough=rough, ao=ao, metal=metal)
        log(f"texture {slot}: Poly Haven")
        return True
    except Exception as e:  # noqa: BLE001
        log(f"texture {slot}: download unusable ({e}), procedural instead")
        return False


def proc_wood(size, seed, plank_rows, base, dark, gaps=True, length_cuts=True):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size] / size
    grain = fbm(size, seed, ((3, 0.4), (1.2, 0.35), (0.5, 0.25)), aspect=(1.0, 14.0))
    rings = 0.5 + 0.5 * np.sin((grain * 22 + y * 40) * math.pi)
    row = np.floor(y * plank_rows).astype(int)
    shade = np.zeros((size, size), np.float32)
    cut = np.zeros((size, size), bool)
    for i in range(plank_rows):
        m = row == i
        shade[m] = r.uniform(-0.12, 0.12)
        if length_cuts:
            off = r.uniform(0, 1)
            xs = (x[m] + off) % 0.5
            cut[m] = xs < 0.004
    t = np.clip(0.55 * grain + 0.3 * rings + shade, 0, 1)
    alb = lerp(col(dark), col(base), t[..., None])
    height = 0.6 + 0.3 * grain
    if gaps:
        edge = (y * plank_rows) % 1.0
        g = (edge < 0.025) | (edge > 0.975) | cut
        alb[g] *= 0.35
        height = np.where(g, 0.0, height)
    alb *= (0.9 + 0.2 * fbm(size, seed + 5))[..., None]
    rough = 0.55 + 0.25 * (1 - grain)
    ao = np.clip(0.55 + 0.45 * ndimage.gaussian_filter(height, 2, mode="wrap") / max(height.max(), 1e-6), 0, 1)
    return alb, height, rough, ao


def proc_tiles(size, seed, n, c1, c2, grout, dirt=0.25):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size] / size
    tx, ty = np.floor(x * n).astype(int), np.floor(y * n).astype(int)
    var = r.uniform(-0.06, 0.06, (n, n))
    checker = ((tx + ty) % 2).astype(np.float32)
    alb = lerp(col(c1), col(c2), checker[..., None]) + var[ty, tx][..., None]
    fx, fy = (x * n) % 1.0, (y * n) % 1.0
    gw = 0.035
    g = (fx < gw) | (fx > 1 - gw) | (fy < gw) | (fy > 1 - gw)
    noise = fbm(size, seed + 3)
    alb = np.where(g[..., None], col(grout) * (0.8 + 0.3 * noise[..., None]), alb)
    alb *= (1 - dirt * fbm(size, seed + 9, ((60, 0.6), (12, 0.4)))[..., None] ** 2)
    bev = np.minimum(np.minimum(fx, 1 - fx), np.minimum(fy, 1 - fy))
    height = np.clip(bev / 0.08, 0, 1) * 0.8 + noise * 0.05
    rough = np.where(g, 0.9, 0.25 + 0.2 * noise)
    ao = np.where(g, 0.55, 1.0)
    return alb, height, rough, ao


def proc_concrete(size, seed, base):
    n1 = fbm(size, seed)
    n2 = fbm(size, seed + 1, ((6, 0.5), (2, 0.3), (0.8, 0.2)))
    stains = fbm(size, seed + 2, ((90, 0.7), (30, 0.3)))
    alb = col(base)[None, None, :] * (0.75 + 0.35 * n1[..., None]) * (1 - 0.3 * (stains[..., None] > 0.62))
    pits = (n2 > 0.86).astype(np.float32)
    alb *= (1 - 0.35 * pits[..., None])
    height = n1 * 0.4 + n2 * 0.6 - pits * 0.6
    return alb, height, 0.75 + 0.2 * n2, 0.75 + 0.25 * n1


def proc_brick(size, seed):
    r = np.random.default_rng(seed)
    y, x = np.mgrid[0:size, 0:size] / size
    rows, cols = 8, 4
    ry = np.floor(y * rows).astype(int)
    off = (ry % 2) * 0.5 / cols
    bx = np.floor(((x + off) % 1.0) * cols).astype(int)
    var = r.uniform(-0.1, 0.1, (rows, cols, 3))
    base = col((150, 70, 52))
    alb = base[None, None, :] + var[ry, bx]
    fx, fy = ((x + off) * cols) % 1.0, (y * rows) % 1.0
    m = (fx < 0.04) | (fx > 0.96) | (fy < 0.07) | (fy > 0.93)
    n = fbm(size, seed + 4)
    alb = np.where(m[..., None], col((170, 165, 155)) * (0.8 + 0.3 * n[..., None]), alb * (0.8 + 0.35 * n[..., None]))
    height = np.where(m, 0.1, 0.8 + 0.2 * n)
    return alb, height, np.where(m, 0.95, 0.75), np.where(m, 0.6, 1.0)


def proc_metal(size, seed, paint):
    n = fbm(size, seed)
    chips = fbm(size, seed + 1, ((20, 0.6), (5, 0.4))) > 0.72
    scratches = np.zeros((size, size), np.float32)
    r = np.random.default_rng(seed)
    im = Image.fromarray(np.zeros((size, size), np.uint8))
    d = ImageDraw.Draw(im)
    for _ in range(120):
        x0, y0 = r.uniform(0, size, 2)
        a = r.uniform(0, math.pi)
        L = r.uniform(20, 160)
        d.line([(x0, y0), (x0 + math.cos(a) * L, y0 + math.sin(a) * L)], fill=int(r.uniform(80, 255)), width=1)
    scratches = np.asarray(im).astype(np.float32) / 255.0
    alb = col(paint)[None, None, :] * (0.85 + 0.25 * n[..., None])
    rust = col((110, 60, 35)) * (0.7 + 0.5 * n[..., None])
    alb = np.where(chips[..., None], rust, alb)
    alb = alb * (1 - 0.25 * scratches[..., None]) + 0.15 * scratches[..., None]
    metal = np.where(chips, 0.0, 0.2) + scratches * 0.6
    height = 0.7 + 0.1 * n - chips * 0.3 - scratches * 0.1
    return alb, height, np.where(chips, 0.9, 0.45 - 0.2 * scratches), np.ones_like(n), np.clip(metal, 0, 1)


def proc_rust(size, seed):
    n1 = fbm(size, seed)
    n2 = fbm(size, seed + 1, ((8, 0.5), (2.5, 0.3), (0.8, 0.2)))
    alb = lerp(col((70, 38, 22)), col((160, 85, 40)), n1[..., None]) * (0.7 + 0.4 * n2[..., None])
    return alb, n1 * 0.5 + n2 * 0.5, 0.85 + 0.1 * n2, 0.8 + 0.2 * n1, np.full_like(n1, 0.15)


def proc_fabric(size, seed):
    y, x = np.mgrid[0:size, 0:size] / size
    w = 0.5 + 0.25 * np.sin(x * size * 0.5 * math.pi) * np.sign(np.sin(y * size * 0.125 * math.pi)) + \
        0.25 * np.sin(y * size * 0.5 * math.pi) * np.sign(np.sin(x * size * 0.125 * math.pi))
    n = fbm(size, seed)
    alb = col((150, 140, 132))[None, None, :] * (0.75 + 0.2 * w[..., None] + 0.15 * n[..., None])
    return alb, w * 0.6 + n * 0.4, np.full_like(n, 0.92), 0.85 + 0.15 * w


def proc_plaster(size, seed):
    n1 = fbm(size, seed)
    n2 = fbm(size, seed + 1, ((4, 0.6), (1.2, 0.4)))
    stains = fbm(size, seed + 2, ((120, 0.7), (40, 0.3)))
    alb = col((222, 220, 210))[None, None, :] * (0.88 + 0.1 * n1[..., None]) * (1 - 0.18 * np.clip(stains - 0.55, 0, 1)[..., None] * 3)
    return alb, n2 * 0.6 + n1 * 0.4, 0.85 + 0.1 * n2, 0.9 + 0.1 * n1


def textures():
    gens = {
        "wood_floor": lambda: proc_wood(TEX, 11, 6, (176, 130, 86), (92, 58, 34)),
        "tiles_floor": lambda: proc_tiles(TEX, 12, 4, (196, 192, 182), (120, 118, 112), (70, 68, 64)),
        "tiles_small": lambda: proc_tiles(TEX, 13, 10, (226, 232, 230), (214, 222, 220), (150, 150, 145), 0.15),
        "concrete": lambda: proc_concrete(TEX, 14, (150, 148, 142)),
        "plaster": lambda: proc_plaster(TEX, 15),
        "brick": lambda: proc_brick(TEX, 16),
        "wood_furniture": lambda: proc_wood(TEX, 17, 1, (190, 145, 98), (110, 70, 40), gaps=False, length_cuts=False),
        "metal_painted": lambda: proc_metal(TEX, 18, (140, 150, 148)),
        "rust": lambda: proc_rust(TEX, 19),
        "fabric": lambda: proc_fabric(TEX, 20),
    }
    for name in ("paper", "chalkboard", "cork", "fabric2"):
        from_download(name, src("extra", name))
    for slot, gen in gens.items():
        if from_download(slot):
            continue
        if slot == "fabric" and from_download("fabric", src("extra", "fabric2")):
            continue
        res = gen()
        alb, height, rough, ao = res[:4]
        metal = res[4] if len(res) > 4 else None
        write_set(slot, np.clip(alb, 0, 1), height=height, rough=np.clip(rough, 0, 1), ao=np.clip(ao, 0, 1), metal=metal)
        log(f"texture {slot}: procedural")


# ============================================================================ decals
def real_tex(name, w, h, seed=0):
    """Crop of a downloaded photo texture (Tex/<name>_albedo.jpg), or None."""
    p = out("Tex", f"{name}_albedo.jpg")
    if not os.path.exists(p):
        return None
    im = Image.open(p).convert("RGB")
    r = np.random.default_rng(seed)
    scale = max(w / im.width, h / im.height) * 1.05
    im = im.resize((max(w, int(im.width * scale)), max(h, int(im.height * scale))), Image.LANCZOS)
    x0 = int(r.uniform(0, im.width - w)) if im.width > w else 0
    y0 = int(r.uniform(0, im.height - h)) if im.height > h else 0
    return im.crop((x0, y0, x0 + w, y0 + h))


def paper_bg(w, h, seed, base=(232, 224, 200)):
    real = real_tex("paper", w, h, seed)
    if real is not None:
        a = np.asarray(real).astype(np.float32) / 255.0
        lum = a.mean(axis=2, keepdims=True)
        a = lerp(a, lum * col(base) / max(col(base).mean(), 1e-3), 0.35)
        return Image.fromarray(np.clip(a / max(a.mean(), 1e-3) * col(base).mean() * 1.0 * 255, 0, 255).astype(np.uint8), "RGB")
    n = ndimage.gaussian_filter(np.random.default_rng(seed).random((h, w)), 3)
    n = (n - n.min()) / (n.max() - n.min())
    big = ndimage.gaussian_filter(np.random.default_rng(seed + 1).random((h, w)), 40)
    big = (big - big.min()) / (big.max() - big.min())
    a = col(base)[None, None, :] * (0.9 + 0.08 * n[..., None]) * (0.85 + 0.15 * big[..., None])
    y, x = np.mgrid[0:h, 0:w]
    edge = np.minimum(np.minimum(x, w - 1 - x) / (w * 0.08), np.minimum(y, h - 1 - y) / (h * 0.08))
    a *= (0.75 + 0.25 * np.clip(edge, 0, 1))[..., None]
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "RGB")


def board_bg(w, h, seed, base=(34, 48, 40)):
    real = real_tex("chalkboard", w, h, seed)
    if real is not None:
        a = np.asarray(real).astype(np.float32) / 255.0
        a = a / max(a.mean(), 1e-3) * col(base).mean() * 1.15
        a = lerp(a, a.mean(axis=2, keepdims=True) * col(base) / max(col(base).mean(), 1e-3), 0.5)
        return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "RGB")
    r = np.random.default_rng(seed)
    n = ndimage.gaussian_filter(r.random((h, w)), 2)
    n = (n - n.min()) / (n.max() - n.min())
    smudge = ndimage.gaussian_filter(r.random((h, w)), (h * 0.05, w * 0.12))
    smudge = (smudge - smudge.min()) / (smudge.max() - smudge.min())
    a = col(base)[None, None, :] * (0.85 + 0.15 * n[..., None]) + 0.12 * np.clip(smudge - 0.45, 0, 1)[..., None] * 2
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "RGB")


def chalk_layer(size, draw_fn, seed):
    """Draw white chalk strokes, then break them up with grainy noise."""
    w, h = size
    m = Image.new("L", (w, h), 0)
    draw_fn(ImageDraw.Draw(m))
    a = np.asarray(m).astype(np.float32) / 255.0
    grain = np.random.default_rng(seed).random((h, w))
    a = a * np.clip(0.45 + grain * 0.8, 0, 1)
    return Image.fromarray(np.clip(a * 255, 0, 255).astype(np.uint8), "L")


def compose_chalk(bg, mask, color=(235, 235, 225)):
    layer = Image.new("RGB", bg.size, color)
    return Image.composite(layer, bg, mask)


def decals():
    D = lambda n: out("Decals", n)
    chalk = lambda s: font("CabinSketch-Bold.ttf", s)
    hand = lambda s: font("PermanentMarker-Regular.ttf", s)
    sans = lambda s: font("Barlow-SemiBold.ttf", s)
    horror = lambda s: font("Creepster-Regular.ttf", s)

    # chalkboard (3.4 x 1.2 m)
    W, H = 1536, 542
    bg = board_bg(W, H, 1)

    def board(d):
        d.text((60, 40), "Lesson 7: Obedience", font=chalk(64), fill=255)
        d.text((60, 140), "1. No talking.", font=chalk(46), fill=230)
        d.text((60, 205), "2. No running in the halls.", font=chalk(46), fill=230)
        d.text((60, 270), "3. No leaving before the bell.", font=chalk(46), fill=230)
        d.text((60, 335), "4. She is always watching.", font=chalk(46), fill=200)
        d.text((980, 60), "7 x 8 = 56", font=chalk(52), fill=230)
        d.text((980, 140), "12 - 5 = 7", font=chalk(52), fill=230)
        d.text((980, 220), "x + 3 = 10", font=chalk(52), fill=230)
        d.text((960, 330), "DETENTION:", font=chalk(50), fill=255)
        d.text((990, 400), "YOU", font=chalk(72), fill=255)
        d.line([(950, 480), (1300, 470)], fill=200, width=6)
        for k in range(5):
            d.line([(700 + k * 22, 420), (712 + k * 22, 470)], fill=210, width=5)
    img = compose_chalk(bg, chalk_layer((W, H), board, 2))
    img.save(D("chalkboard.png"))

    # secret room board (2.4 x 0.9 m)
    W, H = 1536, 576
    bg = board_bg(W, H, 3, (30, 30, 34))

    def secret(d):
        text_center(d, (W / 2, 120), "YOU FOUND THE SECRET ROOM", chalk(92), 255)
        text_center(d, (W / 2, 270), "Class dismissed... for now.", chalk(64), 220)
        text_center(d, (W / 2, 420), "Thank you for playing NIGHT CLASS", chalk(56), 235)
        for k in range(14):
            x = 120 + k * 95
            d.ellipse([x, 500, x + 20, 520], outline=200, width=4)
    compose_chalk(bg, chalk_layer((W, H), secret, 4)).save(D("secret_board.png"))

    # the principal's note with the garage code
    W, H = 512, 683
    img = paper_bg(W, H, 5, (236, 230, 205))
    d = ImageDraw.Draw(img)
    for k in range(14):
        d.line([(30, 90 + k * 42), (W - 30, 90 + k * 42)], fill=(160, 180, 205), width=2)
    d.line([(70, 0), (70, H)], fill=(205, 120, 120), width=2)
    d.text((95, 40), "Reminder", font=hand(44), fill=(40, 40, 70))
    d.text((95, 160), "Garage code:", font=hand(48), fill=(30, 30, 60))
    d.text((100, 270), "4 7 1 9", font=hand(92), fill=(150, 20, 20))
    d.text((95, 470), "Do NOT give it", font=hand(38), fill=(30, 30, 60))
    d.text((95, 520), "to the students!", font=hand(38), fill=(30, 30, 60))
    d.text((250, 600), "- Principal", font=hand(34), fill=(30, 30, 60))
    img.save(D("note.png"))

    # school map (1.2 x 0.85 m), drawn from the real layout
    W, H = 1024, 725
    img = paper_bg(W, H, 6, (222, 214, 190))
    d = ImageDraw.Draw(img)
    text_center(d, (W / 2, 42), "SCHOOL MAP", sans(46), (40, 40, 45))
    x0, x1, z0, z1 = -37.0, 37.0, -17.0, 16.0
    sx = (W - 80) / (x1 - x0)
    sz = (H - 120) / (z1 - z0)
    P = lambda x, z: (40 + (x - x0) * sx, 90 + (z1 - z) * sz)
    rooms = [((-36, -2, 26, 2), "Corridor"), ((-24, 2, -14, 12), "Class A"), ((-14, 2, -4, 12), "Class B"), ((-4, 2, 4, 12), "Lounge"),
             ((4, 2, 14, 12), "Class C"), ((14, 2, 24, 12), "Toilets"), ((-36, 2, -24, 10), "Office"), ((-36, -10, -24, -2), "Library"),
             ((-24, -12, -14, -2), "Cafeteria"), ((-14, -12, -8, -2), "Janitor"), ((-8, -14, 4, -2), "Entrance"), ((4, -16, 24, -2), "Gym"),
             ((26, -6, 36, 6), "Garage")]
    for (ax, az, bx, bz), name in rooms:
        p0, p1 = P(ax, bz), P(bx, az)
        d.rectangle([p0[0], p0[1], p1[0], p1[1]], outline=(50, 50, 60), width=4, fill=(235, 228, 205) if name != "Corridor" else (210, 204, 182))
        text_center(d, ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2), name, sans(22 if name not in ("Janitor",) else 17), (50, 50, 60))
    ex = P(-2, -14)
    d.ellipse([ex[0] - 12, ex[1] - 12, ex[0] + 12, ex[1] + 12], fill=(190, 30, 30))
    d.text((ex[0] + 18, ex[1] - 30), "YOU ARE HERE", font=sans(24), fill=(190, 30, 30))
    img.save(D("map.png"))

    # clock face
    S = 512
    img = Image.new("RGB", (S, S), (25, 25, 25))
    d = ImageDraw.Draw(img)
    d.ellipse([8, 8, S - 8, S - 8], fill=(232, 228, 214))
    for k in range(60):
        a = k / 60 * 2 * math.pi
        r0 = 0.40 if k % 5 == 0 else 0.43
        d.line([(S / 2 + math.sin(a) * S * r0, S / 2 - math.cos(a) * S * r0), (S / 2 + math.sin(a) * S * 0.46, S / 2 - math.cos(a) * S * 0.46)],
               fill=(30, 30, 30), width=8 if k % 5 == 0 else 3)
    for h in range(1, 13):
        a = h / 12 * 2 * math.pi
        text_center(d, (S / 2 + math.sin(a) * S * 0.33, S / 2 - math.cos(a) * S * 0.33), str(h), sans(46), (30, 30, 30))
    for ang, ln, wd in ((3.1 / 12 * 2 * math.pi, 0.22, 14), (7 / 60 * 2 * math.pi, 0.36, 9)):
        d.line([(S / 2, S / 2), (S / 2 + math.sin(ang) * S * ln, S / 2 - math.cos(ang) * S * ln)], fill=(20, 20, 20), width=wd)
    d.line([(S / 2, S / 2), (S / 2 + math.sin(4.2) * S * 0.38, S / 2 - math.cos(4.2) * S * 0.38)], fill=(170, 20, 20), width=4)
    d.ellipse([S / 2 - 14, S / 2 - 14, S / 2 + 14, S / 2 + 14], fill=(20, 20, 20))
    img.save(D("clock.png"))

    # keypad
    W, H = 256, 370
    img = Image.new("RGB", (W, H), (40, 42, 44))
    d = ImageDraw.Draw(img)
    d.rectangle([24, 22, W - 24, 78], fill=(20, 40, 30))
    d.text((38, 30), "- - - -", font=sans(34), fill=(80, 200, 120))
    keys = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "*", "0", "#"]
    for i, k in enumerate(keys):
        cx, cy = 52 + (i % 3) * 76, 120 + (i // 3) * 64
        d.rounded_rectangle([cx - 30, cy - 24, cx + 30, cy + 24], radius=8, fill=(185, 185, 180), outline=(90, 90, 90), width=2)
        text_center(d, (cx, cy), k, sans(34), (30, 30, 30))
    img.save(D("keypad.png"))

    # posters
    posters = [
        ("SILENCE", "is a virtue", (120, 30, 30), (230, 220, 200)),
        ("READ", "every day", (30, 70, 110), (225, 220, 205)),
        ("SCIENCE FAIR", "cancelled", (40, 90, 60), (220, 225, 210)),
        ("RULES", "1 Sit still\n2 Eyes front\n3 Obey", (60, 50, 90), (225, 218, 200)),
    ]
    for i, (title, sub, accent, paper) in enumerate(posters):
        W, H = 512, 725
        img = paper_bg(W, H, 10 + i, paper)
        d = ImageDraw.Draw(img)
        d.rectangle([28, 28, W - 28, H - 28], outline=accent, width=10)
        d.rectangle([28, 28, W - 28, 200], fill=accent)
        text_center(d, (W / 2, 114), title, sans(84 if len(title) < 8 else 58), (240, 236, 225))
        if "\n" in sub:
            for k, line in enumerate(sub.split("\n")):
                d.text((70, 280 + k * 100), line, font=sans(56), fill=(40, 40, 45))
        else:
            text_center(d, (W / 2, 300), sub, sans(56), (40, 40, 45))
            # simple pictogram
            cx, cy = W / 2, 500
            if i == 0:
                d.ellipse([cx - 90, cy - 90, cx + 90, cy + 90], outline=accent, width=12)
                d.line([(cx - 20, cy - 60), (cx - 20, cy + 60)], fill=accent, width=24)
            elif i == 1:
                d.polygon([(cx - 140, cy - 60), (cx, cy - 30), (cx, cy + 90), (cx - 140, cy + 60)], outline=accent, width=10)
                d.polygon([(cx + 140, cy - 60), (cx, cy - 30), (cx, cy + 90), (cx + 140, cy + 60)], outline=accent, width=10)
            else:
                d.ellipse([cx - 70, cy - 40, cx + 70, cy + 100], outline=accent, width=10)
                d.rectangle([cx - 25, cy - 120, cx + 25, cy - 40], outline=accent, width=10)
                d.line([(cx - 160, cy + 140), (cx + 160, cy - 140)], fill=(170, 20, 20), width=16)
        # tears and stains
        arr = np.asarray(img).astype(np.float32) / 255
        st = ndimage.gaussian_filter(np.random.default_rng(30 + i).random((H, W)), 30)
        st = (st - st.min()) / (st.max() - st.min())
        arr *= (1 - 0.35 * np.clip(st - 0.6, 0, 1) * 2.5)[..., None]
        Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8)).save(D(f"poster{i}.png"))

    # child's drawing (easter egg in the gym storage)
    W, H = 512, 384
    img = paper_bg(W, H, 40, (238, 234, 222))
    d = ImageDraw.Draw(img)
    d.polygon([(60, 230), (150, 150), (240, 230)], outline=(200, 60, 40), width=6)
    d.rectangle([80, 230, 220, 330], outline=(60, 60, 200), width=6)
    d.ellipse([400, 30, 470, 100], outline=(230, 190, 30), width=6)
    for k, x in enumerate((290, 340)):
        d.ellipse([x - 16, 210, x + 16, 242], outline=(30, 30, 30), width=5)
        d.line([(x, 242), (x, 300), (x - 20, 340), (x, 300), (x + 20, 340)], fill=(30, 30, 30), width=5)
        d.line([(x - 25, 262), (x + 25, 262)], fill=(30, 30, 30), width=5)
    tx = 440
    d.ellipse([tx - 18, 120, tx + 18, 160], outline=(20, 20, 20), width=5)
    d.ellipse([tx - 10, 133, tx - 3, 140], fill=(220, 20, 20))
    d.ellipse([tx + 3, 133, tx + 10, 140], fill=(220, 20, 20))
    d.line([(tx, 160), (tx, 270), (tx - 30, 340), (tx, 270), (tx + 30, 340)], fill=(20, 20, 20), width=6)
    d.line([(tx - 35, 190), (tx + 40, 175)], fill=(20, 20, 20), width=5)
    d.line([(tx + 40, 175), (tx + 70, 120)], fill=(150, 90, 40), width=8)
    d.text((40, 20), "MY SCHOOL", font=hand(36), fill=(40, 40, 160))
    img.save(D("drawing.png"))

    # cake: bottom strip = the side (sponge + cream), the rest = frosting with sprinkles
    W, H = 512, 512
    a = np.zeros((H, W, 3), np.float32)
    a[:] = col((245, 214, 222))
    rr = np.random.default_rng(41)
    img = Image.fromarray((a * 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for _ in range(500):
        x, y = rr.uniform(0, W), rr.uniform(0, H * 0.86)
        ang = rr.uniform(0, math.pi)
        c = tuple(int(v) for v in rr.choice([(220, 40, 60), (40, 120, 220), (250, 200, 40), (60, 180, 80), (250, 250, 250)]))
        d.line([(x, y), (x + math.cos(ang) * 9, y + math.sin(ang) * 9)], fill=c, width=4)
    side_top = int(H * 0.88)
    d.rectangle([0, side_top, W, H], fill=(95, 55, 35))
    d.rectangle([0, side_top, W, side_top + 14], fill=(245, 214, 222))
    d.rectangle([0, side_top + 30, W, side_top + 38], fill=(250, 240, 230))
    img.save(D("cake.png"))


# ============================================================================ FX
def fx():
    F = lambda n: out("FX", n)
    y, x = np.mgrid[0:128, 0:128] / 127.0
    r = np.sqrt((x - 0.5) ** 2 * 4 + (y - 0.62) ** 2 * 1.2)
    tongue = np.clip(1 - r * 1.6, 0, 1) ** 1.5 * np.clip((y - 0.05) * 1.3, 0, 1)
    n = ndimage.gaussian_filter(RNG.random((128, 128)), 4)
    n = (n - n.min()) / (n.max() - n.min())
    tongue *= 0.75 + 0.25 * n
    save_rgba(np.dstack([np.ones_like(tongue), 0.55 + 0.45 * tongue, 0.2 + 0.35 * tongue ** 2, tongue]), F("flame.png"))
    n = ndimage.gaussian_filter(RNG.random((128, 128)), 6)
    n = (n - n.min()) / (n.max() - n.min())
    rr = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) * 2
    puff = np.clip(1 - rr, 0, 1) ** 1.6 * (0.55 + 0.45 * n)
    save_rgba(np.dstack([np.full_like(puff, 0.85), np.full_like(puff, 0.85), np.full_like(puff, 0.87), puff]), F("smoke.png"))
    y2, x2 = np.mgrid[0:64, 0:64] / 63.0
    rs = np.sqrt((x2 - 0.5) ** 2 + (y2 - 0.5) ** 2) * 2
    spark = np.clip(1 - rs, 0, 1) ** 3
    save_rgba(np.dstack([np.ones_like(spark), 0.85 + 0.15 * spark, 0.5 + 0.5 * spark, spark]), F("spark.png"))
    drop = np.clip(1 - np.sqrt(((x2 - 0.5) * 4) ** 2 + ((y2 - 0.5) * 1.3) ** 2), 0, 1) ** 1.5
    save_rgba(np.dstack([np.full_like(drop, 0.8), np.full_like(drop, 0.88), np.ones_like(drop), drop]), F("drop.png"))
    # grime for the windows (R channel): from the real concrete photo when available
    realc = real_tex("concrete", 512, 512, 3)
    if realc is not None:
        g = np.asarray(realc.convert("L")).astype(np.float32) / 255.0
        g = (g - g.min()) / max(g.max() - g.min(), 1e-6)
    else:
        g = fbm(512, 50, ((40, 0.5), (10, 0.3), (2, 0.2)))
    streak = ndimage.gaussian_filter(RNG.random((512, 512)), (40, 1.5), mode="wrap")
    streak = (streak - streak.min()) / (streak.max() - streak.min())
    gr = np.clip(g * 0.7 + streak * 0.5 - 0.2, 0, 1)
    save_rgb(np.dstack([gr, gr, gr]), F("grime.png"))
    # a cockroach
    S = 256
    im = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    body = (58, 32, 18, 255)
    for k in (-1, 1):
        for j, yy in enumerate((100, 130, 160)):
            d.line([(128, yy), (128 + k * 70, yy + (j - 1) * 30 - 10), (128 + k * 95, yy + (j - 1) * 45)], fill=body, width=7)
        d.line([(128, 60), (128 + k * 50, 10)], fill=body, width=4)
    d.ellipse([92, 70, 164, 220], fill=body)
    d.ellipse([104, 48, 152, 90], fill=(40, 22, 12, 255))
    d.line([(128, 92), (128, 210)], fill=(30, 16, 8, 255), width=3)
    im.resize((64, 64), Image.LANCZOS).save(F("bug.png"))


# ============================================================================ UI
def ss_draw(size, fn, scale=4):
    big = Image.new("RGBA", (size * scale, size * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(big)
    fn(d, size * scale)
    return big.resize((size, size), Image.LANCZOS)


def ui():
    U = lambda n: out("UI", n)
    W = (255, 255, 255, 255)
    ss_draw(256, lambda d, s: d.ellipse([2, 2, s - 3, s - 3], fill=W)).save(U("circle.png"))
    ss_draw(256, lambda d, s: d.ellipse([s * 0.03, s * 0.03, s * 0.97, s * 0.97], outline=W, width=int(s * 0.035))).save(U("ring.png"))
    ss_draw(64, lambda d, s: d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.3), fill=W)).save(U("rounded.png"))

    def soft(size, power):
        yy, xx = np.mgrid[0:size, 0:size]
        r = np.sqrt((xx - size / 2 + 0.5) ** 2 + (yy - size / 2 + 0.5) ** 2) / (size / 2)
        a = np.clip(1 - r, 0, 1) ** power
        return np.dstack([np.ones_like(a), np.ones_like(a), np.ones_like(a), a])
    save_rgba(soft(128, 2.2), U("glow.png"))
    save_rgba(soft(64, 1.0), U("dot.png"))
    yy, xx = np.mgrid[0:512, 0:512] / 511.0
    rv = np.sqrt(((xx - 0.5) * 1.0) ** 2 + ((yy - 0.5) * 1.15) ** 2) * 2
    va = np.clip((rv - 0.55) / 0.75, 0, 1) ** 1.6
    save_rgba(np.dstack([np.zeros_like(va), np.zeros_like(va), np.zeros_like(va), va]), U("vignette.png"))

    def icon(name, fn):
        ss_draw(128, fn).save(U(f"icon_{name}.png"))

    def hand(d, s):
        d.rounded_rectangle([s * 0.3, s * 0.45, s * 0.72, s * 0.86], radius=s * 0.12, fill=W)
        for i, x in enumerate((0.31, 0.42, 0.53, 0.64)):
            top = 0.2 if i in (1, 2) else 0.27
            d.rounded_rectangle([s * x, s * top, s * (x + 0.085), s * 0.6], radius=s * 0.042, fill=W)
        d.rounded_rectangle([s * 0.14, s * 0.48, s * 0.36, s * 0.6], radius=s * 0.055, fill=W)

    def drop(d, s):
        w = int(s * 0.1)
        d.line([(s * 0.5, s * 0.15), (s * 0.5, s * 0.58)], fill=W, width=w)
        d.polygon([(s * 0.3, s * 0.45), (s * 0.7, s * 0.45), (s * 0.5, s * 0.7)], fill=W)
        d.line([(s * 0.2, s * 0.84), (s * 0.8, s * 0.84)], fill=W, width=w)

    def crouch(d, s):
        w = int(s * 0.11)
        d.line([(s * 0.25, s * 0.36), (s * 0.5, s * 0.6), (s * 0.75, s * 0.36)], fill=W, width=w, joint="curve")
        d.line([(s * 0.28, s * 0.8), (s * 0.72, s * 0.8)], fill=W, width=int(w * 0.8))

    def stand(d, s):
        w = int(s * 0.11)
        d.line([(s * 0.25, s * 0.6), (s * 0.5, s * 0.36), (s * 0.75, s * 0.6)], fill=W, width=w, joint="curve")
        d.line([(s * 0.28, s * 0.8), (s * 0.72, s * 0.8)], fill=W, width=int(w * 0.8))

    def locker(d, s, open_=False):
        d.rounded_rectangle([s * 0.28, s * 0.12, s * 0.72, s * 0.9], radius=s * 0.04, outline=W, width=int(s * 0.07))
        for k in range(3):
            d.line([(s * 0.38, s * (0.24 + k * 0.07)), (s * 0.62, s * (0.24 + k * 0.07))], fill=W, width=int(s * 0.04))
        if open_:
            d.polygon([(s * 0.72, s * 0.12), (s * 0.9, s * 0.2), (s * 0.9, s * 0.82), (s * 0.72, s * 0.9)], fill=W)
        else:
            d.ellipse([s * 0.56, s * 0.52, s * 0.64, s * 0.6], fill=W)

    def fire(d, s):
        d.polygon([(s * 0.5, s * 0.08), (s * 0.7, s * 0.4), (s * 0.78, s * 0.62), (s * 0.7, s * 0.82), (s * 0.5, s * 0.92), (s * 0.3, s * 0.82),
                   (s * 0.22, s * 0.62), (s * 0.32, s * 0.44), (s * 0.4, s * 0.55)], fill=W)
        d.polygon([(s * 0.5, s * 0.5), (s * 0.6, s * 0.68), (s * 0.5, s * 0.84), (s * 0.4, s * 0.7)], fill=(0, 0, 0, 0))

    def jump(d, s):
        w = int(s * 0.11)
        d.line([(s * 0.25, s * 0.5), (s * 0.5, s * 0.25), (s * 0.75, s * 0.5)], fill=W, width=w, joint="curve")
        d.line([(s * 0.25, s * 0.72), (s * 0.5, s * 0.47), (s * 0.75, s * 0.72)], fill=W, width=w, joint="curve")

    def pause(d, s):
        d.rounded_rectangle([s * 0.3, s * 0.25, s * 0.43, s * 0.75], radius=s * 0.03, fill=W)
        d.rounded_rectangle([s * 0.57, s * 0.25, s * 0.7, s * 0.75], radius=s * 0.03, fill=W)

    for name, fn in (("hand", hand), ("drop", drop), ("crouch", crouch), ("stand", stand), ("hide", lambda d, s: locker(d, s)),
                     ("unhide", lambda d, s: locker(d, s, True)), ("fire", fire), ("jump", jump), ("pause", pause)):
        icon(name, fn)

    # coloured item icons
    def item(name, fn):
        ss_draw(256, fn, 3).save(U(f"item_{name}.png"))

    BR, BR2 = (205, 160, 70, 255), (150, 110, 40, 255)

    def key(d, s, c1, c2, big):
        k = 1.0 if big else 0.8
        cx, cy = s * 0.32, s * 0.5
        R = s * 0.17 * k
        d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=c1, outline=c2, width=int(s * 0.03))
        d.ellipse([cx - R * 0.45, cy - R * 0.45, cx + R * 0.45, cy + R * 0.45], fill=(0, 0, 0, 0))
        d.rectangle([cx + R * 0.9, cy - s * 0.035, s * 0.86, cy + s * 0.035], fill=c1, outline=c2, width=int(s * 0.015))
        for bx in (0.66, 0.77) if big else (0.72,):
            d.rectangle([s * bx, cy, s * (bx + 0.06), cy + s * 0.12], fill=c1, outline=c2, width=int(s * 0.015))

    item("mainkey", lambda d, s: key(d, s, BR, BR2, True))
    item("safekey", lambda d, s: key(d, s, (190, 195, 200, 255), (110, 115, 120, 255), False))

    def hammer(d, s):
        d.polygon([(s * 0.47, s * 0.3), (s * 0.55, s * 0.3), (s * 0.58, s * 0.9), (s * 0.44, s * 0.9)], fill=(150, 100, 55, 255))
        d.rounded_rectangle([s * 0.22, s * 0.14, s * 0.8, s * 0.32], radius=s * 0.03, fill=(95, 98, 105, 255), outline=(50, 50, 55, 255), width=int(s * 0.015))
    item("hammer", hammer)

    def torch(d, s):
        d.polygon([(s * 0.45, s * 0.42), (s * 0.55, s * 0.42), (s * 0.53, s * 0.92), (s * 0.47, s * 0.92)], fill=(110, 70, 40, 255))
        d.rectangle([s * 0.42, s * 0.36, s * 0.58, s * 0.46], fill=(60, 50, 45, 255))
        d.polygon([(s * 0.5, s * 0.04), (s * 0.66, s * 0.24), (s * 0.62, s * 0.38), (s * 0.38, s * 0.38), (s * 0.34, s * 0.24)], fill=(255, 140, 30, 255))
        d.polygon([(s * 0.5, s * 0.16), (s * 0.58, s * 0.3), (s * 0.5, s * 0.37), (s * 0.42, s * 0.3)], fill=(255, 225, 120, 255))
    item("torch", torch)

    def note(d, s):
        d.polygon([(s * 0.24, s * 0.12), (s * 0.76, s * 0.16), (s * 0.72, s * 0.9), (s * 0.2, s * 0.86)], fill=(236, 228, 200, 255), outline=(150, 140, 120, 255))
        for k in range(5):
            d.line([(s * 0.3, s * (0.3 + k * 0.11)), (s * 0.66, s * (0.32 + k * 0.11))], fill=(70, 70, 110, 255), width=int(s * 0.025))
        d.text((s * 0.3, s * 0.52), "4719", font=font("PermanentMarker-Regular.ttf", int(s * 0.17)), fill=(170, 20, 20, 255))
    item("note", note)

    def spring(d, s):
        for k in range(7):
            y0 = s * (0.18 + k * 0.09)
            d.arc([s * 0.3, y0, s * 0.7, y0 + s * 0.12], 0, 360, fill=(180, 185, 190, 255), width=int(s * 0.04))
    item("spring", spring)

    def dynamite(d, s):
        for k in range(3):
            x = s * (0.28 + k * 0.15)
            d.rounded_rectangle([x, s * 0.3, x + s * 0.14, s * 0.86], radius=s * 0.04, fill=(185, 35, 30, 255), outline=(110, 20, 15, 255), width=int(s * 0.012))
        d.rectangle([s * 0.26, s * 0.44, s * 0.74, s * 0.5], fill=(30, 30, 30, 255))
        d.rectangle([s * 0.26, s * 0.68, s * 0.74, s * 0.74], fill=(30, 30, 30, 255))
        d.line([(s * 0.5, s * 0.3), (s * 0.56, s * 0.14), (s * 0.66, s * 0.08)], fill=(60, 60, 60, 255), width=int(s * 0.02))
        d.ellipse([s * 0.63, s * 0.04, s * 0.71, s * 0.12], fill=(255, 200, 60, 255))
    item("dynamite", dynamite)


# ============================================================================ the teacher's face + glasses
def teacher():
    T = lambda n: out("Teacher", n)
    S = 1024
    yy, xx = np.mgrid[0:S, 0:S] / (S - 1.0)
    u, v = xx, 1.0 - yy                      # texture uv
    dx, dy = (u - 0.5) * 2, (v - 0.5) * 2    # sphere direction x / y

    def g(cx, cy, sx, sy):
        return np.exp(-(((dx - cx) / sx) ** 2 + ((dy - cy) / sy) ** 2))

    n1 = fbm(S, 60, ((30, 0.5), (8, 0.3), (2, 0.2)))
    n2 = fbm(S, 61, ((4, 0.6), (1.2, 0.4)))
    skin = col((200, 182, 170))[None, None, :] * (0.9 + 0.12 * n1[..., None])
    skin = skin * (1 - 0.06 * n2[..., None])
    sym = lambda cx, cy, sx, sy: g(cx, cy, sx, sy) + g(-cx, cy, sx, sy)
    # sallow/grey tones, reddish nose and eyelids, dark sockets
    skin = lerp(skin, col((150, 140, 140))[None, None, :], (0.25 * sym(0.6, -0.3, 0.25, 0.25))[..., None])
    skin = lerp(skin, col((175, 120, 115))[None, None, :], (0.35 * g(0, -0.12, 0.1, 0.12))[..., None])
    sockets = sym(0.36, 0.14, 0.16, 0.11)
    skin = lerp(skin, col((70, 52, 56))[None, None, :], (0.75 * np.clip(sockets * 1.3, 0, 1))[..., None])
    under = sym(0.36, 0.03, 0.15, 0.05)
    skin = lerp(skin, col((110, 85, 95))[None, None, :], (0.45 * under)[..., None])
    # age spots
    rr = np.random.default_rng(62)
    spots = np.zeros((S, S), np.float32)
    for _ in range(70):
        cx, cy = rr.uniform(-0.85, 0.85), rr.uniform(-0.75, 0.85)
        if abs(cx) < 0.5 and -0.2 < cy < 0.3:
            continue
        r0 = rr.uniform(0.01, 0.03)
        spots = np.maximum(spots, rr.uniform(0.3, 0.7) * np.exp(-(((dx - cx) ** 2 + (dy - cy) ** 2) / r0 ** 2)))
    skin = lerp(skin, col((130, 95, 70))[None, None, :], spots[..., None])
    img = Image.fromarray(np.clip(skin * 255, 0, 255).astype(np.uint8))

    # wrinkles: dark creases with a faint highlight
    crease = Image.new("L", (S, S), 0)
    hi = Image.new("L", (S, S), 0)
    dc, dh = ImageDraw.Draw(crease), ImageDraw.Draw(hi)
    P = lambda x, y: (S * (0.5 + x * 0.5), S * (1 - (0.5 + y * 0.5)))

    def wline(pts, w=3, strength=170):
        pp = [P(*p) for p in pts]
        dc.line(pp, fill=strength, width=w, joint="curve")
        dh.line([(x, y + w + 1) for x, y in pp], fill=strength // 3, width=max(1, w - 1))

    for k in range(5):   # forehead
        y = 0.46 + k * 0.055
        wline([(-0.42, y - 0.01), (-0.15, y + 0.012), (0.15, y + 0.012), (0.42, y - 0.01)], 3, 150 - k * 15)
    wline([(-0.03, 0.34), (-0.05, 0.42)], 4, 190)   # frown lines
    wline([(0.03, 0.34), (0.05, 0.42)], 4, 190)
    for s_ in (-1, 1):
        for k in range(4):   # crow's feet
            a = -0.5 + k * 0.33
            wline([(s_ * 0.55, 0.14), (s_ * (0.55 + 0.14 * math.cos(a)), 0.14 + 0.1 * math.sin(a))], 2, 140)
        wline([(s_ * 0.08, -0.16), (s_ * 0.16, -0.3), (s_ * 0.2, -0.44), (s_ * 0.2, -0.52)], 5, 200)   # nasolabial folds
        wline([(s_ * 0.22, -0.5), (s_ * 0.24, -0.62), (s_ * 0.2, -0.74)], 4, 160)   # marionette lines
        wline([(s_ * 0.22, 0.06), (s_ * 0.36, 0.035), (s_ * 0.5, 0.06)], 3, 150)   # bags under the eyes
        wline([(s_ * 0.22, 0.21), (s_ * 0.36, 0.245), (s_ * 0.5, 0.21)], 3, 170)   # upper lids
        wline([(s_ * 0.32, -0.15), (s_ * 0.5, -0.28)], 3, 120)   # under the cheekbone
        wline([(s_ * 0.72, -0.1), (s_ * 0.7, -0.45)], 3, 110)
    for k in range(6):   # lines above the lip
        x = -0.12 + k * 0.048
        wline([(x, -0.36), (x * 0.9, -0.42)], 2, 140)
    for k in range(3):   # neck/chin
        wline([(-0.22, -0.78 - k * 0.05), (0.22, -0.78 - k * 0.05)], 2, 100)
    crease = crease.filter(ImageFilter.GaussianBlur(1.6))
    hi = hi.filter(ImageFilter.GaussianBlur(2.0))
    arr = np.asarray(img).astype(np.float32) / 255
    c = np.asarray(crease).astype(np.float32)[..., None] / 255
    h = np.asarray(hi).astype(np.float32)[..., None] / 255
    arr = arr * (1 - 0.55 * c) + 0.18 * h
    img = Image.fromarray(np.clip(arr * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    # thin, pale lips with a dark line between them
    mouth_y = -0.45
    d.polygon([P(-0.2, mouth_y + 0.005), P(-0.08, mouth_y + 0.05), P(0, mouth_y + 0.035), P(0.08, mouth_y + 0.05), P(0.2, mouth_y + 0.005), P(0, mouth_y - 0.005)],
              fill=(125, 72, 74))
    d.polygon([P(-0.19, mouth_y - 0.002), P(0, mouth_y - 0.06), P(0.19, mouth_y - 0.002), P(0, mouth_y - 0.01)], fill=(118, 68, 70))
    d.line([P(-0.22, mouth_y + 0.01), P(-0.1, mouth_y), P(0, mouth_y + 0.004), P(0.1, mouth_y), P(0.22, mouth_y + 0.01)], fill=(40, 12, 14), width=6)
    # stern grey eyebrows, angled down to the middle
    for s_ in (-1, 1):
        for k in range(40):
            t = k / 39
            x = s_ * (0.1 + t * 0.34)
            y = 0.31 + t * 0.06 - 0.06 * (t - 0.6) ** 2 * 4 * 0.25
            d.line([P(x, y - 0.012), P(x + s_ * 0.03, y + 0.02)], fill=(150, 145, 140), width=3)
    img = img.filter(ImageFilter.GaussianBlur(0.6))
    img.save(T("face.png"))

    # lenses
    L = 256
    yy, xx = np.mgrid[0:L, 0:L] / (L - 1.0)
    rr2 = np.sqrt((xx - 0.5) ** 2 + (yy - 0.5) ** 2)
    inside = (rr2 < 0.48).astype(np.float32)
    base = np.dstack([np.full_like(rr2, 0.75), np.full_like(rr2, 0.8), np.full_like(rr2, 0.86), 0.16 * inside])
    glint = np.exp(-(((xx - 0.33) / 0.09) ** 2 + ((yy - 0.3) / 0.05) ** 2)) * inside
    base[..., 3] = np.clip(base[..., 3] + 0.45 * glint, 0, 1)
    base[..., :3] = np.clip(base[..., :3] + glint[..., None] * 0.3, 0, 1)
    save_rgba(base, T("lens_clean.png"))
    im = Image.new("L", (L, L), 0)
    dd = ImageDraw.Draw(im)
    rq = np.random.default_rng(63)
    hx, hy = L * 0.6, L * 0.38
    for k in range(9):
        a = k / 9 * 2 * math.pi + rq.uniform(-0.25, 0.25)
        x, y = hx, hy
        pts = [(x, y)]
        for _ in range(6):
            a += rq.uniform(-0.35, 0.35)
            step = rq.uniform(14, 30)
            x, y = x + math.cos(a) * step, y + math.sin(a) * step
            pts.append((x, y))
        dd.line(pts, fill=255, width=2)
    for rad in (16, 34):
        dd.arc([hx - rad, hy - rad, hx + rad, hy + rad], 20, 300, fill=200, width=2)
    cr = np.asarray(im.filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) / 255 * inside
    cracked = base.copy()
    cracked[..., :3] = np.clip(cracked[..., :3] + cr[..., None] * 0.6, 0, 1)
    cracked[..., 3] = np.clip(cracked[..., 3] + cr * 0.85, 0, 1)
    save_rgba(cracked, T("lens_crack.png"))


def rocketbox_teacher():
    """Realistic teacher (Microsoft Rocketbox, MIT): converts the TGA textures to PNG and grades
    them older and paler (grey hair, sallow skin, darker suit); copies the rig and animations."""
    sd = src("teacher")
    fbx = os.path.join(sd, "Business_Female_02_facial.fbx")
    if not os.path.exists(fbx) or os.path.getsize(fbx) < 100000:
        log("teacher: Rocketbox model missing, the build uses the procedural teacher")
        return
    dst = os.path.join(ART, "Teacher", "Rocketbox")
    os.makedirs(os.path.join(dst, "Textures"), exist_ok=True)
    os.makedirs(os.path.join(dst, "Anims"), exist_ok=True)
    shutil.copyfile(fbx, os.path.join(dst, "Business_Female_02_facial.fbx"))
    for f in os.listdir(os.path.join(sd, "Anims")) if os.path.isdir(os.path.join(sd, "Anims")) else []:
        if f.endswith(".fbx") and os.path.getsize(os.path.join(sd, "Anims", f)) > 10000:
            shutil.copyfile(os.path.join(sd, "Anims", f), os.path.join(dst, "Anims", f))
    td = os.path.join(sd, "Textures")
    for f in sorted(os.listdir(td)) if os.path.isdir(td) else []:
        if not f.endswith(".tga"):
            continue
        im = Image.open(os.path.join(td, f))
        name = f[:-4]
        size = 1024
        if "glasses" in name:
            size = 256
        rgba = "opacity" in name
        im = im.convert("RGBA" if rgba else "RGB").resize((size, size), Image.LANCZOS)
        a = np.asarray(im).astype(np.float32) / 255.0
        if name.endswith("head_color"):
            rgb = a[..., :3]
            mx, mn = rgb.max(axis=2), rgb.min(axis=2)
            sat = (mx - mn) / np.maximum(mx, 1e-4)
            r_, g_, b_ = rgb[..., 0], rgb[..., 1], rgb[..., 2]
            hue = (np.degrees(np.arctan2(np.sqrt(3) * (g_ - b_), 2 * r_ - g_ - b_)) + 360) % 360
            hair = np.clip((hue - 30) / 8, 0, 1) * np.clip((62 - hue) / 8, 0, 1) * np.clip((sat - 0.18) / 0.1, 0, 1)
            hair = ndimage.gaussian_filter(hair, 2)[..., None]
            lum = rgb.mean(axis=2, keepdims=True)
            skin = lerp(rgb, lum * np.array([1.0, 0.97, 0.95]), 0.45) * 0.94 + np.array([0.02, 0.025, 0.01])
            silver = np.clip(lerp(lum, 0.7, 0.5) * np.array([0.97, 0.97, 1.0]), 0, 1)
            a[..., :3] = lerp(skin, silver, hair)
        elif name.endswith("opacity_color") and "glasses" not in name:
            lum = a[..., :3].mean(axis=2, keepdims=True)
            a[..., :3] = np.clip(lerp(lum, 0.72, 0.55) * np.array([0.98, 0.98, 1.0]), 0, 1)   # grey-silver hair
        elif name.endswith("body_color"):
            lum = a[..., :3].mean(axis=2, keepdims=True)
            a[..., :3] = lerp(a[..., :3], lum, 0.3) * 0.72
        mode = "RGBA" if rgba else "RGB"
        Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), mode).save(os.path.join(dst, "Textures", name + ".png"))
    log("teacher: Rocketbox Business_Female_02 + " + str(len(os.listdir(os.path.join(dst, "Anims")))) + " animations")


def models():
    md = src("models")
    if not os.path.isdir(md):
        log("models: none downloaded")
        return
    n = 0
    for slot in sorted(os.listdir(md)):
        sdir = os.path.join(md, slot)
        fbxs = [f for f in os.listdir(sdir) if f.lower().endswith(".fbx")]
        if not fbxs:
            continue
        ddir = os.path.join(ART, "Models", slot)
        if os.path.isdir(ddir):
            shutil.rmtree(ddir)
        shutil.copytree(sdir, ddir)
        n += 1
    log(f"models: {n} real props")


def app_icon():
    S = 1024
    yy, xx = np.mgrid[0:S, 0:S] / (S - 1.0)
    r = np.sqrt((xx - 0.5) ** 2 + (yy - 0.45) ** 2)
    bgc = lerp(col((70, 12, 14)), col((8, 6, 8)), np.clip(r * 1.6, 0, 1)[..., None])
    img = Image.fromarray(np.clip(bgc * 255, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    sil = (6, 5, 6)
    d.ellipse([S * 0.33, S * 0.2, S * 0.67, S * 0.66], fill=sil)                       # head
    d.ellipse([S * 0.41, S * 0.08, S * 0.59, S * 0.26], fill=sil)                      # bun
    d.polygon([(S * 0.2, S), (S * 0.3, S * 0.72), (S * 0.5, S * 0.64), (S * 0.7, S * 0.72), (S * 0.8, S)], fill=sil)
    for cx in (0.42, 0.58):
        d.ellipse([S * (cx - 0.075), S * 0.38, S * (cx + 0.075), S * 0.53], outline=(235, 235, 230), width=14)
        d.ellipse([S * (cx - 0.02), S * 0.43, S * (cx + 0.02), S * 0.48], fill=(230, 40, 30))
    d.line([(S * 0.495, S * 0.45), (S * 0.505, S * 0.45)], fill=(235, 235, 230), width=10)
    d.line([(S * 0.6, S * 0.41), (S * 0.63, S * 0.45), (S * 0.615, S * 0.5)], fill=(235, 235, 230), width=5)
    d.polygon([(S * 0.72, S * 0.92), (S * 0.9, S * 0.3), (S * 0.94, S * 0.31), (S * 0.77, S * 0.93)], fill=(165, 110, 60))
    img = img.filter(ImageFilter.GaussianBlur(0.8))
    img.save(out("Icons", "app_icon.png"))


def fonts():
    fdir = src("fonts")
    need = ["Barlow-Medium.ttf", "Barlow-SemiBold.ttf", "Creepster-Regular.ttf", "CabinSketch-Bold.ttf"]
    for f in need:
        p = os.path.join(fdir, f)
        if os.path.exists(p) and os.path.getsize(p) > 10000:
            shutil.copyfile(p, out("Fonts", f))
        else:
            for fb in FONT_FALLBACK:
                if os.path.exists(fb):
                    shutil.copyfile(fb, out("Fonts", f))
                    log(f"font {f}: fallback {os.path.basename(fb)}")
                    break


# ============================================================================ audio
SR = 22050


def write_wav(name, x):
    x = np.clip(np.asarray(x, np.float64), -1, 1)
    with wave.open(out("Audio", name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def butter(x, kind, f, order=2):
    wn = [min(0.99, fi / (SR / 2)) for fi in f] if isinstance(f, (list, tuple)) else min(0.99, f / (SR / 2))
    return signal.sosfilt(signal.butter(order, wn, btype=kind, output="sos"), x)


def env(n, a, d, curve=3.0):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * curve / max(d, 1e-4))


def loopify(x, fade):
    n = int(fade * SR)
    head, tail = x[:n].copy(), x[-n:].copy()
    w = np.linspace(0, 1, n)
    x = x[:-n].copy()
    x[:n] = head * w + tail * (1 - w)
    return x


def norm(x, peak=0.9):
    return x / max(np.abs(x).max(), 1e-9) * peak


def noise(n, r=None):
    return (r or RNG).standard_normal(n)


def pink(n):
    w = RNG.standard_normal(n)
    f = np.fft.rfftfreq(n)
    f[0] = f[1]
    p = np.fft.irfft(np.fft.rfft(w) / np.sqrt(f), n)
    return p / np.abs(p).max()


def tone(f, dur, decay=4.0, harm=((1, 1.0),)):
    t = np.arange(int(dur * SR)) / SR
    return sum(a * np.sin(2 * np.pi * f * k * t) for k, a in harm) * np.exp(-t * decay)


def sweep(f0, f1, dur):
    m = int(dur * SR)
    f = np.geomspace(f0, f1, m)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


def mix(n, *parts):
    y = np.zeros(n)
    for off, x in parts:
        o = int(off * SR)
        L = min(len(x), n - o)
        if L > 0:
            y[o:o + L] += x[:L]
    return y


def reverb(x, size=0.35, wet=0.35):
    n = int(SR * (0.6 + size * 2.5))
    ir = RNG.standard_normal(n) * np.exp(-np.arange(n) / SR * (3.5 / (0.3 + size)))
    ir = butter(ir, "lowpass", 3500)
    ir[:int(SR * 0.012)] = 0
    y = signal.fftconvolve(x, ir)
    y = np.concatenate([y, np.zeros(len(x) + n - len(y))])[: len(x) + n]
    y = y / max(np.abs(y).max(), 1e-9) * np.abs(x).max()
    out_ = np.concatenate([x, np.zeros(n)]) * (1 - wet) + y * wet
    return out_


def creak(dur, f0, f1, rough=0.6, seed=1):
    r = np.random.default_rng(seed)
    m = int(dur * SR)
    f = np.interp(np.arange(m), np.linspace(0, m, 8), np.geomspace(f0, f1, 8) * r.uniform(0.9, 1.1, 8))
    ph = np.cumsum(f) / SR
    pulses = (np.sin(2 * np.pi * ph) > 1 - rough * 0.3).astype(float)
    x = butter(pulses * (0.6 + 0.4 * r.random(m)), "bandpass", [300, 3200])
    return x * np.sin(np.linspace(0, np.pi, m)) ** 0.5


def audio():
    W = write_wav
    # ---- UI / items
    W("ui_click", norm(tone(1500, 0.06, 60, ((1, 1), (2, 0.3))) + butter(noise(int(SR * 0.06)), "highpass", 3000) * env(int(SR * 0.06), 0.001, 0.01, 5) * 0.3, 0.5))
    W("pickup", norm(mix(int(SR * 0.5), (0, butter(noise(int(SR * 0.08)), "bandpass", [800, 5000]) * env(int(SR * 0.08), 0.002, 0.04, 5)),
                         (0.02, tone(620, 0.45, 9, ((1, 1), (2.7, 0.4))) * 0.5)), 0.6))
    W("drop", norm(mix(int(SR * 0.5), (0, butter(noise(int(SR * 0.2)), "lowpass", 900) * env(int(SR * 0.2), 0.002, 0.06, 6)),
                       (0.11, butter(noise(int(SR * 0.12)), "lowpass", 1200) * env(int(SR * 0.12), 0.001, 0.04, 6) * 0.4)), 0.8))
    # ---- doors
    n = int(SR * 1.4)
    W("door_open", norm(reverb(mix(n, (0, butter(noise(int(SR * 0.08)), "bandpass", [600, 3000]) * env(int(SR * 0.08), 0.002, 0.03, 6) * 0.6),
                                   (0.08, creak(1.1, 380, 620, seed=2))), 0.25, 0.25), 0.7))
    n = int(SR * 0.8)
    thud = butter(noise(n), "lowpass", 220) * env(n, 0.002, 0.15, 6)
    latch = butter(noise(int(SR * 0.05)), "highpass", 2000) * env(int(SR * 0.05), 0.0005, 0.01, 5)
    W("door_close", norm(reverb(mix(n, (0, thud), (0.01, latch * 0.5)), 0.3, 0.3), 0.85))
    rattles = [(0.09 * k, butter(noise(int(SR * 0.06)), "bandpass", [700, 4000]) * env(int(SR * 0.06), 0.001, 0.02, 6) * (1 - k * 0.1)) for k in range(6)]
    W("door_locked", norm(mix(int(SR * 0.7), *rattles) + mix(int(SR * 0.7), (0, thud[: int(SR * 0.3)] * 0.4)), 0.7))
    W("slam", norm(reverb(mix(int(SR * 1.0), (0, butter(noise(int(SR * 0.6)), "lowpass", 350) * env(int(SR * 0.6), 0.001, 0.2, 7) * 1.5),
                              (0, butter(noise(int(SR * 0.08)), "bandpass", [900, 5000]) * env(int(SR * 0.08), 0.0005, 0.02, 6))), 0.5, 0.35), 0.95))
    # ---- wood / metal impacts
    n = int(SR * 0.9)
    cracks = [(RNG.uniform(0, 0.12), butter(noise(int(SR * 0.05)), "highpass", 900) * env(int(SR * 0.05), 0.0005, 0.015, 6) * RNG.uniform(0.4, 1)) for _ in range(14)]
    W("plank_break", norm(reverb(mix(n, *cracks, (0, butter(noise(int(SR * 0.4)), "lowpass", 400) * env(int(SR * 0.4), 0.002, 0.12, 6))), 0.3, 0.25), 0.9))
    W("ruler_hit", norm(reverb(mix(int(SR * 0.5), (0, butter(noise(int(SR * 0.05)), "bandpass", [1200, 7000]) * env(int(SR * 0.05), 0.0003, 0.015, 6)),
                                   (0, tone(410, 0.3, 18, ((1, 1), (2.3, 0.5))) * 0.4)), 0.2, 0.2), 0.9))
    n = int(SR * 1.3)
    W("trapdoor", norm(reverb(mix(n, (0, creak(0.4, 300, 200, seed=4) * 0.4), (0.42, butter(noise(int(SR * 0.7)), "lowpass", 260) * env(int(SR * 0.7), 0.001, 0.25, 6) * 1.6)), 0.6, 0.35), 0.95))
    W("safe_open", norm(reverb(mix(int(SR * 1.6), (0, tone(150, 0.4, 10, ((1, 1), (3.1, 0.5))) * 0.8), (0.05, butter(noise(int(SR * 0.05)), "highpass", 1500) * 0.4),
                                   (0.3, creak(1.1, 200, 160, seed=5) * 0.6)), 0.3, 0.3), 0.8))
    # ---- keypad
    W("keypad_beep", norm(tone(1250, 0.09, 25), 0.45))
    W("keypad_ok", norm(mix(int(SR * 0.45), (0, tone(990, 0.12, 15)), (0.13, tone(1480, 0.25, 12))), 0.5))
    W("keypad_no", norm(mix(int(SR * 0.5), (0, tone(330, 0.18, 6, ((1, 1), (3, 0.3)))), (0.2, tone(260, 0.25, 6, ((1, 1), (3, 0.3))))), 0.5))
    # ---- fire / water / steam
    n = SR * 6
    fl = butter(pink(n), "lowpass", 700) * 0.35
    for _ in range(320):
        p = int(RNG.integers(0, n - 800))
        L = int(RNG.integers(60, 600))
        fl[p:p + L] += butter(noise(L), "highpass", 1600) * env(L, 0.0005, 0.008, 6) * RNG.uniform(0.15, 0.9)
    W("fire_loop", norm(loopify(fl, 0.5), 0.6))
    n = int(SR * 1.0)
    W("fire_whoosh", norm(butter(noise(n), "bandpass", [200, 1800]) * np.sin(np.linspace(0, np.pi, n)) ** 1.5 * env(n, 0.15, 0.7, 2), 0.85))
    n = SR * 5
    W("water", norm(loopify(butter(noise(n), "bandpass", [700, 7000]) * (0.8 + 0.2 * butter(noise(n), "lowpass", 4)), 0.4), 0.55))
    n = int(SR * 2.5)
    W("steam", norm(butter(noise(n), "highpass", 2500) * env(n, 0.05, 2.0, 2.5), 0.6))
    n = SR * 3
    fz = butter(noise(n), "highpass", 3000) * (0.6 + 0.4 * np.abs(butter(noise(n), "lowpass", 30)))
    W("fuse", norm(loopify(fz, 0.3), 0.5))
    # ---- explosion
    n = int(SR * 3.5)
    boom = butter(noise(n), "lowpass", 160) * env(n, 0.003, 1.4, 3) * 2 + butter(noise(n), "bandpass", [300, 3000]) * env(n, 0.001, 0.35, 5)
    debris = [(0.15 + RNG.uniform(0, 1.6), butter(noise(int(SR * 0.05)), "bandpass", [800, 4000]) * env(int(SR * 0.05), 0.001, 0.02, 6) * RNG.uniform(0.1, 0.4)) for _ in range(40)]
    W("explosion", norm(mix(n, (0, boom), *debris), 0.98))
    # ---- misc
    n = int(SR * 0.7)
    crunch = [(RNG.uniform(0, 0.45), butter(noise(int(SR * 0.03)), "bandpass", [500, 4000]) * env(int(SR * 0.03), 0.001, 0.01, 6) * RNG.uniform(0.3, 1)) for _ in range(18)]
    W("eat", norm(mix(n, *crunch), 0.7))
    n = int(SR * 3.2)
    t = np.arange(n) / SR
    ring = (np.sin(2 * np.pi * 980 * t) + 0.6 * np.sin(2 * np.pi * 2210 * t) + 0.3 * np.sin(2 * np.pi * 3420 * t)) * (0.6 + 0.4 * (np.sin(2 * np.pi * 24 * t) > 0))
    W("bell", norm(reverb(ring * env(n, 0.01, 3.0, 1.2) * (t < 2.5), 0.5, 0.3), 0.6))
    n = SR * 4
    t = np.arange(n) / SR
    motor = (np.sin(2 * np.pi * 95 * t) + 0.5 * np.sin(2 * np.pi * 190 * t) + 0.25 * np.sign(np.sin(2 * np.pi * 47.5 * t))) * 0.5 + butter(noise(n), "bandpass", [300, 1500]) * 0.25
    W("motor", norm(motor * np.minimum(1, t / 0.2) * np.minimum(1, (4 - t) / 0.4), 0.55))
    n = int(SR * 0.5)
    pop = butter(noise(int(SR * 0.05)), "highpass", 1500) * env(int(SR * 0.05), 0.0003, 0.02, 6)
    zap = butter(noise(n), "bandpass", [2000, 6000]) * (np.sin(np.arange(n) / SR * 2 * np.pi * 60) > 0.6) * env(n, 0.001, 0.3, 4) * 0.4
    W("light_pop", norm(mix(n, (0, pop), (0.02, zap)), 0.8))
    W("jump", norm(butter(noise(int(SR * 0.22)), "bandpass", [300, 2000]) * env(int(SR * 0.22), 0.02, 0.12, 4), 0.4))
    n = int(SR * 0.35)
    W("land", norm(butter(noise(n), "lowpass", 300) * env(n, 0.002, 0.1, 6), 0.8))
    # music box (original melody, A minor)
    notes = [(0, 69), (0.4, 72), (0.8, 76), (1.2, 74), (1.6, 72), (2.0, 71), (2.4, 69), (3.2, 64), (3.6, 69), (4.0, 71), (4.4, 72), (4.8, 71), (5.2, 69), (6.0, 68)]
    n = int(SR * 7.5)
    mb = mix(n, *[(o, tone(440 * 2 ** ((m - 69) / 12), 1.4, 3.5, ((1, 1), (3.0, 0.25), (5.1, 0.1)))) for o, m in notes])
    W("music_box", norm(reverb(mb, 0.4, 0.3), 0.5))
    # ---- footsteps
    def step(kind, seed):
        r = np.random.default_rng(seed)
        m = int(SR * 0.28)
        x = np.zeros(m)
        if kind == "concrete":
            x += butter(r.standard_normal(m), "bandpass", [120, 900]) * env(m, 0.002, 0.05, 7) * 1.2
            for _ in range(8):
                o, L = int(r.uniform(0, 0.03) * SR), int(r.uniform(30, 120))
                x[o:o + L] += butter(r.standard_normal(L), "highpass", 2500) * env(L, 0.0002, 0.002, 5) * 0.5
        elif kind == "wood":
            t2 = np.arange(m) / SR
            f = r.uniform(110, 170)
            x += (np.sin(2 * np.pi * f * t2) + 0.5 * np.sin(2 * np.pi * f * 2.6 * t2)) * env(m, 0.002, 0.07, 6)
            x += butter(r.standard_normal(m), "bandpass", [250, 2200]) * env(m, 0.001, 0.03, 6) * 0.6
            if r.random() < 0.5:
                ck = creak(0.25, 500, 700, seed=seed)[:m]
                x[:len(ck)] += ck * 0.15
        elif kind == "tile":
            x += butter(r.standard_normal(m), "bandpass", [600, 4500]) * env(m, 0.0008, 0.035, 7) * 1.1
            x += butter(r.standard_normal(m), "lowpass", 300) * env(m, 0.002, 0.04, 6) * 0.5
        elif kind == "metal":
            t2 = np.arange(m) / SR
            x += sum(np.sin(2 * np.pi * f * t2) * a for f, a in ((520, 1), (1310, 0.6), (2270, 0.4))) * env(m, 0.001, 0.12, 5) * 0.6
            x += butter(r.standard_normal(m), "bandpass", [400, 3000]) * env(m, 0.001, 0.03, 6) * 0.6
        elif kind == "heel":
            x += butter(r.standard_normal(m), "bandpass", [1500, 6000]) * env(m, 0.0004, 0.025, 7) * 1.3
            x += butter(r.standard_normal(m), "bandpass", [150, 700]) * env(m, 0.001, 0.05, 6) * 0.6
            x = reverb(x, 0.45, 0.35)[: int(SR * 0.6)] if len(x) else x
        return norm(x, 0.85)

    for kind, count in (("concrete", 4), ("wood", 4), ("tile", 4), ("metal", 3)):
        for i in range(count):
            W(f"step_{kind}_{i}", step(kind, sum(map(ord, kind)) * 31 + i))
    for i in range(3):
        W(f"teacher_step_{i}", step("heel", 900 + i))
    # ---- voices: synthesized formant voice (scream, burn scream, hum, laugh)
    def voice(f0_curve, dur, formants, breath=0.15, vib=5.5, vib_amt=0.012, seed=0):
        r = np.random.default_rng(seed)
        m = int(dur * SR)
        t2 = np.arange(m) / SR
        f0 = np.interp(np.linspace(0, 1, m), np.linspace(0, 1, len(f0_curve)), f0_curve)
        f0 = f0 * (1 + vib_amt * np.sin(2 * np.pi * vib * t2) + 0.01 * butter(r.standard_normal(m), "lowpass", 8))
        ph = np.cumsum(f0) / SR
        src_ = 2 * (ph % 1.0) - 1                            # sawtooth glottal source
        src_ = src_ + breath * r.standard_normal(m)
        y = np.zeros(m)
        for fc, bw, g in formants:
            y += butter(src_, "bandpass", [max(50, fc - bw / 2), fc + bw / 2]) * g
        return y

    n = int(SR * 2.2)
    scream = voice([700, 1150, 1250, 1180, 1100, 900], 2.0, [(900, 300, 1.0), (1500, 400, 0.8), (2900, 600, 0.6), (4200, 900, 0.3)], breath=0.5, vib=9, vib_amt=0.03, seed=1)
    scream = np.tanh(scream * 3) * env(len(scream), 0.03, 1.8, 1.2)
    W("scream", norm(reverb(scream, 0.4, 0.3), 0.98))
    burn = voice([900, 1300, 1000, 1400, 800, 500], 2.6, [(800, 300, 1.0), (1300, 400, 0.8), (2700, 700, 0.5)], breath=0.6, vib=11, vib_amt=0.05, seed=2)
    burn = np.tanh(burn * 2.5) * env(len(burn), 0.05, 2.4, 1.0)
    fz2 = butter(noise(len(burn)), "bandpass", [300, 3000]) * 0.2
    W("burn_scream", norm(reverb(burn + fz2, 0.4, 0.3), 0.95))
    # humming an eerie lullaby, loopable
    hum_notes = [57, 60, 64, 62, 60, 59, 57, 57, 52, 57, 59, 60, 59, 57, 56, 57]
    seg = []
    for k, m_ in enumerate(hum_notes):
        f = 440 * 2 ** ((m_ - 69) / 12)
        L = 0.55 if k % 4 != 3 else 0.85
        s_ = voice([f, f], L, [(300, 150, 1.0), (900, 250, 0.25), (2400, 400, 0.08)], breath=0.08, vib=5, vib_amt=0.02, seed=10 + k)
        s_ *= np.sin(np.linspace(0, np.pi, len(s_))) ** 0.6
        seg.append(s_)
    hum = np.concatenate(seg + [np.zeros(int(SR * 1.5))])
    W("teacher_hum", norm(loopify(butter(hum, "lowpass", 2500), 0.4), 0.6))
    laughs = []
    for k in range(7):
        f = 520 - k * 25
        s_ = voice([f * 1.2, f], 0.17, [(800, 300, 1.0), (1200, 300, 0.7), (2600, 600, 0.4)], breath=0.7, vib=0, vib_amt=0, seed=20 + k)
        laughs.append(s_ * env(len(s_), 0.01, 0.15, 3))
        laughs.append(np.zeros(int(SR * 0.07)))
    W("teacher_laugh", norm(reverb(np.concatenate(laughs), 0.6, 0.4), 0.8))
    # ---- music / ambience loops
    n = SR * 6
    t = np.arange(n) / SR
    beat = 60 / 140
    hb = np.zeros(n)
    for k in range(int(6 / beat)):
        for o, a in ((0, 1.0), (0.17, 0.7)):
            p = int((k * beat + o) * SR)
            L = int(SR * 0.15)
            if p + L < n:
                hb[p:p + L] += butter(noise(L), "lowpass", 90) * env(L, 0.004, 0.06, 6) * a + np.sin(2 * np.pi * 48 * np.arange(L) / SR) * env(L, 0.003, 0.08, 6) * a
    W("heartbeat", norm(hb, 0.9))
    # chase: driving low ostinato + screeching strings + percussion (original), 8 s loop
    n = SR * 8
    t = np.arange(n) / SR
    bass = np.zeros(n)
    pat = [45, 45, 46, 45, 45, 45, 48, 46]
    for k in range(32):
        p = int(k * 0.25 * SR)
        f = 440 * 2 ** ((pat[k % 8] - 69) / 12)
        L = int(SR * 0.24)
        bass[p:p + L] += np.sign(np.sin(2 * np.pi * f * np.arange(L) / SR)) * env(L, 0.005, 0.2, 3)
    bass = butter(bass, "lowpass", 600)
    strings = sum(np.sin(2 * np.pi * f * t + 3 * np.sin(2 * np.pi * 6 * t)) for f in (880, 932.3)) * (0.5 + 0.5 * np.sin(2 * np.pi * t / 8)) * 0.25
    perc = np.zeros(n)
    for k in range(16):
        p = int(k * 0.5 * SR)
        L = int(SR * 0.3)
        perc[p:p + L] += butter(noise(L), "lowpass", 140) * env(L, 0.002, 0.15, 5) * (1.2 if k % 2 == 0 else 0.7)
    W("chase_loop", norm(bass * 0.6 + strings + perc * 0.8, 0.8))
    # ambient drone: dark pads + air, 20 s loop
    n = SR * 20
    t = np.arange(n) / SR
    pad = sum(np.sin(2 * np.pi * f * t + 0.8 * np.sin(2 * np.pi * 0.07 * t * (i + 1))) * a for i, (f, a) in enumerate(((55, 1.0), (82.4, 0.5), (110.8, 0.3), (164.8, 0.12))))
    air = butter(pink(n), "bandpass", [200, 1200]) * 0.4 * (0.6 + 0.4 * np.sin(2 * np.pi * t / 10))
    W("ambient_loop", norm(loopify(pad * 0.5 + air, 2.0), 0.55))
    # one-shot ambient scares
    W("ambient_0", norm(reverb(creak(2.2, 180, 260, seed=31), 0.7, 0.45), 0.7))                       # long creak
    knocks = [(k * 0.35, butter(noise(int(SR * 0.12)), "lowpass", 300) * env(int(SR * 0.12), 0.002, 0.05, 6)) for k in range(3)]
    W("ambient_1", norm(reverb(mix(int(SR * 1.4), *knocks), 0.7, 0.4), 0.8))                            # three knocks
    wh = butter(noise(SR * 2), "bandpass", [2000, 6000]) * (np.abs(butter(noise(SR * 2), "lowpass", 6)) > 0.25)
    W("ambient_2", norm(reverb(wh * np.sin(np.linspace(0, np.pi, SR * 2)), 0.7, 0.5), 0.45))             # whisper-like
    W("ambient_3", norm(reverb(tone(210, 1.5, 2, ((1, 1), (2.76, 0.6), (5.4, 0.3))), 0.8, 0.5), 0.6))    # distant metal clank
    howl = butter(noise(SR * 3), "bandpass", [400, 900]) * np.sin(np.linspace(0, np.pi, SR * 3)) ** 2
    W("ambient_4", norm(howl, 0.5))                                                                     # wind howl
    W("ambient_5", norm(reverb(mix(int(SR * 1.5), (0, step("heel", 950)), (0.6, step("heel", 951)), (1.2, step("heel", 952))), 0.9, 0.5), 0.5))  # far footsteps


def main():
    os.makedirs(ART, exist_ok=True)
    textures()
    decals()
    fx()
    ui()
    teacher()
    rocketbox_teacher()
    models()
    app_icon()
    fonts()
    audio()
    log("done")


if __name__ == "__main__":
    main()
