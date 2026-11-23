"""Renders the HUD images (assets/ui/*.png) from the icon sources in tools/ui_src.

Layout and sizes follow the Evil Nun HUD the developer asked for (white icons with a dark
outline); the icon artwork itself comes from these packs, all made by people (see CREDITS.md):
  noto-emoji/person_standing.svg, person_kneeling.svg - Noto Emoji, Google, SIL OFL 1.1
  game-icons/sbed_hand.svg                           - "Hand" by Sbed, game-icons.net, CC BY 3.0
  kenney/*.svg                                       - Kenney "Mobile Controls", CC0

Needs rsvg-convert. Run:  python3 tools/make_ui.py
"""
import os
import subprocess
import tempfile
import numpy as np
from PIL import Image, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "ui_src")
OUT = os.path.join(HERE, "..", "assets", "ui")
INK = (22, 22, 22)


def render(svg_path, width, height=None):
    """SVG -> RGBA image that fits inside width x height (aspect kept)."""
    height = height or width
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out = tmp.name
    subprocess.check_call(["rsvg-convert", "-w", str(width), "-h", str(height), "-a", svg_path, "-o", out])
    img = Image.open(out).convert("RGBA")
    os.remove(out)
    return img


def without_background(svg_path):
    """game-icons.net SVGs have a black square behind the icon; drop it."""
    text = open(svg_path).read().replace('<path d="M0 0h512v512H0z"/>', "")
    tmp = tempfile.NamedTemporaryFile(suffix=".svg", delete=False, mode="w")
    tmp.write(text)
    tmp.close()
    return tmp.name


def on_canvas(img, w, h):
    c = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    c.alpha_composite(img, ((w - img.width) // 2, (h - img.height) // 2))
    return c


def outlined(img, px, color=INK, alpha=235):
    """Dark outline around a white icon, like the Evil Nun HUD icons."""
    a = img.getchannel("A")
    grown = a.filter(ImageFilter.MaxFilter(px * 2 + 1)).filter(ImageFilter.GaussianBlur(0.7))
    out = Image.new("RGBA", img.size, color + (0,))
    out.putalpha(grown.point(lambda v: v * alpha // 255))
    out.alpha_composite(img)
    return out


def tinted(img, factor, alpha=1.0):
    a = np.asarray(img).astype(np.float64)
    a[..., :3] *= factor
    a[..., 3] *= alpha
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def main():
    os.makedirs(OUT, exist_ok=True)

    # pause (top left): one rounded bar from Kenney's pause icon, used twice with Evil Nun's thin spacing
    bars = render(os.path.join(SRC, "kenney", "icon_pause.svg"), 480)
    bar = bars.crop((0, 0, 200, 480)).resize((46, 200), Image.LANCZOS)
    pause = Image.new("RGBA", (160, 260), (0, 0, 0, 0))
    pause.alpha_composite(bar, (80 - 23 - 49, 30))
    pause.alpha_composite(bar, (80 - 23 + 49, 30))
    outlined(pause, 9).save(os.path.join(OUT, "pause.png"))

    # crouch button (left): standing / crouched figure
    for name, svg in (("stand", "person_standing.svg"), ("crouch", "person_kneeling.svg")):
        fig = render(os.path.join(SRC, "noto-emoji", svg), 240, 270)
        outlined(on_canvas(fig, 220, 300), 8).save(os.path.join(OUT, name + ".png"))

    # use button (right): hand
    hand_svg = without_background(os.path.join(SRC, "game-icons", "sbed_hand.svg"))
    hand = render(hand_svg, 220, 280)
    os.remove(hand_svg)
    outlined(on_canvas(hand, 240, 300), 8).save(os.path.join(OUT, "hand.png"))

    # marker shown on the thing you can use (with its name under it)
    target = render(os.path.join(SRC, "kenney", "icon_target.svg"), 52)
    outlined(on_canvas(target, 64, 64), 4).save(os.path.join(OUT, "marker.png"))

    # joystick: grey pad with a dark rim, white knob with a dark outline
    pad = render(os.path.join(SRC, "kenney", "joystick_circle_pad_d_style_f.svg"), 488)
    outlined(on_canvas(tinted(pad, 0.6, 0.9), 512, 512), 6).save(os.path.join(OUT, "joystick_base.png"))
    knob = render(os.path.join(SRC, "kenney", "joystick_circle_nub_c_style_f.svg"), 240)
    outlined(on_canvas(knob, 256, 256), 6).save(os.path.join(OUT, "joystick_knob.png"))
    grab = render(os.path.join(SRC, "kenney", "joystick_circle_nub_c_style_f.svg"), 38)
    outlined(on_canvas(grab, 48, 48), 2).save(os.path.join(OUT, "slider_grabber.png"))
    print("ui images written to", os.path.normpath(OUT))


if __name__ == "__main__":
    main()
