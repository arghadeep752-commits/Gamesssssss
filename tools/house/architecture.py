"""The house's walls, floors, ceilings, stair, windows, doors and the outside, built from layout.py (numpy only).

build(L) -> (chunks, dyn, coll)
  chunks: {"arch_<room>": Geo, "arch_outside": Geo, "glass": Geo}  - every surface belongs to the room it faces, so
          each room gets its own baked lightmap
  dyn:    {name: {"geo": Geo (relative to pivot), "pivot": (x, y, z), ...}}  - door leaves, the main door's planks
          and padlocks, the keypad light
  coll:   collision boxes [(x0, x1, y0, y1, z0, z1, rot_x_deg), ...] (rot_x tilts the stair ramp)
"""
import math

import numpy as np

import layout as LY
from geo import Geo, rot_z

FRAME = 0.05          # window frame width
GLASS = "glass"


def _rooms_on(floor):
    return [r for r in LY.ROOMS if r[1] == floor]


def _edge_t(floor, rect, side):
    """Half thickness of the wall on one side of a room rect (0 where the room is open to the next one)."""
    x0, y0, x1, y1 = rect
    for (fl, ax, c, a, b, t, _o) in LY.WALLS:
        if fl != floor:
            continue
        if side in ("w", "e") and ax == "y":
            xv = x0 if side == "w" else x1
            if abs(c - xv) < 1e-6 and a <= (y0 + y1) / 2 <= b:
                return t / 2
        if side in ("s", "n") and ax == "x":
            yv = y0 if side == "s" else y1
            if abs(c - yv) < 1e-6 and a <= (x0 + x1) / 2 <= b:
                return t / 2
    return 0.0


def inner_rect(room):
    name, floor, rect = room[0], room[1], room[2]
    x0, y0, x1, y1 = rect
    return (x0 + _edge_t(floor, rect, "w"), y0 + _edge_t(floor, rect, "s"),
            x1 - _edge_t(floor, rect, "e"), y1 - _edge_t(floor, rect, "n"))


def _rect_minus(r, hole):
    """Axis-aligned rect minus a hole rect -> list of rects."""
    x0, y0, x1, y1 = r
    hx0, hy0, hx1, hy1 = hole
    if hx1 <= x0 or hx0 >= x1 or hy1 <= y0 or hy0 >= y1:
        return [r]
    out = []
    if hy0 > y0:
        out.append((x0, y0, x1, hy0))
    if hy1 < y1:
        out.append((x0, hy1, x1, y1))
    yy0, yy1 = max(y0, hy0), min(y1, hy1)
    if hx0 > x0:
        out.append((x0, yy0, hx0, yy1))
    if hx1 < x1:
        out.append((hx1, yy0, x1, yy1))
    return [q for q in out if q[2] - q[0] > 1e-4 and q[3] - q[1] > 1e-4]


def _hquad(g, x0, y0, x1, y1, z, mat, up=True):
    a, b, c, d = (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z)
    if up:
        g.quad(a, b, c, d, mat)
    else:
        g.quad(a, d, c, b, mat)


def _wall_face(g, ax, plane, u0, u1, z0, z1, normal_sign, mat):
    """Vertical rectangle on a wall plane. ax 'x': the wall runs along x, the plane is y = plane, facing +-y."""
    if u1 - u0 < 1e-5 or z1 - z0 < 1e-5:
        return
    if ax == "x":
        a, b, c, d = (u0, plane, z0), (u1, plane, z0), (u1, plane, z1), (u0, plane, z1)
        if normal_sign > 0:      # facing +y
            g.quad(b, a, d, c, mat)
        else:
            g.quad(a, b, c, d, mat)
    else:
        a, b, c, d = (plane, u0, z0), (plane, u1, z0), (plane, u1, z1), (plane, u0, z1)
        if normal_sign > 0:      # facing +x
            g.quad(a, b, c, d, mat)
        else:
            g.quad(b, a, d, c, mat)


