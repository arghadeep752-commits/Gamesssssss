#!/usr/bin/env python3
"""TRADER'S MADNESS - downloads the real (photographed / recorded) assets at build time. Nothing AI-generated.

    python3 tools/fetch_assets.py textures|sounds|sky|all  [out dir = assets/downloaded]

* textures : photo-scanned PBR surfaces, CC0 - Poly Haven (api.polyhaven.com) and ambientCG (ambientcg.com)
* sounds   : real recordings from Openverse / Wikimedia Commons / the Internet Archive (CC0, public domain, CC BY,
             CC BY-SA), trimmed, loudness-matched and converted to Ogg Vorbis
* sky      : a photographed night sky (Poly Haven HDRI, CC0)
Every file used is listed in build/CREDITS_AUTO.md (the release's CREDITS.md).
"""
import html
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.error
import urllib.request
import wave
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(ROOT, "assets", "downloaded")
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)
UA = "TradersMadnessBuild/1.0 (GitHub Actions asset fetch; contact via github.com/arghadeep752-commits)"
CREDITS = []
REPORT = []


def log(*a):
    print(*a, flush=True)


def http(url, tries=3, timeout=45):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:      # noqa: BLE001
            last = e
            time.sleep((12.0 if "429" in str(e) else 2.0) * (k + 1))
    raise RuntimeError("download failed %s: %s" % (url, last))


