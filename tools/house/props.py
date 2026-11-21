"""Code-built furniture and fittings for the trader's house (numpy only).

Every builder returns (geo, parts) in the piece's own frame: x across, y depth (front = -y), z up, origin on the
floor at the footprint centre. `parts` are moving pieces {name: (geo relative to its pivot, pivot)}: the safe door,
the locked drawer, the fuse box door, the six monitor screens and the LED cove of the trading room.

Pieces that have a Hyper3D (Rodin) model (RODIN) use the model; the builders here are their stand-ins when a model
is missing. FOOTPRINT gives the box each model is fitted into: (w, d, h, y offset).
"""
import math

import numpy as np

from geo import Geo, rot_z

# kind -> Rodin model name
RODIN = {
    "tv_unit": "tv_unit", "sofa": "sofa", "sofa_trading": "sofa", "coffee_table": "coffee_table", "fridge": "fridge",
    "dining_set": "dining_set", "plant": "plant", "bed": "bed", "bed_guest": "bed", "wardrobe": "wardrobe",
    "tall_cabinet": "wardrobe", "trading_desk": "trading_desk", "gaming_chair": "gaming_chair", "gaming_pc": "gaming_pc",
    "toolbox": "toolbox", "trophy": "trophy",
}

FOOTPRINT = {
    "tv_unit": (1.9, 0.45, 1.28, 0.0), "sofa": (2.55, 1.55, 0.86, 0.0), "sofa_trading": (2.1, 1.1, 0.84, 0.0),
    "coffee_table": (1.2, 0.65, 0.42, 0.0), "fridge": (0.86, 0.74, 1.82, 0.0), "dining_set": (2.3, 1.9, 0.96, 0.0),
    "plant": (0.75, 0.75, 1.75, 0.0), "bed": (2.05, 2.25, 1.15, 0.0), "bed_guest": (1.65, 2.1, 1.05, 0.0),
    "wardrobe": (1.3, 0.62, 2.2, 0.0), "tall_cabinet": (0.82, 0.55, 2.0, 0.0), "trading_desk": (2.4, 0.86, 0.76, 0.0),
    "gaming_chair": (0.72, 0.72, 1.36, 0.0), "gaming_pc": (0.24, 0.5, 0.52, 0.0), "toolbox": (0.52, 0.28, 0.32, 0.0),
    "trophy": (0.2, 0.2, 0.4, 0.0),
    # code-built
    "rug": (3.0, 2.2, 0.012, 0.0), "rug_small": (1.6, 1.1, 0.012, 0.0), "rug_dark": (2.6, 1.9, 0.012, 0.0),
    "floor_lamp": (0.4, 0.4, 1.65, 0.0), "armchair": (0.85, 0.85, 0.82, 0.0), "kitchen_run": (7.7, 0.62, 0.94, 0.0),
    "island": (2.6, 1.0, 0.94, 0.0), "stool": (0.42, 0.42, 0.78, 0.0), "pendant": (0.3, 0.3, 0.9, 0.0),
    "console": (1.4, 0.36, 0.8, 0.0), "hall_bench": (1.2, 0.42, 0.46, 0.0), "workbench": (2.4, 0.7, 0.92, 0.0),
    "shelf_unit": (1.8, 0.45, 1.9, 0.0), "boxes": (1.0, 0.6, 1.0, 0.0), "fusebox": (0.42, 0.14, 0.56, 0.0),
    "washer": (0.6, 0.62, 0.86, 0.0), "utility_shelf": (1.5, 0.36, 1.7, 0.0), "nightstand": (0.5, 0.4, 0.55, 0.0),
    "vanity": (1.3, 0.5, 0.86, 0.0), "toilet": (0.4, 0.66, 0.8, 0.0), "shower": (1.4, 1.4, 2.1, 0.0),
    "bench": (1.6, 0.42, 0.46, 0.0), "monitors": (2.0, 0.3, 0.85, 0.0), "drawers": (0.48, 0.6, 0.64, 0.0),
    "wall_shelf": (1.3, 0.26, 0.04, 0.0), "led_cove": (8.4, 6.0, 0.03, 0.0), "safe": (0.52, 0.5, 0.62, 0.0),
}
# pieces you can walk through, or that stand on other pieces / walls: no collision box
NO_COLLIDE = {"rug", "rug_small", "rug_dark", "pendant", "led_cove", "monitors", "trophy", "toolbox", "fusebox",
              "wall_shelf", "shower"}


def _g(name):
    return Geo(name)


