#!/usr/bin/env python3
"""
Downloads the real (human made, not AI generated) assets for Scary Aunty.
Runs inside GitHub Actions before Godot imports the project.

  * Chalk font ............ dafont.com ("Chalkboard" by Florence S, 100% free)
  * Wall / floor / door ... your own photos in assets/user_textures/ if present,
                            otherwise real photo-scanned CC0 textures (Poly Haven / ambientCG)
  * Sounds ................ real recorded CC0 sounds (Kenney.nl audio packs)
  * Music ................. Kevin MacLeod (incompetech.com), CC-BY 4.0
  * 3D models ............. Sketchfab (free CC0 / CC-BY models), needs the
                            SKETCHFAB_API_TOKEN secret in GitHub

Nothing here is required: if a download fails the game uses its fallback.
"""
import glob
import io
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import zipfile

import numpy as np
import requests
from PIL import Image, ImageFilter

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ASSETS = os.path.join(ROOT, "assets")
CACHE = os.path.expanduser(os.environ.get("ASSET_CACHE", "~/.cache/scary_aunty_assets"))
UA = {"User-Agent": "ScaryAuntyBuild/1.0 (GitHub Actions; Godot game asset fetch)"}
REPORT = {"font": None, "textures": {}, "sounds": {}, "music": {}, "models": {}, "notes": []}
CREDITS = []

os.makedirs(CACHE, exist_ok=True)


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------ helpers

def http_get(url, headers=None, timeout=90, tries=3):
    h = dict(UA)
    if headers:
        h.update(headers)
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                return r
            last = "HTTP %s" % r.status_code
            if r.status_code in (401, 403, 404):
                break
        except Exception as e:  # noqa
            last = str(e)
        time.sleep(2 + i * 3)
    log("   ! download failed:", url, "->", last)
    return None