def jget(url):
    return json.loads(http(url).decode("utf-8", "replace"))


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# ============================================================================================ textures
# slot: Poly Haven ids tried first, then keyword search (must / prefer / avoid), then ambientCG queries
SLOTS = {
    "plaster":        dict(ids=["painted_plaster_wall", "white_plaster_02", "plaster_grey_04", "beige_wall_001"],
                           must=["plaster", "wall", "paint", "stucco"], prefer=["white", "painted", "smooth", "clean", "interior"],
                           avoid=["brick", "tile", "wood", "metal", "stone", "peel", "damaged", "broken", "dirty", "graffiti"],
                           acg=["PaintedPlaster", "Plaster"], look=dict(min_bright=0.5, max_sat=0.15)),
    "plaster_ext":    dict(ids=["white_plaster_rough_01", "rough_plaster", "plastered_wall_04", "beige_wall_002"],
                           must=["plaster", "stucco", "wall", "render"], prefer=["white", "rough", "exterior", "clean"],
                           avoid=["brick", "tile", "wood", "metal", "broken", "damaged", "peel", "moss", "grass"], acg=["Plaster", "Facade"],
                           look=dict(min_bright=0.45, max_sat=0.18)),
    "concrete":       dict(ids=["concrete_wall_008", "smooth_concrete", "concrete_wall_004", "concrete_wall_006"],
                           must=["concrete"], prefer=["smooth", "wall", "clean", "grey", "panel"], avoid=["floor", "tile", "brick", "broken", "dirty"],
                           acg=["Concrete"], look=dict(max_sat=0.2)),
    "concrete_floor": dict(ids=["concrete_floor_02", "polished_concrete_01", "concrete_floor_painted", "concrete_floor_03"],
                           must=["concrete", "floor", "cement"], prefer=["floor", "polished", "smooth", "garage", "grey"],
                           avoid=["wall", "brick", "tile", "wood", "broken", "cracked"], acg=["Concrete floor", "Concrete"],
                           look=dict(max_sat=0.2)),
    "oak_floor":      dict(ids=["wood_floor", "laminate_floor_02", "oak_floor", "wood_floor_deck"],
                           must=["wood", "floor", "parquet", "laminate", "plank"], prefer=["oak", "floor", "laminate", "parquet", "light", "clean"],
                           avoid=["dirty", "old", "weathered", "painted", "bark", "worn", "rotten", "damaged"], acg=["WoodFloor", "Wood floor"]),
    "dark_floor":     dict(ids=["dark_wooden_planks", "wood_floor_worn", "dark_wood_floor", "brown_floor_tiles"],
                           must=["wood", "floor", "plank", "parquet"], prefer=["dark", "walnut", "floor", "brown", "smooth"],
                           avoid=["painted", "bark", "rotten", "white", "damaged", "weathered"], acg=["WoodFloor dark", "Wood floor"]),
    "stone_tiles":    dict(ids=["large_floor_tiles_02", "stone_tiles_02", "marble_tiles", "floor_tiles_08"],
                           must=["tile", "floor", "stone", "marble"], prefer=["large", "floor", "tile", "grey", "marble", "polished", "porcelain"],
                           avoid=["roof", "terracotta", "wood", "hex", "dirty", "cobble", "broken", "mosaic"], acg=["Tiles", "Marble tiles"]),
    "bath_tiles":     dict(ids=["white_tiles", "ceramic_tiles", "tiles_white_01"],
                           must=["tile"], prefer=["white", "ceramic", "bathroom", "square", "clean", "glossy"],
                           avoid=["roof", "terracotta", "wood", "hex", "dirty", "old", "broken", "checker"], acg=["Tiles white", "Tiles", "Ceramic tiles"],
                           look=dict(min_bright=0.55, max_sat=0.15, max_contrast=0.13)),
    "marble":         dict(ids=["white_marble_03", "calacatta_marble"],
                           must=["marble"], prefer=["white", "polished", "clean", "vein"], avoid=["tile", "tiles", "dirty", "broken", "bust"],
                           acg=["Marble white", "Marble"], look=dict(min_bright=0.6, max_sat=0.12, max_contrast=0.16)),
    "walnut":         dict(ids=["dark_wood", "wood_table_001", "walnut_veneer", "wooden_table_02"],
                           must=["wood"], prefer=["walnut", "dark", "veneer", "table", "smooth", "furniture"],
                           avoid=["floor", "planks", "bark", "painted", "old", "weathered", "rotten"], acg=["Wood", "Wood dark"]),
    "oak":            dict(ids=["oak_veneer_01", "wood_table_worn", "plywood", "light_wood"],
                           must=["wood", "veneer", "oak"], prefer=["oak", "veneer", "light", "table", "smooth"],
                           avoid=["floor", "planks", "bark", "painted", "old", "dark"], acg=["Wood light", "Wood"]),
    "wood_plank":     dict(ids=["weathered_planks", "old_planks_02", "wood_planks_grey", "brown_planks_03"],
                           must=["wood", "plank", "board"], prefer=["old", "plank", "rough", "board"],
                           avoid=["floor", "painted", "white", "parquet"], acg=["Planks old", "Wood planks"]),
    "cladding":       dict(ids=["brown_planks_03", "wood_planks", "wood_cabinet_worn_long", "plank_flooring_02"],
                           must=["wood", "plank", "board", "cladding", "siding"], prefer=["planks", "wood", "boards", "brown", "clean", "facade"],
                           avoid=["old", "weathered", "painted", "rotten", "broken", "white"], acg=["Wood siding", "Planks"]),
    "fabric":         dict(ids=["fabric_pattern_07", "cotton_fabric", "linen_fabric", "fabric_pattern_05"],
                           must=["fabric", "cloth", "cotton", "linen", "woven"], prefer=["woven", "linen", "cotton", "grey", "plain"],
                           avoid=["leather", "carpet", "denim", "rug", "pattern_floral"], acg=["Fabric", "Fabric linen"],
                           look=dict(max_sat=0.22, max_contrast=0.15)),
    "rug":            dict(ids=["carpet_wool", "rug_wool", "fabric_carpet", "carpet_01"],
                           must=["carpet", "rug", "wool", "felt"], prefer=["carpet", "rug", "wool", "grey", "beige"],
                           avoid=["leather", "dirty", "rock", "stone"], acg=["Carpet", "Fabric carpet"],
                           look=dict(max_sat=0.3, max_contrast=0.18)),
    "leather":        dict(ids=["leather_white", "leather_red_02", "brown_leather", "fabric_leather_01"],
                           must=["leather"], prefer=["leather", "black", "smooth"], avoid=["old", "worn", "cracked"], acg=["Leather"]),
    "metal_brushed":  dict(ids=["brushed_metal", "stainless_steel"],
                           must=["brushed", "stainless", "aluminium", "aluminum"], prefer=["brushed", "steel", "stainless", "clean"],
                           avoid=["rust", "rusty", "painted", "grate", "mesh", "corrugated", "dirty", "diamond", "plate", "floor"],
                           acg=["Metal brushed", "Brushed metal", "Metal"], look=dict(max_sat=0.1, max_contrast=0.14)),
    "metal_painted":  dict(ids=["painted_metal_02", "painted_metal"],
                           must=["metal", "steel", "iron"], prefer=["painted", "paint", "grey", "clean", "powder"],
                           avoid=["floor", "grate", "mesh", "corrugated", "diamond", "rust", "rusty", "blue", "green", "red"],
                           acg=["Painted metal", "Metal painted", "Metal"], look=dict(max_sat=0.18, max_contrast=0.16)),
    "corrugated":     dict(ids=["corrugated_iron", "corrugated_iron_02", "metal_roof", "corrugated_metal"],
                           must=["corrugated", "metal", "iron", "shutter"], prefer=["corrugated", "metal", "grey"], avoid=["rust"],
                           acg=["Corrugated steel", "Metal"]),
    "grass":          dict(ids=["grass_medium_01", "leafy_grass"],
                           must=["grass", "lawn"], prefer=["grass", "lawn", "green", "short"],
                           avoid=["snow", "dirt", "rock", "rocks", "forest", "leaves", "mud", "path", "dry"], acg=["Grass", "Lawn"],
                           look=dict(green=True)),
    "paving":         dict(ids=["paving_stones_01", "patio_tiles", "square_floor_tiles", "concrete_pavers"],
                           must=["paving", "pavement", "tile", "stone", "paver", "patio"], prefer=["paving", "patio", "grey", "square", "clean"],
                           avoid=["cobble", "brick", "wood", "dirty", "moss"], acg=["Paving stones", "PavingStones"]),
    "cardboard":      dict(ids=["cardboard", "corrugated_cardboard", "kraft_paper", "paper_crumpled"],
                           must=["cardboard", "paper"], prefer=["cardboard", "paper", "brown"], avoid=["wall"], acg=["Cardboard", "Paper"]),
    "hedge":          dict(ids=["hedge", "leaves_hedge"],
                           must=["hedge", "leaves", "ivy", "foliage", "bush"], prefer=["hedge", "green", "leaves", "bush"],
                           avoid=["dry", "autumn", "dead", "brown", "forest", "ground"], acg=["Hedge", "Foliage", "Leaves", "Grass"],
                           look=dict(green=True)),
}
PH = "https://api.polyhaven.com/"


def ph_files_maps(aid):
    files = jget(PH + "files/" + aid)

    def url_of(keys, res_pref=("1k", "2k")):
        for k in keys:
            if k in files:
                for res in res_pref:
                    f = files[k].get(res, {})
                    for fmt in ("jpg", "png"):
                        if fmt in f:
                            return f[fmt]["url"]
        return None
    return {"diff": url_of(["Diffuse", "diff", "Color"]), "nor": url_of(["nor_gl", "Normal"]), "rough": url_of(["Rough", "rough"]),
            "ao": url_of(["AO", "ao"])}