# ------------------------------------------------------------------------------------------------------ helpers
def box(g, x0, x1, y0, y1, z0, z1, mat, mats=None):
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat, mats=mats)


def legs4(g, w, d, h, t, mat, inset=0.03):
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = sx * (w / 2 - inset - t / 2)
            cy = sy * (d / 2 - inset - t / 2)
            box(g, cx - t / 2, cx + t / 2, cy - t / 2, cy + t / 2, 0.0, h, mat)


def disc(g, c, r, z, mat, seg=20, up=True):
    pts = [g.vert((c[0] + r * math.cos(2 * math.pi * k / seg), c[1] + r * math.sin(2 * math.pi * k / seg), z)) for k in range(seg)]
    g.face(pts if up else pts[::-1], mat)


# ------------------------------------------------------------------------------------------------------ living
def rug(w=3.0, d=2.2, mat="rug_fabric"):
    g = _g("rug")
    box(g, -w / 2, w / 2, -d / 2, d / 2, 0.0, 0.012, mat)
    return g, {}


def floor_lamp():
    g = _g("floor_lamp")
    g.cyl((0, 0, 0.0), (0, 0, 0.03), 0.17, "metal_black", seg=20)
    g.cyl((0, 0, 0.03), (0, 0, 1.38), 0.013, "metal_black", seg=8, caps=False)
    g.lathe([(0.2, 1.36), (0.2, 1.38), (0.17, 1.62), (0.165, 1.64)], (0, 0, 0), "lampshade", seg=24)
    g.cyl((0, 0, 1.42), (0, 0, 1.5), 0.04, "bulb_glow", seg=10)
    return g, {}


def armchair():
    g = _g("armchair")
    box(g, -0.42, 0.42, -0.42, 0.42, 0.1, 0.42, "fabric_grey")          # seat block
    box(g, -0.42, 0.42, 0.24, 0.42, 0.42, 0.82, "fabric_grey")          # back
    for sx in (-1, 1):
        x0, x1 = (0.32, 0.44) if sx > 0 else (-0.44, -0.32)
        box(g, x0, x1, -0.42, 0.42, 0.1, 0.62, "fabric_grey")
    box(g, -0.36, 0.36, -0.4, 0.22, 0.42, 0.5, "fabric_light")         # cushion
    legs4(g, 0.8, 0.8, 0.1, 0.04, "wood_walnut", 0.04)
    return g, {}


# ------------------------------------------------------------------------------------------------------ kitchen
def kitchen_run():
    """Base cabinets along the north wall (the piece's back is +y), counter, sink, hob, two tall wall units."""
    g = _g("kitchen_run")
    L, Dp = 7.7, 0.62
    x0, x1 = -L / 2, L / 2
    box(g, x0, x1, -Dp / 2 + 0.05, Dp / 2, 0.0, 0.1, "metal_black")               # plinth
    box(g, x0, x1, -Dp / 2 + 0.02, Dp / 2, 0.1, 0.9, "cabinet_white")             # carcass
    # door / drawer fronts as thin raised panels with gaps
    n = 10
    for i in range(n):
        a = x0 + i * L / n + 0.004
        b = x0 + (i + 1) * L / n - 0.004
        box(g, a, b, -Dp / 2, -Dp / 2 + 0.02, 0.12, 0.88, "cabinet_white")
        box(g, a + 0.05, b - 0.05, -Dp / 2 - 0.025, -Dp / 2, 0.8, 0.82, "metal_brushed")   # bar handle
    box(g, x0, x1, -Dp / 2 - 0.02, Dp / 2, 0.9, 0.94, "marble")                   # counter
    # sink (centre, under the window) and tap
    box(g, -0.4, 0.4, -0.2, 0.18, 0.905, 0.942, "metal_brushed")
    box(g, -0.36, 0.36, -0.17, 0.15, 0.943, 0.944, "sink_dark")
    g.cyl((0.0, 0.24, 0.94), (0.0, 0.24, 1.25), 0.016, "metal_brushed", seg=10)
    g.cyl((0.0, 0.24, 1.25), (0.0, 0.08, 1.25), 0.014, "metal_brushed", seg=10)
    # hob
    box(g, 1.5, 2.2, -0.24, 0.24, 0.94, 0.946, "glass_black")
    # tall units at both ends (above the counter, beside the window)
    for (a, b) in ((x0 + 0.0, x0 + 0.85), (x1 - 1.6, x1)):
        box(g, a, b, 0.0, Dp / 2, 1.5, 2.45, "cabinet_white")
        box(g, a + 0.004, b - 0.004, -0.02, 0.0, 1.52, 2.43, "cabinet_white")
    return g, {}


