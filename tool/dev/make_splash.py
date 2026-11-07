#!/usr/bin/env python3
"""Generates Hime's WhatsApp-style launch screen assets: the centred app logo
and the "from ARGHADEEP DAS" signature at the bottom, in light and dark.
Run from the repository root:  python3 tool/dev/make_splash.py

Outputs:
  android_overlay/app/src/main/res/drawable-*/splash_icon.png        Android 12+ splash icon (288dp canvas)
  android_overlay/app/src/main/res/drawable-*/splash_logo.png        logo for the pre-Android 12 launch screen
  android_overlay/app/src/main/res/drawable(-night)-*/splash_branding.png   200x80dp signature
  assets/images/splash_branding_light.png / _dark.png                 the same signature for the Flutter splash
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
from make_assets import DENSITIES, RES, ROOT, launcher, save  # noqa: E402

FONTS = ROOT / "assets" / "fonts"
LOGO_DP = 96          # logo size on screen (dp)
ICON_CANVAS_DP = 288  # Android 12 splash icon canvas without icon background
BRAND_W_DP, BRAND_H_DP = 200, 80

THEMES = {
    # name: (from colour, gradient start, gradient end)
    "light": ((138, 141, 145, 255), (214, 170, 0, 255), (168, 124, 0, 255)),
    "dark": ((154, 156, 161, 255), (245, 213, 71, 255), (226, 188, 31, 255)),
}


def splash_icon(scale: float) -> Image.Image:
    size = round(ICON_CANVAS_DP * scale)
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    logo = launcher(round(LOGO_DP * scale), False)
    off = (size - logo.width) // 2
    img.alpha_composite(logo, (off, off))
    return img


def spaced_text(draw_size, text, font, spacing):
    """Returns (mask, width, height) of text drawn with letter spacing."""
    tmp = ImageDraw.Draw(Image.new("L", (1, 1)))
    widths = [tmp.textlength(ch, font=font) for ch in text]
    total = sum(widths) + spacing * (len(text) - 1)
    asc, desc = font.getmetrics()
    w, h = int(total + 4), asc + desc
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    x = 0.0
    for ch, cw in zip(text, widths):
        d.text((x, 0), ch, font=font, fill=255)
        x += cw + spacing
    bbox = mask.getbbox()
    return mask.crop(bbox), bbox


def branding(theme: str, scale: float) -> Image.Image:
    """'from' over 'ARGHADEEP DAS', drawn at 4x then scaled down."""
    ss = 4.0  # supersampling factor relative to the target density
    k = scale * ss
    W, H = round(BRAND_W_DP * k), round(BRAND_H_DP * k)
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    from_col, g0, g1 = THEMES[theme]

    small = ImageFont.truetype(str(FONTS / "Poppins-Medium.ttf"), round(13 * k))
    big = ImageFont.truetype(str(FONTS / "Poppins-Bold.ttf"), round(16 * k))

    name_mask, _ = spaced_text(None, "ARGHADEEP DAS", big, 2.2 * k)
    from_mask, _ = spaced_text(None, "from", small, 0.4 * k)

    gap = round(5 * k)
    bottom_pad = round(8 * k)
    name_y = H - bottom_pad - name_mask.height
    from_y = name_y - gap - from_mask.height

    # 'from' in grey.
    grey = Image.new("RGBA", from_mask.size, from_col)
    img.paste(grey, ((W - from_mask.width) // 2, from_y), from_mask)

    # Name with a left-to-right gradient.
    nw, nh = name_mask.size
    grad = Image.new("RGBA", (nw, nh))
    gd = ImageDraw.Draw(grad)
    for x in range(nw):
        t = x / max(1, nw - 1)
        c = tuple(round(g0[i] + (g1[i] - g0[i]) * t) for i in range(4))
        gd.line([(x, 0), (x, nh)], fill=c)
    img.paste(grad, ((W - nw) // 2, name_y), name_mask)

    return img.resize((round(BRAND_W_DP * scale), round(BRAND_H_DP * scale)), Image.LANCZOS)


def main() -> None:
    for name, scale in DENSITIES.items():
        save(splash_icon(scale), RES / f"drawable-{name}" / "splash_icon.png")
        save(launcher(round(LOGO_DP * scale), False), RES / f"drawable-{name}" / "splash_logo.png")
        save(branding("light", scale), RES / f"drawable-{name}" / "splash_branding.png")
        save(branding("dark", scale), RES / f"drawable-night-{name}" / "splash_branding.png")
        old = RES / f"drawable-{name}" / "launch_mark.png"
        if old.exists():
            old.unlink()
    images = ROOT / "assets" / "images"
    save(branding("light", 4), images / "splash_branding_light.png")
    save(branding("dark", 4), images / "splash_branding_dark.png")
    print("splash assets written")


if __name__ == "__main__":
    main()
