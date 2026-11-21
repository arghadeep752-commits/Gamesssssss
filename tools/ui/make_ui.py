#!/usr/bin/env python3
"""Draws the game's touch-control icons (joystick ring and knob, pause gear, hand, stand / crouch) and the app
icon (square, adaptive background + foreground, round) with PIL.   python3 tools/ui/make_ui.py UNITY_PROJECT"""
import math
import os
import sys

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FONT_DIR = os.path.join(ROOT, "Assets", "Resources", "Fonts")
SS = 4          # supersampling


def canvas(w, h):
    return Image.new("RGBA", (w * SS, h * SS), (0, 0, 0, 0))


def down(im, w, h):
    return im.resize((w, h), Image.LANCZOS)


def ring(path):
    im = canvas(256, 256)
    d = ImageDraw.Draw(im)
    s = SS
    d.ellipse([10 * s, 10 * s, 246 * s, 246 * s], outline=(255, 255, 255, 235), width=9 * s)
    d.ellipse([30 * s, 30 * s, 226 * s, 226 * s], outline=(255, 255, 255, 70), width=3 * s)
    for k in range(4):           # four small direction ticks
        a = k * math.pi / 2
        cx, cy = 128 + math.cos(a) * 100, 128 + math.sin(a) * 100
        d.ellipse([(cx - 5) * s, (cy - 5) * s, (cx + 5) * s, (cy + 5) * s], fill=(255, 255, 255, 160))
    down(im, 256, 256).save(path)


def knob(path):
    im = canvas(160, 160)
    d = ImageDraw.Draw(im)
    s = SS
    d.ellipse([6 * s, 6 * s, 154 * s, 154 * s], fill=(255, 255, 255, 215))
    d.ellipse([28 * s, 28 * s, 132 * s, 132 * s], outline=(0, 0, 0, 50), width=4 * s)
    down(im, 160, 160).save(path)


def gear(path):
    im = canvas(128, 128)
    d = ImageDraw.Draw(im)
    s = SS
    c = 64
    pts = []
    teeth = 8
    for k in range(teeth * 4):
        a = 2 * math.pi * k / (teeth * 4)
        r = 56 if (k % 4) in (1, 2) else 44
        pts.append(((c + math.cos(a) * r) * s, (c + math.sin(a) * r) * s))
    d.polygon(pts, fill=(255, 255, 255, 255))
    d.ellipse([(c - 18) * s, (c - 18) * s, (c + 18) * s, (c + 18) * s], fill=(0, 0, 0, 0))
    down(im, 128, 128).save(path)


def hand(path):
    """An open hand reaching to grab, white with a dark edge."""
    W, H = 188, 170
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    s = SS

    def rr(x0, y0, x1, y1, r, fill):
        d.rounded_rectangle([x0 * s, y0 * s, x1 * s, y1 * s], radius=r * s, fill=fill)

    def hand_shape(fill, grow=0):
        g = grow
        rr(52 - g, 70 - g, 142 + g, 160 + g, 26 + g, fill)              # palm
        for (x, top) in ((54, 22), (78, 10), (102, 14), (124, 30)):      # fingers
            rr(x - g, top - g, x + 20 + g, 100 + g, 10 + g, fill)
        # thumb: a thick rounded stroke from the side of the palm, slanting up and out
        w = (22 + 2 * g) * s
        p0, p1 = (128 * s, 128 * s), (166 * s, 84 * s)
        d.line([p0, p1], fill=fill, width=int(w))
        for (x, y) in (p0, p1):
            d.ellipse([x - w / 2, y - w / 2, x + w / 2, y + w / 2], fill=fill)

    hand_shape((0, 0, 0, 120), grow=4)
    hand_shape((255, 255, 255, 255))
    down(im, W, H).save(path)


def person(path, crouch):
    W, H = 112, 160
    im = canvas(W, H)
    d = ImageDraw.Draw(im)
    s = SS
    lw = 13 * s
    col = (255, 255, 255, 255)

    def line(p, q):
        d.line([p[0] * s, p[1] * s, q[0] * s, q[1] * s], fill=col, width=lw)
        for x, y in (p, q):
            d.ellipse([x * s - lw / 2, y * s - lw / 2, x * s + lw / 2, y * s + lw / 2], fill=col)
    if not crouch:
        d.ellipse([40 * s, 8 * s, 72 * s, 40 * s], fill=col)
        line((56, 48), (56, 98))
        line((56, 60), (30, 88))
        line((56, 60), (82, 88))
        line((56, 98), (36, 148))
        line((56, 98), (76, 148))
    else:
        d.ellipse([46 * s, 46 * s, 76 * s, 76 * s], fill=col)
        line((56, 82), (44, 116))
        line((52, 92), (82, 110))
        line((44, 116), (74, 124))
        line((74, 124), (70, 150))
        line((44, 116), (30, 150))
    down(im, W, H).save(path)


# ------------------------------------------------------------------------------------------------ app icon
def font(name, size):
    p = os.path.join(FONT_DIR, name)
    return ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default()


