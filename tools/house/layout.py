"""TRADER'S MADNESS - the binary trader's two-storey modern house, as data (numpy only).

Blender axes: x east, y north, z up, metres. The house covers x 0..18, y 0..12.
Ground floor at z = 0, first floor at z = 3.3 (ceilings at 3.05 and 6.3).

    GROUND FLOOR                                FIRST FLOOR
    y=12 +---------+--------+------------------+   +---------+--------+------------------+
         | UTILITY |  HALL  |   KITCHEN /      |   |  BATH   |CORRIDOR|  MASTER BEDROOM  |
    y=8  +---------+ stair  |   DINING         |   |         | stair  |                  |
         |         |  ^     +- - open plan - - +   +---------+  void  +------------------+
         | GARAGE  |  ^     |   LIVING ROOM    |   |  GUEST  |        |  TRADING ROOM    |
         |         |        |                  |   |  (you   |        |  (6 monitors,    |
    y=0  +---------+--MAIN--+------------------+   +---------+--------+------------------+
        x=0       x=5  DOOR x=9               x=18

The main door (south wall of the hall) is blocked by three planks, a gold padlock, a silver padlock and a code
keypad. See README.md for the puzzle chain.
"""
import math

W, D = 18.0, 12.0
T_EXT = 0.24
T_INT = 0.14
H1 = 3.3                    # first floor level
STOREY = 3.3
CEIL = (3.05, 6.3)          # ceiling heights (underside) per floor
ROOF_TOP = 6.55
PARAPET = 7.05
DOOR_H = 2.2
MAIN_DOOR_H = 2.45
ARCH_H = 2.6

# stair: against the hall's west wall, rising north from y0 (z = 0) to y1 (z = H1)
STAIR = {"x0": 5.07, "x1": 6.32, "y0": 5.4, "y1": 10.2, "risers": 18}

ROOMS = [
    # name, floor, rect (wall centre lines), label, floor material, wall material, ceiling material
    ("garage",   0, (0.0, 0.0, 5.0, 8.0),   "Garage",         "floor_concrete", "wall_concrete", "ceiling"),
    ("utility",  0, (0.0, 8.0, 5.0, 12.0),  "Utility Room",   "floor_tiles",    "wall_plaster",  "ceiling"),
    ("hall",     0, (5.0, 0.0, 9.0, 12.0),  "Hall",           "floor_oak",      "wall_plaster",  "ceiling"),
    ("living",   0, (9.0, 0.0, 18.0, 6.5),  "Living Room",    "floor_oak",      "wall_plaster",  "ceiling"),
    ("kitchen",  0, (9.0, 6.5, 18.0, 12.0), "Kitchen",        "floor_stone",    "wall_plaster",  "ceiling"),
    ("guest",    1, (0.0, 0.0, 5.0, 6.5),   "Guest Bedroom",  "floor_oak",      "wall_plaster",  "ceiling"),
    ("bath",     1, (0.0, 6.5, 5.0, 12.0),  "Bathroom",       "floor_tiles",    "wall_tiles",    "ceiling"),
    ("corridor", 1, (5.0, 0.0, 9.0, 12.0),  "Upstairs Hall",  "floor_oak",      "wall_plaster",  "ceiling"),
    ("trading",  1, (9.0, 0.0, 18.0, 6.5),  "Trading Room",   "floor_dark",     "wall_dark",     "ceiling_dark"),
    ("master",   1, (9.0, 6.5, 18.0, 12.0), "Master Bedroom", "floor_oak",      "wall_plaster",  "ceiling"),
]

