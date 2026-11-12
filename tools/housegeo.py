"""Chaya - geometry of the two-storey courtyard house (see tools/house.py), as plain numpy arrays.

build(layout) -> (objs, meta), same conventions as tools/mazegeo.py (Godot / glTF axes, one UV unit = one texture repeat).
meta carries what the game needs besides the meshes: doors, the front and exit doors, item spots, pillars, the ritual
spot, collision boxes (walls, slabs, railings, the stairs ramp) and spots for lamps.
"""
import math
import numpy as np

import mazegeo
from mazegeo import Builder, Obj, TILE, SPLIT_H

TILE.update({
    "floor_courtyard": 1.8, "floor_marble": 1.6, "ext_plaster": 2.4, "ext_plinth": 1.6, "roof_top": 3.0, "roof_tiles": 1.4,
    "ground_mud": 4.0, "stair_wood": 1.2, "rail_wood": 0.8, "sindoor": 0.3, "silver": 0.3,
})
FLOOR_OF = {"kitchen": "floor_redtile", "pooja": "floor_marble", "veranda": "floor_terracotta", "entrance": "floor_terracotta",
            "passage": "floor_terracotta", "courtyard": "floor_courtyard", "store": "floor_terracotta", "stairs": "floor_terracotta"}
SOLID = ("wall", "outer", "front", "exit", "door", "arch", "pooja", "wide")


