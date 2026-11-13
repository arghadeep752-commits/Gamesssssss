"""ADARSH VIDYALAYA - the old government school Ragini haunts. Plain-Python layout (no Blender needed).

One storey around an open courtyard, entered from the front yard through the main door:

    back wing  :  Prayer Hall (stage)                      | Mid-day Meal Kitchen
    left wing  :  Class 7 / Library      courtyard          right wing : Class 8 / Store Room / Toilets
    front wing :  Class 5 | Principal | Entrance | Staff Room | Class 6
                                  [ MAIN DOOR ]
                                  front yard, compound wall and gate

Blender axes: x east, y north (the main door faces south, -y), z up. Metres. 9-inch brick walls.
Everything the Blender build and the game need comes from here: walls with their door and window openings,
rooms and their finishes, doors (locks and keys), lights, furniture, item spots, Ragini's patrol points and a
walkability grid for her path finding.
"""
import json
import math
import sys

WALL_T = 0.23
CEIL_H = 3.4
DOOR_H = 2.2
SILL = 0.9
WIN_H = 1.45

# x0, y0, x1, y1
BUILDING = (-14.0, -6.0, 14.0, 22.0)
COURT = (-6.5, 3.5, 6.5, 12.5)            # open to the sky
VERANDA = (-9.0, 1.0, 9.0, 15.0)          # covered walkway around the courtyard (outer edge)
YARD = (-16.0, -17.0, 16.0, -6.0)

ROOMS = [
    # name, label, rect, floor, wall paint (lower dado), ceiling light count
    ("class5", "CLASS V", (-14.0, -6.0, -7.0, 1.0), "floor_cement", "dado_green"),
    ("principal", "PRINCIPAL", (-7.0, -6.0, -2.5, 1.0), "floor_terrazzo", "dado_blue"),
    ("entrance", "ENTRANCE", (-2.5, -6.0, 2.5, 1.0), "floor_terrazzo", "dado_red"),
    ("staff", "STAFF ROOM", (2.5, -6.0, 7.0, 1.0), "floor_terrazzo", "dado_blue"),
    ("class6", "CLASS VI", (7.0, -6.0, 14.0, 1.0), "floor_cement", "dado_green"),
    ("class7", "CLASS VII", (-14.0, 1.0, -9.0, 8.0), "floor_cement", "dado_green"),
    ("library", "LIBRARY", (-14.0, 8.0, -9.0, 15.0), "floor_terrazzo", "dado_brown"),
    ("class8", "CLASS VIII", (9.0, 1.0, 14.0, 8.0), "floor_cement", "dado_green"),
    ("store", "STORE ROOM", (9.0, 8.0, 14.0, 11.5), "floor_cement", "dado_brown"),
    ("toilet", "TOILET", (9.0, 11.5, 14.0, 15.0), "floor_tiles", "dado_tiles"),
    ("hall", "PRAYER HALL", (-14.0, 15.0, 5.0, 22.0), "floor_kota", "dado_red"),
    ("kitchen", "MID-DAY MEAL", (5.0, 15.0, 14.0, 22.0), "floor_kota", "dado_brown"),
]

# doors: name, room, wall side of that room (n/s/e/w), centre along the wall, width, kind, lock
#   lock: None, "office_key", "store_key", "main" (planks + main door key)
DOORS = [
    ("door_main", "entrance", "s", 0.0, 1.9, "main", "main"),
    ("door_entrance_in", "entrance", "n", 0.0, 2.2, "arch", None),
    ("door_principal", "principal", "e", -2.2, 1.0, "door", "office_key"),
    ("door_staff", "staff", "w", -2.2, 1.0, "door", None),
    ("door_class5", "class5", "n", -8.0, 1.1, "door", None),
    ("door_class6", "class6", "n", 8.0, 1.1, "door", None),
    ("door_class7", "class7", "e", 4.5, 1.1, "door", None),
    ("door_library", "library", "e", 11.5, 1.1, "door", None),
    ("door_class8", "class8", "w", 4.5, 1.1, "door", None),
    ("door_store", "store", "w", 9.75, 1.0, "door", "store_key"),
    ("door_toilet", "toilet", "w", 13.25, 1.0, "door", None),
    ("door_hall", "hall", "s", -2.0, 2.0, "door2", None),
    ("door_hall2", "hall", "s", -11.0, 1.1, "door", None),
    ("door_kitchen", "kitchen", "s", 9.5, 1.1, "door", None),
]

