#!/usr/bin/env python3
"""Downloads the free source assets for Night Class.

* PBR texture sets from Poly Haven (https://polyhaven.com, CC0 / public domain).
  Each material slot has a list of preferred asset ids; if none of them exists in the
  catalog any more, the best keyword match from the live catalog is used instead.
* Four Google Fonts (SIL Open Font License) from github.com/google/fonts.

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
        aid = choose(catalog, preferred, keywords, used)
        if not aid:
            print(f"warning: no texture for {slot}")
            continue
        used.add(aid)
        try:
            files = get_json(f"{API}/files/{aid}")
        except Exception as e:  # noqa: BLE001
            print(f"warning: {aid}: {e}")
            continue
        got = {}
        for kind, aliases in MAPS.items():
            for a in aliases:
                if a in files:
                    p = pick(files[a], ["png", "jpg"] if kind == "nor" else ["jpg", "png"])
                    if p:
                        url, f = p
                        path = os.path.join(out, slot, f"{kind}.{f}")
                        jobs.append((url, path))
                        got[kind] = path
                        break
        manifest["textures"][slot] = {"id": aid, "maps": got}
        print(f"{slot:15s} <- {aid} ({', '.join(sorted(got))})")

    for name, url in FONTS.items():
        path = os.path.join(out, "fonts", name)
        jobs.append((url, path))
        manifest["fonts"][name] = path

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
