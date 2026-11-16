#!/usr/bin/env python3
"""Granny Dimnight's name on the menu picture and the app icon.

    python3 branding.py <Unity project dir> <fonts cache dir>

* Assets/Texture2D/mainmenu.png (the main menu background; Granny 4 EndGame used DVloper's Granny artwork there)
  becomes a dark picture of the game's own cleaned-up wall with the title GRANNY DIMNIGHT, same size.
* Assets/Dimnight/Branding/icon_1024.png: the app icon (Granny's eye from the game, the title underneath).
Fonts: Creepster (SIL Open Font License, Google Fonts), falling back to DejaVu Sans Bold.
"""
import os
import sys
import urllib.request

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

FONT_URL = "https://raw.githubusercontent.com/google/fonts/main/ofl/creepster/Creepster-Regular.ttf"


def log(*a):
    print("[branding]", *a, flush=True)


def font(cache, size):
    path = os.path.join(cache, "Creepster-Regular.ttf")
    if not os.path.exists(path):
        try:
            os.makedirs(cache, exist_ok=True)
            req = urllib.request.Request(FONT_URL, headers={"User-Agent": "GrannyDimnightBuild/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r, open(path, "wb") as f:
                f.write(r.read())
        except Exception as e:  # noqa: BLE001
            log("font download failed:", e)
    for p in (path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def find(proj, stem):
    for dp, _dn, fn in os.walk(os.path.join(proj, "Assets")):
        for f in fn:
            if os.path.splitext(f)[0] == stem and f.lower().endswith((".png", ".jpg")):
                return os.path.join(dp, f)
    return None


def glow_text(img, xy, text, fnt, fill, glow, radius, anchor="mm"):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).text(xy, text, font=fnt, fill=glow, anchor=anchor)
    img.alpha_composite(layer.filter(ImageFilter.GaussianBlur(radius)))
    ImageDraw.Draw(img).text(xy, text, font=fnt, fill=fill, anchor=anchor)


def menu(proj, cache):
    target = find(proj, "mainmenu")
    if not target:
        log("no mainmenu picture in this export")
        return
    w, h = Image.open(target).size
    wall_path = find(proj, "wall3") or find(proj, "wall2")
    base = Image.new("RGBA", (w, h), (8, 6, 7, 255))
    if wall_path:
        wall = Image.open(wall_path).convert("RGB")
        tiles = Image.new("RGB", (w, h))
        tw, th = wall.size
        for y in range(0, h, th):
            for x in range(0, w, tw):
                tiles.paste(wall, (x, y))
        tiles = ImageOps.autocontrast(tiles.convert("L"), cutoff=1).convert("RGB")
        tiles = Image.blend(Image.new("RGB", (w, h), (0, 0, 0)), tiles, 0.22)
        base = Image.alpha_composite(base, tiles.convert("RGBA"))
    # vignette and a cold light from the top left, like a dim hallway at night
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse((-w * 0.25, -h * 0.6, w * 0.9, h * 1.1), fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(w // 8))
    light = Image.new("RGBA", (w, h), (70, 80, 110, 0))
    light.putalpha(mask.point(lambda v: int(v * 0.35)))
    base = Image.alpha_composite(base, light)
    dark = Image.new("L", (w, h), 0)
    ImageDraw.Draw(dark).ellipse((-w * 0.1, -h * 0.1, w * 1.1, h * 1.1), fill=255)
    dark = ImageOps.invert(dark.filter(ImageFilter.GaussianBlur(w // 10)))
    shade = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    shade.putalpha(dark.point(lambda v: int(v * 0.9)))
    base = Image.alpha_composite(base, shade)
    big, small = font(cache, int(h * 0.19)), font(cache, int(h * 0.14))
    cx = int(w * 0.70)
    glow_text(base, (cx, int(h * 0.20)), "GRANNY", big, (236, 232, 222, 255), (255, 255, 255, 120), 18)
    glow_text(base, (cx, int(h * 0.36)), "DIMNIGHT", small, (186, 18, 22, 255), (255, 40, 40, 160), 22)
    base.convert("RGB").save(target)
    log("menu picture written:", os.path.relpath(target, proj), "%dx%d" % (w, h))


def icon(proj, cache):
    out = os.path.join(proj, "Assets", "Dimnight", "Branding", "icon_1024.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    size = 1024
    img = Image.new("RGBA", (size, size), (0, 0, 0, 255))
    grad = Image.new("L", (size, size), 0)
    ImageDraw.Draw(grad).ellipse((-200, -260, size + 200, size + 120), fill=255)
    grad = grad.filter(ImageFilter.GaussianBlur(160))
    red = Image.new("RGBA", (size, size), (110, 6, 10, 0))
    red.putalpha(grad.point(lambda v: int(v * 0.85)))
    img = Image.alpha_composite(img, red)
    eye_path = find(proj, "Eye")
    if eye_path:
        eye = Image.open(eye_path).convert("RGBA").resize((560, 560), Image.LANCZOS)
        m = Image.new("L", eye.size, 0)
        ImageDraw.Draw(m).ellipse((0, 0, 560, 560), fill=255)
        eye.putalpha(m.filter(ImageFilter.GaussianBlur(6)))
        img.alpha_composite(eye, ((size - 560) // 2, 120))
    glow_text(img, (size // 2, 790), "GRANNY", font(cache, 150), (240, 236, 228, 255), (255, 255, 255, 110), 10)
    glow_text(img, (size // 2, 920), "DIMNIGHT", font(cache, 118), (205, 20, 24, 255), (255, 50, 50, 150), 12)
    img.convert("RGB").save(out)
    log("app icon written:", os.path.relpath(out, proj))


if __name__ == "__main__":
    menu(sys.argv[1], sys.argv[2])
    icon(sys.argv[1], sys.argv[2])
