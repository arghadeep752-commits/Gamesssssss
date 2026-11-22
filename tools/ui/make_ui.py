#!/usr/bin/env python3
"""Builds the game's interface pictures from human-made art (tools/ui/fetch_ui.py): game-icons.net icons
(CC BY 3.0), Kenney's buttons, joystick and panels (CC0) and the dafont fonts. The simple drawings below are
only used for the light glows and as a last resort if a download failed (each one is reported).

    make_ui.py --ui assets/downloaded/ui --out Assets/Resources/UI --branding Assets/Branding --font fonts/DisplayFont.ttf
"""
import argparse
import json
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFilter, ImageFont

S = 4  # supersampling


def canvas(n):
    im = Image.new("RGBA", (n * S, n * S), (0, 0, 0, 0))
    return im, ImageDraw.Draw(im)


def done(im, n, path):
    im.resize((n, n), Image.LANCZOS).save(path)


def P(pts, n):
    return [(x * n * S, y * n * S) for x, y in pts]


def star_pts(cx, cy, r1, r2, k=5, rot=-90):
    pts = []
    for i in range(2 * k):
        a = math.radians(rot + i * 180 / k)
        r = r1 if i % 2 == 0 else r2
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def radial(n, inner, outer, power=1.6, color=(255, 255, 255)):
    im = Image.new("RGBA", (n, n))
    px = im.load()
    c = (n - 1) / 2
    for y in range(n):
        for x in range(n):
            d = math.hypot(x - c, y - c) / c
            t = 0.0 if d >= 1 else (1 - d) ** power
            px[x, y] = color + (int(255 * max(0.0, min(1.0, t * inner + (1 - t) * 0)) * (1 if d < 1 else 0)),)
    return im


