#!/usr/bin/env python3
"""Generates Hime's launcher icons, notification icon, splash mark and call
tones. Run from the repository root:  python3 tool/dev/make_assets.py

Outputs:
  android_overlay/app/src/main/res/...   launcher, adaptive, notification icons
  assets/images/hime_mark.png             in-app logo mark
  assets/sounds/ringback.wav, busy.wav    outgoing-call tones (Indian cadence)
"""
import math
import struct
import wave
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
FONT = ROOT / "assets" / "fonts" / "Poppins-Bold.ttf"
YELLOW = (245, 213, 71, 255)   # #F5D547
INK = (32, 33, 36, 255)        # #202124
RES = ROOT / "android_overlay" / "app" / "src" / "main" / "res"
DENSITIES = {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}


def glyph(size: int, ink=INK, hole=(0, 0, 0, 0)) -> Image.Image:
    """The Hime mark: a speech bubble with an 'h' cut out and a spark."""
    s = size * 4  # supersample
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    u = s / 1000.0
    # Bubble body and tail.
    d.rounded_rectangle([170 * u, 200 * u, 830 * u, 760 * u], radius=230 * u, fill=ink)
    d.polygon([(250 * u, 690 * u), (190 * u, 885 * u), (430 * u, 745 * u)], fill=ink)
    # Spark (four-point star) at the top right.
    cx, cy, r, w = 845 * u, 175 * u, 120 * u, 30 * u
    d.polygon([(cx, cy - r), (cx + w, cy - w), (cx + r, cy), (cx + w, cy + w),
               (cx, cy + r), (cx - w, cy + w), (cx - r, cy), (cx - w, cy - w)], fill=ink)
    # 'h' cut out of the bubble.
    font = ImageFont.truetype(str(FONT), int(520 * u))
    box = d.textbbox((0, 0), "h", font=font)
    tw, th = box[2] - box[0], box[3] - box[1]
    tx = 500 * u - tw / 2 - box[0]
    ty = 480 * u - th / 2 - box[1]
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).text((tx, ty), "h", font=font, fill=255)
    hole_layer = Image.new("RGBA", (s, s), hole)
    img.paste(hole_layer, (0, 0), mask)
    return img.resize((size, size), Image.LANCZOS)


def save(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)


def launcher(size: int, round_icon: bool) -> Image.Image:
    s = size * 4
    base = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(base)
    if round_icon:
        d.ellipse([0, 0, s - 1, s - 1], fill=YELLOW)
    else:
        d.rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=YELLOW)
    base = base.resize((size, size), Image.LANCZOS)
    g = glyph(int(size * (0.62 if round_icon else 0.70)), hole=YELLOW)
    off = (size - g.width) // 2
    base.alpha_composite(g, (off, off))
    return base


def adaptive_foreground(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    g = glyph(int(size * 0.56), hole=YELLOW)
    off = (size - g.width) // 2
    img.alpha_composite(g, (off, off))
    return img


def notification_icon(size: int) -> Image.Image:
    return glyph(size, ink=(255, 255, 255, 255), hole=(0, 0, 0, 0))


def make_icons() -> None:
    for name, scale in DENSITIES.items():
        save(launcher(int(48 * scale), False), RES / f"mipmap-{name}" / "ic_launcher.png")
        save(launcher(int(48 * scale), True), RES / f"mipmap-{name}" / "ic_launcher_round.png")
        save(adaptive_foreground(int(108 * scale)), RES / f"drawable-{name}" / "ic_launcher_foreground.png")
        save(notification_icon(int(24 * scale)), RES / f"drawable-{name}" / "ic_stat_hime.png")
        save(glyph(int(96 * scale), hole=YELLOW), RES / f"drawable-{name}" / "launch_mark.png")
    adaptive = (
        '<?xml version="1.0" encoding="utf-8"?>\n'
        '<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">\n'
        '    <background android:drawable="@color/ic_launcher_background"/>\n'
        '    <foreground android:drawable="@drawable/ic_launcher_foreground"/>\n'
        '    <monochrome android:drawable="@drawable/ic_launcher_foreground"/>\n'
        '</adaptive-icon>\n'
    )
    for n in ("ic_launcher.xml", "ic_launcher_round.xml"):
        p = RES / "mipmap-anydpi-v26" / n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(adaptive)
    images = ROOT / "assets" / "images"
    save(glyph(512, hole=YELLOW), images / "hime_mark.png")
    save(launcher(512, False), images / "hime_icon.png")


def tone(path: Path, segments, rate=16000) -> None:
    """segments: list of (seconds, on) using 400 Hz modulated by 25 Hz."""
    frames = bytearray()
    t0 = 0.0
    for seconds, on in segments:
        n = int(seconds * rate)
        for i in range(n):
            t = t0 + i / rate
            v = 0.0
            if on:
                v = math.sin(2 * math.pi * 400 * t) * (0.6 + 0.4 * math.sin(2 * math.pi * 25 * t)) * 0.35
                edge = min(i, n - i) / (0.01 * rate)
                v *= min(1.0, edge)
            frames += struct.pack("<h", int(v * 32767))
        t0 += seconds
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(bytes(frames))


def make_tones() -> None:
    sounds = ROOT / "assets" / "sounds"
    tone(sounds / "ringback.wav", [(0.4, True), (0.2, False), (0.4, True), (2.0, False)])
    tone(sounds / "busy.wav", [(0.75, True), (0.75, False)])


if __name__ == "__main__":
    make_icons()
    make_tones()
    print("done")
