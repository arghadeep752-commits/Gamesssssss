"""Shot types, VFX and the edit decision list for the trailer."""
import math
import os
from functools import lru_cache

import cv2
import numpy as np

import fx

STOCK = os.path.expanduser(os.environ.get("MB_STOCK", "~/mb/stock"))
REND = os.path.expanduser(os.environ.get("MB_RENDERS", "~/mb/renders"))
ART = fx.ASSETS
GOLD = np.array([1.0, 0.74, 0.34], np.float32)
WARM = np.array([1.0, 0.86, 0.62], np.float32)


def stock(name):
    return os.path.join(STOCK, name + ".mov")


# ------------------------------------------------------------------ cached art
@lru_cache(maxsize=None)
def art(name):
    p = os.path.join(ART, name)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im.ndim == 3 and im.shape[2] == 4:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    return im.astype(np.float32) / 255.0


@lru_cache(maxsize=None)
def render_img(name):
    p = os.path.join(REND, name)
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    if im is None:
        raise FileNotFoundError(p)
    if im.ndim == 3 and im.shape[2] == 4:
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA)
    else:
        im = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
    return im.astype(np.float32) / 255.0


def bbox_crop(rgba, pad=8):
    a = rgba[..., 3]
    ys, xs = np.where(a > 0.02)
    y0, y1 = max(0, ys.min() - pad), min(a.shape[0], ys.max() + pad)
    x0, x1 = max(0, xs.min() - pad), min(a.shape[1], xs.max() + pad)
    return rgba[y0:y1, x0:x1].copy()


def _pad(rgba, frac=0.14):
    p = int(max(rgba.shape[:2]) * frac)
    return cv2.copyMakeBorder(rgba, p, p, p, p, cv2.BORDER_CONSTANT, value=0)


def _feather_left(rgba, px=70):
    out = rgba.copy()
    ramp = np.clip(np.arange(out.shape[1], dtype=np.float32) / px, 0, 1)
    out[..., 3] *= ramp[None, :]
    return out


@lru_cache(maxsize=None)
def sprite(name):
    """Cutout sprites used by the VFX (padded so glows can spread)."""
    if name == "krishna":
        k = _feather_left(art("flute_fg.png")[:, 380:1000].copy())
        return _pad(bbox_crop(k))
    if name == "krishna_upper":
        k = bbox_crop(_feather_left(art("flute_fg.png")[:, 380:1000].copy()))
        k = k[: int(k.shape[0] * 0.66)].copy()
        ramp = np.clip((k.shape[0] - np.arange(k.shape[0], dtype=np.float32)) / 60.0, 0, 1)
        k[..., 3] *= ramp[:, None]
        return _pad(k)
    if name == "arjuna":
        return _pad(bbox_crop(art("chariot_arjuna.png")))
    if name == "wheel":
        return render_img("wheel_alpha.png")
    raise KeyError(name)


@lru_cache(maxsize=None)
def divine(name, glow=1.0):
    """Body of a 'divine' cutout: darkened detail + thin burning golden rim (RGBA, alpha = cutout alpha)."""
    s = sprite(name)
    rgb, a = s[..., :3], s[..., 3]
    k = max(3, int(min(a.shape) * 0.008)) | 1
    er = cv2.erode(a, np.ones((k, k), np.uint8))
    rim = cv2.GaussianBlur(np.clip(a - er, 0, 1), (0, 0), k * 0.5)
    col = rgb * 0.55 + rim[..., None] * GOLD * 1.6 * glow
    return np.dstack([col, a]).astype(np.float32)


@lru_cache(maxsize=None)
def divine_glow(name, size=0.035):
    """Additive halo around a cutout (RGBA: rgb = gold, alpha = glow strength)."""
    a = sprite(name)[..., 3]
    r = max(4.0, min(a.shape) * size)
    g = cv2.GaussianBlur(a, (0, 0), r) * 0.8 + cv2.GaussianBlur(a, (0, 0), r * 3) * 0.5
    g = np.clip(g - a * 0.6, 0, 1)
    return np.dstack([np.broadcast_to(GOLD * 1.25, g.shape + (3,)), g]).astype(np.float32)


@lru_cache(maxsize=None)
def chakra_tex(size=1024, teeth=108, spokes=24, fancy=True):
    """Procedural Sudarshan Chakra intensity texture (float 0..1)."""
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    nx, ny = (x - size / 2) / (size / 2), (y - size / 2) / (size / 2)
    r = np.sqrt(nx * nx + ny * ny)
    th = np.arctan2(ny, nx)
    tooth = (np.sin(th * teeth) > 0).astype(np.float32)
    outer = ((r > 0.86) & (r < 0.86 + 0.1 * (0.55 + 0.45 * tooth))).astype(np.float32)
    ring = lambda r0, w: np.exp(-((r - r0) / w) ** 2)
    rings = ring(0.84, 0.012) + ring(0.70, 0.010) * 0.9 + ring(0.47, 0.012) + ring(0.28, 0.02) * 1.2
    sp = np.abs(np.sin(th * spokes / 2))
    spoke = np.exp(-(sp / 0.035) ** 2) * ((r > 0.28) & (r < 0.84))
    petals = 0
    if fancy:
        pet = np.cos(th * 12) * 0.5 + 0.5
        petals = (np.exp(-((r - (0.55 + 0.12 * pet)) / 0.015) ** 2) * 0.8)
    hub = np.exp(-(r / 0.13) ** 2) * 1.2
    tex = np.clip(outer + rings + spoke * 0.9 + petals + hub, 0, 1.5)
    tex *= (r < 1.0)
    return tex.astype(np.float32)


def rotate_img(img, ang_deg, scale=1.0):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), ang_deg, scale)
    return cv2.warpAffine(img, M, (w, h), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)


def put(base, rgba, cx, cy, height, opacity=1.0, add=False, rot=0.0):
    """Place an RGBA sprite with its centre at fractional (cx, cy) and given height (fraction of H)."""
    hpx = max(2, int(height * fx.H))
    sc = hpx / rgba.shape[0]
    wpx = max(2, int(rgba.shape[1] * sc))
    spr = cv2.resize(rgba, (wpx, hpx), interpolation=cv2.INTER_AREA if sc < 1 else cv2.INTER_CUBIC)
    if rot:
        pad = int(max(wpx, hpx) * 0.5)
        spr = cv2.copyMakeBorder(spr, pad, pad, pad, pad, cv2.BORDER_CONSTANT, value=0)
        spr = rotate_img(spr, rot)
    h, w = spr.shape[:2]
    x0, y0 = int(cx * fx.W - w / 2), int(cy * fx.H - h / 2)
    xs, ys = max(0, -x0), max(0, -y0)
    xe, ye = min(w, fx.W - x0), min(h, fx.H - y0)
    if xe <= xs or ye <= ys:
        return base
    reg = base[y0 + ys:y0 + ye, x0 + xs:x0 + xe]
    s = spr[ys:ye, xs:xe]
    a = s[..., 3:] * opacity
    if add:
        base[y0 + ys:y0 + ye, x0 + xs:x0 + xe] = reg + s[..., :3] * a
    else:
        base[y0 + ys:y0 + ye, x0 + xs:x0 + xe] = reg * (1 - a) + s[..., :3] * a
    return base


