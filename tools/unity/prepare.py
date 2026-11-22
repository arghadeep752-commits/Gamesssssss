#!/usr/bin/env python3
"""Puts everything the Unity project loads at run time into Assets/Resources (after tools/city/build.py and
tools/unity/convert_models.py have run):

    prepare.py --project . --assets ci-assets/assets/downloaded [--credits ci-assets/build/CREDITS_AUTO.md]

  Assets/Resources/Gen/City/   chunks, extras, colliders, water (.bytes), layers.png + layers_n.png (texture-array
                               flipbooks, 6 x 6), map.png, lightmap.png
  Assets/Resources/Gen/Sky/    day.png, night.png (Poly Haven HDRIs, tone-mapped), sky.json (horizon colours)
  Assets/Resources/Sounds/     recorded sound effects (.ogg)
  Assets/Resources/Music/      the radio and menu music (.ogg)
  Assets/Resources/Fonts/      DisplayFont.ttf, UIFont.ttf (dafont)
  Assets/Resources/credits.txt every source and licence
"""
import argparse
import glob
import json
import os
import shutil

import numpy as np
from PIL import Image

GRID = 6


def ensure(d):
    os.makedirs(d, exist_ok=True)
    return d


def read_hdr(path):
    """Radiance .hdr (32-bit_rle_rgbe) -> float32 array [h, w, 3]."""
    data = open(path, "rb").read()
    pos = 0
    while True:
        end = data.index(b"\n", pos)
        line = data[pos:end].decode("ascii", "replace")
        pos = end + 1
        if line.startswith("-Y") or line.startswith("+Y"):
            parts = line.split()
            h, w = int(parts[1]), int(parts[3])
            break
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        if data[pos] == 2 and data[pos + 1] == 2 and (data[pos + 2] << 8 | data[pos + 3]) == w:
            pos += 4
            for c in range(4):
                x = 0
                while x < w:
                    n = data[pos]
                    pos += 1
                    if n > 128:
                        n -= 128
                        img[y, x:x + n, c] = data[pos]
                        pos += 1
                    else:
                        img[y, x:x + n, c] = np.frombuffer(data, np.uint8, n, pos)
                        pos += n
                    x += n
        else:
            img[y] = np.frombuffer(data, np.uint8, w * 4, pos).reshape(w, 4)
            pos += w * 4
    e = img[..., 3].astype(np.int32)
    scale = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0)
    return img[..., :3].astype(np.float32) * scale[..., None]


def filmic(c):
    A, B, C, D, E, F, W = 0.22 * 4.0, 0.30 * 2.0, 0.10, 0.20, 0.01, 0.30, 1.0
    t = ((c * (A * c + C * B) + D * E) / (c * (A * c + B) + D * F)) - E / F
    w = ((W * (A * W + C * B) + D * E) / (W * (A * W + B) + D * F)) - E / F
    return t / w


def to_srgb(x):
    x = np.clip(x, 0, None)
    return np.clip(np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055), 0, 1)


def sky(hdr, out_png, target):
    rgb = read_hdr(hdr)
    h = rgb.shape[0]
    lum = rgb[: h // 2].mean(axis=2)
    exp = target / max(1e-4, float(np.percentile(lum, 55)))
    out = to_srgb(filmic(rgb * exp))
    img = Image.fromarray((out * 255 + 0.5).astype(np.uint8), "RGB")
    if img.size[0] > 2048:
        img = img.resize((2048, 1024), Image.LANCZOS)
    img.save(out_png)
    band = out[int(h * 0.44): int(h * 0.5)].reshape(-1, 3).mean(0)
    zen = out[: int(h * 0.1)].reshape(-1, 3).mean(0)
    return [round(float(v), 3) for v in band], [round(float(v), 3) for v in zen]


def atlas(files, cell, out_png, mode):
    im = Image.new(mode, (GRID * cell, GRID * cell), (128, 128, 255, 255) if mode == "RGBA" else (128, 128, 255))
    for i, f in enumerate(files):
        t = Image.open(f).convert(mode)
        if t.size != (cell, cell):
            t = t.resize((cell, cell), Image.LANCZOS)
        im.paste(t, ((i % GRID) * cell, (i // GRID) * cell))     # first slice = top-left cell, row by row
    im.save(out_png, optimize=False, compress_level=3)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", default=".")
    ap.add_argument("--assets", required=True)
    ap.add_argument("--credits", default="")
    ap.add_argument("--layer-size", type=int, default=1024)
    a = ap.parse_args()
    P = a.project
    res = os.path.join(P, "Assets", "Resources")
    city_src = os.path.join(P, "Assets", "Game", "City")
    city = ensure(os.path.join(res, "Gen", "City"))
    for f in ("chunks.bytes", "extras.bytes", "colliders.bytes", "water.bytes", "map.png", "lightmap.png"):
        src = os.path.join(city_src, f)
        if os.path.exists(src):
            shutil.move(src, os.path.join(city, f))
    lay = sorted(f for f in glob.glob(os.path.join(city_src, "Layers", "*.png")) if not f.endswith("_n.png"))
    nrm = sorted(glob.glob(os.path.join(city_src, "Layers", "*_n.png")))
    assert len(lay) <= GRID * GRID, len(lay)
    if lay:
        atlas(lay, a.layer_size, os.path.join(city, "layers.png"), "RGBA")
        atlas(nrm, a.layer_size // 2, os.path.join(city, "layers_n.png"), "RGB")
        print("layers: %d albedo, %d normal" % (len(lay), len(nrm)))
    shutil.rmtree(city_src, ignore_errors=True)

    skyd = ensure(os.path.join(res, "Gen", "Sky"))
    info = {}
    for name, target in (("day", 0.62), ("night", 0.035)):
        hdr = os.path.join(a.assets, "sky", name + ".hdr")
        if os.path.exists(hdr):
            hz, zen = sky(hdr, os.path.join(skyd, name + ".png"), target)
            info[name] = {"horizon": hz, "zenith": zen}
            print("sky %s: horizon %s zenith %s" % (name, hz, zen))
    json.dump(info, open(os.path.join(skyd, "sky.json"), "w"))

    credits = ["DANGA - made by MXYAN GAMES", "", "3D models: Hyper3D Rodin. City of Agartala: built by tools/city (Blender / Python).", ""]
    for kind, sub, exts in (("Sounds", "sounds", (".ogg",)), ("Music", "music", (".ogg",)), ("Fonts", "fonts", (".ttf", ".otf")), ("UI", "ui", ())):
        src = os.path.join(a.assets, sub)
        dst = ensure(os.path.join(res, kind))
        n = 0
        for f in sorted(glob.glob(os.path.join(src, "*"))):
            if f.lower().endswith(exts):
                shutil.copy(f, os.path.join(dst, os.path.basename(f)))
                n += 1
            elif f.lower().endswith((".md", ".txt")) and not os.path.basename(f).startswith("ui_"):
                credits += [open(f, encoding="utf-8", errors="replace").read(), ""]
        print("%s: %d files" % (kind, n))
    if a.credits and os.path.exists(a.credits):
        credits += [open(a.credits, encoding="utf-8", errors="replace").read()]
    txt = "\n".join(credits).replace("**", "").replace("`", "")
    open(os.path.join(res, "credits.txt"), "w", encoding="utf-8").write(txt)


if __name__ == "__main__":
    main()