def has_word(words, k):
    """k as a whole word (or its plural; keys of 4+ letters also match longer words: tile -> tiled, paint -> painted)."""
    return any(w == k or w == k + "s" or w == k + "es" or (len(k) >= 4 and w.startswith(k)) for w in words)


def look_ok(path, look):
    """The photo's colour fits the slot (a white plaster must not be green moss, a lawn must be green, ...)."""
    if not look:
        return True, ""
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB").resize((96, 96)), np.float64) / 255.0
    mean = a.reshape(-1, 3).mean(0)
    bright = float(mean.mean())
    sat = float((mean.max() - mean.min()) / max(mean.max(), 1e-3))
    lum = a.mean(2)
    k = 8                                       # contrast of the large-scale pattern (8 x 8 blocks): checkers, planks
    blocks = lum.reshape(96 // k, k, 96 // k, k).mean((1, 3))
    contrast = float(blocks.std())
    why = "bright %.2f sat %.2f contrast %.2f" % (bright, sat, contrast)
    if bright < look.get("min_bright", 0.0) or bright > look.get("max_bright", 1.0):
        return False, why
    if sat > look.get("max_sat", 1.0):
        return False, why
    if contrast > look.get("max_contrast", 1.0):
        return False, why
    if look.get("green") and not (mean[1] > mean[0] * 1.04 and mean[1] > mean[2] * 1.15 and sat > 0.15):
        return False, why
    return True, why


def ph_rank(spec, assets, used):
    def score(i):
        a = assets[i]
        text = " ".join([i, a.get("name", "")] + list(a.get("tags", [])) + list(a.get("categories", []))).lower()
        words = re.findall(r"[a-z]+", text)
        if not any(has_word(words, k) for k in spec["must"]):
            return -99
        s = sum(2 for k in spec["prefer"] if has_word(words, k)) - sum(5 for k in spec["avoid"] if has_word(words, k))
        return s + min(3.0, a.get("download_count", 0) / 40000.0)
    explicit = [i for i in spec["ids"] if i in assets and i not in used]
    ranked = sorted((i for i in assets if i not in explicit and i not in used and score(i) > 0), key=score, reverse=True)
    return explicit + ranked[:10]


def acg_try(queries, dest, used, look=None):
    for q in queries:
        try:
            data = jget("https://ambientcg.com/api/v2/full_json?type=Material&sort=Popular&limit=15&include=downloadData&q=" + urllib.parse.quote(q))
        except Exception as e:      # noqa: BLE001
            log("   ambientcg query failed", q, e)
            continue
        for a in data.get("foundAssets", []):
            aid = a.get("assetId")
            if not aid or aid in used:
                continue
            link = None
            for dl in a.get("downloadFolders", {}).get("default", {}).get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
                if dl.get("attribute") == "1K-JPG":
                    link = dl.get("fullDownloadPath") or dl.get("downloadLink")
            if not link:
                link = "https://ambientcg.com/get?file=%s_1K-JPG.zip" % aid
            try:
                z = zipfile.ZipFile(io.BytesIO(http(link)))
            except Exception as e:      # noqa: BLE001
                log("   ambientcg zip failed", aid, e)
                continue
            got = {}
            for n in z.namelist():
                low = n.lower()
                if low.endswith("_color.jpg"):
                    got["diff"] = n
                elif low.endswith("_normalgl.jpg"):
                    got["nor"] = n
                elif low.endswith("_roughness.jpg"):
                    got["rough"] = n
                elif low.endswith("_ambientocclusion.jpg"):
                    got["ao"] = n
            if "diff" not in got:
                continue
            shutil.rmtree(dest, ignore_errors=True)
            for k, n in got.items():
                save(os.path.join(dest, k + ".jpg"), z.read(n))
            ok, why = look_ok(os.path.join(dest, "diff.jpg"), look)
            if not ok:
                log("   ambientcg %s does not look right (%s)" % (aid, why))
                used.add(aid)
                shutil.rmtree(dest, ignore_errors=True)
                continue
            return "ambientcg", aid
    return None


def textures():
    try:
        assets = jget(PH + "assets?t=textures")
        log("Poly Haven textures listed:", len(assets))
    except Exception as e:      # noqa: BLE001
        log("Poly Haven list failed:", e)
        assets = {}
    used = set()
    chosen = {}

    def one(slot):
        spec = SLOTS[slot]
        dest = os.path.join(OUT, "tex", slot)
        shutil.rmtree(dest, ignore_errors=True)
        for aid in ph_rank(spec, assets, used) if assets else []:
            try:
                maps = ph_files_maps(aid)
                if not maps["diff"]:
                    continue
                save(os.path.join(dest, "diff.jpg"), http(maps["diff"]))
                ok, why = look_ok(os.path.join(dest, "diff.jpg"), spec.get("look"))
                if not ok:
                    log("   polyhaven %s does not look right for %s (%s)" % (aid, slot, why))
                    shutil.rmtree(dest, ignore_errors=True)
                    continue
                for k, u in maps.items():
                    if u and k != "diff":
                        save(os.path.join(dest, k + ".jpg"), http(u))
                used.add(aid)
                return slot, ("polyhaven", aid)
            except Exception as e:      # noqa: BLE001
                log("   polyhaven failed", aid, e)
        r = acg_try(spec["acg"], dest, used, spec.get("look"))
        if r:
            used.add(r[1])
        return slot, r
    for slot in SLOTS:                     # sequential: keeps the 'used' set honest and is polite to the servers
        s, r = one(slot)
        chosen[s] = r
        log("texture %-15s <- %s" % (s, "%s:%s" % r if r else "NOTHING"))
        if r:
            url = ("https://polyhaven.com/a/" + r[1]) if r[0] == "polyhaven" else ("https://ambientcg.com/view?id=" + r[1])
            CREDITS.append("- Texture `%s`: %s (%s, CC0) %s" % (s, r[1], "Poly Haven" if r[0] == "polyhaven" else "ambientCG", url))
    json.dump(chosen, open(os.path.join(BUILD, "textures_chosen.json"), "w"), indent=1)
    try:
        from PIL import Image
        names = list(SLOTS)
        sheet = Image.new("RGB", (256 * 6, 256 * ((len(names) + 5) // 6) + 20 * ((len(names) + 5) // 6)), (0, 0, 0))
        from PIL import ImageDraw
        dr = ImageDraw.Draw(sheet)
        for i, s in enumerate(names):
            p = os.path.join(OUT, "tex", s, "diff.jpg")
            x, y = (i % 6) * 256, (i // 6) * 276
            if os.path.exists(p):
                sheet.paste(Image.open(p).convert("RGB").resize((256, 256)), (x, y))
            dr.text((x + 4, y + 258), s, fill=(255, 255, 255))
        sheet.save(os.path.join(BUILD, "textures_contact.jpg"), quality=85)
    except Exception as e:      # noqa: BLE001
        log("contact sheet failed:", e)


def sky():
    for aid in ("rogland_clear_night", "dikhololo_night", "satara_night", "moonlit_golf", "kloppenheim_02"):
        try:
            f = jget(PH + "files/" + aid)
            u = f.get("hdri", {}).get("1k", {}).get("hdr", {}).get("url")
            if u:
                save(os.path.join(OUT, "sky", "night.hdr"), http(u))
                CREDITS.append("- Night sky: Poly Haven HDRI `%s` (CC0) https://polyhaven.com/a/%s" % (aid, aid))
                log("sky <-", aid)
                return
        except Exception as e:      # noqa: BLE001
            log("sky failed", aid, e)


# ============================================================================================ sounds
COMMONS = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(cc0|cc[- ]zero|public domain|pd|cc[- ]by(?![- ]nc)(?![- ]nd)|cc[- ]by[- ]sa|attribution)", re.I)
SR = 44100
# name: queries, title must contain one of `req`, must not contain `ban`, duration range, seconds kept, options
SOUNDS = {
    "footstep":      dict(q=["footsteps wood floor", "footsteps wooden floor", "footsteps indoor", "walking footsteps"],
                          req=["footstep", "foot step", "walking", "steps"], ban=["snow", "gravel", "grass", "leaves", "run", "horse", "march", "music", "heels",
                                                                                   "crowd", "voice", "voices", "party", "talk", "people", "office", "rain"],
                          dur=(2, 400), out=0.45, steps=6, ia="footsteps wood floor", v=2),
    "door_open":     dict(q=["door open", "wooden door open", "door opening", "opening a door"], req=["door"],
                          ban=["music", "song", "slam", "knock", "bell", "creak", "squeak", "car ", "car door", "vehicle", "truck", "van ", "bus ",
                               "train", "fridge", "refrigerator", "elevator", "lift ", "oven", "microwave", "garage", "cabinet", "sliding", "alarm"],
                          dur=(0.4, 20), out=1.3, gain=-3, ia="door open"),
    "door_close":    dict(q=["wooden door close", "door close", "door closing", "door shut"], req=["door"],
                          ban=["music", "song", "knock", "bell", "creak", "car ", "car door", "vehicle", "truck", "van ", "bus ", "train", "fridge",
                               "refrigerator", "elevator", "lift ", "oven", "microwave", "garage", "cabinet"],
                          dur=(0.3, 40), out=1.6, ia="door close"),
    "door_locked":   dict(q=["locked door handle", "door handle rattle", "locked door", "door handle"], req=["door", "handle", "knob", "lock", "rattle"],
                          ban=["music", "song", "slam", "bell", "car ", "car door", "vehicle", "truck", "van ", "bus ", "train", "fridge", "refrigerator",
                               "elevator", "lift ", "oven", "microwave", "garage", "cabinet"], dur=(0.3, 40), out=1.4, ia="door handle"),
    "unlock":        dict(q=["key in lock", "unlocking door", "lock click", "key turning lock"], req=["key", "lock", "unlock"],
                          ban=["music", "song", "keyboard", "piano"], dur=(0.3, 40), out=1.5, ia="key lock"),
    "padlock":       dict(q=["padlock open", "padlock", "chain padlock"], req=["padlock", "lock", "chain"],
                          ban=["music", "song", "keyboard"], dur=(0.3, 40), out=1.5, ia="padlock"),
    "plank_crack":   dict(q=["wood crack", "wood breaking", "nail pulling wood", "plank break"], req=["wood", "crack", "break", "nail", "plank", "snap"],
                          ban=["music", "song", "fire", "fireplace", "door", "woodpecker", "bones"], dur=(0.3, 60), out=1.2, ia="wood breaking"),
    "plank_fall":    dict(q=["wood plank drop", "wood drop", "plank fall"], req=["wood", "plank", "board", "timber"],
                          ban=["music", "song", "creak", "door", "woodpecker"], dur=(0.3, 40), out=1.5, ia="wood drop"),
    "pickup":        dict(q=["keys jingle", "keys jingling", "bunch of keys"], req=["key"], ban=["music", "song", "keyboard", "piano", "monkey", "turkey"],
                          dur=(0.3, 30), out=0.9, ia="keys jingle"),
    "drop":          dict(q=["metal object falling", "metal clang", "metal drop"], req=["metal", "drop", "clang", "fall"],
                          ban=["music", "song", "rain", "heavy metal", "band"], dur=(0.2, 30), out=1.2, ia="metal drop"),
    "switch":        dict(q=["light switch", "electrical switch", "breaker switch", "switch click"], req=["switch", "breaker", "click"],
                          ban=["music", "song", "train", "railway"], dur=(0.1, 20), out=0.6, ia="light switch"),
    "drawer":        dict(q=["drawer open", "drawer slide", "opening drawer"], req=["drawer"], ban=["music", "song"],
                          dur=(0.3, 30), out=1.4, ia="drawer open"),
    "safe_open":     dict(q=["safe door open", "metal door open", "vault door"], req=["safe", "vault", "metal door"],
                          ban=["music", "song", "car", "train"], dur=(0.3, 30), out=1.8, ia="metal door open"),
    "punch":         dict(q=["body punch", "punch hit", "face punch", "punch"], req=["punch", "hit", "slap", "smack"],
                          ban=["music", "song", "drum", "keyboard", "8 bit", "8bit", "8-bit", "snare", "chiptune", "synth", "retro", "arcade", "game",
                               "kick", "electronic"],
                          dur=(0.1, 20), out=0.7, ia="punch", v=2),
    "grunt":         dict(q=["man shouting angry", "angry man shout", "man yelling"], req=["shout", "yell", "angry", "scream", "grunt"],
                          ban=["music", "song", "woman", "female", "child", "baby", "crowd", "girl"], dur=(0.4, 30), out=1.8, gain=1, ia="man shouting"),
    "laugh":         dict(q=["man laughing evil", "evil laugh man", "man laugh"], req=["laugh"],
                          ban=["music", "song", "baby", "child", "crowd", "audience", "woman", "female", "girl"], dur=(0.8, 40), out=3.0, ia="evil laugh man"),
    "heartbeat":     dict(q=["heartbeat", "heart beat"], req=["heart"], ban=["music", "song", "monitor", "ecg"],
                          dur=(3, 300), out=8.0, loop=True, ia="heartbeat"),
    "night":         dict(q=["night ambience city", "city night ambience", "crickets night", "night ambience"], req=["night", "ambien", "cricket", "city"],
                          ban=["music", "song", "voice", "speech", "game", "traffic jam", "siren"], dur=(15, 900), out=40, loop=True, gain=-6,
                          ia="night ambience"),
    "rain":          dict(q=["rain on window", "rain window", "light rain"], req=["rain"], ban=["music", "song", "thunder", "storm"],
                          dur=(10, 900), out=40, loop=True, gain=-8, ia="rain on window"),
    "clock":         dict(q=["clock ticking", "clock tick", "ticking clock"], req=["clock", "tick"], ban=["music", "song", "alarm", "bell", "chime"],
                          dur=(3, 300), out=8.0, loop=True, gain=-10, ia="clock ticking"),
    # music under the gameplay: low, slow horror suspense, recorded or composed by a person. Only Freesound uploads
    # from before 2022 (sound ids under 600000), so nothing made by an AI music generator can slip in.
    "game_music":    dict(q=["dark ambient horror", "horror ambience", "suspense drone", "creepy ambient"],
                          req=["horror", "suspense", "creepy", "eerie", "ominous", "tension", "sinister", "dark ambient", "haunt", "scary"],
                          ban=["song", "vocal", "voice", "scream", "laugh", "jumpscare", "jump scare", "8bit", "8-bit", "chiptune", "metal",
                               "dubstep", "trailer", "stinger", "riser", "impact", "whoosh", "beat", "drum", "music box", "piano", "glitch"],
                          ban_re=r"\b(ai|a\.i\.|ai[- ]generated|generated|suno|udio|neural)\b", fs_max_id=600000, calm=True,
                          dur=(60, 1800), out=150, loop=True, gain=-2, ia="dark ambient horror"),
    "chase_music":   dict(q=["horror chase music", "tense chase", "action horror loop", "suspense chase"],
                          req=["chase", "tension", "tense", "action", "horror", "suspense", "run"],
                          ban=["song", "vocal", "voice", "8bit", "8-bit", "chiptune", "dubstep", "happy", "comedy"],
                          ban_re=r"\b(ai|a\.i\.|ai[- ]generated|generated|suno|udio|neural)\b", fs_max_id=600000,
                          dur=(20, 900), out=60, loop=True, gain=0, ia="horror chase music"),
}
LEVELS = {}


def commons_search(q, limit=30):
    p = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6", "gsrlimit": str(limit),
         "gsrsearch": q + " filetype:audio", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
         "iiextmetadatafilter": "LicenseShortName|Artist", "iiextmetadatamultilang": "0"}
    data = json.loads(polite_get(COMMONS + "?" + urllib.parse.urlencode(p)).decode("utf-8", "replace"))
    out = []
    for pg in (data.get("query") or {}).get("pages", {}).values():
        ii = (pg.get("imageinfo") or [None])[0]
        if not ii:
            continue
        md = ii.get("extmetadata", {})
        lic = md.get("LicenseShortName", {}).get("value", "")
        art = re.sub(r"<[^>]+>", "", html.unescape(md.get("Artist", {}).get("value", ""))).strip()
        out.append(dict(title=pg["title"], url=ii["url"], page=ii.get("descriptionurl", ""), size=ii.get("size", 0), mime=ii.get("mime", ""),
                        lic=lic, author=art[:80], index=pg.get("index", 99)))
    out.sort(key=lambda r: r["index"])
    return out


def decode(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def encode(x, path):
    x = np.clip(np.asarray(x, np.float32), -1, 1)
    if len(x):
        LEVELS[os.path.basename(path)] = (20 * np.log10(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) + 1e-9), len(x) / SR)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    os.makedirs(os.path.dirname(path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", "4", path], check=True)
    os.remove(tmp)


def trim(x, thr=0.01):
    i = np.where(np.abs(x) > thr)[0]
    return x if len(i) == 0 else x[max(0, i[0] - int(0.015 * SR)): i[-1] + int(0.05 * SR)]


def loudest(x, n):
    if len(x) <= n:
        return x
    hop = SR // 4
    e = np.convolve(np.abs(x), np.ones(hop) / hop, mode="same")[::hop]
    k = max(1, n // hop)
    best = int(np.argmax(np.convolve(e, np.ones(k) / k, mode="valid"))) * hop if len(e) > k else 0
    return x[best: best + n]


def make_loop(x, cross=1.0):
    c = int(cross * SR)
    if len(x) < 3 * c:
        return x
    h = x[: len(x) - c].copy()
    f = np.linspace(0, 1, c, dtype=np.float32)
    h[:c] = h[:c] * f + x[len(x) - c:] * (1 - f)
    return h


def normalise(x, gain_db=0.0, target=-16.0):
    x = np.asarray(x, np.float32)
    if not len(x):
        return x
    w = int(0.05 * SR)
    n = len(x) // w
    if n >= 2:
        e = (x[: n * w].astype(np.float64) ** 2).reshape(n, w).mean(axis=1)
        keep = e >= max(float(np.percentile(e, 30)), float(e.max()) * 1e-5)
        rms = float(np.sqrt(np.median(e[keep])))
    else:
        rms = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
    g = 10 ** ((target + gain_db) / 20) / (rms + 1e-9)
    g = min(g, 1.0 / (float(np.max(np.abs(x))) + 1e-9))      # bells and clicks stay clean instead of being squashed
    y = x * g
    return (np.tanh(y / 0.95) * 0.95).astype(np.float32)


def onsets(x, count, length):
    hop = int(0.01 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(hop) / hop, mode="same"))[::hop]
    thr = np.percentile(env, 90)
    clips, last = [], -999
    for i in range(2, len(env) - 2):
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] > env[i + 1] and i - last > 30:
            last = i
            s = max(0, i * hop - int(0.03 * SR))
            seg = x[s: s + int(length * SR)]
            if len(seg) == int(length * SR):
                clips.append(seg.copy())
    clips.sort(key=lambda s: -float(np.max(np.abs(s))))
    clips = clips[: count]
    for c in clips:
        f = int(0.08 * SR)
        c[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return clips


_last_req = [0.0]
MANIFEST = "manifest_v2.json"      # bump to fetch every clip again
FAILS = {"commons": 0, "openverse": 0}


def dead(src):
    return FAILS[src] >= (4 if src == "commons" else 3)


def polite_get(url):
    """Wikimedia asks bots for one request at a time; it throttles cloud machines hard, so give up quickly."""
    if dead("commons"):
        raise RuntimeError("wikimedia is throttling this machine")
    last = None
    for k in range(3):
        gap = time.time() - _last_req[0]
        if gap < 1.3:
            time.sleep(1.3 - gap)
        _last_req[0] = time.time()
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=40) as r:
                data = r.read()
            FAILS["commons"] = 0
            return data
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 404:
                raise
            if e.code == 429:
                FAILS["commons"] += 1
                if dead("commons"):
                    log("wikimedia keeps answering 429 - switching to other sources")
                    break
                try:
                    wait = int(e.headers.get("Retry-After", "8"))
                except Exception:       # noqa: BLE001
                    wait = 8
                time.sleep(min(max(wait, 3), 15))
                continue
            time.sleep(2)
        except Exception as e:      # noqa: BLE001
            last = e
            time.sleep(2)
    raise RuntimeError("gave up on %s: %s" % (url, last))


def transcoded(url):
    m = re.match(r"(https://upload\.wikimedia\.org/wikipedia/commons/)(\w/\w\w/)([^?]+)", url)
    if not m:
        return None
    return m.group(1) + "transcoded/" + m.group(2) + m.group(3) + "/" + m.group(3) + ".mp3"


def calm_dark(x):
    """True for audio that stays low and even: most energy below ~1.5 kHz and no sudden loud hits."""
    w = int(0.05 * SR)
    n = len(x) // w
    if n < 40:
        return False
    rms = np.sqrt(np.mean(x[: n * w].reshape(n, w) ** 2, axis=1) + 1e-12)
    spikes = float(np.percentile(rms, 99.5) / (np.median(rms) + 1e-9))
    seg = x[: min(len(x), 60 * SR)]
    spec = np.abs(np.fft.rfft(seg * np.hanning(len(seg))))
    freqs = np.fft.rfftfreq(len(seg), 1.0 / SR)
    centroid = float(np.sum(freqs * spec) / (np.sum(spec) + 1e-9))
    log("   calm check: centroid %.0f Hz, loudest/median %.1f" % (centroid, spikes))
    return centroid < 1500 and spikes < 4.5


def process(name, spec, x, path_dir):
    dur = len(x) / SR
    if not (spec["dur"][0] <= dur <= spec["dur"][1]) or float(np.max(np.abs(x))) < 0.01:
        return False
    if spec.get("calm") and not calm_dark(x):
        return False
    outn = int(spec["out"] * SR)
    gain = spec.get("gain", 0.0)
    path = os.path.join(path_dir, name + ".ogg")
    if spec.get("steps"):
        clips = onsets(x, spec["steps"], spec["out"])
        if len(clips) < 3:
            return False
        for i, c in enumerate(clips, 1):
            encode(normalise(c, -4.0), os.path.join(path_dir, "%s_%d.ogg" % (name, i)))
    elif spec.get("loop"):
        y = loudest(x, outn + SR) if len(x) > outn + SR else x
        encode(normalise(make_loop(y, 1.0), gain), path)
    else:
        y = trim(x)
        y = loudest(y, outn) if len(y) > outn else y
        f = min(len(y) // 4, int(0.2 * SR))
        if f > 0:
            y[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
        y[:64] *= np.linspace(0, 1, min(64, len(y)), dtype=np.float32)
        encode(normalise(y, gain), path)
    return True


OV_PREF = {"freesound": 0, "jamendo": 1, "ccmixter": 1, "wikimedia_audio": 3}


def openverse_fetch(name, spec, tmp):
    """Openverse indexes openly licensed recordings (mostly Freesound) and serves direct file links."""
    for q in spec["q"][:4]:
        if dead("openverse") or time.time() > SOUND_DEADLINE[0]:
            return None
        time.sleep(1.0)
        url = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(
            {"q": q, "license": "cc0,pdm,by,by-sa", "page_size": "20", "mature": "false"})
        try:
            data = json.loads(http(url, tries=2, timeout=30).decode("utf-8", "replace"))
            FAILS["openverse"] = 0
        except Exception as e:      # noqa: BLE001
            FAILS["openverse"] += 1
            log("openverse search failed", q, str(e)[:120])
            continue
        cands = []
        for i, r in enumerate(data.get("results", [])):
            title = (r.get("title") or "").lower()
            tags = " ".join((t.get("name") or "") for t in (r.get("tags") or [])).lower()
            if not any(k in title + " " + tags for k in spec["req"]) or any(k in title for k in spec["ban"]):
                continue
            if spec.get("ban_re") and re.search(spec["ban_re"], title + " " + tags):
                continue
            if spec.get("fs_max_id"):
                mfs = re.search(r"freesound\.org/people/[^/]+/sounds/(\d+)", r.get("foreign_landing_url") or "")
                if not mfs or int(mfs.group(1)) >= spec["fs_max_id"]:
                    continue
            d = (r.get("duration") or 0) / 1000.0
            if d and not (spec["dur"][0] <= d <= spec["dur"][1]):
                continue
            src = r.get("source") or r.get("provider") or ""
            if src == "wikimedia_audio" and dead("commons"):
                continue
            if not r.get("url") or (r.get("license") or "").lower() not in ("cc0", "pdm", "by", "by-sa"):
                continue
            cands.append((OV_PREF.get(src, 2), i, r))
        cands.sort(key=lambda c: (c[0], c[1]))
        for _, _, r in cands[:4]:
            u = r["url"]
            ext = os.path.splitext(urllib.parse.urlparse(u).path)[1] or ".mp3"
            try:
                src = os.path.join(tmp, re.sub(r"\W", "_", name) + "_ov" + ext)
                save(src, polite_get(u) if "wikimedia.org" in u else http(u, tries=2, timeout=40))
                x = decode(src)
            except Exception as e:      # noqa: BLE001
                log("  skip", r.get("title"), str(e)[:80])
                continue
            if not process(name, spec, x, os.path.join(OUT, "sounds")):
                continue
            lic = (r.get("license") or "").upper().replace("BY", "CC BY") if r.get("license") not in ("cc0", "pdm") else r["license"].upper()
            lic += (" " + r["license_version"]) if r.get("license_version") and r.get("license") != "pdm" else ""
            REPORT.append("%-12s <- openverse/%s %s | %s | %s | %.1fs" % (name, r.get("source"), r.get("title"), lic, r.get("creator"), len(x) / SR))
            return "- Sound `%s`: \"%s\" by %s - %s - %s" % (name, r.get("title"), r.get("creator") or "unknown", lic, r.get("foreign_landing_url") or u)
    return None


def archive_fetch(name, spec, tmp):
    """Fallback: public-domain / Creative Commons recordings on the Internet Archive."""
    q = '(%s) AND mediatype:(audio) AND (licenseurl:(*publicdomain*) OR licenseurl:(*creativecommons.org/licenses/by/*) OR licenseurl:(*creativecommons.org/licenses/by-sa/*))' % spec["ia"]
    try:
        res = jget("https://archive.org/advancedsearch.php?" + urllib.parse.urlencode({"q": q, "fl[]": "identifier", "rows": "8", "output": "json"}))
    except Exception as e:      # noqa: BLE001
        log("archive search failed", name, e)
        return None
    for doc in res.get("response", {}).get("docs", []):
        ident = doc["identifier"]
        try:
            md = jget("https://archive.org/metadata/" + ident)
        except Exception:       # noqa: BLE001
            continue
        lic = md.get("metadata", {}).get("licenseurl", "")
        title = md.get("metadata", {}).get("title", ident)
        creator = md.get("metadata", {}).get("creator", "")
        if isinstance(creator, list):
            creator = ", ".join(creator)
        files = [f for f in md.get("files", []) if f.get("format") in ("VBR MP3", "Ogg Vorbis", "MP3") and 3000 < int(f.get("size", 0) or 0) < 8_000_000]
        files.sort(key=lambda f: (0 if any(k in f["name"].lower() for k in spec["req"]) else 1, int(f.get("size", 0))))
        for f in files[:3]:
            try:
                src = os.path.join(tmp, re.sub(r"\W", "_", name) + "_ia" + os.path.splitext(f["name"])[1])
                save(src, http("https://archive.org/download/%s/%s" % (ident, urllib.parse.quote(f["name"]))))
                x = decode(src)
            except Exception:       # noqa: BLE001
                continue
            if process(name, spec, x, os.path.join(OUT, "sounds")):
                REPORT.append("%-12s <- archive.org %s / %s | %s" % (name, ident, f["name"], lic))
                return "- Sound `%s`: %s (%s) - %s - %s https://archive.org/details/%s" % (name, title, f["name"], creator or "unknown", lic, ident)
    return None


SOUND_DEADLINE = [time.time() + 30 * 60]      # never let the sound search stall the build


def fetch_sound(name, spec, tmp):
    tried = set()
    t_start = time.time()
    if time.time() > SOUND_DEADLINE[0]:
        REPORT.append("%-12s <- skipped (time budget)" % name)
        return None
    c = openverse_fetch(name, spec, tmp)
    if c:
        return c
    for q in spec["q"]:
        if time.time() - t_start > 110 or dead("commons"):
            break
        try:
            res = commons_search(q)
        except Exception as e:      # noqa: BLE001
            log("search failed", q, e)
            continue
        for r in res:
            t = r["title"].lower()
            if r["url"] in tried or not OK_LIC.match(r["lic"] or ""):
                continue
            if not any(k in t for k in spec["req"]) or any(k in t for k in spec["ban"]):
                continue
            if not (5000 < r["size"] < 40_000_000) or time.time() - t_start > 110:
                continue
            tried.add(r["url"])
            x = None
            for u in ([transcoded(r["url"])] if r["size"] > 1_500_000 and not r["url"].lower().endswith(".mp3") else []) + [r["url"]]:
                if not u:
                    continue
                try:
                    src = os.path.join(tmp, re.sub(r"\W", "_", name) + os.path.splitext(u)[1])
                    save(src, polite_get(u))
                    x = decode(src)
                    break
                except Exception as e:      # noqa: BLE001
                    log("  skip", r["title"], str(e)[:80])
            if x is None:
                continue
            if not process(name, spec, x, os.path.join(OUT, "sounds")):
                continue
            REPORT.append("%-12s <- %s | %s | %s | %.1fs" % (name, r["title"], r["lic"], r["author"], len(x) / SR))
            return "- Sound `%s`: %s - %s - %s (%s)" % (name, r["title"].replace("File:", ""), r["author"] or "unknown", r["lic"], r["page"])
    c = archive_fetch(name, spec, tmp) if time.time() < SOUND_DEADLINE[0] else None
    if c:
        return c
    REPORT.append("%-12s <- NOTHING FOUND" % name)
    return None


def derived():
    """Sounds made only from the recordings above."""
    snd = lambda n: os.path.join(OUT, "sounds", n + ".ogg")      # noqa: E731
    try:
        if os.path.exists(snd("grunt")):
            x = trim(decode(snd("grunt")))[: int(1.6 * SR)]
            y = np.concatenate([x, np.zeros(int(0.7 * SR), np.float32)])
            for d, g in ((int(0.12 * SR), 0.45), (int(0.29 * SR), 0.28), (int(0.55 * SR), 0.15)):
                y[d:] += y[:-d] * g
            encode(normalise(y, -1.0), snd("spotted"))
            REPORT.append("spotted      <- the shout with an echo")
        if os.path.exists(snd("game_music")):
            x = decode(snd("game_music"))
            idx = np.arange(0, len(x) - 1, 0.86)
            y = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
            acc = 0.0
            lp = np.empty_like(y)
            for k in range(len(y)):
                acc += 0.25 * (float(y[k]) - acc)
                lp[k] = acc
            encode(normalise(make_loop(lp, 2.0), -3.0), snd("menu_music"))
            REPORT.append("menu_music   <- game_music slowed and darkened")
    except Exception as e:      # noqa: BLE001
        log("derived sounds failed:", e)
    for a, b in (("padlock", "unlock"), ("unlock", "padlock"), ("plank_fall", "drop"), ("safe_open", "door_open"),
                 ("drawer", "door_open"), ("spotted", "grunt")):
        if not os.path.exists(snd(a)) and os.path.exists(snd(b)):
            shutil.copy(snd(b), snd(a))


def sounds():
    tmp = tempfile.mkdtemp(prefix="tm_snd_")
    sdir = os.path.join(OUT, "sounds")
    os.makedirs(sdir, exist_ok=True)
    SOUND_DEADLINE[0] = time.time() + float(os.environ.get("SOUND_BUDGET_MIN", "30")) * 60
    mpath = os.path.join(sdir, MANIFEST)
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}
    def mkey(name, spec):
        return name + ("@v%d" % spec["v"] if spec.get("v") else "")

    for name, spec in SOUNDS.items():
        first = os.path.join(sdir, name + ("_1" if spec.get("steps") else "") + ".ogg")
        if mkey(name, spec) in manifest and os.path.exists(first):
            log("sound %-12s kept from the last build" % name)
            continue
        try:
            c = fetch_sound(name, spec, tmp)
        except Exception as e:      # noqa: BLE001
            log("sound failed", name, e)
            c = None
        log("sound %-12s %s" % (name, "ok" if c else "MISSING"))
        if c:
            manifest[mkey(name, spec)] = c
            json.dump(manifest, open(mpath, "w"), indent=1)
    derived()
    REPORT.append("")
    REPORT.append("%d of %d recorded sounds found" % (sum(1 for n, sp in SOUNDS.items() if mkey(n, sp) in manifest), len(SOUNDS)))
    open(os.path.join(BUILD, "sounds_report.txt"), "w").write("\n".join(REPORT) + "\n")
    open(os.path.join(sdir, "CREDITS_SOUNDS.md"), "w").write("\n".join(manifest[mkey(n, sp)] for n, sp in SOUNDS.items() if mkey(n, sp) in manifest) + "\n")


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"textures": textures, "sky": sky, "sounds": sounds}
    for s in (list(steps) if what == "all" else what.split(",")):
        log("=== %s ===" % s)
        try:
            steps[s]()
        except Exception as e:      # noqa: BLE001
            import traceback
            traceback.print_exc()
            log("STEP FAILED:", s, e)
    with open(os.path.join(BUILD, "CREDITS_AUTO.md"), "a") as f:
        f.write("\n".join(CREDITS) + "\n")
    log("done")
