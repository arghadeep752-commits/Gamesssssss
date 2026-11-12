"""Validates chunk shapes and checks every level is completable (approximate jump-graph BFS)."""
import re
import sys
from collections import deque

PRJ = sys.argv[1] if len(sys.argv) > 1 else "/home/claude/ninja_shadow_legacy"
src = open(f"{PRJ}/scripts/levels/chunk_library.gd").read()
chunks = {}
for m in re.finditer(r'"(\w+)":\s*\[(.*?)\]', src, re.S):
    rows = re.findall(r'"([^"]*)"', m.group(2))
    chunks[m.group(1)] = rows

ok = True
for name, rows in chunks.items():
    w = {len(r) for r in rows}
    if len(w) != 1:
        print("BAD WIDTH", name, [len(r) for r in rows])
        ok = False
    if rows[-2][0] not in "#F=" or rows[-2][-1] not in "#":
        print("EDGE?", name, rows[-2][0], rows[-2][-1])

H = 22
SOLID = set("#X?B")  # standable solids (crate/blocks are solid until broken)
PLAT = set("=FMVm")


def build(seq):
    cols = []
    for name in seq:
        rows = chunks[name]
        w = len(rows[0])
        top = 19 - len(rows)
        grid = [["."] * w for _ in range(H)]
        for i, r in enumerate(rows):
            for x, ch in enumerate(r):
                grid[top + i][x] = ch
        for y in range(19, H):
            for x in range(w):
                ch = rows[-1][x]
                grid[y][x] = "#" if ch in "^#" else ("L" if ch == "L" else ".")
        for x in range(w):
            cols.append([grid[y][x] for y in range(H)])
    W = len(cols)
    g = [[cols[x][y] for x in range(W)] for y in range(H)]
    # moving platforms cover their whole travel range
    for y in range(H):
        for x in range(W):
            if g[y][x] == "M":
                for k in range(-5, 6):
                    if 0 <= x + k < W and g[y][x + k] == ".":
                        g[y][x + k] = "m"
            if g[y][x] == "V":
                for dy in range(-3, 4):
                    for k in (-1, 0, 1):
                        if 0 <= y + dy < H and 0 <= x + k < W and g[y + dy][x + k] == ".":
                            g[y + dy][x + k] = "m"
    return g, W


def standable(g, W, x, y):
    if not (0 <= x < W and 0 <= y < H - 1):
        return False
    c = g[y][x]
    if c in SOLID or c == "L":
        return False
    below = g[y + 1][x]
    return below in SOLID or below in PLAT or below == "H" or c == "H"


def blocked(g, W, x, y):
    if x < 0 or x >= W or y < 0:
        return True
    if y >= H:
        return False
    return g[y][x] in SOLID


def reach(g, W, start, max_rise, max_dx):
    seen = {start}
    q = deque([start])
    while q:
        x, y = q.popleft()
        # ladders
        for dy in (-1, 1):
            ny = y + dy
            if 0 <= ny < H and (g[ny][x] == "H" or g[y][x] == "H") and not blocked(g, W, x, ny):
                if (x, ny) not in seen:
                    seen.add((x, ny)); q.append((x, ny))
        for nx in range(x - max_dx - 3, x + max_dx + 4):
            for ny in range(max(0, y - max_rise), H - 1):
                if (nx, ny) in seen or not standable(g, W, nx, ny):
                    continue
                dx = abs(nx - x)
                rise = y - ny
                limit = max_dx + (0 if rise >= 0 else min(3, (-rise) // 2))
                if dx > limit:
                    continue
                # head clearance along the jump: need free cells above start for rises
                if rise > 0 and any(blocked(g, W, x, y - k) for k in range(1, rise + 1)):
                    continue
                if rise > 0 and any(blocked(g, W, nx, ny - 1 - k) for k in range(0, 1)):
                    continue
                seen.add((nx, ny)); q.append((nx, ny))
        if g[y + 1][x] == "J" or g[y][x] == "J":
            for ny in range(max(0, y - 8), y):
                for nx in range(x - 4, x + 5):
                    if standable(g, W, nx, ny) and (nx, ny) not in seen:
                        seen.add((nx, ny)); q.append((nx, ny))
    return seen


import glob
fail = 0
for path in sorted(glob.glob(f"{PRJ}/resources/levels/level_*.tres")):
    txt = open(path).read()
    seq = re.findall(r'"(\w+)"', re.search(r"chunks = PackedStringArray\((.*?)\)", txt).group(1))
    idx = int(re.search(r"index = (\d+)", txt).group(1))
    world = int(re.search(r"world = (\d+)", txt).group(1))
    missing = [s for s in seq if s not in chunks]
    if missing:
        print(idx, "MISSING", missing); fail += 1; continue
    g, W = build(seq)
    P = E = None
    for y in range(H):
        for x in range(W):
            if g[y][x] == "P": P = (x, y)
            if g[y][x] == "E": E = (x, y)
    rise, dx = (3, 4) if world == 1 else (5, 6)
    seen = reach(g, W, P, rise, dx)
    good = E in seen
    print("level %02d w%d width=%d %s" % (idx, world, W, "OK" if good else "UNREACHABLE"))
    if not good:
        fail += 1
        far = max(seen, key=lambda p: p[0])
        print("   furthest reach", far, "of", W)
print("chunks ok" if ok else "chunk errors", "| failures:", fail)