def cached_download(url, name, headers=None):
    path = os.path.join(CACHE, name)
    if os.path.exists(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            return f.read()
    r = http_get(url, headers)
    if r is None:
        return None
    with open(path, "wb") as f:
        f.write(r.content)
    return r.content


def is_zip(data):
    return data is not None and data[:2] == b"PK"


def ensure(d):
    os.makedirs(d, exist_ok=True)
    return d


def save_image(img, path, max_size):
    img = img.convert("RGB")
    if max(img.size) > max_size:
        img.thumbnail((max_size, max_size), Image.LANCZOS)
    img.save(path, quality=90)


def res_path(abs_path):
    rel = os.path.relpath(abs_path, ROOT).replace(os.sep, "/")
    return "res://" + rel


# ------------------------------------------------------------------ font

def fetch_font():
    log("== Chalk font (dafont)")
    out = os.path.join(ensure(os.path.join(ASSETS, "fonts")), "chalk.ttf")
    sources = [
        ("https://dl.dafont.com/dl/?f=chalkboard_3", "Chalkboard by Florence S (dafont.com, 100% free)"),
        ("https://dl.dafont.com/dl/?f=chalk_clouds", "Chalk Clouds (dafont.com, 100% free)"),
    ]
    for url, credit in sources:
        data = cached_download(url, "font_" + re.sub(r"\W", "_", url) + ".zip")
        if not is_zip(data):
            continue
        z = zipfile.ZipFile(io.BytesIO(data))
        fonts = [n for n in z.namelist() if n.lower().endswith((".ttf", ".otf")) and not n.startswith("__MACOSX")]
        if not fonts:
            continue
        fonts.sort(key=lambda n: (("bold" in n.lower()), len(n)))
        with open(out, "wb") as f:
            f.write(z.read(fonts[0]))
        REPORT["font"] = credit
        CREDITS.append("Font: " + credit)
        log("   ok:", credit, "->", fonts[0])
        return
    # Last resort (not dafont): an open-licence sketch font from Google Fonts.
    data = cached_download("https://raw.githubusercontent.com/google/fonts/main/ofl/cabinsketch/CabinSketch-Regular.ttf", "cabinsketch.ttf")
    if data and len(data) > 10000:
        with open(out, "wb") as f:
            f.write(data)
        REPORT["font"] = "Cabin Sketch (Google Fonts, OFL) - dafont download failed"
        CREDITS.append("Font: Cabin Sketch by Pablo Impallari (SIL Open Font License)")
        REPORT["notes"].append("dafont download failed, used Cabin Sketch instead")


# ------------------------------------------------------------------ textures

TEXTURE_SLOTS = {
    # slot: (poly haven slugs..., ambientCG ids..., poly haven category)
    "wall": (["beige_wall_001", "beige_wall_002", "painted_plaster_wall"], ["Plaster001", "PaintedPlaster017"], "wall"),
    "floor": (["laminate_floor_02", "wood_floor_worn", "wood_floor_deck"], ["WoodFloor041", "WoodFloor051"], "floor"),
    "door": (["dark_wood", "wood_planks", "brown_planks_04"], ["Wood049", "Wood066"], "wood"),
    "wood": (["fine_grained_wood", "wood_planks", "dark_wood"], ["Wood049", "Wood051"], "wood"),
    "ground": (["aerial_grass_rock", "grass_path_2", "forrest_ground_01"], ["Grass001", "Grass004"], "grass"),
}
TEXTURE_SIZE = {"wall": 1024, "floor": 1024, "door": 1024, "wood": 512, "ground": 1024}


def user_texture(slot):
    for ext in ("jpg", "jpeg", "png", "webp"):
        cands = glob.glob(os.path.join(ASSETS, "user_textures", "%s.%s" % (slot, ext)))
        cands += glob.glob(os.path.join(ASSETS, "user_textures", "%s.%s" % (slot, ext.upper())))
        if cands:
            return cands[0]
    return None


def make_normal_and_rough(img):
    """Simple normal + roughness maps from a photo (for your own textures)."""
    g = np.asarray(img.convert("L").filter(ImageFilter.GaussianBlur(1.2)), dtype=np.float32) / 255.0
    dx = np.roll(g, -1, axis=1) - np.roll(g, 1, axis=1)
    dy = np.roll(g, -1, axis=0) - np.roll(g, 1, axis=0)
    strength = 2.5
    nx, ny, nz = -dx * strength, dy * strength, np.ones_like(g)
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / ln, ny / ln, nz / ln], axis=-1)
    normal = Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8), "RGB")
    lo, hi = np.percentile(g, 2), np.percentile(g, 98)
    t = np.clip((g - lo) / max(hi - lo, 1e-3), 0, 1)
    rough = Image.fromarray(((0.9 - 0.35 * t) * 255).astype(np.uint8), "L").convert("RGB")
    return normal, rough


def polyhaven(slug, folder, slot, size):
    base = "https://dl.polyhaven.org/file/ph-assets/Textures/jpg/1k/%s/%s_%s_1k.jpg"
    maps = {"albedo": "diff", "normal": "nor_gl", "roughness": "rough"}
    got = {}
    for key, suffix in maps.items():
        data = cached_download(base % (slug, slug, suffix), "ph_%s_%s.jpg" % (slug, suffix))
        if data is None or data[:2] != b"\xff\xd8":
            got = None
            break
        got[key] = data
    if got is None:
        r = http_get("https://api.polyhaven.com/files/" + slug)
        if r is None:
            return None
        try:
            files = r.json()
            keys = {"albedo": "Diffuse", "normal": "nor_gl", "roughness": "Rough"}
            got = {}
            for key, k in keys.items():
                url = files[k]["1k"]["jpg"]["url"]
                data = cached_download(url, "ph_api_%s_%s.jpg" % (slug, k))
                if data is None:
                    return None
                got[key] = data
        except Exception as e:  # noqa
            log("   ! poly haven api parse failed:", slug, e)
            return None
    out = {}
    for key, data in got.items():
        p = os.path.join(folder, "%s_%s.jpg" % (slot, key))
        save_image(Image.open(io.BytesIO(data)), p, size)
        out[key] = res_path(p)
    out["source"] = "Poly Haven: %s (CC0)" % slug
    return out


