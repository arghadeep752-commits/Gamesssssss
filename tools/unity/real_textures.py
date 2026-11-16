#!/usr/bin/env python3
"""Granny Dimnight: gives the house real, photographed surfaces (nothing AI-made, nothing drawn).

    python3 real_textures.py <Unity project dir> <cache dir> <credits.md>

Walls, floors, stairs, tiles, wood panels, the garage floor, stones and grass of Granny 4 EndGame are replaced by
photo-scanned CC0 textures from Poly Haven (polyhaven.com) and ambientCG (ambientcg.com). Each replacement:
  * keeps the original file name and .meta (so every material keeps using it, the 3D models stay the same),
  * is tinted to the average colour of the texture it replaces (every room keeps its colour scheme),
  * is clean: worn, dirty, peeling, rusty or broken surfaces are avoided,
  * is cropped to the original's shape and resized to its size; matching normal maps replace the "_N" maps.
Furniture, props, items and characters keep their own textures (they are painted onto the models' UV layouts).
"""
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile

from PIL import Image, ImageStat

UA = "GrannyDimnightBuild/1.0 (MXYAN GAMES; GitHub Actions; github.com/arghadeep752-commits/Gamesssssss)"
PH = "https://api.polyhaven.com/"
CLEAN_AVOID = ["dirty", "damaged", "broken", "peel", "rust", "worn", "old", "grunge", "mold", "moss", "stain",
               "crack", "rotten", "burnt", "graffiti", "weathered"]

# kinds of real surface: Poly Haven ids tried first, then a keyword search over Poly Haven, then ambientCG queries
SLOTS = {
    "plaster": dict(ids=["painted_plaster_wall", "beige_wall_001", "beige_wall_002", "white_plaster_02"],
                    must=["plaster", "paint", "stucco", "wall"], prefer=["painted", "smooth", "white", "beige", "interior"],
                    avoid=["brick", "tile", "wood", "metal", "stone", "rock", "concrete"], acg=["PaintedPlaster", "Plaster"]),
    "fabric_wall": dict(ids=["fabric_pattern_07", "fabric_pattern_05", "floral_fabric"],
                        must=["fabric", "pattern", "damask", "floral"], prefer=["pattern", "floral", "fabric", "damask"],
                        avoid=["leather", "denim", "carpet", "rug", "knit"], acg=["Fabric pattern", "Fabric"]),
    "wood_floor": dict(ids=["wood_floor", "laminate_floor_02", "wood_floor_deck", "plank_flooring_02", "herringbone_parquet"],
                       must=["floor", "parquet", "laminate", "plank"], prefer=["wood", "floor", "parquet", "polished", "clean"],
                       avoid=["tile", "concrete", "stone", "carpet", "painted"], acg=["WoodFloor", "Wood floor"]),
    "wood_planks": dict(ids=["wooden_planks", "brown_planks_03", "plank_flooring", "wood_planks"],
                        must=["plank", "board", "wood"], prefer=["planks", "wall", "clean", "new", "pine"],
                        avoid=["floor", "parquet", "painted", "bark", "log"], acg=["Planks", "Wood planks"]),
    "wood_fine": dict(ids=["dark_wood", "wood_table_001", "oak_veneer_01", "wood_cabinet_worn_long"],
                      must=["wood"], prefer=["veneer", "table", "grain", "polished", "oak", "walnut"],
                      avoid=["floor", "planks", "bark", "painted", "plywood"], acg=["Wood", "Wood veneer"]),
    "tiles_wall": dict(ids=["white_tiles", "tiles_white_01", "floor_tiles_06", "ceramic_tiles"],
                       must=["tile"], prefer=["white", "ceramic", "bathroom", "square", "glossy", "clean"],
                       avoid=["roof", "terracotta", "wood", "hex", "stone"], acg=["Tiles white", "Tiles"]),
    "marble_floor": dict(ids=["marble_tiles", "marble_01", "marble_floor_tiles"],
                         must=["marble"], prefer=["white", "tiles", "floor", "polished"], avoid=["black", "green"],
                         acg=["Marble tiles", "Marble"]),
    "concrete_floor": dict(ids=["concrete_floor_02", "smooth_concrete", "concrete_floor_painted", "polished_concrete"],
                           must=["concrete", "cement", "floor"], prefer=["smooth", "floor", "polished", "clean", "grey"],
                           avoid=["wall", "brick", "tile", "wood"], acg=["Concrete floor", "Concrete"]),
    "stone_wall": dict(ids=["stone_wall", "castle_wall_slates", "stacked_stone_wall", "rock_wall_08"],
                       must=["stone", "rock", "slate"], prefer=["wall", "stone", "masonry", "clean"],
                       avoid=["brick", "floor", "cobble", "path"], acg=["Stone wall", "Rock"]),
    "grass": dict(ids=["grass_path_3", "aerial_grass_rock", "grass_medium_01", "lawn"],
                  must=["grass", "lawn"], prefer=["lawn", "green", "short", "grass"],
                  avoid=["dry", "dead", "rock", "path", "forest", "leaves", "snow"], acg=["Grass", "Lawn"]),
    "rock": dict(ids=["rock_ground", "rocks_ground_02", "rock_face", "boulder"],
                 must=["rock", "stone", "boulder"], prefer=["rock", "grey", "boulder"], avoid=["brick", "tile", "path"],
                 acg=["Rock"]),
}

