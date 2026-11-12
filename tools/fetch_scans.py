#!/usr/bin/env python3
"""Chaya - download the real scanned 3D models and the extra photo textures the house is dressed with.

    python3 tools/fetch_scans.py [out dir = assets/downloaded/scans]

Everything is CC0 from Poly Haven (photo-scanned or hand-made from real objects, no AI):
  models/<id>/…gltf + .bin + textures/   the 1k glTF package of each model in MODELS
  tex/<slot>/{diff,nor,rough,ao}.jpg     extra surfaces for the old Indian house (aged lime plaster, panelled wood,
                                         terracotta and chequered floors, thatch for the coconut husk …)
  art/*.jpg                              Raja Ravi Varma paintings (public domain) for the frames on the walls
tools/build_map.py turns the models into game props in Blender (clean-up, decimation, scale, placement).
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 else os.path.join(ROOT, "assets", "downloaded", "scans")
PH = "https://api.polyhaven.com/"
UA = "chaya-game-build/1.0 (Mxyan Games; CC0 asset fetch)"

MODELS = """
GothicBed_01 vintage_day_bed painted_wooden_cabinet_02 painted_wooden_cabinet GothicCommode_01 Rockingchair_01
vintage_grandfather_clock_01 chinese_cabinet wooden_bookshelf_worn WoodenTable_01 ceramic_pot planter_pot_clay wooden_bucket_01
wicker_basket_02 wicker_basket_01 metal_jug brass_vase_02 wooden_stool_01 treasure_chest wooden_crate_01 wine_barrel_01 wooden_broom
small_wooden_table_01 painted_wooden_chair_02 spinning_wheel_01 vintage_oil_lamp brass_diya_lantern food_pomegranate_01 food_apple_01
lemon Lantern_01 ClassicNightstand_01 WoodenTable_02 brass_vase_03 brass_pot_01 brass_pot_02 wooden_bowl_02 brass_candleholders
wooden_candlestick
""".split()

# slot -> Poly Haven texture ids, first one that downloads wins (HIRES slots at 2k: the big walls and floors stay sharp)
TEXTURES = {
    "wall_planks": ["wood_planks_grey", "wood_planks"],
    "wall_beige": ["beige_wall_001", "beige_wall_002"],
    "door_planks": ["wooden_planks", "wood_planks"],
    "floor_deck": ["wood_floor_deck", "wood_floor_worn"],
    "floor_terracotta": ["patterned_terracotta_tiling", "terracotta_floor_tiles"],
    "floor_courtyard": ["red_sandstone_pavement", "brick_pavement_02"],
    "floor_marble": ["marble_01", "marble_tiles"],
    "floor_redtile": ["terracotta_floor_tiles", "brick_villa_floor"],
    "ceiling_planks": ["wood_planks_dirt", "dark_wooden_planks"],
    "trim_dark": ["dark_wood", "dark_wooden_planks"],
    "wood_carved": ["fine_grained_wood", "rosewood_veneer1", "dark_wood"],
    "wood_beam": ["weathered_brown_planks", "dark_wooden_planks"],
    "wood_shutter": ["wood_shutter", "worn_shutter"],
    "stone_slab": ["concrete_floor_worn_001", "stone_tiles"],
    "plinth": ["red_sandstone_wall", "large_sandstone_blocks"],
    "ground_mud": ["brown_mud_dry", "dry_mud_field_001", "brown_mud"],
    "roof_tiles": ["clay_roof_tiles_02", "clay_roof_tiles"],
    "stair_planks": ["stair_planks", "wood_planks"],
    "husk": ["thatch_roof_angled", "riet_01", "bark_brown_02"],
    "powder": ["red_sand", "red_laterite_soil_stones"],
    "cloth_red": ["quatrefoil_jacquard_fabric", "velour_velvet"],
    "clay_pbr": ["clay_plaster", "clay_floor_001"],
    "hessian": ["hessian_230", "hessian_380"],
}
HIRES = {"wall_planks", "wall_beige", "door_planks", "floor_deck", "floor_terracotta", "floor_courtyard"}
SKIES = ["dikhololo_night", "satara_night", "rogland_clear_night", "kloppenheim_02", "moonless_golf"]   # bush, trees, stars - no buildings
COMMONS = "https://commons.wikimedia.org/w/api.php"


def log(*a):
    print(*a, flush=True)


def http(url, tries=4, timeout=120):
    last = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"}), timeout=timeout) as r:
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


def model(mid):
    d = os.path.join(OUT, "models", mid)
    try:
        files = jget(PH + "files/" + mid)
        g = files["gltf"]
        res = "1k" if "1k" in g else sorted(g)[0]
        pack = g[res]["gltf"]
        save(os.path.join(d, os.path.basename(urllib.parse.urlparse(pack["url"]).path)), http(pack["url"]))
        total = 0
        for rel, inf in (pack.get("include") or {}).items():
            data = http(inf["url"])
            total += len(data)
            save(os.path.join(d, rel), data)
        info = jget(PH + "info/" + mid)
        json.dump({k: info.get(k) for k in ("name", "authors", "polycount", "dimensions", "categories", "tags")}, open(os.path.join(d, "info.json"), "w"))
        log("model %-28s %s %5.1f MB" % (mid, res, total / 1e6))
        return mid, info.get("name", mid), ", ".join((info.get("authors") or {}).keys())
    except Exception as e:      # noqa: BLE001
        log("MODEL FAILED", mid, e)
        return mid, None, None


def texture(slot, ids):
    dest = os.path.join(OUT, "tex", slot)
    for aid in ids:
        try:
            files = jget(PH + "files/" + aid)

            def url_of(keys):
                for k in keys:
                    for res in (("2k", "1k") if slot in HIRES else ("1k", "2k")):
                        f = files.get(k, {}).get(res, {})
                        if "jpg" in f:
                            return f["jpg"]["url"]
                return None
            du = url_of(["Diffuse", "diff", "Color"])
            if not du:
                continue
            save(os.path.join(dest, "diff.jpg"), http(du))
            nu = url_of(["nor_gl", "Normal"])
            if nu:
                save(os.path.join(dest, "nor.jpg"), http(nu))
            ru = url_of(["Rough", "rough"])
            if ru:
                save(os.path.join(dest, "rough.jpg"), http(ru))
            au = url_of(["AO", "ao"])
            if au:
                save(os.path.join(dest, "ao.jpg"), http(au))
            log("texture %-18s <- %s" % (slot, aid))
            return slot, aid
        except Exception as e:      # noqa: BLE001
            log("  texture failed", slot, aid, e)
    log("TEXTURE MISSING", slot)
    return slot, None


def sky():
    """A night sky (HDRI photographed by Poly Haven, CC0) over the open courtyard and the village outside."""
    for aid in SKIES:
        try:
            f = jget(PH + "files/" + aid)
            h = f.get("hdri", {})
            for res in ("1k", "2k"):
                u = h.get(res, {}).get("hdr", {}).get("url")
                if u:
                    save(os.path.join(OUT, "sky", "sky.hdr"), http(u))
                    log("sky <- %s (%s)" % (aid, res))
                    return aid
        except Exception as e:      # noqa: BLE001
            log("  sky failed", aid, e)
    return None


def paintings():
    """A few of Raja Ravi Varma's portraits of women (he died in 1906: public domain), for the frames on the walls."""
    dest = os.path.join(OUT, "art")
    got = []
    seen = set()
    for q in ('"Raja Ravi Varma" lady painting', '"Ravi Varma" woman portrait painting', '"Raja Ravi Varma" painting'):
        try:
            url = COMMONS + "?" + urllib.parse.urlencode({
                "action": "query", "format": "json", "generator": "search", "gsrsearch": q + " filetype:bitmap", "gsrnamespace": 6,
                "gsrlimit": 40, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 512})
            pages = (jget(url).get("query") or {}).get("pages") or {}
        except Exception as e:      # noqa: BLE001
            log("commons search failed", e)
            continue
        for p in sorted(pages.values(), key=lambda p: p.get("index", 99)):
            title = p.get("title", "")
            ii = (p.get("imageinfo") or [{}])[0]
            low = title.lower()
            if title in seen or not re.search(r"ravi[ _]?varma", low) or not low.endswith((".jpg", ".jpeg")):
                continue
            if re.search(r"photo|portrait of raja|press|stamp|statue|house|palace|bust|signature|lithograph|oleograph|calendar|book|museum|gallery|studio|grave|memorial", low):
                continue
            w, h = ii.get("width", 0), ii.get("height", 0)
            if w < 500 or h < 600 or not (1.15 <= h / max(1, w) <= 1.75):
                continue                    # upright portraits only
            lic = ((ii.get("extmetadata") or {}).get("LicenseShortName") or {}).get("value", "")
            if not re.search(r"public domain|pd|cc0", lic, re.I):
                continue
            try:
                data = http(ii.get("thumburl") or ii["url"])
            except Exception as e:      # noqa: BLE001
                log("  painting failed", title, e)
                continue
            seen.add(title)
            save(os.path.join(dest, "painting_%d.jpg" % len(got)), data)
            got.append(title)
            log("painting %d <- %s (%s)" % (len(got) - 1, title, lic))
            if len(got) >= 4:
                return got
    return got