def put_at(base, rgba, ax, ay, sx, sy, height, opacity=1.0, add=False, rot=0.0):
    """Place sprite so its fractional point (ax, ay) lands on frame point (sx, sy)."""
    h, w = rgba.shape[:2]
    hf = height
    wf = height * fx.H * (w / h) / fx.W
    cx = sx + (0.5 - ax) * wf
    cy = sy + (0.5 - ay) * hf
    return put(base, rgba, cx, cy, height, opacity, add, rot)


# ------------------------------------------------------------------ overlays
class Overlay:
    def open(self, t0):
        pass

    def close(self):
        pass


class Embers(Overlay):
    def __init__(self, n=120, seed=3, strength=0.9, kind="embers", area=(0, 0, 1, 1)):
        self.p = fx.Particles(n, seed, kind, area)
        self.k = strength

    def apply(self, img, t, shot):
        return img + self.p.render(t + shot.start, self.k)


class Fog(Overlay):
    def __init__(self, density=0.25, color=(1.0, 0.78, 0.55), seed=2, speed=(0.012, 0.0), vgrad=0.6):
        self.d, self.c, self.s, self.sp, self.vg = density, np.array(color, np.float32), seed, speed, vgrad

    def apply(self, img, t, shot):
        f = fx.fog(t + shot.start, self.s, self.d, self.sp, vgrad=self.vg)
        return img * (1 - f) + self.c * f


class Rays(Overlay):
    def __init__(self, center=(0.5, 0.3), strength=0.45, threshold=0.62, tint=(1.0, 0.82, 0.55), move=(0, 0)):
        self.c, self.k, self.th, self.tint, self.mv = center, strength, threshold, tint, move

    def apply(self, img, t, shot):
        u = t / max(shot.dur, 1e-3)
        c = (self.c[0] + self.mv[0] * u, self.c[1] + self.mv[1] * u)
        return fx.god_rays(img, c, self.k, self.th, tint=self.tint)


class Flare(Overlay):
    def __init__(self, pos=(0.5, 0.3), strength=0.5, move=(0, 0), pulse=0.0):
        self.p, self.k, self.mv, self.pl = pos, strength, move, pulse

    def apply(self, img, t, shot):
        u = t / max(shot.dur, 1e-3)
        k = self.k * (1 + self.pl * math.sin(t * 2.1))
        return fx.flare(img, (self.p[0] + self.mv[0] * u, self.p[1] + self.mv[1] * u), k)


class StockScreen(Overlay):
    """Screen-blend a stock overlay clip (embers/dust/smoke/clouds on black)."""

    def __init__(self, name, t_in=0.0, amount=0.6, tint=(1, 1, 1), speed=1.0, gain=1.0):
        self.name, self.t_in, self.k, self.tint, self.sp, self.g = name, t_in, amount, np.array(tint, np.float32), speed, gain
        self.clip = None

    def open(self, t0):
        self.clip = fx.Clip(stock(self.name), self.t_in + t0 * self.sp, self.sp, overscan=1.0)

    def apply(self, img, t, shot):
        fr = self.clip.read()
        fr = cv2.resize(fr, (fx.W, fx.H), interpolation=cv2.INTER_AREA)
        return fx.screen(img, np.clip(fr * self.g, 0, 1) * self.tint, self.k)

    def close(self):
        if self.clip:
            self.clip.close()


class Shake(Overlay):
    def __init__(self, amp=0.006, freq=9.0, seed=1):
        self.a, self.f = amp, freq
        self.ph = np.random.default_rng(seed).uniform(0, 6.28, 4)

    def apply(self, img, t, shot):
        dx = self.a * fx.W * (math.sin(t * self.f + self.ph[0]) + 0.5 * math.sin(t * self.f * 2.3 + self.ph[1]))
        dy = self.a * fx.H * (math.sin(t * self.f * 1.3 + self.ph[2]) + 0.5 * math.sin(t * self.f * 2.9 + self.ph[3]))
        M = np.array([[1.02, 0, -0.01 * fx.W + dx], [0, 1.02, -0.01 * fx.H + dy]], np.float32)
        return cv2.warpAffine(img, M, (fx.W, fx.H), borderMode=cv2.BORDER_REFLECT101)


class Flicker(Overlay):
    def __init__(self, amount=0.12, color=(1.0, 0.45, 0.2)):
        self.k, self.c = amount, np.array(color, np.float32)

    def apply(self, img, t, shot):
        n = 0.5 + 0.5 * math.sin(t * 17) * math.sin(t * 7.3 + 1)
        return img + self.c * self.k * n * fx.vignette_mask()


# ------------------------------------------------------------------ text overlays
@lru_cache(maxsize=None)
def text_img(text, fontname, size, tracking=0.0, style="gold", lang=None, glow=0.0):
    return fx.text_rgba(text, fontname, size, tracking, style, glow=glow, lang=lang)


@lru_cache(maxsize=4)
def bottom_band():
    y = np.linspace(0, 1, fx.H, dtype=np.float32)[:, None, None]
    return np.clip((y - 0.6) / 0.4, 0, 1) ** 1.5


class Dialogue:
    def __init__(self, speaker, line, t0, t1, y=0.86):
        self.sp, self.line, self.t0, self.t1, self.y = speaker, line, t0, t1, y

    def apply(self, img, T):
        if not (self.t0 <= T <= self.t1):
            return img
        a = fx.env(T - self.t0, self.t1 - self.t0, 0.35, 0.35)
        img = img * (1 - 0.42 * a * bottom_band())
        lab = text_img(self.sp, "FreeSerifBold.ttf", 27, 0, "gold", "hi")
        ln = text_img(self.line, "FreeSerifBold.ttf", 46, 0, "cream", "hi")
        dy = (1 - a) * 0.01
        fx.place(img, lab, 0.5, self.y - 0.075 + dy, opacity=a * 0.95, shadow=0.7)
        fx.place(img, ln, 0.5, self.y + dy, opacity=a, shadow=0.8)
        return img