# original texture (file name without extension) -> kind of real surface. "_N" partners get the matching normal map.
PLAN = {
    # wallpapers and painted walls
    "wall3": "plaster", "wall6": "plaster", "wall7": "plaster", "wall9": "plaster", "F2244": "plaster",
    "SRN16222-5": "plaster", "wall": "plaster", "wall8": "plaster", "underwall2": "plaster",
    "wall2": "fabric_wall", "royal-purple-pattern-stockcake": "fabric_wall",
    # wood walls and panels
    "wall10": "wood_planks", "secret_room": "wood_planks", "outside_roomwall": "wood_planks",
    "outsidewall": "wood_planks", "storage_roomwall": "wood_planks", "outside_wallroom.ong": "wood_planks",
    "nor_wall_woodenWall01_Alb": "wood_planks", "walltext": "wood_fine", "the-rich-dark-grain-of-polished-rosewood": "wood_fine",
    # floors and stairs
    "floor": "wood_floor", "floor_new": "wood_floor", "floor_new 1": "wood_floor", "stair_wood": "wood_floor",
    "stair_block": "wood_floor", "WoodFinedark": "wood_floor", "WoodFineLight": "wood_floor",
    "WoodPlanksClean0039_1_M": "wood_floor", "wood_text": "wood_floor",
    "bathroom_floor1": "marble_floor", "Bathroom_wall": "tiles_wall", "garage_floor": "concrete_floor",
    # outside and the basement
    "underwall": "stone_wall", "Rocks": "rock",
    "07c2b8bcad9fb6a6efb8d3c62e5f3080": "grass", "07c2b8bcad9fb6a6efb8d3c62e5f3080 1": "grass",
}
NORMALS = {"wall3_N": "wall3", "wall6_N": "wall6", "wall7_N": "wall7", "wall9_N": "wall9", "wall_N": "wall",
           "wall2_N": "wall2", "wall8_N": "wall8", "SRN16222-5_N": "SRN16222-5", "Bathroom_wall_N": "Bathroom_wall",
           "outsidewall_N": "outsidewall", "secret_room_N": "secret_room", "floor_new_N": "floor_new",
           "royal-purple-pattern-stockcake_N": "royal-purple-pattern-stockcake"}


def log(*a):
    print("[textures]", *a, flush=True)


def http(url, tries=3, timeout=60):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep((10.0 if "429" in str(e) else 2.0) * (k + 1))
    raise RuntimeError("download failed %s: %s" % (url, last))


def jget(url):
    return json.loads(http(url).decode("utf-8", "replace"))


def ph_maps(aid, res):
    files = jget(PH + "files/" + aid)

    def url_of(keys):
        for k in keys:
            if k in files:
                for r in (res, "1k", "2k"):
                    f = files[k].get(r, {})
                    for fmt in ("jpg", "png"):
                        if fmt in f:
                            return f[fmt]["url"]
        return None
    return {"diff": url_of(["Diffuse", "diff", "Color"]), "nor": url_of(["nor_gl", "Normal"])}


