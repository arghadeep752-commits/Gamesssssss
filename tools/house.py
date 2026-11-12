#!/usr/bin/env python3
"""Chaya - the house: a two-storey village house of rural India built round an open courtyard (aangan).

    python3 tools/house.py <out layout.json>

Ground floor: the entrance hall (deorhi) behind the front door, a pillared veranda (baranda) round the aangan with the
tulsi chaura in the middle, the pooja ghar with Hanuman ji's murti (the ritual is done on the veranda in front of it),
the kitchen, the store rooms, dadi's room, the sitting room (baithak), the stairs and the back passage with the exit
door. First floor: a gallery round the open courtyard with a wooden railing, and the bedrooms - one of them Chaya's.

The plan is drawn by hand below (one letter per 2.6 m cell). Everything else - walls, openings, the stairs, the walking
graph for Chaya, lamps, item spots, windows - is worked out from it. tools/housegeo.py turns it into geometry.
"""
import json
import math
import random
import sys

CELL = 2.6
WALL_T = 0.22
WALL_H = 3.0          # floor to ceiling
SLAB = 0.3
FLOOR_H = WALL_H + SLAB
DOOR_W, DOOR_H = 1.25, 2.15

GF = [
    "KKKPXSBB",
    "KKVVVVTB",
    "QQVAAVRB",
    "DDVAAVRB",
    "DDVVVVUU",
    "HHHEEWWW",
    "HHHEEWWW",
]
FF = [
    "CCMMMMNN",
    "CCGGGGNN",
    "OOG--G-N",
    "OOG--G-N",
    "OOGGGGLY",
    "FFFIIJJJ",
    "FFFIIJJJ",
]
ROOMS = {   # letter: (name, kind)
    0: {"K": ("rasoi", "kitchen"), "P": ("pooja_ghar", "pooja"), "X": ("back_passage", "passage"), "S": ("bhandar_2", "store"),
        "B": ("guest_room", "bedroom"), "V": ("baranda", "veranda"), "A": ("aangan", "courtyard"), "T": ("stair_foot", "passage"),
        "R": ("stairs", "stairs"), "Q": ("bhandar", "store"), "D": ("dadi_room", "bedroom"), "U": ("store_room", "store"),
        "H": ("baithak", "hall"), "E": ("deorhi", "entrance"), "W": ("anaj_ghar", "store")},
    1: {"C": ("chaya_room", "bedroom"), "M": ("kothri", "store"), "N": ("bada_kamra", "bedroom"), "G": ("gallery", "gallery"),
        "-": ("void", "void"), "L": ("landing", "passage"), "Y": ("chhota_kamra", "study"), "O": ("bedroom_2", "bedroom"),
        "F": ("upper_hall", "hall"), "I": ("front_room", "study"), "J": ("east_room", "bedroom")},
}
# openings between cells on the same floor: (floor, (i, j), (i, j), kind)   kind: door | arch | pooja | open
OPENINGS = [
    (0, (1, 1), (2, 1), "door"), (0, (3, 0), (3, 1), "pooja"), (0, (4, 0), (4, 1), "arch"), (0, (5, 0), (5, 1), "door"),
    (0, (6, 1), (5, 1), "arch"), (0, (6, 1), (7, 1), "door"), (0, (6, 1), (6, 2), "open"), (0, (1, 2), (2, 2), "door"),
    (0, (1, 3), (2, 3), "door"), (0, (6, 4), (5, 4), "door"), (0, (2, 5), (3, 5), "door"), (0, (4, 5), (5, 5), "door"),
    (1, (1, 1), (2, 1), "door"), (1, (3, 0), (3, 1), "door"), (1, (6, 1), (5, 1), "door"), (1, (1, 3), (2, 3), "door"),
    (1, (6, 4), (5, 4), "arch"), (1, (6, 3), (6, 4), "open"), (1, (7, 4), (6, 4), "door"), (1, (2, 5), (2, 4), "door"),
    (1, (3, 5), (3, 4), "door"), (1, (6, 5), (6, 4), "door"),
]
# the wide arch from the entrance hall into the veranda, centred between two cells (x = 0)
WIDE = [(0, "h", 5, (3, 5), 1.9, 2.45, "arch")]      # floor, orientation, line index, (first cell i, j), width, height, kind
STAIRS = {"floor": 0, "foot": (6, 1), "cells": [(6, 2), (6, 3)], "top": (6, 4), "dir": (0, 1)}
OPEN_KINDS = {("veranda", "courtyard")}               # no wall between these: the courtyard edge has pillars
RAILING_KINDS = {("gallery", "void")}                  # wooden railing on the first floor round the open courtyard
ITEM_ROOMS = ["rasoi", "dadi_room", "baithak", "chaya_room", "bedroom_2", "front_room"]
ITEMS = ["kalash", "diya", "coconut", "kumkum", "kapoor", "gangajal"]
# windows on the outer walls: (floor, (i, j), side) - side (di, dj) points out of the house
WINDOWS = [
    (0, (1, 6), (0, 1)), (0, (6, 6), (0, 1)), (0, (0, 3), (-1, 0)), (0, (7, 2), (1, 0)), (0, (0, 0), (0, -1)),
    (1, (1, 6), (0, 1)), (1, (3, 6), (0, 1)), (1, (4, 6), (0, 1)), (1, (6, 6), (0, 1)), (1, (0, 0), (-1, 0)),
    (1, (0, 3), (-1, 0)), (1, (7, 0), (1, 0)), (1, (7, 3), (1, 0)), (1, (3, 0), (0, -1)), (1, (6, 0), (0, -1)),
]


