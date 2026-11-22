#!/usr/bin/env python3
"""DANGA - downloads the real (photographed / recorded / human-made) assets at build time. Nothing AI-generated.

    python3 tools/fetch_assets.py textures|sky|leaves|sounds|music|fonts|all  [out dir = assets/downloaded]

* textures : photo-scanned PBR surfaces, CC0 - Poly Haven (api.polyhaven.com) and ambientCG (ambientcg.com)
* sky      : photographed day and night skies (Poly Haven HDRIs, CC0)
* leaves   : the photographed leaf / branch cut-outs of Poly Haven's tree models (CC0) for the procedural trees
* sounds   : real recordings from Openverse (Freesound, ...) / Wikimedia Commons / the Internet Archive
             (CC0, public domain, CC BY, CC BY-SA), trimmed, loudness-matched and converted to Ogg Vorbis
* music    : music made and played by people (Freesound uploads from before 2021, ccMixter, Jamendo tracks from before
             2021, Wikimedia Commons, the Internet Archive) - CC0 / CC BY / CC BY-SA only
* fonts    : dafont.com - The Bold Font (Sven Pels, 100% free) and Bebas Neue (Dharma Type, SIL OFL)
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
import urllib.error
import urllib.parse
import urllib.request
import wave
import zipfile

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.abspath(sys.argv[2]) if len(sys.argv) > 2 else os.path.join(ROOT, "assets", "downloaded")
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)
UA = "DangaGameBuild/1.0 (GitHub Actions asset fetch; contact via github.com/arghadeep752-commits)"
BROWSER_UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
CREDITS = []
REPORT = []


def log(*a):
    print(*a, flush=True)


def http(url, tries=3, timeout=45, ua=None):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": ua or UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:      # noqa: BLE001
            last = e
            if isinstance(e, urllib.error.HTTPError) and e.code in (403, 404):
                break
            time.sleep((12.0 if "429" in str(e) else 2.0) * (k + 1))
    raise RuntimeError("download failed %s: %s" % (url, last))


def jget(url):
    return json.loads(http(url).decode("utf-8", "replace"))


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# ============================================================================================ textures
# slot: Poly Haven ids tried first, then keyword search (must / prefer / avoid), then ambientCG queries.
# look: colour checks of the photo (a white plaster must not be green moss, a lawn must be green, ...)
SLOTS = {
    "asphalt":      dict(ids=["asphalt_02", "asphalt_track", "rough_asphalt", "asphalt_03"],
                         must=["asphalt", "road", "tarmac"], prefer=["asphalt", "road", "grey", "tarmac"],
                         avoid=["marking", "line", "cracked", "puddle", "wet", "snow", "pit"], acg=["Asphalt", "Road"],
                         look=dict(max_sat=0.25, max_contrast=0.12, max_bright=0.6)),
    "asphalt_old":  dict(ids=["cracked_asphalt", "asphalt_01", "damaged_asphalt"],
                         must=["asphalt", "road", "tarmac"], prefer=["old", "worn", "cracked", "patch"],
                         avoid=["marking", "snow", "puddle"], acg=["Asphalt cracked", "Asphalt"], look=dict(max_sat=0.3)),
    "paving":       dict(ids=["concrete_pavers", "paving_stones_01", "patterned_paving", "square_floor_tiles"],
                         must=["paving", "pavers", "pavement", "tiles", "sidewalk"], prefer=["paving", "concrete", "grey", "pavers"],
                         avoid=["cobble", "wood", "moss", "brick", "dirty"], acg=["Paving stones", "PavingStones"],
                         look=dict(max_sat=0.3)),
    "curb":         dict(ids=["concrete_floor_02", "smooth_concrete", "concrete_wall_008"],
                         must=["concrete"], prefer=["smooth", "grey", "clean"], avoid=["painted", "dirty", "moss", "tiles"],
                         acg=["Concrete"], look=dict(max_sat=0.2)),
    "concrete":     dict(ids=["concrete_wall_008", "concrete_wall_004", "concrete_wall_006"],
                         must=["concrete"], prefer=["wall", "grey", "weathered"], avoid=["floor", "tiles", "moss", "graffiti"],
                         acg=["Concrete wall", "Concrete"], look=dict(max_sat=0.25)),
    "plaster":      dict(ids=["painted_plaster_wall", "white_plaster_02", "beige_wall_001", "plaster_grey_04"],
                         must=["plaster", "wall", "stucco", "paint"], prefer=["white", "painted", "smooth", "plaster"],
                         avoid=["brick", "stone", "wood", "dirty", "moss", "graffiti", "tile"], acg=["Plaster", "PaintedPlaster"],
                         look=dict(min_bright=0.45, max_sat=0.25, max_contrast=0.08)),
    "plaster_old":  dict(ids=["plastered_wall_04", "rough_plaster", "white_plaster_rough_01", "worn_plaster"],
                         must=["plaster", "wall", "stucco"], prefer=["old", "worn", "rough", "weathered", "dirty"],
                         avoid=["brick", "wood", "moss", "graffiti", "tile"], acg=["Plaster rough", "Plaster"],
                         look=dict(min_bright=0.3, max_sat=0.35)),
    "brick":        dict(ids=["red_brick_03", "red_brick", "brick_wall_02", "red_bricks_04"],
                         must=["brick"], prefer=["red", "wall", "old"], avoid=["white", "painted", "floor", "moss", "dark"],
                         acg=["Bricks"], look=dict(max_bright=0.6)),
    "roof_tin":     dict(ids=["corrugated_iron", "corrugated_iron_02", "rusty_corrugated_iron"],
                         must=["corrugated", "iron", "metal", "roof"], prefer=["corrugated", "rust", "roof", "iron"],
                         avoid=["floor", "plate"], acg=["Corrugated steel", "CorrugatedSteel"]),
    "roof_tiles":   dict(ids=["clay_roof_tiles", "roof_tiles_14", "roof_tiles"],
                         must=["roof", "tiles", "clay"], prefer=["clay", "red", "roof", "terracotta"], avoid=["floor", "bath"],
                         acg=["Roofing tiles", "RoofingTiles"]),
    "grass":        dict(ids=["leafy_grass", "aerial_grass_rock", "grass_path_2"],
                         must=["grass", "lawn", "meadow"], prefer=["green", "grass", "lawn", "leafy"],
                         avoid=["dry", "snow", "autumn", "dead", "brown", "rock", "path"], acg=["Grass"], look=dict(green=True)),
    "ground":       dict(ids=["red_dirt_mud_01", "brown_mud_02", "dirt", "forrest_ground_01"],
                         must=["dirt", "mud", "soil", "ground", "earth"], prefer=["dirt", "brown", "red", "soil", "dry"],
                         avoid=["snow", "rock", "stone", "leaves", "moss", "wet"], acg=["Ground", "Dirt"]),
    "sand":         dict(ids=["coast_sand_01", "sand_01", "sandy_gravel"],
                         must=["sand", "beach"], prefer=["sand", "beach", "coast", "fine"],
                         avoid=["rock", "stone", "snow", "gravel", "wet", "seaweed"], acg=["Sand"], look=dict(min_bright=0.35, max_contrast=0.1)),
    "rock":         dict(ids=["rocks_ground_01", "coast_sand_rocks_02", "rock_wall_02"],
                         must=["rock", "stone", "boulder"], prefer=["rock", "coast", "grey"], avoid=["snow", "moss", "wall", "brick"],
                         acg=["Rock"]),
    "wood":         dict(ids=["wood_planks", "old_planks_02", "weathered_planks", "brown_planks_03"],
                         must=["wood", "planks", "plank", "timber"], prefer=["planks", "brown", "old"], avoid=["floor", "painted", "white"],
                         acg=["Planks", "Wood"]),
    "metal":        dict(ids=["painted_metal_02", "metal_plate", "painted_metal"],
                         must=["metal", "steel", "iron"], prefer=["painted", "plate", "metal"], avoid=["rust", "corrugated", "grate"],
                         acg=["Painted metal", "Metal"]),
    "marble":       dict(ids=["white_marble_03", "marble_01", "calacatta_marble"],
                         must=["marble"], prefer=["white", "marble"], avoid=["black", "green", "dark"], acg=["Marble"],
                         look=dict(min_bright=0.5)),
    "tiles":        dict(ids=["large_floor_tiles_02", "floor_tiles_06", "stone_tiles_02"],
                         must=["tiles", "tile"], prefer=["floor", "stone", "large"], avoid=["bath", "wall", "roof", "mosaic"],
                         acg=["Tiles"]),
    "bark":         dict(ids=["bark_brown_02", "bark_willow", "pine_bark"],
                         must=["bark", "trunk"], prefer=["bark", "brown", "tree"], avoid=["moss", "snow"], acg=["Bark"]),
    "fabric":       dict(ids=["fabric_pattern_07", "denim_fabric", "cotton_fabric"],
                         must=["fabric", "cloth", "canvas"], prefer=["fabric", "canvas", "cotton"], avoid=["leather", "carpet"],
                         acg=["Fabric"]),
    "facade1":      dict(ids=[], must=["facade", "building"], prefer=["windows", "apartment"], avoid=["brick", "wood"],
                         acg=["Facade"], look=dict(max_sat=0.4)),
    "facade2":      dict(ids=[], must=["facade", "building"], prefer=["windows", "office", "concrete"], avoid=["wood"],
                         acg=["Facade", "Building facade"], look=dict(max_sat=0.4)),
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
    return {"diff": url_of(["Diffuse", "diff", "Color"]), "nor": url_of(["nor_gl", "Normal"]), "rough": url_of(["Rough", "rough"])}


def has_word(words, k):
    return any(w == k or w == k + "s" or w == k + "es" or (len(k) >= 4 and w.startswith(k)) for w in words)


def look_ok(path, look):
    if not look:
        return True, ""
    from PIL import Image
    a = np.asarray(Image.open(path).convert("RGB").resize((96, 96)), np.float64) / 255.0
    mean = a.reshape(-1, 3).mean(0)
    bright = float(mean.mean())
    sat = float((mean.max() - mean.min()) / max(mean.max(), 1e-3))
    lum = a.mean(2)
    k = 8
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
    return explicit + ranked[:8]


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
        if slot.startswith("facade"):            # real photographed facades only exist on ambientCG
            r = acg_try(spec["acg"], dest, used, spec.get("look"))
            if r:
                used.add(r[1])
            return slot, r
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
    for slot in SLOTS:
        s, r = one(slot)
        chosen[s] = r
        log("texture %-12s <- %s" % (s, "%s:%s" % r if r else "NOTHING"))
        if r:
            url = ("https://polyhaven.com/a/" + r[1]) if r[0] == "polyhaven" else ("https://ambientcg.com/view?id=" + r[1])
            CREDITS.append("- Texture `%s`: %s (%s, CC0) %s" % (s, r[1], "Poly Haven" if r[0] == "polyhaven" else "ambientCG", url))
    json.dump(chosen, open(os.path.join(BUILD, "textures_chosen.json"), "w"), indent=1)
    contact_sheet([os.path.join(OUT, "tex", s, "diff.jpg") for s in SLOTS], list(SLOTS), os.path.join(BUILD, "textures_contact.jpg"))


def contact_sheet(paths, names, out):
    try:
        from PIL import Image, ImageDraw
        cols = 6
        rows = (len(paths) + cols - 1) // cols
        sheet = Image.new("RGB", (256 * cols, 276 * rows), (0, 0, 0))
        dr = ImageDraw.Draw(sheet)
        for i, (p, n) in enumerate(zip(paths, names)):
            x, y = (i % cols) * 256, (i // cols) * 276
            if os.path.exists(p):
                sheet.paste(Image.open(p).convert("RGB").resize((256, 256)), (x, y))
            dr.text((x + 4, y + 258), n, fill=(255, 255, 255))
        sheet.save(out, quality=85)
    except Exception as e:      # noqa: BLE001
        log("contact sheet failed:", e)


def sky():
    for key, ids in (("day", ("kloofendal_48d_partly_cloudy_puresky", "qwantani_puresky", "sunflowers_puresky",
                              "kloofendal_43d_clear_puresky", "kloofendal_38d_partly_cloudy")),
                     ("night", ("rogland_clear_night", "satara_night", "dikhololo_night", "moonlit_golf"))):
        for aid in ids:
            try:
                f = jget(PH + "files/" + aid)
                u = f.get("hdri", {}).get("2k" if key == "day" else "1k", {}).get("hdr", {}).get("url") or \
                    f.get("hdri", {}).get("1k", {}).get("hdr", {}).get("url")
                if u:
                    save(os.path.join(OUT, "sky", key + ".hdr"), http(u, timeout=120))
                    CREDITS.append("- %s sky: Poly Haven HDRI `%s` (CC0) https://polyhaven.com/a/%s" % (key.title(), aid, aid))
                    log("sky %s <- %s" % (key, aid))
                    break
            except Exception as e:      # noqa: BLE001
                log("sky failed", aid, e)


def leaves():
    """Photographed leaf / branch cut-outs (colour + alpha) from Poly Haven tree and plant models."""
    want = [("island_tree_01", ["leaves", "branches"]), ("jacaranda_tree", ["leaves"]), ("shrub_04", ["leaves", "shrub"]),
            ("fern_02", ["fern", ""])]
    got = 0
    for aid, parts in want:
        try:
            files = jget(PH + "files/" + aid)
        except Exception as e:      # noqa: BLE001
            log("leaves: no file list for", aid, e)
            continue
        urls = {}

        def walk(o):
            if isinstance(o, dict):
                if "url" in o and isinstance(o["url"], str):
                    urls[o["url"].rsplit("/", 1)[-1]] = o["url"]
                for v in o.values():
                    walk(v)
        walk(files)
        for part in parts:
            pre = aid + ("_" + part if part else "")
            diff = [n for n in urls if n.startswith(pre + "_diff_1k") and n.endswith((".png", ".jpg"))]
            alpha = [n for n in urls if n.startswith(pre + "_alpha_1k") and n.endswith((".png", ".jpg"))]
            if not diff:
                continue
            d = os.path.join(OUT, "leaves", "%s_%s" % (aid, part or "main"))
            try:
                save(os.path.join(d, "diff" + os.path.splitext(diff[0])[1]), http(urls[diff[0]], timeout=90))
                if alpha:
                    save(os.path.join(d, "alpha" + os.path.splitext(alpha[0])[1]), http(urls[alpha[0]], timeout=90))
                got += 1
                log("leaves %s/%s <- %s %s" % (aid, part, diff[0], alpha[0] if alpha else "(alpha in the colour file)"))
                CREDITS.append("- Leaf texture `%s_%s`: Poly Haven model `%s` (CC0) https://polyhaven.com/a/%s" % (aid, part, aid, aid))
            except Exception as e:      # noqa: BLE001
                log("leaves failed", aid, part, e)
    log("leaf sets:", got)


# ============================================================================================ sounds
COMMONS = "https://commons.wikimedia.org/w/api.php"
OK_LIC = re.compile(r"^(cc0|cc[- ]zero|public domain|pd|cc[- ]by(?![- ]nc)(?![- ]nd)|cc[- ]by[- ]sa|attribution)", re.I)
SR = 44100
NO_MUSIC = ["music", "song", "melody", "remix"]
NO_SYNTH = ["8 bit", "8bit", "8-bit", "chiptune", "synth", "retro", "arcade", "laser", "sci-fi", "scifi", "cartoon", "toy"]
# name: queries, title must contain one of `req`, must not contain `ban`, duration range, seconds kept, options
SOUNDS = {
    # --- vehicles (loops are pitched by the engine revs in the game)
    "engine_car":    dict(q=["car engine idle loop", "car engine running", "petrol engine idle", "car engine interior"],
                          req=["engine", "idle", "motor"], ban=NO_MUSIC + NO_SYNTH + ["start", "starting", "truck", "motorcycle", "boat", "plane"],
                          dur=(3, 600), out=6.0, loop=True, gain=-4, ia="car engine idle"),
    "engine_bike":   dict(q=["motorcycle engine idle", "motorbike idle", "motorcycle running", "royal enfield"],
                          req=["motorcycle", "motorbike", "bike", "enfield", "scooter"], ban=NO_MUSIC + NO_SYNTH + ["bicycle", "start"],
                          dur=(3, 600), out=5.0, loop=True, gain=-4, ia="motorcycle idle"),
    "engine_auto":   dict(q=["auto rickshaw", "tuk tuk", "rickshaw engine", "three wheeler engine"],
                          req=["rickshaw", "tuk", "auto", "three wheel"], ban=NO_MUSIC + NO_SYNTH + ["horn"],
                          dur=(3, 600), out=5.0, loop=True, gain=-4, ia="auto rickshaw"),
    "engine_diesel": dict(q=["diesel engine idle", "truck engine idle", "bus engine idle", "lorry engine"],
                          req=["diesel", "truck", "bus", "lorry", "engine"], ban=NO_MUSIC + NO_SYNTH + ["horn", "brake", "train"],
                          dur=(3, 600), out=6.0, loop=True, gain=-4, ia="diesel engine"),
    "engine_heli":   dict(q=["helicopter flying", "helicopter rotor", "helicopter hover", "helicopter"],
                          req=["helicopter", "rotor", "chopper"], ban=NO_MUSIC + NO_SYNTH + ["toy", "rc "],
                          dur=(3, 600), out=6.0, loop=True, gain=-3, ia="helicopter"),
    "engine_boat":   dict(q=["outboard motor", "motor boat", "speedboat engine", "boat engine"],
                          req=["boat", "outboard", "motor"], ban=NO_MUSIC + NO_SYNTH + ["horn", "toy"],
                          dur=(3, 600), out=6.0, loop=True, gain=-4, ia="motor boat"),
    "horn_car":      dict(q=["car horn", "car horn honk", "horn beep car"], req=["horn", "honk", "beep"],
                          ban=NO_MUSIC + NO_SYNTH + ["air horn", "train", "ship", "truck", "bike", "bicycle"], dur=(0.2, 30), out=0.9, ia="car horn"),
    "horn_truck":    dict(q=["truck horn", "air horn truck", "bus horn", "lorry horn"], req=["horn"],
                          ban=NO_MUSIC + NO_SYNTH + ["train", "ship", "bicycle", "stadium", "party"], dur=(0.3, 30), out=1.6, ia="truck horn"),
    "horn_bike":     dict(q=["motorcycle horn", "scooter horn", "moped horn", "small horn beep"], req=["horn", "beep"],
                          ban=NO_MUSIC + NO_SYNTH + ["train", "ship", "truck"], dur=(0.1, 20), out=0.7, ia="motorcycle horn"),
    "siren":         dict(q=["police siren", "siren passing", "emergency siren", "police car siren"], req=["siren"],
                          ban=NO_MUSIC + NO_SYNTH + ["air raid", "tornado", "fire alarm"], dur=(2, 300), out=6.0, loop=True, gain=-6,
                          ia="police siren"),
    "tyre_screech":  dict(q=["tire screech", "tyre squeal", "car skid", "brakes screech"], req=["tire", "tyre", "skid", "screech", "squeal"],
                          ban=NO_MUSIC + NO_SYNTH, dur=(0.3, 30), out=1.6, ia="tire screech"),
    "crash":         dict(q=["car crash", "car accident", "metal crash", "car impact"], req=["crash", "impact", "accident", "collision", "smash"],
                          ban=NO_MUSIC + NO_SYNTH + ["cymbal", "drum", "glass only"], dur=(0.3, 30), out=1.8, ia="car crash", v=2),
    "car_door":      dict(q=["car door close", "car door slam", "car door"], req=["door"],
                          ban=NO_MUSIC + NO_SYNTH + ["house", "wooden", "creak", "knock"], dur=(0.2, 20), out=1.0, ia="car door"),
    "glass_break":   dict(q=["glass break", "window smash", "glass shatter"], req=["glass", "shatter", "window"],
                          ban=NO_MUSIC + NO_SYNTH + ["clink", "toast", "bottle"], dur=(0.3, 30), out=1.6, ia="glass breaking"),
    "explosion":     dict(q=["explosion", "big explosion", "car explosion", "blast"], req=["explosion", "blast", "explode", "boom"],
                          ban=NO_MUSIC + NO_SYNTH + ["firework", "small"], dur=(0.5, 60), out=3.5, ia="explosion"),
    # --- weapons
    "shot_pistol":   dict(q=["pistol gunshot", "handgun shot", "9mm gunshot", "pistol shot"], req=["pistol", "handgun", "gun", "shot", "9mm"],
                          ban=NO_MUSIC + NO_SYNTH + ["toy", "nerf", "cap gun", "silenced", "laser", "reload"], dur=(0.1, 20), out=0.9, ia="pistol gunshot"),
    "shot_revolver": dict(q=["revolver gunshot", "revolver shot", "magnum shot", "357 magnum"], req=["revolver", "magnum", "gun", "shot"],
                          ban=NO_MUSIC + NO_SYNTH + ["toy", "cap gun", "spin", "reload"], dur=(0.1, 20), out=1.1, ia="revolver shot"),
    "shot_smg":      dict(q=["submachine gun", "machine gun burst", "uzi", "automatic gunfire"],
                          req=["machine", "smg", "uzi", "automatic", "burst", "gunfire", "mp5"], ban=NO_MUSIC + NO_SYNTH + ["toy", "airsoft"],
                          dur=(0.2, 30), out=0.5, single=True, ia="machine gun"),
    "shot_shotgun":  dict(q=["shotgun blast", "shotgun shot", "12 gauge", "shotgun"], req=["shotgun", "gauge"],
                          ban=NO_MUSIC + NO_SYNTH + ["toy", "pump only", "reload"], dur=(0.1, 20), out=1.4, ia="shotgun"),
    "reload":        dict(q=["gun reload", "pistol reload", "magazine insert", "gun cocking"], req=["reload", "magazine", "cock", "clip"],
                          ban=NO_MUSIC + NO_SYNTH + ["toy", "nerf"], dur=(0.2, 20), out=1.4, ia="gun reload"),
    "empty_click":   dict(q=["gun dry fire", "empty gun click", "trigger click"], req=["click", "dry", "empty", "trigger"],
                          ban=NO_MUSIC + NO_SYNTH + ["mouse", "keyboard", "pen", "camera"], dur=(0.05, 10), out=0.4, ia="gun click"),
    "bat_hit":       dict(q=["baseball bat hit", "wood hit body", "bat swing hit", "stick hit"], req=["bat", "hit", "wood", "whack", "smack"],
                          ban=NO_MUSIC + NO_SYNTH + ["ball", "cricket ball", "animal", "flying"], dur=(0.1, 20), out=0.7, ia="bat hit"),
    "knife_slash":   dict(q=["knife slash", "sword slash", "blade swish", "knife stab"], req=["knife", "slash", "stab", "blade", "sword", "swish"],
                          ban=NO_MUSIC + NO_SYNTH + ["sharpen", "chop", "kitchen"], dur=(0.1, 20), out=0.6, ia="knife slash"),
    "swing":         dict(q=["whoosh swing", "swish", "swing whoosh"], req=["whoosh", "swish", "swing"],
                          ban=NO_MUSIC + NO_SYNTH + ["wind", "car", "transition"], dur=(0.1, 20), out=0.5, ia="whoosh"),
    "punch":         dict(q=["body punch", "punch hit", "face punch", "punch"], req=["punch", "hit", "slap", "smack"],
                          ban=NO_MUSIC + NO_SYNTH + ["drum", "keyboard", "snare", "game", "kick", "electronic"],
                          dur=(0.1, 20), out=0.7, ia="punch"),
    "body_fall":     dict(q=["body fall", "body falling ground", "body drop"], req=["body", "fall", "thud", "drop"],
                          ban=NO_MUSIC + NO_SYNTH + ["water", "tree", "rock", "rain"], dur=(0.1, 20), out=1.0, ia="body fall"),
    "bullet_impact": dict(q=["bullet impact", "bullet hit metal", "ricochet", "bullet hit concrete"], req=["bullet", "impact", "ricochet", "hit"],
                          ban=NO_MUSIC + NO_SYNTH, dur=(0.05, 20), out=0.6, ia="bullet impact"),
    # --- people
    "footstep":      dict(q=["footsteps concrete", "footsteps asphalt", "walking on concrete", "footsteps street"],
                          req=["footstep", "foot step", "walking", "steps"], ban=NO_MUSIC + ["snow", "gravel", "grass", "leaves", "horse", "march",
                                                                                           "heels", "crowd", "voice", "rain", "wood"],
                          dur=(2, 400), out=0.4, steps=6, ia="footsteps concrete"),
    "grunt":         dict(q=["man pain grunt", "man hurt", "male grunt pain", "man groan"], req=["grunt", "pain", "hurt", "groan", "ugh", "ouch"],
                          ban=NO_MUSIC + NO_SYNTH + ["woman", "female", "child", "baby", "zombie", "monster"], dur=(0.2, 20), out=1.0, ia="man grunt"),
    "scream":        dict(q=["woman scream", "scream fear", "people screaming panic", "scream"], req=["scream", "shriek", "panic"],
                          ban=NO_MUSIC + NO_SYNTH + ["baby", "monster", "zombie", "laugh", "fun", "game"], dur=(0.3, 30), out=1.8, ia="scream"),
    "crowd_panic":   dict(q=["crowd panic", "crowd screaming running", "people panic"], req=["crowd", "panic", "people", "scream"],
                          ban=NO_MUSIC + NO_SYNTH + ["cheer", "stadium", "applause", "concert"], dur=(1, 120), out=4.0, ia="crowd panic"),
    "splash":        dict(q=["water splash", "jump into water", "big splash"], req=["splash", "water"],
                          ban=NO_MUSIC + NO_SYNTH + ["drip", "rain", "tap"], dur=(0.2, 20), out=1.6, ia="water splash"),
    # --- places
    "amb_city":      dict(q=["india traffic", "indian street ambience", "kolkata traffic", "busy street horns", "city traffic horns"],
                          req=["traffic", "street", "city", "india", "kolkata", "delhi", "horn"],
                          ban=NO_MUSIC + NO_SYNTH + ["siren only", "rain", "night"], dur=(15, 1200), out=40, loop=True, gain=-10, ia="india street traffic"),
    "amb_market":    dict(q=["indian market", "bazaar ambience", "market crowd india", "street market"], req=["market", "bazaar", "crowd", "vendor"],
                          ban=NO_MUSIC + NO_SYNTH + ["cheer", "stadium", "applause"], dur=(15, 1200), out=40, loop=True, gain=-10, ia="indian market"),
    "amb_birds":     dict(q=["birds morning", "crows india", "birds ambience", "tropical birds"], req=["bird", "crow", "chirp", "morning"],
                          ban=NO_MUSIC + NO_SYNTH + ["owl", "night", "parrot talking"], dur=(15, 1200), out=40, loop=True, gain=-12, ia="birds ambience"),
    "amb_night":     dict(q=["crickets night", "night insects", "night ambience frogs"], req=["cricket", "night", "insect", "frog"],
                          ban=NO_MUSIC + NO_SYNTH + ["voice", "speech", "game", "siren"], dur=(15, 1200), out=40, loop=True, gain=-10, ia="crickets night"),
    "amb_sea":       dict(q=["sea waves beach", "ocean waves", "waves on shore"], req=["wave", "sea", "ocean", "surf", "beach"],
                          ban=NO_MUSIC + NO_SYNTH + ["storm", "underwater", "radio", "brain"], dur=(15, 1200), out=40, loop=True, gain=-8, ia="ocean waves"),
    "amb_wind":      dict(q=["wind high altitude", "wind ambience", "strong wind"], req=["wind"], ban=NO_MUSIC + NO_SYNTH + ["chime", "instrument"],
                          dur=(10, 1200), out=30, loop=True, gain=-10, ia="wind"),
    # --- phone / shops / interface
    "cash":          dict(q=["cash register", "coins money", "cash register ching"], req=["cash", "register", "coin", "money", "till"],
                          ban=NO_MUSIC + NO_SYNTH + ["slot machine", "game"], dur=(0.2, 20), out=1.4, ia="cash register"),
    "phone_ring":    dict(q=["phone ringing", "telephone ring", "mobile ringtone"], req=["phone", "ring", "telephone"],
                          ban=NO_MUSIC + NO_SYNTH + ["old", "rotary", "song"], dur=(1, 60), out=3.0, ia="phone ringing"),
    "ui_click":      dict(q=["button click", "switch click", "mouse click soft"], req=["click", "button", "switch", "tap"],
                          ban=NO_MUSIC + NO_SYNTH + ["gun", "pen", "camera shutter"], dur=(0.02, 10), out=0.25, gain=-6, ia="button click"),
    "camera":        dict(q=["camera shutter", "photo camera click"], req=["camera", "shutter", "photo"], ban=NO_MUSIC + NO_SYNTH,
                          dur=(0.05, 10), out=0.6, ia="camera shutter"),
}
# music made and played by people: Freesound uploads from before 2021 (sound ids under 560000), Jamendo tracks from before
# 2021 (track ids under 1700000), ccMixter, Wikimedia Commons; never anything mentioning AI generators.
AI_RE = r"\b(ai|a\.i\.|ai[- ]generated|generated|suno|udio|neural|aiva|mubert|soundraw|boomy)\b"
MUSIC = {
    # the menu: calm, quiet piano by Kevin MacLeod (incompetech.com, CC BY 4.0) - played softly under the title screen
    "music_menu":   dict(v=2, q=["calm piano", "peaceful piano", "ambient piano"], req=["piano", "calm", "peaceful", "ambient"],
                         ban=["vocal", "voice", "speech", "8bit", "chiptune", "dubstep", "horror"], dur=(40, 900), out=180, loop=True, gain=-6,
                         ia="calm piano",
                         direct=[("https://incompetech.com/music/royalty-free/mp3-royaltyfree/Meditation%20Impromptu%2002.mp3",
                                  '"Meditation Impromptu 02" - Kevin MacLeod (incompetech.com), CC BY 4.0 http://creativecommons.org/licenses/by/4.0/'),
                                 ("https://incompetech.com/music/royalty-free/mp3-royaltyfree/Gymnopedie%20No%201.mp3",
                                  '"Gymnopedie No 1" - Kevin MacLeod (incompetech.com), CC BY 4.0 http://creativecommons.org/licenses/by/4.0/'),
                                 ("https://incompetech.com/music/royalty-free/mp3-royaltyfree/Healing.mp3",
                                  '"Healing" - Kevin MacLeod (incompetech.com), CC BY 4.0 http://creativecommons.org/licenses/by/4.0/')]),
    "radio_desi":   dict(q=["bollywood", "indian groove", "tabla groove", "indian dance beat", "bhangra"],
                         req=["bollywood", "india", "indian", "tabla", "bhangra", "desi", "punjabi", "dhol"],
                         ban=["8bit", "8-bit", "chiptune", "meditation", "sleep", "drone only"], dur=(30, 900), out=240, loop=True, gain=-3,
                         ia="bollywood instrumental"),
    "radio_hiphop": dict(q=["hip hop instrumental", "hip hop beat", "boom bap beat", "rap beat instrumental"],
                         req=["hip hop", "hiphop", "hip-hop", "rap", "boom bap", "beat"],
                         ban=["8bit", "8-bit", "chiptune", "vocal", "lyrics", "meditation"], dur=(30, 900), out=240, loop=True, gain=-3,
                         ia="hip hop instrumental"),
    "radio_sitar":  dict(q=["sitar", "indian classical sitar", "sitar music", "raga sitar"], req=["sitar", "raga", "indian classical", "sarod"],
                         ban=["8bit", "8-bit", "chiptune", "synth"], dur=(30, 1500), out=240, loop=True, gain=-3, ia="sitar raga"),
    "music_chase":  dict(q=["action drums", "tense percussion", "chase music", "action percussion loop"],
                         req=["action", "tense", "chase", "percussion", "drum", "suspense"],
                         ban=["8bit", "8-bit", "chiptune", "happy", "comedy", "vocal"], dur=(15, 900), out=90, loop=True, gain=-2,
                         ia="action percussion"),
}
for _m in MUSIC.values():
    _m["ban_re"] = AI_RE
    _m["fs_max_id"] = 560000
    _m["jam_max_id"] = 1700000
    _m["music"] = True
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


def decode_stereo(path):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "2", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy().reshape(-1, 2)


def encode(x, path, quality=4):
    x = np.clip(np.asarray(x, np.float32), -1, 1)
    ch = 1 if x.ndim == 1 else x.shape[1]
    if len(x):
        LEVELS[os.path.basename(path)] = (20 * np.log10(float(np.sqrt(np.mean(x.astype(np.float64) ** 2))) + 1e-9), len(x) / SR)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(ch)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", str(quality), path], check=True)
    os.remove(tmp)


def trim(x, thr=0.01):
    a = np.abs(x) if x.ndim == 1 else np.abs(x).max(1)
    i = np.where(a > thr)[0]
    return x if len(i) == 0 else x[max(0, i[0] - int(0.015 * SR)): i[-1] + int(0.05 * SR)]


def loudest(x, n):
    if len(x) <= n:
        return x
    mono = x if x.ndim == 1 else x.mean(1)
    hop = SR // 4
    e = np.convolve(np.abs(mono), np.ones(hop) / hop, mode="same")[::hop]
    k = max(1, n // hop)
    best = int(np.argmax(np.convolve(e, np.ones(k) / k, mode="valid"))) * hop if len(e) > k else 0
    return x[best: best + n]


def make_loop(x, cross=1.0):
    c = int(cross * SR)
    if len(x) < 3 * c:
        return x
    h = x[: len(x) - c].copy()
    f = np.linspace(0, 1, c, dtype=np.float32)
    if x.ndim > 1:
        f = f[:, None]
    h[:c] = h[:c] * f + x[len(x) - c:] * (1 - f)
    return h


def normalise(x, gain_db=0.0, target=-16.0):
    x = np.asarray(x, np.float32)
    if not len(x):
        return x
    mono = x if x.ndim == 1 else x.mean(1)
    w = int(0.05 * SR)
    n = len(mono) // w
    if n >= 2:
        e = (mono[: n * w].astype(np.float64) ** 2).reshape(n, w).mean(axis=1)
        keep = e >= max(float(np.percentile(e, 30)), float(e.max()) * 1e-5)
        rms = float(np.sqrt(np.median(e[keep])))
    else:
        rms = float(np.sqrt(np.mean(mono.astype(np.float64) ** 2)))
    g = 10 ** ((target + gain_db) / 20) / (rms + 1e-9)
    g = min(g, 1.0 / (float(np.max(np.abs(x))) + 1e-9))
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
MANIFEST = "manifest_v1.json"      # bump to fetch every clip again
FAILS = {"commons": 0, "openverse": 0}


def dead(src):
    return FAILS[src] >= (4 if src == "commons" else 3)


def polite_get(url):
    """Wikimedia asks bots for one request at a time; it throttles cloud machines hard, so give up quickly."""
    if dead("commons"):
        raise RuntimeError("wikimedia is throttling this machine")
    last = None
    for _ in range(3):
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


def first_shot(x, length):
    """The first loud hit of a burst of gunfire, as one shot."""
    hop = int(0.005 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(hop) / hop, mode="same"))
    thr = 0.35 * float(env.max())
    idx = np.where(env > thr)[0]
    if len(idx) == 0:
        return x[: int(length * SR)]
    s = max(0, int(idx[0]) - int(0.004 * SR))
    y = x[s: s + int(length * SR)].copy()
    f = min(len(y) // 3, int(0.12 * SR))
    if f > 0:
        y[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return y


def process(name, spec, path_dir, src_path):
    music = spec.get("music")
    x = decode_stereo(src_path) if music else decode(src_path)
    dur = len(x) / SR
    if not (spec["dur"][0] <= dur <= spec["dur"][1]) or float(np.max(np.abs(x))) < 0.01:
        return False, dur
    outn = int(spec["out"] * SR)
    gain = spec.get("gain", 0.0)
    path = os.path.join(path_dir, name + ".ogg")
    if spec.get("steps"):
        clips = onsets(x, spec["steps"], spec["out"])
        if len(clips) < 3:
            return False, dur
        for i, c in enumerate(clips, 1):
            encode(normalise(c, -4.0), os.path.join(path_dir, "%s_%d.ogg" % (name, i)))
    elif spec.get("single"):
        encode(normalise(first_shot(trim(x), spec["out"]), gain), path)
    elif spec.get("loop"):
        y = loudest(x, outn + SR) if len(x) > outn + SR else x
        encode(normalise(make_loop(y, 1.5 if music else 1.0), gain, -18.0 if music else -16.0), path, 5 if music else 4)
    else:
        y = trim(x)
        y = loudest(y, outn) if len(y) > outn else y.copy()
        f = min(len(y) // 4, int(0.2 * SR))
        if f > 0:
            y[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
        y[:64] *= np.linspace(0, 1, min(64, len(y)), dtype=np.float32)
        encode(normalise(y, gain), path)
    return True, dur


OV_PREF = {"freesound": 0, "jamendo": 1, "ccmixter": 1, "wikimedia_audio": 3}
SOUND_DEADLINE = [time.time() + 30 * 60]


def openverse_fetch(name, spec, tmp, outdir):
    for q in spec["q"][:5]:
        if dead("openverse") or time.time() > SOUND_DEADLINE[0]:
            return None
        time.sleep(1.0)
        params = {"q": q, "license": "cc0,pdm,by,by-sa", "page_size": "20", "mature": "false"}
        if spec.get("music"):
            params["category"] = "music"
        url = "https://api.openverse.org/v1/audio/?" + urllib.parse.urlencode(params)
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
            land = r.get("foreign_landing_url") or ""
            src = r.get("source") or r.get("provider") or ""
            if spec.get("fs_max_id") and src == "freesound":
                mfs = re.search(r"freesound\.org/people/[^/]+/sounds/(\d+)", land)
                if not mfs or int(mfs.group(1)) >= spec["fs_max_id"]:
                    continue
            if spec.get("jam_max_id") and src == "jamendo":
                mj = re.search(r"jamendo\.com/(?:\w+/)?track/(\d+)", land)
                if not mj or int(mj.group(1)) >= spec["jam_max_id"]:
                    continue
            d = (r.get("duration") or 0) / 1000.0
            if d and not (spec["dur"][0] <= d <= spec["dur"][1]):
                continue
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
                srcp = os.path.join(tmp, re.sub(r"\W", "_", name) + "_ov" + ext)
                save(srcp, polite_get(u) if "wikimedia.org" in u else http(u, tries=2, timeout=60))
                ok, dur = process(name, spec, outdir, srcp)
            except Exception as e:      # noqa: BLE001
                log("  skip", r.get("title"), str(e)[:80])
                continue
            if not ok:
                continue
            lic = r["license"].upper() if r.get("license") in ("cc0", "pdm") else (r.get("license") or "").upper().replace("BY", "CC BY")
            lic += (" " + r["license_version"]) if r.get("license_version") and r.get("license") != "pdm" else ""
            REPORT.append("%-13s <- openverse/%s %s | %s | %s | %.1fs" % (name, r.get("source"), r.get("title"), lic, r.get("creator"), dur))
            return "- `%s`: \"%s\" by %s - %s - %s" % (name, r.get("title"), r.get("creator") or "unknown", lic, r.get("foreign_landing_url") or u)
    return None


def archive_fetch(name, spec, tmp, outdir):
    q = '(%s) AND mediatype:(audio) AND (licenseurl:(*publicdomain*) OR licenseurl:(*creativecommons.org/licenses/by/*) OR licenseurl:(*creativecommons.org/licenses/by-sa/*))' % spec["ia"]
    if spec.get("music"):
        q += " AND date:[1900-01-01 TO 2020-12-31]"
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
        meta = md.get("metadata", {})
        lic = meta.get("licenseurl", "")
        title = meta.get("title", ident)
        creator = meta.get("creator", "")
        if isinstance(creator, list):
            creator = ", ".join(creator)
        text = (str(title) + " " + str(meta.get("subject", "")) + " " + str(meta.get("description", ""))).lower()
        if spec.get("ban_re") and re.search(spec["ban_re"], text):
            continue
        files = [f for f in md.get("files", []) if f.get("format") in ("VBR MP3", "Ogg Vorbis", "MP3") and 3000 < int(f.get("size", 0) or 0) < 20_000_000]
        files.sort(key=lambda f: (0 if any(k in f["name"].lower() for k in spec["req"]) else 1, int(f.get("size", 0))))
        for f in files[:3]:
            try:
                srcp = os.path.join(tmp, re.sub(r"\W", "_", name) + "_ia" + os.path.splitext(f["name"])[1])
                save(srcp, http("https://archive.org/download/%s/%s" % (ident, urllib.parse.quote(f["name"])), timeout=90))
                ok, dur = process(name, spec, outdir, srcp)
            except Exception:       # noqa: BLE001
                continue
            if ok:
                REPORT.append("%-13s <- archive.org %s / %s | %s" % (name, ident, f["name"], lic))
                return "- `%s`: %s (%s) - %s - %s https://archive.org/details/%s" % (name, title, f["name"], creator or "unknown", lic, ident)
    return None


def commons_fetch(name, spec, tmp, outdir):
    tried = set()
    t_start = time.time()
    for q in spec["q"]:
        if time.time() - t_start > 100 or dead("commons"):
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
            if spec.get("ban_re") and re.search(spec["ban_re"], t):
                continue
            if not (5000 < r["size"] < 60_000_000) or time.time() - t_start > 100:
                continue
            tried.add(r["url"])
            for u in ([transcoded(r["url"])] if r["size"] > 1_500_000 and not r["url"].lower().endswith(".mp3") else []) + [r["url"]]:
                if not u:
                    continue
                try:
                    srcp = os.path.join(tmp, re.sub(r"\W", "_", name) + os.path.splitext(u)[1])
                    save(srcp, polite_get(u))
                    ok, dur = process(name, spec, outdir, srcp)
                except Exception as e:      # noqa: BLE001
                    log("  skip", r["title"], str(e)[:80])
                    continue
                if ok:
                    REPORT.append("%-13s <- %s | %s | %s | %.1fs" % (name, r["title"], r["lic"], r["author"], dur))
                    return "- `%s`: %s - %s - %s (%s)" % (name, r["title"].replace("File:", ""), r["author"] or "unknown", r["lic"], r["page"])
                break
    return None


def direct_fetch(name, spec, tmp, outdir):
    """Tracks chosen by hand (known artist and licence), tried before any search."""
    for url, credit in spec.get("direct", []):
        try:
            srcp = os.path.join(tmp, re.sub(r"\W", "_", name) + "_direct" + os.path.splitext(url.split("?")[0])[1])
            save(srcp, http(url, timeout=120, ua=BROWSER_UA))
            ok, dur = process(name, spec, outdir, srcp)
        except Exception as e:      # noqa: BLE001
            log("  direct %s: %s" % (url, e))
            continue
        if ok:
            REPORT.append("%-13s <- %s" % (name, credit))
            return "- `%s`: %s" % (name, credit)
    return None


def fetch_one(name, spec, tmp, outdir):
    if time.time() > SOUND_DEADLINE[0]:
        REPORT.append("%-13s <- skipped (time budget)" % name)
        return None
    for fn in (direct_fetch, openverse_fetch, commons_fetch, archive_fetch):
        try:
            c = fn(name, spec, tmp, outdir)
        except Exception as e:      # noqa: BLE001
            log("  %s failed for %s: %s" % (fn.__name__, name, e))
            c = None
        if c:
            return c
        if time.time() > SOUND_DEADLINE[0]:
            break
    REPORT.append("%-13s <- NOTHING FOUND" % name)
    return None


def run_set(table, subdir, credits_name, budget_env, budget_default):
    tmp = tempfile.mkdtemp(prefix="dg_snd_")
    outdir = os.path.join(OUT, subdir)
    os.makedirs(outdir, exist_ok=True)
    SOUND_DEADLINE[0] = time.time() + float(os.environ.get(budget_env, str(budget_default))) * 60
    mpath = os.path.join(outdir, MANIFEST)
    manifest = json.load(open(mpath)) if os.path.exists(mpath) else {}

    def mkey(name, spec):
        return name + ("@v%d" % spec["v"] if spec.get("v") else "")

    for name, spec in table.items():
        first = os.path.join(outdir, name + ("_1" if spec.get("steps") else "") + ".ogg")
        if mkey(name, spec) in manifest and os.path.exists(first):
            log("%-13s kept from the last build" % name)
            continue
        c = fetch_one(name, spec, tmp, outdir)
        log("%-13s %s" % (name, "ok" if c else "MISSING"))
        if c:
            manifest[mkey(name, spec)] = c
            json.dump(manifest, open(mpath, "w"), indent=1)
    REPORT.append("%d of %d %s found" % (sum(1 for n, sp in table.items() if mkey(n, sp) in manifest), len(table), subdir))
    with open(os.path.join(outdir, credits_name), "w") as f:
        f.write("\n".join(manifest[mkey(n, sp)] for n, sp in table.items() if mkey(n, sp) in manifest) + "\n")
    shutil.rmtree(tmp, ignore_errors=True)


def sounds():
    run_set(SOUNDS, "sounds", "CREDITS_SOUNDS.md", "SOUND_BUDGET_MIN", 30)
    snd = lambda n: os.path.join(OUT, "sounds", n + ".ogg")      # noqa: E731
    for a, b in (("shot_revolver", "shot_pistol"), ("shot_pistol", "shot_revolver"), ("horn_bike", "horn_car"),
                 ("horn_truck", "horn_car"), ("engine_auto", "engine_bike"), ("engine_diesel", "engine_car"),
                 ("amb_market", "amb_city"), ("knife_slash", "swing"), ("bat_hit", "punch"), ("crowd_panic", "scream")):
        if not os.path.exists(snd(a)) and os.path.exists(snd(b)):
            shutil.copy(snd(b), snd(a))
    with open(os.path.join(BUILD, "sounds_report.txt"), "a") as f:
        f.write("\n".join(REPORT) + "\n")
    del REPORT[:]


def music():
    run_set(MUSIC, "music", "CREDITS_MUSIC.md", "MUSIC_BUDGET_MIN", 20)
    with open(os.path.join(BUILD, "sounds_report.txt"), "a") as f:
        f.write("\n".join(REPORT) + "\n")
    del REPORT[:]


# ============================================================================================ fonts
FONTS = [("the_bold_font", "The Bold Font", "Sven Pels", "100% Free", "https://www.dafont.com/the-bold-font.font", "DisplayFont"),
         ("bebas_neue", "Bebas Neue", "Dharma Type", "SIL Open Font License", "https://www.dafont.com/bebas-neue.font", "UIFont"),
         ("pricedown", "Pricedown", "Typodermic Fonts", "Typodermic desktop licence (free, commercial use allowed)", "https://www.dafont.com/pricedown.font",
          "TitleFont")]


def fonts():
    d = os.path.join(OUT, "fonts")
    os.makedirs(d, exist_ok=True)
    for key, title, author, lic, page, role in FONTS:
        try:
            data = http("https://dl.dafont.com/dl/?f=" + key, timeout=60, ua=BROWSER_UA)
            z = zipfile.ZipFile(io.BytesIO(data))
            names = [n for n in z.namelist() if n.lower().endswith((".ttf", ".otf")) and not n.startswith("__MACOSX")]
            # prefer a regular / bold TrueType file
            names.sort(key=lambda n: (0 if n.lower().endswith(".ttf") else 1, 0 if re.search(r"(regular|bold)", n, re.I) else 1, len(n)))
            if not names:
                log("font %s: no font file in the zip (%s)" % (key, z.namelist()[:8]))
                continue
            ext = os.path.splitext(names[0])[1].lower()
            save(os.path.join(d, role + ext), z.read(names[0]))
            for n in z.namelist():
                if re.search(r"(licen[cs]e|ofl|readme)", n, re.I) and n.lower().endswith((".txt", ".md")):
                    save(os.path.join(d, role + "_LICENSE.txt"), z.read(n))
                    break
            CREDITS.append("- Font `%s`: %s by %s (%s) - dafont.com %s" % (role, title, author, lic, page))
            log("font %s <- %s (%s)" % (role, names[0], key))
        except Exception as e:      # noqa: BLE001
            log("font failed", key, e)


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"textures": textures, "sky": sky, "leaves": leaves, "sounds": sounds, "music": music, "fonts": fonts}
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