# walls: floor, axis ('x' = runs along x at y = c, 'y' = runs along y at x = c), c, from, to, thickness, openings
# opening: (u0, u1, z0, z1, kind[, name]) in metres along the wall and above the floor; kinds:
#   door (swing door), main (front door), arch (open), window, shutter (closed garage shutter)
WALLS = [
    # ---------------------------------------------------------------- ground floor, outside walls
    (0, "x", 0.0, 0.0, W, T_EXT, [(0.8, 4.2, 0.0, 2.6, "shutter"), (6.4, 7.6, 0.0, MAIN_DOOR_H, "main", "door_main"),
                                 (10.0, 17.2, 0.25, 2.75, "window")]),
    (0, "y", W, 0.0, D, T_EXT, [(1.0, 5.5, 0.25, 2.75, "window"), (7.5, 11.0, 1.05, 2.4, "window")]),
    (0, "x", D, 0.0, W, T_EXT, [(1.5, 3.5, 1.5, 2.25, "window"), (11.0, 16.0, 1.05, 2.4, "window")]),
    (0, "y", 0.0, 0.0, D, T_EXT, [(2.6, 5.4, 1.85, 2.45, "window")]),
    # ---------------------------------------------------------------- ground floor, inside walls
    (0, "y", 5.0, 0.0, D, T_INT, [(4.25, 5.15, 0.0, DOOR_H, "door", "door_garage"), (10.65, 11.55, 0.0, DOOR_H, "door", "door_utility")]),
    (0, "x", 8.0, 0.0, 5.0, T_INT, []),
    (0, "y", 9.0, 0.0, D, T_INT, [(0.8, 3.6, 0.0, ARCH_H, "arch"), (7.2, 10.2, 0.0, ARCH_H, "arch")]),
    # ---------------------------------------------------------------- first floor, outside walls
    (1, "x", 0.0, 0.0, W, T_EXT, [(1.2, 3.8, 0.9, 2.3, "window"), (5.6, 8.4, 0.3, 2.7, "window"), (10.0, 17.2, 0.6, 2.6, "window")]),
    (1, "y", W, 0.0, D, T_EXT, [(1.0, 5.5, 0.6, 2.6, "window"), (7.5, 11.0, 0.9, 2.4, "window")]),
    (1, "x", D, 0.0, W, T_EXT, [(1.5, 3.5, 1.6, 2.3, "window"), (11.0, 16.0, 0.9, 2.4, "window")]),
    (1, "y", 0.0, 0.0, D, T_EXT, [(1.5, 5.0, 0.9, 2.3, "window")]),
    # ---------------------------------------------------------------- first floor, inside walls
    (1, "y", 5.0, 0.0, D, T_INT, [(4.25, 5.15, 0.0, DOOR_H, "door", "door_guest"), (10.65, 11.55, 0.0, DOOR_H, "door", "door_bath")]),
    (1, "x", 6.5, 0.0, 5.0, T_INT, []),
    (1, "y", 9.0, 0.0, D, T_INT, [(4.8, 5.7, 0.0, DOOR_H, "door", "door_trading"), (7.3, 8.2, 0.0, DOOR_H, "door", "door_master")]),
    (1, "x", 6.5, 9.0, W, T_INT, []),
]

# door leaves: which room they swing into and what locks them
DOORS = {
    "door_main":    {"room": "hall",    "into": (0, 1),  "lock": "main",       "label": "Main Door"},
    "door_garage":  {"room": "garage",  "into": (-1, 0), "lock": "garage_key", "label": "Garage Door"},
    "door_utility": {"room": "utility", "into": (-1, 0), "lock": None,         "label": "Utility Room"},
    "door_guest":   {"room": "guest",   "into": (-1, 0), "lock": None,         "label": "Guest Bedroom"},
    "door_bath":    {"room": "bath",    "into": (-1, 0), "lock": None,         "label": "Bathroom"},
    "door_trading": {"room": "trading", "into": (1, 0),  "lock": None,         "label": "Trading Room"},
    "door_master":  {"room": "master",  "into": (1, 0),  "lock": None,         "label": "Master Bedroom"},
}

