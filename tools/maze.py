#!/usr/bin/env python3
"""Chaya - maze layout generator.

Pure python. Produces layout.json: the old wooden house as a grid of cells (corridors, rooms, one locked
pooja room in the middle), wall runs, doorways, ritual item spots, lantern lights and the ghost's patrol cells.
Both the Blender map builder (tools/build_map.py) and the Godot game (game/scripts) read this file, so the
map the player sees, its collision and the ghost's path-finding always agree.

World coordinates are Godot's: x east, y up, z south. Cell (i, j): i grows east, j grows south.
"""
import json
import math
import random
import sys
from collections import deque

COLS, ROWS = 15, 11
CELL = 2.6
WALL_T = 0.22
WALL_H = 3.0
DOOR_W = 1.25
DOOR_H = 2.15

ITEMS = ["kalash", "diya", "coconut", "kumkum", "kapoor", "gangajal"]


class DSU:
    def __init__(self, n):
        self.p = list(range(n))

    def find(self, a):
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        a, b = self.find(a), self.find(b)
        if a == b:
            return False
        self.p[a] = b
        return True


def generate(seed=11):
    rnd = random.Random(seed)
    C, R = COLS, ROWS
    x0 = -C * CELL / 2.0
    z0 = -R * CELL / 2.0
    region = [[-1] * C for _ in range(R)]
    rooms = []

    def free(i0, j0, w, h, margin):
        for j in range(j0 - margin, j0 + h + margin):
            for i in range(i0 - margin, i0 + w + margin):
                if 0 <= i < C and 0 <= j < R and region[j][i] != -1:
                    return False
        return i0 >= 0 and j0 >= 0 and i0 + w <= C and j0 + h <= R

    def claim(i0, j0, w, h, name, kind, margin=1):
        if not free(i0, j0, w, h, margin):
            return False
        rid = len(rooms)
        for j in range(j0, j0 + h):
            for i in range(i0, i0 + w):
                region[j][i] = rid
        rooms.append(dict(id=rid, name=name, kind=kind, i0=i0, j0=j0, w=w, h=h))
        return True

    claim(0, R - 2, 2, 2, "start", "start", 0)
    claim(6, 4, 3, 3, "pooja", "pooja", 0)
    kinds = ["bedroom", "kitchen", "store", "hall", "study", "bedroom", "store", "hall", "kitchen"]
    sizes = [(3, 2), (2, 3), (2, 2), (3, 2), (2, 2), (2, 3), (2, 2), (3, 3), (2, 2)]
    tries = 0
    k = 0
    while k < len(sizes) and tries < 3000:
        tries += 1
        w, h = sizes[k]
        if claim(rnd.randrange(0, C - w + 1), rnd.randrange(0, R - h + 1), w, h, "%s%d" % (kinds[k], k), kinds[k], 1):
            k += 1

    idx = lambda i, j: j * C + i
    dsu = DSU(C * R)
    open_edges = set()

    def edge(a, b):
        return (a, b) if a < b else (b, a)

    def open_edge(a, b):
        open_edges.add(edge(a, b))

    # inside a room every wall is open
    for j in range(R):
        for i in range(C):
            if region[j][i] == -1:
                continue
            for di, dj in ((1, 0), (0, 1)):
                ni, nj = i + di, j + dj
                if ni < C and nj < R and region[nj][ni] == region[j][i]:
                    open_edge(idx(i, j), idx(ni, nj))
                    dsu.union(idx(i, j), idx(ni, nj))

    pooja = [r for r in rooms if r["kind"] == "pooja"][0]

    def in_pooja(i, j):
        return region[j][i] == pooja["id"]

    cand = []
    for j in range(R):
        for i in range(C):
            for di, dj in ((1, 0), (0, 1)):
                ni, nj = i + di, j + dj
                if ni >= C or nj >= R:
                    continue
                if in_pooja(i, j) or in_pooja(ni, nj):
                    continue
                if region[j][i] != -1 and region[j][i] == region[nj][ni]:
                    continue
                cand.append((idx(i, j), idx(ni, nj)))
    rnd.shuffle(cand)
    for a, b in cand:
        if dsu.union(a, b):
            open_edge(a, b)

    def neighbours(i, j):
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            if 0 <= ni < C and 0 <= nj < R:
                yield ni, nj

    def degree(i, j):
        return sum(1 for ni, nj in neighbours(i, j) if edge(idx(i, j), idx(ni, nj)) in open_edges)

    # braid: knock through some dead ends so the maze has loops (the ghost can circle around you)
    for j in range(R):
        for i in range(C):
            if region[j][i] != -1 or in_pooja(i, j) or degree(i, j) != 1:
                continue
            if rnd.random() < 0.5:
                opts = [(ni, nj) for ni, nj in neighbours(i, j)
                        if not in_pooja(ni, nj) and edge(idx(i, j), idx(ni, nj)) not in open_edges]
                if opts:
                    ni, nj = rnd.choice(opts)
                    open_edge(idx(i, j), idx(ni, nj))

    # the only way into the pooja room: a heavy door on its south side
    pi = pooja["i0"] + pooja["w"] // 2
    pj = pooja["j0"] + pooja["h"]
    pooja_door_edge = edge(idx(pi, pj - 1), idx(pi, pj))
    open_edges.add(pooja_door_edge)

    # ---- walls & doorways
    walls = []
    doorways = []

    def is_open(a, b):
        return edge(a, b) in open_edges

    # horizontal grid lines (walls along x): line j between row j-1 and row j, cell i
    def cell_xc(i):
        return x0 + (i + 0.5) * CELL

    def cell_zc(j):
        return z0 + (j + 0.5) * CELL

    runs_h = {}
    runs_v = {}
    did = 0
    for j in range(R + 1):
        cur = None
        for i in range(C + 1):
            closed = False
            doorway = None
            if i < C:
                if j == 0 or j == R:
                    closed = True
                else:
                    a, b = idx(i, j - 1), idx(i, j)
                    if is_open(a, b):
                        ra, rb = region[j - 1][i], region[j][i]
                        if edge(a, b) == pooja_door_edge:
                            doorway = "pooja"
                        elif ra != rb:
                            doorway = "door" if rnd.random() < 0.7 else "arch"
                    else:
                        closed = True
            if closed:
                if cur is None:
                    cur = i
            else:
                if cur is not None:
                    walls.append(dict(o="h", p=z0 + j * CELL, a=x0 + cur * CELL, b=x0 + i * CELL))
                    cur = None
                if doorway:
                    doorways.append(dict(id=did, o="h", p=z0 + j * CELL, c=cell_xc(i), kind=doorway,
                                         cells=[[i, j - 1], [i, j]]))
                    did += 1
    for i in range(C + 1):
        cur = None
        for j in range(R + 1):
            closed = False
            doorway = None
            if j < R:
                if i == 0 or i == C:
                    closed = True
                else:
                    a, b = idx(i - 1, j), idx(i, j)
                    if is_open(a, b):
                        ra, rb = region[j][i - 1], region[j][i]
                        if ra != rb:
                            doorway = "door" if rnd.random() < 0.7 else "arch"
                    else:
                        closed = True
            if closed:
                if cur is None:
                    cur = j
            else:
                if cur is not None:
                    walls.append(dict(o="v", p=x0 + i * CELL, a=z0 + cur * CELL, b=z0 + j * CELL))
                    cur = None
                if doorway:
                    doorways.append(dict(id=did, o="v", p=x0 + i * CELL, c=cell_zc(j), kind=doorway,
                                         cells=[[i - 1, j], [i, j]]))
                    did += 1

    # ---- graph distances from the start room
    start = [r for r in rooms if r["kind"] == "start"][0]
    sc = (start["i0"], start["j0"])
    dist = {}
    dq = deque([sc])
    dist[sc] = 0
    while dq:
        i, j = dq.popleft()
        for ni, nj in neighbours(i, j):
            if (ni, nj) in dist or edge(idx(i, j), idx(ni, nj)) not in open_edges:
                continue
            if in_pooja(ni, nj):
                continue
            dist[(ni, nj)] = dist[(i, j)] + 1
            dq.append((ni, nj))

    # ---- ritual item spots: dead ends and room corners, far from the start and from each other
    spots = []
    for (i, j), d in dist.items():
        if region[j][i] == start["id"] or d < 7:
            continue
        deg = degree(i, j)
        r = region[j][i]
        if r == -1 and deg == 1:
            spots.append((i, j, 3.0))
        elif r != -1 and rooms[r]["kind"] not in ("start", "pooja"):
            rr = rooms[r]
            corner = (i in (rr["i0"], rr["i0"] + rr["w"] - 1)) and (j in (rr["j0"], rr["j0"] + rr["h"] - 1))
            if corner:
                spots.append((i, j, 1.5))
    rnd.shuffle(spots)
    spots.sort(key=lambda s: -s[2] - rnd.random())
    chosen = []
    for s in spots:
        if all(math.hypot(s[0] - c[0], s[1] - c[1]) >= 4.5 for c in chosen):
            chosen.append(s)
        if len(chosen) == len(ITEMS):
            break
    if len(chosen) < len(ITEMS):          # relax the spacing
        for s in spots:
            if s not in chosen and all(math.hypot(s[0] - c[0], s[1] - c[1]) >= 3.0 for c in chosen):
                chosen.append(s)
            if len(chosen) == len(ITEMS):
                break
    items = []
    for n, (i, j, _) in enumerate(chosen):
        cx, cz = cell_xc(i), cell_zc(j)
        # push the pedestal against a closed wall of the cell (the side with no opening)
        best = None
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ni, nj = i + di, j + dj
            closed = not (0 <= ni < C and 0 <= nj < R) or edge(idx(i, j), idx(ni, nj)) not in open_edges
            if closed:
                best = (di, dj)
                if rnd.random() < 0.5:
                    break
        di, dj = best if best else (0, -1)
        off = CELL / 2 - WALL_T / 2 - 0.5
        items.append(dict(id=ITEMS[n], cell=[i, j], pos=[round(cx + di * off, 3), round(cz + dj * off, 3)],
                          face=[-di, -dj]))

    # ---- lanterns
    cells = [(i, j) for j in range(R) for i in range(C) if not in_pooja(i, j)]
    rnd.shuffle(cells)
    lights = []
    for i, j in cells:
        cx, cz = cell_xc(i), cell_zc(j)
        if all(math.hypot(cx - l["pos"][0], cz - l["pos"][2]) >= 5.3 for l in lights):
            lights.append(dict(pos=[round(cx, 3), WALL_H - 0.55, round(cz, 3)]))
        if len(lights) >= 20:
            break

    # ---- the ghost's spawn: the corner farthest from the player
    far = max(dist.items(), key=lambda kv: kv[1] if region[kv[0][1]][kv[0][0]] != pooja["id"] else -1)
    ghost_cell = list(far[0])

    # ---- props: slots inside rooms (the game places real furniture models here)
    props = []
    for r in rooms:
        if r["kind"] in ("start", "pooja"):
            continue
        for _ in range(3 + r["w"] * r["h"] // 3):
            i = rnd.randrange(r["i0"], r["i0"] + r["w"])
            j = rnd.randrange(r["j0"], r["j0"] + r["h"])
            # along the room's outer walls only
            sides = []
            if i == r["i0"]: sides.append((-1, 0))
            if i == r["i0"] + r["w"] - 1: sides.append((1, 0))
            if j == r["j0"]: sides.append((0, -1))
            if j == r["j0"] + r["h"] - 1: sides.append((0, 1))
            if not sides:
                continue
            di, dj = rnd.choice(sides)
            ni, nj = i + di, j + dj
            if 0 <= ni < C and 0 <= nj < R and edge(idx(i, j), idx(ni, nj)) in open_edges:
                continue                  # keep doorways clear
            t = rnd.uniform(-0.7, 0.7)
            along = (dj, di)              # perpendicular direction along the wall
            off = CELL / 2 - WALL_T / 2 - 0.45
            props.append(dict(room=r["name"], kind=r["kind"],
                              pos=[round(cell_xc(i) + di * off + along[0] * t, 3), round(cell_zc(j) + dj * off + along[1] * t, 3)],
                              yaw=round(math.degrees(math.atan2(-di, -dj)), 1)))

    out = dict(
        cols=C, rows=R, cell=CELL, wall_t=WALL_T, wall_h=WALL_H, door_w=DOOR_W, door_h=DOOR_H, x0=x0, z0=z0,
        region=region, rooms=rooms,
        edges=[[a, b] for a, b in sorted(open_edges)],
        walls=walls, doorways=doorways, items=items, lights=lights, props=props,
        spawn=dict(pos=[round(cell_xc(start["i0"]) + CELL / 2, 3), round(cell_zc(start["j0"]) + CELL / 2, 3)], yaw=0.0),
        ghost_cell=ghost_cell,
        pooja=dict(i0=pooja["i0"], j0=pooja["j0"], w=pooja["w"], h=pooja["h"],
                   center=[round(x0 + (pooja["i0"] + pooja["w"] / 2) * CELL, 3), round(z0 + (pooja["j0"] + pooja["h"] / 2) * CELL, 3)],
                   door=pooja_door_edge[0]),
        seed=seed,
    )
    return out


def ascii_map(L):
    C, R = L["cols"], L["rows"]
    edges = set(map(tuple, L["edges"]))
    ed = lambda a, b: ((a, b) if a < b else (b, a)) in edges
    idx = lambda i, j: j * C + i
    lines = []
    items = {tuple(it["cell"]): it["id"][0].upper() for it in L["items"]}
    for j in range(R):
        top = "+"
        mid = ""
        for i in range(C):
            top += ("   " if j > 0 and ed(idx(i, j - 1), idx(i, j)) else "---") + "+"
            left_open = i > 0 and ed(idx(i - 1, j), idx(i, j))
            r = L["region"][j][i]
            ch = items.get((i, j), "·" if r == -1 else str(r % 10))
            if [i, j] == L["ghost_cell"]:
                ch = "G"
            if (i, j) == (L["spawn"]["pos"][0] > 0 and 0, 0):
                pass
            mid += (" " if left_open else "|") + " " + ch + " "
        mid += "|"
        lines += [top, mid]
    lines.append("+" + "---+" * C)
    return "\n".join(lines)


if __name__ == "__main__":
    seed = int(sys.argv[2]) if len(sys.argv) > 2 else 11
    out = sys.argv[1] if len(sys.argv) > 1 else "layout.json"
    L = generate(seed)
    with open(out, "w") as f:
        json.dump(L, f, separators=(",", ":"))
    print(ascii_map(L))
    print("rooms:", [(r["name"], r["i0"], r["j0"], r["w"], r["h"]) for r in L["rooms"]])
    print("walls %d, doorways %d (%s), items %s, lights %d, props %d" % (
        len(L["walls"]), len(L["doorways"]), ",".join(sorted(set(d["kind"] for d in L["doorways"]))),
        [(i["id"], i["cell"]) for i in L["items"]], len(L["lights"]), len(L["props"])))