class Caption:
    """Centered trailer caption (Latin or Devanagari) with optional light sweep."""

    def __init__(self, text, t0, t1, y=0.5, size=60, font="Cardo-Bold.ttf", tracking=0.22, style="gold", lang=None,
                 fin=0.6, fout=0.5, sweep=True, grow=0.03):
        self.text, self.t0, self.t1, self.y = text, t0, t1, y
        self.size, self.font, self.tr, self.style, self.lang = size, font, tracking, style, lang
        self.fin, self.fout, self.sweep, self.grow = fin, fout, sweep, grow

    def apply(self, img, T):
        if not (self.t0 <= T <= self.t1):
            return img
        d = self.t1 - self.t0
        u = T - self.t0
        a = fx.env(u, d, self.fin, self.fout)
        im = text_img(self.text, self.font, self.size, self.tr, self.style, self.lang)
        if self.sweep:
            im = sweep(im, (u / max(d, 0.1)) * 1.6 - 0.3)
        sc = 1.0 + self.grow * (1 - u / d)
        fx.place(img, im, 0.5, self.y, opacity=a, scale=sc, blur=(1 - a) * 3.0, shadow=0.6)
        return img


def sweep(rgba, pos, width=0.12, gain=0.9):
    """Diagonal light sweep across a text/logo RGBA image (pos 0..1 across)."""
    h, w = rgba.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u = (xx / w) + (yy / h) * 0.25 - 0.12
    band = np.exp(-((u - pos) / width) ** 2) * gain
    out = rgba.copy()
    out[..., :3] = np.clip(out[..., :3] + band[..., None] * np.array([1.0, 0.92, 0.75], np.float32), 0, 1.6)
    return out


# ------------------------------------------------------------------ base shot
class Shot:
    def __init__(self, start, end, grade="gold", exposure=0.0, gamount=1.0, overlays=(), texts=(), fin=0.0, fout=0.0,
                 flash_in=0.0, flash_out=0.0, vig=1.0, bloom=0.22, label=""):
        self.start, self.end = start, end
        self.grade, self.exposure, self.gamount = grade, exposure, gamount
        self.overlays, self.texts = list(overlays), list(texts)
        self.fin, self.fout, self.flash_in, self.flash_out = fin, fout, flash_in, flash_out
        self.vig, self.bloom = vig, bloom
        self.label = label
        self.opened = False

    @property
    def dur(self):
        return self.end - self.start

    def open(self, t0):
        for o in self.overlays:
            o.open(t0)
        self.opened = True

    def close(self):
        for o in self.overlays:
            o.close()
        self.opened = False

    def base(self, t):
        return np.zeros((fx.H, fx.W, 3), np.float32)

    def render(self, t):
        img = self.base(t)
        if self.grade:
            img = fx.grade(img, self.grade, self.gamount, self.exposure)
        for o in self.overlays:
            img = o.apply(img, t, self)
        if self.bloom:
            img = fx.bloom(img, 0.7, self.bloom)
        if self.vig:
            img = fx.vignette(img, self.vig)
        T = self.start + t
        for tx in self.texts:
            img = tx.apply(img, T)
        e = fx.env(t, self.dur, self.fin, self.fout)
        if e < 1:
            img = img * e
        if self.flash_in and t < self.flash_in:
            img = img + (1 - t / self.flash_in) ** 2 * 1.2
        if self.flash_out and t > self.dur - self.flash_out:
            img = img + ((t - (self.dur - self.flash_out)) / self.flash_out) ** 2 * 1.4
        return img


class Black(Shot):
    def __init__(self, start, end, **kw):
        kw.setdefault("grade", None)
        kw.setdefault("vig", 0)
        kw.setdefault("bloom", 0)
        super().__init__(start, end, **kw)


class StockShot(Shot):
    def __init__(self, start, end, clip, t_in=0.0, speed=1.0, z0=1.0, z1=1.06, c0=(0.5, 0.5), c1=(0.5, 0.5),
                 blend=False, rot=(0.0, 0.0), **kw):
        super().__init__(start, end, **kw)
        self.clipname, self.t_in, self.speed = clip, t_in, speed
        self.z0, self.z1, self.c0, self.c1, self.blend, self.rot = z0, z1, c0, c1, blend, rot
        self.clip = None

    def open(self, t0):
        super().open(t0)
        self.clip = fx.Clip(stock(self.clipname), self.t_in + t0 * self.speed, self.speed, overscan=1.0, blend=self.blend)

    def close(self):
        super().close()
        if self.clip:
            self.clip.close()

    def base(self, t):
        fr = self.clip.read()
        return fx.kenburns(fr, t / self.dur, self.z0, self.z1, self.c0, self.c1, self.rot[0], self.rot[1])


class StillShot(Shot):
    def __init__(self, start, end, image, z0=1.0, z1=1.06, c0=(0.5, 0.5), c1=(0.5, 0.5), rot=(0.0, 0.0), **kw):
        super().__init__(start, end, **kw)
        self.image, self.z0, self.z1, self.c0, self.c1, self.rot = image, z0, z1, c0, c1, rot

    def base(self, t):
        im = render_img(self.image)[..., :3]
        return fx.kenburns(im, t / self.dur, self.z0, self.z1, self.c0, self.c1, self.rot[0], self.rot[1], cv2.INTER_CUBIC)


class SeqShot(Shot):
    def __init__(self, start, end, prefix, f0, f1, z0=1.0, z1=1.04, c0=(0.5, 0.5), c1=(0.5, 0.5), **kw):
        super().__init__(start, end, **kw)
        self.prefix, self.f0, self.f1 = prefix, f0, f1
        self.z0, self.z1, self.c0, self.c1 = z0, z1, c0, c1

    def base(self, t):
        n = self.f1 - self.f0 + 1
        f = self.f0 + min(n - 1, int(t * fx.FPS * n / max(1, self.dur * fx.FPS)))
        im = cv2.imread(os.path.join(REND, f"{self.prefix}_{f:04d}.png"))[..., ::-1].astype(np.float32) / 255
        return fx.kenburns(im, t / self.dur, self.z0, self.z1, self.c0, self.c1, interp=cv2.INTER_CUBIC)


