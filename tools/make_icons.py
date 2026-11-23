"""App icon (launcher icons) made from the developer's own door and wallpaper photos.
Run:  python3 tools/make_icons.py
"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source_images")
OUT = os.path.join(HERE, "..", "assets", "icons")


def dark_wallpaper(size):
    wall = Image.open(os.path.join(SRC, "wall.jpg")).convert("RGB")
    wall = wall.resize((size, int(size * wall.height / wall.width)), Image.LANCZOS).crop((0, 0, size, size))
    a = np.asarray(wall).astype(np.float64) * 0.33
    # vignette
    yy, xx = np.mgrid[0:size, 0:size] / (size - 1) - 0.5
    v = np.clip(1.15 - np.sqrt(xx ** 2 + yy ** 2) * 1.5, 0.25, 1.0)[..., None]
    return Image.fromarray(np.clip(a * v, 0, 255).astype(np.uint8)).convert("RGBA")


def door(height):
    d = Image.open(os.path.join(SRC, "door.jpg")).convert("RGB")
    d = d.resize((int(height * d.width / d.height), height), Image.LANCZOS)
    d = Image.fromarray(np.clip(np.asarray(d).astype(np.float64) * 1.15, 0, 255).astype(np.uint8))
    return d.convert("RGBA")


def with_door(bg, door_h, shadow=True):
    out = bg.copy()
    d = door(door_h)
    x = (out.width - d.width) // 2
    y = (out.height - d.height) // 2
    if shadow:
        sh = Image.new("RGBA", out.size, (0, 0, 0, 0))
        ImageDraw.Draw(sh).rectangle([x + 4, y + 6, x + d.width + 4, y + d.height + 6], fill=(0, 0, 0, 170))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(out.width / 60)))
    out.alpha_composite(d, (x, y))
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    full = with_door(dark_wallpaper(512), 400)
    mask = Image.new("L", (512, 512), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, 511, 511], radius=96, fill=255)
    rounded = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    rounded.paste(full, (0, 0), mask)
    rounded.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "icon.png"))
    rounded.resize((192, 192), Image.LANCZOS).save(os.path.join(OUT, "icon_192.png"))
    # adaptive icon: Android crops to a circle/squircle, keep the door inside the middle 66%
    dark_wallpaper(432).save(os.path.join(OUT, "icon_background_432.png"))
    fg = Image.new("RGBA", (432, 432), (0, 0, 0, 0))
    fg = with_door(fg, 250)
    fg.save(os.path.join(OUT, "icon_foreground_432.png"))
    print("icons written")


if __name__ == "__main__":
    main()
