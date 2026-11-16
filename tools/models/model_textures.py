#!/usr/bin/env python3
"""
Granny Dimnight: textures for the new models - real CC0 photo-scanned surfaces (Poly Haven, ambientCG) for each
material slot in materials.json, plus the pictures drawn here (the paintings, the padlock code note, the TV screen).

usage: model_textures.py <Unity project dir> <models dir with materials.json> <cache dir> <credits.md>
writes <Unity>/Assets/Dimnight/Textures/<slot>/diff.jpg (+ nor.jpg) and <Unity>/Assets/Dimnight/Textures/<name>.png
"""
import json
import math
import os
import random
import shutil
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "unity"))
import real_textures as rt  # noqa: E402

S = rt.SLOTS
NEW = {
    "plaster": S["plaster"],
    "wallpaper": S["fabric_wall"],
    "wood_planks": S["wood_planks"],
    "wood_floor": S["wood_floor"],
    "tiles": S["tiles_wall"],
    "tiles_floor": S["marble_floor"],
    "concrete": S["concrete_floor"],
    "stone": S["stone_wall"],
    "grass": S["grass"],
    "brick": dict(ids=["red_brick_03", "red_brick", "brick_wall_001", "brick_wall_02"], must=["brick"],
                  prefer=["red", "wall", "clean"], avoid=["painted", "white", "floor", "pavement", "tile"], acg=["Bricks", "Brick"]),
    "dirt": dict(ids=["brown_mud_02", "forest_ground_04", "dirt_floor"], must=["dirt", "ground", "soil", "mud"],
                 prefer=["dirt", "soil", "ground", "brown"], avoid=["leaves", "rock", "snow", "road", "asphalt"], acg=["Ground", "Dirt"]),
    "roof": dict(ids=["clay_roof_tiles_02", "roof_tiles_14", "roof_09"], must=["roof", "shingle"],
                 prefer=["tiles", "clay", "red", "terracotta"], avoid=["metal", "corrugated", "thatch"], acg=["Roofing tiles", "Roof"]),
    "wood_painted": dict(ids=["painted_wood_planks", "wood_painted_white", "painted_wood"], must=["paint", "painted"],
                         prefer=["wood", "white", "plank", "smooth"], avoid=["metal", "brick", "plaster", "concrete", "peel"],
                         acg=["Painted wood", "PaintedWood"]),
    "wood_light": dict(ids=["oak_veneer_01", "wood_table_001", "fine_grained_wood"], must=["wood"],
                       prefer=["oak", "light", "veneer", "table", "grain"], avoid=["floor", "planks", "bark", "painted", "dark", "plywood"],
                       acg=["Wood veneer oak", "Wood"]),
    "wood_dark": dict(ids=["dark_wood", "walnut_veneer", "wood_table_worn"], must=["wood"],
                      prefer=["dark", "walnut", "veneer", "polished", "mahogany"], avoid=["floor", "planks", "bark", "painted", "plywood"],
                      acg=["Wood veneer walnut", "Wood"]),
    "fabric": dict(ids=["fabric_leather_01", "denim_fabric_02", "jute_fabric"], must=["fabric", "cloth", "textile"],
                   prefer=["upholstery", "woven", "linen", "fabric", "sofa"], avoid=["leather", "pattern", "floral", "carpet", "denim"],
                   acg=["Fabric", "Upholstery"]),
    "linen": dict(ids=["white_linen", "cotton_fabric", "linen_fabric"], must=["linen", "cotton", "fabric", "cloth"],
                  prefer=["linen", "white", "cotton", "bed"], avoid=["leather", "pattern", "denim", "carpet"], acg=["Fabric linen", "Fabric"]),
    "knit": dict(ids=["knitted_fabric", "wool_fabric"], must=["knit", "wool", "fabric"], prefer=["knit", "wool", "blanket"],
                 avoid=["leather", "denim"], acg=["Knitted fabric", "Fabric"]),
    "rug": dict(ids=["carpet_01", "persian_rug"], must=["rug", "carpet"], prefer=["rug", "carpet", "woven"],
                avoid=["tile", "grass"], acg=["Carpet", "Rug"]),
    "leather": dict(ids=["brown_leather", "leather_red_02", "fabric_leather_02"], must=["leather"],
                    prefer=["brown", "leather", "smooth"], avoid=[], acg=["Leather"]),
    "wicker": dict(ids=["wicker_weave", "rattan_weave"], must=["wicker", "rattan", "woven", "basket", "weave"],
                   prefer=["wicker", "rattan", "weave"], avoid=["metal"], acg=["Wicker", "Rattan"]),
    "cardboard": dict(ids=["cardboard", "corrugated_cardboard"], must=["cardboard", "paper"], prefer=["cardboard", "brown"],
                      avoid=["wall"], acg=["Cardboard"]),
    "metal": dict(ids=["metal_plate", "brushed_metal", "metal_grate_rusty"], must=["metal", "steel", "aluminium"],
                  prefer=["brushed", "steel", "clean", "plate", "smooth"], avoid=["corrugated", "painted", "grate", "diamond"],
                  acg=["Metal brushed", "Metal"]),
    "nylon": dict(ids=["canvas_fabric", "nylon_fabric"], must=["fabric", "nylon", "canvas", "cloth"],
                  prefer=["canvas", "nylon", "smooth", "tent"], avoid=["leather", "pattern", "carpet"], acg=["Fabric canvas", "Fabric"]),
    "bark": dict(ids=["bark_willow", "pine_bark", "bark_brown_02"], must=["bark"], prefer=["bark", "tree", "oak", "pine"],
                 avoid=[], acg=["Bark"]),
}