# windows: room, side, centre along wall, width (outer walls look onto the yard/outside, inner ones onto the veranda)
WINDOWS = [
    ("class5", "s", -12.0, 1.4), ("class5", "s", -9.0, 1.4), ("class5", "w", -2.5, 1.4),
    ("principal", "s", -4.75, 1.2),
    ("staff", "s", 4.75, 1.2),
    ("class6", "s", 9.0, 1.4), ("class6", "s", 12.0, 1.4), ("class6", "e", -2.5, 1.4),
    ("class7", "w", 3.0, 1.4), ("class7", "w", 6.0, 1.4), ("class7", "e", 2.5, 1.2),
    ("library", "w", 10.0, 1.4), ("library", "w", 13.0, 1.4),
    ("class8", "e", 3.0, 1.4), ("class8", "e", 6.0, 1.4), ("class8", "w", 2.5, 1.2),
    ("store", "e", 9.75, 1.0),
    ("toilet", "e", 13.25, 0.9),
    ("hall", "n", -10.0, 1.4), ("hall", "n", -5.0, 1.4), ("hall", "n", 0.0, 1.4), ("hall", "s", -6.5, 1.4), ("hall", "s", 2.0, 1.4),
    ("kitchen", "n", 9.5, 1.2), ("kitchen", "e", 18.5, 1.2),
]

ITEMS = {
    # id: (label, candidate spots: (room, x, y, z_hint) - one is picked each game)
    "office_key": ("OFFICE KEY", [("staff", 5.6, -4.6, "table"), ("class7", -10.6, 2.0, "desk"), ("library", -12.6, 12.4, "table"),
                                  ("class6", 12.6, -0.4, "desk")]),
    "store_key": ("STORE ROOM KEY", [("class5", -12.4, -0.2, "desk"), ("hall", 0.0, 20.4, "stage"), ("kitchen", 12.0, 19.0, "table"),
                                     ("class8", 12.2, 6.6, "desk")]),
    "hammer": ("HAMMER", [("store", 12.6, 9.4, "floor"), ("store", 10.4, 10.6, "crate")]),
    "main_key": ("MAIN DOOR KEY", [("principal", -4.8, -4.4, "desk"), ("principal", -6.2, -0.6, "almirah")]),
}

ROOM_KIND = {"class5": "classroom", "class6": "classroom", "class7": "classroom", "class8": "classroom",
             "principal": "principal", "staff": "staff", "entrance": "entrance", "library": "library", "store": "store",
             "toilet": "toilet", "hall": "hall", "kitchen": "kitchen"}


def room(name):
    for r in ROOMS:
        if r[0] == name:
            return r
    raise KeyError(name)


def wall_line(rname, side):
    """(orientation, fixed coordinate, a, b) of one side of a room. 'h' walls run along x."""
    x0, y0, x1, y1 = room(rname)[2]
    return {"s": ("h", y0, x0, x1), "n": ("h", y1, x0, x1), "w": ("v", x0, y0, y1), "e": ("v", x1, y0, y1)}[side]


