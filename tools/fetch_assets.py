#!/usr/bin/env python3
"""Downloads the free source assets for Night Class.

* PBR texture sets from Poly Haven (https://polyhaven.com, CC0 / public domain).
  Each material slot has a list of preferred asset ids; if none of them exists in the
  catalog any more, the best keyword match from the live catalog is used instead.
* Real 3D furniture and props from Poly Haven (CC0): FBX + their photo textures, picked per
  slot from preferred ids or the best keyword match in the live model catalog.
* Extra photo textures (paper, chalkboard, cork...) from Poly Haven or ambientCG (CC0).
* The teacher: a rigged, realistic woman with facial blendshapes from the Microsoft Rocketbox
  avatar library (MIT licence) and motion-captured animations from the same library.
* Google Fonts (SIL Open Font License) from github.com/google/fonts.

Runs in GitHub Actions before the Unity build. Output: <out>/<slot>/<map>.<ext>,
<out>/fonts/*.ttf and <out>/manifest.json. Anything that fails to download is simply
missing: tools/process_assets.py then generates a procedural replacement.
Usage: python3 tools/fetch_assets.py <out_dir>
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "NightClass-build/1.0 (github.com/arghadeep752-commits/gamesssssss)"
API = "https://api.polyhaven.com"
RES = "1k"

# slot -> (preferred Poly Haven ids, fallback keywords)
SLOTS = {
    "wood_floor": (["wood_floor_worn", "laminate_floor_02", "old_wood_floor", "wood_floor", "brown_floor_tiles"], ["wood floor", "parquet", "laminate", "planks"]),
    "tiles_floor": (["floor_tiles_06", "floor_tiles_08", "floor_tiles_02", "checkered_pavement_tiles", "worn_tile_floor"], ["floor tiles", "tiles", "linoleum"]),
    "tiles_small": (["small_square_tiles", "tiles_white", "bathroom_tiles", "square_tiles", "white_tiles"], ["bathroom tiles", "white tiles", "square tiles", "tiles"]),
    "concrete": (["concrete_floor_worn_001", "concrete_floor_02", "concrete_floor_03", "rough_concrete", "concrete_wall_008"], ["concrete floor", "concrete"]),
    "plaster": (["painted_plaster_wall", "plastered_wall_02", "white_plaster_02", "beige_wall_001", "plaster_grey_04"], ["plaster", "painted wall", "wall paint"]),
    "brick": (["red_brick_03", "brick_wall_02", "red_bricks_04", "medieval_red_brick", "brick_wall_001"], ["red brick", "brick wall", "brick"]),
    "wood_furniture": (["wood_table_001", "oak_veneer_01", "fine_grained_wood", "plywood", "wood_table"], ["wood veneer", "fine wood", "table wood", "wood"]),
    "metal_painted": (["painted_metal_shutter", "metal_plate", "green_metal_rust", "blue_metal_plate", "metal_plate_02"], ["painted metal", "metal plate", "metal"]),
    "rust": (["rust_coarse_01", "rusty_metal_02", "rusty_metal", "rusty_metal_03", "corrugated_iron_02"], ["rust", "rusty metal"]),
    "fabric": (["fabric_pattern_05", "denim_fabric", "velour_velvet", "fabric_leather_02", "hessian_230"], ["fabric", "cloth", "carpet"]),
}

# Poly Haven map keys we want (first available alias wins)
MAPS = {
    "diff": ["Diffuse", "diff", "Color"],
    "nor": ["nor_gl", "nor_dx", "Normal"],
    "rough": ["Rough", "rough", "Roughness"],
    "ao": ["AO", "ao"],
    "arm": ["arm", "ARM"],
    "metal": ["Metal", "metal", "Metalness"],
}

FONTS = {
    "Barlow-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/barlow/Barlow-Medium.ttf",
    "Barlow-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/barlow/Barlow-SemiBold.ttf",
    "Creepster-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/creepster/Creepster-Regular.ttf",
    "CabinSketch-Bold.ttf": "https://github.com/google/fonts/raw/main/ofl/cabinsketch/CabinSketch-Bold.ttf",
    "PermanentMarker-Regular.ttf": "https://github.com/google/fonts/raw/main/apache/permanentmarker/PermanentMarker-Regular.ttf",
}

RES_ORDER = ["1k", "2k", "4k", "8k"]

# Poly Haven 3D models: slot -> (preferred ids, keywords; a keyword must match a whole word)
MODEL_SLOTS = {
    "school_desk": (["SchoolDesk_01"], ["school desk", "desk"]),
    "school_chair": (["SchoolChair_01"], ["school chair"]),
    "table": (["WoodenTable_01", "WoodenTable_03", "WoodenTable_02"], ["wooden table", "table"]),
    "table2": (["WoodenTable_02", "WoodenTable_03"], ["wooden table", "table"]),
    "chair": (["WoodenChair_01"], ["wooden chair", "chair"]),
    "shelf": (["Shelf_01"], ["bookshelf", "bookcase", "shelf"]),
    "metal_shelf": (["steel_frame_shelves_01", "steel_frame_shelves_02", "steel_frame_shelves_03"], ["metal shelves", "steel shelves", "shelving", "rack"]),
    "sofa": (["Sofa_01"], ["sofa", "couch"]),
    "armchair": (["ArmChair_01", "GreenChair_01"], ["armchair", "arm chair"]),
    "coffee_table": (["CoffeeTable_01"], ["coffee table"]),
    "tv": (["Television_01"], ["television", "tv"]),
    "cabinet": (["GothicCabinet_01", "GothicCommode_01"], ["cabinet", "cupboard"]),
    "nightstand": (["ClassicNightstand_01"], ["nightstand", "bedside"]),
    "barrel": (["Barrel_01", "Barrel_02"], ["barrel"]),
    "wet_sign": (["WetFloorSign_01"], ["wet floor"]),
    "drill": (["Drill_01"], ["drill"]),
    "wrench": (["adjustable_wrench"], ["wrench", "spanner"]),
    "box": (["cardboard_box_01", "cardboard_box_02", "CheeseBox_01"], ["cardboard box", "cardboard"]),
    "crate": (["wooden_crate_01", "wooden_crate_02"], ["wooden crate", "crate"]),
    "bucket": (["metal_bucket_01", "bucket_01"], ["bucket"]),
    "plant": (["potted_plant_01", "potted_plant_02", "potted_plant_04"], ["potted plant", "houseplant", "plant"]),
    "books": (["book_encyclopedia_set_01"], ["books", "book"]),
    "desk_lamp": (["desk_lamp_arm_01"], ["desk lamp"]),
    "extinguisher": (["korean_fire_extinguisher_01", "fire_extinguisher_01"], ["fire extinguisher", "extinguisher"]),
    "clock": (["vintage_wall_clock", "wall_clock_01", "alarm_clock_01"], ["wall clock", "clock"]),
    "hammer": (["claw_hammer", "hammer_01"], ["hammer"]),
    "cash_register": (["CashRegister_01"], ["cash register"]),
    "trash": (["trash_can_01", "metal_trash_can_01"], ["trash can", "trash", "bin", "garbage"]),
    "rock": (["rock_moss_set_01", "boulder_01"], ["rock", "boulder"]),
    "radiator": ([], ["radiator"]),
    "toolbox": ([], ["toolbox"]),
    "piano": ([], ["piano"]),
}

# extra photo textures: name -> (Poly Haven ids, Poly Haven keywords, ambientCG search words)
EXTRA_TEX = {
    "paper": ([], ["paper"], ["paper"]),
    "fabric2": (["velour_velvet", "denim_fabric", "hessian_230"], ["velvet", "fabric"], ["fabric"]),
}

RB = "https://raw.githubusercontent.com/microsoft/Microsoft-Rocketbox/master/Assets/"
RB_AVATAR = RB + "Avatars/Professions/Business_Female_02/"
TEACHER_FILES = {
    "Business_Female_02_facial.fbx": RB_AVATAR + "Export/Business_Female_02_facial.fbx",
    "Textures/f015_body_color.tga": RB_AVATAR + "Textures/f015_body_color.tga",
    "Textures/f015_body_normal.tga": RB_AVATAR + "Textures/f015_body_normal.tga",
    "Textures/f015_head_color.tga": RB_AVATAR + "Textures/f015_head_color.tga",
    "Textures/f015_head_normal.tga": RB_AVATAR + "Textures/f015_head_normal.tga",
    "Textures/f015_opacity_color.tga": RB_AVATAR + "Textures/f015_opacity_color.tga",
    "Textures/f015_glasses_opacity_color.tga": RB_AVATAR + "Textures/f015_glasses_opacity_color.tga",
}
RB_ANIM = RB + "Animations/"
TEACHER_ANIMS = {
    "walk": "all_animations_max_motextr_xy/f_walk_self-assured.max.fbx",
    "run": "all_animations_max_motextr_xy/f_run_fast_01.max.fbx",
    "idle": "all_animations_max_motextr_static/f_idle_angry_01.max.fbx",
    "look": "all_animations_max_motextr_static/f_idle_look_around_01.max.fbx",
    "attack": "all_animations_max_motextr_static/f_gestic_talk_angry_01.max.fbx",
    "burn": "all_animations_max_motextr_static/f_idle_nervous_01.max.fbx",
}


def get(url, retries=4):
    last = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError(f"download failed: {url}: {last}")


def get_json(url):
    return json.loads(get(url))


def pick(entry, fmts):
    order = [RES] + [r for r in RES_ORDER if r != RES]
    for r in order:
        if r in entry:
            for f in fmts:
                v = entry[r].get(f) if isinstance(entry[r], dict) else None
                if isinstance(v, dict) and "url" in v:
                    return v["url"], f
    return None


def score(meta, keywords):
    text = " ".join([meta.get("name", "")] + list(meta.get("tags", [])) + list(meta.get("categories", []))).lower()
    s = 0
    for i, k in enumerate(keywords):
        if k in text:
            s += 10 - i
        for w in k.split():
            if w in text:
                s += 1
    return s + min(meta.get("download_count", 0), 200000) / 200000.0


def choose(catalog, preferred, keywords, used):
    for aid in preferred:
        if aid in catalog and aid not in used:
            return aid
    best, best_s = None, 0
    for aid, meta in catalog.items():
        if aid in used:
            continue
        s = score(meta, keywords)
        if s > best_s:
            best, best_s = aid, s
    return best


def word_match(text, kw):
    import re
    return re.search(r"(^|[^a-z])" + re.escape(kw) + r"($|[^a-z])", text) is not None


def choose_model(catalog, preferred, keywords, used):
    for aid in preferred:
        if aid in catalog and aid not in used:
            return aid
    best, best_s = None, 0.0
    for aid, meta in catalog.items():
        if aid in used:
            continue
        name = (meta.get("name", "") + " " + aid.replace("_", " ")).lower()
        tags = " ".join(list(meta.get("tags", [])) + list(meta.get("categories", []))).lower()
        s = 0.0
        for i, k in enumerate(keywords):
            if word_match(name, k):
                s += 20 - i
            elif word_match(tags, k):
                s += 8 - i * 0.5
        if s <= 0:
            continue
        s += min(meta.get("download_count", 0), 100000) / 100000.0
        if s > best_s:
            best, best_s = aid, s
    return best


def model_jobs(out, manifest):
    jobs = []
    try:
        catalog = get_json(f"{API}/assets?t=models")
        print(f"Poly Haven catalog: {len(catalog)} models")
    except Exception as e:  # noqa: BLE001
        print(f"warning: no model catalog ({e})")
        return jobs
    used = set()
    for slot, (preferred, keywords) in MODEL_SLOTS.items():
        aid = choose_model(catalog, preferred, keywords, used)
        if not aid:
            print(f"model {slot:14s} -- none")
            continue
        used.add(aid)
        try:
            files = get_json(f"{API}/files/{aid}")
            fbx = None
            for res in ["1k", "2k", "4k"]:
                fbx = files.get("fbx", {}).get(res, {}).get("fbx")
                if fbx:
                    break
            if not fbx:
                print(f"model {slot:14s} -- {aid} has no FBX")
                continue
            base = os.path.join(out, "models", slot)
            jobs.append((fbx["url"], os.path.join(base, os.path.basename(fbx["url"]))))
            for rel, info in fbx.get("include", {}).items():
                jobs.append((info["url"], os.path.join(base, rel)))
            manifest["models"][slot] = aid
            print(f"model {slot:14s} <- {aid} ({len(fbx.get('include', {}))} textures)")
        except Exception as e:  # noqa: BLE001
            print(f"warning: model {aid}: {e}")
    return jobs


def ambientcg_jobs(name, words, out):
    import io
    import zipfile
    for w in words:
        try:
            data = get_json(f"https://ambientcg.com/api/v2/full_json?type=Material&q={w}&sort=Popular&limit=5")
            for a in data.get("foundAssets", []):
                aid = a.get("assetId")
                if not aid:
                    continue
                blob = get(f"https://ambientcg.com/get?file={aid}_1K-JPG.zip")
                z = zipfile.ZipFile(io.BytesIO(blob))
                d = os.path.join(out, "extra", name)
                os.makedirs(d, exist_ok=True)
                kinds = {"Color": "diff.jpg", "NormalGL": "nor.jpg", "Roughness": "rough.jpg", "AmbientOcclusion": "ao.jpg"}
                got = []
                for zn in z.namelist():
                    for k, fn in kinds.items():
                        if zn.endswith(f"_{k}.jpg"):
                            with open(os.path.join(d, fn), "wb") as fh:
                                fh.write(z.read(zn))
                            got.append(k)
                if "Color" in got:
                    print(f"texture {name:10s} <- ambientCG {aid}")
                    return True
        except Exception as e:  # noqa: BLE001
            print(f"warning: ambientCG {w}: {e}")
    return False


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "SourceAssets"
    os.makedirs(out, exist_ok=True)
    manifest = {"textures": {}, "fonts": {}}
    jobs = []
    try:
        catalog = get_json(f"{API}/assets?t=textures")
        print(f"Poly Haven catalog: {len(catalog)} textures")
    except Exception as e:  # noqa: BLE001
        print(f"warning: no Poly Haven catalog ({e}); textures will be procedural")
        catalog = {}

    used = set()
    for slot, (preferred, keywords) in SLOTS.items():
        if not catalog:
            break
        for attempt in range(4):   # skip sets without a colour or normal map
            aid = choose(catalog, preferred, keywords, used)
            if not aid:
                print(f"warning: no texture for {slot}")
                break
            used.add(aid)
            try:
                files = get_json(f"{API}/files/{aid}")
            except Exception as e:  # noqa: BLE001
                print(f"warning: {aid}: {e}")
                continue
            found = {}
            for kind, aliases in MAPS.items():
                for a in aliases:
                    if a in files:
                        p = pick(files[a], ["png", "jpg"] if kind == "nor" else ["jpg", "png"])
                        if p:
                            found[kind] = p
                            break
            if "diff" not in found or "nor" not in found:
                print(f"{slot}: {aid} has no colour/normal map ({', '.join(sorted(files))}), trying another")
                continue
            got = {}
            for kind, (url, f) in found.items():
                path = os.path.join(out, slot, f"{kind}.{f}")
                jobs.append((url, path))
                got[kind] = path
            manifest["textures"][slot] = {"id": aid, "maps": got}
            print(f"{slot:15s} <- {aid} ({', '.join(sorted(got))})")
            break

    for name, url in FONTS.items():
        path = os.path.join(out, "fonts", name)
        jobs.append((url, path))
        manifest["fonts"][name] = path

    manifest["models"] = {}
    jobs += model_jobs(out, manifest)

    for name, (ids, kws, acg) in EXTRA_TEX.items():
        done = False
        if catalog:
            aid = choose_model(catalog, ids, kws, used)
            if aid:
                try:
                    files = get_json(f"{API}/files/{aid}")
                    found = {}
                    for kind, aliases in MAPS.items():
                        for a in aliases:
                            if a in files:
                                p = pick(files[a], ["png", "jpg"] if kind == "nor" else ["jpg", "png"])
                                if p:
                                    found[kind] = p
                                    break
                    if "diff" in found:
                        used.add(aid)
                        for kind, (url, f) in found.items():
                            jobs.append((url, os.path.join(out, "extra", name, f"{kind}.{f}")))
                        print(f"texture {name:10s} <- Poly Haven {aid}")
                        done = True
                except Exception as e:  # noqa: BLE001
                    print(f"warning: {aid}: {e}")
        if not done:
            ambientcg_jobs(name, acg, out)

    for rel, url in TEACHER_FILES.items():
        jobs.append((url, os.path.join(out, "teacher", rel)))
    for name, rel in TEACHER_ANIMS.items():
        jobs.append((RB_ANIM + rel, os.path.join(out, "teacher", "Anims", name + ".fbx")))

    def fetch(job):
        url, path = job
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path, True
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            data = get(url)
            with open(path, "wb") as fh:
                fh.write(data)
            return path, True
        except Exception as e:  # noqa: BLE001
            print(f"warning: {e}")
            return path, False

    ok = 0
    with ThreadPoolExecutor(max_workers=8) as ex:
        for path, good in ex.map(fetch, jobs):
            ok += 1 if good else 0
    print(f"downloaded {ok}/{len(jobs)} files")
    with open(os.path.join(out, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)


if __name__ == "__main__":
    main()