def build(L):
    B = Builder(L)
    C, R = L["cols"], L["rows"]
    S, T, H = L["cell"], L["wall_t"], L["wall_h"]
    FH, SL = L["floor_h"], L["slab"]
    x0, z0 = L["x0"], L["z0"]
    DW, DH = L["door_w"], L["door_h"]
    rooms = L["rooms"]
    region = L["region"]
    colliders = []

    def room(f, i, j):
        if 0 <= i < C and 0 <= j < R:
            return rooms[region[f][j][i]]
        return None

    def kind(f, i, j):
        r = room(f, i, j)
        return r["kind"] if r else None

    def cx(i):
        return x0 + (i + 0.5) * S

    def cz(j):
        return z0 + (j + 0.5) * S

    def col(cx_, cy_, cz_, sx, sy, sz, rx=0.0):
        colliders.append([round(cx_, 4), round(cy_, 4), round(cz_, 4), round(sx, 4), round(sy, 4), round(sz, 4), round(rx, 3)])

    stair_cells = set(tuple(c) for c in L["stairs"]["cells"])

    def has_ceiling(f, i, j):
        k = kind(f, i, j)
        if k is None:
            return False
        if f == 0:
            return k not in ("courtyard",) and (i, j) not in stair_cells
        return k != "void" or (i, j) in stair_cells

    def has_floor(f, i, j):
        k = kind(f, i, j)
        return k is not None and k != "void"

    # ---------------------------------------------------------------- floors, ceilings, slab edges, beams, roof
    for f in range(2):
        y = f * FH
        for j in range(R):
            for i in range(C):
                k = kind(f, i, j)
                ax, az = x0 + i * S, z0 + j * S
                if has_floor(f, i, j):
                    mat = FLOOR_OF.get(k, "floor_wood") if f == 0 else ("floor_wood" if k not in ("gallery", "passage") else "floor_wood")
                    B.face(mat, (ax, y, az), (S, 0, 0), (0, 0, S), (0, 1, 0))
                    if f == 1:
                        col(ax + S / 2, y - SL / 2, az + S / 2, S, SL, S)
                if has_ceiling(f, i, j):
                    B.face("ceiling_wood", (ax, y + H, az), (S, 0, 0), (0, 0, S), (0, -1, 0), cell=1.3)
                    for kk in (1, 2, 3):                                  # joists
                        xx = ax + kk * S / 4.0
                        B.box((xx - 0.035, y + H - 0.09, az), (xx + 0.035, y + H, az + S), "beam_wood", skip=("py",))
                # slab edges where the ceiling stops (the courtyard, the stairwell)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if has_ceiling(f, i, j) and not has_ceiling(f, i + di, j + dj) and room(f, i + di, j + dj) is not None:
                        if di:
                            xe = ax + (S if di > 0 else 0)
                            B.face("beam_wood", (xe, y + H - 0.24, az), (0, 0, S), (0, SL + 0.24 if f == 0 else 0.24, 0), (di, 0, 0))
                        else:
                            ze = az + (S if dj > 0 else 0)
                            B.face("beam_wood", (ax, y + H - 0.24, ze), (S, 0, 0), (0, SL + 0.24 if f == 0 else 0.24, 0), (0, 0, dj))
        # main beams where rooms run on without a wall (veranda, gallery, big rooms)
        for e in L["edges"]:
            if e["f"] != f or e["b"] is None or e["kind"] not in ("same",):
                continue
            (ia, ja), (ib, jb) = e["a"], e["b"]
            if not (has_ceiling(f, ia, ja) and has_ceiling(f, ib, jb)):
                continue
            if e["o"] == "v":
                xx = x0 + ib * S
                B.box((xx - 0.1, y + H - 0.24, z0 + ja * S), (xx + 0.1, y + H, z0 + (ja + 1) * S), "beam_wood", skip=("py",))
            else:
                zz = z0 + jb * S
                B.box((x0 + ia * S, y + H - 0.2, zz - 0.08), (x0 + (ia + 1) * S, y + H, zz + 0.08), "beam_wood", skip=("py",))
    # flat roof with a parapet, open over the courtyard
    roof_y = FH + H + SL
    for j in range(R):
        for i in range(C):
            if has_ceiling(1, i, j):
                B.face("roof_top", (x0 + i * S, roof_y, z0 + j * S), (S, 0, 0), (0, 0, S), (0, 1, 0), cell=2.6)
                for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    if room(1, i + di, j + dj) is not None and not has_ceiling(1, i + di, j + dj):
                        ax, az = x0 + i * S, z0 + j * S
                        if di:
                            xe = ax + (S if di > 0 else 0)
                            B.face("ext_plaster", (xe, roof_y - SL, az), (0, 0, S), (0, SL + 0.55, 0), (di, 0, 0))
                            B.face("ext_plaster", (xe - di * 0.15, roof_y, az), (0, 0, S), (0, 0.55, 0), (-di, 0, 0))
                            B.face("ext_plaster", (min(xe, xe - di * 0.15), roof_y + 0.55, az), (0.15, 0, 0), (0, 0, S), (0, 1, 0))
                        else:
                            ze = az + (S if dj > 0 else 0)
                            B.face("ext_plaster", (ax, roof_y - SL, ze), (S, 0, 0), (0, SL + 0.55, 0), (0, 0, dj))
                            B.face("ext_plaster", (ax, roof_y, ze - dj * 0.15), (S, 0, 0), (0, 0.55, 0), (0, 0, -dj))
                            B.face("ext_plaster", (ax, roof_y + 0.55, min(ze, ze - dj * 0.15)), (S, 0, 0), (0, 0, 0.15), (0, 1, 0))
    W, D = C * S, R * S
    pt = 0.24
    for (a, b, c_, o, s) in ((x0, x0 + W, z0, "h", -1), (x0, x0 + W, z0 + D, "h", 1), (z0, z0 + D, x0, "v", -1), (z0, z0 + D, x0 + W, "v", 1)):
        if o == "h":
            B.box((a - (pt if s else 0), roof_y, c_ - (pt if s < 0 else 0)), (b + pt, roof_y + 0.9, c_ + (pt if s > 0 else 0)), "ext_plaster", cell=2.6)
            B.box((a - pt - 0.04, roof_y + 0.9, c_ - (pt + 0.04 if s < 0 else 0.04)), (b + pt + 0.04, roof_y + 0.98, c_ + (pt + 0.04 if s > 0 else 0.04)),
                  "stone_base", cell=2.6)
        else:
            B.box((c_ - (pt if s < 0 else 0), roof_y, a), (c_ + (pt if s > 0 else 0), roof_y + 0.9, b), "ext_plaster", cell=2.6)
            B.box((c_ - (pt + 0.04 if s < 0 else 0.04), roof_y + 0.9, a - 0.04), (c_ + (pt + 0.04 if s > 0 else 0.04), roof_y + 0.98, b + 0.04),
                  "stone_base", cell=2.6)
    # the ground outside (village yard) and the floor under the house
    G = 36.0
    for (ax, az, bx, bz) in ((x0 - G, z0 - G, x0 + W + G, z0), (x0 - G, z0 + D, x0 + W + G, z0 + D + G),
                             (x0 - G, z0, x0, z0 + D), (x0 + W, z0, x0 + W + G, z0 + D)):
        go = Obj("ground_%d" % len(B.objs))
        B.face("ground_mud", (ax, -0.02, az), (bx - ax, 0, 0), (0, 0, bz - az), (0, 1, 0), obj=go, cell=6.0)
        B.objs.append(go)
    col(x0 + W / 2, -0.5, z0 + D / 2, W + 2 * G, 1.0, D + 2 * G)

    # ---------------------------------------------------------------- walls
    def edge_line(e):
        """(orientation, line coordinate, span a..b, cell on the negative side, cell on the positive side)"""
        (i, j) = e["a"]
        if e["b"] is None:
            di, dj = e["side"]
            if e["o"] == "h":
                p = z0 + (j + (1 if dj > 0 else 0)) * S
                return "h", p, x0 + i * S, x0 + (i + 1) * S, ((i, j) if dj > 0 else None), ((i, j) if dj < 0 else None)
            p = x0 + (i + (1 if di > 0 else 0)) * S
            return "v", p, z0 + j * S, z0 + (j + 1) * S, ((i, j) if di > 0 else None), ((i, j) if di < 0 else None)
        (ib, jb) = e["b"]
        if e["o"] == "h":
            return "h", z0 + jb * S, x0 + i * S, x0 + (i + 1) * S, (i, j), (ib, jb)
        return "v", x0 + ib * S, z0 + j * S, z0 + (j + 1) * S, (i, j), (ib, jb)

    solid_at = {}           # (f, o, line index, cell index along) -> edge kind
    for e in L["edges"]:
        o, p, a, b, cn, cp = edge_line(e)
        li = int(round(((p - z0) if o == "h" else (p - x0)) / S))
        ai = int(round(((a - x0) if o == "h" else (a - z0)) / S))
        solid_at[(e["f"], o, li, ai)] = e["kind"]

    def extents(f, o, p, a, b):
        li = int(round(((p - z0) if o == "h" else (p - x0)) / S))
        ai = int(round(((a - x0) if o == "h" else (a - z0)) / S))
        lo_ext = 0.0 if solid_at.get((f, o, li, ai - 1)) in SOLID else T / 2
        hi_ext = 0.0 if solid_at.get((f, o, li, ai + 1)) in SOLID else T / 2
        return a - lo_ext, b + hi_ext

    def face_side(f, o, p, a, b, ya, yb, side, inner):
        """One side of a wall piece: inside the house wainscot + plaster, outside plaster with a stone plinth."""
        fpos = p + side * T / 2
        nrm = (0, 0, side) if o == "h" else (side, 0, 0)
        base = f * FH

        def F(mat, y1, y2):
            if y2 - y1 < 1e-4:
                return
            if o == "h":
                B.face(mat, (a, y1, fpos), (b - a, 0, 0), (0, y2 - y1, 0), nrm)
            else:
                B.face(mat, (fpos, y1, a), (0, 0, b - a), (0, y2 - y1, 0), nrm)
        if inner:
            F("wall_wood", ya, min(yb, base + SPLIT_H))
            F("wall_plaster", max(ya, base + SPLIT_H), yb)
            ends = ("nx", "px") if o == "h" else ("nz", "pz")
            inward = ("pz" if side < 0 else "nz") if o == "h" else ("px" if side < 0 else "nx")
            ch = B.chunk(*(((a + b) / 2, fpos) if o == "h" else (fpos, (a + b) / 2)))
            if ya <= base + 1e-3:
                B.box_un(ch, o, a, b, base, base + 0.13, fpos, fpos + side * 0.03, "trim_wood", skip=("ny", inward) + ends)
            if ya < base + SPLIT_H < yb:
                B.box_un(ch, o, a, b, base + SPLIT_H - 0.04, base + SPLIT_H + 0.04, fpos, fpos + side * 0.03, "trim_wood", skip=(inward,) + ends)
        else:
            top = yb
            if f == 0:
                F("ext_plinth", ya, min(top, 0.6))
                F("ext_plaster", max(ya, 0.6), top)
            else:
                F("ext_plaster", ya, top)

    def wall_piece(f, o, p, a, b, ya, yb, cneg, cpos, jambs=False, outer_top=None):
        kn = kind(f, *cneg) if cneg else None
        kp = kind(f, *cpos) if cpos else None
        for side, k, c in ((-1, kn, cneg), (1, kp, cpos)):
            if c is None:          # outside the house: full height over the slab
                face_side(f, o, p, a, b, ya, outer_top if outer_top is not None else yb, side, False)
            elif k != "void":
                face_side(f, o, p, a, b, ya, yb, side, True)
        if jambs:
            for e_ in (a, b):
                if o == "h":
                    B.face("trim_wood", (e_, ya, p - T / 2), (0, 0, T), (0, yb - ya, 0), (1 if e_ == b else -1, 0, 0))
                else:
                    B.face("trim_wood", (p - T / 2, ya, e_), (T, 0, 0), (0, yb - ya, 0), (0, 0, 1 if e_ == b else -1))
        if o == "h":
            col((a + b) / 2, (ya + yb) / 2, p, b - a, yb - ya, T)
        else:
            col(p, (ya + yb) / 2, (a + b) / 2, T, yb - ya, b - a)

    windows = []
    doors = []
    special = {}
    for e in L["edges"]:
        f = e["f"]
        base = f * FH
        o, p, a, b, cneg, cpos = edge_line(e)
        k = e["kind"]
        is_outer = e["b"] is None or k in ("front", "exit")
        top = base + H
        outer_top = base + FH if is_outer else None
        if k in ("wall", "outer"):
            a2, b2 = extents(f, o, p, a, b)
            wall_piece(f, o, p, a2, b2, base, top, cneg, cpos, outer_top=outer_top)
            if is_outer and f == 0:
                pass
            if e.get("window"):
                windows.append((f, o, p, (a + b) / 2, e["side"]))
        elif k == "railing":
            railing(B, f * FH, o, p, a, b, col)
        elif k in ("door", "arch", "pooja"):
            ow, oh = {"door": (DW, DH), "arch": (DW + 0.35, DH + 0.15), "pooja": (DW + 0.2, DH + 0.1)}[k]
            c = (a + b) / 2
            a2, b2 = extents(f, o, p, a, b)
            doorway(B, f, o, p, a2, b2, c, ow, oh, base, top, cneg, cpos, wall_piece, k, e, doors, outer_top)
        elif k in ("front", "exit"):
            special.setdefault(k, []).append((f, o, p, a, b, cneg, cpos, base, top, outer_top))
    # the wide arch from the entrance hall into the veranda (between two cells)
    for (f, o, line, c0, w, h, kd) in L["wide"]:
        base = f * FH
        p = z0 + line * S
        a, b = x0 + c0[0] * S, x0 + (c0[0] + 2) * S
        a2 = a - (0.0 if solid_at.get((f, o, line, c0[0] - 1)) in SOLID else T / 2)
        b2 = b + (0.0 if solid_at.get((f, o, line, c0[0] + 2)) in SOLID else T / 2)
        doorway(B, f, o, p, a2, b2, (a + b) / 2, w, h, base, base + H, (c0[0], line - 1), (c0[0], line), wall_piece, "arch", None, doors, None)
    # the front door (double, middle of the south wall) and the exit door (back passage, north wall)
    front = exitd = None
    for k, segs in special.items():
        f, o, p = segs[0][0], segs[0][1], segs[0][2]
        a = min(s[3] for s in segs)
        b = max(s[4] for s in segs)
        cneg, cpos = segs[0][5], segs[0][6]
        base, top, outer_top = segs[0][7], segs[0][8], segs[0][9]
        a2, b2 = extents(f, o, p, a, a + S)[0], extents(f, o, p, b - S, b)[1]
        if k == "front":
            front = big_door(B, f, o, p, a2, b2, (a + b) / 2, 1.6, 2.45, base, top, cneg, cpos, wall_piece, outer_top, double=True, name="front_door")
            # stone step and a tiled awning (chhajja) on wooden brackets outside the front door
            zf = p + T / 2
            B.box((-1.3, -0.02, zf), (1.3, 0.16, zf + 1.0), "stone_base", cell=2.6)
            awning(B, -1.6, 1.6, zf, 2.95, 1.05)
        else:
            exitd = big_door(B, f, o, p, a2, b2, (a + b) / 2, 1.1, 2.2, base, top, cneg, cpos, wall_piece, outer_top, double=False, name="exit_door")
    # windows: closed wooden shutters on both faces of the outer walls
    for (f, o, p, uc, side) in windows:
        base = f * FH
        s = side[1] if o == "h" else side[0]
        for face_s in (s, -s):
            fpos = p + face_s * T / 2
            wo = B.chunk(*((uc, fpos) if o == "h" else (fpos, uc)))
            w2, ya, yb = 0.48, base + 0.95, base + 2.15
            B.box_un(wo, o, uc - w2 - 0.1, uc + w2 + 0.1, ya - 0.08, ya, fpos, fpos + face_s * 0.12, "stone_base" if face_s == s else "trim_wood")
            B.box_un(wo, o, uc - w2 - 0.08, uc - w2, ya, yb, fpos, fpos + face_s * 0.06, "trim_wood")
            B.box_un(wo, o, uc + w2, uc + w2 + 0.08, ya, yb, fpos, fpos + face_s * 0.06, "trim_wood")
            B.box_un(wo, o, uc - w2 - 0.12, uc + w2 + 0.12, yb, yb + 0.12, fpos, fpos + face_s * 0.08, "trim_wood")
            for ua, ub in ((uc - w2, uc - 0.004), (uc + 0.004, uc + w2)):
                B.box_un(wo, o, ua, ub, ya, yb, fpos, fpos + face_s * 0.035, "shutter_wood")
            B.box_un(wo, o, uc - 0.06, uc + 0.06, base + 1.5, base + 1.54, fpos + face_s * 0.035, fpos + face_s * 0.05, "brass")

    # ---------------------------------------------------------------- the stairs (solid steps; the game walks a ramp)
    st = L["stairs"]
    n_steps = 18
    rise = st["rise"] / n_steps
    run = (st["z_end"] - st["z_start"]) / n_steps
    hw = st["width"] / 2
    sx = st["x"]
    so = Obj("stairs", (sx, 0.0, (st["z_start"] + st["z_end"]) / 2))
    for kk in range(n_steps):
        za = st["z_start"] + kk * run
        yt = (kk + 1) * rise
        B.box((sx - hw, 0.0, za), (sx + hw, yt - 0.04, za + run), {"nz": "wall_plaster", "py": None, "default": None}, obj=so)
        B.box((sx - hw, yt - 0.04, za - 0.025), (sx + hw, yt, za + run), {"default": "stair_wood", "ny": None, "px": None, "nx": None}, obj=so)
    B.objs.append(so)
    ln = math.hypot(st["z_end"] - st["z_start"], st["rise"])
    ang = math.atan2(st["rise"], st["z_end"] - st["z_start"])
    mz, my = (st["z_start"] + st["z_end"]) / 2, st["rise"] / 2
    nrm = (math.cos(ang), -math.sin(ang))           # (y, z) of the ramp's upward normal
    col(sx, my - nrm[0] * 0.1, mz - nrm[1] * 0.1, st["width"], 0.2, ln + 0.2, -math.degrees(ang))

    # ---------------------------------------------------------------- pillars round the courtyard (both floors)
    pillars = []
    aangan = [r for r in rooms if r["kind"] == "courtyard"][0]
    ai = [c[0] for c in aangan["cells"]]
    aj = [c[1] for c in aangan["cells"]]
    gi0, gi1, gj0, gj1 = min(ai), max(ai) + 1, min(aj), max(aj) + 1
    for gj in range(gj0, gj1 + 1):
        for gi in range(gi0, gi1 + 1):
            if gi0 < gi < gi1 and gj0 < gj < gj1:
                continue                                   # the middle of the courtyard: the tulsi chaura stands there
            px, pz = x0 + gi * S, z0 + gj * S
            for f in range(2):
                pillar(B, px, pz, f * FH, H)
                pillars.append([round(px, 3), round(pz, 3), round(f * FH, 3)])
                col(px, f * FH + H / 2, pz, 0.36, H, 0.36)
    # beams over the courtyard edge on the ground floor (the gallery floor rests on them)
    for e in L["edges"]:
        if e["f"] == 0 and e["kind"] == "open" and {kind(0, *e["a"]), kind(0, *e["b"])} == {"veranda", "courtyard"}:
            o, p, a, b, _, _ = edge_line(e)
            B.box_un(B.chunk(*(((a + b) / 2, p) if o == "h" else (p, (a + b) / 2))), o, a, b, H - 0.26, FH, p - 0.13, p + 0.13, "beam_wood")

    # ---------------------------------------------------------------- the tulsi chaura in the middle of the courtyard
    tx, tz = L["tulsi"]
    to = Obj("tulsi_chaura", (tx, 0.0, tz))
    B.box((tx - 0.5, 0.0, tz - 0.5), (tx + 0.5, 0.15, tz + 0.5), "stone_base", obj=to, cell=2.6)
    B.box((tx - 0.36, 0.15, tz - 0.36), (tx + 0.36, 0.95, tz + 0.36), "ext_plaster", obj=to, cell=2.6)
    B.box((tx - 0.42, 0.95, tz - 0.42), (tx + 0.42, 1.02, tz + 0.42), "stone_base", obj=to, cell=2.6)
    B.box((tx - 0.12, 0.35, tz + 0.36), (tx + 0.12, 0.6, tz + 0.37), "trim_wood", obj=to, cell=2.6)       # the little lamp niche
    B.objs.append(to)
    col(tx, 0.5, tz, 1.0, 1.0, 1.0)

    # ---------------------------------------------------------------- the pooja ghar: marble platform for the murti
    rt = L["ritual"]
    mx_, mz_ = rt["murti"]
    po = Obj("murti_platform", (mx_, 0.0, mz_))
    B.box((mx_ - 0.8, 0.0, mz_ - 0.45), (mx_ + 0.8, 0.32, mz_ + 0.45), "floor_marble", obj=po, cell=2.6)
    B.box((mx_ - 0.55, 0.32, mz_ - 0.38), (mx_ + 0.55, 0.62, mz_ + 0.2), "floor_marble", obj=po, cell=2.6)
    B.objs.append(po)
    col(mx_, 0.31, mz_, 1.6, 0.62, 0.9)
    # the ritual chowki on the veranda in front of it (low wooden stool with a red cloth)
    kx, kz = rt["chowki"]
    ko = Obj("chowki", (kx, 0.0, kz))
    for lx in (-0.38, 0.38):
        for lz in (-0.38, 0.38):
            B.box((kx + lx - 0.04, 0.0, kz + lz - 0.04), (kx + lx + 0.04, 0.28, kz + lz + 0.04), "trim_wood", obj=ko, cell=2.6)
    B.box((kx - 0.45, 0.28, kz - 0.45), (kx + 0.45, 0.34, kz + 0.45), "trim_wood", obj=ko, cell=2.6)
    B.box((kx - 0.47, 0.34, kz - 0.47), (kx + 0.47, 0.36, kz + 0.47), "red_cloth", obj=ko, cell=2.6)
    B.objs.append(ko)
    col(kx, 0.18, kz, 0.95, 0.36, 0.95)

    # ---------------------------------------------------------------- simple lanterns (build_map.py swaps in scanned ones)
    for li, l in enumerate(L["lights"]):
        x, y, z = l["pos"]
        ch = Obj("lamp_%d" % li, (x, 0.0, z))
        B.lathe(ch, "lantern_glow", [(0.1, y - 0.2), (0.105, y), (0.1, y + 0.2)], 8, (x, 0, z))
        B.objs.append(ch)

    # ---------------------------------------------------------------- item stands (build_map.py swaps in scanned ones)
    items = []
    for it in L["items"]:
        x, z = it["pos"]
        base = it["floor"] * FH
        ped = Obj("pedestal_" + it["id"], (x, base, z))
        top = base + 0.74
        B.box((x - 0.28, top - 0.05, z - 0.28), (x + 0.28, top, z + 0.28), "trim_wood", obj=ped, cell=10.0)
        for lx in (-0.23, 0.23):
            for lz in (-0.23, 0.23):
                B.box((x + lx - 0.03, base, z + lz - 0.03), (x + lx + 0.03, top - 0.05, z + lz + 0.03), "trim_wood", obj=ped, cell=10.0)
        B.objs.append(ped)
        o = Obj("item_" + it["id"], (x, top, z), local=True)
        mazegeo.add_item(B, o, it["id"])
        B.objs.append(o)
        items.append(dict(id=it["id"], name=o.name, pos=[x, top, z], face=it.get("face", [0, 1]), ped=[0.56, 0.56], floor=it["floor"]))

    objs = [c for _, c in sorted(B.chunks.items())] + B.objs
    for o in objs:
        o.finish()
    meta = dict(doors=doors, items=items, pillars=pillars, colliders=colliders, front_door=front, exit_door=exitd,
                altar=dict(pos=[kx, 0.36, kz]), murti=dict(pos=[mx_, 0.62, mz_], yaw=0.0), tulsi=dict(pos=[tx, 1.02, tz]),
                windows=[[w[0], w[1], round(w[2], 3), round(w[3], 3), w[4]] for w in windows])
    return objs, meta