def _segments():
    """Every wall as an axis-aligned segment, merged where rooms share a wall."""
    segs = set()
    for r in ROOMS:
        for side in "snwe":
            o, p, a, b = wall_line(r[0], side)
            segs.add((o, round(p, 3), round(a, 3), round(b, 3)))
    # split overlapping collinear segments into unique pieces
    by_line = {}
    for o, p, a, b in segs:
        by_line.setdefault((o, p), []).append((a, b))
    out = []
    for (o, p), spans in by_line.items():
        cuts = sorted(set([x for s in spans for x in s]))
        for i in range(len(cuts) - 1):
            a, b = cuts[i], cuts[i + 1]
            mid = (a + b) / 2
            if any(s[0] <= mid <= s[1] for s in spans):
                out.append((o, p, a, b))
    # merge touching pieces back into long runs
    out.sort()
    merged = []
    for o, p, a, b in out:
        if merged and merged[-1][0] == o and merged[-1][1] == p and abs(merged[-1][3] - a) < 1e-6:
            merged[-1] = (o, p, merged[-1][2], b)
        else:
            merged.append((o, p, a, b))
    return merged


def _outer(o, p):
    x0, y0, x1, y1 = BUILDING
    return (o == "h" and p in (y0, y1)) or (o == "v" and p in (x0, x1))