def ph_rank(spec, assets, used):
    def score(i):
        a = assets[i]
        text = " ".join([i, a.get("name", "")] + list(a.get("tags", [])) + list(a.get("categories", []))).lower()
        text = text.replace("_", " ")
        if not any(k in text for k in spec["must"]):
            return -99
        s = sum(2 for k in spec["prefer"] if k in text) - sum(5 for k in spec["avoid"] + CLEAN_AVOID if k in text)
        return s + min(3.0, a.get("download_count", 0) / 40000.0)
    explicit = [i for i in spec["ids"] if i in assets and i not in used]
    ranked = sorted((i for i in assets if i not in explicit and i not in used and score(i) > 0), key=score, reverse=True)
    return explicit + ranked[:6]


def acg_get(queries, used, res):
    for q in queries:
        try:
            data = jget("https://ambientcg.com/api/v2/full_json?type=Material&sort=Popular&limit=20&include=downloadData&q="
                        + urllib.parse.quote(q))
        except Exception as e:  # noqa: BLE001
            log("  ambientCG search failed", q, e)
            continue
        for a in data.get("foundAssets", []):
            aid = a.get("assetId")
            tags = " ".join(a.get("tags") or []).lower() + " " + (aid or "").lower()
            if not aid or aid in used or any(k in tags for k in CLEAN_AVOID):
                continue
            want = "%s-JPG" % res.upper()
            link = None
            cats = a.get("downloadFolders", {}).get("default", {}).get("downloadFiletypeCategories", {})
            for dl in cats.get("zip", {}).get("downloads", []):
                if dl.get("attribute") == want:
                    link = dl.get("fullDownloadPath") or dl.get("downloadLink")
            link = link or "https://ambientcg.com/get?file=%s_%s.zip" % (aid, want)
            try:
                z = zipfile.ZipFile(io.BytesIO(http(link)))
            except Exception as e:  # noqa: BLE001
                log("  ambientCG zip failed", aid, e)
                continue
            out = {}
            for n in z.namelist():
                low = n.lower()
                if low.endswith("_color.jpg"):
                    out["diff"] = z.read(n)
                elif low.endswith("_normalgl.jpg"):
                    out["nor"] = z.read(n)
            if "diff" in out:
                return ("ambientCG", aid, "https://ambientcg.com/view?id=" + aid), out
    return None, None


def fetch(slot, assets, used, cache):
    folder = os.path.join(cache, slot)
    info = os.path.join(folder, "source.json")
    if os.path.exists(info) and os.path.exists(os.path.join(folder, "diff.jpg")):
        with open(info) as f:
            src = json.load(f)
        used.add(src[1])
        return src, folder
    spec = SLOTS[slot]
    os.makedirs(folder, exist_ok=True)
    for aid in ph_rank(spec, assets, used) if assets else []:
        try:
            maps = ph_maps(aid, "2k")
            if not maps["diff"]:
                continue
            for k, u in maps.items():
                if u:
                    with open(os.path.join(folder, k + ".jpg"), "wb") as f:
                        f.write(http(u))
            src = ("Poly Haven", aid, "https://polyhaven.com/a/" + aid)
            break
        except Exception as e:  # noqa: BLE001
            log("  Poly Haven failed", aid, e)
    else:
        src, data = acg_get(spec["acg"], used, "2k")
        if not src:
            return None, None
        for k, b in data.items():
            with open(os.path.join(folder, k + ".jpg"), "wb") as f:
                f.write(b)
    with open(info, "w") as f:
        json.dump(src, f)
    used.add(src[1])
    return src, folder