def fetch_1k(slot, assets, used, cache):
    folder = os.path.join(cache, slot)
    info = os.path.join(folder, "source.json")
    if os.path.exists(info) and os.path.exists(os.path.join(folder, "diff.jpg")):
        with open(info) as f:
            src = json.load(f)
        used.add(src[1])
        return src, folder
    spec = NEW[slot]
    os.makedirs(folder, exist_ok=True)
    src = None
    for aid in rt.ph_rank(spec, assets, used) if assets else []:
        try:
            maps = rt.ph_maps(aid, "1k")
            if not maps["diff"]:
                continue
            for k, u in maps.items():
                if u:
                    with open(os.path.join(folder, k + ".jpg"), "wb") as f:
                        f.write(rt.http(u))
            src = ("Poly Haven", aid, "https://polyhaven.com/a/" + aid)
            break
        except Exception as e:  # noqa: BLE001
            rt.log("  Poly Haven failed", aid, e)
    if src is None:
        src, data = rt.acg_get(spec["acg"], used, "1k")
        if not src:
            return None, None
        for k, b in data.items():
            with open(os.path.join(folder, k + ".jpg"), "wb") as f:
                f.write(b)
    with open(info, "w") as f:
        json.dump(src, f)
    used.add(src[1])
    return src, folder


# ---------------------------------------------------------------------------------------------- drawn pictures
def painting(seed, w=512, h=400):
    """Simple naive landscapes and still lifes, drawn from shapes (original pictures for the frames)."""
    r = random.Random(seed)
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    kind = seed % 4
    if kind in (0, 2):
        sky = [(120, 150, 190), (200, 150, 120), (90, 110, 150), (150, 170, 190)][seed % 4]
        for y in range(h):
            t = y / h
            d.line([(0, y), (w, y)], fill=tuple(int(c * (1 - 0.3 * t) + 40 * t) for c in sky))
        if kind == 0:
            d.ellipse([w * 0.7, h * 0.12, w * 0.85, h * 0.31], fill=(250, 230, 180))
        for k in range(3):
            col = [(70, 100, 70), (90, 120, 80), (60, 80, 60)][k]
            base = h * (0.55 + 0.12 * k)
            pts = [(0, h)]
            for x in range(0, w + 32, 32):
                pts.append((x, base - 40 * math.sin(x / w * math.pi * (1 + k) + seed) - r.uniform(0, 20)))
            pts.append((w, h))
            d.polygon(pts, fill=col)
        if kind == 2:
            hx = w * 0.3
            d.rectangle([hx, h * 0.55, hx + 70, h * 0.72], fill=(210, 200, 180))
            d.polygon([(hx - 10, h * 0.55), (hx + 35, h * 0.45), (hx + 80, h * 0.55)], fill=(150, 70, 60))
            d.rectangle([hx + 28, h * 0.63, hx + 42, h * 0.72], fill=(90, 60, 40))
    else:
        bg = [(70, 60, 50), (60, 70, 80)][kind == 3]
        d.rectangle([0, 0, w, h], fill=bg)
        d.rectangle([0, h * 0.7, w, h], fill=(120, 90, 60))
        d.ellipse([w * 0.3, h * 0.35, w * 0.7, h * 0.8], fill=(200, 200, 190))
        for k in range(5):
            cx = w * 0.35 + k * w * 0.075
            d.ellipse([cx - 20, h * 0.3 - (k % 2) * 20, cx + 20, h * 0.42 - (k % 2) * 20],
                      fill=[(200, 60, 50), (220, 160, 60), (190, 80, 120), (230, 200, 90), (150, 50, 60)][k])
        d.ellipse([w * 0.18, h * 0.6, w * 0.3, h * 0.72], fill=(180, 50, 40))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def code_note():
    im = Image.new("RGB", (512, 384), (238, 232, 214))
    d = ImageDraw.Draw(im)
    for y in range(40, 384, 34):
        d.line([(20, y), (492, y)], fill=(170, 190, 215), width=2)
    d.line([(70, 0), (70, 384)], fill=(220, 120, 120), width=2)
    code = "4 8 1 5"
    # big hand-written-ish digits made of strokes
    x = 110
    segs = {"0": "abcdef", "1": "bc", "2": "abged", "3": "abgcd", "4": "fgbc", "5": "afgcd", "6": "afgedc", "7": "abc",
            "8": "abcdefg", "9": "abcdfg"}
    for ch in code.replace(" ", ""):
        X, Y, W, H = x, 120, 60, 130
        P = {"a": [(X, Y), (X + W, Y)], "b": [(X + W, Y), (X + W, Y + H / 2)], "c": [(X + W, Y + H / 2), (X + W, Y + H)],
             "d": [(X, Y + H), (X + W, Y + H)], "e": [(X, Y + H / 2), (X, Y + H)], "f": [(X, Y), (X, Y + H / 2)],
             "g": [(X, Y + H / 2), (X + W, Y + H / 2)]}
        for s in segs[ch]:
            d.line(P[s], fill=(30, 40, 90), width=9)
        x += 95
    return im


