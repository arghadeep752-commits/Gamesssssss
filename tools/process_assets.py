#!/usr/bin/env python3
"""Turns the downloaded Poly Haven sources (tools/fetch_assets.py) into the
files the Unity project uses, and generates the sounds, UI sprites and icon.

Usage: python3 tools/process_assets.py <sources_dir> <project_dir>
Writes <project_dir>/Assets/Art/... and Assets/Art/art.json (sun, fog, ambient
light and atlas layout read by the editor build script).
"""
import json
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
RNG = np.random.default_rng(20261031)
INFO = {}

SUN_INTENSITY = 1.6      # Unity directional light intensity
SKY_STORE = 0.6          # sky texture stores K*L*SKY_STORE; skybox exposure undoes it


def out(*p):
    path = os.path.join(ART, *p)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    return path


def src(*p):
    return os.path.join(SRC, *p)


def log(*a):
    print("[assets]", *a, flush=True)


# ----------------------------------------------------------------------------- colour helpers
def srgb_to_lin(c):
    c = np.asarray(c, np.float32)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(np.asarray(c, np.float32), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1 / 2.4) - 0.055)


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


def save_rgb(a, path, quality=None):
    im = Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), "RGB")
    if path.endswith(".jpg"):
        im.save(path, quality=quality or 93, subsampling=0)
    else:
        im.save(path, optimize=False)


def save_rgba(a, path):
    Image.fromarray(np.clip(a * 255 + 0.5, 0, 255).astype(np.uint8), "RGBA").save(path)


def bleed(rgb, alpha, thr=0.3):
    """Fill RGB of transparent pixels with the nearest opaque colour (no dark fringes)."""
    solid = alpha > thr
    if solid.all() or not solid.any():
        return rgb
    _, (iy, ix) = ndimage.distance_transform_edt(~solid, return_indices=True)
    filled = rgb[iy, ix]
    out_rgb = np.where(solid[..., None], rgb, filled)
    return out_rgb


def normal_png(path_in, path_out, size, strength=1.0, flip_g=False):
    n = load_rgb(path_in, size)
    v = n * 2 - 1
    if flip_g:
        v[..., 1] *= -1
    v[..., 0] *= strength
    v[..., 1] *= strength
    v /= np.maximum(np.linalg.norm(v, axis=2, keepdims=True), 1e-6)
    save_rgb(v * 0.5 + 0.5, path_out)


# ----------------------------------------------------------------------------- HDR sky
def read_hdr(path):
    with open(path, "rb") as f:
        data = f.read()
    pos = 0
    while True:
        e = data.index(b"\n", pos)
        line = data[pos:e]
        pos = e + 1
        if line.startswith(b"-Y") or line.startswith(b"+Y"):
            parts = line.split()
            H, W = int(parts[1]), int(parts[3])
            break
    buf = np.frombuffer(data, dtype=np.uint8, offset=pos)
    rgbe = np.empty((H, W, 4), np.uint8)
    p = 0
    for y in range(H):
        if int(buf[p]) == 2 and int(buf[p + 1]) == 2 and ((int(buf[p + 2]) << 8) | int(buf[p + 3])) == W:
            p += 4
            for c in range(4):
                x = 0
                row = rgbe[y, :, c]
                while x < W:
                    n = int(buf[p])
                    p += 1
                    if n > 128:
                        n -= 128
                        row[x:x + n] = buf[p]
                        p += 1
                    else:
                        row[x:x + n] = buf[p:p + n]
                        p += n
                    x += n
        else:
            rgbe[y] = buf[p:p + W * 4].reshape(W, 4)
            p += W * 4
    ex = rgbe[..., 3].astype(np.int32)
    scale = np.where(ex > 0, np.ldexp(1.0, ex - 136), 0.0).astype(np.float32)
    return rgbe[..., :3].astype(np.float32) * scale[..., None]


def area_resize(img, w, h):
    """Box-filter downsample of a float image (exact integer factors)."""
    H, W, C = img.shape
    fy, fx = H // h, W // w
    return img[:h * fy, :w * fx].reshape(h, fy, w, fx, C).mean(axis=(1, 3))