def icon(name, n=128):
    im, d = canvas(n)
    W = (255, 255, 255, 255)
    L = n * S
    def poly(pts):
        d.polygon(P(pts, n), fill=W)
    def ell(x0, y0, x1, y1, fill=W):
        d.ellipse(P([(x0, y0), (x1, y1)], n), fill=fill)
    def rect(x0, y0, x1, y1, r=0.0, fill=W):
        d.rounded_rectangle(P([(x0, y0), (x1, y1)], n), radius=r * L, fill=fill)
    def line(pts, w):
        d.line(P(pts, n), fill=W, width=int(w * L), joint="curve")
    clear = (0, 0, 0, 0)
    if name == "fist":
        rect(0.24, 0.30, 0.76, 0.72, 0.1)
        for i in range(4):
            rect(0.24 + i * 0.13, 0.22, 0.24 + i * 0.13 + 0.12, 0.40, 0.05)
        rect(0.16, 0.42, 0.40, 0.58, 0.07)
        rect(0.30, 0.70, 0.70, 0.86, 0.04)
    elif name == "bat":
        poly([(0.20, 0.86), (0.26, 0.90), (0.84, 0.24), (0.74, 0.12)])
        ell(0.70, 0.08, 0.90, 0.28)
        ell(0.14, 0.82, 0.26, 0.94)
    elif name == "knife":
        poly([(0.18, 0.82), (0.30, 0.90), (0.48, 0.70), (0.38, 0.62)])
        poly([(0.40, 0.60), (0.50, 0.70), (0.90, 0.12), (0.78, 0.16), (0.44, 0.54)])
        rect(0.30, 0.56, 0.56, 0.64, 0.02)
    elif name in ("revolver", "pistol"):
        poly([(0.10, 0.30), (0.88, 0.30), (0.88, 0.44), (0.46, 0.44), (0.44, 0.50), (0.34, 0.50), (0.38, 0.86),
              (0.18, 0.86), (0.14, 0.50), (0.10, 0.44)])
        if name == "revolver":
            ell(0.36, 0.26, 0.58, 0.52)
            rect(0.10, 0.34, 0.95, 0.40, 0.02)
        line([(0.34, 0.50), (0.40, 0.62), (0.48, 0.50)], 0.03)
    elif name == "smg":
        poly([(0.06, 0.34), (0.82, 0.34), (0.82, 0.30), (0.96, 0.30), (0.96, 0.44), (0.70, 0.44), (0.62, 0.50), (0.56, 0.86),
              (0.46, 0.86), (0.48, 0.50), (0.36, 0.50), (0.32, 0.72), (0.22, 0.72), (0.24, 0.48), (0.06, 0.48)])
    elif name == "shotgun":
        poly([(0.02, 0.36), (0.98, 0.36), (0.98, 0.44), (0.58, 0.44), (0.58, 0.50), (0.36, 0.50), (0.24, 0.66), (0.08, 0.66),
              (0.20, 0.48), (0.02, 0.46)])
        rect(0.52, 0.44, 0.80, 0.52, 0.02)
    elif name == "jump":
        poly([(0.50, 0.12), (0.84, 0.50), (0.62, 0.50), (0.62, 0.78), (0.38, 0.78), (0.38, 0.50), (0.16, 0.50)])
        rect(0.26, 0.82, 0.74, 0.90, 0.02)
    elif name == "sprint":
        for o in (0.0, 0.28):
            poly([(0.14 + o, 0.20), (0.34 + o, 0.20), (0.62 + o, 0.50), (0.34 + o, 0.80), (0.14 + o, 0.80), (0.42 + o, 0.50)])
    elif name == "car":
        poly([(0.06, 0.62), (0.08, 0.48), (0.24, 0.44), (0.36, 0.28), (0.66, 0.28), (0.80, 0.44), (0.94, 0.48), (0.95, 0.62)])
        d.polygon(P([(0.40, 0.33), (0.50, 0.33), (0.50, 0.44), (0.31, 0.44)], n), fill=clear)
        d.polygon(P([(0.55, 0.33), (0.63, 0.33), (0.72, 0.44), (0.55, 0.44)], n), fill=clear)
        ell(0.16, 0.54, 0.36, 0.74)
        ell(0.64, 0.54, 0.84, 0.74)
        ell(0.21, 0.59, 0.31, 0.69, clear)
        ell(0.69, 0.59, 0.79, 0.69, clear)
    elif name == "exit":
        rect(0.14, 0.16, 0.56, 0.84, 0.04)
        rect(0.20, 0.22, 0.50, 0.78, 0.02, clear)
        poly([(0.40, 0.44), (0.66, 0.44), (0.66, 0.30), (0.90, 0.50), (0.66, 0.70), (0.66, 0.56), (0.40, 0.56)])
    elif name == "phone":
        rect(0.30, 0.08, 0.70, 0.92, 0.08)
        rect(0.34, 0.16, 0.66, 0.78, 0.02, clear)
        ell(0.46, 0.81, 0.54, 0.89, clear)
    elif name == "map":
        ell(0.26, 0.10, 0.74, 0.58)
        poly([(0.30, 0.44), (0.70, 0.44), (0.50, 0.90)])
        ell(0.40, 0.24, 0.60, 0.44, clear)
    elif name == "horn":
        poly([(0.14, 0.40), (0.34, 0.40), (0.78, 0.16), (0.78, 0.84), (0.34, 0.60), (0.14, 0.60)])
        line([(0.84, 0.34), (0.92, 0.30)], 0.04)
        line([(0.86, 0.50), (0.96, 0.50)], 0.04)
        line([(0.84, 0.66), (0.92, 0.70)], 0.04)
    elif name == "camera":
        rect(0.10, 0.30, 0.90, 0.80, 0.08)
        rect(0.34, 0.20, 0.56, 0.32, 0.03)
        ell(0.34, 0.38, 0.66, 0.70, clear)
        ell(0.41, 0.45, 0.59, 0.63)
    elif name == "pause":
        rect(0.26, 0.20, 0.42, 0.80, 0.03)
        rect(0.58, 0.20, 0.74, 0.80, 0.03)
    elif name == "up":
        poly([(0.50, 0.16), (0.88, 0.70), (0.12, 0.70)])
    elif name == "down":
        poly([(0.50, 0.84), (0.88, 0.30), (0.12, 0.30)])
    elif name == "left":
        poly([(0.16, 0.50), (0.70, 0.12), (0.70, 0.88)])
    elif name == "right":
        poly([(0.84, 0.50), (0.30, 0.12), (0.30, 0.88)])
    elif name in ("gas", "brake"):
        rect(0.24 if name == "gas" else 0.14, 0.10, 0.76 if name == "gas" else 0.86, 0.90, 0.10)
        for i in range(5 if name == "gas" else 3):
            y = 0.20 + i * (0.14 if name == "gas" else 0.22)
            rect(0.32 if name == "gas" else 0.24, y, 0.68 if name == "gas" else 0.76, y + 0.06, 0.02, clear)
    elif name == "star":
        poly(star_pts(0.5, 0.53, 0.46, 0.19))
    elif name == "house":
        poly([(0.50, 0.10), (0.92, 0.48), (0.80, 0.48), (0.80, 0.88), (0.20, 0.88), (0.20, 0.48), (0.08, 0.48)])
        rect(0.42, 0.60, 0.58, 0.88, 0.02, clear)
    elif name == "shirt":
        poly([(0.34, 0.12), (0.66, 0.12), (0.92, 0.30), (0.80, 0.48), (0.72, 0.42), (0.72, 0.90), (0.28, 0.90), (0.28, 0.42),
              (0.20, 0.48), (0.08, 0.30)])
        ell(0.40, 0.04, 0.60, 0.22, clear)
    elif name == "cross":
        rect(0.38, 0.12, 0.62, 0.88, 0.04)
        rect(0.12, 0.38, 0.88, 0.62, 0.04)
    elif name == "badge":
        poly([(0.50, 0.08), (0.88, 0.22), (0.82, 0.62), (0.50, 0.92), (0.18, 0.62), (0.12, 0.22)])
        d.polygon(P(star_pts(0.5, 0.48, 0.24, 0.10), n), fill=clear)
    elif name == "heart":
        ell(0.12, 0.16, 0.52, 0.56)
        ell(0.48, 0.16, 0.88, 0.56)
        poly([(0.14, 0.44), (0.86, 0.44), (0.50, 0.88)])
    elif name == "shield":
        poly([(0.50, 0.08), (0.86, 0.20), (0.82, 0.58), (0.50, 0.92), (0.18, 0.58), (0.14, 0.20)])
    elif name == "boat":
        poly([(0.06, 0.56), (0.94, 0.56), (0.78, 0.80), (0.20, 0.80)])
        poly([(0.48, 0.12), (0.48, 0.50), (0.18, 0.50)])
        poly([(0.54, 0.20), (0.80, 0.50), (0.54, 0.50)])
    elif name == "heli":
        rect(0.06, 0.16, 0.94, 0.22, 0.02)
        rect(0.46, 0.20, 0.54, 0.32, 0.01)
        ell(0.22, 0.30, 0.64, 0.66)
        rect(0.58, 0.42, 0.92, 0.50, 0.02)
        rect(0.86, 0.32, 0.92, 0.56, 0.02)
        rect(0.20, 0.74, 0.70, 0.79, 0.02)
        line([(0.32, 0.64), (0.30, 0.75)], 0.03)
        line([(0.56, 0.64), (0.58, 0.75)], 0.03)
    elif name == "settings":
        for i in range(8):
            a = i * math.pi / 4
            cx, cy = 0.5 + 0.34 * math.cos(a), 0.5 + 0.34 * math.sin(a)
            ell(cx - 0.09, cy - 0.09, cx + 0.09, cy + 0.09)
        ell(0.20, 0.20, 0.80, 0.80)
        ell(0.38, 0.38, 0.62, 0.62, clear)
    elif name == "radio":
        rect(0.10, 0.34, 0.90, 0.84, 0.06)
        line([(0.30, 0.34), (0.74, 0.10)], 0.035)
        ell(0.18, 0.44, 0.48, 0.74, clear)
        for i in range(3):
            rect(0.56, 0.46 + i * 0.09, 0.82, 0.50 + i * 0.09, 0.01, clear)
    elif name == "wallet":
        rect(0.10, 0.24, 0.90, 0.84, 0.08)
        rect(0.60, 0.44, 0.96, 0.64, 0.05, clear)
        ell(0.68, 0.50, 0.76, 0.58)
    elif name == "notes":
        rect(0.20, 0.10, 0.80, 0.90, 0.05)
        for i in range(5):
            rect(0.28, 0.22 + i * 0.13, 0.72, 0.27 + i * 0.13, 0.01, clear)
    elif name == "dial":
        for r in range(4):
            for c in range(3):
                cx, cy = 0.26 + c * 0.24, 0.14 + r * 0.24
                ell(cx - 0.08, cy - 0.08, cx + 0.08, cy + 0.08)
    elif name == "save":
        rect(0.14, 0.14, 0.86, 0.86, 0.06)
        rect(0.28, 0.14, 0.72, 0.38, 0.02, clear)
        rect(0.28, 0.54, 0.72, 0.86, 0.02, clear)
    elif name == "sleep":
        ell(0.14, 0.14, 0.78, 0.78)
        ell(0.32, 0.06, 0.92, 0.66, clear)
    elif name == "target":
        ell(0.10, 0.10, 0.90, 0.90)
        ell(0.18, 0.18, 0.82, 0.82, clear)
        rect(0.47, 0.02, 0.53, 0.34, 0.0)
        rect(0.47, 0.66, 0.53, 0.98, 0.0)
        rect(0.02, 0.47, 0.34, 0.53, 0.0)
        rect(0.66, 0.47, 0.98, 0.53, 0.0)
        ell(0.44, 0.44, 0.56, 0.56)
    elif name == "reload":
        d.arc(P([(0.16, 0.16), (0.84, 0.84)], n), 40, 330, fill=W, width=int(0.10 * L))
        poly([(0.62, 0.02), (0.92, 0.24), (0.60, 0.36)])
    else:
        raise ValueError(name)
    done(im, n, None) if False else None
    return im.resize((n, n), Image.LANCZOS)