def generate(seed=7):
    rnd = random.Random(seed)
    C, R = len(GF[0]), len(GF)
    x0, z0 = -C * CELL / 2.0, -R * CELL / 2.0
    plans = [GF, FF]

    def cx(i):
        return x0 + (i + 0.5) * CELL

    def cz(j):
        return z0 + (j + 0.5) * CELL

    # rooms
    rooms = []
    rid = {}
    for f, plan in enumerate(plans):
        letters = {}
        for j, row in enumerate(plan):
            for i, ch in enumerate(row):
                letters.setdefault(ch, []).append([i, j])
        for ch, cells in letters.items():
            name, kind = ROOMS[f][ch]
            rid[(f, ch)] = len(rooms)
            rooms.append(dict(id=len(rooms), name=name, kind=kind, floor=f, letter=ch, cells=cells))
    region = [[[rid[(f, plans[f][j][i])] for i in range(C)] for j in range(R)] for f in range(2)]

    def room_at(f, i, j):
        if 0 <= i < C and 0 <= j < R:
            return rooms[region[f][j][i]]
        return None

    stair_cells = set(tuple(c) for c in STAIRS["cells"])
    # edges (between neighbours on one floor, and the outer boundary)
    open_map = {}
    for f, a, b, kind in OPENINGS:
        open_map[(f, tuple(sorted([tuple(a), tuple(b)])))] = kind
    wide_cells = {}
    for (f, o, line, c0, w, h, kind) in WIDE:
        i, j = c0
        if o == "h":
            for ii in (i, i + 1):
                wide_cells[(f, tuple(sorted([(ii, j - 1), (ii, j)])))] = "wide"
    edges = []      # dict(f, o, a:(i,j), b:(i,j) or None, kind)
    for f in range(2):
        for j in range(R):
            for i in range(C):
                for di, dj, o in ((1, 0, "v"), (0, 1, "h")):
                    a, b = (i, j), (i + di, j + dj)
                    ra, rb = room_at(f, *a), room_at(f, *b)
                    if rb is None:
                        continue
                    key = (f, tuple(sorted([a, b])))
                    if key in wide_cells:
                        kind = "wide"
                    elif key in open_map:
                        kind = open_map[key]
                    elif ra["id"] == rb["id"]:
                        kind = "same"
                    elif tuple(sorted([ra["kind"], rb["kind"]])) in {tuple(sorted(k)) for k in OPEN_KINDS}:
                        kind = "open"
                    elif tuple(sorted([ra["kind"], rb["kind"]])) in {tuple(sorted(k)) for k in RAILING_KINDS}:
                        kind = "railing"
                    elif ra["kind"] == "void" and rb["kind"] == "void":
                        kind = "same"
                    else:
                        kind = "wall"
                    edges.append(dict(f=f, o=o, a=list(a), b=list(b), kind=kind))
        # outer boundary
        for i in range(C):
            edges.append(dict(f=f, o="h", a=[i, 0], b=None, side=[0, -1], kind="outer"))
            edges.append(dict(f=f, o="h", a=[i, R - 1], b=None, side=[0, 1], kind="outer"))
        for j in range(R):
            edges.append(dict(f=f, o="v", a=[0, j], b=None, side=[-1, 0], kind="outer"))
            edges.append(dict(f=f, o="v", a=[C - 1, j], b=None, side=[1, 0], kind="outer"))
    # outer walls round the courtyard void have nothing to do with the boundary; fine.
    win = {(f, tuple(c), tuple(s)) for f, c, s in WINDOWS}
    for e in edges:
        if e["kind"] == "outer" and (e["f"], tuple(e["a"]), tuple(e["side"])) in win:
            e["window"] = True
    # the front door (middle of the south wall) and the exit door (back passage, north wall)
    for e in edges:
        if e["kind"] == "outer" and e["f"] == 0 and e["side"] == [0, 1] and e["a"][0] in (3, 4):
            e["kind"] = "front"
        if e["kind"] == "outer" and e["f"] == 0 and e["side"] == [0, -1] and e["a"] == [4, 0]:
            e["kind"] = "exit"

    # walking graph (cell centres on each floor + the stairs)
    def walkable(f, i, j):
        r = room_at(f, i, j)
        if r is None or r["kind"] == "void":
            return False
        if f == 0 and (i, j) in stair_cells:
            return False
        return True
    links = []
    for e in edges:
        if e["b"] is None or e["kind"] not in ("same", "open", "door", "arch", "pooja", "wide"):
            continue
        f = e["f"]
        if walkable(f, *e["a"]) and walkable(f, *e["b"]):
            links.append([[e["a"][0], e["a"][1], f], [e["b"][0], e["b"][1], f]])
    fi, fj = STAIRS["foot"]
    ti, tj = STAIRS["top"]
    links.append([[fi, fj, 0], [ti, tj, 1]])
    nodes = [[i, j, f] for f in range(2) for j in range(R) for i in range(C) if walkable(f, i, j)]

    # the stairs: a straight flight over two cells, rising from the foot cell's edge to the top cell's edge
    (si0, sj0), (si1, sj1) = STAIRS["cells"]
    stairs = dict(foot=[fi, fj, 0], top=[ti, tj, 1], cells=[list(c) for c in STAIRS["cells"]], dir=list(STAIRS["dir"]),
                  x=cx(si0), z_start=z0 + sj0 * CELL, z_end=z0 + (sj1 + 1) * CELL, rise=FLOOR_H, width=CELL - WALL_T - 0.08)

    # lamps: one per room (two in the big ones), round the veranda and the gallery
    lights = []
    for r in rooms:
        if r["kind"] in ("void", "courtyard", "stairs"):
            continue
        y = r["floor"] * FLOOR_H + WALL_H - 0.55
        cells = r["cells"]
        if r["kind"] in ("veranda", "gallery"):
            picks = [c for c in cells if tuple(c) in ((2, 1), (5, 4))]       # two opposite corners
        elif r["kind"] == "passage" and len(cells) == 1 and r["floor"] == 0 and r["name"] == "back_passage":
            picks = []                                                       # lit by the veranda lamp next to it
        elif r["kind"] == "pooja":
            picks = []                                                       # only the samai lamps by the murti
        else:
            picks = [None] if len(cells) in (2, 4, 6) else [cells[len(cells) // 2]]
        for c in picks:
            if c is None:
                xs = sum(cx(c2[0]) for c2 in cells) / len(cells)
                zs = sum(cz(c2[1]) for c2 in cells) / len(cells)
                lights.append(dict(pos=[round(xs, 3), round(y, 3), round(zs, 3)], room=r["name"]))
            else:
                lights.append(dict(pos=[round(cx(c[0]), 3), round(y, 3), round(cz(c[1]), 3)], room=r["name"]))

    # item spots: against a plain wall of each chosen room, facing into the room
    edge_kind = {}
    for e in edges:
        if e["b"] is None:
            edge_kind[(e["f"], tuple(e["a"]), tuple(e["side"]))] = e
        else:
            a, b = tuple(e["a"]), tuple(e["b"])
            d = (b[0] - a[0], b[1] - a[1])
            edge_kind[(e["f"], a, d)] = e
            edge_kind[(e["f"], b, (-d[0], -d[1]))] = e
    items = []
    names = list(ITEMS)
    rnd.shuffle(names)
    for k, rn in enumerate(ITEM_ROOMS):
        r = [x for x in rooms if x["name"] == rn][0]
        cand = []
        for c in r["cells"]:
            for d in ((0, -1), (1, 0), (0, 1), (-1, 0)):
                e = edge_kind.get((r["floor"], tuple(c), d))
                if e and e["kind"] in ("wall", "outer") and not e.get("window"):
                    cand.append((c, d))
        c, d = cand[rnd.randrange(len(cand))]
        off = CELL / 2 - WALL_T / 2 - 0.5
        items.append(dict(id=names[k], room=rn, floor=r["floor"],
                          pos=[round(cx(c[0]) + d[0] * off, 3), round(cz(c[1]) + d[1] * off, 3)], face=[-d[0], -d[1]]))

    pooja = [x for x in rooms if x["name"] == "pooja_ghar"][0]
    pc = pooja["cells"][0]
    ritual = dict(chowki=[round(cx(pc[0]), 3), round(cz(pc[1] + 1) - 0.35, 3)], murti=[round(cx(pc[0]), 3), round(cz(pc[1]) - 0.85, 3)],
                  pooja_cell=pc, chaya_from=[4, 3, 0])
    aangan = [x for x in rooms if x["name"] == "aangan"][0]
    tulsi = [round(x0 + 4 * CELL, 3), round(z0 + 3 * CELL, 3)]
    spawn = dict(pos=[0.0, round(z0 + 6 * CELL - 0.2, 3)], yaw=0.0, floor=0)
    outside = dict(start=[0.0, round(z0 + R * CELL + 13.0, 3)], door=[0.0, round(z0 + R * CELL + 1.1, 3)])
    exit_e = [e for e in edges if e["kind"] == "exit"][0]
    exit_pos = [round(cx(exit_e["a"][0]), 3), round(z0, 3)]

    return dict(type="house", cols=C, rows=R, cell=CELL, wall_t=WALL_T, wall_h=WALL_H, slab=SLAB, floor_h=FLOOR_H, floors=2,
                x0=x0, z0=z0, door_w=DOOR_W, door_h=DOOR_H, rooms=rooms, region=region, edges=edges, wide=[list(w) for w in WIDE],
                links=links, nodes=nodes, stairs=stairs, lights=lights, items=items, ritual=ritual, tulsi=tulsi, spawn=spawn,
                outside=outside, exit=exit_pos, ghost_cell=[1, 0, 1], seed=seed)


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "layout.json"
    L = generate()
    json.dump(L, open(out, "w"))
    kinds = {}
    for e in L["edges"]:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    print("house: %d rooms, %d walkable cells, %d links, %d lamps, edges %s" % (len(L["rooms"]), len(L["nodes"]), len(L["links"]),
                                                                              len(L["lights"]), kinds))
    for it in L["items"]:
        print("  item %-9s in %s" % (it["id"], it["room"]))
