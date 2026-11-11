#!/usr/bin/env python3
"""Thumbnails of Poly Haven's CC0 textures that could dress an old Indian wooden house (CI only).

    python3 tools/scout/polyhaven_tex_scout.py <out dir>
"""
import io
import json
import os
import re
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from PIL import Image, ImageDraw

OUT = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "scout_out")
os.makedirs(OUT, exist_ok=True)
UA = {"User-Agent": "chaya-game-ci/1.0 (asset scout)"}
GROUPS = {
    "plaster": r"plaster|peel|painted_wall|paint|stucco|lime|mud|adobe|clay|whitewash|wall_0|damp|mold|stain",
    "wood": r"wood|plank|timber|teak|rosewood|walnut|mahogany|veneer|carv|shutter|door|bark|bamboo|parquet|beam",
    "floor": r"tile|terracotta|floor|mosaic|encaustic|pattern|marble|slate|flagstone|brick|cobble",
    "fibre": r"thatch|straw|hay|coir|coco|wicker|rattan|rope|jute|burlap|hessian|weav|basket|mat\b|reed|fabric|cotton|linen|quilt|carpet|rug|velvet|silk",
    "misc": r"red_sand|red_soil|red_dirt|red_mud|laterite|chalk|rust|soot|ash|leaf|leaves|moss|gold|brass|copper|bronze|metal_plate",
}


def get(url, binary=False):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90) as r:
        b = r.read()
    return b if binary else json.loads(b)


allt = get("https://api.polyhaven.com/assets?type=textures")
print(len(allt), "textures on Poly Haven")
T, COLS, ROWS = 200, 10, 6


def thumb(i):
    try:
        return i, get("https://cdn.polyhaven.com/asset_img/thumbs/%s.png?height=200" % i, True)
    except Exception as ex:     # noqa: BLE001
        return i, None


report = {}
for g, pat in GROUPS.items():
    rx = re.compile(pat, re.I)
    ids = sorted(i for i, a in allt.items() if rx.search(i) or rx.search(" ".join(a.get("tags", []) + a.get("categories", [])) + " " + a.get("name", "")))
    if g != "wood":
        ids = [i for i in ids if not re.search(r"^(bark|tree|forest|grass|rock|snow|aerial|coast|sand_|mud_cracked|gravel|asphalt|road)", i)] or ids
    report[g] = ids
    print(g, len(ids))
    with ThreadPoolExecutor(max_workers=12) as ex:
        th = dict(ex.map(thumb, ids))
    per = COLS * ROWS
    for s in range(0, len(ids), per):
        chunk = ids[s:s + per]
        rows = -(-len(chunk) // COLS)
        sheet = Image.new("RGB", (COLS * T, rows * (T + 16)), (40, 40, 44))
        d = ImageDraw.Draw(sheet)
        for k, i in enumerate(chunk):
            x, y = (k % COLS) * T, (k // COLS) * (T + 16)
            if th.get(i):
                try:
                    im = Image.open(io.BytesIO(th[i])).convert("RGB")
                    im.thumbnail((T, T))
                    sheet.paste(im, (x + (T - im.width) // 2, y))
                except Exception:       # noqa: BLE001
                    pass
            d.text((x + 2, y + T + 2), i[:32], fill=(255, 255, 0))
        sheet.save(os.path.join(OUT, "tex_%s_%d.jpg" % (g, s // per)), quality=85)
json.dump(report, open(os.path.join(OUT, "tex_scout.json"), "w"), indent=1)