def rupee(n=128):
    """The Indian rupee sign (from DejaVu Sans Bold when the system has it, else drawn)."""
    im, d = canvas(n)
    L = n * S
    for path in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"):
        if os.path.exists(path):
            f = ImageFont.truetype(path, int(L * 0.9))
            bb = d.textbbox((0, 0), "\u20b9", font=f)
            d.text(((L - (bb[2] - bb[0])) / 2 - bb[0], (L - (bb[3] - bb[1])) / 2 - bb[1]), "\u20b9", font=f, fill=(255, 255, 255, 255))
            return im.resize((n, n), Image.LANCZOS)
    w = int(0.1 * L)
    d.line((0.22 * L, 0.16 * L, 0.80 * L, 0.16 * L), fill="white", width=w)
    d.line((0.22 * L, 0.36 * L, 0.80 * L, 0.36 * L), fill="white", width=w)
    d.arc((0.0 * L, 0.16 * L, 0.62 * L, 0.56 * L), 270, 90, fill="white", width=w)
    d.line((0.22 * L, 0.56 * L, 0.70 * L, 0.92 * L), fill="white", width=w)
    return im.resize((n, n), Image.LANCZOS)


def round_button(n=256):
    im, d = canvas(n)
    L = n * S
    d.ellipse((0, 0, L - 1, L - 1), fill=(30, 30, 30, 230))                  # dark rim
    d.ellipse((L * 0.05, L * 0.05, L * 0.95, L * 0.95), fill=(255, 255, 255, 255))
    out = im.resize((n, n), Image.LANCZOS)
    # top highlight / bottom shade so the tinted button looks domed (like the Indian Bike Driving 3D buttons)
    px = out.load()
    for y in range(n):
        k = 1.06 - 0.32 * (y / n)
        for x in range(n):
            r, g, b, a = px[x, y]
            if r > 60:
                v = max(0, min(255, int(r * k)))
                px[x, y] = (v, v, v, a)
    return out