# furniture: kind, x, y, z, yaw (deg; the piece's front faces (sin yaw, -cos yaw): 0 = south, 90 = east, 180 = north,
# -90 = west), room. Footprints (w along the piece's own x, d along its y, h) are in props.FOOTPRINT.
FURNITURE = [
    # living room
    ("tv_unit",      9.38, 5.05, 0.0, 90, "living"),
    ("sofa",        13.55, 5.05, 0.0, -90, "living"),
    ("coffee_table", 11.65, 5.05, 0.0, 90, "living"),
    ("rug",         12.6, 5.0, 0.0, 90, "living"),
    ("floor_lamp",  15.4, 6.1, 0.0, 0, "living"),
    ("plant",       17.35, 0.65, 0.0, 0, "living"),
    ("armchair",    16.0, 2.2, 0.0, -60, "living"),
    # kitchen / dining
    ("fridge",       9.62, 11.55, 0.0, 0, "kitchen"),
    ("kitchen_run", 13.95, 11.57, 0.0, 0, "kitchen"),
    ("island",      13.4, 9.75, 0.0, 0, "kitchen"),
    ("stool",       12.6, 8.95, 0.0, 180, "kitchen"),
    ("stool",       13.4, 8.95, 0.0, 180, "kitchen"),
    ("stool",       14.2, 8.95, 0.0, 180, "kitchen"),
    ("dining_set",  16.3, 8.15, 0.0, 0, "kitchen"),
    ("pendant",     12.6, 9.75, 0.0, 0, "kitchen"),
    ("pendant",     13.4, 9.75, 0.0, 0, "kitchen"),
    ("pendant",     14.2, 9.75, 0.0, 0, "kitchen"),
    # hall
    ("console",      5.3, 2.1, 0.0, 90, "hall"),
    ("hall_bench",   8.66, 5.4, 0.0, -90, "hall"),
    # garage
    ("workbench",    0.5, 5.6, 0.0, 90, "garage"),
    ("toolbox",      0.45, 5.15, 0.92, 90, "garage"),
    ("shelf_unit",   2.2, 7.65, 0.0, 0, "garage"),
    ("boxes",        3.9, 7.35, 0.0, 0, "garage"),
    ("fusebox",      4.91, 6.6, 1.25, -90, "garage"),
    # utility
    ("washer",       0.5, 11.5, 0.0, 90, "utility"),
    ("utility_shelf", 2.6, 11.72, 0.0, 0, "utility"),
    ("tall_cabinet", 4.45, 8.75, 0.0, -90, "utility"),
    # guest bedroom (first floor)
    ("bed_guest",    1.2, 3.1, H1, 90, "guest"),
    ("nightstand",   0.35, 4.6, H1, 90, "guest"),
    ("wardrobe",     3.3, 6.12, H1, 0, "guest"),
    ("rug_small",    2.4, 3.1, H1, 90, "guest"),
    # bathroom
    ("vanity",       1.8, 6.82, H1, 180, "bath"),
    ("toilet",       3.7, 6.95, H1, 180, "bath"),
    ("shower",       0.75, 11.25, H1, 0, "bath"),
    # upstairs hall
    ("plant",        8.5, 0.65, H1, 0, "corridor"),
    ("bench",        7.0, 0.55, H1, 180, "corridor"),
    # trading room
    ("trading_desk", 13.5, 5.98, H1, 0, "trading"),
    ("monitors",     13.5, 6.22, H1 + 0.76, 0, "trading"),
    ("gaming_chair", 13.5, 4.95, H1, 180, "trading"),
    ("gaming_pc",   15.2, 6.05, H1, 0, "trading"),
    ("drawers",     11.85, 6.06, H1, 0, "trading"),
    ("wall_shelf",   9.12, 2.3, H1 + 1.42, 90, "trading"),
    ("trophy",       9.27, 2.3, H1 + 1.45, 90, "trading"),
    ("led_cove",    13.5, 3.25, H1, 0, "trading"),
    ("rug_dark",    13.5, 4.3, H1, 0, "trading"),
    ("sofa_trading", 16.9, 3.2, H1, -90, "trading"),
    # master bedroom
    ("bed",         13.5, 10.82, H1, 0, "master"),
    ("nightstand",  12.15, 11.62, H1, 0, "master"),
    ("nightstand",  14.85, 11.62, H1, 0, "master"),
    ("wardrobe",    15.9, 6.88, H1, 180, "master"),
    ("safe",        17.45, 6.93, H1, 180, "master"),
    ("rug",         13.5, 9.3, H1, 0, "master"),
]

# things you can pick up: id -> label, spots (x, y, z, what it lies on); one spot is picked at random per game.
# 'drawer_key' hides in one of the two plant pots, 'gold_key' in the safe, 'silver_key' in the trading desk drawer.
ITEMS = {
    "garage_key": {"label": "Garage Key", "spots": [(12.2, 11.62, 0.93, "kitchen_run"), (13.0, 9.75, 0.93, "island"),
                                                    (9.4, 4.45, 0.55, "tv_unit")]},
    "hammer":     {"label": "Claw Hammer", "spots": [(0.5, 6.15, 0.93, "workbench"), (2.2, 7.62, 1.06, "shelf_unit"),
                                                     (3.0, 5.6, 0.0, "floor")]},
    "fuse":       {"label": "Fuse", "spots": [(2.6, 11.7, 1.24, "utility_shelf"), (0.5, 11.5, 0.86, "washer"),
                                              (1.4, 6.82, H1 + 0.86, "vanity")]},
    "drawer_key": {"label": "Small Key", "spots": []},
    "gold_key":   {"label": "Gold Key", "spots": [(17.45, 6.93, H1 + 0.08, "safe")]},
    "silver_key": {"label": "Silver Key", "spots": [(11.85, 6.0, H1 + 0.5, "drawers")]},
}

# hiding places: in front of / inside these pieces
HIDE_KINDS = ("wardrobe", "tall_cabinet")

