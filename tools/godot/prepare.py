#!/usr/bin/env python3
"""Puts the downloaded and generated assets into the Godot project's gen/ folder.

    prepare.py --gen godot/gen --assets DOWNLOADS [--sounds DIR] [--music DIR] [--credits DIR ...]

  gen/city/layers.png, layers_n.png   6 x 6 atlases of the city's texture layers, imported as Texture2DArray
  gen/sky/day.png, night.png, sky.json
  gen/sounds/*.ogg, gen/music/*.ogg, gen/fonts/*
  gen/CREDITS.txt
"""
import argparse
import glob
import json
import os
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "unity"))
import prepare as UP  # noqa: E402  (atlas and sky helpers shared with the Unity build)

ARRAY_IMPORT = """[remap]

importer="2d_array_texture"
type="CompressedTexture2DArray"

[deps]

source_file="res://gen/city/{name}"

[params]

compress/mode=2
compress/high_quality=false
compress/lossy_quality=0.7
compress/uastc_level=0
compress/rdo_quality_loss=0.0
compress/hdr_compression=1
compress/channel_pack={pack}
mipmaps/generate=true
mipmaps/limit=-1
slices/horizontal=6
slices/vertical=6
"""

TEX_IMPORT = """[remap]

importer="texture"
type="CompressedTexture2D"

[deps]

source_file="res://{path}"

[params]

compress/mode={mode}
compress/high_quality=false
compress/lossy_quality=0.8
compress/hdr_compression=1
compress/normal_map=0
compress/channel_pack=0
mipmaps/generate={mips}
mipmaps/limit=-1
roughness/mode=0
process/fix_alpha_border=true
process/premult_alpha=false
process/size_limit=0
detect_3d/compress_to=0
"""


def ensure(d):
    os.makedirs(d, exist_ok=True)
    return d


def tex_import(path_in_gen, gen, mode=2, mips=True):
    """Import settings for a picture (2 = VRAM compressed, 0 = lossless)."""
    with open(os.path.join(gen, path_in_gen) + ".import", "w") as f:
        f.write(TEX_IMPORT.format(path="gen/" + path_in_gen, mode=mode, mips="true" if mips else "false"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True)
    ap.add_argument("--assets", required=True)
    ap.add_argument("--sounds", default="")
    ap.add_argument("--music", default="")
    ap.add_argument("--credits", nargs="*", default=[])
    ap.add_argument("--layer-size", type=int, default=1024)
    a = ap.parse_args()
    gen = a.gen
    city = ensure(os.path.join(gen, "city"))
    lay = sorted(f for f in glob.glob(os.path.join(city, "Layers", "*.png")) if not f.endswith("_n.png"))
    nrm = sorted(glob.glob(os.path.join(city, "Layers", "*_n.png")))
    if lay:
        UP.atlas(lay, a.layer_size, os.path.join(city, "layers.png"), "RGBA")
        UP.atlas(nrm, a.layer_size // 2, os.path.join(city, "layers_n.png"), "RGB")
        for name, pack in (("layers.png", 0), ("layers_n.png", 0)):
            with open(os.path.join(city, name + ".import"), "w") as f:
                f.write(ARRAY_IMPORT.format(name=name, pack=pack))
        open(os.path.join(city, "Layers", ".gdignore"), "w").close()       # the single layers are not needed in the game
        print("layers: %d albedo, %d normal" % (len(lay), len(nrm)))
    for f in ("map.png", "lightmap.png"):
        if os.path.exists(os.path.join(city, f)):
            tex_import("city/" + f, gen, mode=0 if f == "map.png" else 2, mips=f != "map.png")

    skyd = ensure(os.path.join(gen, "sky"))
    info = {}
    for name, target in (("day", 0.62), ("night", 0.035)):
        hdr = os.path.join(a.assets, "sky", name + ".hdr")
        if os.path.exists(hdr):
            hz, zen = UP.sky(hdr, os.path.join(skyd, name + ".png"), target)
            info[name] = {"horizon": hz, "zenith": zen}
            tex_import("sky/" + name + ".png", gen, mode=2, mips=False)
    with open(os.path.join(skyd, "sky.json"), "w") as f:
        json.dump(info, f)

    for src, dst in ((a.sounds, "sounds"), (a.music, "music"), (os.path.join(a.assets, "fonts"), "fonts")):
        if src and os.path.isdir(src):
            d = ensure(os.path.join(gen, dst))
            for f in os.listdir(src):
                if f.lower().endswith((".ogg", ".wav", ".mp3", ".ttf", ".otf")):
                    shutil.copy(os.path.join(src, f), os.path.join(d, f))
            print("%s: %d files" % (dst, len(os.listdir(d))))

    parts = ["DANGA - credits", "=" * 40, "",
             "3D models: generated with Hyper3D Rodin (hyper3d.ai) for this game.",
             "Game engine: Godot Engine (godotengine.org), MIT licence.", ""]
    for src in [a.sounds, a.music, os.path.join(a.assets, "fonts")] + list(a.credits):
        if not src or not os.path.isdir(src):
            continue
        for f in sorted(glob.glob(os.path.join(src, "*.md")) + glob.glob(os.path.join(src, "*LICENSE*.txt"))):
            parts.append(open(f, encoding="utf-8", errors="replace").read().strip())
            parts.append("")
    with open(os.path.join(gen, "CREDITS.txt"), "w") as f:
        f.write("\n".join(parts))


if __name__ == "__main__":
    main()