class ArtShot(Shot):
    """2.5D parallax move over the user's key art: bg plate + cut-out foreground."""

    SCENES = {"flute": ("flute_bg.png", "flute_fg.png", "art_flute.png"),
              "chariot": ("chariot_bg.png", "chariot_fg.png", "art_chariot.png")}

    def __init__(self, start, end, scene, z0=1.0, z1=1.08, c0=(0.5, 0.5), c1=(0.5, 0.5), parallax=0.05,
                 fog=0.0, fogc=(1.0, 0.8, 0.58), moon=False, cloth=False, **kw):
        super().__init__(start, end, **kw)
        self.scene, self.z0, self.z1, self.c0, self.c1 = scene, z0, z1, c0, c1
        self.par, self.fogd, self.fogc, self.moon, self.cloth = parallax, fog, np.array(fogc, np.float32), moon, cloth

    def base(self, t):
        bgn, fgn, _ = self.SCENES[self.scene]
        bg, fg = art(bgn), art(fgn)
        sh, sw = bg.shape[:2]
        u = fx.ease_io(t / self.dur)
        base = fx.cover_scale(sw, sh)
        z = fx.lerp(self.z0, self.z1, u)
        cx, cy = fx.lerp(self.c0[0], self.c1[0], u) * sw, fx.lerp(self.c0[1], self.c1[1], u) * sh
        hw, hh = fx.W / (2 * base * z), fx.H / (2 * base * z)
        cx, cy = min(max(cx, hw), sw - hw), min(max(cy, hh), sh - hh)
        b = fx.view(bg, base * z, cx, cy, interp=cv2.INTER_CUBIC)
        if self.moon:
            b = b * (1 + 0.05 * math.sin((self.start + t) * 1.7))
        if self.fogd:
            f = fx.fog(self.start + t, 5, self.fogd, (0.01, 0.0), vgrad=0.4)
            b = b * (1 - f) + self.fogc * f
        zf = z * (1 + self.par * u)
        layer = fx.view(fg, base * zf, cx, cy, interp=cv2.INTER_CUBIC)
        if self.cloth:
            layer = cloth_warp(layer, self.start + t)
        a = layer[..., 3:]
        img = b * (1 - a) + layer[..., :3] * a
        # light unsharp to counter the up-scaling of the 1365 px art
        bl = cv2.GaussianBlur(img, (0, 0), 1.2)
        return np.clip(img + (img - bl) * 0.45, 0, 1.2)


def cloth_warp(layer, T, amp=0.006, wave=0.22, speed=1.4):
    """Flutter the lower-left (dupatta) area of a layer."""
    h, w = layer.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    m = np.clip((yy / h - 0.45) / 0.3, 0, 1) * np.clip((0.75 - xx / w) / 0.4, 0, 1)
    dx = amp * w * np.sin(2 * np.pi * (yy / (wave * h) - speed * T)) * m
    dy = amp * 0.6 * h * np.sin(2 * np.pi * (xx / (wave * w * 1.3) - speed * 0.8 * T)) * m
    return cv2.remap(layer, xx + dx, yy + dy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REFLECT101)


# ------------------------------------------------------------------ VFX shots
class CosmicBG(Shot):
    """Base for VFX over a cosmic stock plate."""

    def __init__(self, start, end, plate="s_nebula", t_in=0.0, speed=1.0, dim=0.8, zoom=(1.0, 1.06), **kw):
        kw.setdefault("grade", "cosmic")
        super().__init__(start, end, **kw)
        self.plate, self.t_in, self.speed, self.dim, self.zoom = plate, t_in, speed, dim, zoom
        self.clip = None

    def open(self, t0):
        super().open(t0)
        self.clip = fx.Clip(stock(self.plate), self.t_in + t0 * self.speed, self.speed, overscan=1.0)

    def close(self):
        super().close()
        if self.clip:
            self.clip.close()

    def plate_frame(self, t, cy=0.5):
        fr = self.clip.read()
        return fx.kenburns(fr, t / self.dur, self.zoom[0], self.zoom[1], (0.5, cy), (0.5, cy)) * self.dim


def _head_anchor(name):
    a = sprite(name)[..., 3]
    ys, xs = np.where(a > 0.5)
    top = ys.min()
    band = (ys < top + a.shape[0] * 0.12)
    return float(xs[band].mean() / a.shape[1]), float((top + a.shape[0] * 0.09) / a.shape[0])


KHEAD = None
KUHEAD = None


def heads():
    global KHEAD, KUHEAD
    if KHEAD is None:
        KHEAD = _head_anchor("krishna")
        KUHEAD = _head_anchor("krishna_upper")
    return KHEAD, KUHEAD


def halo_layer(T, size=1.25, speed=18, strength=0.55):
    h = chakra_tex(768)
    h = cv2.resize(rotate_img(h, -T * speed), (int(fx.H * size), int(fx.H * size)))
    return np.dstack([np.broadcast_to(GOLD * 1.35, h.shape + (3,)), np.clip(h * strength, 0, 1)])


class VishwaRise(CosmicBG):
    def base(self, t):
        KHEAD, KUHEAD = heads()
        u = fx.ease_io(t / self.dur)
        p = -0.45 * (1 - u)          # tilt up: content slides down
        img = self.plate_frame(t, 0.5 + 0.08 * (1 - u))
        T = self.start + t
        gin = fx.smooth((t - 0.3) / 2.4)
        hx, hy = 0.5, 0.27 + p * 1.0
        put(img, halo_layer(T, 1.05, 18, 0.5 * gin), hx, hy, 1.05, 1.0, add=True)
        put_at(img, divine_glow("krishna"), KHEAD[0], KHEAD[1], hx, hy, 1.7, 0.9 * gin, add=True)
        put_at(img, divine("krishna", 1.2), KHEAD[0], KHEAD[1], hx, hy, 1.7, gin)
        img = fx.god_rays(img, (hx, max(0.02, hy)), 0.5 * gin, 0.55)
        put(img, divine("arjuna", 0.5), 0.76, 1.0 + (-p) * -1.2 + 0.0, 0.95, 1.0)
        return img


class Mandala(CosmicBG):
    def base(self, t):
        KHEAD, KUHEAD = heads()
        img = self.plate_frame(t)
        T = self.start + t
        put(img, halo_layer(T, 1.5, 10, 0.42), 0.5, 0.3, 1.5, 1.0, add=True)
        k = divine("krishna", 1.0)
        n = 12
        grow = 0.7 + 0.3 * fx.smooth(t / 1.5)
        for i in range(n):
            ang = i * 360 / n + T * 6
            put_at(img, k, KHEAD[0], KHEAD[1] + 0.25, 0.5, 0.42, 1.2 * grow, 0.2, add=True, rot=ang)
        put_at(img, divine_glow("krishna"), KHEAD[0], KHEAD[1], 0.5, 0.3, 1.25, 0.9, add=True)
        put_at(img, divine("krishna", 1.3), KHEAD[0], KHEAD[1], 0.5, 0.3, 1.25, 1.0)
        return fx.god_rays(img, (0.5, 0.3), 0.55, 0.5)