# the trader walks between these points (x, y, floor)
PATROL = [
    (7.4, 2.0, 0), (7.6, 9.2, 0), (12.0, 2.6, 0), (15.0, 3.6, 0), (12.0, 8.2, 0), (16.8, 10.6, 0), (2.5, 10.2, 0),
    (2.5, 3.0, 0),
    (7.6, 2.4, 1), (7.6, 11.2, 1), (12.0, 3.0, 1), (15.8, 5.2, 1), (11.5, 8.5, 1), (16.5, 9.8, 1), (2.6, 2.4, 1),
    (2.5, 9.0, 1),
]
TRADER_START = (14.5, 8.0, 0)
SPAWN = {"x": 2.9, "y": 1.7, "floor": 1, "yaw": 0.0}       # the guest bedroom, looking north

# lights for the Blender bake: kind, x, y, z, energy, colour, room
WARM = (1.0, 0.78, 0.55)
NEUTRAL = (1.0, 0.9, 0.78)
COOL = (0.85, 0.92, 1.0)
LIGHTS = [
    # ground floor
    ("down", 7.0, 2.0, 3.0, 26, WARM, "hall"), ("down", 7.6, 7.4, 3.0, 22, WARM, "hall"), ("down", 7.6, 11.0, 3.0, 20, WARM, "hall"),
    ("down", 11.2, 2.0, 3.0, 24, WARM, "living"), ("down", 15.6, 2.0, 3.0, 24, WARM, "living"),
    ("down", 11.2, 5.0, 3.0, 20, WARM, "living"), ("down", 15.6, 5.0, 3.0, 20, WARM, "living"),
    ("lamp", 15.4, 6.1, 1.55, 16, WARM, "living"),
    ("pendant", 12.6, 9.75, 2.15, 14, WARM, "kitchen"), ("pendant", 13.4, 9.75, 2.15, 14, WARM, "kitchen"),
    ("pendant", 14.2, 9.75, 2.15, 14, WARM, "kitchen"),
    ("down", 11.0, 11.0, 3.0, 22, NEUTRAL, "kitchen"), ("down", 16.4, 11.0, 3.0, 20, NEUTRAL, "kitchen"),
    ("down", 16.3, 8.1, 3.0, 18, WARM, "kitchen"),
    ("tube", 2.5, 3.6, 2.98, 30, COOL, "garage"),
    ("down", 2.5, 10.0, 3.0, 18, NEUTRAL, "utility"),
    # first floor
    ("down", 7.2, 2.2, H1 + 2.95, 22, WARM, "corridor"), ("down", 7.6, 8.0, H1 + 2.95, 20, WARM, "corridor"),
    ("down", 6.6, 11.1, H1 + 2.95, 18, WARM, "corridor"),
    ("ceiling", 2.5, 3.2, H1 + 2.92, 9, WARM, "guest"),
    ("down", 2.5, 9.2, H1 + 2.95, 18, COOL, "bath"),
    ("down", 12.0, 8.6, H1 + 2.95, 13, WARM, "master"), ("down", 15.2, 8.6, H1 + 2.95, 13, WARM, "master"),
    ("lamp", 12.15, 11.62, H1 + 0.72, 8, WARM, "master"), ("lamp", 14.85, 11.62, H1 + 0.72, 8, WARM, "master"),
]
# the trading room has no power until the fuse goes in: these only light the "on" bake
TRADING_LIGHTS = [
    ("down", 11.5, 2.0, H1 + 2.95, 18, NEUTRAL, "trading"), ("down", 15.5, 2.0, H1 + 2.95, 18, NEUTRAL, "trading"),
    ("down", 13.5, 4.6, H1 + 2.95, 16, NEUTRAL, "trading"),
    ("strip", 13.5, 3.25, H1 + 2.86, 40, (0.55, 0.35, 1.0), "trading"),
    ("screen", 13.5, 6.05, H1 + 1.35, 26, (0.55, 0.75, 1.0), "trading"),
]
OUTSIDE_LIGHTS = [
    ("garden", 6.0, -0.6, 2.6, 30, WARM, "outside"), ("garden", 8.0, -0.6, 2.6, 30, WARM, "outside"),
    ("street", 9.0, -9.5, 5.5, 220, (1.0, 0.72, 0.45), "outside"),
]

# the plot around the house (compound wall), the drive and the lawn
PLOT = (-6.0, -11.0, 24.0, 18.0)
DRIVE = (0.4, -11.0, 4.6, 0.0)
PATH = (6.3, -11.0, 7.7, 0.0)


def room(name):
    for r in ROOMS:
        if r[0] == name:
            return r
    raise KeyError(name)


def room_at(floor, x, y):
    """Name of the room containing (x, y) on a floor, or None outside the house."""
    for r in ROOMS:
        if r[1] != floor:
            continue
        x0, y0, x1, y1 = r[2]
        if x0 <= x <= x1 and y0 <= y <= y1:
            # rooms share their boundary lines: prefer the one whose inside the point is clearly in
            return r[0]
    return None