def panel(n=128, r=0.22, border=0.035):
    im, d = canvas(n)
    L = n * S
    d.rounded_rectangle((0, 0, L - 1, L - 1), radius=r * L, fill=(20, 20, 20, 235))
    d.rounded_rectangle((border * L, border * L, L - 1 - border * L, L - 1 - border * L), radius=(r - border) * L, fill=(255, 255, 255, 255))
    return im.resize((n, n), Image.LANCZOS)


def ring(n=256, w=0.07, north=False):
    im, d = canvas(n)
    L = n * S
    d.ellipse((0, 0, L - 1, L - 1), fill=(25, 25, 25, 255))
    d.ellipse((w * L, w * L, L - 1 - w * L, L - 1 - w * L), fill=(0, 0, 0, 0))
    if north:
        d.ellipse((0.40 * L, -0.02 * L, 0.60 * L, 0.18 * L), fill=(230, 60, 40, 255))
    return im.resize((n, n), Image.LANCZOS)


def solid_circle(n=256):
    im, d = canvas(n)
    d.ellipse((0, 0, n * S - 1, n * S - 1), fill=(255, 255, 255, 255))
    return im.resize((n, n), Image.LANCZOS)


def arrow(n=128):
    im, d = canvas(n)
    d.polygon(P([(0.5, 0.06), (0.86, 0.90), (0.5, 0.70), (0.14, 0.90)], n), fill=(20, 20, 20, 255))
    d.polygon(P([(0.5, 0.16), (0.78, 0.82), (0.5, 0.64), (0.22, 0.82)], n), fill=(255, 255, 255, 255))
    return im.resize((n, n), Image.LANCZOS)