def tv_screen():
    im = Image.new("RGB", (256, 192))
    r = random.Random(7)
    for y in range(192):
        for x in range(256):
            v = 40 + r.randint(0, 60)
            im.putpixel((x, y), (v, v + 6, v))
    return im.filter(ImageFilter.GaussianBlur(0.6))


def main():
    proj, models, cache, credits = sys.argv[1:5]
    mats = json.load(open(os.path.join(models, "materials.json")))
    out_root = os.path.join(proj, "Assets", "Dimnight", "Textures")
    os.makedirs(out_root, exist_ok=True)
    slots = sorted({m["slot"] for m in mats.values() if m.get("slot") and not m["slot"].startswith("@")})
    try:
        assets = rt.jget(rt.PH + "assets?t=textures")
    except Exception as e:  # noqa: BLE001
        rt.log("Poly Haven list failed:", e)
        assets = {}
    used, lines = set(), []
    for slot in slots:
        if slot not in NEW:
            rt.log("  no source for slot", slot)
            continue
        src, folder = fetch_1k(slot, assets, used, cache)
        if not src:
            rt.log("  %-12s NOTHING FOUND (plain colour)" % slot)
            continue
        dst = os.path.join(out_root, slot)
        os.makedirs(dst, exist_ok=True)
        for k in ("diff", "nor"):
            p = os.path.join(folder, k + ".jpg")
            if os.path.exists(p):
                img = Image.open(p).convert("RGB")
                if max(img.size) > 1024:
                    img = img.resize((1024, 1024), Image.LANCZOS)
                img.save(os.path.join(dst, k + ".jpg"), quality=90)
        lines.append("- %s: %s `%s`, CC0, %s" % (slot, src[0], src[1], src[2]))
        rt.log("  %-12s <- %s %s" % (slot, src[0], src[1]))
    for i in range(1, 5):
        painting(i * 37 + i).save(os.path.join(out_root, "painting_%d.png" % i))
    code_note().save(os.path.join(out_root, "code_note.png"))
    tv_screen().save(os.path.join(out_root, "tv_screen.png"))
    os.makedirs(os.path.dirname(os.path.abspath(credits)), exist_ok=True)
    with open(credits, "w", encoding="utf-8") as f:
        f.write("# Textures of the new models\n\nPhoto-scanned surfaces, all CC0 (public domain):\n\n" + "\n".join(lines) +
                "\n\nThe paintings, the code note and the TV picture are drawn by the build script.\n")
    rt.log("model textures: %d slots" % len(lines))


if __name__ == "__main__":
    main()