def fit(photo, size):
    """Crop the photo to the target's shape (centre), then resize to the target size."""
    w, h = photo.size
    tw, th = size
    ratio = tw / th
    if w / h > ratio:
        nw = int(h * ratio)
        photo = photo.crop(((w - nw) // 2, 0, (w - nw) // 2 + nw, h))
    elif w / h < ratio:
        nh = int(w / ratio)
        photo = photo.crop((0, (h - nh) // 2, w, (h - nh) // 2 + nh))
    return photo.resize((tw, th), Image.LANCZOS)


# how much of the original room colour each kind of surface takes (the rest is the photo's own colour):
# wood stays mostly natural wood, painted walls and wallpaper keep the room's colour
TINT_STRENGTH = {
    "wood_floor": 0.25, "wood_planks": 0.3, "wood_fine": 0.3,
    "plaster": 0.7, "fabric_wall": 0.6,
    "tiles_wall": 0.45, "marble_floor": 0.4, "concrete_floor": 0.4, "stone_wall": 0.4,
    "grass": 0.35, "rock": 0.35,
}
# the brightest a surface's average may get (0-255): very light originals clipped the photo's grain to flat white
MAX_LUMA = {"wood_floor": 150, "wood_planks": 150, "wood_fine": 140, "plaster": 205, "fabric_wall": 170}


def luma(rgb):
    return 0.299 * rgb[0] + 0.587 * rgb[1] + 0.114 * rgb[2]


def tint_to(photo, target_mean, slot=None):
    """Give the photo the original room's colour without flattening it: the photo's own light and dark detail is kept
    (its contrast around its average), the colour moves part of the way to the original's average colour, and very
    light originals are held back so the grain of wood or plaster still shows."""
    k = TINT_STRENGTH.get(slot, 0.5)
    pm = ImageStat.Stat(photo).mean[:3]
    tl = luma(target_mean)
    cap = MAX_LUMA.get(slot, 215)
    if tl > cap:
        target_mean = [c * cap / tl for c in target_mean]
    natural_scale = luma(target_mean) / max(1.0, luma(pm))   # the photo's own colour at the original's brightness
    goal = [k * t + (1 - k) * m * natural_scale for t, m in zip(target_mean, pm)]
    gains = [max(0.2, min(2.5, g / max(m, 1.0))) for g, m in zip(goal, pm)]
    bands = [b.point(lambda v, g=g: max(0, min(255, int(v * g + 0.5)))) for b, g in zip(photo.split()[:3], gains)]
    return Image.merge("RGB", bands)


def main():
    proj, cache, credits = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(cache, exist_ok=True)
    textures = {}
    for dp, _dn, fn in os.walk(os.path.join(proj, "Assets")):
        for f in fn:
            if f.lower().endswith((".png", ".jpg", ".jpeg", ".tga")):
                textures.setdefault(os.path.splitext(f)[0], os.path.join(dp, f))
    log("%d texture images in the project" % len(textures))
    try:
        assets = jget(PH + "assets?t=textures")
        log("Poly Haven textures listed:", len(assets))
    except Exception as e:  # noqa: BLE001
        log("Poly Haven list failed:", e)
        assets = {}

    def lookup(name):
        if name in textures:
            return textures[name]
        hits = [k for k in textures if k.startswith(name)]
        return textures[hits[0]] if len(hits) == 1 else None

    used, chosen, lines = set(), {}, []
    for name, slot in PLAN.items():
        target = lookup(name)
        if not slot or not target:
            if slot and not target:
                log("  (no texture named %s in this export)" % name)
            continue
        if slot not in chosen:
            chosen[slot] = fetch(slot, assets, used, cache)
            log("%-14s <- %s" % (slot, chosen[slot][0][1] if chosen[slot][0] else "NOTHING FOUND"))
        src, folder = chosen[slot]
        if not src:
            continue
        orig = Image.open(target)
        size, mode = orig.size, orig.mode
        mean = ImageStat.Stat(orig.convert("RGB")).mean[:3]
        photo = fit(Image.open(os.path.join(folder, "diff.jpg")).convert("RGB"), size)
        photo = tint_to(photo, mean, slot)
        if "A" in mode:
            photo = photo.convert("RGBA")
            photo.putalpha(orig.convert("RGBA").split()[3])
        photo.save(target)
        lines.append("- `%s` (%s): %s `%s`, CC0, %s" % (name, slot, src[0], src[1], src[2]))
        log("  %-28s %dx%d <- %s %s" % (name[:28], size[0], size[1], src[0], src[1]))

    for nname, base in NORMALS.items():
        target, slot = lookup(nname), PLAN.get(base)
        if not target or not slot or not chosen.get(slot, (None,))[0]:
            continue
        folder = chosen[slot][1]
        size = Image.open(target).size
        nor = os.path.join(folder, "nor.jpg")
        img = fit(Image.open(nor).convert("RGB"), size) if os.path.exists(nor) else Image.new("RGB", size, (128, 128, 255))
        img.save(target)
        log("  %-28s normal map from %s" % (nname[:28], chosen[slot][0][1]))

    os.makedirs(os.path.dirname(os.path.abspath(credits)), exist_ok=True)
    with open(credits, "w", encoding="utf-8") as f:
        f.write("# Real textures in Granny Dimnight\n\nPhoto-scanned surfaces, all CC0 (public domain), tinted to the "
                "colours of the original rooms:\n\n" + "\n".join(lines) + "\n")
    log("replaced %d textures" % len(lines))


if __name__ == "__main__":
    main()