def ambientcg(asset_id, folder, slot, size):
    data = cached_download("https://ambientcg.com/get?file=%s_1K-JPG.zip" % asset_id, "acg_%s.zip" % asset_id)
    if not is_zip(data):
        return None
    z = zipfile.ZipFile(io.BytesIO(data))
    names = z.namelist()

    def find(tag):
        for n in names:
            if tag.lower() in n.lower() and n.lower().endswith((".jpg", ".png")):
                return n
        return None

    pick = {"albedo": find("_Color"), "normal": find("_NormalGL"), "roughness": find("_Roughness")}
    if not pick["albedo"]:
        return None
    out = {}
    for key, n in pick.items():
        if not n:
            continue
        p = os.path.join(folder, "%s_%s.jpg" % (slot, key))
        save_image(Image.open(io.BytesIO(z.read(n))), p, size)
        out[key] = res_path(p)
    out["source"] = "ambientCG: %s (CC0)" % asset_id
    return out


def polyhaven_category(cat):
    r = http_get("https://api.polyhaven.com/assets?type=textures&categories=" + urllib.parse.quote(cat))
    if r is None:
        return []
    try:
        data = r.json()
        return sorted(data.keys(), key=lambda k: -int(data[k].get("download_count", 0)))[:4]
    except Exception:  # noqa
        return []


def fetch_textures():
    log("== Textures")
    folder = ensure(os.path.join(ASSETS, "textures"))
    table = {}
    for slot, (ph_slugs, acg_ids, cat) in TEXTURE_SLOTS.items():
        size = TEXTURE_SIZE.get(slot, 1024)
        user = user_texture(slot)
        if user:
            img = Image.open(user)
            p = os.path.join(folder, "%s_albedo.jpg" % slot)
            save_image(img, p, size)
            img = Image.open(p)
            normal, rough = make_normal_and_rough(img)
            pn = os.path.join(folder, "%s_normal.jpg" % slot)
            pr = os.path.join(folder, "%s_roughness.jpg" % slot)
            normal.save(pn, quality=92)
            rough.save(pr, quality=92)
            table[slot] = {"albedo": res_path(p), "normal": res_path(pn), "roughness": res_path(pr),
                           "source": "Your own texture (%s)" % os.path.basename(user), "user": True}
            log("   %s: your own image %s" % (slot, os.path.basename(user)))
            continue
        result = None
        for slug in ph_slugs:
            result = polyhaven(slug, folder, slot, size)
            if result:
                break
        if not result:
            for aid in acg_ids:
                result = ambientcg(aid, folder, slot, size)
                if result:
                    break
        if not result:
            for slug in polyhaven_category(cat):
                result = polyhaven(slug, folder, slot, size)
                if result:
                    break
        if result:
            table[slot] = result
            log("   %s: %s" % (slot, result["source"]))
            CREDITS.append("Texture (%s): %s" % (slot, result["source"]))
        else:
            log("   %s: FAILED (game uses a plain colour)" % slot)
            REPORT["notes"].append("texture %s missing" % slot)
    with open(os.path.join(folder, "textures.json"), "w") as f:
        json.dump(table, f, indent=1)
    REPORT["textures"] = {k: v.get("source") for k, v in table.items()}


# ------------------------------------------------------------------ sounds

