"""Floor plans of both floors with walls, openings, furniture, items, hiding places, the trader's patrol and walk
grid, for checking the layout without Blender (PIL only).   python3 preview_plan.py OUT.png"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

import architecture  # noqa: E402
import layout as LY  # noqa: E402
import navigation  # noqa: E402
import props  # noqa: E402

S = 48            # pixels per metre
M = 40            # margin


def font(sz):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", os.path.join(HERE, "../../Assets/Resources/Fonts/Rajdhani-SemiBold.ttf")):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def plan(fl, L, G, coll):
    w = int(LY.W * S + 2 * M)
    h = int(LY.D * S + 2 * M + 30)
    im = Image.new("RGB", (w, h), (250, 250, 247))
    dr = ImageDraw.Draw(im)
    f12, f14 = font(12), font(16)

    def P(x, y):
        return (M + x * S, h - 30 - M - y * S)

    # walk grid
    ok = G["layers"][fl]
    for i in range(G["nx"]):
        for j in range(G["ny"]):
            x0, y0 = P(i * G["cell"], (j + 1) * G["cell"])
            x1, y1 = P((i + 1) * G["cell"], j * G["cell"])
            if ok[i, j]:
                dr.rectangle([x0, y0, x1, y1], fill=(222, 240, 222))
            if G["layers"][2][i, j]:
                dr.rectangle([x0 + 3, y0 + 3, x1 - 3, y1 - 3], outline=(120, 120, 220))
    # rooms
    for r in LY.ROOMS:
        if r[1] != fl:
            continue
        x0, y0, x1, y1 = r[2]
        a, b = P(x0, y1), P(x1, y0)
        dr.text(((a[0] + b[0]) / 2 - 40, a[1] + 8), r[3], fill=(60, 60, 60), font=f14)
    # colliders at walking height (walls dark, furniture brown)
    zf = LY.floor_z(fl)
    for (x0, x1, y0, y1, z0, z1, rx) in coll:
        if z1 < zf + 0.3 or z0 > zf + 1.6 or x1 - x0 > 30:
            continue
        a, b = P(x0, y1), P(x1, y0)
        dr.rectangle([a, b], fill=(70, 70, 75) if rx == 0 else (150, 150, 230))
    for (cx, cy, wd, dd, hh, yaw, z0, kind) in navigation.furniture_boxes(L):
        if abs(z0 - zf) > 1.2 and not (fl == 1 and z0 > LY.H1 - 0.1) and not (fl == 0 and z0 < LY.H1 - 0.5):
            continue
        if (fl == 0 and z0 >= LY.H1 - 0.1) or (fl == 1 and z0 < LY.H1 - 0.1):
            continue
        a = math.radians(yaw)
        pts = []
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            lx, ly = sx * wd / 2, sy * dd / 2
            pts.append(P(cx + lx * math.cos(a) - ly * math.sin(a), cy + lx * math.sin(a) + ly * math.cos(a)))
        col = (196, 160, 120) if kind in props.RODIN else (170, 180, 200)
        if kind in props.NO_COLLIDE:
            dr.polygon(pts, outline=col)
        else:
            dr.polygon(pts, fill=col + (0,), outline=(90, 70, 50))
        # front marker
        fx, fy = cx + math.sin(a) * dd / 2, cy - math.cos(a) * dd / 2
        dr.ellipse([P(fx, fy)[0] - 3, P(fx, fy)[1] - 3, P(fx, fy)[0] + 3, P(fx, fy)[1] + 3], fill=(200, 40, 40))
        c = P(cx, cy)
        dr.text((c[0] - 20, c[1] - 6), kind, fill=(20, 20, 20), font=f12)
    # doors
    for d in L["doors"]:
        if d["floor"] != fl:
            continue
        c = P(d["x"], d["y"])
        col = (220, 40, 40) if d["lock"] else (40, 140, 40)
        dr.ellipse([c[0] - 6, c[1] - 6, c[0] + 6, c[1] + 6], fill=col)
        dr.text((c[0] + 8, c[1] - 14), d["name"].replace("door_", ""), fill=col, font=f12)
    # items
    for k, v in L["items"].items():
        for sp in v["spots"]:
            sfl = 1 if sp["z"] >= LY.H1 - 0.1 else 0
            if sfl != fl:
                continue
            c = P(sp["x"], sp["y"])
            dr.rectangle([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], fill=(230, 160, 0))
            dr.text((c[0] + 6, c[1] + 2), k, fill=(160, 100, 0), font=f12)
    # patrol, spawn, trader start
    for (x, y, pf) in LY.PATROL:
        if pf == fl:
            c = P(x, y)
            dr.ellipse([c[0] - 5, c[1] - 5, c[0] + 5, c[1] + 5], outline=(140, 0, 160), width=2)
    if LY.SPAWN["floor"] == fl:
        c = P(LY.SPAWN["x"], LY.SPAWN["y"])
        dr.polygon([(c[0], c[1] - 10), (c[0] - 7, c[1] + 6), (c[0] + 7, c[1] + 6)], fill=(0, 120, 255))
        dr.text((c[0] + 8, c[1]), "YOU", fill=(0, 90, 200), font=f14)
    if LY.TRADER_START[2] == fl:
        c = P(LY.TRADER_START[0], LY.TRADER_START[1])
        dr.ellipse([c[0] - 8, c[1] - 8, c[0] + 8, c[1] + 8], fill=(200, 0, 0))
        dr.text((c[0] + 10, c[1]), "TRADER", fill=(200, 0, 0), font=f14)
    dr.text((M, h - 28), ("GROUND FLOOR" if fl == 0 else "FIRST FLOOR") + "  (1 m = %d px)" % S, fill=(0, 0, 0), font=f14)
    return im


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "plan.png"
    L = LY.build()
    chunks, dyn, coll, extra = architecture.build(L)
    G = navigation.grid(L, coll)
    a, b = plan(0, L, G, coll), plan(1, L, G, coll)
    im = Image.new("RGB", (a.width, a.height + b.height), (255, 255, 255))
    im.paste(b, (0, 0))
    im.paste(a, (0, b.height))
    im.save(out)
    st = (1, int(LY.SPAWN["x"] / G["cell"]), int(LY.SPAWN["y"] / G["cell"]))
    R = navigation.reach(G, st[0], st[1:])
    tot = sum(int(G["layers"][k].sum()) for k in (0, 1, 2))
    print("walk cells: %d, reachable from the spawn: %d" % (tot, len(R)))
    for (x, y, pf) in LY.PATROL:
        c = (pf, int(x / G["cell"]), int(y / G["cell"]))
        if c not in R:
            print("  patrol point not reachable:", (x, y, pf))
    c = (LY.TRADER_START[2], int(LY.TRADER_START[0] / G["cell"]), int(LY.TRADER_START[1] / G["cell"]))
    print("trader start reachable:", c in R)


if __name__ == "__main__":
    main()