def island():
    g = _g("island")
    box(g, -1.25, 1.25, -0.45, 0.45, 0.0, 0.9, "cabinet_oak")
    box(g, -1.3, 1.3, -0.5, 0.5, 0.9, 0.94, "marble")
    return g, {}


def stool():
    g = _g("stool")
    g.cyl((0, 0, 0.0), (0, 0, 0.02), 0.2, "metal_black", seg=18)
    g.cyl((0, 0, 0.02), (0, 0, 0.72), 0.025, "metal_black", seg=8, caps=False)
    g.lathe([(0.25, 0.3), (0.26, 0.31)], (0, 0, 0), "metal_black", seg=18)
    g.cyl((0, 0, 0.72), (0, 0, 0.78), 0.19, "leather_black", seg=18)
    return g, {}


def pendant():
    g = _g("pendant")
    g.cyl((0, 0, 2.3), (0, 0, 3.05), 0.004, "metal_black", seg=4, caps=False)
    g.lathe([(0.03, 2.33), (0.16, 2.2), (0.17, 2.15)], (0, 0, 0), "metal_black", seg=20)
    g.cyl((0, 0, 2.17), (0, 0, 2.23), 0.05, "bulb_glow", seg=10)
    return g, {}


def fridge():
    g = _g("fridge")
    box(g, -0.43, 0.43, -0.37, 0.37, 0.0, 1.82, "metal_brushed")
    for x in (-0.03, 0.03):
        box(g, x - 0.012, x + 0.012, -0.4, -0.37, 0.9, 1.6, "metal_brushed")
    return g, {}


# ------------------------------------------------------------------------------------------------------ hall / lounge
def console():
    g = _g("console")
    box(g, -0.7, 0.7, -0.18, 0.18, 0.76, 0.8, "wood_walnut")
    for sx in (-1, 1):
        box(g, sx * 0.66 - 0.02, sx * 0.66 + 0.02, -0.15, 0.15, 0.0, 0.76, "metal_black")
    box(g, -0.5, 0.5, 0.15, 0.17, 1.15, 1.95, "mirror")                       # mirror on the wall behind
    box(g, -0.52, 0.52, 0.17, 0.18, 1.13, 1.97, "metal_black")
    return g, {}


def bench(w=1.6):
    g = _g("bench")
    box(g, -w / 2, w / 2, -0.21, 0.21, 0.4, 0.46, "wood_oak")
    for sx in (-1, 1):
        box(g, sx * (w / 2 - 0.08) - 0.02, sx * (w / 2 - 0.08) + 0.02, -0.18, 0.18, 0.0, 0.4, "metal_black")
    return g, {}


# ------------------------------------------------------------------------------------------------------ garage / utility
def workbench():
    g = _g("workbench")
    box(g, -1.2, 1.2, -0.35, 0.35, 0.86, 0.92, "wood_oak")
    legs4(g, 2.4, 0.7, 0.86, 0.05, "metal_painted", 0.05)
    box(g, -1.15, 1.15, -0.3, 0.3, 0.2, 0.23, "wood_oak")                      # lower shelf
    box(g, -1.2, 1.2, 0.33, 0.35, 0.95, 1.85, "pegboard")                      # pegboard on the wall
    return g, {}


def shelf_unit():
    g = _g("shelf_unit")
    for sx in (-1, 1):
        for sy in (-1, 1):
            box(g, sx * 0.88 - 0.02, sx * 0.88 + 0.02, sy * 0.2 - 0.02, sy * 0.2 + 0.02, 0.0, 1.9, "metal_painted")
    for z in (0.15, 0.6, 1.05, 1.5):
        box(g, -0.9, 0.9, -0.22, 0.22, z - 0.015, z + 0.015, "metal_painted")
    rng = np.random.default_rng(3)
    for z in (0.165, 0.615, 1.515):
        x = -0.8
        while x < 0.6:
            w = rng.uniform(0.25, 0.45)
            box(g, x, x + w, -0.17, 0.17, z, z + rng.uniform(0.18, 0.32), "cardboard")
            x += w + rng.uniform(0.05, 0.2)
    return g, {}


