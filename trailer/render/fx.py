"""Image/FX toolkit for the Mahabharata trailer compositor (numpy + OpenCV)."""
import math
import os
import subprocess
from functools import lru_cache

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FPS = 24
BASE_W, BASE_H = 1920, 804
W, H = BASE_W, BASE_H
S = 1.0  # global scale (1.0 = full 1920x804)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONTS = os.path.join(ROOT, "fonts")
ASSETS = os.path.join(ROOT, "assets")


def init(scale=1.0):
    global W, H, S
    S = scale
    W = int(round(BASE_W * scale / 2) * 2)
    H = int(round(BASE_H * scale / 2) * 2)


# ---------------------------------------------------------------- basics
def f32(img):
    return img.astype(np.float32) * (1.0 / 255.0)


def u8(img):
    return (np.clip(img, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def ease_io(x):
    x = min(max(x, 0.0), 1.0)
    return 0.5 - 0.5 * math.cos(math.pi * x)


def lerp(a, b, t):
    return a + (b - a) * t


def env(t, dur, fin=0.4, fout=0.4):
    """0..1 envelope with fade-in/out (seconds)."""
    a = 1.0 if fin <= 0 else smooth(t / fin)
    b = 1.0 if fout <= 0 else smooth((dur - t) / fout)
    return max(0.0, min(a, b))


def view(src, scale, cx, cy, rot=0.0, interp=cv2.INTER_LINEAR, out=None):
    """Sample a W x H view from src (float or uint8 HxWxC). scale = output px per source px.
    (cx, cy) is the source point (in source px) shown at the frame centre."""
    ow, oh = (W, H) if out is None else out
    a = math.cos(rot) * scale
    b = math.sin(rot) * scale
    M = np.array([[a, b, ow / 2 - (a * cx + b * cy)],
                  [-b, a, oh / 2 - (-b * cx + a * cy)]], np.float32)
    return cv2.warpAffine(src, M, (ow, oh), flags=interp, borderMode=cv2.BORDER_REFLECT101)


def cover_scale(sw, sh, ow=None, oh=None):
    ow = ow or W
    oh = oh or H
    return max(ow / sw, oh / sh)


def kenburns(src, t01, z0=1.0, z1=1.08, c0=(0.5, 0.5), c1=(0.5, 0.5), rot0=0.0, rot1=0.0, interp=cv2.INTER_LINEAR):
    sh, sw = src.shape[:2]
    k = ease_io(t01)
    base = cover_scale(sw, sh)
    z = lerp(z0, z1, k)
    cx = lerp(c0[0], c1[0], k) * sw
    cy = lerp(c0[1], c1[1], k) * sh
    # keep inside the source
    hw, hh = W / (2 * base * z), H / (2 * base * z)
    cx = min(max(cx, hw), sw - hw)
    cy = min(max(cy, hh), sh - hh)
    return view(src, base * z, cx, cy, lerp(rot0, rot1, k), interp)


# ---------------------------------------------------------------- grading
GRADES = {
    # lift, gamma, gain (rgb), saturation, contrast, shadow tint, highlight tint
    "gold": ((0.015, 0.008, 0.0), (1.0, 1.02, 1.08), (1.06, 0.98, 0.86), 1.05, 1.10, (0.02, 0.0, -0.02), (0.05, 0.02, -0.04)),
    "dusk": ((0.01, 0.004, 0.012), (1.0, 1.03, 1.06), (1.04, 0.96, 0.86), 0.95, 1.14, (0.0, 0.01, 0.03), (0.06, 0.02, -0.05)),
    "cosmic": ((0.0, 0.004, 0.02), (1.0, 1.0, 1.0), (1.05, 1.0, 0.95), 1.12, 1.08, (0.0, 0.005, 0.03), (0.04, 0.02, -0.03)),
    "storm": ((0.01, 0.012, 0.016), (1.02, 1.02, 1.0), (0.96, 0.98, 1.0), 0.55, 1.18, (0.0, 0.01, 0.025), (0.03, 0.02, 0.0)),
    "night": ((0.0, 0.006, 0.02), (1.04, 1.02, 0.98), (0.98, 0.96, 0.94), 0.9, 1.08, (0.0, 0.008, 0.03), (0.05, 0.03, -0.02)),
    "neutral": ((0, 0, 0), (1, 1, 1), (1, 1, 1), 1.0, 1.0, (0, 0, 0), (0, 0, 0)),
    "ember": ((0.02, 0.006, 0.0), (1.0, 1.0, 1.12), (1.2, 0.95, 0.7), 1.4, 1.24, (0.02, 0.0, -0.012), (0.08, 0.02, -0.06)),
    "warm_hi": ((0.02, 0.01, 0.0), (1.0, 1.0, 1.05), (1.04, 0.97, 0.84), 0.92, 1.16, (0.025, 0.008, -0.01), (0.06, 0.025, -0.05)),
}


def grade(img, name="gold", amount=1.0, exposure=0.0):
    if name is None:
        return img
    lift, gamma, gain, sat, con, ts, th = GRADES[name]
    x = img
    if exposure:
        x = x * (2.0 ** exposure)
    lift = np.array(lift, np.float32) * amount
    gain = 1 + (np.array(gain, np.float32) - 1) * amount
    gamma = 1 + (np.array(gamma, np.float32) - 1) * amount
    x = np.clip(x * gain + lift * (1 - x), 0, 1.5)
    x = np.power(np.maximum(x, 1e-6), 1.0 / gamma)
    lum = (x[..., 0] * 0.2126 + x[..., 1] * 0.7152 + x[..., 2] * 0.0722)[..., None]
    s = 1 + (sat - 1) * amount
    x = lum + (x - lum) * s
    c = 1 + (con - 1) * amount
    x = (x - 0.45) * c + 0.45
    lum = np.clip(lum, 0, 1)
    x = x + np.array(ts, np.float32) * amount * (1 - lum) ** 2 + np.array(th, np.float32) * amount * lum ** 2
    return np.clip(x, 0, 1)


def vignette_mask():
    return _vig(W, H)


@lru_cache(maxsize=4)
def _vig(w, h):
    y, x = np.mgrid[0:h, 0:w].astype(np.float32)
    nx = (x - w / 2) / (w / 2)
    ny = (y - h / 2) / (h / 2)
    r = np.sqrt(nx * nx * 0.85 + ny * ny * 1.15)
    return np.clip(1 - 0.42 * np.clip(r - 0.35, 0, None) ** 1.6, 0, 1)[..., None].astype(np.float32)


def vignette(img, strength=1.0):
    v = _vig(W, H)
    return img * (1 - strength + strength * v)


@lru_cache(maxsize=2)
def _grain_bank(w, h, n=12, seed=7):
    rng = np.random.default_rng(seed)
    bank = []
    for _ in range(n):
        g = rng.standard_normal((h // 2, w // 2)).astype(np.float32)
        g = cv2.resize(g, (w, h), interpolation=cv2.INTER_LINEAR)
        g = cv2.GaussianBlur(g, (0, 0), 0.6)
        bank.append(g / (g.std() + 1e-6))
    return bank


def grain(img, frame, amount=0.035):
    bank = _grain_bank(W, H)
    g = bank[frame % len(bank)]
    lum = img.mean(axis=2, keepdims=True)
    w = amount * (0.35 + 0.65 * (1 - np.abs(lum - 0.45) * 1.6).clip(0.15, 1))
    return img + g[..., None] * w


def bloom(img, threshold=0.72, strength=0.35, radius=0.02, tint=(1.0, 0.86, 0.62)):
    small = cv2.resize(img, (W // 4, H // 4), interpolation=cv2.INTER_AREA)
    hi = np.clip(small - threshold, 0, None) / (1 - threshold)
    r = max(1.0, radius * W / 4)
    b = cv2.GaussianBlur(hi, (0, 0), r) + 0.6 * cv2.GaussianBlur(hi, (0, 0), r * 3.5)
    b = cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return img + b * np.array(tint, np.float32) * strength


def god_rays(img, center, strength=0.5, threshold=0.6, length=0.92, samples=28, tint=(1.0, 0.85, 0.6)):
    """Radial light rays from bright areas around `center` (fractional coords)."""
    sw, sh = W // 4, H // 4
    small = cv2.resize(img, (sw, sh), interpolation=cv2.INTER_AREA)
    lum = small.max(axis=2)
    src = np.clip(lum - threshold, 0, None) / max(1e-3, 1 - threshold)
    cx, cy = center[0] * sw, center[1] * sh
    acc = np.zeros_like(src)
    decay = 1.0
    wsum = 0.0
    for i in range(samples):
        sc = 1.0 - (1.0 - length) * i / samples
        M = np.array([[sc, 0, cx * (1 - sc)], [0, sc, cy * (1 - sc)]], np.float32)
        acc += cv2.warpAffine(src, M, (sw, sh), flags=cv2.INTER_LINEAR) * decay
        wsum += decay
        decay *= 0.94
    acc /= wsum
    acc = cv2.GaussianBlur(acc, (0, 0), 1.2)
    acc = cv2.resize(acc, (W, H), interpolation=cv2.INTER_LINEAR)
    return img + acc[..., None] * np.array(tint, np.float32) * strength


def flare(img, pos, strength=0.6, tint=(1.0, 0.8, 0.55)):
    """Anamorphic streak + soft glow at fractional position."""
    x0, y0 = pos[0] * W, pos[1] * H
    yy, xx = np.ogrid[0:H, 0:W]
    dx = (xx - x0) / W
    dy = (yy - y0) / H
    glow = np.exp(-(dx * dx + dy * dy) / 0.004) * 0.9 + np.exp(-(dx * dx + dy * dy) / 0.03) * 0.25
    streak = np.exp(-(dy * dy) / 0.00002) * np.exp(-np.abs(dx) / 0.35) * 0.55
    m = (glow + streak).astype(np.float32)
    return img + m[..., None] * np.array(tint, np.float32) * strength


def screen(base, layer, amount=1.0):
    l = layer * amount
    return 1 - (1 - base) * (1 - np.clip(l, 0, 1))


def over(base, rgb, alpha):
    a = alpha if alpha.ndim == 3 else alpha[..., None]
    return base * (1 - a) + rgb * a


# ---------------------------------------------------------------- noise / fog
@lru_cache(maxsize=8)
def noise_tex(seed=1, size=512, octaves=5):
    """Tileable fBm noise texture in [0,1] (size x size)."""
    rng = np.random.default_rng(seed)
    tex = np.zeros((size, size), np.float32)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        n = 4 * 2 ** o
        g = rng.random((n, n)).astype(np.float32)
        g = np.tile(g, (3, 3))
        up = cv2.resize(g, (size * 3, size * 3), interpolation=cv2.INTER_CUBIC)[size:2 * size, size:2 * size]
        tex += up * amp
        tot += amp
        amp *= 0.5
    tex /= tot
    tex = (tex - tex.min()) / (tex.max() - tex.min() + 1e-6)
    return tex


def fog(t, seed=1, density=0.35, speed=(0.012, 0.002), scale=1.6, low=0.35, high=0.85, vgrad=0.6):
    """Animated fog alpha (H x W x 1) drifting over time."""
    tex = noise_tex(seed)
    n = tex.shape[0]
    big = np.tile(tex, (2, 3))
    ox = int((t * speed[0] * n * 3) % n)
    oy = int((t * speed[1] * n * 3) % n)
    tw, th = int(n * 1.6 / scale * 1.0), int(n * 0.67 / scale)
    tw = max(16, min(tw, big.shape[1] - ox - 1))
    th = max(16, min(th, big.shape[0] - oy - 1))
    crop = big[oy:oy + th, ox:ox + tw]
    f = cv2.resize(crop, (W, H), interpolation=cv2.INTER_CUBIC)
    f = np.clip((f - low) / (high - low), 0, 1)
    if vgrad:
        g = np.linspace(1 - vgrad, 1, H, dtype=np.float32)[:, None]
        f = f * g
    return (f * density)[..., None]


# ---------------------------------------------------------------- particles
class Particles:
    """Deterministic glowing particles (embers / dust / sparks / gold)."""

    def __init__(self, n=160, seed=3, kind="embers", area=(0, 0, 1, 1)):
        rng = np.random.default_rng(seed)
        self.kind = kind
        self.n = n
        x0, y0, x1, y1 = area
        self.p = np.stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n)], 1)
        if kind == "embers":
            self.v = np.stack([rng.normal(0.01, 0.02, n), rng.uniform(-0.09, -0.03, n)], 1)
            self.size = rng.uniform(1.2, 3.2, n)
            self.col = np.array([1.0, 0.55, 0.18], np.float32)
        elif kind == "dust":
            self.v = np.stack([rng.normal(0.006, 0.01, n), rng.normal(-0.004, 0.008, n)], 1)
            self.size = rng.uniform(0.8, 2.6, n)
            self.col = np.array([1.0, 0.9, 0.72], np.float32)
        elif kind == "gold":
            self.v = np.stack([rng.normal(0.0, 0.02, n), rng.uniform(-0.05, -0.01, n)], 1)
            self.size = rng.uniform(1.0, 3.0, n)
            self.col = np.array([1.0, 0.82, 0.4], np.float32)
        else:  # sparks
            self.v = np.stack([rng.normal(0.08, 0.06, n), rng.uniform(-0.25, -0.08, n)], 1)
            self.size = rng.uniform(1.0, 2.2, n)
            self.col = np.array([1.0, 0.62, 0.25], np.float32)
        self.ph = rng.uniform(0, 6.28, n)
        self.fl = rng.uniform(0.6, 3.0, n)
        self.br = rng.uniform(0.35, 1.0, n)

    def render(self, t, strength=1.0):
        layer = np.zeros((H, W, 3), np.float32)
        pos = self.p + self.v * t
        pos[:, 0] += 0.01 * np.sin(t * 0.7 + self.ph)
        pos = np.mod(pos, 1.0)
        flick = 0.65 + 0.35 * np.sin(t * self.fl * 3 + self.ph)
        for i in range(self.n):
            x, y = pos[i, 0] * W, pos[i, 1] * H
            r = self.size[i] * S * (1.0 if self.kind != "dust" else 1.3)
            sprite = _sprite(round(r * 4) / 4)
            k = sprite.shape[0] // 2
            xi, yi = int(x), int(y)
            x0, y0 = xi - k, yi - k
            x1, y1 = x0 + sprite.shape[1], y0 + sprite.shape[0]
            if x1 <= 0 or y1 <= 0 or x0 >= W or y0 >= H:
                continue
            sx0, sy0 = max(0, -x0), max(0, -y0)
            sx1 = sprite.shape[1] - max(0, x1 - W)
            sy1 = sprite.shape[0] - max(0, y1 - H)
            layer[max(0, y0):min(H, y1), max(0, x0):min(W, x1)] += \
                sprite[sy0:sy1, sx0:sx1, None] * (self.br[i] * flick[i])
        return layer * self.col * strength


@lru_cache(maxsize=64)
def _sprite(r):
    k = int(math.ceil(r * 4)) + 1
    y, x = np.mgrid[-k:k + 1, -k:k + 1].astype(np.float32)
    d2 = x * x + y * y
    core = np.exp(-d2 / (2 * (r * 0.5) ** 2))
    halo = np.exp(-d2 / (2 * (r * 1.6) ** 2)) * 0.35
    return (core + halo).astype(np.float32)


# ---------------------------------------------------------------- text
@lru_cache(maxsize=16)
def font(name, size):
    return ImageFont.truetype(os.path.join(FONTS, name), size)


def text_rgba(text, fontname, size, tracking=0.0, style="gold", stroke=0, glow=0.0, lang=None):
    """Render text to an RGBA float image. style: gold | white | silver | cream.
    lang='hi' shapes Devanagari (needs libraqm); tracking is in em units (Latin only)."""
    size = max(8, int(round(size * S)))
    f = font(fontname, size)
    pad = int(size * 0.7)
    probe = ImageDraw.Draw(Image.new("L", (4, 4)))
    kw = {"language": lang} if lang else {}
    if tracking and not lang:
        widths = [f.getlength(ch) for ch in text]
        total = sum(widths) + tracking * size * (len(text) - 1)
        x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=f)
        total = max(total, 1)
    else:
        x0, y0, x1, y1 = probe.textbbox((0, 0), text, font=f, **kw)
        total = x1 - x0
    w = int(total + pad * 2)
    h = int((y1 - min(0, y0)) + pad * 2)
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    if tracking and not lang:
        x = pad
        for ch, cw in zip(text, widths):
            d.text((x, pad - min(0, y0)), ch, font=f, fill=255)
            x += cw + tracking * size
    else:
        d.text((pad - x0, pad - min(0, y0)), text, font=f, fill=255, **kw)
    a = np.asarray(mask).astype(np.float32) / 255.0
    yy = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    if style == "gold":
        top = np.array([1.0, 0.93, 0.68], np.float32)
        mid = np.array([0.95, 0.72, 0.32], np.float32)
        bot = np.array([0.55, 0.33, 0.12], np.float32)
        g = np.where(yy < 0.52, top + (mid - top) * (yy / 0.52), mid + (bot - mid) * ((yy - 0.52) / 0.48))
        rgb = np.broadcast_to(g[:, None, :] if g.ndim == 2 else g, (h, w, 3)).copy() if False else np.repeat(g[:, None, :], w, axis=1)
        # bevel: light from top-left using alpha gradient
        ab = cv2.GaussianBlur(a, (0, 0), max(0.8, size / 40))
        gx = cv2.Sobel(ab, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(ab, cv2.CV_32F, 0, 1, ksize=3)
        shade = np.clip(0.5 + (-gx - gy) * 1.6, 0, 1)[..., None]
        rgb = np.clip(rgb * (0.78 + 0.5 * shade), 0, 1)
    elif style == "silver":
        g = (0.95 - 0.35 * yy)[:, :, None] * np.array([1.0, 0.98, 0.95], np.float32)
        rgb = np.repeat(g, w, axis=1)
    elif style == "cream":
        rgb = np.ones((h, w, 3), np.float32) * np.array([1.0, 0.95, 0.86], np.float32)
    else:
        rgb = np.ones((h, w, 3), np.float32)
    out = np.dstack([rgb, a])
    if glow > 0:
        gl = cv2.GaussianBlur(a, (0, 0), size * 0.25) * glow
        out = _add_glow(out, gl, (1.0, 0.7, 0.3) if style == "gold" else (1, 1, 1))
    return out


def _add_glow(rgba, gl, col):
    rgb, a = rgba[..., :3], rgba[..., 3:]
    glow_rgb = np.array(col, np.float32) * gl[..., None]
    na = np.clip(a + gl[..., None] * (1 - a), 0, 1)
    nrgb = (rgb * a + glow_rgb * (1 - a)) / np.maximum(na, 1e-4)
    return np.dstack([nrgb, na])


def place(base, rgba, cx, cy, opacity=1.0, scale=1.0, blur=0.0, shadow=0.0):
    """Composite an RGBA float image centred at fractional (cx, cy)."""
    img = rgba
    if scale != 1.0:
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC if scale > 1 else cv2.INTER_AREA)
    if blur > 0.05:
        img = cv2.GaussianBlur(img, (0, 0), blur)
    h, w = img.shape[:2]
    x0 = int(cx * W - w / 2)
    y0 = int(cy * H - h / 2)
    xs0, ys0 = max(0, -x0), max(0, -y0)
    xe, ye = min(w, W - x0), min(h, H - y0)
    if xe <= xs0 or ye <= ys0:
        return base
    region = base[y0 + ys0:y0 + ye, x0 + xs0:x0 + xe]
    src = img[ys0:ye, xs0:xe]
    a = src[..., 3:] * opacity
    if shadow > 0:
        sh = cv2.GaussianBlur(src[..., 3], (0, 0), max(2, h * 0.04))[..., None] * shadow * opacity
        region = region * (1 - sh * 0.85)
    base[y0 + ys0:y0 + ye, x0 + xs0:x0 + xe] = region * (1 - a) + src[..., :3] * a
    return base


# ---------------------------------------------------------------- video reading
class Clip:
    """Sequential frame reader for a stock clip, already conformed to 24 fps.
    speed < 1 = slow motion (uses source frames; best with 50/60 fps sources)."""

    def __init__(self, path, t_in=0.0, speed=1.0, overscan=1.12, blend=False):
        self.path = path
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0", path], capture_output=True, text=True)
        sw, sh = map(int, probe.stdout.strip().split(",")[:2])
        sc = max(W * overscan / sw, H * overscan / sh)
        self.w = int(round(sw * sc / 2) * 2)
        self.h = int(round(sh * sc / 2) * 2)
        rate = "framerate=fps=24:interp_start=0:interp_end=255" if blend else "fps=24"
        vf = f"setpts=(PTS-STARTPTS)/{speed},{rate},scale={self.w}:{self.h}:flags=lanczos"
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-ss", f"{t_in:.3f}", "-i", path, "-an", "-vf", vf,
                                      "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, bufsize=self.w * self.h * 3 * 2)
        self.last = None

    def read(self):
        n = self.w * self.h * 3
        buf = self.proc.stdout.read(n)
        if len(buf) < n:
            if self.last is None:
                self.last = np.zeros((self.h, self.w, 3), np.float32)
            return self.last
        self.last = f32(np.frombuffer(buf, np.uint8).reshape(self.h, self.w, 3))
        return self.last

    def close(self):
        try:
            self.proc.stdout.close()
            self.proc.kill()
        except Exception:
            pass


def load_rgba(path):
    im = Image.open(path).convert("RGBA")
    return f32(np.asarray(im))


def load_rgb(path):
    return f32(np.asarray(Image.open(path).convert("RGB")))
