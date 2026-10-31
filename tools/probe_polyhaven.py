#!/usr/bin/env python3
"""One-off probe (runs in GitHub Actions, which can reach Poly Haven):
lists Poly Haven's CC0 HDRIs, textures and models with their metadata and
thumbnails so the realistic-fps assets can be chosen."""
import json
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

OUT = sys.argv[1] if len(sys.argv) > 1 else "probe"
UA = "RealisticFPS-asset-probe/1.0 (github.com/arghadeep752-commits/gamesssssss)"
API = "https://api.polyhaven.com"


def get(url, retries=3):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == retries - 1:
                print("FAILED", url, e)
                return None
            time.sleep(2 + i * 3)


def get_json(url):
    b = get(url)
    return json.loads(b) if b else None


def save(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    lists = {}
    for kind in ("hdris", "textures", "models"):
        d = get_json(f"{API}/assets?type={kind}") or {}
        lists[kind] = d
        save(f"{OUT}/{kind}.json", json.dumps(d, indent=1).encode())
        print(kind, len(d))
    cats = {k: get_json(f"{API}/categories/{k}") for k in ("hdris", "textures", "models")}
    save(f"{OUT}/categories.json", json.dumps(cats, indent=1).encode())

    jobs = []
    for kind, d in lists.items():
        for aid, info in d.items():
            c = set(info.get("categories", []))
            want = False
            if kind == "hdris":
                want = bool(c & {"skies", "outdoor", "nature", "natural light", "sunrise-sunset", "morning-afternoon", "midday"}) or "puresky" in aid
            elif kind == "textures":
                want = bool(c & {"terrain", "rock", "natural", "wood", "floor", "outdoor", "sand", "bark", "brick", "plaster-concrete", "roofing"})
            else:
                want = True
            if want:
                url = info.get("thumbnail_url") or f"https://cdn.polyhaven.com/asset_img/thumbs/{aid}.png?width=256&height=256"
                if "width=" not in url:
                    url += ("&" if "?" in url else "?") + "width=256&height=256"
                jobs.append((kind, aid, url))
    print("thumbnails:", len(jobs))

    def thumb(job):
        kind, aid, url = job
        b = get(url)
        if b:
            save(f"{OUT}/thumbs/{kind}/{aid}.png", b)

    with ThreadPoolExecutor(8) as ex:
        list(ex.map(thumb, jobs))

    # Full file listings (formats, sizes, polycount) for every model.
    files = {}

    def model_files(aid):
        return aid, get_json(f"{API}/files/{aid}"), get_json(f"{API}/info/{aid}")

    with ThreadPoolExecutor(6) as ex:
        for aid, fl, info in ex.map(model_files, list(lists["models"].keys())):
            slim = {}
            if fl:
                for fmt, res in fl.items():
                    if isinstance(res, dict):
                        slim[fmt] = {}
                        for r, v in res.items():
                            if isinstance(v, dict) and "size" in v:
                                slim[fmt][r] = v.get("size")
                            elif isinstance(v, dict):
                                slim[fmt][r] = {k: (vv.get("size") if isinstance(vv, dict) else vv) for k, vv in v.items()}
            files[aid] = {"files": slim, "info": info}
    save(f"{OUT}/model_files.json", json.dumps(files, indent=1).encode())

    # One full example of each kind so the download layout is known exactly.
    for aid in ("kloofendal_48d_partly_cloudy_puresky", "aerial_rocks_02", "rock_moss_set_01"):
        fl = get_json(f"{API}/files/{aid}")
        if fl:
            save(f"{OUT}/example_files_{aid}.json", json.dumps(fl, indent=1).encode())
    print("done")


if __name__ == "__main__":
    main()