def boxes():
    g = _g("boxes")
    box(g, -0.5, 0.05, -0.3, 0.3, 0.0, 0.45, "cardboard")
    box(g, 0.1, 0.5, -0.25, 0.28, 0.0, 0.5, "cardboard")
    box(g, -0.42, 0.0, -0.25, 0.25, 0.45, 0.82, "cardboard")
    return g, {}


def fusebox():
    """Grey steel cabinet on the wall: body + a door hinged on its left (part 'fusebox_door')."""
    g = _g("fusebox")
    box(g, -0.21, 0.21, -0.07, 0.07, 0.0, 0.56, "metal_painted")
    box(g, -0.17, 0.17, -0.072, -0.07, 0.06, 0.5, "fuse_panel")               # breakers behind the door
    door = _g("fusebox_door")
    box(door, 0.0, 0.42, -0.012, 0.0, 0.0, 0.56, "metal_painted")
    box(door, 0.34, 0.38, -0.03, -0.012, 0.24, 0.32, "metal_black")
    return g, {"fusebox_door": (door, (-0.21, -0.072, 0.0))}


def washer():
    g = _g("washer")
    box(g, -0.3, 0.3, -0.31, 0.31, 0.0, 0.85, "appliance_white")
    g.cyl((0, -0.31, 0.42), (0, -0.33, 0.42), 0.2, "glass_black", seg=24)
    box(g, -0.26, 0.26, -0.315, -0.31, 0.72, 0.82, "plastic_grey")
    return g, {}


def utility_shelf():
    g = _g("utility_shelf")
    for sx in (-1, 1):
        box(g, sx * 0.73 - 0.02, sx * 0.73 + 0.02, -0.17, 0.17, 0.0, 1.7, "wood_oak")
    for z in (0.4, 0.82, 1.24, 1.66):
        box(g, -0.75, 0.75, -0.18, 0.18, z - 0.02, z, "wood_oak")
    rng = np.random.default_rng(5)
    for z in (0.4, 0.82):
        x = -0.68
        while x < 0.5:
            w = rng.uniform(0.15, 0.3)
            box(g, x, x + w, -0.12, 0.12, z, z + rng.uniform(0.18, 0.3), "cardboard" if rng.random() < 0.6 else "plastic_blue")
            x += w + 0.06
    return g, {}


# ------------------------------------------------------------------------------------------------------ bedrooms / bath
def nightstand():
    g = _g("nightstand")
    box(g, -0.25, 0.25, -0.2, 0.2, 0.06, 0.55, "wood_walnut")
    box(g, -0.23, 0.23, -0.205, -0.2, 0.33, 0.52, "wood_walnut")
    box(g, -0.05, 0.05, -0.22, -0.205, 0.41, 0.43, "metal_brushed")
    legs4(g, 0.48, 0.38, 0.06, 0.03, "metal_black", 0.02)
    # table lamp
    g.cyl((0.08, 0.04, 0.55), (0.08, 0.04, 0.57), 0.07, "metal_black", seg=14)
    g.cyl((0.08, 0.04, 0.57), (0.08, 0.04, 0.72), 0.01, "metal_black", seg=6, caps=False)
    g.lathe([(0.13, 0.66), (0.1, 0.84)], (0.08, 0.04, 0), "lampshade", seg=18)
    g.cyl((0.08, 0.04, 0.7), (0.08, 0.04, 0.76), 0.03, "bulb_glow", seg=8)
    return g, {}


def vanity():
    g = _g("vanity")
    box(g, -0.65, 0.65, -0.25, 0.25, 0.25, 0.82, "wood_walnut")
    box(g, -0.67, 0.67, -0.27, 0.25, 0.82, 0.86, "marble")
    g.lathe([(0.0, 0.84), (0.2, 0.845), (0.22, 0.9), (0.2, 0.9)], (0.0, -0.02, 0), "ceramic_white", seg=24)
    g.cyl((0.0, 0.18, 0.86), (0.0, 0.18, 1.08), 0.014, "metal_brushed", seg=8)
    g.cyl((0.0, 0.18, 1.08), (0.0, 0.05, 1.08), 0.012, "metal_brushed", seg=8)
    box(g, -0.6, 0.6, 0.23, 0.25, 1.05, 1.95, "mirror")
    box(g, -0.62, 0.62, 0.245, 0.255, 1.03, 1.97, "metal_black")
    return g, {}


def toilet():
    g = _g("toilet")
    box(g, -0.18, 0.18, 0.12, 0.33, 0.0, 0.8, "ceramic_white")                # cistern block (back = +y)
    g.lathe([(0.12, 0.0), (0.16, 0.2), (0.19, 0.38), (0.18, 0.4), (0.0, 0.41)], (0.0, -0.08, 0), "ceramic_white", seg=20)
    return g, {}