KENNEY_PACKS = {
    # pack: GitHub copies (CC0) used if the kenney.nl download link is not found
    "impact-sounds": ["https://github.com/Loppansson/kenney-impact-sounds-for-godot/archive/999dd1684873f8b020a3aa5b26e713da21688924.zip",
                      "https://github.com/Loppansson/kenney-impact-sounds-for-godot/archive/0dd04139bb9e1a3477afd4f26434efdc6d86aac5.zip"],
    "rpg-audio": ["https://github.com/Loppansson/kenney-rpg-audio-for-godot/archive/214a7dabca3594f933e96133b6cf66dddc5771ef.zip",
                  "https://github.com/Loppansson/kenney-rpg-audio-for-godot/archive/22eb79bb843bbcadcaa6ed119353a33265ffad11.zip"],
    "interface-sounds": ["https://github.com/Calinou/kenney-interface-sounds/archive/ad144fc2dd079cdd728bc8c7fcf9c4e64a7a7f83.zip"],
    "music-jingles": [],
}
## Sounds kept in the repo (ci/sounds): Unity Standard Assets footsteps + CC0 Freesound recordings.
LOCAL_SOUNDS = {
    "step_wood": ("unity_footstep_*.wav", "Footsteps: Footstep01-04 from Unity Standard Assets (FirstPersonCharacter), Unity Technologies, Unity Asset Store EULA"),
    "locked": ("freesound_door_rattle_*.wav", "Locked door rattles: EpicWizard, TRP and MarcusGraham325 on freesound.org (CC0)"),
    "drawer": ("freesound_drawer_slide.ogg", "Drawer: \"Drawer Opening & Closing\" by quantumriver on freesound.org (CC0)"),
}
SOUND_MAP = {
    # game name: list of filename patterns (first pattern that matches wins)
    "step_wood": ["footstep_wood_*", "footstep_carpet_*", "footstep0*"],
    "aunty_step": ["footstep0*", "footstep_concrete_*", "footstep_wood_*"],
    "door_open": ["dooropen_*"],
    "door_close": ["doorclose_*"],
    "creak": ["creak*"],
    "locked": ["metallatch*", "impactmetal_light_*"],
    "unlock": ["metalclick*", "impactmetal_light_*"],
    "pickup": ["handlesmallleather*", "cloth*", "impactsoft_medium_*"],
    "drawer": ["impactwood_light_*", "creak*"],
    "break_metal": ["impactmetal_heavy_*", "impactplate_heavy_*"],
    "break_wood": ["impactwood_heavy_*", "impactplank_medium_*"],
    "cut": ["impactmetal_medium_*", "impacttin_medium_*"],
    "beep": ["click_00*", "tick_00*", "click*"],
    "click": ["select_00*", "click_00*", "click*"],
    "wrong": ["error_00*", "error*"],
    "right": ["confirmation_00*", "confirmation*"],
    "paper": ["bookflip*", "bookopen*"],
    "caught": ["impactpunch_heavy_*"],
    "sting": ["jingles_hit0*", "impactbell_heavy_*"],
    "win": ["jingles_pizzi0*", "jingles_sax0*", "confirmation_00*", "confirmation*"],
    "lose": ["jingles_steel0*", "jingles_nes0*", "impactbell_heavy_*"],
}
MUSIC = {
    "music_bgm": ["Sneaky Snitch", "Investigations", "Comfortable Mystery 4"],
    "music_chase": ["Run Amok", "Hitman", "Volatile Reaction"],
}


def kenney_pack(slug):
    page = http_get("https://kenney.nl/assets/" + slug, tries=1)
    urls = []
    if page is not None:
        urls = re.findall(r'https://kenney\.nl/media/pages/assets/%s/[^"\'\s]+?\.zip' % re.escape(slug), page.text)
        rel = re.findall(r'(/media/pages/assets/%s/[^"\'\s]+?\.zip)' % re.escape(slug), page.text)
        urls += ["https://kenney.nl" + u for u in rel]
    urls += KENNEY_PACKS.get(slug, [])
    for i, u in enumerate(urls):
        data = cached_download(u, "kenney_%s_%d.zip" % (slug, i))
        if is_zip(data):
            return data
    return None