def _subtract(spans, cuts):
    out = []
    for (a, b) in spans:
        segs = [(a, b)]
        for (c0, c1) in cuts:
            nxt = []
            for (s0, s1) in segs:
                if c1 <= s0 or c0 >= s1:
                    nxt.append((s0, s1))
                    continue
                if c0 > s0:
                    nxt.append((s0, c0))
                if c1 < s1:
                    nxt.append((c1, s1))
            segs = nxt
        out.extend(segs)
    return [s for s in out if s[1] - s[0] > 1e-4]


class Builder:
    def __init__(self, L):
        self.L = L
        self.chunks = {}
        self.dyn = {}
        self.coll = []

    def chunk(self, name):
        if name not in self.chunks:
            self.chunks[name] = Geo(name)
        return self.chunks[name]

    def room_chunk(self, room):
        return self.chunk("arch_" + room)

    def C(self, x0, x1, y0, y1, z0, z1, rx=0.0):
        self.coll.append((min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), min(z0, z1), max(z0, z1), rx))

    # ------------------------------------------------------------------------------------------------ walls
    def walls(self):
        for (fl, ax, c, a, b, t, ops) in LY.WALLS:
            zf = LY.floor_z(fl)
            exterior = t >= LY.T_EXT - 1e-6
            top = zf + LY.STOREY
            ceil = LY.CEIL[fl]
            if fl == 1 and exterior:
                top = LY.PARAPET
            openings = [dict(u0=o[0], u1=o[1], z0=zf + o[2], z1=zf + o[3], kind=o[4], name=(o[5] if len(o) > 5 else None))
                        for o in ops]
            for side in (-1, 1):
                plane = c + side * t / 2
                # who is on this side: rooms whose boundary is this wall line, or outside
                if ax == "x":
                    rooms = [r for r in _rooms_on(fl) if abs((r[2][1] if side > 0 else r[2][3]) - c) < 1e-6]
                else:
                    rooms = [r for r in _rooms_on(fl) if abs((r[2][0] if side > 0 else r[2][2]) - c) < 1e-6]
                if rooms:
                    for r in rooms:
                        ir = inner_rect(r)
                        s0, s1 = (ir[0], ir[2]) if ax == "x" else (ir[1], ir[3])
                        s0, s1 = max(s0, a), min(s1, b)
                        if s1 <= s0:
                            continue
                        self._wall_side(self.room_chunk(r[0]), ax, plane, side, s0, s1, zf, ceil + 0.02, openings,
                                        r[5], interior=True)
                elif exterior:
                    s0, s1 = a - t / 2, b + t / 2
                    if (ax == "y"):
                        s0, s1 = a - t / 2, b + t / 2
                    mat = "wall_ext"
                    if fl == 1 and ((ax == "x" and c < 1e-6) or (ax == "y" and c > LY.W - 1e-6)):
                        mat = "cladding"
                    zlo = -0.03 if fl == 0 else zf
                    self._wall_side(self.chunk("arch_outside"), ax, plane, side, s0, s1, zlo, top, openings, mat,
                                    interior=False)
            # reveals (jambs, lintel undersides, sills) and collision
            self._reveals_and_coll(fl, ax, c, a, b, t, zf, top, ceil, openings, exterior)

    def _wall_side(self, g, ax, plane, side, s0, s1, z0, z1, openings, mat, interior):
        cuts = [(o["u0"], o["u1"]) for o in openings]
        for (u0, u1) in _subtract([(s0, s1)], cuts):
            _wall_face(g, ax, plane, u0, u1, z0, z1, side, mat)
        for o in openings:
            u0, u1 = max(o["u0"], s0), min(o["u1"], s1)
            if u1 <= u0:
                continue
            if o["z1"] < z1:
                _wall_face(g, ax, plane, u0, u1, o["z1"], z1, side, mat)
            if o["z0"] > z0 + 1e-4:
                _wall_face(g, ax, plane, u0, u1, z0, o["z0"], side, mat)

    def _inside_room(self, fl, ax, c, t, o):
        """Room a reveal belongs to: the door's room, else the room on the + side, else the - side."""
        if o["name"] and o["name"] in LY.DOORS:
            return LY.DOORS[o["name"]]["room"]
        um = (o["u0"] + o["u1"]) / 2
        for s in (1, -1):
            x, y = ((um, c + s * (t / 2 + 0.05)) if ax == "x" else (c + s * (t / 2 + 0.05), um))
            rn = LY.room_at(fl, x, y)
            if rn:
                return rn
        return None

    def _reveals_and_coll(self, fl, ax, c, a, b, t, zf, top, ceil, openings, exterior):
        lo_p, hi_p = c - t / 2, c + t / 2
        for o in openings:
            rn = self._inside_room(fl, ax, c, t, o)
            g = self.room_chunk(rn) if rn else self.chunk("arch_outside")
            mat = "reveal" if o["kind"] in ("window",) else ("door_frame" if o["kind"] in ("door", "main") else "wall_plaster")
            z0, z1 = o["z0"], o["z1"]
            # jambs (facing into the opening)
            for (u, sgn) in ((o["u0"], 1), (o["u1"], -1)):
                if ax == "x":
                    p = [(u, lo_p, z0), (u, hi_p, z0), (u, hi_p, z1), (u, lo_p, z1)]
                    if sgn > 0:
                        g.quad(p[0], p[1], p[2], p[3], mat)
                    else:
                        g.quad(p[1], p[0], p[3], p[2], mat)
                else:
                    p = [(lo_p, u, z0), (hi_p, u, z0), (hi_p, u, z1), (lo_p, u, z1)]
                    if sgn > 0:
                        g.quad(p[1], p[0], p[3], p[2], mat)
                    else:
                        g.quad(p[0], p[1], p[2], p[3], mat)
            # lintel underside (facing down) and sill top (facing up)
            if ax == "x":
                _hquad(g, o["u0"], lo_p, o["u1"], hi_p, z1, mat, up=False)
                if z0 > zf + 1e-3:
                    _hquad(g, o["u0"], lo_p, o["u1"], hi_p, z0, "sill" if o["kind"] == "window" else mat, up=True)
            else:
                _hquad(g, lo_p, o["u0"], hi_p, o["u1"], z1, mat, up=False)
                if z0 > zf + 1e-3:
                    _hquad(g, lo_p, o["u0"], hi_p, o["u1"], z0, "sill" if o["kind"] == "window" else mat, up=True)
            if o["kind"] == "window":
                self._window(fl, ax, c, t, o, g)
            elif o["kind"] == "shutter":
                self._shutter(ax, c, t, o)
            elif o["kind"] == "door":
                self._door(fl, ax, c, t, o, g)
            elif o["kind"] == "main":
                self._main_door(ax, c, t, o, g)
        # collision: solid spans full height, lintels, sills; windows get a glass blocker
        ztop = max(top, zf + LY.STOREY)
        cuts = [(o["u0"], o["u1"]) for o in openings]
        for (u0, u1) in _subtract([(a - t / 2, b + t / 2)], cuts):
            self._coll_span(ax, u0, u1, lo_p, hi_p, zf if fl == 0 else zf - 0.25, ztop)
        for o in openings:
            self._coll_span(ax, o["u0"], o["u1"], lo_p, hi_p, o["z1"], ztop)
            if o["kind"] in ("window", "shutter"):
                self._coll_span(ax, o["u0"], o["u1"], lo_p, hi_p, zf, max(o["z1"], zf + 2.2))

    def _coll_span(self, ax, u0, u1, p0, p1, z0, z1):
        if ax == "x":
            self.C(u0, u1, p0, p1, z0, z1)
        else:
            self.C(p0, p1, u0, u1, z0, z1)

    # ------------------------------------------------------------------------------------------------ windows
    def _window(self, fl, ax, c, t, o, g):
        gl = self.chunk(GLASS)
        u0, u1, z0, z1 = o["u0"], o["u1"], o["z0"], o["z1"]
        f = FRAME
        wdt = u1 - u0
        n = max(1, int(round(wdt / 1.8)))
        mull = [u0 + wdt * k / n for k in range(1, n)]
        depth = 0.07

        def fbox(a0, a1, b0, b1):
            # a: along the wall, b: height
            if ax == "x":
                g.box(((a0 + a1) / 2, c, (b0 + b1) / 2), (a1 - a0, depth, b1 - b0), "frame_alu")
            else:
                g.box((c, (a0 + a1) / 2, (b0 + b1) / 2), (depth, a1 - a0, b1 - b0), "frame_alu")
        fbox(u0, u1, z0, z0 + f)
        fbox(u0, u1, z1 - f, z1)
        fbox(u0, u0 + f, z0, z1)
        fbox(u1 - f, u1, z0, z1)
        for m in mull:
            fbox(m - f / 2, m + f / 2, z0, z1)
        # one glass pane through the frame's middle
        if ax == "x":
            gl.quad((u0 + f, c, z0 + f), (u1 - f, c, z0 + f), (u1 - f, c, z1 - f), (u0 + f, c, z1 - f), GLASS)
        else:
            gl.quad((c, u0 + f, z0 + f), (c, u1 - f, z0 + f), (c, u1 - f, z1 - f), (c, u0 + f, z1 - f), GLASS)

    def _shutter(self, ax, c, t, o):
        """The closed roller shutter of the garage (outside and inside faces)."""
        go = self.chunk("arch_outside")
        gi = self.room_chunk("garage")
        u0, u1, z0, z1 = o["u0"], o["u1"], o["z0"], o["z1"]
        _wall_face(go, ax, c - 0.04, u0, u1, z0, z1, -1, "shutter")
        _wall_face(gi, ax, c + 0.04, u0, u1, z0, z1, 1, "shutter")

    # ------------------------------------------------------------------------------------------------ doors
    def _door(self, fl, ax, c, t, o, g):
        """Interior door: casings on both faces and a leaf hinged at u0 (dynamic)."""
        name = o["name"]
        info = LY.DOORS[name]
        u0, u1, z0, z1 = o["u0"], o["u1"], o["z0"], o["z1"]
        cw, cd = 0.07, 0.015
        for side in (-1, 1):
            plane = c + side * (t / 2 + cd / 2)
            x_, y_ = ((u0 + u1) / 2, plane + side * 0.6) if ax == "x" else (plane + side * 0.6, (u0 + u1) / 2)
            rn = LY.room_at(fl, x_, y_) or info["room"]
            gg = self.room_chunk(rn)
            for (a0, a1, b0, b1) in ((u0 - cw, u0, z0, z1 + cw), (u1, u1 + cw, z0, z1 + cw), (u0 - cw, u1 + cw, z1, z1 + cw)):
                if ax == "x":
                    gg.box(((a0 + a1) / 2, plane, (b0 + b1) / 2), (a1 - a0, cd, b1 - b0), "door_frame")
                else:
                    gg.box((plane, (a0 + a1) / 2, (b0 + b1) / 2), (cd, a1 - a0, b1 - b0), "door_frame")
        lw, lt, lh = (u1 - u0) - 0.02, 0.04, (z1 - z0) - 0.015
        leaf = Geo(name)
        if ax == "x":
            leaf.box((lw / 2, 0, lh / 2), (lw, lt, lh), "door_white")
            for s in (-1, 1):
                leaf.box((lw - 0.09, s * 0.035, 1.02), (0.13, 0.02, 0.02), "metal_brushed")
            pivot = (u0 + 0.01, c, z0)
            ldir = (1.0, 0.0)
        else:
            leaf.box((0, lw / 2, lh / 2), (lt, lw, lh), "door_white")
            for s in (-1, 1):
                leaf.box((s * 0.035, lw - 0.09, 1.02), (0.02, 0.13, 0.02), "metal_brushed")
            pivot = (c, u0 + 0.01, z0)
            ldir = (0.0, 1.0)
        self.dyn[name] = {"geo": leaf, "pivot": pivot, "door": name, "leaf_dir": ldir, "into": list(info["into"]),
                          "floor": fl, "room": info["room"]}

    def _main_door(self, ax, c, t, o, g):
        """Front door: walnut pivot leaf, three planks nailed across the inside, two padlocks, a code keypad."""
        u0, u1, z0, z1 = o["u0"], o["u1"], o["z0"], o["z1"]
        inside = c + t / 2           # the hall side (+y)
        cw, cd = 0.09, 0.02
        for (a0, a1, b0, b1) in ((u0 - cw, u0, z0, z1 + cw), (u1, u1 + cw, z0, z1 + cw), (u0 - cw, u1 + cw, z1, z1 + cw)):
            g.box(((a0 + a1) / 2, inside + cd / 2, (b0 + b1) / 2), (a1 - a0, cd, b1 - b0), "door_frame")
            self.chunk("arch_outside").box(((a0 + a1) / 2, c - t / 2 - cd / 2, (b0 + b1) / 2), (a1 - a0, cd, b1 - b0), "frame_alu")
        lw, lt, lh = (u1 - u0) - 0.03, 0.07, (z1 - z0) - 0.02
        leaf = Geo("door_main")
        leaf.box((lw / 2, 0, lh / 2), (lw, lt, lh), "door_wood")
        leaf.box((lw - 0.12, -0.06, lh * 0.45), (0.035, 0.03, 0.9), "metal_black")     # outside pull bar
        leaf.box((lw - 0.1, 0.05, 1.05), (0.15, 0.025, 0.025), "metal_black")         # inside lever
        self.dyn["door_main"] = {"geo": leaf, "pivot": (u0 + 0.015, c, z0), "door": "door_main", "leaf_dir": (1.0, 0.0),
                                 "into": [0, 1], "floor": 0, "room": "hall"}
        # planks across the inside face (each its own part so it can be pried off)
        for k, (z, ang) in enumerate(((0.62, -4.0), (1.24, 3.0), (1.86, -2.5))):
            pl = Geo("plank_%d" % k)
            R = np.array([[math.cos(math.radians(ang)), 0, -math.sin(math.radians(ang))], [0, 1, 0],
                          [math.sin(math.radians(ang)), 0, math.cos(math.radians(ang))]])
            pb = Geo("p")
            pb.box((0, 0, 0), (1.72, 0.032, 0.15), "wood_plank")
            for sx in (-0.78, 0.78):
                for sz in (-0.035, 0.035):
                    pb.box((sx, -0.02, sz), (0.012, 0.01, 0.012), "metal_black")
            pl.merge(pb, R=R)
            self.dyn["plank_%d" % k] = {"geo": pl, "pivot": ((u0 + u1) / 2, inside + 0.045, z), "plank": k}
        # hasps on the latch side and the two padlocks hanging from them
        for name, z in (("padlock_gold", 0.93), ("padlock_silver", 1.55)):
            g.box((u1 - 0.05, inside + 0.012, z + 0.06), (0.16, 0.012, 0.05), "steel")
            self.dyn[name] = {"geo": None, "pivot": (u1 - 0.02, inside + 0.05, z - 0.07), "padlock": name}
        # keypad on the wall beside the door
        kx, kz = u1 + 0.32, 1.35
        g.box((kx, inside + 0.012, kz), (0.1, 0.024, 0.15), "metal_black")
        g.box((kx, inside + 0.0245, kz - 0.015), (0.075, 0.002, 0.09), "keypad_face")
        led = Geo("keypad_led")
        a = led.vert((-0.03, 0.0, 0.0))
        b = led.vert((0.03, 0.0, 0.0))
        cc = led.vert((0.03, 0.0, 0.012))
        d = led.vert((-0.03, 0.0, 0.012))
        led.face([b, a, d, cc], "keypad_led", uvs=[(1, 0), (0, 0), (0, 1), (1, 1)])
        self.dyn["keypad_led"] = {"geo": led, "pivot": (kx, inside + 0.0262, kz + 0.042), "keypad": True}
        self.keypad = (kx, inside + 0.03, kz)

    # ------------------------------------------------------------------------------------------------ floors, ceilings, stair
    def floors(self):
        void = (LY.STAIR["x0"], LY.STAIR["y0"], LY.STAIR["x1"], LY.STAIR["y1"])
        for r in LY.ROOMS:
            name, fl = r[0], r[1]
            ir = inner_rect(r)
            g = self.room_chunk(name)
            zf = LY.floor_z(fl)
            zc = LY.CEIL[fl]
            parts = [ir]
            if name == "corridor":
                parts = _rect_minus(ir, void)
            for (x0, y0, x1, y1) in parts:
                _hquad(g, x0, y0, x1, y1, zf, r[4], up=True)
            # GF: no floor under the stair (the stair mass covers it)
            cparts = [ir]
            if name in ("hall",):
                cparts = _rect_minus(ir, void)
            for (x0, y0, x1, y1) in cparts:
                _hquad(g, x0, y0, x1, y1, zc, r[6], up=False)
        # thresholds under door / arch openings (floor through the wall thickness)
        for (fl, ax, c, a, b, t, ops) in LY.WALLS:
            for o in ops:
                if o[4] not in ("door", "arch", "main"):
                    continue
                name = o[5] if len(o) > 5 else None
                rn = LY.DOORS[name]["room"] if name in LY.DOORS else self._inside_room(fl, ax, c, t, dict(u0=o[0], u1=o[1], name=name))
                g = self.room_chunk(rn)
                zf = LY.floor_z(fl)
                if ax == "x":
                    _hquad(g, o[0], c - t / 2, o[1], c + t / 2, zf, "threshold" if o[4] != "arch" else LY.room(rn)[4], up=True)
                else:
                    _hquad(g, c - t / 2, o[0], c + t / 2, o[1], zf, "threshold" if o[4] != "arch" else LY.room(rn)[4], up=True)
        # slab edges around the stair void (seen from the stair), in the hall
        s = LY.STAIR
        g = self.room_chunk("hall")
        c0, c1 = LY.CEIL[0], LY.H1
        _wall_face(g, "y", s["x1"], s["y0"], s["y1"], c0, c1, -1, "wall_plaster")
        _wall_face(g, "x", s["y0"], s["x0"], s["x1"], c0, c1, 1, "wall_plaster")
        # first floor slab colliders (around the void) and the big ground
        for r in LY.ROOMS:
            if r[1] != 1:
                continue
            for (x0, y0, x1, y1) in (_rect_minus(r[2], void) if r[0] == "corridor" else [r[2]]):
                self.C(x0, x1, y0, y1, LY.CEIL[0], LY.H1)
        p = LY.PLOT
        self.C(p[0] - 5, p[2] + 5, p[1] - 5, p[3] + 5, -1.0, 0.0)

    def stair(self):
        s = LY.STAIR
        g = self.room_chunk("hall")
        n = s["risers"]
        run = (s["y1"] - s["y0"]) / n
        rise = LY.H1 / n
        x0, x1 = s["x0"], s["x1"]
        for i in range(n):
            ya, yb = s["y0"] + i * run, s["y0"] + (i + 1) * run
            zt = (i + 1) * rise
            zb = i * rise
            _hquad(g, x0, ya, x1, yb, zt, "stair_oak", up=True)                    # tread
            _wall_face(g, "x", ya, x0, x1, zb, zt, -1, "stair_riser")              # riser (faces south)
            _wall_face(g, "y", x1, ya, yb, 0.0, zt, 1, "stair_side")               # the stair's side (faces east)
            # nosing strip
            g.box(((x0 + x1) / 2, ya + 0.012, zt - 0.012), (x1 - x0, 0.024, 0.024), "stair_oak")
        # closed under the top end (faces north, toward the utility door)
        _wall_face(g, "x", s["y1"], x0, x1, 0.0, LY.CEIL[0], 1, "stair_side")
        # glass balustrade along the open side + steel handrail, and the railings round the void upstairs
        gl = self.chunk(GLASS)
        y0, y1 = s["y0"], s["y1"]
        gl.quad((x1 + 0.01, y0, 0.05), (x1 + 0.01, y1, LY.H1 + 0.05), (x1 + 0.01, y1, LY.H1 + 0.95), (x1 + 0.01, y0, 0.95), GLASS)
        L_ = math.hypot(y1 - y0, LY.H1)
        ang = math.degrees(math.atan2(LY.H1, y1 - y0))
        rail = Geo("rail")
        rail.box((0, 0, 0), (0.05, L_, 0.04), "metal_brushed")
        Rr = np.array([[1, 0, 0], [0, math.cos(math.radians(ang)), -math.sin(math.radians(ang))],
                       [0, math.sin(math.radians(ang)), math.cos(math.radians(ang))]])
        g.merge(rail, R=Rr, T=(x1 + 0.01, (y0 + y1) / 2, LY.H1 / 2 + 0.97))
        gc = self.room_chunk("corridor")
        zf = LY.H1
        gl.quad((x1 + 0.01, y0, zf), (x1 + 0.01, y1, zf), (x1 + 0.01, y1, zf + 1.0), (x1 + 0.01, y0, zf + 1.0), GLASS)
        gl.quad((x0, y0 - 0.01, zf), (x1, y0 - 0.01, zf), (x1, y0 - 0.01, zf + 1.0), (x0, y0 - 0.01, zf + 1.0), GLASS)
        gc.box((x1 + 0.01, (y0 + y1) / 2, zf + 1.02), (0.05, y1 - y0, 0.04), "metal_brushed")
        gc.box(((x0 + x1) / 2, y0 - 0.01, zf + 1.02), (x1 - x0, 0.05, 0.04), "metal_brushed")
        for y in np.linspace(y0, y1, 5):
            gc.box((x1 + 0.01, y, zf + 0.5), (0.04, 0.04, 1.0), "metal_brushed")
        # colliders: the ramp, its open side (also the railing upstairs), the closed end, the void's south rail
        ramp_len = L_
        cy = (y0 + y1) / 2
        self.C(x0, x1, cy - ramp_len / 2, cy + ramp_len / 2, LY.H1 / 2 - 0.08, LY.H1 / 2 + 0.0, rx=ang)
        self.C(x1 - 0.02, x1 + 0.04, y0, y1, 0.0, LY.H1 + 1.1)
        self.C(x0, x1, y1 - 0.06, y1, 0.0, LY.CEIL[0] - 0.05)
        self.C(x0, x1, y0 - 0.05, y0 + 0.01, LY.H1, LY.H1 + 1.1)

    # ------------------------------------------------------------------------------------------------ outside
    def outside(self):
        g = self.chunk("arch_outside")
        W, D = LY.W, LY.D
        t = LY.T_EXT
        # roof top inside the parapet, parapet cap and inner faces
        _hquad(g, t / 2, t / 2, W - t / 2, D - t / 2, LY.ROOF_TOP, "roof", up=True)
        _hquad(g, -t / 2, -t / 2, W + t / 2, D + t / 2, LY.PARAPET, "roof", up=True)
        # canopy over the front door
        g.box((7.0, -0.7, 2.85), (2.8, 1.4, 0.2), "concrete")
        # ground: lawn around, the drive to the garage, the path to the door
        p = LY.PLOT
        lawn = _rect_minus((p[0], p[1], p[2], p[3]), (-t / 2, -t / 2, W + t / 2, D + t / 2))
        for r in lawn:
            for q in _rect_minus(r, tuple(LY.DRIVE)):
                for q2 in _rect_minus(q, tuple(LY.PATH)):
                    _hquad(g, q2[0], q2[1], q2[2], q2[3], -0.03, "grass", up=True)
        d = LY.DRIVE
        _hquad(g, d[0], d[1], d[2], d[3] - t / 2, -0.02, "paving", up=True)
        pa = LY.PATH
        _hquad(g, pa[0], pa[1], pa[2], pa[3] - t / 2, -0.02, "paving", up=True)
        # compound wall with the gate
        h = 2.1
        wt = 0.22
        segs = [((p[0], p[1]), (p[2], p[1])), ((p[2], p[1]), (p[2], p[3])), ((p[2], p[3]), (p[0], p[3])), ((p[0], p[3]), (p[0], p[1]))]
        for (a, b) in segs:
            if abs(a[1] - b[1]) < 1e-6:          # along x
                x0, x1 = min(a[0], b[0]), max(a[0], b[0])
                spans = [(x0, x1)]
                if abs(a[1] - p[1]) < 1e-6:
                    spans = _subtract(spans, [(d[0] - 0.2, d[2] + 0.2), (pa[0] - 0.3, pa[2] + 0.3)])
                for (u0, u1) in spans:
                    g.box(((u0 + u1) / 2, a[1], h / 2), (u1 - u0, wt, h), "wall_ext")
                    self.C(u0, u1, a[1] - wt / 2, a[1] + wt / 2, 0.0, h)
            else:
                y0, y1 = min(a[1], b[1]), max(a[1], b[1])
                g.box((a[0], (y0 + y1) / 2, h / 2), (wt, y1 - y0, h), "wall_ext")
                self.C(a[0] - wt / 2, a[0] + wt / 2, y0, y1, 0.0, h)
        # the gates (closed, dark steel slats)
        for (u0, u1) in ((d[0] - 0.2, d[2] + 0.2), (pa[0] - 0.3, pa[2] + 0.3)):
            for k in range(int((u1 - u0) / 0.12)):
                x = u0 + 0.06 + k * 0.12
                g.box((x, p[1], 0.95), (0.06, 0.04, 1.8), "metal_black")
            g.box(((u0 + u1) / 2, p[1], 1.85), (u1 - u0, 0.06, 0.06), "metal_black")
            self.C(u0, u1, p[1] - 0.05, p[1] + 0.05, 0.0, 2.0)
        # street light beyond the gate and two lamp posts by the door
        g.cyl((9.0, -9.5, 0.0), (9.0, -9.5, 5.4), 0.07, "metal_black", seg=10)
        g.box((9.0, -9.2, 5.45), (0.25, 0.7, 0.12), "metal_black")
        g.box((9.0, -9.0, 5.38), (0.18, 0.3, 0.02), "bulb_glow")
        for x in (6.0, 8.0):
            g.box((x, -0.25, 2.6), (0.12, 0.12, 0.25), "metal_black")
            g.box((x, -0.25, 2.47), (0.09, 0.09, 0.02), "bulb_glow")
        # a low hedge along the front of the house (between the drive and the path, and east of the path)
        for (x0, x1) in ((4.9, 6.1), (8.0, 9.6)):
            g.box(((x0 + x1) / 2, -0.75, 0.35), (x1 - x0, 0.6, 0.7), "hedge")
        g.box((13.5, -0.75, 0.35), (8.6, 0.6, 0.7), "hedge")

    def build(self):
        self.keypad = None
        self.walls()
        self.floors()
        self.stair()
        self.outside()
        return self.chunks, self.dyn, self.coll


def build(L=None):
    b = Builder(L or LY.build())
    chunks, dyn, coll = b.build()
    return chunks, dyn, coll, {"keypad": b.keypad}


if __name__ == "__main__":
    import sys
    chunks, dyn, coll, extra = build()
    tot = 0
    for k, g in sorted(chunks.items()):
        tot += len(g.F)
        print("%-16s %5d faces, materials %s" % (k, len(g.F), sorted(set(g.M))))
    print("total faces", tot, "dynamic", len(dyn), sorted(dyn), "colliders", len(coll), "keypad", extra["keypad"])