def sky():
    path = None
    for aid in os.listdir(SRC):
        d = src(aid)
        if os.path.isdir(d):
            for f in os.listdir(d):
                if f.startswith("hdri_") and f.endswith(".hdr"):
                    path = os.path.join(d, f)
    if not path:
        raise SystemExit("no HDRI downloaded")
    log("sky from", path)
    img = read_hdr(path)
    H, W, _ = img.shape
    lum = img @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    theta = (np.arange(H) + 0.5) / H * np.pi
    dw_row = (2 * np.pi / W) * (np.pi / H) * np.sin(theta)

    # The sun: the very bright pixels.  Its irradiance sets the scale K so the
    # directional light (intensity SUN_INTENSITY) and the sky agree physically
    # (Unity's light intensity == irradiance / pi).
    thr = max(50.0, float(lum.max()) * 0.002)
    sun = lum > thr
    rows, cols = np.nonzero(sun)
    w = lum[sun] * dw_row[rows]
    th = (rows + 0.5) / H * np.pi
    ph = (0.5 - (cols + 0.5) / W) * 2 * np.pi          # Unity Skybox/Panoramic mapping
    dirs = np.stack([np.sin(th) * np.cos(ph), np.cos(th), np.sin(th) * np.sin(ph)], 1)
    sun_dir = (dirs * w[:, None]).sum(0)
    sun_dir /= np.linalg.norm(sun_dir)
    e_sun = (img[sun] * dw_row[rows][:, None]).sum(0)
    e_sun_lum = float(e_sun @ np.array([0.2126, 0.7152, 0.0722]))
    sun_color = e_sun / e_sun.max()
    K = SUN_INTENSITY * math.pi / e_sun_lum
    log(f"sun dir {sun_dir} elevation {math.degrees(math.asin(sun_dir[1])):.1f} K={K:.3f} color {sun_color}")

    # sun removed (clamped) for the ambient light; kept in the visible sky texture
    lim = float(np.percentile(lum[: H // 2], 99.0)) * 3.0
    clamp = np.minimum(1.0, lim / np.maximum(lum, 1e-6))[..., None]
    sky_nosun = img * clamp

    # visible sky texture (sRGB), 4096x2048, mip-less in Unity
    tex = img * (K * SKY_STORE)
    if W != 4096:
        tex = ndimage.zoom(tex, (2048 / H, 4096 / W, 1), order=1)
    save_rgb(lin_to_srgb(tex), out("Sky", "sky_pano.png"))
    # reflections / water: 1024x512 area-averaged
    refl = area_resize(img * K, 1024, 512)
    save_rgb(lin_to_srgb(refl), out("Sky", "sky_reflect.png"))
    # same image, imported by Unity as the reflection cubemap (latitude-longitude layout)
    save_rgb(lin_to_srgb(refl), out("Sky", "sky_cube.png"))

    # horizon colour -> fog
    r0, r1 = int(H / 2 - 7 / 180 * H), int(H / 2 - 1 / 180 * H)
    horizon = (sky_nosun[r0:r1] * K).reshape(-1, 3).mean(0)
    # ambient grid 32x16 (linear radiance, K-scaled); lower half = light bounced off the ground
    grid = area_resize(sky_nosun * K, 32, 16)
    e_sky_h = float(((sky_nosun[: H // 2] * K) @ np.array([0.2126, 0.7152, 0.0722]) * (dw_row * np.cos(theta))[: H // 2, None]).sum())
    ground_albedo = np.array([0.16, 0.17, 0.11])
    ground = ground_albedo * (SUN_INTENSITY * max(sun_dir[1], 0.0) * sun_color + e_sky_h / math.pi)
    for r in range(8, 16):
        t = (r - 8) / 7.0
        grid[r, :, :] = horizon * (1 - t) * 0.35 + ground * (0.65 + 0.35 * t)
    # expected diffuse ambient (irradiance / pi, L2 band-limited) for an up- and a down-facing surface,
    # used by the build script to calibrate Unity's SH probe
    gh, gw = grid.shape[:2]
    gth = (np.arange(gh) + 0.5) / gh * np.pi
    gdw = (2 * np.pi / gw) * (np.pi / gh) * np.sin(gth)
    cy = np.cos(gth)
    def l2(c):
        return (0.25 + 0.5 * c + (5.0 / 16.0) * (3 * c * c - 1) / 2) * 16.0 / 17.0
    amb_up = (grid * (gdw / np.pi * l2(cy))[:, None, None]).sum(axis=(0, 1))
    amb_down = (grid * (gdw / np.pi * l2(-cy))[:, None, None]).sum(axis=(0, 1))
    INFO.update({
        "ambientUp": [float(x) for x in amb_up],
        "ambientDown": [float(x) for x in amb_down],
        "sunDir": [float(x) for x in sun_dir],
        "sunColor": [float(x) for x in sun_color],
        "sunIntensity": SUN_INTENSITY,
        "skyExposure": 1.0 / SKY_STORE,
        "fogColorLinear": [float(x) for x in horizon],
        "shW": 32, "shH": 16,
        "shGrid": [round(float(x), 5) for x in grid.reshape(-1)],
    })
    log(f"horizon {horizon} ground {ground} e_sky_h {e_sky_h:.3f} ambient up {amb_up} down {amb_down}")
    return np.clip(lin_to_srgb(tex), 0, 1)


# ----------------------------------------------------------------------------- terrain layers
TERRAIN = {
    # name: (asset, out size, tile metres, albedo tint)
    "grass": ("forrest_ground_01", 2048, 2.4, (1.0, 1.0, 1.0)),
    "dirt": ("forest_ground_04", 2048, 3.2, (1.0, 1.0, 1.0)),
    "rock": ("lichen_rock", 1024, 6.0, (1.0, 1.0, 1.0)),
    "shore": ("river_small_rocks", 2048, 2.5, (1.0, 1.0, 1.0)),
}


def terrain():
    layers = {}
    for name, (aid, size, tile, tint) in TERRAIN.items():
        d = src(aid)
        alb = load_rgb(os.path.join(d, "Diffuse.jpg"), size)
        rough = load_gray(os.path.join(d, "Rough.jpg"), size)
        ao_path = os.path.join(d, "AO.jpg")
        if os.path.exists(ao_path):
            ao = load_gray(ao_path, size)
            alb = alb * (0.55 + 0.45 * ao[..., None])
        alb = np.clip(alb * np.array(tint, np.float32), 0, 1)
        smooth = np.clip(1.0 - rough, 0, 1) * 0.85
        save_rgba(np.dstack([alb, smooth]), out("Terrain", f"{name}_albedo.png"))
        normal_png(os.path.join(d, "nor_gl.png"), out("Terrain", f"{name}_normal.png"), size)
        mean = lin_to_srgb(srgb_to_lin(alb).reshape(-1, 3).mean(0))
        layers[name] = {"tile": tile, "mean": [float(x) for x in mean]}
        log("terrain layer", name, aid, "mean", mean)
    INFO["terrainLayers"] = layers


# ----------------------------------------------------------------------------- foliage atlases
def components(alpha, thr=0.08, close=9):
    m = alpha > thr
    m2 = ndimage.binary_closing(m, structure=np.ones((close, close)))
    m2 = ndimage.binary_dilation(m2, iterations=3)
    lab, n = ndimage.label(m2)
    return lab, ndimage.find_objects(lab)


def cut(rgb, alpha, lab, objs, box):
    """Isolated crop of the component whose bbox best matches `box` (x0,y0,x1,y1)."""
    bx0, by0, bx1, by1 = box
    best, best_iou = None, 0
    for i, sl in enumerate(objs):
        if sl is None:
            continue
        y0, y1, x0, x1 = sl[0].start, sl[0].stop, sl[1].start, sl[1].stop
        ix = max(0, min(x1, bx1) - max(x0, bx0))
        iy = max(0, min(y1, by1) - max(y0, by0))
        inter = ix * iy
        union = (x1 - x0) * (y1 - y0) + (bx1 - bx0) * (by1 - by0) - inter
        iou = inter / max(union, 1)
        if iou > best_iou:
            best, best_iou = i, iou
    sl = objs[best]
    m = (lab[sl] == best + 1)
    a = alpha[sl] * m
    c = rgb[sl]
    # tighten
    ys, xs = np.nonzero(a > 0.02)
    a = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    c = c[ys.min():ys.max() + 1, xs.min():xs.max() + 1]
    return c, a


def place(atlas_rgb, atlas_a, c, a, cell, pad=6, align="bottom"):
    """Scale (c,a) into the pixel cell (x0,y0,x1,y1); returns the used UV rect."""
    x0, y0, x1, y1 = cell
    cw, ch = x1 - x0 - 2 * pad, y1 - y0 - 2 * pad
    h, w = a.shape
    s = min(cw / w, ch / h)
    nw, nh = max(1, int(w * s)), max(1, int(h * s))
    ci = Image.fromarray((np.clip(c, 0, 1) * 255).astype(np.uint8), "RGB").resize((nw, nh), Image.LANCZOS)
    ai = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "L").resize((nw, nh), Image.LANCZOS)
    ox = x0 + pad + (cw - nw) // 2
    oy = (y1 - pad - nh) if align == "bottom" else (y0 + pad + (ch - nh) // 2)
    atlas_rgb[oy:oy + nh, ox:ox + nw] = np.asarray(ci).astype(np.float32) / 255
    atlas_a[oy:oy + nh, ox:ox + nw] = np.asarray(ai).astype(np.float32) / 255
    S = atlas_a.shape[0]
    return [ox / S, 1 - (oy + nh) / S, (ox + nw) / S, 1 - oy / S]


def twigs():
    d = src("fir_tree_01")
    rgb = load_rgb(os.path.join(d, "twig_diff.jpg"))
    alpha = load_gray(os.path.join(d, "twig_alpha.png"))
    ao = load_gray(os.path.join(d, "twig_ao.jpg"))
    rgb = rgb * (0.6 + 0.4 * ao[..., None])
    lab, objs = components(alpha)
    boxes = [(622, 815, 1324, 1592), (1295, 923, 1964, 1704), (384, 92, 881, 642), (1333, 79, 1924, 759)]
    S = 1024
    A_rgb = np.zeros((S, S, 3), np.float32)
    A_a = np.zeros((S, S), np.float32)
    cells = [(0, 512, 512, 1024), (512, 512, 1024, 1024), (0, 0, 512, 512), (512, 0, 1024, 512)]
    rects = []
    for box, cell in zip(boxes, cells):
        c, a = cut(rgb, alpha, lab, objs, box)
        rects += place(A_rgb, A_a, c, a, cell)
    # slightly deeper, less yellow needles (reads better at distance)
    lin = srgb_to_lin(A_rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lin = lum[..., None] + (lin - lum[..., None]) * 0.9
    lin *= np.array([0.86, 0.92, 0.86], np.float32)
    A_rgb = lin_to_srgb(lin)
    A_rgb = bleed(A_rgb, A_a)
    save_rgba(np.dstack([A_rgb, A_a]), out("Trees", "twig_atlas.png"))
    INFO["twigRects"] = [round(x, 5) for x in rects]
    solid = A_a > 0.5
    log("twig atlas mean", lin_to_srgb(srgb_to_lin(A_rgb)[solid].mean(0)))

    # bark (fir)
    alb = load_rgb(os.path.join(d, "bark_diff.jpg"), 1024)
    # a touch more contrast so the trunks do not look flat
    lin = srgb_to_lin(alb)
    m = lin.reshape(-1, 3).mean(0)
    lin = np.clip(m + (lin - m) * 1.25, 0, 1) * 1.05
    save_rgb(lin_to_srgb(lin), out("Trees", "bark_albedo.jpg"))
    normal_png(os.path.join(d, "bark_nor_gl.png"), out("Trees", "bark_normal.png"), 1024, strength=1.3)
    rough = load_gray(os.path.join(d, "bark_rough.jpg"), 1024)
    mask = np.dstack([np.zeros_like(rough), np.ones_like(rough), np.zeros_like(rough), (1 - rough) * 0.6])
    save_rgba(mask, out("Trees", "bark_mask.png"))


GRASS_SOURCES = {
    # (asset, approx bbox) -> kind 0 = tall plant (portrait cell), 1 = wide tuft, 2 = square tuft
    "tall": [("grass_bermuda_01", (727, 57, 967, 641)), ("grass_bermuda_01", (468, 1287, 792, 2021)),
             ("grass_bermuda_01", (863, 1401, 1262, 2032)), ("grass_bermuda_01", (1426, 1358, 1774, 2031))],
    "wide": [("grass_bermuda_01", (1394, 221, 1944, 490)), ("grass_medium_01", (486, 1806, 1029, 2047))],
    "square": [("grass_bermuda_01", (1100, 735, 1470, 1122)), ("grass_bermuda_01", (570, 825, 946, 1105)),
               ("grass_bermuda_01", (103, 855, 384, 1112)), ("grass_bermuda_01", (1589, 655, 1919, 1125))],
}


def grass():
    cache = {}

    def get(aid):
        if aid not in cache:
            d = src(aid)
            rgb = load_rgb(os.path.join(d, "Diffuse.jpg"))
            alpha = load_gray(os.path.join(d, "Alpha.png"))
            lab, objs = components(alpha)
            cache[aid] = (rgb, alpha, lab, objs)
        return cache[aid]

    S = 1024
    A_rgb = np.zeros((S, S, 3), np.float32)
    A_a = np.zeros((S, S), np.float32)
    cells = {
        "tall": [(i * 256, 0, i * 256 + 256, 384) for i in range(4)],
        "wide": [(0, 384, 512, 640), (512, 384, 1024, 640)],
        "square": [(i * 256, 640, i * 256 + 256, 1024) for i in range(4)],
    }
    rects, kinds = [], []
    kind_id = {"tall": 0, "wide": 1, "square": 2}
    for kind, lst in GRASS_SOURCES.items():
        for (aid, box), cell in zip(lst, cells[kind]):
            rgb, alpha, lab, objs = get(aid)
            c, a = cut(rgb, alpha, lab, objs, box)
            rects += place(A_rgb, A_a, c, a, cell, pad=4)
            kinds.append(kind_id[kind])
    # unify the colour a little with the meadow ground and keep it from looking neon
    lin = srgb_to_lin(A_rgb)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    lin = lum[..., None] + (lin - lum[..., None]) * 0.85
    lin *= np.array([0.95, 1.0, 0.85], np.float32)
    A_rgb = bleed(lin_to_srgb(lin), A_a)
    save_rgba(np.dstack([A_rgb, A_a]), out("Grass", "grass_atlas.png"))
    INFO["grassRects"] = [round(x, 5) for x in rects]
    INFO["grassKinds"] = kinds


# ----------------------------------------------------------------------------- models
MODELS = {
    # id: {material key: (diff, nor, arm, alpha)}
    "rock_face_01": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "rock_face_02": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "rock_moss_set_01": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "rock_moss_set_02": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "stone_fire_pit": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "dry_branches_medium_01": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "tree_stump_01": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", None)},
    "fern_02": {"": ("Diffuse.jpg", "nor_gl.png", "arm.jpg", "Alpha.png")},
    "modular_wooden_pier": {"planks": ("planks_diff.jpg", "planks_nor_gl.png", "planks_arm.jpg", None),
                            "poles": ("poles_diff.jpg", "poles_nor_gl.png", "poles_arm.jpg", None)},
    "Lantern_01": {"painted": ("painted_diff.jpg", "painted_nor_gl.png", "painted_arm.jpg", "painted_opacity.png"),
                   "brass": ("brass_diff.jpg", "brass_nor_gl.png", "brass_arm.jpg", "brass_opacity.png")},
}


def models():
    info = {}
    for mid, mats in MODELS.items():
        d = src(mid)
        if not os.path.exists(os.path.join(d, mid + ".fbx")):
            log("model missing", mid)
            continue
        shutil.copyfile(os.path.join(d, mid + ".fbx"), out("Models", mid, mid + ".fbx"))
        minfo = {}
        for key, (diff, nor, arm, alpha) in mats.items():
            tag = key or "main"
            alb = load_rgb(os.path.join(d, diff))
            size = alb.shape[0]
            if size > 1024:
                alb = load_rgb(os.path.join(d, diff), 1024)
                size = 1024
            if alpha and os.path.exists(os.path.join(d, alpha)):
                a = load_gray(os.path.join(d, alpha), size)
                save_rgba(np.dstack([bleed(alb, a), a]), out("Models", mid, f"{tag}_albedo.png"))
            else:
                save_rgb(alb, out("Models", mid, f"{tag}_albedo.jpg"))
            normal_png(os.path.join(d, nor), out("Models", mid, f"{tag}_normal.png"), size)
            armv = load_rgb(os.path.join(d, arm), size)
            mask = np.dstack([armv[..., 2], armv[..., 0], np.zeros_like(armv[..., 0]), 1 - armv[..., 1]])
            save_rgba(mask, out("Models", mid, f"{tag}_mask.png"))
            minfo[tag] = {"alpha": bool(alpha)}
        info[mid] = minfo
        log("model", mid, list(minfo))
    INFO["models"] = list(info.keys())


# ----------------------------------------------------------------------------- water normal map
def water_normal(size=512):
    # height field from a wind-driven spectrum (tileable by construction)
    k = np.fft.fftfreq(size) * size
    kx, ky = np.meshgrid(k, k)
    kk = np.sqrt(kx ** 2 + ky ** 2) + 1e-6
    wind = np.array([0.8, 0.6])
    align = np.abs((kx * wind[0] + ky * wind[1]) / kk) ** 2
    spec = np.exp(-1.0 / (kk / 7.0) ** 2) / kk ** 3.2 * (0.25 + align)
    spec[kk > size * 0.42] = 0
    phase = RNG.random((size, size)) * 2 * np.pi
    h = np.real(np.fft.ifft2(np.sqrt(spec) * np.exp(1j * phase)))
    h /= np.abs(h).max()
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    s = 18.0
    n = np.dstack([-gx * s, gy * s, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    save_rgb(n * 0.5 + 0.5, out("Water", "water_normal.png"))


# ----------------------------------------------------------------------------- audio
SR = 22050


def write_wav(path, x, stereo=False):
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype(np.int16)
    with wave.open(path, "wb") as w:
        w.setnchannels(2 if stereo else 1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def butter(x, kind, f, order=2):
    if isinstance(f, (list, tuple)):
        wn = [min(0.99, fi / (SR / 2)) for fi in f]
    else:
        wn = min(0.99, f / (SR / 2))
    sos = signal.butter(order, wn, btype=kind, output="sos")
    return signal.sosfilt(sos, x, axis=0)


def env(n, a, d, curve=3.0):
    t = np.arange(n) / SR
    e = np.minimum(1, t / max(a, 1e-4)) * np.exp(-np.maximum(0, t - a) * curve / max(d, 1e-4))
    return e


def loopify(x, fade):
    """Seamless loop: crossfade the tail into the head."""
    n = int(fade * SR)
    head, tail = x[:n].copy(), x[-n:].copy()
    w = np.linspace(0, 1, n)
    if x.ndim == 2:
        w = w[:, None]
    x = x[:-n].copy()
    x[:n] = head * w + tail * (1 - w)
    return x


def norm(x, peak=0.9):
    return x / max(np.abs(x).max(), 1e-9) * peak


def pink(n, ch=1):
    w = RNG.standard_normal((n, ch))
    f = np.fft.rfftfreq(n)
    f[0] = f[1]
    W = np.fft.rfft(w, axis=0) / np.sqrt(f)[:, None]
    p = np.fft.irfft(W, n, axis=0)
    return p / np.abs(p).max()


def audio():
    A = lambda name: out("Audio", name)
    # wind: slow gusts over pink noise, a soft high whoosh on gusts
    n = SR * 24
    base = pink(n, 2)
    base = butter(base, "lowpass", 900)
    gust = np.interp(np.arange(n), np.linspace(0, n, 14), RNG.uniform(0.35, 1.0, 14))
    gust = ndimage.gaussian_filter1d(gust, SR * 0.8)
    hi = butter(RNG.standard_normal((n, 2)), "bandpass", [1800, 4200]) * 0.25
    wind = base * (0.45 + 0.55 * gust[:, None]) + hi * (gust[:, None] ** 3)
    write_wav(A("wind.wav"), norm(loopify(wind, 3.0), 0.7), stereo=True)

    # lake: soft lapping
    n = SR * 12
    lap = np.zeros(n)
    t = 0
    while t < n - SR:
        L = int(SR * RNG.uniform(0.25, 0.6))
        burst = butter(RNG.standard_normal(L), "bandpass", [250, 1400]) * env(L, 0.08, 0.35, 4)
        lap[t:t + L] += burst * RNG.uniform(0.4, 1.0)
        t += int(SR * RNG.uniform(0.35, 1.1))
    lap += butter(RNG.standard_normal(n), "lowpass", 300) * 0.15
    write_wav(A("lake.wav"), norm(loopify(lap, 1.0), 0.6))

    # fire crackle
    n = SR * 8
    fire = butter(pink(n)[:, 0], "lowpass", 600) * 0.35
    for _ in range(260):
        p = RNG.integers(0, n - 800)
        L = int(RNG.integers(60, 700))
        fire[p:p + L] += butter(RNG.standard_normal(L), "highpass", 1500) * env(L, 0.0005, 0.01, 6) * RNG.uniform(0.2, 1.0)
    write_wav(A("fire.wav"), norm(loopify(fire, 0.5), 0.6))

    # birds: a few synthetic songbird phrases
    def chirp(f0, f1, dur, vib=0.0, vibf=30.0):
        m = int(dur * SR)
        tt = np.arange(m) / SR
        f = np.geomspace(f0, f1, m) * (1 + vib * np.sin(2 * np.pi * vibf * tt))
        ph = 2 * np.pi * np.cumsum(f) / SR
        e = np.sin(np.pi * np.linspace(0, 1, m)) ** 1.5
        return (np.sin(ph) + 0.25 * np.sin(2 * ph)) * e

    for k in range(6):
        parts = []
        style = k % 3
        for _ in range(int(RNG.integers(3, 8))):
            if style == 0:
                parts.append(chirp(RNG.uniform(4200, 6000), RNG.uniform(2500, 3400), RNG.uniform(0.06, 0.12)))
            elif style == 1:
                parts.append(chirp(RNG.uniform(3000, 3600), RNG.uniform(3600, 4400), RNG.uniform(0.15, 0.3), vib=0.04, vibf=RNG.uniform(25, 45)))
            else:
                for _ in range(int(RNG.integers(4, 9))):
                    parts.append(chirp(5200, 4300, 0.035))
                    parts.append(np.zeros(int(SR * 0.025)))
            parts.append(np.zeros(int(SR * RNG.uniform(0.04, 0.16))))
        x = np.concatenate(parts + [np.zeros(int(SR * 0.3))])
        x = butter(x, "highpass", 1800)
        write_wav(A(f"bird{k + 1}.wav"), norm(x, 0.5))

    # footsteps
    def step(kind, seed):
        r = np.random.default_rng(seed)
        m = int(SR * 0.32)
        x = np.zeros(m)
        if kind == "grass":
            for _ in range(3):
                off = int(r.uniform(0, 0.05) * SR)
                L = int(SR * r.uniform(0.12, 0.2))
                b = butter(r.standard_normal(L), "bandpass", [900, 6000]) * env(L, 0.01, 0.12, 5)
                x[off:off + L] += b * r.uniform(0.4, 0.8)
            x += butter(r.standard_normal(m), "lowpass", 400) * env(m, 0.005, 0.06, 6) * 0.6
        elif kind == "dirt":
            for _ in range(40):
                off = int(r.uniform(0, 0.12) * SR)
                L = int(r.uniform(40, 220))
                x[off:off + L] += butter(r.standard_normal(L), "highpass", 1200) * env(L, 0.0003, 0.004, 5) * r.uniform(0.2, 1)
            x += butter(r.standard_normal(m), "lowpass", 500) * env(m, 0.004, 0.05, 6) * 0.9
        elif kind == "rock":
            x += butter(r.standard_normal(m), "bandpass", [150, 900]) * env(m, 0.002, 0.04, 7) * 1.2
            for _ in range(10):
                off = int(r.uniform(0, 0.03) * SR)
                L = int(r.uniform(30, 120))
                x[off:off + L] += butter(r.standard_normal(L), "highpass", 2500) * env(L, 0.0002, 0.002, 5) * 0.5
        elif kind == "wood":
            tt = np.arange(m) / SR
            f = r.uniform(140, 210)
            x += (np.sin(2 * np.pi * f * tt) + 0.5 * np.sin(2 * np.pi * f * 2.7 * tt)) * env(m, 0.002, 0.08, 6)
            x += butter(r.standard_normal(m), "bandpass", [300, 2500]) * env(m, 0.001, 0.03, 6) * 0.6
        elif kind == "water":
            for _ in range(6):
                off = int(r.uniform(0, 0.08) * SR)
                L = int(SR * r.uniform(0.08, 0.2))
                x[off:off + L] += butter(r.standard_normal(L), "bandpass", [400, 3000]) * env(L, 0.01, 0.1, 4) * r.uniform(0.3, 0.9)
        return norm(x, 0.85)

    for kind, count in (("grass", 4), ("dirt", 4), ("rock", 3), ("wood", 3), ("water", 3)):
        for i in range(count):
            write_wav(A(f"step_{kind}{i + 1}.wav"), step(kind, sum(map(ord, kind)) * 31 + i))

    # jump / land / ui / pickup
    m = int(SR * 0.25)
    write_wav(A("jump.wav"), norm(butter(RNG.standard_normal(m), "bandpass", [300, 2500]) * env(m, 0.03, 0.12, 4), 0.5))
    m = int(SR * 0.35)
    land = butter(RNG.standard_normal(m), "lowpass", 350) * env(m, 0.003, 0.12, 6)
    g = step("grass", 7)
    land[: len(g)] += g[:m] * 0.5
    write_wav(A("land.wav"), norm(land, 0.85))
    m = int(SR * 0.06)
    tt = np.arange(m) / SR
    write_wav(A("ui_click.wav"), norm(np.sin(2 * np.pi * 1800 * tt) * env(m, 0.001, 0.02, 6), 0.5))
    m = int(SR * 1.4)
    tt = np.arange(m) / SR
    bell = sum(np.sin(2 * np.pi * f * tt) * a * np.exp(-tt * d) for f, a, d in ((880, 1, 3), (1320, 0.6, 4), (1760, 0.35, 5), (2640, 0.2, 7)))
    write_wav(A("pickup.wav"), norm(bell * env(m, 0.003, 1.2, 1), 0.6))
    notes = [523.25, 659.25, 783.99, 1046.5]
    seq = np.zeros(int(SR * 2.2))
    for i, f in enumerate(notes):
        o = int(SR * 0.16 * i)
        mm = int(SR * 1.5)
        t2 = np.arange(mm) / SR
        tone = (np.sin(2 * np.pi * f * t2) + 0.3 * np.sin(4 * np.pi * f * t2)) * np.exp(-t2 * 2.5)
        seq[o:o + mm] += tone[: len(seq) - o]
    write_wav(A("complete.wav"), norm(seq, 0.6))


# ----------------------------------------------------------------------------- UI sprites
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

    def rounded(d, s):
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.25), fill=W)
    ss_draw(64, rounded).save(U("rounded.png"))

    def soft(size, power):
        y, x = np.mgrid[0:size, 0:size]
        r = np.sqrt((x - size / 2 + 0.5) ** 2 + (y - size / 2 + 0.5) ** 2) / (size / 2)
        a = np.clip(1 - r, 0, 1) ** power
        return np.dstack([np.ones_like(a), np.ones_like(a), np.ones_like(a), a])
    save_rgba(soft(128, 2.2), U("glow.png"))
    save_rgba(soft(64, 1.0), U("dot.png"))

    # gradient strip for menu panels (left dark -> transparent)
    g = np.linspace(1, 0, 256) ** 1.4
    strip = np.dstack([np.zeros((4, 256)), np.zeros((4, 256)), np.zeros((4, 256)), np.tile(g, (4, 1))])
    save_rgba(strip, U("fade_h.png"))
    gv = np.linspace(0, 1, 256) ** 1.6
    stripv = np.dstack([np.zeros((256, 4)), np.zeros((256, 4)), np.zeros((256, 4)), np.tile(gv[:, None], (1, 4))])
    save_rgba(stripv, U("fade_v.png"))

    def icon(name, fn):
        ss_draw(128, fn).save(U(f"icon_{name}.png"))

    def jump(d, s):
        w = s * 0.11
        d.line([(s * 0.25, s * 0.58), (s * 0.5, s * 0.33), (s * 0.75, s * 0.58)], fill=W, width=int(w), joint="curve")
        d.line([(s * 0.3, s * 0.78), (s * 0.7, s * 0.78)], fill=W, width=int(w * 0.8))

    def crouch(d, s):
        w = s * 0.11
        d.line([(s * 0.25, s * 0.38), (s * 0.5, s * 0.63), (s * 0.75, s * 0.38)], fill=W, width=int(w), joint="curve")
        d.line([(s * 0.3, s * 0.8), (s * 0.7, s * 0.8)], fill=W, width=int(w * 0.8))

    def run(d, s):
        w = s * 0.1
        for off in (0.0, 0.2):
            d.line([(s * (0.28 + off), s * 0.28), (s * (0.48 + off), s * 0.5), (s * (0.28 + off), s * 0.72)], fill=W, width=int(w), joint="curve")

    def pause(d, s):
        d.rounded_rectangle([s * 0.3, s * 0.25, s * 0.43, s * 0.75], radius=s * 0.03, fill=W)
        d.rounded_rectangle([s * 0.57, s * 0.25, s * 0.7, s * 0.75], radius=s * 0.03, fill=W)

    def hand(d, s):
        # open palm
        d.rounded_rectangle([s * 0.3, s * 0.45, s * 0.72, s * 0.85], radius=s * 0.12, fill=W)
        for i, x in enumerate((0.32, 0.43, 0.54, 0.65)):
            top = 0.22 if i in (1, 2) else 0.28
            d.rounded_rectangle([s * x, s * top, s * (x + 0.08), s * 0.6], radius=s * 0.04, fill=W)
        d.rounded_rectangle([s * 0.16, s * 0.5, s * 0.36, s * 0.6], radius=s * 0.05, fill=W)

    def lantern(d, s):
        d.arc([s * 0.36, s * 0.08, s * 0.64, s * 0.36], 180, 360, fill=W, width=int(s * 0.05))
        d.rectangle([s * 0.3, s * 0.22, s * 0.7, s * 0.3], fill=W)
        d.rounded_rectangle([s * 0.33, s * 0.32, s * 0.67, s * 0.8], radius=s * 0.06, outline=W, width=int(s * 0.06))
        d.ellipse([s * 0.43, s * 0.45, s * 0.57, s * 0.68], fill=W)
        d.rectangle([s * 0.28, s * 0.8, s * 0.72, s * 0.88], fill=W)

    def gear(d, s):
        c = s / 2
        for k in range(8):
            a = k * math.pi / 4
            d.line([(c + math.cos(a) * s * 0.18, c + math.sin(a) * s * 0.18), (c + math.cos(a) * s * 0.4, c + math.sin(a) * s * 0.4)], fill=W, width=int(s * 0.12))
        d.ellipse([c - s * 0.3, c - s * 0.3, c + s * 0.3, c + s * 0.3], fill=W)
        d.ellipse([c - s * 0.12, c - s * 0.12, c + s * 0.12, c + s * 0.12], fill=(0, 0, 0, 0))

    for name, fn in (("jump", jump), ("crouch", crouch), ("run", run), ("pause", pause), ("hand", hand), ("lantern", lantern), ("gear", gear)):
        icon(name, fn)

    # flame + smoke particle textures
    y, x = np.mgrid[0:128, 0:128] / 127.0
    r = np.sqrt((x - 0.5) ** 2 * 4 + (y - 0.62) ** 2 * 1.2)
    tongue = np.clip(1 - r * 1.6, 0, 1) ** 1.5 * np.clip((y - 0.05) * 1.3, 0, 1)
    flame = np.dstack([np.ones_like(tongue), 0.55 + 0.45 * tongue, 0.2 + 0.3 * tongue ** 2, tongue])
    save_rgba(flame, U("flame.png"))
    n = ndimage.gaussian_filter(RNG.random((128, 128)), 6)
    n = (n - n.min()) / (n.max() - n.min())
    rr = np.sqrt((x - 0.5) ** 2 + (y - 0.5) ** 2) * 2
    puff = np.clip(1 - rr, 0, 1) ** 1.6 * (0.6 + 0.4 * n)
    save_rgba(np.dstack([np.full_like(puff, 0.8), np.full_like(puff, 0.8), np.full_like(puff, 0.82), puff]), U("smoke.png"))


def app_icon(sky_srgb):
    S = 1024
    # crop a cloudy part of the sky above the horizon, opposite the sun's glare
    H, W, _ = sky_srgb.shape
    crop = sky_srgb[int(H * 0.18):int(H * 0.5), int(W * 0.05):int(W * 0.05) + int(H * 0.32)]
    im = Image.fromarray((crop * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS)
    d = ImageDraw.Draw(im, "RGBA")
    rng = np.random.default_rng(3)
    # far mountains
    xs = np.linspace(0, S, 60)
    far = S * 0.58 - (np.abs(np.sin(xs / S * 5.1 + 0.6)) * 120 + rng.random(60) * 25)
    d.polygon([(0, S)] + list(zip(xs, far)) + [(S, S)], fill=(70, 88, 104, 255))
    near = S * 0.68 - (np.abs(np.sin(xs / S * 3.3 + 2.0)) * 90 + rng.random(60) * 18)
    d.polygon([(0, S)] + list(zip(xs, near)) + [(S, S)], fill=(38, 52, 52, 255))
    # lake
    d.rectangle([0, S * 0.74, S, S], fill=(46, 74, 88, 255))
    d.rectangle([0, S * 0.74, S, S * 0.75], fill=(150, 175, 190, 120))
    # conifers
    def tree(cx, base, h, col):
        w = h * 0.34
        for k in range(6):
            t0 = k / 6
            y0 = base - h * (0.15 + 0.85 * t0)
            ww = w * (1 - t0 * 0.8)
            d.polygon([(cx, y0 - h * 0.22), (cx - ww, y0 + h * 0.05), (cx + ww, y0 + h * 0.05)], fill=col)
        d.rectangle([cx - h * 0.02, base - h * 0.16, cx + h * 0.02, base], fill=(40, 30, 22, 255))
    for cx, h in ((90, 330), (210, 420), (880, 380), (980, 300), (760, 250)):
        tree(cx, S * 0.76, h, (24, 40, 30, 255))
    im = im.convert("RGB")
    im.save(out("Icons", "app_icon.png"))


def fonts():
    fdir = src("fonts")
    if not os.path.isdir(fdir):
        log("no fonts downloaded; the game will use Arial")
        return
    for f in os.listdir(fdir):
        if f.endswith(".ttf") and os.path.getsize(os.path.join(fdir, f)) > 10000:
            shutil.copyfile(os.path.join(fdir, f), out("Fonts", f))
    log("fonts", os.listdir(os.path.join(ART, "Fonts")) if os.path.isdir(os.path.join(ART, "Fonts")) else [])


def main():
    os.makedirs(ART, exist_ok=True)
    sky_srgb = sky()
    terrain()
    twigs()
    grass()
    models()
    water_normal()
    audio()
    ui()
    app_icon(sky_srgb)
    fonts()
    with open(out("art.json"), "w") as f:
        json.dump(INFO, f, indent=1)
    log("done")


if __name__ == "__main__":
    main()