def shower():
    g = _g("shower")
    box(g, -0.7, 0.7, -0.7, 0.7, 0.0, 0.04, "ceramic_white")
    box(g, -0.7, 0.7, -0.705, -0.695, 0.04, 2.0, "glass")
    box(g, 0.695, 0.705, -0.7, 0.7, 0.04, 2.0, "glass")
    g.cyl((-0.55, 0.62, 1.2), (-0.55, 0.62, 2.0), 0.012, "metal_brushed", seg=8)
    g.cyl((-0.55, 0.62, 2.0), (-0.55, 0.4, 2.0), 0.012, "metal_brushed", seg=8)
    g.cyl((-0.55, 0.4, 1.99), (-0.55, 0.4, 2.02), 0.1, "metal_brushed", seg=16)
    return g, {}


def safe():
    """Steel floor safe (front = -y): body and a door hinged on its left with a keypad (part 'safe_door')."""
    g = _g("safe")
    w, d, h = 0.52, 0.5, 0.62
    t = 0.04
    box(g, -w / 2, w / 2, -d / 2 + 0.03, d / 2, 0.0, t, "safe_steel")
    box(g, -w / 2, w / 2, -d / 2 + 0.03, d / 2, h - t, h, "safe_steel")
    box(g, -w / 2, -w / 2 + t, -d / 2 + 0.03, d / 2, t, h - t, "safe_steel")
    box(g, w / 2 - t, w / 2, -d / 2 + 0.03, d / 2, t, h - t, "safe_steel")
    box(g, -w / 2, w / 2, d / 2 - t, d / 2, t, h - t, "safe_steel")
    box(g, -w / 2 + t, w / 2 - t, -d / 2 + 0.05, d / 2 - t, 0.06, 0.07, "felt_dark")   # inside floor
    door = _g("safe_door")
    box(door, 0.0, w, -0.04, 0.0, 0.0, h, "safe_steel")
    box(door, w - 0.2, w - 0.06, -0.046, -0.04, h - 0.27, h - 0.08, "keypad_face")
    box(door, w - 0.15, w - 0.11, -0.07, -0.04, h * 0.32, h * 0.46, "metal_brushed")  # handle
    return g, {"safe_door": (door, (-w / 2, -d / 2 + 0.03, 0.0))}


# ------------------------------------------------------------------------------------------------------ trading room
MON_W, MON_H = 0.62, 0.37        # screen size (m)
MON_POS = [(-0.66, 0.12, -14), (0.0, 0.12, 0), (0.66, 0.12, 14), (-0.66, 0.52, -14), (0.0, 0.52, 0), (0.66, 0.52, 14)]