class CosmicFace(CosmicBG):
    def base(self, t):
        KHEAD, KUHEAD = heads()
        img = self.plate_frame(t)
        k = divine("krishna_upper", 1.2)
        u = t / self.dur
        for i in range(4, 0, -1):
            sc = 1.0 + 0.2 * i * (0.6 + 0.4 * u)
            put_at(img, k, KUHEAD[0], KUHEAD[1], 0.5, 0.36, 1.35 * sc, 0.14 * (1 - i / 5), add=True,
                   rot=(i % 2 * 2 - 1) * i * 1.5)
        put_at(img, divine_glow("krishna_upper"), KUHEAD[0], KUHEAD[1], 0.5, 0.36, 1.35 * (1 + 0.05 * u), 0.8, add=True)
        put_at(img, k, KUHEAD[0], KUHEAD[1], 0.5, 0.36, 1.35 * (1 + 0.05 * u), 1.0)
        return fx.god_rays(img, (0.5, 0.22), 0.5, 0.55)


class ArjunaAwe(CosmicBG):
    def base(self, t):
        img = self.plate_frame(t)
        u = t / self.dur
        img = fx.flare(img, (0.78, 0.18), 0.6 + 1.6 * u ** 2)
        img = fx.god_rays(img, (0.78, 0.18), 0.6 + 0.6 * u, 0.5)
        put(img, divine_glow("arjuna", 0.02), 0.33, 0.62, 1.15 * (1 + 0.04 * u), 0.35 + 0.6 * u, add=True)
        put(img, divine("arjuna", 0.6 + 1.0 * u), 0.33, 0.62, 1.15 * (1 + 0.04 * u), 1.0)
        return img + (u ** 4) * 1.4


class Chakra(CosmicBG):
    def base(self, t):
        img = self.plate_frame(t) * 0.85
        T = self.start + t
        tex = chakra_tex(1024)
        spin = T * 220
        acc = np.zeros_like(tex)
        for j in range(5):
            acc += rotate_img(tex, spin + j * 3.0)
        acc /= 5
        sc = 0.9 + 0.12 * fx.ease_io(t / self.dur)
        # metallic shading: bright sector rotating opposite
        size = acc.shape[0]
        y, x = np.mgrid[0:size, 0:size].astype(np.float32)
        th = np.arctan2(y - size / 2, x - size / 2)
        spec = 0.55 + 0.45 * np.cos(th + T * 1.5) ** 8
        col = np.dstack([acc * spec * 1.25, acc * spec * 0.88, acc * spec * 0.42])
        alpha = np.clip(acc * 1.2, 0, 1)
        glow = cv2.GaussianBlur(acc, (0, 0), 18) * 0.9
        rgba_glow = np.dstack([np.broadcast_to(GOLD * 1.5, glow.shape + (3,)), np.clip(glow, 0, 1)])
        put(img, rgba_glow, 0.5, 0.5, 1.05 * sc * 1.25, 1.0, add=True)
        put(img, np.dstack([col, alpha]), 0.5, 0.5, 1.05 * sc, 1.0)
        img = fx.god_rays(img, (0.5, 0.5), 0.45, 0.6)
        return img


class Arrows(Shot):
    def __init__(self, start, end, plate="s_storm_field", t_in=0.0, n=46, seed=5, **kw):
        kw.setdefault("grade", "storm")
        super().__init__(start, end, **kw)
        self.plate, self.t_in = plate, t_in
        rng = np.random.default_rng(seed)
        self.a = []
        for i in range(n):
            left = rng.random() < 0.8
            x0 = rng.uniform(-0.4, 0.3) if left else rng.uniform(0.7, 1.4)
            y0 = rng.uniform(0.25, 0.85)
            vx = rng.uniform(0.9, 1.5) * (1 if left else -1)
            vy = rng.uniform(-0.75, -0.35)
            t0 = rng.uniform(-0.3, self.dur * 0.7)
            self.a.append((x0, y0, vx, vy, t0, rng.uniform(0.6, 1.0)))
        self.clip = None

    def open(self, t0):
        super().open(t0)
        self.clip = fx.Clip(stock(self.plate), self.t_in + t0, 1.0, overscan=1.0)

    def close(self):
        super().close()
        if self.clip:
            self.clip.close()

    def base(self, t):
        fr = self.clip.read()
        img = fx.kenburns(fr, t / self.dur, 1.05, 1.12) * 0.75
        layer = np.zeros((fx.H, fx.W), np.float32)
        g = 0.9  # gravity
        for x0, y0, vx, vy, t0, br in self.a:
            tt = t - t0
            if tt < 0 or tt > 1.6:
                continue
            pts = []
            for k in range(6):
                s = max(0.0, tt - k * 0.018)
                x = x0 + vx * s
                y = y0 + vy * s + 0.5 * g * s * s
                pts.append((int(x * fx.W), int(y * fx.H)))
            for k in range(len(pts) - 1):
                cv2.line(layer, pts[k], pts[k + 1], br * (1 - k / 6), max(1, int(2 * fx.S)), cv2.LINE_AA)
            cv2.circle(layer, pts[0], max(1, int(3 * fx.S)), br * 1.5, -1, cv2.LINE_AA)
        glow = cv2.GaussianBlur(layer, (0, 0), 4 * fx.S)
        return img + (layer[..., None] * np.array([1.0, 0.8, 0.5]) + glow[..., None] * np.array([1.0, 0.55, 0.2]) * 1.5)


