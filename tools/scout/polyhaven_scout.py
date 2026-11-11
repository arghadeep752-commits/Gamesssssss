#!/usr/bin/env python3
"""Look at Poly Haven's CC0 models before choosing which ones go into the house (CI only: needs the internet).

    python3 tools/scout/polyhaven_scout.py <out dir>

Writes labelled contact sheets of the thumbnails and scout.json (size, polygons, files of the 1k glTF).
"""
import io
import json
import os
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "scout_out")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "chaya-game-ci/1.0 (asset scout)"}
IDS = """
GothicBed_01 old_bed_frame vintage_day_bed
GothicCabinet_01 GothicCommode_01 chinese_cabinet chinese_commode vintage_cabinet_01 painted_wooden_cabinet painted_wooden_cabinet_02
drawer_cabinet vintage_wooden_drawer_01 wooden_display_shelves_01 wooden_bookshelf_worn painted_wooden_shelves ClassicNightstand_01
painted_wooden_nightstand Shelf_01
WoodenTable_01 WoodenTable_02 WoodenTable_03 wooden_table_02 round_wooden_table_01 round_wooden_table_02 small_wooden_table_01 side_table_01
side_table_tall_01 chinese_tea_table chinese_console_table ClassicConsole_01 painted_wooden_table gallinera_table dining_table gothic_coffee_table
WoodenChair_01 painted_wooden_chair_01 painted_wooden_chair_02 painted_wooden_bench painted_wooden_stool wooden_stool_01 wooden_stool_02
folding_wooden_stool chinese_stool Rockingchair_01 chinese_armchair painted_wooden_sofa chinese_sofa gallinera_chair
treasure_chest vintage_suitcase old_military_crate wooden_crate_01 wooden_crate_02 wooden_military_crate ceramic_pot planter_pot_clay
antique_ceramic_vase_01 ceramic_vase_01 ceramic_vase_02 ceramic_vase_03 ceramic_vase_04 jug_01 metal_jug pot_enamel_01 wooden_bucket_01
wooden_bucket_02 wooden_bowl_01 wooden_bowl_02 wicker_basket_01 wicker_basket_02 wine_barrel_01 wooden_barrels_01 Barrel_01 barrel_03
brass_candleholders brass_diya_lantern brass_goblets brass_pan_01 brass_pot_01 brass_pot_02 brass_vase_01 brass_vase_02 brass_vase_03 brass_vase_04
Lantern_01 wooden_lantern_01 vintage_oil_lamp wooden_candlestick lantern_chandelier_01 chinese_chandelier Chandelier_01 Chandelier_02 Chandelier_03
carved_wooden_elephant carved_wooden_plate fancy_picture_frame_01 fancy_picture_frame_02 hanging_picture_frame_01 hanging_picture_frame_02
hanging_picture_frame_03 standing_picture_frame_01 ornate_mirror_01 vintage_grandfather_clock_01 mantel_clock_01 spinning_wheel_01
book_encyclopedia_set_01 decorative_book_set_01 tea_set_01 sungka_board wooden_broom wooden_ladder throw_pillows_01 ceiling_fan horse_statue_01
bull_head marble_bust_01 lion_head chinese_screen_panels large_castle_door potted_plant_01 potted_plant_02 wooden_spoon wall_clock
bananas lemon food_lime_01 food_pomegranate_01 food_apple_01 sweet_potato yellow_onion wooden_axe hatchet street_rat wheelchair_01 trashbag
""".split()


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        b = r.read()
    return b if binary else json.loads(b)


def one(i):
    rec = {"id": i}
    try:
        info = get("https://api.polyhaven.com/info/" + i)
        rec.update({k: info.get(k) for k in ("name", "polycount", "dimensions", "categories", "tags", "authors")})
    except Exception as ex:     # noqa: BLE001
        rec["info_error"] = str(ex)
    try:
        files = get("https://api.polyhaven.com/files/" + i)
        g = files.get("gltf", {})
        rec["gltf_res"] = sorted(g.keys())
        k = g.get("1k", {}).get("gltf", {})
        rec["gltf_1k"] = {"size": k.get("size"), "include": {n: v.get("size") for n, v in (k.get("include") or {}).items()}}
    except Exception as ex:     # noqa: BLE001
        rec["files_error"] = str(ex)
    try:
        rec["thumb"] = get("https://cdn.polyhaven.com/asset_img/thumbs/%s.png?height=256" % i, True)
    except Exception as ex:     # noqa: BLE001
        rec["thumb_error"] = str(ex)
    return rec


with ThreadPoolExecutor(max_workers=8) as ex:
    recs = list(ex.map(one, IDS))
T, COLS = 256, 8
per = COLS * 5
for s in range(0, len(recs), per):
    chunk = recs[s:s + per]
    rows = -(-len(chunk) // COLS)
    sheet = Image.new("RGB", (COLS * T, rows * (T + 30)), (58, 58, 62))
    d = ImageDraw.Draw(sheet)
    for k, r in enumerate(chunk):
        x, y = (k % COLS) * T, (k // COLS) * (T + 30)
        if "thumb" in r:
            try:
                im = Image.open(io.BytesIO(r["thumb"])).convert("RGBA")
                im.thumbnail((T, T))
                sheet.paste(im, (x + (T - im.width) // 2, y + (T - im.height) // 2), im)
            except Exception as ex:     # noqa: BLE001
                d.text((x + 4, y + 100), "thumb: %s" % ex, fill=(255, 80, 80))
        dim = r.get("dimensions") or []
        dims = "x".join("%.2f" % (v / 1000.0) for v in dim) if dim else ""
        d.text((x + 3, y + T + 1), r["id"], fill=(255, 255, 0))
        d.text((x + 3, y + T + 14), "%s  %sp" % (dims, r.get("polycount")), fill=(200, 200, 200))
    sheet.save(os.path.join(OUT, "scout_%d.jpg" % (s // per)), quality=88)
for r in recs:
    r.pop("thumb", None)
json.dump(recs, open(os.path.join(OUT, "scout.json"), "w"), indent=1)
print(len(recs), "models scouted")