def railing(B, y, o, p, a, b, col):
    """A turned wooden balustrade with a hand rail along a gallery edge."""
    ch = B.chunk(*(((a + b) / 2, p) if o == "h" else (p, (a + b) / 2)))
    B.box_un(ch, o, a, b, y, y + 0.1, p - 0.07, p + 0.07, "trim_wood")
    B.box_un(ch, o, a, b, y + 0.86, y + 0.96, p - 0.08, p + 0.08, "trim_wood")
    n = max(2, int((b - a) / 0.2))
    prof = [(0.028, 0.0), (0.03, 0.06), (0.018, 0.12), (0.03, 0.3), (0.034, 0.38), (0.018, 0.5), (0.016, 0.62), (0.026, 0.7), (0.022, 0.76)]
    for k in range(1, n):
        u = a + (b - a) * k / n
        c = (u, y + 0.1, p) if o == "h" else (p, y + 0.1, u)
        B.lathe(ch, "trim_wood", prof, seg=6, center=c)
    if o == "h":
        col((a + b) / 2, y + 0.5, p, b - a, 1.0, 0.16)
    else:
        col(p, y + 0.5, (a + b) / 2, 0.16, 1.0, b - a)


def pillar(B, x, z, y0, H):
    """A turned teak pillar on a stone plinth with a bracket capital, for a storey of height H starting at y0."""
    o = B.chunk(x, z)
    B.box((x - 0.19, y0, z - 0.19), (x + 0.19, y0 + 0.2, z + 0.19), "stone_base", obj=o, skip=("ny",), cell=10.0)
    k = (H - 0.24 - 0.32) / (2.47 - 0.3)
    prof = [(0.12, 0.0), (0.13, 0.03), (0.096, 0.08), (0.088, 0.2), (0.11, 0.26), (0.126, 0.32), (0.11, 0.38), (0.084, 0.44),
            (0.08, 0.6), (0.077, 1.25), (0.088, 1.32), (0.106, 1.38), (0.088, 1.44), (0.077, 1.5), (0.075, 1.92), (0.094, 2.0),
            (0.122, 2.08), (0.13, 2.13), (0.115, 2.17)]
    prof = [(r, y0 + 0.2 + yy * k) for r, yy in prof]
    B.lathe(o, "pillar_wood", prof, seg=12, center=(x, 0, z))
    top = y0 + H - 0.26
    cap0 = prof[-1][1]
    B.box((x - 0.15, cap0, z - 0.15), (x + 0.15, cap0 + 0.08, z + 0.15), "pillar_wood", obj=o, cell=10.0)
    for (dx, dz) in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ya, yb = cap0 + 0.08, top
        ln = 0.34
        if dx:
            B.box((x + min(0, dx * ln), ya, z - 0.06), (x + max(0, dx * ln), yb, z + 0.06), "pillar_wood", obj=o, cell=10.0)
        else:
            B.box((x - 0.06, ya, z + min(0, dz * ln)), (x + 0.06, yb, z + max(0, dz * ln)), "pillar_wood", obj=o, cell=10.0)


