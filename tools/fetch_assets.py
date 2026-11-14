#!/usr/bin/env python3
"""RAGINI - downloads the real (photographed / recorded) assets at build time. No 3D models, nothing AI-generated.

    python3 tools/fetch_assets.py textures|sounds|fonts|sky|all  [out dir = assets/downloaded]

* textures : photo-scanned PBR surfaces, CC0 - Poly Haven (api.polyhaven.com) and ambientCG (ambientcg.com)
* sounds   : real field recordings from Wikimedia Commons (CC0 / public domain / CC BY / CC BY-SA), trimmed,
             loudness-matched and converted to Ogg Vorbis; a few are layered or slowed from those recordings
* fonts    : SIL Open Font License fonts from the Google Fonts repository
* sky      : a photographed night sky (Poly Haven HDRI, CC0)
Every file used is listed in build/CREDITS_AUTO.md (the release's CREDITS.md - not shown in the game).
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
import urllib.request
import wave
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(ROOT, "assets", "downloaded")
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)
UA = "RaginiGameBuild/1.0 (MXYAN GAMES OFFICIAL; GitHub Actions asset fetch; contact via github.com/arghadeep752-commits)"
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
    "plaster":        dict(ids=["painted_plaster_wall", "white_plaster_rough_01", "beige_wall_001", "plastered_wall"],
                           must=["plaster", "wall", "paint", "stucco"], prefer=["white", "painted", "old", "rough", "dirty", "stain"],
                           avoid=["brick", "tile", "wood", "metal", "stone"], acg=["Plaster", "PaintedPlaster"]),
    "plaster_rough":  dict(ids=["rough_plaster_broken", "plaster_grey_04", "rough_plaster", "concrete_wall_008"],
                           must=["plaster", "stucco", "wall", "concrete"], prefer=["rough", "old", "weathered", "dirty", "exterior"],
                           avoid=["brick", "tile", "wood", "metal"], acg=["Plaster", "Concrete"]),
    "paint_chipped":  dict(ids=["peeling_painted_wall", "painted_concrete", "worn_painted_wall", "green_painted_wall"],
                           must=["paint", "peel", "chipped", "worn"], prefer=["peel", "chip", "wall", "old", "painted"],
                           avoid=["wood", "metal", "brick", "floor"], acg=["PaintedPlaster", "Paint peeling"]),
    "concrete_floor": dict(ids=["concrete_floor_worn_001", "concrete_floor_02", "dirty_concrete", "worn_concrete"],
                           must=["concrete", "floor", "cement"], prefer=["floor", "worn", "old", "dirty", "stain"],
                           avoid=["wall", "brick", "tile", "wood"], acg=["Concrete floor", "Concrete"]),
    "terrazzo":       dict(ids=["terrazzo", "terrazzo_floor", "granite_tile", "marble_01"],
                           must=["terrazzo", "granite", "marble", "speckle", "chip"], prefer=["terrazzo", "floor", "old"],
                           avoid=["wall", "brick", "wood"], acg=["Terrazzo", "Granite"]),
    "tiles_white":    dict(ids=["floor_tiles_06", "white_tiles", "ceramic_tiles", "tiles_white_01"],
                           must=["tile"], prefer=["white", "ceramic", "bathroom", "square", "dirty", "old"],
                           avoid=["roof", "terracotta", "wood", "hex"], acg=["Tiles white", "Tiles"]),
    "stone_floor":    dict(ids=["stone_tiles", "slate_floor", "grey_stone_floor", "stone_floor"],
                           must=["stone", "slate", "slab", "flag"], prefer=["floor", "tiles", "grey", "old"],
                           avoid=["wall", "brick", "cobble", "wood"], acg=["Paving stones", "Slate"]),
    "red_tiles":      dict(ids=["terracotta_tiles", "red_floor_tiles", "patterned_terracotta_tiling", "terracotta_floor_tiles"],
                           must=["tile", "terracotta"], prefer=["red", "terracotta", "floor", "old", "worn"],
                           avoid=["roof", "white", "wood"], acg=["Tiles red", "Terracotta tiles"]),
    "wood":           dict(ids=["wood_table_001", "oak_veneer_01", "wood_table_worn", "plywood"],
                           must=["wood"], prefer=["table", "oak", "worn", "old", "grain", "brown"],
                           avoid=["floor", "planks", "bark", "painted", "white"], acg=["Wood", "Wood table"]),
    "wood_old":       dict(ids=["weathered_planks", "old_planks_02", "wood_planks_grey", "worn_planks"],
                           must=["wood", "plank", "board"], prefer=["old", "weathered", "worn", "grey", "rough"],
                           avoid=["floor", "painted", "white", "parquet"], acg=["Planks old", "Wood weathered"]),
    "wood_painted":   dict(ids=["blue_painted_planks", "painted_wood_peeling", "green_painted_planks", "old_painted_wood"],
                           must=["paint", "painted"], prefer=["wood", "plank", "peel", "old", "blue", "green"],
                           avoid=["metal", "concrete", "brick", "floor"], acg=["Painted wood", "Wood painted"]),
    "metal_painted":  dict(ids=["green_metal_rust", "painted_metal_02", "metal_plate_02", "painted_metal_shutter"],
                           must=["metal", "steel", "iron"], prefer=["painted", "paint", "rust", "green", "old", "worn"],
                           avoid=["floor", "grate", "mesh", "corrugated", "diamond"], acg=["Painted metal", "Metal painted"]),
    "rust":           dict(ids=["rusty_metal_02", "rust_coarse_01", "rusty_metal", "corrugated_iron"],
                           must=["rust", "metal", "iron"], prefer=["rust", "old", "corroded"], avoid=["floor", "mesh"],
                           acg=["Rust", "Metal rust"]),
    "metal_brushed":  dict(ids=["brushed_metal", "metal_plate", "stainless_steel", "metal_grate_rusty"],
                           must=["metal", "steel", "aluminium", "aluminum"], prefer=["brushed", "steel", "scratched"],
                           avoid=["rust", "painted", "grate", "mesh", "corrugated"], acg=["Metal brushed", "Metal"]),
    "slate":          dict(ids=["slate_driveway", "dark_slate", "slate_floor_02", "black_painted_planks"],
                           must=["slate", "stone", "black", "dark"], prefer=["slate", "dark", "smooth", "black"],
                           avoid=["brick", "wood", "tile", "cobble"], acg=["Slate", "Blackboard"]),
    "ground_dirt":    dict(ids=["dry_ground_01", "brown_mud_dry", "dirt_floor", "rocky_dirt1"],
                           must=["dirt", "ground", "mud", "soil", "earth"], prefer=["dry", "brown", "dirt", "ground"],
                           avoid=["snow", "grass", "forest", "leaves", "wet", "moss"], acg=["Ground dirt", "Ground"]),
    "ground_court":   dict(ids=["gravel_ground_01", "aerial_ground_rock", "rocky_trail", "gravelly_sand"],
                           must=["gravel", "ground", "dirt", "sand", "rock"], prefer=["gravel", "dry", "ground", "sand"],
                           avoid=["snow", "forest", "leaves", "moss", "wet"], acg=["Gravel", "Ground"]),
    "brick":          dict(ids=["red_brick_03", "brick_wall_001", "old_brick_wall", "red_brick"],
                           must=["brick"], prefer=["red", "old", "worn", "wall"], avoid=["white", "painted", "floor"],
                           acg=["Bricks"]),
    "concrete":       dict(ids=["concrete_wall_004", "rough_concrete", "concrete_pavement", "grey_concrete"],
                           must=["concrete"], prefer=["rough", "old", "grey", "weathered"], avoid=["floor", "tile", "brick"],
                           acg=["Concrete"]),
    "fabric":         dict(ids=["fabric_pattern_07", "cotton_fabric", "linen_fabric", "fabric_pattern_05"],
                           must=["fabric", "cloth", "cotton", "linen", "silk", "woven"], prefer=["woven", "cotton", "silk", "linen"],
                           avoid=["leather", "carpet", "denim", "rug"], acg=["Fabric"]),
    "hessian":        dict(ids=["hessian_230", "burlap", "jute_fabric", "hessian_380"],
                           must=["hessian", "burlap", "jute", "sack"], prefer=["burlap", "hessian", "jute"], avoid=["leather"],
                           acg=["Burlap", "Fabric jute"]),
    "bark":           dict(ids=["bark_brown_02", "bark_willow", "tree_bark", "pine_bark"],
                           must=["bark"], prefer=["brown", "rough", "old"], avoid=["moss", "birch"], acg=["Bark"]),
    "wood_scale":     dict(ids=["plywood", "light_wood", "pine_wood", "birch_wood"],
                           must=["wood", "plywood", "pine", "birch"], prefer=["light", "plywood", "pine", "smooth", "grain"],
                           avoid=["floor", "dark", "bark", "painted", "planks"], acg=["Plywood", "Wood light"]),
    "cardboard":      dict(ids=["cardboard", "corrugated_cardboard", "paper_crumpled", "kraft_paper"],
                           must=["cardboard", "paper"], prefer=["cardboard", "paper", "brown"], avoid=["wall"],
                           acg=["Cardboard", "Paper"]),
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


def ph_rank(spec, assets, used):
    def score(i):
        a = assets[i]
        text = " ".join([i, a.get("name", "")] + list(a.get("tags", [])) + list(a.get("categories", []))).lower().replace("_", " ")
        if not any(k in text for k in spec["must"]):
            return -99
        s = sum(2 for k in spec["prefer"] if k in text) - sum(5 for k in spec["avoid"] if k in text)
        return s + min(3.0, a.get("download_count", 0) / 40000.0)
    explicit = [i for i in spec["ids"] if i in assets and i not in used]
    ranked = sorted((i for i in assets if i not in explicit and i not in used and score(i) > 0), key=score, reverse=True)
    return explicit + ranked[:6]


def acg_try(queries, dest, used):
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
            for k, n in got.items():
                save(os.path.join(dest, k + ".jpg"), z.read(n))
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
                for k, u in maps.items():
                    if u:
                        save(os.path.join(dest, k + ".jpg"), http(u))
                used.add(aid)
                return slot, ("polyhaven", aid)
            except Exception as e:      # noqa: BLE001
                log("   polyhaven failed", aid, e)
        r = acg_try(spec["acg"], dest, used)
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
    for aid in ("dikhololo_night", "satara_night", "rogland_clear_night", "moonless_golf", "kloppenheim_02"):
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


# ============================================================================================ fonts
def fonts():
    base = "https://raw.githubusercontent.com/google/fonts/main/ofl/"
    for name, path in (("Creepster-Regular.ttf", "creepster/Creepster-Regular.ttf"),
                       ("Oswald.ttf", "oswald/Oswald%5Bwght%5D.ttf"),
                       ("SpecialElite-Regular.ttf", "specialelite/SpecialElite-Regular.ttf")):
        try:
            data = http(base + path)
            if len(data) > 10000:
                save(os.path.join(OUT, "fonts", name), data)
                log("font", name)
        except Exception as e:      # noqa: BLE001
            log("font failed", name, e)
    CREDITS.append("- Fonts: Creepster (Sideshow), Oswald (Vernon Adams), Special Elite (Astigmatic) - SIL Open Font License.")


# ============================================================================================ sounds
COMMONS = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(cc0|cc[- ]zero|public domain|pd|cc[- ]by(?![- ]nc)(?![- ]nd)|cc[- ]by[- ]sa|attribution)", re.I)
SR = 44100
# name: queries, title must contain one of `req`, must not contain `ban`, duration range, seconds kept, options
SOUNDS = {
    "footstep":      dict(q=["footsteps concrete", "footsteps on concrete", "footsteps tile floor", "walking footsteps indoor", "footsteps"],
                          req=["footstep", "foot step", "walking", "steps"], ban=["snow", "gravel", "grass", "leaves", "run", "horse", "march", "stairs", "music"],
                          dur=(2, 400), out=0.45, steps=6),
    "payal":         dict(q=["ghungroo", "ghunghroo", "anklet bells", "ankle bells", "jingle bells small", "small bells jingle", "bells shaking"],
                          req=["ghungr", "anklet", "ankle", "jingle", "bell"], ban=["church", "tower", "alarm", "door", "bicycle", "music", "song", "christmas", "sleigh"],
                          dur=(0.5, 120), out=1.4),
    "door_open":     dict(q=["door creak", "creaking door", "door creaking", "squeaky door"], req=["door", "creak", "squeak"],
                          ban=["music", "song", "slam", "knock", "bell"], dur=(0.8, 60), out=2.6),
    "door_close":    dict(q=["door close", "door closing", "wooden door shut", "door shut"], req=["door"], ban=["music", "song", "knock", "bell", "creak"],
                          dur=(0.3, 40), out=1.6),
    "door_locked":   dict(q=["door handle rattle", "locked door", "door knob rattle", "door handle"], req=["door", "handle", "knob", "lock", "rattle"],
                          ban=["music", "song", "slam", "bell"], dur=(0.3, 40), out=1.4),
    "unlock":        dict(q=["key in lock", "unlocking door", "key turning lock", "padlock", "lock click"], req=["key", "lock", "unlock", "padlock"],
                          ban=["music", "song", "keyboard", "piano"], dur=(0.3, 40), out=1.5),
    "hammer_hit":    dict(q=["hammer hitting wood", "hammer wood", "hammering nail", "hammer"], req=["hammer", "hammering", "nail"],
                          ban=["music", "song", "drill", "jack"], dur=(0.3, 120), out=0.7),
    "plank_fall":    dict(q=["wood plank drop", "wooden plank falling", "wood drop", "plank"], req=["wood", "plank", "board", "timber"],
                          ban=["music", "song", "creak", "door", "wood pecker", "woodpecker"], dur=(0.3, 40), out=1.5),
    "nail_creak":    dict(q=["nail pulling", "wood creak", "creaking wood", "wooden creak"], req=["nail", "creak"],
                          ban=["music", "song", "door"], dur=(0.4, 60), out=1.6),
    "pickup":        dict(q=["keys jingle", "keys jingling", "bunch of keys", "keys"], req=["key"], ban=["music", "song", "keyboard", "piano", "monkey", "turkey"],
                          dur=(0.3, 30), out=0.9),
    "drop":          dict(q=["metal object falling", "drop metal", "metal clang", "metal drop floor"], req=["metal", "drop", "clang", "fall"],
                          ban=["music", "song", "rain", "heavy metal", "band"], dur=(0.2, 30), out=1.2),
    "whack":         dict(q=["stick hit", "slap", "wood stick hit", "whip crack", "punch"], req=["hit", "slap", "whip", "punch", "smack", "stick"],
                          ban=["music", "song", "drum"], dur=(0.1, 20), out=0.8),
    "scream":        dict(q=["woman screaming", "female scream", "woman scream", "scream"], req=["scream", "shriek"],
                          ban=["music", "song", "child", "baby", "man ", "male", "boy", "radio"], dur=(0.5, 30), out=2.6, gain=2),
    "laugh":         dict(q=["woman laughing", "female laugh", "evil laugh", "laughing woman", "witch laugh"], req=["laugh", "cackl"],
                          ban=["music", "song", "baby", "child", "crowd", "audience", "man ", "male"], dur=(0.8, 40), out=3.0),
    "whisper":       dict(q=["whispering", "whisper", "whispers"], req=["whisper"], ban=["music", "song"], dur=(0.8, 120), out=5.0),
    "heartbeat":     dict(q=["heartbeat", "heart beat", "human heartbeat"], req=["heart"], ban=["music", "song", "monitor", "ecg", "act"],
                          dur=(3, 300), out=8.0, loop=True),
    "night":         dict(q=["crickets night", "night ambience crickets", "crickets", "night sounds india", "night ambience"],
                          req=["cricket", "night", "ambien", "insect"], ban=["music", "song", "voice", "speech", "game"], dur=(15, 900), out=40, loop=True, gain=-5),
    "wind":          dict(q=["wind howling", "wind blowing", "strong wind", "wind ambience"], req=["wind"], ban=["music", "song", "instrument", "chime"],
                          dur=(8, 900), out=30, loop=True, gain=-7),
    "fan":           dict(q=["ceiling fan", "fan squeak", "fan creaking", "fan motor"], req=["fan"], ban=["music", "song", "football", "crowd"],
                          dur=(3, 300), out=10, loop=True, gain=-8),
    "tube_buzz":     dict(q=["fluorescent light hum", "fluorescent lamp", "electrical hum", "neon hum", "buzz electric"], req=["fluorescent", "hum", "buzz", "neon"],
                          ban=["music", "song", "bee", "insect"], dur=(2, 300), out=8, loop=True, gain=-10),
    "chalk":         dict(q=["chalk on blackboard", "chalk blackboard", "chalk writing", "chalkboard"], req=["chalk"], ban=["music", "song"],
                          dur=(0.5, 60), out=2.5),
    "bell":          dict(q=["gong", "brass gong", "temple gong", "school bell", "big bell"], req=["gong", "bell"],
                          ban=["music", "song", "door", "bicycle", "alarm", "phone", "church", "jingle"], dur=(1, 60), out=5.0),
    "children":      dict(q=["children laughing", "kids playing", "children playground", "school children"], req=["child", "kid", "school", "playground"],
                          ban=["music", "song", "crying", "baby"], dur=(4, 300), out=8),
    "dog_howl":      dict(q=["dog howling", "dog howl", "dogs howling night", "howling"], req=["howl"], ban=["music", "song", "wolf whistle", "wind"],
                          dur=(1, 60), out=5.0),
    "owl":           dict(q=["owl hooting", "owl", "owl call night"], req=["owl"], ban=["music", "song", "growl", "howl"], dur=(1, 60), out=4.0),
    "clock":         dict(q=["clock ticking", "ticking clock", "clock tick"], req=["clock", "tick"], ban=["music", "song", "alarm"], dur=(2, 120), out=6, loop=True, gain=-8),
    "drip":          dict(q=["water dripping", "dripping tap", "water drip", "drops"], req=["drip", "drop"], ban=["music", "song", "rain storm"],
                          dur=(1, 120), out=6, loop=True, gain=-8),
    "door_slam":     dict(q=["door slam", "slamming door", "door slamming"], req=["slam"], ban=["music", "song"], dur=(0.3, 30), out=2.0),
    "drone":         dict(q=["tanpura", "tambura drone", "drone", "dark ambient drone", "harmonium drone"], req=["tanpura", "tambura", "drone", "harmonium"],
                          ban=["song", "quadcopter", "aircraft", "uav"], dur=(15, 1500), out=60, loop=True, gain=-4),
    "breath":        dict(q=["heavy breathing", "breathing", "panting"], req=["breath", "pant"], ban=["music", "song"], dur=(1, 60), out=4.0),
}
LEVELS = {}


def commons_search(q, limit=40):
    p = {"action": "query", "format": "json", "generator": "search", "gsrnamespace": "6", "gsrlimit": str(limit),
         "gsrsearch": q + " filetype:audio", "prop": "imageinfo", "iiprop": "url|size|mime|extmetadata",
         "iiextmetadatafilter": "LicenseShortName|Artist", "iiextmetadatamultilang": "0"}
    data = jget(COMMONS + "?" + urllib.parse.urlencode(p))
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
    y = x * (10 ** ((target + gain_db) / 20) / (rms + 1e-9))
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


def fetch_sound(name, spec, tmp):
    tried = set()
    t_start = time.time()
    for q in spec["q"]:
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
            if not (5000 < r["size"] < 6_000_000) or time.time() - t_start > 120:
                continue
            tried.add(r["url"])
            try:
                src = os.path.join(tmp, re.sub(r"\W", "_", name) + os.path.splitext(r["url"])[1])
                save(src, http(r["url"]))
                x = decode(src)
            except Exception as e:      # noqa: BLE001
                log("  skip", r["title"], e)
                continue
            dur = len(x) / SR
            if not (spec["dur"][0] <= dur <= spec["dur"][1]) or float(np.max(np.abs(x))) < 0.01:
                continue
            outn = int(spec["out"] * SR)
            gain = spec.get("gain", 0.0)
            path = os.path.join(OUT, "sounds", name + ".ogg")
            if spec.get("steps"):
                clips = onsets(x, spec["steps"], spec["out"])
                if len(clips) < 3:
                    continue
                for i, c in enumerate(clips, 1):
                    encode(normalise(c, -4.0), os.path.join(OUT, "sounds", "%s_%d.ogg" % (name, i)))
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
            REPORT.append("%-12s <- %s | %s | %s | %.1fs" % (name, r["title"], r["lic"], r["author"], dur))
            return "- Sound `%s`: %s - %s - %s (%s)" % (name, r["title"].replace("File:", ""), r["author"] or "unknown", r["lic"], r["page"])
    REPORT.append("%-12s <- NOTHING FOUND" % name)
    return None


def derived():
    """A few sounds made only from the recordings above."""
    snd = lambda n: os.path.join(OUT, "sounds", n + ".ogg")      # noqa: E731
    try:
        if os.path.exists(snd("scream")):
            x = trim(decode(snd("scream")))[: int(1.6 * SR)]
            idx = np.arange(0, len(x) - 1, 0.8)
            y = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
            y = np.concatenate([y, np.zeros(int(0.7 * SR), np.float32)])
            for d, g in ((int(0.12 * SR), 0.5), (int(0.29 * SR), 0.3), (int(0.55 * SR), 0.18)):
                y[d:] += y[:-d] * g
            encode(normalise(y, -1.0), snd("spotted"))
            REPORT.append("spotted      <- the scream, slowed with an echo")
        if os.path.exists(snd("drone")):
            x = decode(snd("drone"))
            idx = np.arange(0, len(x) - 1, 0.84)
            y = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
            acc = 0.0
            lp = np.empty_like(y)
            for k in range(len(y)):
                acc += 0.3 * (float(y[k]) - acc)
                lp[k] = acc
            wet = lp.copy()
            for d, g in ((int(0.21 * SR), 0.45), (int(0.47 * SR), 0.3), (int(0.83 * SR), 0.2)):
                wet[d:] += lp[:-d] * g
            if os.path.exists(snd("wind")):
                w = decode(snd("wind"))
                w = np.tile(w, len(wet) // max(1, len(w)) + 1)[: len(wet)]
                wet = normalise(wet, -2.0) + normalise(w, -12.0)
            encode(normalise(make_loop(wet, 2.0), -3.0), snd("menu_music"))
            REPORT.append("menu_music   <- the drone recording slowed, low-passed and echoed, with the wind")
    except Exception as e:      # noqa: BLE001
        log("derived sounds failed:", e)
    for a, b in (("door_close", "door_slam"), ("door_slam", "door_close"), ("unlock", "pickup"), ("nail_creak", "door_open"),
                 ("plank_fall", "drop"), ("whack", "hammer_hit"), ("spotted", "scream"), ("menu_music", "drone"), ("payal", "pickup")):
        if not os.path.exists(snd(a)) and os.path.exists(snd(b)):
            shutil.copy(snd(b), snd(a))


def sounds():
    tmp = tempfile.mkdtemp(prefix="ragini_snd_")
    with ThreadPoolExecutor(max_workers=2) as ex:
        res = list(ex.map(lambda kv: fetch_sound(kv[0], kv[1], tmp), SOUNDS.items()))
    CREDITS.extend(c for c in res if c)
    derived()
    REPORT.append("")
    REPORT.extend("%-20s %6.1f dBFS %5.1fs" % (k, v[0], v[1]) for k, v in sorted(LEVELS.items()))
    open(os.path.join(BUILD, "sounds_report.txt"), "w").write("\n".join(REPORT) + "\n")
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"textures": textures, "sky": sky, "fonts": fonts, "sounds": sounds}
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
