#!/usr/bin/env python3
"""Generates every texture, UI icon, sound effect and the app icon used by Zombie Strike.
Run from the project root:  python3 tools/gen_assets.py
Outputs go to Assets/Resources/{Textures,UI,Audio} and Assets/Icons/AppIcon.png."""
import math
import os
import wave

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from scipy import signal
from scipy.ndimage import gaussian_filter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "Assets", "Resources", "Textures")
UI = os.path.join(ROOT, "Assets", "Resources", "UI")
AUD = os.path.join(ROOT, "Assets", "Resources", "Audio")
ICON = os.path.join(ROOT, "Assets", "Icons")
for d in (TEX, UI, AUD, ICON):
    os.makedirs(d, exist_ok=True)

rng = np.random.default_rng(1337)


# ----------------------------------------------------------------------------- helpers
def tile_noise(size, sigma, seed):
    """Tileable smooth noise in [0,1] (gaussian blur with wrap-around)."""
    r = np.random.default_rng(seed)
    n = r.random((size, size))
    n = gaussian_filter(n, sigma, mode="wrap")
    n -= n.min()
    n /= max(n.max(), 1e-6)
    return n


def fbm(size, seed, octaves=((24, 0.5), (8, 0.3), (2, 0.2))):
    out = np.zeros((size, size))
    for i, (s, w) in enumerate(octaves):
        out += tile_noise(size, s, seed + i * 31) * w
    out -= out.min()
    return out / max(out.max(), 1e-6)