def doorway(B, f, o, p, a, b, c, ow, oh, base, top, cneg, cpos, wall_piece, kind, e, doors, outer_top):
    """Wall pieces round an opening, a plain wooden frame, and (doors) a plank door leaf on a hinge."""
    T = B.L["wall_t"]
    wall_piece(f, o, p, a, c - ow / 2, base, top, cneg, cpos, jambs=True, outer_top=outer_top)
    wall_piece(f, o, p, c + ow / 2, b, base, top, cneg, cpos, jambs=True, outer_top=outer_top)
    wall_piece(f, o, p, c - ow / 2, c + ow / 2, base + oh, top, cneg, cpos, outer_top=outer_top)
    ch = B.chunk(*((c, p) if o == "h" else (p, c)))
    if o == "h":
        B.face("trim_wood", (c - ow / 2, base + oh, p - T / 2), (ow, 0, 0), (0, 0, T), (0, -1, 0), obj=ch, cell=10.0)
    else:
        B.face("trim_wood", (p - T / 2, base + oh, c - ow / 2), (T, 0, 0), (0, 0, ow), (0, -1, 0), obj=ch, cell=10.0)
    fw, pr = 0.09, 0.025
    for ua, ub in ((c - ow / 2 - fw, c - ow / 2), (c + ow / 2, c + ow / 2 + fw)):
        B.box_un(ch, o, ua, ub, base, base + oh + fw, p - T / 2 - pr, p + T / 2 + pr, "trim_wood", skip=("ny",))
    B.box_un(ch, o, c - ow / 2 - fw, c + ow / 2 + fw, base + oh, base + oh + fw, p - T / 2 - pr, p + T / 2 + pr, "trim_wood")
    if kind in ("door", "pooja"):
        leaf_w, leaf_h = ow - 0.03, oh - 0.02
        th = 0.055 if kind == "door" else 0.08
        idx = len(doors)
        hinge_side = -1 if idx % 2 == 0 else 1
        hu = c + hinge_side * (ow / 2 - 0.015)
        hinge = np.array([hu, base, p]) if o == "h" else np.array([p, base, hu])
        name = ("door_%d" % idx) if kind == "door" else "pooja_door"
        lo = Obj(name, hinge)
        sgn = -hinge_side
        u0, u1 = sorted((hu, hu + sgn * leaf_w))
        B.box_un(lo, o, u0, u1, base + 0.01, base + leaf_h, p - th / 2, p + th / 2, "door_wood")
        if kind == "pooja":                          # brass bands and a pair of small bells on the pooja door
            for s in (-1, 1):
                nf = p + s * th / 2
                for yb in (base + 0.35, base + leaf_h - 0.45):
                    B.box_un(lo, o, u0, u1, yb, yb + 0.07, nf, nf + s * 0.006, "brass")
        hx = hu + sgn * (leaf_w - 0.12)
        for s in (-1, 1):                            # brass ring handle (kundi) on both sides
            nf = p + s * (th / 2)
            B.box_un(lo, o, hx - 0.03, hx + 0.03, base + 0.96, base + 1.04, nf, nf + s * 0.012, "brass")
            B.box_un(lo, o, hx - 0.008, hx + 0.008, base + 0.9, base + 0.97, nf + s * 0.012, nf + s * 0.024, "brass")
        B.objs.append(lo)
        doors.append(dict(name=name, hinge=hinge.tolist(), o=o, sgn=sgn, kind=kind, width=leaf_w, height=leaf_h, thick=th, floor=f))