def floor_z(floor):
    return 0.0 if floor == 0 else H1


def in_stair_void(x, y):
    s = STAIR
    return s["x0"] <= x <= s["x1"] and s["y0"] <= y <= s["y1"]


def stair_z(y):
    """Height of the stair's walking surface (the ramp through the step noses) at y."""
    s = STAIR
    t = (y - s["y0"]) / (s["y1"] - s["y0"])
    return max(0.0, min(1.0, t)) * H1


def build():
    """Everything as one dict (the shape the build scripts and the previews use)."""
    rooms = [{"name": n, "floor": f, "rect": list(rc), "label": lab, "floor_mat": fm, "wall_mat": wm, "ceil_mat": cm}
             for (n, f, rc, lab, fm, wm, cm) in ROOMS]
    walls = []
    doors = []
    windows = []
    for (fl, ax, c, a, b, t, ops) in WALLS:
        w = {"floor": fl, "axis": ax, "c": c, "a": a, "b": b, "t": t, "openings": []}
        for op in ops:
            u0, u1, z0, z1, kind = op[:5]
            name = op[5] if len(op) > 5 else None
            o = {"u0": u0, "u1": u1, "z0": z0, "z1": z1, "kind": kind, "name": name}
            w["openings"].append(o)
            um = (u0 + u1) / 2
            x, y = (um, c) if ax == "x" else (c, um)
            if kind in ("door", "main"):
                info = DOORS[name]
                doors.append({"name": name, "floor": fl, "x": x, "y": y, "w": u1 - u0, "h": z1 - z0, "axis": ax,
                              "t": t, "kind": kind, "room": info["room"], "into": info["into"], "lock": info["lock"],
                              "label": info["label"]})
            elif kind == "window":
                windows.append({"floor": fl, "axis": ax, "c": c, "u0": u0, "u1": u1, "z0": z0, "z1": z1, "t": t})
        walls.append(w)
    furniture = [{"kind": k, "x": x, "y": y, "z": z, "yaw": yaw, "room": rm} for (k, x, y, z, yaw, rm) in FURNITURE]
    items = {k: {"label": v["label"], "spots": [{"x": s[0], "y": s[1], "z": s[2], "on": s[3]} for s in v["spots"]]}
             for k, v in ITEMS.items()}
    lights = [{"kind": k, "x": x, "y": y, "z": z, "energy": e, "color": list(c), "room": r} for (k, x, y, z, e, c, r) in LIGHTS]
    tlights = [{"kind": k, "x": x, "y": y, "z": z, "energy": e, "color": list(c), "room": r} for (k, x, y, z, e, c, r) in TRADING_LIGHTS]
    olights = [{"kind": k, "x": x, "y": y, "z": z, "energy": e, "color": list(c), "room": r} for (k, x, y, z, e, c, r) in OUTSIDE_LIGHTS]
    return {
        "W": W, "D": D, "H1": H1, "ceil": list(CEIL), "roof_top": ROOF_TOP, "parapet": PARAPET,
        "rooms": rooms, "walls": walls, "doors": doors, "windows": windows, "stair": dict(STAIR),
        "furniture": furniture, "items": items, "lights": lights, "trading_lights": tlights, "outside_lights": olights,
        "patrol": [list(p) for p in PATROL], "trader_start": list(TRADER_START), "spawn": dict(SPAWN),
        "plot": list(PLOT), "drive": list(DRIVE), "path": list(PATH), "hide_kinds": list(HIDE_KINDS),
    }


if __name__ == "__main__":
    L = build()
    print("rooms %d, walls %d, doors %d, windows %d, furniture %d, lights %d" %
          (len(L["rooms"]), len(L["walls"]), len(L["doors"]), len(L["windows"]), len(L["furniture"]),
           len(L["lights"]) + len(L["trading_lights"]) + len(L["outside_lights"])))
    # sanity: every furniture piece in its room, every patrol point inside the house
    for f in L["furniture"]:
        fl = 0 if f["z"] < H1 - 0.5 else 1
        rn = room_at(fl, f["x"], f["y"])
        if rn != f["room"] and not (f["room"] in ("living", "kitchen") and rn in ("living", "kitchen")):
            print("  check:", f["kind"], "at", f["x"], f["y"], "is in", rn, "not", f["room"])
    print("stair run %.2f m for %.2f m: %.1f deg" % (STAIR["y1"] - STAIR["y0"], H1,
                                                      math.degrees(math.atan2(H1, STAIR["y1"] - STAIR["y0"]))))
