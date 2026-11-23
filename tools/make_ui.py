"""Makes the HUD images in assets/ui from the developer's own pictures (tools/ui_src/developer):
  interact.png       - the hand + USE button
  joystick_knob.png  - the joystick knob
  joystick_base.png  - a plain grey, see-through circle behind the knob
Run:  python3 tools/make_ui.py
"""
import os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "ui_src", "developer")
OUT = os.path.join(HERE, "..", "assets", "ui")


def trimmed(path, pad=6):
    img = Image.open(path).convert("RGBA")
    x0, y0, x1, y1 = img.getchannel("A").point(lambda v: 255 if v > 8 else 0).getbbox()
    return img.crop((max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad)))


def fit(img, height):
    return img.resize((round(img.width * height / img.height), height), Image.LANCZOS)


def main():
    os.makedirs(OUT, exist_ok=True)
    fit(trimmed(os.path.join(SRC, "interact_use.png")), 420).save(os.path.join(OUT, "interact.png"))
    knob = trimmed(os.path.join(SRC, "joystick_knob.png"), pad=4)
    knob.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "joystick_knob.png"))

    # grey see-through circle, drawn 4x bigger and scaled down for smooth edges
    big = 2048
    base = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    d.ellipse([16, 16, big - 16, big - 16], fill=(120, 120, 120, 105), outline=(90, 90, 90, 150), width=28)
    base.resize((512, 512), Image.LANCZOS).save(os.path.join(OUT, "joystick_base.png"))
    print("ui images written to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