def build():
    walls = []
    for o, p, a, b in _segments():
        walls.append({"o": o, "p": p, "a": a, "b": b, "outer": _outer(o, p), "openings": []})

    def wall_at(o, p, c):
        for w in walls:
            if w["o"] == o and abs(w["p"] - p) < 1e-6 and w["a"] - 1e-6 <= c <= w["b"] + 1e-6:
                return w
        raise KeyError((o, p, c))

    doors = []
    for name, rname, side, c, width, kind, lock in DOORS:
        o, p, a, b = wall_line(rname, side)
        w = wall_at(o, p, c)
        h = 2.6 if kind in ("main", "arch") else DOOR_H
        w["openings"].append({"c": c, "w": width, "z0": 0.0, "z1": h, "kind": kind, "name": name})
        x, y = (c, p) if o == "h" else (p, c)
        # which way the door swings: into the room it belongs to
        r = room(rname)[2]
        cx, cy = (r[0] + r[2]) / 2, (r[1] + r[3]) / 2
        into = (0, 1 if cy > y else -1) if o == "h" else (1 if cx > x else -1, 0)
        doors.append({"name": name, "room": rname, "o": o, "x": x, "y": y, "w": width, "h": h, "kind": kind,
                      "lock": lock, "into": into})
    windows = []
    for rname, side, c, width in WINDOWS:
        o, p, a, b = wall_line(rname, side)
        w = wall_at(o, p, c)
        w["openings"].append({"c": c, "w": width, "z0": SILL, "z1": SILL + WIN_H, "kind": "window", "name": "win_%s_%s_%g" % (rname, side, c)})
        x, y = (c, p) if o == "h" else (p, c)
        windows.append({"room": rname, "o": o, "x": x, "y": y, "w": width, "outer": w["outer"]})
    # the veranda's courtyard edge is open, carried on pillars
    pillars = []
    cx0, cy0, cx1, cy1 = COURT
    for x in [cx0 + i * (cx1 - cx0) / 4 for i in range(5)]:
        pillars += [(x, cy0), (x, cy1)]
    for y in [cy0 + i * (cy1 - cy0) / 3 for i in range(1, 3)]:
        pillars += [(cx0, y), (cx1, y)]
    # lights: (x, y, z, kind, room) kind = tube | bulb | dead (a broken tube that stays dark)
    lights = []
    for r in ROOMS:
        name = r[0]
        x0, y0, x1, y1 = r[2]
        kind = ROOM_KIND[name]
        area = (x1 - x0) * (y1 - y0)
        n = 2 if area > 30 else 1
        for i in range(n):
            if n == 2:
                lx, ly = ((x0 + x1) / 2, y0 + (y1 - y0) * (0.3 + 0.4 * i)) if (y1 - y0) > (x1 - x0) else (x0 + (x1 - x0) * (0.3 + 0.4 * i), (y0 + y1) / 2)
            else:
                lx, ly = (x0 + x1) / 2, (y0 + y1) / 2
            state = "tube"
            if name in ("class7", "store", "kitchen") and i == 0:
                state = "dead"
            if name in ("toilet",):
                state = "bulb"
            lights.append({"x": lx, "y": ly, "z": CEIL_H - 0.12, "kind": state, "room": name})
    for (lx, ly) in [(0, 2.2), (-7.8, 2.2), (7.8, 2.2), (-7.8, 8.0), (7.8, 8.0), (-7.8, 13.8), (7.8, 13.8), (0, 13.8)]:
        lights.append({"x": lx, "y": ly, "z": CEIL_H - 0.15, "kind": "bulb", "room": "veranda"})
    lights.append({"x": 0.0, "y": -6.6, "z": 3.1, "kind": "bulb", "room": "yard"})          # over the main door outside
    # furniture: kind, room, x, y, yaw (degrees, 0 = facing -y / south)
    furn = []

    def classroom(name, front):
        """Rows of dual desks facing the blackboard on the `front` wall, teacher's dais and table."""
        x0, y0, x1, y1 = room(name)[2]
        if front in ("w", "e"):
            # blackboard on a side wall: rows run along x
            fx = x0 if front == "w" else x1
            s = 1 if front == "w" else -1
            yaw = -90 if front == "w" else 90           # students face the board
            furn.append({"kind": "blackboard", "room": name, "x": fx + s * 0.13, "y": (y0 + y1) / 2, "yaw": yaw + 180})
            furn.append({"kind": "dais", "room": name, "x": fx + s * 1.0, "y": (y0 + y1) / 2, "yaw": yaw + 180})
            furn.append({"kind": "teacher_table", "room": name, "x": fx + s * 1.2, "y": (y0 + y1) / 2 + 0.9, "yaw": yaw + 180})
            furn.append({"kind": "teacher_chair", "room": name, "x": fx + s * 0.75, "y": (y0 + y1) / 2 + 0.9, "yaw": yaw})
            for col in range(2):
                for row in range(3):
                    furn.append({"kind": "desk_bench", "room": name, "x": fx + s * (2.6 + row * 1.15),
                                 "y": (y0 + y1) / 2 + (col - 0.5) * 2.5, "yaw": yaw})
            furn.append({"kind": "almirah", "room": name, "x": x1 - 0.4 if front == "w" else x0 + 0.4, "y": y1 - 0.45 if name != "class8" else y0 + 0.45, "yaw": 90 if front == "w" else -90})
        else:
            fy = y0 if front == "s" else y1
            s = 1 if front == "s" else -1
            yaw = 180 if front == "s" else 0
            furn.append({"kind": "blackboard", "room": name, "x": (x0 + x1) / 2, "y": fy + s * 0.13, "yaw": yaw + 180})
            furn.append({"kind": "dais", "room": name, "x": (x0 + x1) / 2, "y": fy + s * 1.0, "yaw": yaw + 180})
            furn.append({"kind": "teacher_table", "room": name, "x": (x0 + x1) / 2 + 1.0, "y": fy + s * 1.2, "yaw": yaw + 180})
            furn.append({"kind": "teacher_chair", "room": name, "x": (x0 + x1) / 2 + 1.0, "y": fy + s * 0.75, "yaw": yaw})
            for col in range(3):
                for row in range(3):
                    furn.append({"kind": "desk_bench", "room": name, "x": (x0 + x1) / 2 + (col - 1) * 1.95,
                                 "y": fy + s * (2.7 + row * 1.15), "yaw": yaw})
            furn.append({"kind": "almirah", "room": name, "x": x0 + 0.45, "y": fy + s * 0.5, "yaw": 90})
        furn.append({"kind": "fan", "room": name, "x": (x0 + x1) / 2, "y": (y0 + y1) / 2, "yaw": 0})
    classroom("class5", "w")
    classroom("class6", "e")
    classroom("class7", "s")
    classroom("class8", "n")
    # principal's office
    furn += [{"kind": "principal_desk", "room": "principal", "x": -4.8, "y": -4.0, "yaw": 0},
             {"kind": "office_chair", "room": "principal", "x": -4.8, "y": -4.9, "yaw": 0},
             {"kind": "visitor_chair", "room": "principal", "x": -5.4, "y": -2.9, "yaw": 180},
             {"kind": "visitor_chair", "room": "principal", "x": -4.2, "y": -2.9, "yaw": 180},
             {"kind": "almirah", "room": "principal", "x": -6.5, "y": -0.6, "yaw": 90},
             {"kind": "file_rack", "room": "principal", "x": -6.55, "y": -3.2, "yaw": 90},
             {"kind": "wall_clock", "room": "principal", "x": -4.8, "y": -5.86, "yaw": 0},
             {"kind": "fan", "room": "principal", "x": -4.75, "y": -2.5, "yaw": 0}]
    # staff room
    furn += [{"kind": "long_table", "room": "staff", "x": 4.75, "y": -2.8, "yaw": 90}]
    for i in range(3):
        furn += [{"kind": "visitor_chair", "room": "staff", "x": 4.05, "y": -4.0 + i * 1.2, "yaw": -90},
                 {"kind": "visitor_chair", "room": "staff", "x": 5.45, "y": -4.0 + i * 1.2, "yaw": 90}]
    furn += [{"kind": "lockers", "room": "staff", "x": 6.62, "y": -1.6, "yaw": -90},
             {"kind": "matka_stand", "room": "staff", "x": 6.5, "y": 0.45, "yaw": 0},
             {"kind": "fan", "room": "staff", "x": 4.75, "y": -2.5, "yaw": 0}]
    # entrance hall
    furn += [{"kind": "bench", "room": "entrance", "x": -1.85, "y": -3.0, "yaw": 90},
             {"kind": "notice_board", "room": "entrance", "x": 2.37, "y": -3.0, "yaw": -90},
             {"kind": "school_bell", "room": "entrance", "x": 1.6, "y": 0.6, "yaw": 180},
             {"kind": "trophy_case", "room": "entrance", "x": -1.9, "y": -0.2, "yaw": 90}]
    # library
    for i in range(3):
        furn.append({"kind": "bookshelf", "room": "library", "x": -13.6, "y": 9.3 + i * 2.0, "yaw": 90})
    furn += [{"kind": "reading_table", "room": "library", "x": -11.3, "y": 11.5, "yaw": 0},
             {"kind": "bench", "room": "library", "x": -11.3, "y": 10.7, "yaw": 0},
             {"kind": "bench", "room": "library", "x": -11.3, "y": 12.3, "yaw": 180},
             {"kind": "fan", "room": "library", "x": -11.5, "y": 11.5, "yaw": 0}]
    # store room
    furn += [{"kind": "broken_desks", "room": "store", "x": 12.9, "y": 10.6, "yaw": -90},
             {"kind": "sacks", "room": "store", "x": 13.2, "y": 8.7, "yaw": 0},
             {"kind": "crate", "room": "store", "x": 10.4, "y": 10.9, "yaw": 0},
             {"kind": "buckets", "room": "store", "x": 11.6, "y": 11.0, "yaw": 0}]
    # toilet
    furn += [{"kind": "sinks", "room": "toilet", "x": 11.3, "y": 14.6, "yaw": 0},
             {"kind": "stalls", "room": "toilet", "x": 13.0, "y": 12.6, "yaw": -90}]
    # prayer hall
    furn += [{"kind": "stage", "room": "hall", "x": -4.5, "y": 20.6, "yaw": 0},
             {"kind": "harmonium", "room": "hall", "x": -4.5, "y": 20.9, "yaw": 0},
             {"kind": "fan", "room": "hall", "x": -9.0, "y": 18.5, "yaw": 0},
             {"kind": "fan", "room": "hall", "x": 0.0, "y": 18.5, "yaw": 0}]
    for i in range(4):
        furn.append({"kind": "mats", "room": "hall", "x": -8.0 + i * 2.6, "y": 17.6, "yaw": 0})
    # kitchen
    furn += [{"kind": "chulha", "room": "kitchen", "x": 12.6, "y": 21.2, "yaw": 0},
             {"kind": "vessels", "room": "kitchen", "x": 10.6, "y": 21.3, "yaw": 0},
             {"kind": "kitchen_table", "room": "kitchen", "x": 12.0, "y": 18.8, "yaw": -90},
             {"kind": "gas_cylinder", "room": "kitchen", "x": 13.5, "y": 20.0, "yaw": 0},
             {"kind": "sacks", "room": "kitchen", "x": 6.0, "y": 21.3, "yaw": 0}]
    # courtyard and yard
    furn += [{"kind": "neem_tree", "room": "court", "x": -3.0, "y": 9.5, "yaw": 0},
             {"kind": "flag_platform", "room": "court", "x": 2.5, "y": 6.5, "yaw": 0},
             {"kind": "hand_pump", "room": "court", "x": 4.6, "y": 11.2, "yaw": 200},
             {"kind": "water_tank", "room": "veranda", "x": 8.4, "y": 13.0, "yaw": -90},
             {"kind": "gate", "room": "yard", "x": 0.0, "y": -17.0, "yaw": 0},
             {"kind": "sign", "room": "yard", "x": 0.0, "y": -6.12, "yaw": 0}]
    # hiding places: under the teacher tables and in the almirahs
    hides = [{"kind": "under", "furn": i} for i, f in enumerate(furn) if f["kind"] in ("teacher_table", "principal_desk")]
    hides += [{"kind": "inside", "furn": i} for i, f in enumerate(furn) if f["kind"] == "almirah"]
    # Ragini's patrol points (room centres, veranda corners, the courtyard)
    patrol = []
    for r in ROOMS:
        x0, y0, x1, y1 = r[2]
        patrol.append(((x0 + x1) / 2, (y0 + y1) / 2))
    patrol += [(-7.8, 2.2), (7.8, 2.2), (-7.8, 13.8), (7.8, 13.8), (0.0, 2.2), (0.0, 13.8), (0.0, 8.0)]
    L = {
        "wall_t": WALL_T, "ceil_h": CEIL_H, "building": BUILDING, "court": COURT, "veranda": VERANDA, "yard": YARD,
        "rooms": [{"name": r[0], "label": r[1], "rect": r[2], "floor": r[3], "dado": r[4], "kind": ROOM_KIND[r[0]]} for r in ROOMS],
        "walls": walls, "doors": doors, "windows": windows, "pillars": pillars, "lights": lights, "furniture": furn,
        "items": {k: {"label": v[0], "spots": [{"room": s[0], "x": s[1], "y": s[2], "on": s[3]} for s in v[1]]} for k, v in ITEMS.items()},
        "hides": hides, "patrol": patrol,
        "spawn": {"x": -10.5, "y": -2.6, "yaw": 90.0, "room": "class5"},       # wakes at a desk in Class V
        "ragini_start": {"x": 0.0, "y": 8.0},
        "outside": {"door": [0.0, -6.0], "gate": [0.0, -17.0], "start": [-2.5, -15.5]},
    }
    return L


if __name__ == "__main__":
    L = build()
    out = sys.argv[1] if len(sys.argv) > 1 else "layout.json"
    json.dump(L, open(out, "w"), indent=1)
    print("walls %d, doors %d, windows %d, furniture %d, lights %d" % (len(L["walls"]), len(L["doors"]), len(L["windows"]),
                                                                       len(L["furniture"]), len(L["lights"])))