def chart_art(size, pad=0.0, with_text=True):
    """Dark terminal, a monitor glow, candles that climb then crash, a red arrow plunging through the frame."""
    S = size * SS
    im = Image.new("RGBA", (S, S), (6, 9, 13, 255))
    d = ImageDraw.Draw(im)
    # vignette background gradient
    for r in range(0, S // 2, max(1, S // 200)):
        a = int(255 * (r / (S / 2)) ** 2 * 0.55)
        d.ellipse([S / 2 - (S / 2 - r) * 1.5, S / 2 - (S / 2 - r) * 1.5, S / 2 + (S / 2 - r) * 1.5, S / 2 + (S / 2 - r) * 1.5],
                  outline=(0, 0, 0, a), width=max(1, S // 200))
    m = pad * S
    inner = S - 2 * m
    # grid
    for k in range(1, 6):
        y = m + inner * (0.12 + 0.13 * k)
        d.line([m + inner * 0.08, y, m + inner * 0.92, y], fill=(30, 52, 60, 255), width=max(1, S // 300))
    # candles
    vals = [0.42, 0.48, 0.45, 0.55, 0.6, 0.57, 0.66, 0.72, 0.69, 0.5, 0.38, 0.24]
    n = len(vals)
    x0, x1 = m + inner * 0.12, m + inner * 0.88
    top, bot = m + inner * 0.18, m + inner * 0.82
    cw = (x1 - x0) / n
    for i in range(1, n):
        o, c = vals[i - 1], vals[i]
        up = c >= o
        col = (30, 235, 125, 255) if up else (250, 45, 60, 255)
        x = x0 + (i + 0.5) * cw
        yo = bot - (bot - top) * o
        yc = bot - (bot - top) * c
        d.line([x, min(yo, yc) - inner * 0.04, x, max(yo, yc) + inner * 0.04], fill=col, width=max(2, int(inner * 0.008)))
        d.rectangle([x - cw * 0.3, min(yo, yc), x + cw * 0.3, max(yo, yc) + 2], fill=col)
    # the crash arrow
    pts = [(x0 + cw * 7.5, top + (bot - top) * 0.2), (x0 + cw * 9.6, top + (bot - top) * 0.62), (x0 + cw * 11.8, top + (bot - top) * 1.02)]
    glow = Image.new("RGBA", im.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.line(pts, fill=(255, 30, 40, 200), width=int(inner * 0.06), joint="curve")
    glow = glow.filter(ImageFilter.GaussianBlur(inner * 0.025))
    im.alpha_composite(glow)
    d = ImageDraw.Draw(im)
    d.line(pts, fill=(255, 60, 70, 255), width=int(inner * 0.035), joint="curve")
    tip = pts[-1]
    ang = math.atan2(pts[-1][1] - pts[-2][1], pts[-1][0] - pts[-2][0])
    L = inner * 0.12
    head = [(tip[0] + math.cos(ang) * L * 0.4, tip[1] + math.sin(ang) * L * 0.4),
            (tip[0] + math.cos(ang + 2.5) * L, tip[1] + math.sin(ang + 2.5) * L),
            (tip[0] + math.cos(ang - 2.5) * L, tip[1] + math.sin(ang - 2.5) * L)]
    d.polygon(head, fill=(255, 60, 70, 255))
    if with_text:
        f = font("BebasNeue-Regular.ttf", int(inner * 0.2))
        txt = "TRADER'S"
        tw = d.textlength(txt, font=f)
        d.text((S / 2 - tw / 2 + inner * 0.012, m + inner * 0.03 + inner * 0.012), txt, font=f, fill=(255, 30, 50, 160))
        d.text((S / 2 - tw / 2, m + inner * 0.03), txt, font=f, fill=(240, 244, 242, 255))
        f2 = font("BebasNeue-Regular.ttf", int(inner * 0.2))
        txt2 = "MADNESS"
        tw2 = d.textlength(txt2, font=f2)
        d.text((S / 2 - tw2 / 2, m + inner * 0.79), txt2, font=f2, fill=(255, 55, 65, 255))
    return im


def app_icons(out):
    os.makedirs(out, exist_ok=True)
    big = chart_art(1024, pad=0.04)
    down(big.convert("RGB"), 1024, 1024).save(os.path.join(out, "tm_icon_1024.png"))
    # adaptive: background = the dark terminal without text, foreground = everything inside the safe circle
    bgim = Image.new("RGBA", (432 * SS, 432 * SS), (6, 9, 13, 255))
    down(bgim, 432, 432).save(os.path.join(out, "tm_icon_bg.png"))
    fg = chart_art(432, pad=0.2)
    # make the foreground's dark backdrop transparent outside a rounded square so the launcher mask shows the bg
    mask = Image.new("L", fg.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([fg.size[0] * 0.17, fg.size[1] * 0.17, fg.size[0] * 0.83, fg.size[1] * 0.83],
                                           radius=fg.size[0] * 0.08, fill=255)
    fg.putalpha(mask)
    down(fg, 432, 432).save(os.path.join(out, "tm_icon_fg.png"))
    r = chart_art(512, pad=0.12)
    m2 = Image.new("L", r.size, 0)
    ImageDraw.Draw(m2).ellipse([0, 0, r.size[0], r.size[1]], fill=255)
    r.putalpha(m2)
    down(r, 512, 512).save(os.path.join(out, "tm_icon_round.png"))


def main():
    proj = sys.argv[1] if len(sys.argv) > 1 else ROOT
    ui = os.path.join(proj, "Assets", "Resources", "UI")
    os.makedirs(ui, exist_ok=True)
    ring(os.path.join(ui, "ring.png"))
    knob(os.path.join(ui, "knob.png"))
    gear(os.path.join(ui, "gear.png"))
    hand(os.path.join(ui, "hand.png"))
    person(os.path.join(ui, "stand.png"), False)
    person(os.path.join(ui, "crouch.png"), True)
    app_icons(os.path.join(proj, "Assets", "Branding"))
    print("ui icons and app icons written")


if __name__ == "__main__":
    main()
