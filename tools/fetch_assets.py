#!/usr/bin/env python3
"""Downloads the free CC0 source assets used by the game from Poly Haven
(https://polyhaven.com, all CC0 / public domain) plus two open-licence fonts.

Runs in GitHub Actions before the Unity build (the build machine has internet
access).  Output: <out>/<asset_id>/<map>.<ext> and <out>/manifest.json.
Usage: python3 tools/fetch_assets.py <out_dir>
"""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "RealisticFPS-build/1.0 (github.com/arghadeep752-commits/gamesssssss)"
API = "https://api.polyhaven.com"

# asset id -> (resolution, [maps]).  Maps are Poly Haven file keys.
HDRIS = {
    "kloofendal_48d_partly_cloudy_puresky": "4k",
}

TEXTURES = {
    # terrain layers
    "forrest_ground_01": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    "forest_ground_04": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    "lichen_rock": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    "rock_face_03": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    "river_small_rocks": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    "aerial_grass_rock": ("2k", ["Diffuse", "nor_gl", "Rough"]),
    "forest_leaves_04": ("2k", ["Diffuse", "nor_gl", "Rough", "AO"]),
    # tree trunks
    "pine_bark": ("1k", ["Diffuse", "nor_gl", "Rough", "AO"]),
}

# Models: FBX geometry + their texture maps (downloaded separately as jpg/png).
MODELS = {
    "rock_face_01": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "rock_face_02": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "rock_moss_set_01": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "rock_moss_set_02": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "fern_02": ("1k", ["Diffuse", "Alpha", "nor_gl", "arm"]),
    "modular_wooden_pier": ("1k", ["planks_diff", "planks_nor_gl", "planks_arm", "poles_diff", "poles_nor_gl", "poles_arm"]),
    "stone_fire_pit": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "Lantern_01": ("1k", ["painted_diff", "painted_nor_gl", "painted_arm", "painted_opacity", "brass_diff", "brass_nor_gl", "brass_arm", "brass_opacity"]),
    "dry_branches_medium_01": ("1k", ["Diffuse", "nor_gl", "arm"]),
    "tree_stump_01": ("1k", ["Diffuse", "nor_gl", "arm"]),
}

# Texture sets taken from heavy Poly Haven models (only the textures are used;
# the game builds light-weight geometry for them).
MODEL_TEXTURES = {
    "fir_tree_01": ("2k", ["twig_diff", "twig_alpha", "twig_nor_gl", "twig_rough", "twig_ao", "bark_diff", "bark_nor_gl", "bark_rough"]),
    "pine_tree_01": ("2k", ["twig_diff", "twig_alpha", "twig_nor_gl", "twig_rough", "twig_ao"]),
    "grass_medium_01": ("2k", ["Diffuse", "Alpha", "nor_gl", "Rough"]),
    "grass_medium_02": ("2k", ["Diffuse", "Alpha", "nor_gl", "Rough"]),
    "grass_bermuda_01": ("2k", ["Diffuse", "Alpha", "nor_gl", "Rough"]),
}

FONTS = {
    "Barlow-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/barlow/Barlow-Medium.ttf",
    "Barlow-SemiBold.ttf": "https://github.com/google/fonts/raw/main/ofl/barlow/Barlow-SemiBold.ttf",
    "BarlowCondensed-Medium.ttf": "https://github.com/google/fonts/raw/main/ofl/barlowcondensed/BarlowCondensed-Medium.ttf",
    "Marcellus-Regular.ttf": "https://github.com/google/fonts/raw/main/ofl/marcellus/Marcellus-Regular.ttf",
    "Cinzel.ttf": "https://github.com/google/fonts/raw/main/ofl/cinzel/Cinzel%5Bwght%5D.ttf",
}

# format preference per map kind (normals lossless where possible)
def formats_for(map_key):
    k = map_key.lower()
    if "nor" in k:
        return ["png", "jpg"]
    if "alpha" in k or "opacity" in k or "mask" in k:
        return ["png", "jpg"]
    return ["jpg", "png"]


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
            time.sleep(2 + 4 * i)
    raise RuntimeError(f"download failed: {url}: {last}")


def get_json(url):
    return json.loads(get(url))


def pick(entry, res, fmts):
    """entry = files[map] -> {res: {fmt: {url,size}}}; prefer res, then nearest."""
    order = [res] + [r for r in RES_ORDER if r != res]
    for r in order:
        if r in entry:
            for f in fmts:
                if f in entry[r] and isinstance(entry[r][f], dict) and "url" in entry[r][f]:
                    return entry[r][f]["url"], r, f
    return None


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "SourceAssets"
    os.makedirs(out, exist_ok=True)
    jobs = []  # (url, path)
    manifest = {"hdris": {}, "textures": {}, "models": {}, "fonts": {}}

    for aid, res in HDRIS.items():
        files = get_json(f"{API}/files/{aid}")
        url = files["hdri"][res]["hdr"]["url"]
        path = os.path.join(out, aid, f"hdri_{res}.hdr")
        jobs.append((url, path))
        manifest["hdris"][aid] = path

    def add_maps(aid, res, maps, section):
        files = get_json(f"{API}/files/{aid}")
        got = {}
        for m in maps:
            if m not in files:
                print(f"warning: {aid} has no map {m}")
                continue
            p = pick(files[m], res, formats_for(m))
            if not p:
                print(f"warning: {aid}/{m} has no usable format")
                continue
            url, r, f = p
            path = os.path.join(out, aid, f"{m}.{f}")
            jobs.append((url, path))
            got[m] = path
        manifest[section].setdefault(aid, {})["maps"] = got
        return files

    for aid, (res, maps) in TEXTURES.items():
        add_maps(aid, res, maps, "textures")
    for aid, (res, maps) in MODEL_TEXTURES.items():
        add_maps(aid, res, maps, "textures")
    for aid, (res, maps) in MODELS.items():
        files = add_maps(aid, res, maps, "models")
        fbx = files["fbx"][res]["fbx"]["url"]
        path = os.path.join(out, aid, f"{aid}.fbx")
        jobs.append((fbx, path))
        manifest["models"][aid]["fbx"] = path

    for name, url in FONTS.items():
        path = os.path.join(out, "fonts", name)
        jobs.append((url, path))
        manifest["fonts"][name] = path

    def run(job):
        url, path = job
        if os.path.exists(path) and os.path.getsize(path) > 0:
            return path, "cached"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        try:
            data = get(url)
        except RuntimeError as e:
            return path, f"FAILED {e}"
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
        return path, f"{len(data) // 1024} KB"

    failures = 0
    with ThreadPoolExecutor(6) as ex:
        for path, status in ex.map(run, jobs):
            print(f"{status:>12}  {path}")
            if status.startswith("FAILED"):
                failures += 1
                if "/fonts/" in path:
                    failures -= 1  # fonts are optional
    with open(os.path.join(out, "manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(f"{len(jobs)} files, {failures} required failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