def monitors():
    """Six monitors in two rows on a desk mount (origin on the desk top). Screens are parts screen_0..5."""
    g = _g("monitors")
    parts = {}
    g.cyl((0, 0.05, 0.0), (0, 0.05, 0.95), 0.025, "metal_black", seg=10)
    box(g, -0.12, 0.12, -0.05, 0.15, 0.0, 0.02, "metal_black")
    for k, (cx, cz, yaw) in enumerate(MON_POS):
        R = rot_z(yaw)
        c = np.array([cx, 0.0, 0.25 + cz])
        bez = Geo("bezel")
        bez.box((0, 0.012, 0), (MON_W + 0.03, 0.03, MON_H + 0.03), "plastic_black")
        bez.box((0, 0.05, 0), (0.12, 0.05, 0.1), "metal_black")
        g.merge(bez, R=R, T=c)
        # arm back to the pole
        g.cyl(tuple(c + R @ np.array([0, 0.06, 0])), (0.0, 0.05, c[2]), 0.012, "metal_black", seg=6, caps=False)
        scr = Geo("screen_%d" % k)
        hw, hh = MON_W / 2, MON_H / 2
        a = scr.vert((-hw, -0.0035, -hh))
        b = scr.vert((hw, -0.0035, -hh))
        cc = scr.vert((hw, -0.0035, hh))
        dd = scr.vert((-hw, -0.0035, hh))
        scr.face([a, b, cc, dd], "screen", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
        sg = Geo("screen_%d" % k)
        sg.merge(scr, R=R)
        parts["screen_%d" % k] = (sg, tuple(c))
    # keyboard and mouse on the desk in front
    box(g, -0.24, 0.24, -0.42, -0.28, -0.0, 0.02, "plastic_black")
    box(g, 0.34, 0.4, -0.38, -0.3, 0.0, 0.025, "plastic_black")
    box(g, -0.45, 0.45, -0.5, -0.2, -0.0, 0.003, "deskmat")
    return g, parts


def drawers():
    """Pedestal with three drawers (front = -y); the top one is locked: part 'drawer_top' slides out along -y."""
    g = _g("drawers")
    w, d, h = 0.48, 0.6, 0.64
    box(g, -w / 2, w / 2, -d / 2 + 0.02, d / 2, 0.0, 0.03, "metal_black")
    box(g, -w / 2, w / 2, -d / 2 + 0.02, d / 2, h - 0.02, h, "wood_walnut")
    box(g, -w / 2, -w / 2 + 0.02, -d / 2 + 0.02, d / 2, 0.03, h - 0.02, "metal_black")
    box(g, w / 2 - 0.02, w / 2, -d / 2 + 0.02, d / 2, 0.03, h - 0.02, "metal_black")
    box(g, -w / 2, w / 2, d / 2 - 0.02, d / 2, 0.03, h - 0.02, "metal_black")
    for (z0, z1) in ((0.04, 0.24), (0.25, 0.43)):
        box(g, -w / 2 + 0.022, w / 2 - 0.022, -d / 2, -d / 2 + 0.02, z0, z1, "metal_black")
        box(g, -0.08, 0.08, -d / 2 - 0.015, -d / 2, z1 - 0.05, z1 - 0.035, "metal_brushed")
    dr = _g("drawer_top")
    zt0, zt1 = 0.44, h - 0.025
    box(dr, -w / 2 + 0.022, w / 2 - 0.022, -0.02, 0.0, 0.0, zt1 - zt0, "metal_black")         # front
    box(dr, -0.08, 0.08, -0.035, -0.02, zt1 - zt0 - 0.05, zt1 - zt0 - 0.035, "metal_brushed")
    box(dr, -w / 2 + 0.03, w / 2 - 0.03, 0.0, d - 0.08, 0.0, 0.01, "metal_black")              # tray
    box(dr, -w / 2 + 0.03, w / 2 - 0.03, d - 0.09, d - 0.08, 0.0, 0.1, "metal_black")
    box(dr, 0.1, 0.13, -0.025, -0.02, zt1 - zt0 - 0.04, zt1 - zt0 - 0.01, "brass")             # keyhole
    return g, {"drawer_top": (dr, (0.0, -d / 2 + 0.02, zt0))}


def wall_shelf():
    g = _g("wall_shelf")
    box(g, -0.65, 0.65, -0.13, 0.13, 0.0, 0.035, "wood_walnut")
    return g, {}


def led_cove():
    """Thin LED strip loop along the trading room ceiling (one part, switched on with the power)."""
    g = _g("led_cove")
    led = _g("led")
    w, d = 8.5, 6.1
    z = 2.86
    t = 0.03
    for (x0, x1, y0, y1) in ((-w / 2, w / 2, -d / 2, -d / 2 + t), (-w / 2, w / 2, d / 2 - t, d / 2),
                             (-w / 2, -w / 2 + t, -d / 2, d / 2), (w / 2 - t, w / 2, -d / 2, d / 2)):
        box(led, x0, x1, y0, y1, z, z + 0.02, "led")
    return g, {"led_strip": (led, (0.0, 0.0, 0.0))}


# ------------------------------------------------------------------------------------------------------ stand-ins for Rodin kinds
def tv_unit():
    g = _g("tv_unit")
    box(g, -0.95, 0.95, -0.22, 0.22, 0.05, 0.5, "wood_walnut")
    box(g, -0.8, 0.8, -0.05, 0.0, 0.55, 1.28, "glass_black")
    box(g, -0.15, 0.15, -0.1, 0.05, 0.5, 0.55, "metal_black")
    return g, {}


def sofa(w=2.55, d=1.55):
    g = _g("sofa")
    box(g, -w / 2, w / 2, -0.45, 0.45, 0.12, 0.45, "fabric_grey")
    box(g, -w / 2, w / 2, 0.25, 0.45, 0.45, 0.86, "fabric_grey")
    box(g, -w / 2, -w / 2 + 0.85, -d / 2, -0.45, 0.12, 0.45, "fabric_grey")
    legs4(g, w - 0.1, 0.8, 0.12, 0.04, "metal_black")
    return g, {}


def coffee_table():
    g = _g("coffee_table")
    box(g, -0.6, 0.6, -0.32, 0.32, 0.38, 0.42, "marble")
    legs4(g, 1.16, 0.6, 0.38, 0.025, "metal_black", 0.02)
    return g, {}


def dining_set():
    g = _g("dining_set")
    box(g, -1.0, 1.0, -0.5, 0.5, 0.72, 0.76, "wood_oak")
    legs4(g, 1.9, 0.9, 0.72, 0.06, "wood_oak")
    for (x, y, yaw) in ((-0.55, -0.82, 0), (0.0, -0.82, 0), (0.55, -0.82, 0), (-0.55, 0.82, 180), (0.0, 0.82, 180), (0.55, 0.82, 180)):
        c = Geo("chair")
        box(c, -0.21, 0.21, -0.21, 0.21, 0.42, 0.47, "fabric_grey")
        box(c, -0.21, 0.21, 0.17, 0.21, 0.47, 0.92, "fabric_grey")
        legs4(c, 0.4, 0.4, 0.42, 0.03, "metal_black", 0.02)
        g.merge(c, R=rot_z(yaw), T=(x, y, 0))
    return g, {}


def plant():
    g = _g("plant")
    g.lathe([(0.0, 0.0), (0.2, 0.0), (0.26, 0.5), (0.24, 0.5), (0.0, 0.48)], (0, 0, 0), "ceramic_white", seg=20)
    g.cyl((0, 0, 0.48), (0, 0, 1.2), 0.02, "bark", seg=6, caps=False)
    g.lathe([(0.05, 0.9), (0.33, 1.2), (0.3, 1.5), (0.05, 1.75)], (0, 0, 0), "leaves", seg=10)
    return g, {}


def bed(w=2.05, d=2.25, h=1.15):
    g = _g("bed")
    box(g, -w / 2, w / 2, -d / 2, d / 2 - 0.1, 0.1, 0.32, "wood_walnut")
    box(g, -w / 2 + 0.05, w / 2 - 0.05, -d / 2 + 0.03, d / 2 - 0.12, 0.32, 0.55, "bedding_white")
    box(g, -w / 2, w / 2, d / 2 - 0.1, d / 2, 0.1, h, "fabric_grey")
    for sx in (-1, 1):
        box(g, sx * w / 4 - 0.32, sx * w / 4 + 0.32, d / 2 - 0.55, d / 2 - 0.15, 0.55, 0.68, "bedding_white")
    return g, {}


def wardrobe(w=1.3, d=0.62, h=2.2):
    g = _g("wardrobe")
    box(g, -w / 2, w / 2, -d / 2, d / 2, 0.0, h, "wood_walnut")
    box(g, -0.006, 0.006, -d / 2 - 0.004, -d / 2, 0.05, h - 0.05, "metal_black")
    for sx in (-1, 1):
        box(g, sx * 0.04 - 0.01, sx * 0.04 + 0.01, -d / 2 - 0.03, -d / 2, h * 0.4, h * 0.6, "metal_black")
    return g, {}


def trading_desk():
    g = _g("trading_desk")
    box(g, -1.2, 1.2, -0.43, 0.43, 0.72, 0.76, "wood_walnut")
    for sx in (-1, 1):
        box(g, sx * 1.12 - 0.03, sx * 1.12 + 0.03, -0.38, 0.38, 0.0, 0.72, "metal_black")
    return g, {}


def gaming_chair():
    g = _g("gaming_chair")
    g.cyl((0, 0, 0.06), (0, 0, 0.45), 0.03, "metal_black", seg=8)
    for k in range(5):
        a = 2 * math.pi * k / 5
        g.cyl((0, 0, 0.07), (0.32 * math.cos(a), 0.32 * math.sin(a), 0.07), 0.02, "plastic_black", seg=6)
    box(g, -0.27, 0.27, -0.27, 0.27, 0.45, 0.55, "leather_black")
    box(g, -0.27, 0.27, 0.2, 0.3, 0.55, 1.36, "leather_black")
    box(g, -0.18, 0.18, 0.18, 0.2, 0.7, 1.2, "leather_red")
    return g, {}


def gaming_pc():
    g = _g("gaming_pc")
    box(g, -0.12, 0.12, -0.25, 0.25, 0.0, 0.52, "plastic_black")
    box(g, -0.122, -0.12, -0.22, 0.22, 0.05, 0.48, "glass_rgb")
    return g, {}


def toolbox():
    g = _g("toolbox")
    box(g, -0.26, 0.26, -0.14, 0.14, 0.0, 0.26, "paint_red")
    g.cyl((-0.15, 0, 0.3), (0.15, 0, 0.3), 0.015, "metal_black", seg=6)
    return g, {}


def trophy():
    g = _g("trophy")
    box(g, -0.08, 0.08, -0.08, 0.08, 0.0, 0.08, "marble_black")
    g.lathe([(0.03, 0.08), (0.02, 0.2), (0.09, 0.3), (0.1, 0.4), (0.0, 0.33)], (0, 0, 0), "gold", seg=20)
    return g, {}


BUILDERS = {
    "rug": lambda: rug(3.0, 2.2), "rug_small": lambda: rug(1.6, 1.1), "rug_dark": lambda: rug(2.6, 1.9, "rug_dark"),
    "floor_lamp": floor_lamp, "armchair": armchair, "kitchen_run": kitchen_run, "island": island, "stool": stool,
    "pendant": pendant, "fridge": fridge, "console": console, "hall_bench": lambda: bench(1.2), "bench": bench,
    "workbench": workbench, "shelf_unit": shelf_unit, "boxes": boxes, "fusebox": fusebox, "washer": washer,
    "utility_shelf": utility_shelf, "nightstand": nightstand, "vanity": vanity, "toilet": toilet, "shower": shower,
    "safe": safe, "monitors": monitors, "drawers": drawers, "wall_shelf": wall_shelf, "led_cove": led_cove,
    "tv_unit": tv_unit, "sofa": sofa, "sofa_trading": lambda: sofa(2.1, 1.1), "coffee_table": coffee_table,
    "dining_set": dining_set, "plant": plant, "bed": bed, "bed_guest": lambda: bed(1.65, 2.1, 1.05),
    "wardrobe": wardrobe, "tall_cabinet": lambda: wardrobe(0.82, 0.55, 2.0), "trading_desk": trading_desk,
    "gaming_chair": gaming_chair, "gaming_pc": gaming_pc, "toolbox": toolbox, "trophy": trophy,
}


# ------------------------------------------------------------------------------------------------------ items
def item_geo(name):
    """Stand-in models for the things you pick up (origin at the bottom centre)."""
    g = Geo(name)
    if name in ("garage_key", "gold_key", "silver_key", "drawer_key"):
        mat = {"gold_key": "gold", "silver_key": "metal_brushed", "garage_key": "brass", "drawer_key": "brass"}[name]
        s = 0.6 if name == "drawer_key" else 1.0
        g.cyl((-0.035 * s, 0, 0.004), (-0.035 * s, 0, 0.012), 0.022 * s, mat, seg=14)
        box(g, -0.015 * s, 0.07 * s, -0.004, 0.004, 0.004, 0.012, mat)
        box(g, 0.045 * s, 0.07 * s, 0.004, 0.016 * s, 0.004, 0.012, mat)
    elif name == "hammer":
        box(g, -0.15, 0.15, -0.012, 0.012, 0.0, 0.026, "wood_handle")
        box(g, 0.13, 0.18, -0.05, 0.05, 0.0, 0.026, "metal_brushed")
    elif name == "fuse":
        g.cyl((-0.05, 0, 0.018), (0.05, 0, 0.018), 0.017, "ceramic_white", seg=12)
        g.cyl((-0.065, 0, 0.018), (-0.05, 0, 0.018), 0.019, "brass", seg=12)
        g.cyl((0.05, 0, 0.018), (0.065, 0, 0.018), 0.019, "brass", seg=12)
    elif name == "padlock":
        box(g, -0.045, 0.045, -0.018, 0.018, 0.0, 0.07, "brass")
        g.lathe([(0.03, 0.07), (0.03, 0.11), (0.0, 0.125)], (0, 0, 0), "steel", seg=10)
    return g


ITEM_BOX = {   # size each picked-up model is fitted into (x, y, z)
    "garage_key": (0.11, 0.035, 0.012), "gold_key": (0.11, 0.035, 0.012), "silver_key": (0.11, 0.035, 0.012),
    "drawer_key": (0.065, 0.022, 0.008), "hammer": (0.33, 0.1, 0.03), "fuse": (0.13, 0.04, 0.04),
    "padlock": (0.09, 0.04, 0.125),
}
ITEM_RODIN = {"garage_key": "key", "gold_key": "key", "silver_key": "key", "drawer_key": "key", "hammer": "hammer",
              "fuse": "fuse", "padlock": "padlock"}