class WheelSpin(Shot):
    def __init__(self, start, end, plate="s_above_clouds", t_in=0.0, **kw):
        super().__init__(start, end, **kw)
        self.plate, self.t_in = plate, t_in
        self.clip = None

    def open(self, t0):
        super().open(t0)
        self.clip = fx.Clip(stock(self.plate), self.t_in + t0, 1.0, overscan=1.0)

    def close(self):
        super().close()
        if self.clip:
            self.clip.close()

    def base(self, t):
        fr = self.clip.read()
        img = fx.kenburns(fr, t / self.dur, 1.1, 1.2, (0.55, 0.4), (0.55, 0.4))
        w = sprite("wheel")
        u = t / self.dur
        ang = (self.start + t) * (120 + 480 * u)
        acc = np.zeros_like(w)
        for j in range(4):
            acc += rotate_img(w, ang + j * (2 + 10 * u))
        acc /= 4
        a = acc[..., 3]
        rim = cv2.GaussianBlur(np.clip(a - cv2.erode(a, np.ones((15, 15), np.uint8)), 0, 1), (0, 0), 9)
        acc[..., :3] = acc[..., :3] * 0.6 + rim[..., None] * GOLD * (1.2 + 1.5 * u)
        glow = cv2.GaussianBlur(a, (0, 0), 40) * (0.5 + 0.8 * u)
        put(img, np.dstack([np.broadcast_to(GOLD * 1.6, glow.shape + (3,)), np.clip(glow, 0, 1)]), 0.5, 0.48, 1.2, 1, add=True)
        put(img, acc, 0.5, 0.48, 0.95 * (1 + 0.08 * u), 1.0)
        return fx.flare(img, (0.5, 0.48), 0.4 + 0.6 * u)


class TitleCard(Shot):
    """Text card(s) on black with drifting smoke."""

    def __init__(self, start, end, lines, smoke=True, **kw):
        kw.setdefault("grade", None)
        kw.setdefault("bloom", 0.25)
        super().__init__(start, end, **kw)
        self.lines = lines
        if smoke:
            self.overlays.insert(0, StockScreen("o_smoke", 4.0, 0.22, (0.9, 0.7, 0.5)))

    def base(self, t):
        img = np.zeros((fx.H, fx.W, 3), np.float32)
        for cap in self.lines:
            img = cap.apply(img, self.start + t)
        return img


class FinalTitle(Shot):
    def __init__(self, start, end, date_at=2.9, **kw):
        kw.setdefault("grade", None)
        kw.setdefault("bloom", 0.3)
        super().__init__(start, end, **kw)
        self.date_at = date_at
        self.overlays = [StockScreen("o_clouds_black", 12.0, 0.33, (0.75, 0.52, 0.32), 0.6),
                         StockScreen("o_embers_rise", 1.0, 0.8, (1, 1, 1), 1.0),
                         Embers(90, 21, 0.8, "embers")] + list(self.overlays)

    def render(self, t):
        img = super().render(t)
        # text & logo go on top of the atmosphere
        logo = art("logo.png")
        pull = 1.0 + 0.1 * (1 - fx.smooth(t / 1.3)) ** 2
        lg = sweep(logo, (t - 0.25) / 1.4) if t < 2.0 else (sweep(logo, (t - 4.2) / 1.4) if 4.0 < t < 6.0 else logo)
        out_a = fx.env(t, self.dur, 0.0, 1.2)
        fx.place(img, lg, 0.5, 0.49, opacity=out_a, scale=(0.62 * fx.W / logo.shape[1]) * pull, shadow=0.5)
        tt = text_img("THE EPIC TALES OF", "Cardo-Bold.ttf", 50, 0.34, "gold")
        fx.place(img, sweep(tt, (t - 0.6) / 1.6), 0.5, 0.165, opacity=fx.smooth((t - 0.15) / 0.9) * out_a, shadow=0.6)
        if t > self.date_at:
            u = t - self.date_at
            d1 = text_img("20 DECEMBER 2026", "texgyrepagella-bold.otf", 58, 0.2, "gold")
            d2 = text_img("COMING TO THEATRES", "Cardo-Regular.ttf", 30, 0.55, "silver")
            fx.place(img, sweep(d1, u / 1.4 - 0.2), 0.5, 0.80, opacity=fx.smooth(u / 0.5) * out_a,
                     scale=1.0 + 0.06 * (1 - fx.smooth(u / 0.6)), shadow=0.6)
            fx.place(img, d2, 0.5, 0.895, opacity=fx.smooth((u - 0.45) / 0.7) * out_a, shadow=0.5)
        if t < 0.35:
            img = img + (1 - t / 0.35) ** 2 * 1.3
        return img


# ------------------------------------------------------------------ the cut
KR, AR = "श्री कृष्ण", "अर्जुन"