def big_door(B, f, o, p, a, b, c, ow, oh, base, top, cneg, cpos, wall_piece, outer_top, double=True, name="front_door"):
    """The front door (double) or the exit door (single) in an outer wall: plank leaves on hinges, iron straps."""
    T = B.L["wall_t"]
    wall_piece(f, o, p, a, c - ow / 2, base, top, cneg, cpos, jambs=True, outer_top=outer_top)
    wall_piece(f, o, p, c + ow / 2, b, base, top, cneg, cpos, jambs=True, outer_top=outer_top)
    wall_piece(f, o, p, c - ow / 2, c + ow / 2, base + oh, top, cneg, cpos, outer_top=outer_top)
    ch = B.chunk(*((c, p) if o == "h" else (p, c)))
    if o == "h":
        B.face("trim_wood", (c - ow / 2, base + oh, p - T / 2), (ow, 0, 0), (0, 0, T), (0, -1, 0), obj=ch, cell=10.0)
    fw, pr = 0.12, 0.04
    for ua, ub in ((c - ow / 2 - fw, c - ow / 2), (c + ow / 2, c + ow / 2 + fw)):
        B.box_un(ch, o, ua, ub, base, base + oh + fw, p - T / 2 - pr, p + T / 2 + pr, "pillar_wood", skip=("ny",))
    B.box_un(ch, o, c - ow / 2 - fw - 0.05, c + ow / 2 + fw + 0.05, base + oh, base + oh + fw + 0.04, p - T / 2 - pr, p + T / 2 + pr, "pillar_wood")
    leaves = []
    th = 0.07
    halves = [(-1, c - ow / 2 + 0.01, c - 0.004), (1, c + 0.004, c + ow / 2 - 0.01)] if double else [(-1, c - ow / 2 + 0.01, c + ow / 2 - 0.01)]
    for (side, u0, u1) in halves:
        hu = u0 if side < 0 else u1
        hinge = np.array([hu, base, p]) if o == "h" else np.array([p, base, hu])
        nm = name + ("_l" if side < 0 else "_r") if double else name
        lo = Obj(nm, hinge)
        B.box_un(lo, o, u0, u1, base + 0.01, base + oh - 0.02, p - th / 2, p + th / 2, "door_wood")
        for s in (-1, 1):
            nf = p + s * th / 2
            for yb in (base + 0.45, base + oh - 0.55):
                B.box_un(lo, o, u0 + 0.02, u1 - 0.02, yb, yb + 0.06, nf, nf + s * 0.01, "iron")
            hx = (u1 - 0.12) if side < 0 else (u0 + 0.12)
            if not double:
                hx = u1 - 0.12
            B.box_un(lo, o, hx - 0.035, hx + 0.035, base + 1.0, base + 1.08, nf, nf + s * 0.014, "brass")
        B.objs.append(lo)
        leaves.append(dict(name=nm, hinge=hinge.tolist(), o=o, sgn=(1 if side < 0 else -1), width=u1 - u0, height=oh - 0.03, thick=th, floor=f))
    return dict(leaves=leaves, center=[c if o == "h" else p, base, p if o == "h" else c], width=ow, height=oh)


def awning(B, xa, xb, zf, y, depth):
    """A small sloping roof of clay tiles on wooden brackets over the front door."""
    o = Obj("awning", ((xa + xb) / 2, y, zf + depth / 2))
    drop = 0.35
    P = [(xa, y, zf), (xb, y, zf), (xb, y - drop, zf + depth), (xa, y - drop, zf + depth)]
    n = np.cross(np.subtract(P[1], P[0]), np.subtract(P[3], P[0]))
    B.quad(o, "roof_tiles", P, tuple(-n if n[1] < 0 else n))
    B.quad(o, "trim_wood", P, tuple(n if n[1] < 0 else -n))
    B.box((xa, y - drop - 0.06, zf + depth - 0.05), (xb, y - drop + 0.02, zf + depth + 0.02), "trim_wood", obj=o, cell=10.0)
    for xx in (xa + 0.2, xb - 0.2):
        B.tilted_box(o, "trim_wood", (xx, y - 0.32, zf + depth * 0.45), (0.07, 0.07, depth * 1.05), yaw=0.0, pitch=-20.0)
    B.objs.append(o)