def fetch_sounds():
    log("== Sounds (Kenney, CC0 real recordings)")
    folder = ensure(os.path.join(ASSETS, "sounds"))
    pool = {}  # lower basename -> (zip, member)
    for slug in KENNEY_PACKS.keys():
        data = kenney_pack(slug)
        if data is None:
            log("   ! pack missing:", slug)
            REPORT["notes"].append("Kenney pack %s missing" % slug)
            continue
        z = zipfile.ZipFile(io.BytesIO(data))
        n = 0
        for m in z.namelist():
            if m.lower().endswith((".ogg", ".wav")) and "__macosx" not in m.lower():
                pool.setdefault(os.path.basename(m).lower(), (z, m))
                n += 1
        log("   pack %s: %d sounds" % (slug, n))
        CREDITS.append("Sounds: Kenney - %s (kenney.nl, CC0)" % slug)
    table = {}
    for name, patterns in SOUND_MAP.items():
        chosen = []
        for pat in patterns:
            rx = re.compile("^" + re.escape(pat.lower()).replace("\\*", ".*") + r"\.(ogg|wav)$")
            chosen = sorted(k for k in pool if rx.match(k))
            if chosen:
                break
        paths = []
        for i, k in enumerate(chosen[:8]):
            z, m = pool[k]
            p = os.path.join(folder, "%s_%d%s" % (name, i, os.path.splitext(k)[1]))
            with open(p, "wb") as f:
                f.write(z.read(m))
            paths.append(res_path(p))
        if name in LOCAL_SOUNDS:
            pat, credit = LOCAL_SOUNDS[name]
            local = sorted(glob.glob(os.path.join(ROOT, "ci", "sounds", pat)))
            if local:
                paths = []
                for i, src in enumerate(local):
                    p = os.path.join(folder, "%s_local_%d%s" % (name, i, os.path.splitext(src)[1]))
                    shutil.copyfile(src, p)
                    paths.append(res_path(p))
                CREDITS.append(credit)
        if paths:
            table[name] = paths
        REPORT["sounds"][name] = len(paths)
    log("== Music (Kevin MacLeod, CC-BY 4.0)")
    for name, titles in MUSIC.items():
        for title in titles:
            url = "https://incompetech.com/music/royalty-free/mp3-royaltyfree/%s.mp3" % urllib.parse.quote(title)
            data = cached_download(url, "music_%s.mp3" % re.sub(r"\W", "_", title))
            if data and len(data) > 200000 and (data[:3] == b"ID3" or data[0] == 0xFF):
                p = os.path.join(folder, "%s.mp3" % name)
                with open(p, "wb") as f:
                    f.write(data)
                table[name] = [res_path(p)]
                REPORT["music"][name] = title
                CREDITS.append('Music: "%s" Kevin MacLeod (incompetech.com), licensed under Creative Commons: By Attribution 4.0 - '
                               'http://creativecommons.org/licenses/by/4.0/' % title)
                log("   %s: %s" % (name, title))
                break
    with open(os.path.join(folder, "sounds.json"), "w") as f:
        json.dump(table, f, indent=1)


# ------------------------------------------------------------------ Sketchfab models

API = "https://api.sketchfab.com/v3"


def sf_headers(token):
    return {"Authorization": "Token " + token}


def sf_search(token, query, cfg):
    results = []
    for lic in ("cc0", "by"):
        params = {
            "type": "models", "q": query, "downloadable": "true", "license": lic,
            "archives_max_size": int(cfg.get("max_mb", 12) * 1024 * 1024),
            "archives_max_face_count": int(cfg.get("max_faces", 20000)),
            "archives_texture_max_resolution": 2048,
            "sort_by": "-likeCount", "count": 24,
        }
        if cfg.get("animated"):
            params["animated"] = "true"
            params["rigged"] = "true"
        r = http_get(API + "/search?" + urllib.parse.urlencode(params), sf_headers(token), tries=2)
        if r is None:
            continue
        try:
            for m in r.json().get("results", []):
                if m.get("isDownloadable", True):
                    results.append(m)
        except Exception:  # noqa
            pass
        time.sleep(0.4)
    words = [w for w in query.lower().split() if len(w) > 2]
    results.sort(key=lambda m: (-sum(w in m.get("name", "").lower() for w in words), -int(m.get("likeCount", 0))))
    return results