def build_edl():
    E = []
    a = E.append
    # ---------------- SCENE 1 — the beginning of an epic
    a(Black(0.0, 1.3))
    a(StockShot(1.2, 4.9, "s_sunrise_mist", 3.0, 1.0, 1.0, 1.08, (0.5, 0.55), (0.5, 0.5), fin=1.1,
                overlays=[Embers(60, 1, 0.5, "dust")], label="sunrise"))
    a(StockShot(4.5, 8.0, "s_meadow_fog", 5.0, 1.0, 1.04, 1.1, (0.5, 0.5), (0.52, 0.48), exposure=-0.15,
                overlays=[Rays((0.62, 0.05), 0.35, 0.7)], label="meadow"))
    a(StockShot(7.7, 10.9, "s_angkor", 15.0, 1.0, 1.12, 1.03, (0.5, 0.42), (0.5, 0.45), grade="dusk",
                overlays=[Embers(40, 2, 0.4, "dust")], label="temple"))
    a(StockShot(10.9, 12.7, "s_birds_sunset", 2.6, 1.0, 1.35, 1.42, (0.38, 0.5), (0.36, 0.48), grade="gold",
                exposure=-0.25, label="birds"))
    a(StillShot(12.7, 15.6, "army_aerial.png", 1.0, 1.07, (0.5, 0.52), (0.5, 0.5), exposure=-0.1,
                overlays=[Fog(0.18, (1.0, 0.75, 0.5), 3), Embers(70, 4, 0.5, "dust"), Rays((0.53, 0.1), 0.5, 0.66)],
                label="army aerial"))
    a(Black(15.6, 16.9))
    cap1 = Caption("WHEN DHARMA IS CHALLENGED...", 13.1, 16.7, 0.5, 60, "Cardo-Bold.ttf", 0.22, "gold", fin=0.9, fout=0.6)
    E[-2].texts.append(cap1)
    E[-1].texts.append(cap1)
    # ---------------- SCENE 2 — the battlefield
    a(StillShot(16.9, 20.4, "army_low.png", 1.03, 1.12, (0.5, 0.5), (0.52, 0.46), exposure=-0.05, flash_in=0.18,
                overlays=[Fog(0.12, (1.0, 0.78, 0.55), 6), StockScreen("o_dust", 2.0, 0.55), Rays((0.5, 0.33), 0.55, 0.62)],
                label="army low"))
    a(StockShot(20.4, 22.6, "s_horses_run", 7.0, 1.0, 1.05, 1.12, (0.5, 0.5), (0.5, 0.48), grade="warm_hi", exposure=-0.35,
                overlays=[StockScreen("o_dust", 6.0, 0.4)], label="horses"))
    a(StockShot(22.6, 24.4, "s_hoof", 1.2, 0.8, 1.08, 1.14, (0.5, 0.55), (0.48, 0.55), grade="gold", exposure=-0.2,
                blend=True, label="hoof"))
    a(StillShot(24.4, 27.4, "army_mid.png", 1.02, 1.1, (0.48, 0.5), (0.53, 0.48),
                overlays=[Fog(0.14, (1.0, 0.76, 0.52), 8), Embers(80, 5, 0.6, "dust"), Rays((0.5, 0.2), 0.45, 0.66)],
                label="army mid"))
    a(StockShot(27.4, 29.2, "s_storm_field", 0.8, 1.0, 1.06, 1.12, (0.5, 0.45), (0.5, 0.42), grade="storm",
                exposure=-0.25, label="storm field"))
    a(StockShot(29.2, 31.0, "s_storm_fly", 0.3, 1.0, 1.04, 1.1, grade="storm", exposure=0.1, label="lightning"))
    a(StillShot(31.0, 34.9, "army_aerial.png", 1.35, 1.55, (0.42, 0.56), (0.58, 0.52), exposure=-0.05,
                overlays=[Fog(0.16, (1.0, 0.75, 0.5), 9), StockScreen("o_embers_rise", 2.0, 0.5), Rays((0.53, 0.06), 0.4, 0.66)],
                label="army aerial 2"))
    # ---------------- SCENE 3 — Krishna's divine arrival
    a(SeqShot(34.9, 37.2, "crown", 3, 58, 1.0, 1.06, overlays=[Embers(70, 6, 0.6, "gold")], grade="gold", bloom=0.32,
              label="crown"))
    a(StockShot(37.2, 38.8, "s_peacock", 2.6, 0.45, 1.06, 1.12, (0.52, 0.42), (0.5, 0.4), grade="gold", exposure=-0.1,
                label="peacock"))
    a(StockShot(38.8, 40.4, "s_gold_fabric", 0.6, 1.0, 1.05, 1.12, grade="gold", exposure=-0.25, label="fabric"))
    a(ArtShot(40.1, 44.6, "flute", 1.02, 1.14, (0.5, 0.42), (0.5, 0.38), 0.05, moon=True, cloth=True, grade="night",
              exposure=0.05, overlays=[Rays((0.55, 0.22), 0.55, 0.6), Embers(80, 7, 0.7, "embers")], label="krishna reveal"))
    a(ArtShot(44.6, 47.0, "chariot", 1.75, 1.95, (0.27, 0.44), (0.28, 0.42), 0.06, grade="dusk",
              overlays=[Rays((0.3, 0.25), 0.5, 0.62), Embers(50, 8, 0.5, "dust")], label="krishna chariot"))
    a(ArtShot(47.0, 50.0, "chariot", 1.28, 1.0, (0.5, 0.5), (0.5, 0.5), 0.04, grade="dusk",
              overlays=[Rays((0.33, 0.28), 0.5, 0.62), StockScreen("o_embers_rise", 3.0, 0.5)], label="wide reveal"))
    # ---------------- SCENE 4 — Krishna advises Arjuna (dialogue as text)
    a(Black(50.0, 50.3))
    a(ArtShot(50.3, 56.3, "chariot", 1.0, 1.16, (0.5, 0.5), (0.46, 0.46), 0.05, grade="dusk", exposure=-0.05, fin=0.4,
              overlays=[Rays((0.33, 0.28), 0.4, 0.62), Embers(50, 9, 0.5, "dust")],
              texts=[Dialogue(KR, "पार्थ... यह युद्ध केवल राज्य के लिए नहीं है।", 50.9, 55.9)], label="gita 1"))
    a(StockShot(56.3, 61.0, "s_rays_clouds", 1.0, 1.0, 1.04, 1.1, grade="dusk", exposure=-0.1,
                overlays=[Rays((0.5, 0.72), 0.45, 0.62)],
                texts=[Dialogue(KR, "यह धर्म और अधर्म के बीच का संघर्ष है।", 56.7, 60.7)], label="gita 2"))
    a(ArtShot(61.0, 67.4, "chariot", 2.1, 2.45, (0.71, 0.63), (0.7, 0.6), 0.04, grade="dusk",
              overlays=[Embers(40, 10, 0.45, "dust")],
              texts=[Dialogue(AR, "माधव... जिनके सामने मैं खड़ा हूँ, वे मेरे अपने हैं।", 61.4, 64.2),
                     Dialogue(AR, "मैं अपने ही परिवार के विरुद्ध शस्त्र कैसे उठाऊँ?", 64.4, 67.2)], label="arjuna doubt"))
    a(ArtShot(67.4, 71.6, "flute", 1.6, 1.8, (0.48, 0.33), (0.48, 0.3), 0.05, moon=True, grade="night",
              overlays=[Rays((0.55, 0.18), 0.45, 0.6), Embers(50, 11, 0.5, "embers")],
              texts=[Dialogue(KR, "तुम्हारा अधिकार केवल कर्म पर है, फल पर नहीं।", 67.8, 71.4)], label="karma"))
    a(ArtShot(71.6, 75.0, "chariot", 2.0, 2.5, (0.36, 0.36), (0.38, 0.34), 0.05, grade="dusk", flash_out=0.5,
              overlays=[Rays((0.42, 0.3), 0.6, 0.6), Flare((0.44, 0.33), 0.3, pulse=0.2)],
              texts=[Dialogue(KR, "उठो पार्थ... अपने धर्म का पालन करो।", 71.9, 74.5)], label="rise partha"))
    # ---------------- SCENE 5 — Vishwaroop
    a(StockShot(75.0, 78.2, "s_galaxy_flight", 6.0, 1.0, 1.0, 1.1, grade="cosmic", flash_in=0.7, label="galaxy"))
    a(VishwaRise(78.2, 82.8, "s_nebula", 1.0, overlays=[Embers(110, 12, 0.8, "gold")], label="vishwa rise"))
    a(Chakra(82.8, 85.6, "s_spiral", 2.0, dim=0.7, overlays=[StockScreen("o_sparks", 3.0, 0.6)], label="chakra"))
    a(Mandala(85.6, 90.2, "s_nebula_fly", 1.0, dim=0.75, overlays=[Embers(120, 13, 0.8, "gold")], label="mandala"))
    a(StockShot(90.2, 93.0, "s_stars_planets", 8.0, 1.0, 1.0, 1.12, grade="cosmic", label="planets"))
    a(CosmicFace(93.0, 97.0, "s_nebula", 5.0, dim=0.75, overlays=[Embers(110, 14, 0.8, "gold")],
                 texts=[Caption("कालोऽस्मि", 94.2, 96.7, 0.86, 64, "FreeSerifBold.ttf", 0, "gold", "hi", 0.5, 0.5,
                                sweep=True)], label="cosmic face"))
    a(ArjunaAwe(97.0, 100.4, "s_galaxy_flight", 10.2, dim=0.85, overlays=[Embers(80, 15, 0.7, "gold")], label="awe"))
    # ---------------- SCENE 6 — Krishna takes up the wheel
    a(TitleCard(100.4, 102.4, [Caption("HE VOWED NEVER TO RAISE A WEAPON", 100.5, 102.35, 0.5, 46, "Cardo-Bold.ttf", 0.2,
                                       "silver", fin=0.3, fout=0.25)], label="card vow"))
    a(StockShot(102.4, 103.8, "s_storm_fly", 1.5, 1.0, 1.1, 1.18, grade="storm", label="storm 2"))
    a(Arrows(103.8, 105.7, "s_storm_field", 3.0, overlays=[Shake(0.004)], label="arrows"))
    a(StillShot(105.7, 108.4, "wheel_dust.png", 1.0, 1.1, (0.45, 0.6), (0.47, 0.58), exposure=-0.1,
                overlays=[StockScreen("o_dust", 9.0, 0.5), Rays((0.66, 0.2), 0.5, 0.64), Fog(0.12, (1, 0.75, 0.5), 12)],
                label="wheel dust"))
    a(TitleCard(108.4, 111.0, [Caption("BUT WHEN DHARMA WAS IN DANGER...", 108.5, 110.95, 0.5, 46, "Cardo-Bold.ttf", 0.2,
                                       "gold", fin=0.35, fout=0.3)], label="card danger"))
    a(StockShot(111.0, 112.4, "s_horses_run", 14.5, 1.0, 1.1, 1.18, grade="warm_hi", exposure=-0.4, label="horses 2"))
    a(ArtShot(112.4, 113.7, "chariot", 2.0, 2.25, (0.28, 0.4), (0.27, 0.38), 0.05, grade="dusk", exposure=0.05,
              overlays=[Flicker(0.15), StockScreen("o_sparks", 8.0, 0.55)], label="krishna resolve"))
    a(StockShot(113.7, 115.1, "s_hoof", 5.0, 0.8, 1.12, 1.2, grade="gold", exposure=-0.25, blend=True, label="hoof 2"))
    a(StillShot(115.1, 117.8, "krishna_wheel.png", 1.0, 1.1, (0.5, 0.42), (0.5, 0.38), flash_in=0.15,
                overlays=[StockScreen("o_dust", 3.0, 0.45), Rays((0.5, 0.25), 0.6, 0.6), StockScreen("o_embers_rise", 4.0, 0.5)],
                label="wheel raised"))
    a(ArtShot(117.8, 119.1, "flute", 1.9, 2.1, (0.28, 0.82), (0.3, 0.8), 0.05, cloth=True, grade="night", exposure=0.05,
              overlays=[Embers(60, 16, 0.6, "embers")], label="garments"))
    a(WheelSpin(119.1, 121.7, "s_above_clouds", 4.0, grade="gold", overlays=[StockScreen("o_sparks", 12.0, 0.6),
                                                                          Shake(0.003)], label="wheel spin"))
    a(SeqShot(121.7, 123.1, "arjuna_run", 4, 37, 1.0, 1.06, grade="gold", exposure=-0.1,
              overlays=[StockScreen("o_dust", 11.0, 0.5), Embers(60, 17, 0.5, "dust")], label="arjuna runs"))
    a(StillShot(123.1, 125.4, "krishna_wheel.png", 1.45, 1.6, (0.5, 0.4), (0.5, 0.37), flash_out=0.3,
                overlays=[Rays((0.5, 0.2), 0.7, 0.58), StockScreen("o_sparks", 15.0, 0.5)], label="wheel close"))
    # ---------------- SCENE 7 — Arjuna tries to stop Krishna
    a(Black(125.4, 125.6))
    a(ArtShot(125.6, 131.0, "chariot", 2.6, 3.0, (0.69, 0.56), (0.68, 0.54), 0.03, grade="night", exposure=-0.05, fin=0.5,
              overlays=[Embers(40, 18, 0.4, "dust")],
              texts=[Dialogue(AR, "माधव! रुक जाइए!", 126.0, 128.4),
                     Dialogue(AR, "अपनी प्रतिज्ञा मत तोड़िए!", 128.6, 130.8)], label="arjuna plea"))
    a(ArtShot(131.0, 136.0, "flute", 2.2, 2.5, (0.49, 0.26), (0.49, 0.24), 0.04, moon=True, grade="night",
              overlays=[Rays((0.55, 0.16), 0.4, 0.6)],
              texts=[Dialogue(AR, "मैं युद्ध करूँगा...", 131.4, 133.6),
                     Dialogue(AR, "...लेकिन आप अपना शस्त्र मत उठाइए!", 133.8, 135.8)], label="plea 2"))
    a(StillShot(136.0, 140.6, "krishna_wheel.png", 1.25, 1.34, (0.5, 0.45), (0.5, 0.43), fout=1.0, exposure=-0.2,
                overlays=[Rays((0.5, 0.25), 0.45, 0.6), Embers(50, 19, 0.5, "dust")], label="krishna pauses"))
    a(Black(140.6, 141.6))
    # ---------------- SCENE 8 — final reveal
    a(ArtShot(141.6, 146.8, "chariot", 1.0, 1.05, (0.5, 0.5), (0.5, 0.48), 0.03, grade="dusk", exposure=0.05,
              flash_in=0.35, overlays=[Rays((0.33, 0.27), 0.55, 0.6), StockScreen("o_embers_rise", 1.0, 0.65),
                                       Embers(70, 20, 0.6, "dust")], label="final wide"))
    a(TitleCard(146.8, 149.3, [Caption("SUPRIO STUDIO PRESENTS", 147.0, 149.2, 0.5, 38, "Cardo-Regular.ttf", 0.5,
                                       "silver", fin=0.5, fout=0.4, sweep=False)], label="presents"))
    a(FinalTitle(149.3, 158.5, label="title"))
    return E


TOTAL = 158.5