def save_rgb(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB").save(path)


def save_rgba(arr, path):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGBA").save(path)


def colorize(gray, dark, light):
    dark = np.array(dark, float)
    light = np.array(light, float)
    return dark + (light - dark) * gray[..., None]


# ----------------------------------------------------------------------------- surface textures
def asphalt():
    s = 256
    base = fbm(s, 10)
    grain = rng.random((s, s))
    g = 0.55 * base + 0.45 * grain
    img = colorize(g, (34, 36, 38), (78, 80, 82))
    # pale stones
    for _ in range(500):
        x, y = rng.integers(0, s, 2)
        img[y, x] = img[y, x] * 0.4 + np.array([130, 130, 128]) * 0.6
    # wrapped cracks
    crack = np.zeros((s, s))
    for _ in range(6):
        x, y = rng.random(2) * s
        ang = rng.random() * math.tau
        for _ in range(140):
            ang += rng.normal(0, 0.35)
            x = (x + math.cos(ang)) % s
            y = (y + math.sin(ang)) % s
            crack[int(y), int(x)] = 1
    crack = gaussian_filter(crack, 0.9, mode="wrap")
    img *= (1 - np.clip(crack * 1.4, 0, 0.35))[..., None]
    save_rgb(img, os.path.join(TEX, "asphalt.png"))


def concrete():
    s = 256
    g = 0.65 * fbm(s, 20) + 0.35 * rng.random((s, s))
    img = colorize(g, (88, 88, 86), (150, 149, 144))
    stains = tile_noise(s, 18, 77)
    img *= (0.75 + 0.25 * stains)[..., None]
    # panel seams
    for k in range(0, s, 128):
        img[:, k:k + 2] *= 0.6
        img[k:k + 2, :] *= 0.6
    save_rgb(img, os.path.join(TEX, "concrete.png"))


def brick():
    s = 256
    rows, cols = 8, 4
    bh, bw = s // rows, s // cols
    img = np.zeros((s, s, 3))
    noise = rng.random((s, s))
    grime = fbm(s, 40)
    for r in range(rows):
        off = (bw // 2) if r % 2 else 0
        for c in range(cols + 1):
            col = np.array([118, 52, 38]) * (0.75 + rng.random() * 0.4)
            col = col * (0.9 + rng.random() * 0.15)
            y0 = r * bh
            x0 = c * bw - off
            for y in range(y0, y0 + bh):
                for x in range(x0, x0 + bw):
                    img[y % s, x % s] = col
    mortar = np.zeros((s, s), bool)
    for r in range(rows):
        y = r * bh
        mortar[y:y + 3, :] = True
        off = (bw // 2) if r % 2 else 0
        for c in range(cols + 1):
            x = (c * bw - off) % s
            mortar[y:y + bh, x:x + 3] = True
    img[mortar] = np.array([70, 66, 60])
    img *= (0.8 + 0.25 * noise)[..., None]
    img *= (0.65 + 0.35 * grime)[..., None]
    save_rgb(img, os.path.join(TEX, "brick.png"))


def crate():
    s = 256
    img = np.zeros((s, s, 3))
    planks = 5
    ph = s // planks
    for p in range(planks):
        tone = 0.8 + rng.random() * 0.35
        y0 = p * ph
        grain = gaussian_filter(rng.random((ph, s)), (0.8, 18))
        grain = (grain - grain.min()) / (grain.max() - grain.min())
        col = colorize(grain, (96, 66, 34), (150, 108, 60)) * tone
        img[y0:y0 + ph] = col
        img[y0:y0 + 2] *= 0.45
    # frame and diagonal brace
    f = 22
    frame = colorize(gaussian_filter(rng.random((s, s)), (12, 0.8)), (80, 54, 28), (128, 92, 50))
    m = np.zeros((s, s), bool)
    m[:f], m[-f:], m[:, :f], m[:, -f:] = True, True, True, True
    yy, xx = np.mgrid[0:s, 0:s]
    m |= np.abs(yy - xx) < f * 0.7
    img[m] = frame[m]
    edge = np.zeros((s, s), bool)
    edge[f - 2:f, :], edge[s - f:s - f + 2, :], edge[:, f - 2:f], edge[:, s - f:s - f + 2] = True, True, True, True
    img[edge] *= 0.5
    # nails
    for (cx, cy) in [(11, 11), (s - 12, 11), (11, s - 12), (s - 12, s - 12)]:
        img[cy - 3:cy + 3, cx - 3:cx + 3] = (60, 60, 64)
    save_rgb(img, os.path.join(TEX, "crate.png"))


def metal():
    s = 128
    g = 0.6 * fbm(s, 55, ((10, 0.6), (3, 0.4))) + 0.4 * rng.random((s, s))
    img = colorize(g, (150, 150, 150), (215, 215, 215))
    rust = tile_noise(s, 6, 91)
    rmask = np.clip((rust - 0.62) * 5, 0, 1)
    img = img * (1 - rmask[..., None]) + np.array([120, 62, 30]) * rmask[..., None]
    for _ in range(40):  # scratches
        x, y = rng.integers(0, s, 2)
        L = rng.integers(6, 20)
        for i in range(L):
            img[(y + i // 3) % s, (x + i) % s] = (230, 230, 230)
    save_rgb(img, os.path.join(TEX, "metal.png"))


def grime():
    s = 128
    g = 0.55 * fbm(s, 66, ((10, 0.5), (4, 0.3), (1, 0.2))) + 0.45 * rng.random((s, s))
    v = 170 + 85 * g
    spots = tile_noise(s, 4, 9)
    v *= 1 - np.clip((spots - 0.7) * 2.5, 0, 0.5)
    save_rgb(np.repeat(v[..., None], 3, axis=2), os.path.join(TEX, "grime.png"))


def soft_particle():
    s = 64
    yy, xx = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    a = np.clip(1 - r, 0, 1) ** 1.6
    img = np.zeros((s, s, 4))
    img[..., :3] = 255
    img[..., 3] = a * 255
    save_rgba(img, os.path.join(TEX, "particle.png"))


def flare():
    s = 128
    yy, xx = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    ang = np.arctan2(yy, xx)
    core = np.clip(1 - r / 0.35, 0, 1) ** 1.5
    spikes = np.clip(1 - r, 0, 1) ** 2 * (0.5 + 0.5 * np.cos(ang * 6)) ** 6
    glow = np.clip(1 - r, 0, 1) ** 3 * 0.6
    a = np.clip(core + spikes + glow, 0, 1)
    img = np.zeros((s, s, 4))
    img[..., 0] = 255
    img[..., 1] = 255 * (0.75 + 0.25 * core)
    img[..., 2] = 255 * (0.35 + 0.65 * core)
    img[..., 3] = a * 255
    save_rgba(img, os.path.join(TEX, "flare.png"))


def blood_splat():
    s = 128
    yy, xx = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2)
    n = gaussian_filter(rng.random((s, s)), 4)
    n = (n - n.min()) / (n.max() - n.min())
    blob = (r + (n - 0.5) * 0.7) < 0.55
    drops = np.zeros((s, s), bool)
    for _ in range(14):
        cx, cy = rng.normal(0, 0.45, 2)
        rr = rng.random() * 0.08 + 0.02
        drops |= (xx - cx) ** 2 + (yy - cy) ** 2 < rr ** 2
    m = gaussian_filter((blob | drops).astype(float), 1.0)
    img = np.zeros((s, s, 4))
    img[..., 0] = 95 + 40 * n
    img[..., 1] = 6
    img[..., 2] = 8
    img[..., 3] = np.clip(m * 1.4, 0, 1) * 230
    save_rgba(img, os.path.join(TEX, "blood.png"))


def vignette():
    s = 256
    yy, xx = np.mgrid[0:s, 0:s] / (s - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + yy ** 2) / math.sqrt(2)
    a = np.clip((r - 0.35) / 0.65, 0, 1) ** 1.7
    img = np.zeros((s, s, 4))
    img[..., :3] = 255
    img[..., 3] = a * 255
    save_rgba(img, os.path.join(TEX, "vignette.png"))


def tracer():
    w, h = 64, 16
    yy = np.linspace(-1, 1, h)[:, None] * np.ones((1, w))
    a = np.clip(1 - np.abs(yy), 0, 1) ** 2.2
    img = np.zeros((h, w, 4))
    img[..., :3] = 255
    img[..., 3] = a * 255
    save_rgba(img, os.path.join(TEX, "tracer.png"))


# ----------------------------------------------------------------------------- UI sprites (white, drawn 4x then downsampled)
def ui_canvas(size=256, ss=4):
    im = Image.new("RGBA", (size * ss, size * ss), (255, 255, 255, 0))
    return im, ImageDraw.Draw(im), ss


def ui_save(im, name, size=256):
    im = im.resize((size, size), Image.LANCZOS)
    arr = np.array(im).astype(float)
    arr[..., :3] = 255  # keep colour channels white so there is no dark fringe
    save_rgba(arr, os.path.join(UI, name))


def ui_circle():
    im, d, ss = ui_canvas()
    d.ellipse([4 * ss, 4 * ss, 252 * ss, 252 * ss], fill=(255, 255, 255, 255))
    ui_save(im, "circle.png")


def ui_ring():
    im, d, ss = ui_canvas()
    d.ellipse([6 * ss, 6 * ss, 250 * ss, 250 * ss], outline=(255, 255, 255, 255), width=10 * ss)
    ui_save(im, "ring.png")


def ui_rounded():
    im, d, ss = ui_canvas(128)
    d.rounded_rectangle([2 * ss, 2 * ss, 126 * ss, 126 * ss], radius=28 * ss, fill=(255, 255, 255, 255))
    ui_save(im, "rounded.png", 128)


def ui_crosshair_icon():
    im, d, ss = ui_canvas()
    c = 128 * ss
    w = 14 * ss
    d.ellipse([c - 70 * ss, c - 70 * ss, c + 70 * ss, c + 70 * ss], outline=(255, 255, 255, 255), width=w)
    for (x0, y0, x1, y1) in [(c, c - 110 * ss, c, c - 40 * ss), (c, c + 40 * ss, c, c + 110 * ss),
                             (c - 110 * ss, c, c - 40 * ss, c), (c + 40 * ss, c, c + 110 * ss, c)]:
        d.line([x0, y0, x1, y1], fill=(255, 255, 255, 255), width=w)
    d.ellipse([c - 14 * ss, c - 14 * ss, c + 14 * ss, c + 14 * ss], fill=(255, 255, 255, 255))
    ui_save(im, "icon_fire.png")


def ui_reload_icon():
    im, d, ss = ui_canvas()
    c = 128 * ss
    R = 78 * ss
    d.arc([c - R, c - R, c + R, c + R], start=-60, end=230, fill=(255, 255, 255, 255), width=22 * ss)
    a = math.radians(-60)
    tip = (c + R * math.cos(a), c + R * math.sin(a))
    # arrow head pointing along the arc direction (clockwise end)
    d.polygon([(tip[0] - 40 * ss, tip[1] - 30 * ss), (tip[0] + 38 * ss, tip[1] - 14 * ss), (tip[0] + 6 * ss, tip[1] + 52 * ss)],
              fill=(255, 255, 255, 255))
    ui_save(im, "icon_reload.png")


def ui_pause_icon():
    im, d, ss = ui_canvas()
    d.rounded_rectangle([70 * ss, 50 * ss, 112 * ss, 206 * ss], radius=10 * ss, fill=(255, 255, 255, 255))
    d.rounded_rectangle([144 * ss, 50 * ss, 186 * ss, 206 * ss], radius=10 * ss, fill=(255, 255, 255, 255))
    ui_save(im, "icon_pause.png")


def ui_heart_icon():
    im, d, ss = ui_canvas()
    pts = []
    for t in np.linspace(0, math.tau, 200):
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((128 * ss + x * 7 * ss, 120 * ss - y * 7 * ss))
    d.polygon(pts, fill=(255, 255, 255, 255))
    ui_save(im, "icon_heart.png")


def ui_ammo_icon():
    im, d, ss = ui_canvas()
    for i, x in enumerate((62, 112, 162)):
        x0 = (x - 18) * ss
        x1 = (x + 18) * ss
        d.rectangle([x0, 100 * ss, x1, 220 * ss], fill=(255, 255, 255, 255))
        d.pieslice([x0, 40 * ss, x1, 160 * ss], 180, 360, fill=(255, 255, 255, 255))
        d.rectangle([x0, 112 * ss, x1, 124 * ss], fill=(255, 255, 255, 0))
    ui_save(im, "icon_ammo.png")


def ui_skull_icon():
    im, d, ss = ui_canvas()
    d.ellipse([48 * ss, 30 * ss, 208 * ss, 180 * ss], fill=(255, 255, 255, 255))
    d.rounded_rectangle([84 * ss, 150 * ss, 172 * ss, 220 * ss], radius=14 * ss, fill=(255, 255, 255, 255))
    d.ellipse([78 * ss, 92 * ss, 120 * ss, 136 * ss], fill=(255, 255, 255, 0))
    d.ellipse([136 * ss, 92 * ss, 178 * ss, 136 * ss], fill=(255, 255, 255, 0))
    d.polygon([(128 * ss, 140 * ss), (116 * ss, 164 * ss), (140 * ss, 164 * ss)], fill=(255, 255, 255, 0))
    for x in (104, 128, 152):
        d.rectangle([(x - 3) * ss, 186 * ss, (x + 3) * ss, 220 * ss], fill=(255, 255, 255, 0))
    ui_save(im, "icon_skull.png")


def ui_damage_arrow():
    im, d, ss = ui_canvas()
    c = 128 * ss
    R = 120 * ss
    d.arc([c - R, c - R, c + R, c + R], start=245, end=295, fill=(255, 255, 255, 255), width=26 * ss)
    ui_save(im, "damage_arc.png")


def ui_run_icon():
    im, d, ss = ui_canvas()
    # simple running chevrons
    for k, x in enumerate((70, 120, 170)):
        d.line([((x - 30) * ss, 70 * ss), (x * ss, 128 * ss), ((x - 30) * ss, 186 * ss)], fill=(255, 255, 255, 255),
               width=22 * ss, joint="curve")
    ui_save(im, "icon_run.png")


# ----------------------------------------------------------------------------- app icon
def app_icon():
    S = 1024
    im = Image.new("RGBA", (S, S), (0, 0, 0, 255))
    yy, xx = np.mgrid[0:S, 0:S] / (S - 1) * 2 - 1
    r = np.sqrt(xx ** 2 + (yy + 0.1) ** 2)
    bg = np.zeros((S, S, 4))
    bg[..., 0] = 120 * np.clip(1 - r * 0.85, 0, 1) ** 1.4 + 8
    bg[..., 1] = 10 * np.clip(1 - r, 0, 1) + 4
    bg[..., 2] = 12 * np.clip(1 - r, 0, 1) + 6
    bg[..., 3] = 255
    im = Image.fromarray(bg.astype(np.uint8), "RGBA")
    d = ImageDraw.Draw(im)
    # blocky zombie head
    hx0, hy0, hx1, hy1 = 262, 250, 762, 760
    d.rectangle([hx0, hy0, hx1, hy1], fill=(96, 138, 74, 255))
    n = gaussian_filter(np.random.default_rng(5).random((hy1 - hy0, hx1 - hx0)), 18)
    n = (n - n.min()) / (n.max() - n.min())
    head = np.array(im)[hy0:hy1, hx0:hx1].astype(float)
    head[..., :3] *= (0.72 + 0.4 * n)[..., None]
    arr = np.array(im)
    arr[hy0:hy1, hx0:hx1] = np.clip(head, 0, 255).astype(np.uint8)
    im = Image.fromarray(arr, "RGBA")
    d = ImageDraw.Draw(im)
    d.rectangle([hx0, hy0, hx1, hy0 + 70], fill=(52, 70, 40, 255))  # hair / shadow band
    d.rectangle([hx0, hy0 + 70, hx1, hy0 + 90], fill=(70, 98, 54, 255))
    # glowing eyes
    glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    for ex in (340, 560):
        gd.rectangle([ex - 30, 380, ex + 150, 520], fill=(255, 30, 20, 200))
    glow = glow.filter(ImageFilter.GaussianBlur(40))
    im = Image.alpha_composite(im, glow)
    d = ImageDraw.Draw(im)
    for ex in (340, 560):
        d.rectangle([ex, 410, ex + 120, 490], fill=(20, 0, 0, 255))
        d.rectangle([ex + 30, 425, ex + 95, 478], fill=(255, 40, 30, 255))
        d.rectangle([ex + 52, 438, ex + 74, 462], fill=(255, 220, 180, 255))
    # mouth with teeth
    d.rectangle([370, 600, 660, 690], fill=(30, 10, 10, 255))
    for tx in range(380, 650, 46):
        d.rectangle([tx, 600, tx + 26, 632], fill=(220, 214, 180, 255))
    d.rectangle([420, 660, 446, 690], fill=(220, 214, 180, 255))
    d.rectangle([560, 662, 586, 690], fill=(220, 214, 180, 255))
    # scar
    d.line([(300, 300), (420, 360)], fill=(60, 20, 20, 255), width=10)
    for k in range(5):
        x = 310 + k * 24
        y = 305 + k * 12
        d.line([(x - 6, y + 14), (x + 6, y - 14)], fill=(40, 10, 10, 255), width=6)
    # blood drips from the mouth
    for (bx, bl) in [(470, 90), (610, 60), (400, 50)]:
        d.rectangle([bx, 690, bx + 22, 690 + bl], fill=(150, 0, 0, 255))
    # crosshair
    cx, cy = 512, 470
    d.ellipse([cx - 300, cy - 300, cx + 300, cy + 300], outline=(255, 255, 255, 235), width=22)
    for (x0, y0, x1, y1) in [(cx, cy - 380, cx, cy - 210), (cx, cy + 210, cx, cy + 380),
                             (cx - 380, cy, cx - 210, cy), (cx + 210, cy, cx + 380, cy)]:
        d.line([x0, y0, x1, y1], fill=(255, 255, 255, 235), width=22)
    im = im.resize((512, 512), Image.LANCZOS).convert("RGB")
    im.save(os.path.join(ICON, "AppIcon.png"))


# ----------------------------------------------------------------------------- audio
SR = 22050


def write_wav(name, x, gain_db=-1.0):
    x = np.asarray(x, float)
    peak = np.max(np.abs(x)) or 1.0
    x = x / peak * (10 ** (gain_db / 20))
    data = (np.clip(x, -1, 1) * 32767).astype(np.int16)
    with wave.open(os.path.join(AUD, name + ".wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def t_axis(dur):
    return np.arange(int(SR * dur)) / SR


def noise(dur, seed=None):
    r = np.random.default_rng(seed) if seed is not None else rng
    return r.uniform(-1, 1, int(SR * dur))


def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), "low")
    return signal.lfilter(b, a, x)


def hp(x, fc, order=2):
    b, a = signal.butter(order, min(fc / (SR / 2), 0.99), "high")
    return signal.lfilter(b, a, x)


def bp(x, lo, hi, order=2):
    b, a = signal.butter(order, [lo / (SR / 2), min(hi / (SR / 2), 0.99)], "band")
    return signal.lfilter(b, a, x)


def env_exp(dur, tau, attack=0.002):
    t = t_axis(dur)
    e = np.exp(-t / tau)
    a = np.clip(t / max(attack, 1e-4), 0, 1)
    return e * a


def adsr(dur, a, d, s, r):
    n = int(SR * dur)
    e = np.ones(n) * s
    na, nd, nr = int(SR * a), int(SR * d), int(SR * r)
    e[:na] = np.linspace(0, 1, na, endpoint=False)
    e[na:na + nd] = np.linspace(1, s, nd, endpoint=False)
    e[-nr:] = np.linspace(s, 0, nr) if nr > 0 else e[-nr:]
    return e


def place(total, part, at):
    i = int(at * SR)
    end = min(len(total), i + len(part))
    total[i:end] += part[:end - i]
    return total


def gunshot(seed):
    dur = 0.45
    t = t_axis(dur)
    crack = hp(noise(dur, seed), 2500) * env_exp(dur, 0.006, 0.0005)
    body = lp(noise(dur, seed + 1), 3200) * env_exp(dur, 0.045, 0.001)
    f = 85 * np.exp(-t * 9) + 42
    thump = np.sin(np.cumsum(2 * np.pi * f / SR)) * env_exp(dur, 0.07, 0.001)
    tail = lp(noise(dur, seed + 2), 900) * env_exp(dur, 0.16, 0.01) * 0.35
    x = crack * 0.9 + body * 1.0 + thump * 1.2 + tail
    return np.tanh(x * 1.8)


def metal_click(dur=0.09, freq=2400, seed=3):
    t = t_axis(dur)
    ping = np.sin(2 * np.pi * freq * t) * env_exp(dur, 0.012) + 0.5 * np.sin(2 * np.pi * freq * 1.63 * t) * env_exp(dur, 0.008)
    tick = hp(noise(dur, seed), 3000) * env_exp(dur, 0.004, 0.0003)
    return ping * 0.6 + tick


def reload_sound():
    total = np.zeros(int(SR * 1.5))
    place(total, metal_click(0.1, 2100, 4) * 0.7, 0.10)
    slide = bp(noise(0.25, 5), 600, 2500) * adsr(0.25, 0.03, 0.1, 0.5, 0.1) * 0.25
    place(total, slide, 0.22)
    place(total, metal_click(0.12, 1700, 6) * 1.0, 0.78)
    place(total, lp(noise(0.08, 7), 800) * env_exp(0.08, 0.02) * 0.8, 0.79)
    place(total, metal_click(0.08, 2600, 8) * 0.8, 1.15)
    place(total, metal_click(0.08, 2300, 9) * 0.9, 1.24)
    return total


def growl(dur, f0, f1, seed, breath=0.35, wobble=6.0, formants=((520, 120), (980, 160), (2400, 300))):
    r = np.random.default_rng(seed)
    t = t_axis(dur)
    jitter = gaussian_filter(r.normal(0, 1, len(t)), 300)
    jitter /= max(np.max(np.abs(jitter)), 1e-6)
    f = f0 + (f1 - f0) * (t / dur) + jitter * f0 * 0.12 + np.sin(2 * np.pi * wobble * t) * f0 * 0.06
    phase = np.cumsum(2 * np.pi * f / SR)
    saw = 2 * ((phase / (2 * np.pi)) % 1) - 1
    src = saw + breath * r.uniform(-1, 1, len(t))
    out = np.zeros_like(src)
    for fc, bw in formants:
        out += bp(src, max(fc - bw, 40), fc + bw)
    out += 0.3 * lp(src, 300)
    am = 0.7 + 0.3 * np.sin(2 * np.pi * (11 + r.random() * 6) * t)
    return np.tanh(out * am * 2.5)


def zombie_groans():
    specs = [(1.5, 95, 70, 21), (1.3, 115, 82, 22), (1.7, 80, 62, 23), (1.1, 130, 90, 24)]
    for i, (dur, f0, f1, seed) in enumerate(specs):
        x = growl(dur, f0, f1, seed) * adsr(dur, 0.18, 0.2, 0.8, 0.45)
        write_wav(f"zombie_groan{i + 1}", x, -4)
    x = growl(0.6, 170, 105, 31, breath=0.6, wobble=14) * adsr(0.6, 0.02, 0.15, 0.8, 0.2)
    write_wav("zombie_attack", x, -2)
    dur = 1.1
    t = t_axis(dur)
    x = growl(dur, 120, 48, 41, breath=0.5, wobble=18) * adsr(dur, 0.03, 0.2, 0.7, 0.6)
    x *= 0.65 + 0.35 * np.sign(np.sin(2 * np.pi * 16 * t))  # gurgle
    write_wav("zombie_death", lp(x, 2500), -3)
    x = growl(1.6, 70, 50, 51, breath=0.25, wobble=4, formants=((350, 120), (700, 150), (1800, 300))) * adsr(1.6, 0.1, 0.3, 0.9, 0.5)
    write_wav("brute_roar", lp(x, 1800), -1)


def flesh_hit():
    dur = 0.2
    t = t_axis(dur)
    splat = lp(noise(dur, 61), 1400) * env_exp(dur, 0.035, 0.001)
    thud = np.sin(2 * np.pi * (110 * np.exp(-t * 12) + 55) * t) * env_exp(dur, 0.05)
    return np.tanh((splat * 1.2 + thud) * 1.5)


def wall_hit():
    dur = 0.12
    return bp(noise(dur, 71), 1500, 6000) * env_exp(dur, 0.012, 0.0005) + metal_click(dur, 3400, 72) * 0.3


def ding():
    dur = 0.3
    t = t_axis(dur)
    return (np.sin(2 * np.pi * 1760 * t) * 0.7 + np.sin(2 * np.pi * 2637 * t) * 0.4) * env_exp(dur, 0.07, 0.002)


def hurt():
    x = growl(0.38, 150, 112, 81, breath=0.4, wobble=3, formants=((650, 120), (1150, 150), (2500, 250)))
    return x * adsr(0.38, 0.015, 0.1, 0.7, 0.18)


def pickup():
    dur = 0.45
    t = t_axis(dur)
    x = np.zeros_like(t)
    for i, (f, at) in enumerate([(784, 0.0), (1175, 0.08), (1568, 0.16)]):
        seg = t_axis(dur - at)
        tone = (np.sin(2 * np.pi * f * seg) + 0.3 * np.sin(2 * np.pi * f * 2 * seg)) * env_exp(dur - at, 0.12, 0.003)
        place(x, tone * 0.6, at)
    return x


def horn(dur, f, seed, swell=0.5):
    t = t_axis(dur)
    x = np.zeros_like(t)
    for k, fm in enumerate((f, f * 1.5, f * 2.0, f * 1.01)):
        ph = np.cumsum(2 * np.pi * (fm + np.sin(2 * np.pi * 0.7 * t) * 0.8) / SR)
        x += (2 * ((ph / (2 * np.pi)) % 1) - 1) * (0.6 if k == 0 else 0.35)
    x = lp(x, 900)
    return x * adsr(dur, swell, 0.2, 0.85, 0.6)


def wave_start():
    x = horn(2.2, 73.4, 91)
    x = x + 0.15 * lp(noise(2.2, 92), 300) * adsr(2.2, 0.4, 0.2, 0.8, 0.6)
    return x


def wave_clear():
    dur = 1.2
    t = t_axis(dur)
    x = np.zeros_like(t)
    for f, at in [(523, 0.0), (659, 0.12), (784, 0.24), (1047, 0.36)]:
        seg = t_axis(dur - at)
        place(x, np.sin(2 * np.pi * f * seg) * env_exp(dur - at, 0.35, 0.005) * 0.5, at)
    return x


def game_over():
    dur = 3.0
    t = t_axis(dur)
    f = 110 * np.exp(-t * 0.35)
    ph = np.cumsum(2 * np.pi * f / SR)
    x = (2 * ((ph / (2 * np.pi)) % 1) - 1) + 0.5 * np.sin(ph * 0.5)
    x = lp(x, 600) * adsr(dur, 0.05, 0.4, 0.8, 1.6)
    return x + 0.2 * lp(noise(dur, 101), 200) * adsr(dur, 0.2, 0.5, 0.6, 1.5)


def footstep(seed):
    dur = 0.16
    t = t_axis(dur)
    x = lp(noise(dur, seed), 500) * env_exp(dur, 0.03, 0.002)
    x += 0.4 * np.sin(2 * np.pi * 70 * t) * env_exp(dur, 0.04)
    return x


def ui_click():
    dur = 0.06
    return metal_click(dur, 3200, 111) * 0.8


def ambience():
    dur = 8.0
    t = t_axis(dur)
    n = noise(dur + 1, 121)
    wind = np.zeros(int(SR * dur))
    # sweep a band-pass slowly
    blocks = 64
    L = len(wind) // blocks
    for b in range(blocks):
        c = max(140.0, 360 + 160 * math.sin(b / blocks * math.tau * 2) + 80 * math.sin(b / blocks * math.tau * 5))
        seg = bp(n[b * L:(b + 1) * L + 2048], c * 0.6, c * 1.6)[:L]
        wind[b * L:(b + 1) * L] = seg * (0.6 + 0.4 * math.sin(b / blocks * math.tau * 3) ** 2)
    rumble = lp(noise(dur, 122), 90) * 0.8
    x = wind + rumble
    # seamless loop: cross-fade the last second into the first
    fade = int(SR * 1.0)
    head = x[:fade].copy()
    w = np.linspace(0, 1, fade)
    x[-fade:] = x[-fade:] * (1 - w) + head * w
    x = x[fade:]
    return x


def heartbeat():
    dur = 0.9
    total = np.zeros(int(SR * dur))
    for at, g in ((0.0, 1.0), (0.22, 0.75)):
        seg = t_axis(0.18)
        beat = np.sin(2 * np.pi * (60 * np.exp(-seg * 8) + 40) * seg) * env_exp(0.18, 0.05, 0.005)
        place(total, beat * g, at)
    return lp(total, 300)


def audio():
    write_wav("gunshot1", gunshot(11), -1)
    write_wav("gunshot2", gunshot(17), -1)
    write_wav("reload", reload_sound(), -3)
    write_wav("dry_fire", metal_click(0.1, 2800, 12), -6)
    zombie_groans()
    write_wav("hit_flesh", flesh_hit(), -2)
    write_wav("hit_wall", wall_hit(), -6)
    write_wav("headshot", ding(), -5)
    write_wav("player_hurt", hurt(), -2)
    write_wav("pickup", pickup(), -4)
    write_wav("wave_start", wave_start(), -2)
    write_wav("wave_clear", wave_clear(), -4)
    write_wav("game_over", game_over(), -2)
    write_wav("footstep1", footstep(131), -8)
    write_wav("footstep2", footstep(132), -8)
    write_wav("ui_click", ui_click(), -6)
    write_wav("ambience", ambience(), -6)
    write_wav("heartbeat", heartbeat(), -3)


if __name__ == "__main__":
    asphalt()
    concrete()
    brick()
    crate()
    metal()
    grime()
    soft_particle()
    flare()
    blood_splat()
    vignette()
    tracer()
    ui_circle()
    ui_ring()
    ui_rounded()
    ui_crosshair_icon()
    ui_reload_icon()
    ui_pause_icon()
    ui_heart_icon()
    ui_ammo_icon()
    ui_skull_icon()
    ui_damage_arrow()
    ui_run_icon()
    app_icon()
    audio()
    print("assets generated")
