#!/usr/bin/env python3
"""Chaya - downloads every third-party asset at build time (nothing AI-generated).

    python3 tools/fetch_assets.py rocketbox|fonts|textures|sounds|all

* rocketbox : Microsoft Rocketbox 'Medical_Female_01' avatar + mocap clips (MIT)      -> assets/downloaded/chaya
* fonts     : Creepster (OFL) title font, Noto Sans Devanagari (OFL)                   -> assets/downloaded/fonts
* textures  : photographic PBR materials from Poly Haven / ambientCG (CC0)             -> assets/downloaded/tex/<slot>
* sounds    : real field recordings from Wikimedia Commons (CC0 / public domain / CC-BY / CC-BY-SA)
              cut, normalised and converted to .ogg                                    -> assets/sounds
Everything that was used is listed in build/CREDITS_AUTO.md.
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

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
UA = "ChayaGameBuild/1.0 (https://github.com/arghadeep752-commits/Gamesssssss; GitHub Actions)"
OUT_DL = os.path.join(ROOT, "assets", "downloaded")
OUT_SND = os.path.join(ROOT, "assets", "sounds")
BUILD = os.path.join(ROOT, "build")
os.makedirs(BUILD, exist_ok=True)
CREDITS = []


def log(*a):
    print(*a, flush=True)


def http(url, tries=3, timeout=90):
    last = None
    for k in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:      # noqa: BLE001
            last = e
            time.sleep(1.5 * (k + 1))
    raise RuntimeError("download failed %s: %s" % (url, last))


def jget(url):
    return json.loads(http(url).decode("utf-8", "replace"))


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# ============================================================================================= rocketbox
RB = "https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/"


def rocketbox():
    d = os.path.join(OUT_DL, "chaya")
    base = RB + "Avatars/Professions/Medical_Female_01/"
    save(os.path.join(d, "Medical_Female_01.fbx"), http(base + "Export/Medical_Female_01.fbx"))
    for t in ("body_color", "body_normal", "body_specular", "head_color", "head_normal", "head_specular", "opacity_color"):
        save(os.path.join(d, "tex", "f152_%s.tga" % t), http(base + "Textures/f152_%s.tga" % t))
    anims = {
        "walk": "Animations/all_animations_max_motextr_xy/f_walk_injured.max.fbx",
        "run": "Animations/all_animations_max_motextr_xy/f_run_injured.max.fbx",
        "idle": "Animations/all_animations_max_motextr_static/f_idle_neutral_01.max.fbx",
    }
    for k, p in anims.items():
        save(os.path.join(d, "anims", k + ".fbx"), http(RB + p))
    CREDITS.append("- **Chaya** character + animations: Microsoft Rocketbox Avatar Library (MIT licence), "
                   "https://github.com/microsoft/Microsoft-Rocketbox - 'Medical_Female_01' avatar, walk/run/idle motion-capture clips. "
                   "Skin, eyes, saree colour, blood and hair are re-shaded in-engine.")
    log("rocketbox ok")


# ============================================================================================= fonts
def fonts():
    d = os.path.join(OUT_DL, "fonts")
    for name, urls in {
        "Creepster-Regular.ttf": ["https://raw.githubusercontent.com/google/fonts/main/ofl/creepster/Creepster-Regular.ttf"],
        "NotoSansDevanagari.ttf": [
            "https://raw.githubusercontent.com/google/fonts/main/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth%2Cwght%5D.ttf",
            "https://raw.githubusercontent.com/notofonts/notofonts.github.io/main/fonts/NotoSansDevanagari/hinted/ttf/NotoSansDevanagari-Bold.ttf",
        ],
    }.items():
        for u in urls:
            try:
                data = http(u)
                if len(data) > 10000:
                    save(os.path.join(d, name), data)
                    log("font ok", name)
                    break
            except Exception as e:      # noqa: BLE001
                log("font failed", u, e)
    CREDITS.append("- Fonts: Creepster (SIL OFL, Sideshow), Noto Sans Devanagari (SIL OFL, Google).")


# ============================================================================================= textures
# slot -> (poly haven ids to try first, keywords: must any-of, prefer, avoid, ambientCG search queries)
TEX_SLOTS = {
    "wood_floor": dict(ids=["wood_floor_deck", "old_wood_floor", "wood_planks", "dark_wood", "wood_floor"],
                       must=["wood", "plank", "floor", "parquet"], prefer=["old", "worn", "dark", "plank", "rough", "deck", "weathered"],
                       avoid=["painted", "white", "tile", "bark", "veneer", "cabinet", "table", "wall"], acg=["old wood planks", "wood floor", "planks"]),
    "stone_floor": dict(ids=["concrete_floor_worn_001", "stone_tiles", "rough_concrete", "concrete_floor_02", "floor_tiles_06"],
                        must=["stone", "concrete", "tile", "floor", "slab", "cobble", "rock"], prefer=["worn", "old", "stone", "rough", "slab", "tiles"],
                        avoid=["marble", "wood", "brick", "grass", "roof", "carpet"], acg=["stone tiles", "concrete floor", "old stone"]),
    "wood_wall": dict(ids=["wood_planks_grey", "dark_planks", "old_planks_02", "wood_planks", "brown_planks_03", "wood_plank_wall"],
                      must=["wood", "plank", "board"], prefer=["old", "worn", "dark", "plank", "weathered", "grey", "rough", "wall"],
                      avoid=["painted", "white", "tile", "floor", "parquet", "veneer", "cabinet", "table"], acg=["old wood planks", "weathered wood", "wood planks"]),
    "plaster": dict(ids=["rough_plaster", "beige_wall_001", "plaster_brick_pattern", "painted_plaster_wall", "plaster_grunge", "wall_plaster"],
                    must=["plaster", "stucco", "wall", "concrete", "paint"], prefer=["old", "rough", "plaster", "grunge", "stained", "peeling", "weathered", "beige", "dirty"],
                    avoid=["brick", "tile", "wood", "marble", "metal"], acg=["old plaster", "plaster", "painted plaster"]),
    "wood_ceiling": dict(ids=["wood_planks_dirt", "dark_wood", "old_wood_planks", "wood_planks"],
                         must=["wood", "plank", "board", "beam"], prefer=["old", "dark", "dirt", "plank", "worn", "rough", "weathered"],
                         avoid=["painted", "white", "tile", "floor", "parquet", "veneer"], acg=["dark wood planks", "old wood", "wood planks"]),
    "wood_dark": dict(ids=["dark_wood", "wood_table_001", "old_wood", "wood_cabinet_worn_long"],
                      must=["wood"], prefer=["dark", "old", "worn", "rough", "bark", "grain"],
                      avoid=["painted", "white", "tile", "parquet", "floor"], acg=["dark wood", "old wood", "wood"]),
    "wood_door": dict(ids=["wood_planks_worn", "old_planks", "wood_door", "wooden_planks", "weathered_planks"],
                      must=["wood", "plank", "door"], prefer=["old", "worn", "weathered", "door", "plank", "rough"],
                      avoid=["painted", "white", "tile", "parquet", "floor"], acg=["old wooden door", "weathered wood", "planks"]),
    "brass": dict(ids=["brass_pan_01", "scratched_metal", "brushed_metal"],
                  must=["metal", "brass", "iron", "steel", "copper", "bronze", "plate"], prefer=["brass", "scratched", "brushed", "old", "worn", "gold", "bronze"],
                  avoid=["floor", "rust_", "corrugated", "mesh", "grid", "wire", "diamond", "plate"], acg=["brass", "bronze", "gold", "scratched metal"], acg_first=True),
    "copper": dict(ids=["copper", "oxidized_copper", "scratched_metal"],
                   must=["metal", "copper", "bronze", "iron", "steel", "plate"], prefer=["copper", "bronze", "old", "worn", "oxid", "scratched"],
                   avoid=["floor", "mesh", "grid", "wire", "corrugated", "diamond"], acg=["copper", "bronze", "oxidized metal"], acg_first=True),
    "cloth": dict(ids=["fabric_pattern_07", "cotton", "red_fabric", "fabric_pattern_05", "curtain_fabric", "fabric_pattern_01"],
                  must=["fabric", "cloth", "cotton", "linen", "curtain", "canvas", "burlap", "wool", "woven"], prefer=["fabric", "cotton", "linen", "woven", "cloth", "pattern", "curtain"],
                  avoid=["leather", "carpet", "rug", "denim", "metal", "stone"], acg=["fabric cotton", "woven fabric", "cloth"]),
    "clay": dict(ids=["terracotta", "clay_plaster", "rough_clay", "brown_mud", "mud_cracked_dry_03", "sandy_gravel"],
                 must=["clay", "terracotta", "mud", "plaster", "sand", "earth", "ground", "dry"], prefer=["clay", "terracotta", "mud", "dry", "cracked", "earth"],
                 avoid=["grass", "roof", "tile", "wood", "metal", "snow", "forest"], acg=["terracotta", "clay", "dry mud"]),
    "fiber": dict(ids=["burlap", "jute_fabric", "rope", "straw", "hessian", "woven_rope", "wicker"],
                  must=["burlap", "jute", "rope", "straw", "hessian", "wicker", "fabric", "fiber", "fibre", "woven", "thatch"], prefer=["burlap", "jute", "rope", "straw", "fibre", "fiber", "hessian", "thatch", "wicker"],
                  avoid=["metal", "stone", "plastic", "leather"], acg=["burlap", "rope", "straw"]),
}
PH = "https://api.polyhaven.com/"


def ph_assets():
    return jget(PH + "assets?t=textures")


def ph_pick(slot, spec, assets, used):
    """Candidate poly haven ids for a slot, best first."""
    def score(i):
        a = assets[i]
        text = " ".join([i, a.get("name", "")] + a.get("tags", []) + a.get("categories", [])).lower().replace("_", " ")
        if not any(k in text for k in spec["must"]):
            return -99
        s = sum(2 for k in spec["prefer"] if k in text) - sum(5 for k in spec["avoid"] if k in text)
        return s + min(3, a.get("download_count", 0) / 40000.0)
    explicit = [i for i in spec["ids"] if i in assets]
    ranked = sorted((i for i in assets if i not in explicit and score(i) > 0), key=score, reverse=True)
    return [i for i in explicit if i not in used] + [i for i in ranked if i not in used][:6]


def ph_download(aid, dest):
    files = jget(PH + "files/" + aid)

    def url_of(keys):
        for k in keys:
            if k in files:
                for res in ("2k", "1k"):
                    if res in files[k]:
                        for fmt in ("jpg", "png"):
                            if fmt in files[k][res]:
                                return files[k][res][fmt]["url"], fmt
        return None, None
    du, df = url_of(["Diffuse", "diff", "Color"])
    if not du:
        return False
    save(os.path.join(dest, "diff.jpg" if df == "jpg" else "diff.png"), http(du))
    nu, nf = url_of(["nor_gl", "Normal"])
    if nu:
        save(os.path.join(dest, "nor.jpg" if nf == "jpg" else "nor.png"), http(nu))
    ru, rf = url_of(["Rough", "rough"])
    if ru:
        save(os.path.join(dest, "rough.jpg" if rf == "jpg" else "rough.png"), http(ru))
    return True


def acg_download(queries, dest, spec, used):
    for q in queries:
        try:
            data = jget("https://ambientcg.com/api/v2/full_json?type=Material&sort=Popular&limit=12&include=downloadData&q="
                        + urllib.parse.quote(q))
        except Exception as e:      # noqa: BLE001
            log("  ambientcg query failed", q, e)
            continue
        for a in data.get("foundAssets", []):
            aid = a.get("assetId")
            if aid in used:
                continue
            link = None
            for dl in a.get("downloadFolders", {}).get("default", {}).get("downloadFiletypeCategories", {}).get("zip", {}).get("downloads", []):
                if dl.get("attribute") == "1K-JPG":
                    link = dl.get("fullDownloadPath")
            if not link:
                continue
            try:
                z = zipfile.ZipFile(io.BytesIO(http(link)))
            except Exception as e:      # noqa: BLE001
                log("  ambientcg zip failed", aid, e)
                continue
            names = z.namelist()
            pick = {}
            for n in names:
                low = n.lower()
                if low.endswith("_color.jpg"):
                    pick["diff"] = n
                elif low.endswith("_normalgl.jpg"):
                    pick["nor"] = n
                elif low.endswith("_roughness.jpg"):
                    pick["rough"] = n
            if "diff" not in pick:
                continue
            for k, n in pick.items():
                save(os.path.join(dest, k + ".jpg"), z.read(n))
            return "ambientcg:" + aid
    return None


def textures():
    assets = {}
    try:
        assets = ph_assets()
        log("poly haven textures listed:", len(assets))
    except Exception as e:      # noqa: BLE001
        log("poly haven list failed", e)
    used, chosen = set(), {}
    for slot, spec in TEX_SLOTS.items():
        dest = os.path.join(OUT_DL, "tex", slot)
        shutil.rmtree(dest, ignore_errors=True)
        got = None
        if spec.get("acg_first"):
            got = acg_download(spec["acg"], dest, spec, used)
            if got:
                used.add(got.split(":")[1])
        if assets and not got:
            cands = ph_pick(slot, spec, assets, used)
            log("  candidates", slot, cands)
            for aid in cands:
                try:
                    if ph_download(aid, dest):
                        got = "polyhaven:" + aid
                        used.add(aid)
                        break
                except Exception as e:      # noqa: BLE001
                    log("  polyhaven failed", aid, e)
        if not got:
            got = acg_download(spec["acg"], dest, spec, used)
            if got:
                used.add(got.split(":")[1])
        chosen[slot] = got
        log("texture", slot, "->", got)
    json.dump(chosen, open(os.path.join(BUILD, "textures_chosen.json"), "w"), indent=1)
    for slot, got in chosen.items():
        if not got:
            continue
        src, aid = got.split(":", 1)
        url = ("https://polyhaven.com/a/" + aid) if src == "polyhaven" else ("https://ambientcg.com/view?id=" + aid)
        CREDITS.append("- Texture '%s': %s - %s (CC0)" % (slot, aid, url))
    # contact sheet for a quick visual check
    try:
        from PIL import Image
        tiles = []
        for slot in TEX_SLOTS:
            for ext in ("jpg", "png"):
                p = os.path.join(OUT_DL, "tex", slot, "diff." + ext)
                if os.path.exists(p):
                    tiles.append(Image.open(p).convert("RGB").resize((256, 256)))
                    break
            else:
                tiles.append(Image.new("RGB", (256, 256), (255, 0, 255)))
        sheet = Image.new("RGB", (256 * 6, 256 * 2))
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 6) * 256, (i // 6) * 256))
        sheet.save(os.path.join(BUILD, "textures_contact.jpg"), quality=82)
    except Exception as e:      # noqa: BLE001
        log("contact sheet failed", e)


# ============================================================================================= sounds
COMMONS = "https://commons.wikimedia.org/w/api.php"
OK_LICENSE = re.compile(r"^(cc0|cc[- ]zero|public domain|pd|cc[- ]by(?![- ]nc)|cc[- ]by[- ]sa|attribution)", re.I)

# name -> dict(q = commons search queries, req = title must contain one of these, ban = title must not contain,
#              dur = (min, max) seconds of usable audio, out = seconds to keep, loop = make seamless, steps = cut single events)
SOUNDS = {
    "ambient":       dict(q=["wind ambience", "night ambience", "wind howling", "wind blowing", "empty room tone", "atmosphere ambience"],
                          req=["wind", "ambien", "night", "atmos", "drone", "room"], ban=["music", "song", "voice", "speech"], dur=(15, 600), out=45, loop=True, gain=-4),
    "heartbeat":     dict(q=["heartbeat sound", "heartbeat", "heart beat", "human heartbeat recording", "stethoscope heartbeat", "heart sounds"],
                          req=["heartbeat", "heart beat", "heart_beat", "herzschlag", "heart sound"], ban=["act", "protection", "music", "song", "ecg", "monitor", "bill", "law", "rokita"], dur=(4, 300), out=12, loop=True),
    "footstep":      dict(q=["footsteps wooden floor", "footsteps on wood", "walking on wooden floor", "footsteps indoors", "footsteps", "footstep", "walking"],
                          req=["foot", "step", "walk"], ban=["music", "song", "snow", "gravel", "grass", "stairs", "scream", "growl", "creepy", "run", "horse", "rain", "thunder", "storm"], dur=(2, 300), out=0.55, steps=5),
    "door_open":     dict(q=["door creak", "door creaking", "creaky door", "door opening", "wooden door open"], req=["door", "creak"], ban=["music", "song", "bell", "slam", "knock"], dur=(0.8, 60), out=3.5),
    "door_close":    dict(q=["door close", "door closing", "door slam", "wooden door shut"], req=["door"], ban=["music", "song", "bell", "knock"], dur=(0.3, 60), out=2.0),
    "door_locked":   dict(q=["locked door handle", "door handle rattle", "door knob rattle", "door locked", "door handle"], req=["door", "handle", "knob", "lock", "rattle"], ban=["music", "song", "bell", "slam"], dur=(0.3, 60), out=2.0),
    "creak":         dict(q=["floor creak", "wood creak", "wooden creak", "creaking wood", "creak"], req=["creak"], ban=["music", "song", "door open"], dur=(0.5, 60), out=3.0),
    "knock":         dict(q=["knock on door", "knocking on wood", "door knock", "knocking"], req=["knock"], ban=["music", "song"], dur=(0.5, 60), out=3.0),
    "whisper_far":   dict(q=["whisper", "whispering", "whispers", "woman whispering"], req=["whisper"], ban=["music", "song"], dur=(1, 120), out=6.0, gain=-3),
    "distant_cry":   dict(q=["woman crying", "crying", "weeping", "sobbing", "female scream distant", "scream"], req=["cry", "weep", "sob", "scream", "wail"], ban=["music", "song", "baby", "child", "kid"], dur=(1, 120), out=6.0),
    "jumpscare":     dict(q=["woman screaming", "female scream", "scream", "screaming woman", "horror scream", "shriek"], req=["scream", "shriek", "yell"], ban=["music", "song", "baby", "child", "kid", " male", "boy", "uvb", "radio", "scratch"], dur=(0.6, 60), out=3.0, gain=2),
    "pickup":        dict(q=["singing bowl", "tingsha", "small bell", "hand bell", "bell chime", "tibetan bell"], req=["bell", "chime", "bowl", "tingsha"], ban=["music", "song", "church", "tower", "alarm", "bicycle", "bike", "door", "school", "cow"], dur=(0.5, 60), out=2.4, gain=-2),
    "bell":          dict(q=["Hindu temple bell", "temple bell India", "mandir bell", "aarti", "puja", "ghanta", "temple bells"], req=["temple", "hindu", "india", "puja", "pooja", "aarti", "arati", "ghanta", "ghanti", "mandir"],
                          ban=["music", "song", "church", "alarm", "protestant", "cathedral", "carillon", "chime", "tower", "bicycle", "school", "cow", "door", "pope", "vito", "kirche", "glocke"], dur=(1, 120), out=5.0),
    "ritual_chant":  dict(q=["Om chanting", "Hindu chanting", "mantra chanting", "Vedic chant", "Gayatri mantra", "bhajan", "Sanskrit chant", "Hare Krishna chant", "chanting"],
                          req=["chant", "mantra", "om ", "om_", "vedic", "gayatri", "sloka", "shloka", "stotra", "bhajan", "kirtan", "aarti", "arati", "hymn"], ban=["gregorian", "christian"], dur=(10, 900), out=40, loop=True, gain=-2),
    "ritual_end":    dict(q=["thunder", "thunderclap", "thunder crack", "explosion distant", "whoosh"], req=["thunder", "explosion", "whoosh", "blast", "boom"], ban=["music", "song"], dur=(1, 120), out=6.0),
    "fire":          dict(q=["fire crackling", "campfire", "fireplace", "burning wood", "fire"], req=["fire", "flame", "burn", "crackl"], ban=["music", "song", "alarm", "truck", "engine", "siren", "bones", "ice", "breaking", "gun"], dur=(8, 900), out=25, loop=True, gain=-4),
    "menu_music":    dict(q=["tanpura", "tambura drone", "dark ambient drone", "drone", "sitar"], req=["tanpura", "tambura", "drone", "sitar", "ambient"], ban=["song"], dur=(15, 900), out=50, loop=True, gain=-3),
    "menu_start":    dict(q=["gong", "temple gong", "door slam heavy", "big gong"], req=["gong", "slam"], ban=["music", "song"], dur=(1, 60), out=4.0),
    "ui_click":      dict(q=["click sound", "button click", "switch click", "light switch", "mouse click", "click"], req=["click", "switch"], ban=["music", "song", "double", "kragen"], dur=(0.05, 5), out=0.4),
}
SR = 44100
GLOBAL_BAN = re.compile(r"^file:(ll-|[a-z]{2,3}(-[a-z]{2,4})?-)|speech|interview|lecture|podcast|senator|congress|c-span|parliament|news|uvb|album| - 0\d|pronunciation", re.I)


def commons_search(q, limit=40):
    p = {
        "action": "query", "format": "json", "generator": "search", "gsrnamespace": "6", "gsrlimit": str(limit),
        "gsrsearch": q + " filetype:audio", "prop": "imageinfo", "iiprop": "url|size|mime|mediatype",
        "iiextmetadatafilter": "LicenseShortName|Artist|Credit|ObjectName", "iiextmetadatamultilang": "0",
    }
    p["iiprop"] += "|extmetadata"
    data = jget(COMMONS + "?" + urllib.parse.urlencode(p))
    out = []
    for pg in data.get("query", {}).get("pages", {}).values():
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
    """audio file -> float32 mono array @ 44.1 kHz"""
    cmd = ["ffmpeg", "-v", "error", "-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32).copy()


def encode(x, out_path, stereo=False):
    x = np.clip(x, -1.0, 1.0)
    pcm = (x * 32767).astype("<i2")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    tmp = out_path + ".tmp.wav"
    with wave.open(tmp, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-c:a", "libvorbis", "-q:a", "4", out_path], check=True)
    os.remove(tmp)


def trim_silence(x, thr=0.01):
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x
    return x[max(0, idx[0] - int(0.02 * SR)): idx[-1] + int(0.05 * SR)]


def loudest_window(x, n):
    if len(x) <= n:
        return x
    hop = SR // 2
    env = np.convolve(np.abs(x), np.ones(hop) / hop, mode="same")[::hop]
    best = int(np.argmax(np.convolve(env, np.ones(max(1, n // hop)) / max(1, n // hop), mode="valid"))) * hop if len(env) > n // hop else 0
    return x[best: best + n]


def make_loop(x, cross=1.0):
    c = int(cross * SR)
    if len(x) < c * 3:
        return x
    head = x[: len(x) - c].copy()
    fade = np.linspace(0, 1, c).astype(np.float32)
    head[:c] = head[:c] * fade + x[len(x) - c:] * (1 - fade)
    return head


def normalise(x, gain_db=0.0, peak=0.89):
    m = float(np.max(np.abs(x)) or 1.0)
    x = x / m * peak
    return x * (10 ** (gain_db / 20.0))


def cut_steps(x, count, length):
    """Find single footsteps (onsets) in a long recording and return up to `count` clips."""
    hop = int(0.01 * SR)
    env = np.sqrt(np.convolve(x * x, np.ones(hop) / hop, mode="same"))[::hop]
    thr = np.percentile(env, 92)
    clips, last = [], -10 ** 9
    for i in range(2, len(env) - 2):
        if env[i] >= thr and env[i] >= env[i - 1] and env[i] > env[i + 1] and i - last > 35:
            last = i
            s = max(0, i * hop - int(0.04 * SR))
            seg = x[s: s + int(length * SR)]
            if len(seg) == int(length * SR):
                clips.append(seg)
    clips.sort(key=lambda s: -float(np.max(np.abs(s))))
    clips = clips[: count * 2]
    clips = sorted(clips, key=lambda s: float(np.max(np.abs(s))))[: count]
    out = []
    for s in clips:
        s = s.copy()
        s[-int(0.1 * SR):] *= np.linspace(1, 0, int(0.1 * SR)).astype(np.float32)
        out.append(s)
    return out


def layer_whispers(x, out_path, seconds=24.0, layers=9):
    """A dense, distant whisper bed made only from the real whisper recording: time-shifted, slightly re-pitched
    copies, low-passed and smeared with a simple room echo."""
    rng = np.random.default_rng(7)
    n = int(seconds * SR)
    bed = np.zeros(n + SR * 4, np.float32)
    x = trim_silence(x)
    for k in range(layers):
        rate = rng.uniform(0.82, 1.08)
        idx = np.arange(0, len(x) - 1, rate)
        y = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
        if rng.random() < 0.5:
            y = y[::-1].copy()      # reversed copies blur the words
        for _ in range(3):
            start = int(rng.uniform(0, n))
            seg = y * rng.uniform(0.25, 0.8)
            end = min(len(bed), start + len(seg))
            bed[start:end] += seg[: end - start]
    # one-pole low-pass + a couple of echoes
    a = 0.18
    for i in range(1, len(bed)):
        bed[i] = bed[i - 1] + a * (bed[i] - bed[i - 1])
    for d, g in ((int(0.083 * SR), 0.45), (int(0.21 * SR), 0.3), (int(0.47 * SR), 0.18)):
        bed[d:] += bed[:-d] * g
    bed = make_loop(bed[: n + SR], 1.0)
    encode(normalise(bed, -6.0), out_path)


def fetch_sound(name, spec, tmp):
    """Search Commons for one sound, process the first recording that passes the filters. -> (report, credit)"""
    tried = set()
    for q in spec["q"]:
        try:
            res = commons_search(q)
        except Exception as e:      # noqa: BLE001
            log("search failed", q, e)
            continue
        for r in res:
            t = r["title"].lower()
            if r["url"] in tried:
                continue
            if not OK_LICENSE.match(r["lic"] or ""):
                continue
            if not any(k in t for k in spec["req"]) or any(k in t for k in spec["ban"]) or GLOBAL_BAN.search(t):
                continue
            if not (6000 < r["size"] < 15_000_000) or r["mime"] not in ("audio/ogg", "audio/wav", "audio/x-wav", "audio/flac", "audio/mpeg", "application/ogg", "audio/x-flac", "audio/mp3"):
                continue
            tried.add(r["url"])
            try:
                src = os.path.join(tmp, "src_" + re.sub(r"\W", "_", name) + os.path.splitext(r["url"])[1])
                save(src, http(r["url"]))
                x = decode(src)
            except Exception as e:      # noqa: BLE001
                log("  skip", r["title"], e)
                continue
            dur = len(x) / SR
            lo, hi = spec["dur"]
            if dur < lo or dur > hi or float(np.max(np.abs(x)) if len(x) else 0) < 0.01:
                continue
            x = trim_silence(x) if not spec.get("loop") else x
            gain = spec.get("gain", 0.0)
            outlen = int(spec["out"] * SR)
            if spec.get("steps"):
                clips = cut_steps(x, spec["steps"], spec["out"])
                if len(clips) < 3:
                    continue
                for i, c in enumerate(clips, 1):
                    encode(normalise(c, -3.0), os.path.join(OUT_SND, "%s_%d.ogg" % (name, i)))
            else:
                if spec.get("loop"):
                    x = make_loop(loudest_window(x, outlen + SR) if len(x) > outlen + SR else x)
                else:
                    x = loudest_window(x, outlen) if len(x) > outlen else x
                    fo = min(len(x) // 4, int(0.25 * SR))
                    x[-fo:] *= np.linspace(1, 0, fo).astype(np.float32)
                    x[:64] *= np.linspace(0, 1, 64).astype(np.float32)
                encode(normalise(x, gain), os.path.join(OUT_SND, name + ".ogg"))
            line = "%-14s <- %s | %s | %s | %.1fs | q='%s'" % (name, r["title"], r["lic"], r["author"], dur, q)
            credit = "- Sound '%s': %s - %s - %s (%s)" % (name, r["title"].replace("File:", ""), r["author"] or "unknown author", r["lic"], r["page"])
            log("sound", line)
            return line, credit
    log("sound", name, "NOTHING FOUND")
    return "%-14s <- NOTHING FOUND" % name, None


def distant_shriek(x, out_path):
    """'Spotted' sting: the start of the real scream recording, pitched down a little, with a room echo."""
    x = trim_silence(x)[: int(1.4 * SR)]
    idx = np.arange(0, len(x) - 1, 0.86)
    y = np.interp(idx, np.arange(len(x)), x).astype(np.float32)
    y = np.concatenate([y, np.zeros(int(0.8 * SR), np.float32)])
    for d, g in ((int(0.11 * SR), 0.5), (int(0.27 * SR), 0.32), (int(0.52 * SR), 0.18)):
        y[d:] += y[:-d] * g
    fo = int(0.3 * SR)
    y[-fo:] *= np.linspace(1, 0, fo).astype(np.float32)
    encode(normalise(y, -1.0), out_path)


def sounds():
    from concurrent.futures import ThreadPoolExecutor
    tmp = tempfile.mkdtemp(prefix="chaya_snd_")
    with ThreadPoolExecutor(max_workers=6) as ex:
        results = list(ex.map(lambda kv: fetch_sound(kv[0], kv[1], tmp), SOUNDS.items()))
    report = [r for r, _ in results]
    CREDITS.extend(c for _, c in results if c)
    snd = lambda n: os.path.join(OUT_SND, n + ".ogg")      # noqa: E731
    # derived sounds - made only from the real recordings above
    if os.path.exists(snd("whisper_far")):
        try:
            layer_whispers(decode(snd("whisper_far")), snd("ghost_whisper"))
            report.append("ghost_whisper  <- layered from the whisper_far recording")
        except Exception as e:      # noqa: BLE001
            log("layering failed", e)
    if os.path.exists(snd("jumpscare")):
        try:
            distant_shriek(decode(snd("jumpscare")), snd("spotted"))
            report.append("spotted        <- the jumpscare scream, pitched down with an echo")
        except Exception as e:      # noqa: BLE001
            log("shriek failed", e)
    open(os.path.join(BUILD, "sounds_report.txt"), "w").write("\n".join(report) + "\n")
    # fall backs so the game is never silent for something important
    for a, b in (("door_locked", "door_close"), ("spotted", "jumpscare"), ("whisper_far", "ghost_whisper"),
                 ("distant_cry", "jumpscare"), ("knock", "door_close"), ("creak", "door_open"), ("bell", "pickup")):
        if not os.path.exists(snd(a)) and os.path.exists(snd(b)):
            shutil.copy(snd(b), snd(a))
    if not os.path.exists(snd("menu_sting")) and os.path.exists(snd("spotted")):
        shutil.copy(snd("spotted"), snd("menu_sting"))
    shutil.rmtree(tmp, ignore_errors=True)


# ============================================================================================= main
if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    steps = {"rocketbox": rocketbox, "fonts": fonts, "textures": textures, "sounds": sounds}
    todo = list(steps) if what == "all" else [what]
    for s in todo:
        log("=== %s ===" % s)
        try:
            steps[s]()
        except Exception as e:      # noqa: BLE001
            log("STEP FAILED:", s, repr(e))
            if s == "rocketbox":
                raise
    with open(os.path.join(BUILD, "CREDITS_AUTO.md"), "a") as f:
        f.write("\n".join(CREDITS) + "\n")
    log("done")