def sf_download(token, uid, key, cfg):
    r = http_get("%s/models/%s/download" % (API, uid), sf_headers(token), tries=2)
    if r is None:
        return None
    info = r.json()
    arch = info.get("gltf") or info.get("glb")
    if not arch or not arch.get("url"):
        return None
    if arch.get("size") and arch["size"] > cfg.get("max_mb", 12) * 1.6 * 1024 * 1024:
        log("   ! too big:", uid)
        return None
    data = http_get(arch["url"], timeout=240, tries=2)
    if data is None:
        return None
    folder = os.path.join(ASSETS, "models", key)
    if os.path.isdir(folder):
        shutil.rmtree(folder)
    ensure(folder)
    if is_zip(data.content):
        zipfile.ZipFile(io.BytesIO(data.content)).extractall(folder)
    else:
        with open(os.path.join(folder, "scene.glb"), "wb") as f:
            f.write(data.content)
    scenes = sorted(glob.glob(os.path.join(folder, "**", "*.gltf"), recursive=True)) + \
        sorted(glob.glob(os.path.join(folder, "**", "*.glb"), recursive=True))
    if not scenes:
        shutil.rmtree(folder, ignore_errors=True)
        return None
    # Make textures phone friendly.
    max_tex = int(cfg.get("texture_size", 512))
    for p in glob.glob(os.path.join(folder, "**", "*"), recursive=True):
        if p.lower().endswith((".png", ".jpg", ".jpeg")):
            try:
                img = Image.open(p)
                if max(img.size) > max_tex:
                    img.thumbnail((max_tex, max_tex), Image.LANCZOS)
                    fmt = "PNG" if p.lower().endswith(".png") else "JPEG"
                    if fmt == "JPEG" and img.mode not in ("RGB", "L"):
                        img = img.convert("RGB")
                    img.save(p, fmt)
            except Exception as e:  # noqa
                log("   ! texture resize failed", p, e)
    meta = {"path": res_path(scenes[0]), "uid": uid, "name": "", "author": "", "license": "", "url": ""}
    mi = http_get("%s/models/%s" % (API, uid), sf_headers(token), tries=2)
    if mi is not None:
        j = mi.json()
        meta["name"] = j.get("name", "")
        meta["author"] = (j.get("user") or {}).get("displayName") or (j.get("user") or {}).get("username", "")
        lic = j.get("license") or {}
        meta["license"] = lic.get("label", "") if isinstance(lic, dict) else str(lic)
        meta["url"] = j.get("viewerUrl", "https://sketchfab.com/3d-models/" + uid)
    return meta


def fetch_models():
    log("== Sketchfab models")
    token = os.environ.get("SKETCHFAB_API_TOKEN", "").strip()
    folder = ensure(os.path.join(ASSETS, "models"))
    manifest = json.load(open(os.path.join(ROOT, "ci", "sketchfab_models.json")))
    lock_path = os.path.join(ROOT, "ci", "models.lock.json")
    lock = json.load(open(lock_path)) if os.path.exists(lock_path) else {}
    table = {}
    if not token:
        log("   No SKETCHFAB_API_TOKEN secret -> using the built-in stand-in models.")
        REPORT["notes"].append("no Sketchfab token: stand-in models used")
        json.dump(table, open(os.path.join(folder, "models.json"), "w"), indent=1)
        return
    for key, cfg in manifest.items():
        if key.startswith("_"):
            continue
        meta = None
        if lock.get(key):
            meta = sf_download(token, lock[key], key, cfg)
        if meta is None:
            tried = set()
            for q in cfg.get("queries", [key]):
                for m in sf_search(token, q, cfg)[:4]:
                    uid = m.get("uid")
                    if not uid or uid in tried:
                        continue
                    tried.add(uid)
                    meta = sf_download(token, uid, key, cfg)
                    if meta:
                        break
                if meta:
                    break
        if meta:
            table[key] = meta
            lock[key] = meta["uid"]
            CREDITS.append('3D model: "%s" by %s (%s) %s' % (meta["name"], meta["author"], meta["license"], meta["url"]))
            REPORT["models"][key] = "%s by %s" % (meta["name"], meta["author"])
            log("   %s: %s by %s [%s]" % (key, meta["name"], meta["author"], meta["license"]))
        else:
            log("   %s: not found (stand-in used)" % key)
    json.dump(table, open(os.path.join(folder, "models.json"), "w"), indent=1)
    json.dump(lock, open(lock_path, "w"), indent=1, sort_keys=True)


# ------------------------------------------------------------------ main

def main():
    for step in (fetch_font, fetch_textures, fetch_sounds, fetch_models):
        try:
            step()
        except Exception as e:  # noqa
            log("!! step failed:", step.__name__, e)
            REPORT["notes"].append("%s failed: %s" % (step.__name__, e))
    with open(os.path.join(ASSETS, "credits.txt"), "w") as f:
        f.write("\n".join(CREDITS) + "\n")
    ensure(os.path.join(ROOT, "build"))
    with open(os.path.join(ROOT, "build", "asset_report.json"), "w") as f:
        json.dump(REPORT, f, indent=1)
    log(json.dumps(REPORT, indent=1))


if __name__ == "__main__":
    sys.exit(main())