def main():
    os.makedirs(OUT, exist_ok=True)
    with ThreadPoolExecutor(max_workers=6) as ex:
        ms = list(ex.map(model, MODELS))
        ts = list(ex.map(lambda kv: texture(*kv), TEXTURES.items()))
    arts = []
    sky_id = None
    try:
        sky_id = sky()
    except Exception as e:      # noqa: BLE001
        log("sky failed", e)
    ok = [m for m in ms if m[1]]
    lines = ["- Furniture, pots, lamps, the candle and the brass ritual vessels are real scanned / hand-crafted models from Poly Haven "
             "(CC0, https://polyhaven.com/models): " + ", ".join("%s" % n for _, n, _ in ok) + "."]
    lines.append("- Extra house surfaces from Poly Haven (CC0): " + ", ".join("%s (%s)" % (a, s) for s, a in ts if a) + ".")
    if sky_id:
        lines.append("- Night sky: Poly Haven HDRI '%s' (CC0)." % sky_id)
    open(os.path.join(OUT, "CREDITS_SCANS.md"), "w").write("\n".join(lines) + "\n")
    json.dump({"models": [m[0] for m in ok], "missing_models": [m[0] for m in ms if not m[1]], "textures": dict(ts), "paintings": arts},
              open(os.path.join(OUT, "manifest.json"), "w"), indent=1)
    log("scans: %d/%d models, %d/%d textures, %d paintings" % (len(ok), len(ms), sum(1 for _, a in ts if a), len(ts), len(arts)))
    if len(ok) < len(ms) * 0.8:
        raise SystemExit("too many models failed to download")


if __name__ == "__main__":
    main()