def title(font_path, text, out, h=320):
    try:
        f = ImageFont.truetype(font_path, int(h * 0.82))
    except Exception:  # noqa: BLE001
        f = ImageFont.load_default()
    bb = f.getbbox(text)
    w = bb[2] - bb[0] + 80
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    m = Image.new("L", (w, h), 0)
    ImageDraw.Draw(m).text((40 - bb[0], (h - (bb[3] - bb[1])) // 2 - bb[1]), text, font=f, fill=255)
    out_m = m.filter(ImageFilter.MaxFilter(15))
    shadow = out_m.filter(ImageFilter.GaussianBlur(10))
    im.paste((0, 0, 0, 170), (8, 12), shadow)
    im.paste((15, 10, 10, 255), (0, 0), out_m)
    grad = Image.new("RGBA", (w, h))
    gp = grad.load()
    for y in range(h):
        t = y / h
        c = (255, int(214 - 120 * t), int(40 - 30 * t), 255)        # saffron to deep orange, like a hot sunset
        for x in range(w):
            gp[x, y] = c
    im.paste(grad, (0, 0), m)
    im.save(out)


def app_icons(font_path, out_dir):
    n = 1024
    bg = Image.new("RGBA", (n, n))
    px = bg.load()
    for y in range(n):
        for x in range(n):
            t = (x + y) / (2 * n)
            px[x, y] = (int(250 - 90 * t), int(120 - 80 * t), int(30 + 20 * t), 255)
    fg = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    try:
        f = ImageFont.truetype(font_path, 560)
    except Exception:  # noqa: BLE001
        f = ImageFont.load_default()
    m = Image.new("L", (n, n), 0)
    dm = ImageDraw.Draw(m)
    bb = f.getbbox("D")
    dm.text(((n - (bb[2] - bb[0])) // 2 - bb[0], (n - (bb[3] - bb[1])) // 2 - bb[1]), "D", font=f, fill=255)
    fg.paste((20, 12, 10, 255), (0, 0), m.filter(ImageFilter.MaxFilter(25)))
    fg.paste((255, 236, 200, 255), (0, 0), m)
    # crosshair ring around the letter
    d = ImageDraw.Draw(fg)
    d.ellipse((150, 150, n - 150, n - 150), outline=(255, 255, 255, 220), width=26)
    for a in range(4):
        ang = a * math.pi / 2
        cx, cy = n / 2 + 360 * math.cos(ang), n / 2 + 360 * math.sin(ang)
        d.line((cx - 40 * math.cos(ang), cy - 40 * math.sin(ang), cx + 70 * math.cos(ang), cy + 70 * math.sin(ang)), fill=(255, 255, 255, 220), width=26)
    full = bg.copy()
    full.alpha_composite(fg)
    full.save(os.path.join(out_dir, "dg_icon_1024.png"))
    bg.save(os.path.join(out_dir, "dg_icon_bg.png"))
    small = fg.resize((int(n * 0.66), int(n * 0.66)), Image.LANCZOS)
    fg2 = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    fg2.alpha_composite(small, ((n - small.size[0]) // 2, (n - small.size[1]) // 2))
    fg2.save(os.path.join(out_dir, "dg_icon_fg.png"))
    mask = Image.new("L", (n, n), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, n - 1, n - 1), fill=255)
    rnd = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    rnd.paste(full, (0, 0), mask)
    rnd.save(os.path.join(out_dir, "dg_icon_round.png"))


ICONS = ["fist", "bat", "knife", "revolver", "pistol", "smg", "shotgun", "jump", "sprint", "car", "exit", "phone", "map", "horn",
         "camera", "pause", "up", "down", "left", "right", "gas", "brake", "star", "house", "shirt", "cross", "badge", "heart",
         "shield", "boat", "heli", "settings", "radio", "wallet", "notes", "dial", "save", "sleep", "target", "reload"]


# game-icons.net names for each button, best first (checked against ui_candidates.jpg from the CI release)
ICON_NAMES = {
    "fist": ["fist", "punch", "high-punch"], "bat": ["baseball-bat", "spiked-bat"], "knife": ["switchblade", "bowie-knife", "butterfly-knife", "knife-thrust"],
    "revolver": ["revolver"], "pistol": ["pistol-gun", "colt-m1911", "luger", "glock"], "smg": ["uzi", "mp5", "thompson-m1928", "machine-gun"],
    "shotgun": ["sawed-off-shotgun", "shotgun"], "jump": ["jump-across", "upgrade"], "sprint": ["sprint", "run"],
    "car": ["city-car", "race-car", "sedan"], "exit": ["exit-door", "entry-door"], "phone": ["smartphone"], "map": ["treasure-map", "position-marker"],
    "horn": ["megaphone", "bugle-call"], "camera": ["photo-camera"], "pause": ["pause-button"], "gas": ["speedometer", "gas-pump"],
    "brake": ["stop-sign", "brake"], "star": ["round-star", "flat-star", "star-formation"], "house": ["house", "family-house"],
    "shirt": ["shirt", "t-shirt"], "cross": ["hospital-cross", "health-normal", "first-aid-kit"], "badge": ["police-badge", "sheriff"],
    "heart": ["hearts", "heart-plus"], "shield": ["kevlar-vest", "bulletproof-vest", "shield"], "boat": ["speedboat", "speedboat-propeller"],
    "heli": ["helicopter"], "settings": ["cog", "gears"], "radio": ["boombox", "radio-tower", "radar-sweep"], "wallet": ["wallet", "cash", "money-stack"],
    "notes": ["notebook", "scroll-unfurled"], "dial": ["rotary-phone", "phone"], "save": ["save", "floppy-disk"], "sleep": ["night-sleep", "sleepy", "moon"],
    "target": ["crosshair", "targeting", "reticule"], "reload": ["anticlockwise-rotation", "cycle", "clockwise-rotation"],
    "up": ["plain-arrow"], "down": ["plain-arrow"], "left": ["plain-arrow"], "right": ["plain-arrow"],
}
# 'plain-arrow' points up and to the right; turn it so each arrow points its way
ARROW_TURN = {"up": 45, "right": -45, "down": -135, "left": 135}
KEYWORDS = {"fist": ["fist", "punch"], "bat": ["baseball"], "knife": ["knife", "dagger"], "pistol": ["pistol"], "smg": ["uzi", "submachine", "machine-gun"],
            "shotgun": ["shotgun"], "car": ["car"], "heli": ["helicopter"], "boat": ["boat"], "house": ["house"], "star": ["star"]}
report = []


def svg_icon(icons, slot, n=128):
    names = icons.get("icons", {})
    pick = next((x for x in ICON_NAMES.get(slot, []) if x in names), None)
    if pick is None:
        for w in KEYWORDS.get(slot, []):
            pick = next((x for x in sorted(names) if w in x), None)
            if pick:
                break
    if pick is None:
        return None, None
    ic = names[pick]
    W, H = ic.get("width", icons.get("width", 512)), ic.get("height", icons.get("height", 512))
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">%s</svg>' % (W, H, n, n, ic["body"].replace("currentColor", "#ffffff"))
    try:
        png = subprocess.run(["rsvg-convert", "-w", str(n), "-h", str(n)], input=svg.encode(), capture_output=True, check=True).stdout
    except Exception as e:  # noqa: BLE001
        report.append("%s: rsvg failed (%s)" % (slot, e))
        return None, None
    im = Image.open(__import__("io").BytesIO(png)).convert("RGBA")
    if slot in ARROW_TURN and pick == "plain-arrow":
        im = im.rotate(ARROW_TURN[slot], resample=Image.BICUBIC)
    return im, pick


def kenney_files(ui):
    root = os.path.join(ui, "kenney")
    out = []
    for dp, _, fs in os.walk(root):
        for f in fs:
            if f.lower().endswith(".png"):
                out.append(os.path.join(dp, f))
    return out


def best(files, need, any_of=(), avoid=(), prefer=(), square=False):
    """The Kenney picture whose path has every word of 'need' (and one of 'any_of'), preferring light, tintable styles."""
    scored = []
    for f in files:
        low = f.lower().replace("\\", "/")
        if not all(w in low for w in need) or (any_of and not any(w in low for w in any_of)) or any(w in low for w in avoid):
            continue
        try:
            w, h = Image.open(f).size
        except Exception:  # noqa: BLE001
            continue
        if square and abs(w - h) > 0.15 * max(w, h):
            continue
        score = sum(10 for p in prefer if p in low) + min(w, h) / 100.0
        scored.append((score, f))
    scored.sort(reverse=True)
    return scored[0][1] if scored else None


def nine_square(path, n=128):
    """Makes a 9-slice square from a Kenney panel or long button, keeping its rounded corners."""
    im = Image.open(path).convert("RGBA")
    w, h = im.size
    k = n / min(w, h)
    im = im.resize((max(n, int(w * k + 0.5)), max(n, int(h * k + 0.5))), Image.LANCZOS)
    w, h = im.size
    half = n // 2
    out = Image.new("RGBA", (n, n))
    out.paste(im.crop((0, 0, half, half)), (0, 0))
    out.paste(im.crop((w - half, 0, w, half)), (half, 0))
    out.paste(im.crop((0, h - half, half, h)), (0, half))
    out.paste(im.crop((w - half, h - half, w, h)), (half, half))
    return out


def whiten(im):
    """Kenney's light-grey art turned into white, keeping its shading, so the game can tint it."""
    px = im.load()
    w, h = im.size
    mx = 1
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a > 40:
                mx = max(mx, r, g, b)
    k = 255.0 / mx
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            v = int(min(255, (0.3 * r + 0.59 * g + 0.11 * b) * k))
            px[x, y] = (v, v, v, a)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--branding", required=True)
    ap.add_argument("--font", default="")
    ap.add_argument("--ui", default="", help="downloaded interface art (tools/ui/fetch_ui.py)")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    os.makedirs(a.branding, exist_ok=True)
    icons = {}
    jp = os.path.join(a.ui, "game-icons.json") if a.ui else ""
    if jp and os.path.exists(jp):
        icons = json.load(open(jp))
    used = {}
    for name in ICONS:
        im, pick = svg_icon(icons, name) if icons else (None, None)
        if im is None:
            im = icon(name)
            report.append("%s: FALLBACK drawing (no game-icons match)" % name)
        else:
            used[name] = pick
        im.save(os.path.join(a.out, "i_" + name + ".png"))
    rupee().save(os.path.join(a.out, "i_rupee.png"))
    files = kenney_files(a.ui) if a.ui else []
    light = ("light", "white", "grey", "gray")
    btn = best(files, ["button"], ("circle", "round"), ("dark", "pressed", "outline", "line", "transparent", "_a.", "_b.", "_x.", "_y."), light, True)
    if btn:
        whiten(Image.open(btn).convert("RGBA").resize((256, 256), Image.LANCZOS)).save(os.path.join(a.out, "btn_round.png"))
        used["btn_round"] = os.path.relpath(btn, a.ui)
    else:
        round_button().save(os.path.join(a.out, "btn_round.png"))
        report.append("btn_round: FALLBACK drawing")
    pan = best(files, ["panel"], (), ("dark", "transparent", "inset", "border"), light)
    if pan:
        whiten(nine_square(pan)).save(os.path.join(a.out, "panel.png"))
        used["panel"] = os.path.relpath(pan, a.ui)
    else:
        panel().save(os.path.join(a.out, "panel.png"))
        report.append("panel: FALLBACK drawing")
    pil = best(files, ["button"], ("rectangle", "long", "rect"), ("dark", "pressed", "transparent", "outline"), light)
    if pil:
        whiten(nine_square(pil)).save(os.path.join(a.out, "pill.png"))
        used["pill"] = os.path.relpath(pil, a.ui)
    else:
        panel(128, 0.5, 0.06).save(os.path.join(a.out, "pill.png"))
        report.append("pill: FALLBACK drawing")
    pad = best(files, ["joystick"], (), ("dark", "nub", "knob", "button"), light + ("pad", "base", "circle"), True)
    nub = best(files, [], ("nub", "knob", "thumb", "stick_button"), ("dark",), light, True)
    if pad:
        Image.open(pad).convert("RGBA").resize((256, 256), Image.LANCZOS).save(os.path.join(a.out, "ring.png"))
        used["ring"] = os.path.relpath(pad, a.ui)
    else:
        ring().save(os.path.join(a.out, "ring.png"))
        report.append("ring: FALLBACK drawing")
    if nub:
        Image.open(nub).convert("RGBA").resize((256, 256), Image.LANCZOS).save(os.path.join(a.out, "circle.png"))
        used["circle"] = os.path.relpath(nub, a.ui)
    else:
        solid_circle().save(os.path.join(a.out, "circle.png"))
        report.append("circle: FALLBACK drawing")
    os.makedirs("build", exist_ok=True)
    json.dump({"used": used, "report": report}, open(os.path.join("build", "ui_used.json"), "w"), indent=1)
    print("ui art used:", json.dumps(used, indent=1))
    for r in report:
        print("ui:", r)
    ring(256, 0.05, True).save(os.path.join(a.out, "minimap_ring.png"))
    solid_circle().save(os.path.join(a.out, "mask_circle.png"))
    arrow().save(os.path.join(a.out, "arrow.png"))
    radial(128, 1.0, 0.0, 2.2).save(os.path.join(a.out, "glow.png"))
    radial(128, 1.0, 0.0, 0.9, (0, 0, 0)).save(os.path.join(a.out, "blob.png"))
    title(a.font, "DANGA", os.path.join(a.out, "title.png"))
    app_icons(a.font, a.branding)
    print("ui: %d icons" % len(ICONS))


if __name__ == "__main__":
    main()
