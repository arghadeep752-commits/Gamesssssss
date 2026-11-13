"""Every piece of furniture and clutter in the school, modelled from code at real sizes (numpy only).

Each builder returns (static Geo, {name: dynamic Geo}) in local coordinates: origin on the floor at the piece's
centre, its front facing -Y, up +Z. Dynamic parts (almirah doors, fan blades) are separate so the game can move them.
Material names map to photographed textures in the game (see geo.TEX_M and game/scripts/mats.gd).
"""
import math

import numpy as np

from geo import Geo, rot_x, rot_y, rot_z


def _rng(seed):
    return np.random.default_rng(seed)


# ------------------------------------------------------------------------------------------------ classroom
def desk_bench(seed=0):
    """Dual-seat desk with its bench (Indian classroom bench-desk): wooden top, book shelf, iron frame."""
    g = Geo("desk_bench")
    r = _rng(seed)
    W = 1.10
    # desk top: slightly sloped towards the student, a flat strip at the far end with a pen groove
    top = Geo()
    top.box((0, 0.03, 0), (W, 0.36, 0.028), "wood")
    top.transform(R=rot_x(-7), T=(0, 0, 0.715))
    g.merge(top)
    g.box((0, -0.18, 0.742), (W, 0.07, 0.028), "wood")
    g.box((0, -0.18, 0.758), (W - 0.1, 0.012, 0.006), "wood_dark")
    g.box((0, 0.0, 0.55), (W - 0.06, 0.34, 0.018), "wood")                 # book shelf
    g.box((0, -0.19, 0.63), (W - 0.06, 0.012, 0.16), "wood")               # front panel
    # bench seat and back rest
    g.box((0, 0.47, 0.425), (W, 0.27, 0.03), "wood")
    g.box((0, 0.63, 0.66), (W, 0.022, 0.13), "wood")
    # iron side frames
    for sx in (-1, 1):
        x = sx * (W / 2 - 0.05)
        for (y0, y1, z0, z1) in ((-0.17, -0.17, 0.0, 0.73), (0.17, 0.17, 0.0, 0.71), (0.35, 0.35, 0.0, 0.42), (0.6, 0.6, 0.0, 0.75)):
            g.box((x, y0, (z0 + z1) / 2), (0.028, 0.028, z1 - z0), "metal_green")
        g.box((x, 0.21, 0.03), (0.026, 0.86, 0.026), "metal_green")         # floor runner
        g.box((x, 0.0, 0.5), (0.022, 0.36, 0.022), "metal_green")
        g.box((x, 0.47, 0.4), (0.022, 0.28, 0.022), "metal_green")
    return g, {}


def blackboard(text_seed=0):
    g = Geo("blackboard")
    W, Hh = 2.4, 1.15
    zc = 0.2 + 0.78 + Hh / 2
    g.box((0, 0.0, zc), (W, 0.03, Hh), "chalkboard")
    for (c, s) in (((0, -0.012, zc + Hh / 2 + 0.025), (W + 0.1, 0.05, 0.05)), ((0, -0.012, zc - Hh / 2 - 0.025), (W + 0.1, 0.05, 0.05)),
                   ((-W / 2 - 0.025, -0.012, zc), (0.05, 0.05, Hh)), ((W / 2 + 0.025, -0.012, zc), (0.05, 0.05, Hh))):
        g.box(c, s, "wood_dark")
    g.box((0, -0.06, zc - Hh / 2 - 0.06), (W, 0.09, 0.022), "wood_dark")   # chalk ledge
    r = _rng(text_seed + 3)
    for k in range(4):
        x = r.uniform(-1.0, 1.0)
        g.cyl((x, -0.07, zc - Hh / 2 - 0.042), (x + r.uniform(0.04, 0.07), -0.07 + r.uniform(-0.01, 0.01), zc - Hh / 2 - 0.042),
              0.0055, "chalk", seg=8)
    g.box((0.7, -0.07, zc - Hh / 2 - 0.03), (0.13, 0.05, 0.035), "wood")      # duster
    g.box((0.7, -0.07, zc - Hh / 2 - 0.052), (0.13, 0.05, 0.01), "felt")
    return g, {}


def dais():
    g = Geo("dais")
    g.box((0, 0, 0.1), (3.0, 2.0, 0.2), "wood_old", mats=["plaster", "plaster", "plaster", "plaster", "wood_old", "wood_old"])
    return g, {}


def teacher_table():
    """Wooden table with a modesty panel on the students' side (you can hide under it) and a drawer."""
    g = Geo("teacher_table")
    W, D, H = 1.2, 0.72, 0.76
    g.box((0, 0, H - 0.02), (W, D, 0.04), "wood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.04), sy * (D / 2 - 0.04), (H - 0.04) / 2), (0.05, 0.05, H - 0.04), "wood_dark")
    g.box((0, -D / 2 + 0.03, 0.47), (W - 0.1, 0.018, 0.5), "wood")          # front panel
    g.box((-W / 2 + 0.04, 0, H - 0.1), (0.018, D - 0.1, 0.12), "wood")
    g.box((W / 2 - 0.04, 0, H - 0.1), (0.018, D - 0.1, 0.12), "wood")
    g.box((0.25, D / 2 - 0.03, H - 0.1), (0.42, 0.02, 0.1), "wood")          # drawer front (teacher side)
    g.cyl((0.25, D / 2 - 0.02, H - 0.1), (0.25, D / 2 + 0.01, H - 0.1), 0.011, "brass", seg=10)
    return g, {}


def chair(back_h=0.95, seed=0, arms=False):
    g = Geo("chair")
    S = 0.44
    g.box((0, 0, 0.44), (S, S, 0.03), "wood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            h = back_h if sy > 0 else 0.43
            g.box((sx * (S / 2 - 0.025), sy * (S / 2 - 0.025), h / 2), (0.035, 0.035, h), "wood_dark")
        g.box((sx * (S / 2 - 0.025), 0, 0.15), (0.025, S - 0.05, 0.025), "wood_dark")
    for z in (0.62, 0.8):
        g.box((0, S / 2 - 0.025, z), (S - 0.05, 0.02, 0.07), "wood")
    g.box((0, S / 2 - 0.02, back_h - 0.04), (S + 0.02, 0.035, 0.06), "wood_dark")
    if arms:
        for sx in (-1, 1):
            g.box((sx * (S / 2 + 0.01), 0.02, 0.66), (0.05, S, 0.03), "wood_dark")
            g.box((sx * (S / 2 + 0.01), -S / 2 + 0.04, 0.55), (0.03, 0.03, 0.22), "wood_dark")
    return g, {}


def almirah(hide=True):
    """Steel almirah (Godrej-style cupboard). Doors are separate so they open; empty inside when it is a hiding place."""
    g = Geo("almirah")
    W, D, H = 0.92, 0.5, 1.86
    t = 0.012
    g.box((0, 0, 0.05), (W - 0.02, D - 0.02, 0.1), "metal_grey")              # plinth
    g.box((-W / 2 + t / 2, 0, H / 2), (t, D, H), "metal_green")
    g.box((W / 2 - t / 2, 0, H / 2), (t, D, H), "metal_green")
    g.box((0, D / 2 - t / 2, H / 2), (W, t, H), "metal_green")
    g.box((0, 0, H - t / 2), (W, D, t), "metal_green")
    g.box((0, 0, 0.1 + t / 2), (W, D, t), "metal_green")
    g.box((0, -D / 2 + 0.01, H - 0.02), (W, 0.03, 0.04), "metal_green")
    g.box((0, 0.02, 1.52), (W - 2 * t, D - 0.05, t), "metal_green")           # top shelf (above head height)
    if not hide:
        for z in (0.55, 1.05):
            g.box((0, 0.02, z), (W - 2 * t, D - 0.05, t), "metal_green")
    doors = {}
    for side, sx in (("L", -1), ("R", 1)):
        d = Geo("almirah_door_" + side)
        dw = W / 2 - 0.006
        # local: hinge at x = 0, the leaf extends towards +x (left door) / -x (right door)
        cx = -sx * dw / 2
        d.box((cx, 0, 0.12 + (H - 0.16) / 2), (dw, 0.016, H - 0.16), "metal_green")
        d.box((cx, -0.009, 1.0), (dw - 0.08, 0.004, 1.2), "metal_green")      # pressed panel
        hx = -sx * (dw - 0.05)
        d.box((hx, -0.03, 0.98), (0.018, 0.022, 0.22), "steel")                 # handle
        d.box((hx, -0.014, 1.05), (0.014, 0.03, 0.016), "steel")
        d.box((hx, -0.014, 0.91), (0.014, 0.03, 0.016), "steel")
        if side == "R":
            d.cyl((hx - 0.03 * -sx, -0.012, 1.12), (hx - 0.03 * -sx, -0.022, 1.12), 0.012, "brass", seg=10)   # lock
        doors["door_" + side] = (d, (sx * W / 2, -D / 2 - 0.008, 0.0))
    return g, doors


def fan():
    """Ceiling fan: rod, canopy, motor, three blades (the motor + blades turn in the game)."""
    g = Geo("fan")
    g.lathe([(0.0, 0.0), (0.075, 0.0), (0.07, -0.05), (0.02, -0.065), (0.0, -0.065)], (0, 0, 0), "metal_grey", seg=16)
    g.cyl((0, 0, -0.06), (0, 0, -0.5), 0.012, "metal_grey", seg=10)
    rot = Geo("fan_rotor")
    rot.lathe([(0.0, 0.0), (0.03, 0.0), (0.11, -0.03), (0.12, -0.09), (0.09, -0.13), (0.03, -0.14), (0.0, -0.14)], (0, 0, 0),
              "metal_grey", seg=20)
    for k in range(3):
        a = k * 120.0
        b = Geo()
        b.box((0.42, 0, -0.08), (0.62, 0.11, 0.006), "aluminium")
        b.box((0.14, 0, -0.075), (0.12, 0.03, 0.012), "metal_grey")
        b.transform(R=rot_x(9))
        b.transform(R=rot_z(a))
        rot.merge(b)
    return g, {"rotor": (rot, (0, 0, -0.5))}


def tube_light(dead=False):
    g = Geo("tube_light")
    g.box((0, 0, -0.025), (1.25, 0.065, 0.045), "metal_white")
    g.cyl((-0.6, 0, -0.06), (0.6, 0, -0.06), 0.0135, "tube_dead" if dead else "tube_glow", seg=10, caps=False)
    for sx in (-1, 1):
        g.box((sx * 0.61, 0, -0.055), (0.03, 0.04, 0.05), "metal_white")
    return g, {}


def bulb():
    g = Geo("bulb")
    g.cyl((0, 0, 0), (0, 0, -0.35), 0.004, "cable", seg=6)
    g.lathe([(0.0, -0.35), (0.018, -0.35), (0.018, -0.39), (0.0, -0.39)], (0, 0, 0), "metal_grey", seg=12)
    g.lathe([(0.014, -0.39), (0.03, -0.41), (0.032, -0.44), (0.02, -0.47), (0.0, -0.475)], (0, 0, 0), "bulb_glow", seg=14)
    return g, {}


# ------------------------------------------------------------------------------------------------ office
def principal_desk(seed=1):
    g = Geo("principal_desk")
    r = _rng(seed)
    W, D, H = 1.5, 0.82, 0.78
    g.box((0, 0, H - 0.025), (W, D, 0.04), "wood_dark")
    g.box((0, 0, H + 0.002), (W - 0.06, D - 0.06, 0.008), "glass")
    for sx in (-1, 1):
        g.box((sx * (W / 2 - 0.22), 0, (H - 0.05) / 2), (0.42, D - 0.04, H - 0.05), "wood")
        for k in range(3):
            z = 0.12 + k * 0.21
            g.box((sx * (W / 2 - 0.22), D / 2 - 0.012, z + 0.09), (0.38, 0.012, 0.18), "wood_dark")
            g.cyl((sx * (W / 2 - 0.22), D / 2 - 0.005, z + 0.12), (sx * (W / 2 - 0.22), D / 2 + 0.02, z + 0.12), 0.01, "brass", seg=8)
    g.box((0, -D / 2 + 0.02, 0.45), (W - 0.86, 0.02, 0.5), "wood")
    # things on the desk: the bell, a stack of registers, the cane, a pen stand
    g.lathe([(0.0, 0.0), (0.045, 0.0), (0.045, 0.012), (0.038, 0.04), (0.02, 0.055), (0.006, 0.06), (0.006, 0.075), (0.0, 0.075)],
            (0.45, -0.05, H + 0.006), "steel", seg=16)
    for k in range(5):
        g.box((-0.45 + r.uniform(-0.01, 0.01), 0.1 + r.uniform(-0.01, 0.01), H + 0.012 + k * 0.03), (0.24, 0.32, 0.028),
              ["register_red", "register_blue", "paper", "register_red", "cardboard"][k], R=rot_z(r.uniform(-6, 6)))
    g.cyl((-0.1, -0.18, H + 0.02), (0.55, 0.05, H + 0.02), 0.007, "cane", seg=8)
    g.lathe([(0.0, 0.0), (0.035, 0.0), (0.035, 0.1), (0.032, 0.1), (0.032, 0.006), (0.0, 0.006)], (0.15, 0.2, H + 0.006), "brass", seg=14)
    return g, {}


def file_rack(seed=2):
    g = Geo("file_rack")
    r = _rng(seed)
    W, D, H = 0.9, 0.4, 1.85
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.015), sy * (D / 2 - 0.015), H / 2), (0.03, 0.03, H), "metal_grey")
    for k in range(5):
        z = 0.08 + k * 0.42
        g.box((0, 0, z), (W, D, 0.012), "metal_grey")
        x = -W / 2 + 0.05
        while x < W / 2 - 0.08 and k < 4:
            th = r.uniform(0.04, 0.09)
            hh = r.uniform(0.25, 0.33)
            m = ["cardboard", "register_red", "file_cloth", "paper"][int(r.integers(0, 4))]
            g.box((x + th / 2, 0, z + 0.006 + hh / 2), (th, D - 0.06, hh), m, R=rot_y(r.uniform(-4, 4)))
            x += th + 0.004
    return g, {}


def wall_clock():
    g = Geo("wall_clock")
    R = rot_x(90)
    g.lathe([(0.0, 0.0), (0.16, 0.0), (0.165, 0.02), (0.16, 0.04), (0.0, 0.04)], (0, 0.0, 2.45), "wood_dark", seg=28, axis=R)
    g.lathe([(0.0, 0.0), (0.145, 0.0), (0.0, 0.0001)], (0, -0.0405, 2.45), "clock_face", seg=28, axis=R)
    g.box((0.0, -0.045, 2.45 + 0.05), (0.008, 0.003, 0.1), "metal_black")
    g.box((0.035, -0.046, 2.45 - 0.01), (0.075, 0.003, 0.007), "metal_black", R=rot_y(-25))
    return g, {}


def long_table():
    g = Geo("long_table")
    W, D, H = 2.4, 0.9, 0.76
    g.box((0, 0, H - 0.02), (W, D, 0.04), "wood", mats=["wood", "wood", "wood", "wood", "wood", "felt"])
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.05), sy * (D / 2 - 0.05), (H - 0.04) / 2), (0.06, 0.06, H - 0.04), "wood_dark")
    g.box((0, 0, 0.15), (W - 0.12, 0.04, 0.04), "wood_dark")
    for k in range(3):
        g.box((-0.6 + k * 0.6, 0.1, H + 0.01), (0.24, 0.32, 0.02), "register_blue" if k % 2 else "register_red")
        g.lathe([(0.0, 0.0), (0.03, 0.0), (0.036, 0.075), (0.033, 0.075), (0.027, 0.004), (0.0, 0.004)], (-0.3 + k * 0.6, -0.2, H),
                "steel", seg=14)
    return g, {}


def lockers():
    g = Geo("lockers")
    W, D, H = 1.2, 0.45, 1.82
    g.box((0, 0, H / 2), (W, D, H), "metal_grey")
    for i in range(3):
        for j in range(4):
            x = -W / 2 + 0.2 + i * 0.4
            z = 0.2 + j * 0.43
            g.box((x, -D / 2 - 0.004, z + 0.19), (0.37, 0.008, 0.4), "metal_grey")
            g.box((x + 0.12, -D / 2 - 0.012, z + 0.19), (0.02, 0.012, 0.06), "steel")
            g.box((x - 0.05, -D / 2 - 0.009, z + 0.33), (0.08, 0.004, 0.04), "paper")
    return g, {}


def matka_stand():
    g = Geo("matka_stand")
    for k in range(3):
        a = math.radians(k * 120 + 30)
        g.cyl((math.cos(a) * 0.18, math.sin(a) * 0.18, 0.0), (math.cos(a) * 0.12, math.sin(a) * 0.12, 0.62), 0.01, "rust", seg=6)
    g.lathe([(0.12, 0.6), (0.17, 0.6), (0.17, 0.63), (0.12, 0.63)], (0, 0, 0), "rust", seg=18)
    prof = [(0.06, 0.0), (0.14, 0.03), (0.2, 0.12), (0.215, 0.2), (0.19, 0.3), (0.12, 0.37), (0.075, 0.4), (0.07, 0.43), (0.09, 0.45),
            (0.085, 0.46), (0.06, 0.45)]
    g.lathe(prof, (0, 0, 0.56), "clay", seg=28)
    g.lathe([(0.1, 0.0), (0.1, 0.008), (0.06, 0.02), (0.0, 0.03)], (0, 0, 1.02), "clay", seg=18)
    g.lathe([(0.0, 0.0), (0.03, 0.0), (0.036, 0.09), (0.033, 0.09), (0.027, 0.004), (0.0, 0.004)], (0.0, 0.0, 1.05), "steel", seg=14)
    return g, {}


def bench(length=1.5):
    g = Geo("bench")
    g.box((0, 0, 0.44), (length, 0.36, 0.04), "wood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (length / 2 - 0.07), sy * 0.13, 0.21), (0.05, 0.05, 0.42), "wood_dark")
        g.box((sx * (length / 2 - 0.07), 0, 0.12), (0.04, 0.26, 0.04), "wood_dark")
    g.box((0, 0, 0.12), (length - 0.14, 0.04, 0.04), "wood_dark")
    return g, {}


def notice_board(seed=4):
    g = Geo("notice_board")
    r = _rng(seed)
    g.box((0, 0.0, 1.6), (1.2, 0.025, 0.9), "felt_green")
    for (c, s) in (((0, -0.01, 2.07), (1.26, 0.04, 0.04)), ((0, -0.01, 1.13), (1.26, 0.04, 0.04)),
                   ((-0.62, -0.01, 1.6), (0.04, 0.04, 0.9)), ((0.62, -0.01, 1.6), (0.04, 0.04, 0.9))):
        g.box(c, s, "wood_dark")
    for k in range(6):
        x = r.uniform(-0.45, 0.45)
        z = r.uniform(1.3, 1.9)
        g.box((x, -0.016, z), (r.uniform(0.18, 0.28), 0.002, r.uniform(0.22, 0.32)), "paper", R=rot_y(r.uniform(-8, 8)))
    return g, {}


def school_bell():
    """The brass gong the peon struck between periods, hanging from its bracket."""
    g = Geo("school_bell")
    g.box((0, 0.1, 2.3), (0.06, 0.25, 0.06), "rust")
    g.cyl((0, -0.02, 2.3), (0, -0.02, 2.05), 0.004, "rust", seg=6)
    g.lathe([(0.0, 0.0), (0.18, 0.0), (0.19, 0.01), (0.18, 0.02), (0.0, 0.016)], (0, -0.02, 1.88), "brass", seg=28, axis=rot_x(90))
    return g, {}


def trophy_case(seed=5):
    g = Geo("trophy_case")
    r = _rng(seed)
    W, D, H = 1.1, 0.42, 1.7
    g.box((0, 0.19, H / 2), (W, 0.04, H), "wood_dark")
    for sx in (-1, 1):
        g.box((sx * (W / 2 - 0.02), 0, H / 2), (0.04, D, H), "wood_dark")
    g.box((0, 0, 0.06), (W, D, 0.12), "wood_dark")
    g.box((0, 0, H - 0.02), (W, D, 0.04), "wood_dark")
    for z in (0.62, 1.12):
        g.box((0, 0, z), (W - 0.08, D - 0.06, 0.015), "glass")
    g.box((0, -D / 2 + 0.01, H / 2 + 0.05), (W - 0.06, 0.006, H - 0.2), "glass")
    for (z0, n) in ((0.12, 3), (0.63, 4), (1.13, 3)):
        for k in range(n):
            x = -W / 2 + 0.18 + k * (W - 0.36) / max(1, n - 1)
            s = r.uniform(0.7, 1.15)
            prof = [(0.05 * s, 0), (0.05 * s, 0.03 * s), (0.015 * s, 0.05 * s), (0.012 * s, 0.14 * s), (0.06 * s, 0.2 * s),
                    (0.065 * s, 0.3 * s), (0.055 * s, 0.3 * s), (0.0, 0.25 * s)]
            g.lathe(prof, (x, 0.02, z0), "brass", seg=14)
    return g, {}


# ------------------------------------------------------------------------------------------------ library / store / toilet
def bookshelf(seed=6):
    g = Geo("bookshelf")
    r = _rng(seed)
    W, D, H = 1.0, 0.36, 2.05
    g.box((0, D / 2 - 0.01, H / 2), (W, 0.02, H), "wood_dark")
    for sx in (-1, 1):
        g.box((sx * (W / 2 - 0.012), 0, H / 2), (0.024, D, H), "wood")
    for k in range(6):
        z = 0.06 + k * 0.39
        g.box((0, 0, z), (W - 0.04, D, 0.022), "wood")
        if k == 5:
            continue
        x = -W / 2 + 0.03
        while x < W / 2 - 0.06:
            if r.random() < 0.06:
                x += r.uniform(0.05, 0.15)
                continue
            th = r.uniform(0.025, 0.06)
            hh = r.uniform(0.2, 0.33)
            lean = r.uniform(-3, 3) if r.random() < 0.8 else r.uniform(-18, 18)
            m = ["book_red", "book_blue", "book_green", "book_brown", "book_black", "paper"][int(r.integers(0, 6))]
            g.box((x + th / 2, -0.01, z + 0.011 + hh / 2), (th, D - 0.08, hh), m, R=rot_y(lean))
            x += th + 0.003
    return g, {}


def reading_table():
    g = Geo("reading_table")
    W, D, H = 2.0, 0.9, 0.76
    g.box((0, 0, H - 0.02), (W, D, 0.04), "wood")
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.06), sy * (D / 2 - 0.06), (H - 0.04) / 2), (0.06, 0.06, H - 0.04), "wood_dark")
    for k in range(3):
        g.box((-0.6 + k * 0.55, 0.0, H + 0.015), (0.2, 0.28, 0.03), ["book_red", "book_green", "book_brown"][k], R=rot_z(15 * k - 10))
    return g, {}


def broken_desks():
    g = Geo("broken_desks")
    a, _ = desk_bench(7)
    g.merge(a, R=rot_z(5), T=(0, 0, 0))
    b, _ = desk_bench(8)
    b.transform(R=rot_x(180))
    g.merge(b, R=rot_z(-8), T=(0.05, 0.1, 1.55))
    c, _ = chair(seed=3)
    g.merge(c, R=rot_y(95) @ rot_z(30), T=(-0.9, -0.2, 0.25))
    return g, {}


def sack(c, s=1.0, seed=0):
    g = Geo()
    r = _rng(seed)
    prof = [(0.0, 0.0), (0.16, 0.0), (0.22, 0.06), (0.24, 0.2), (0.22, 0.38), (0.17, 0.5), (0.08, 0.56), (0.05, 0.62), (0.07, 0.66),
            (0.0, 0.66)]
    g.lathe([(p[0] * s, p[1] * s) for p in prof], (0, 0, 0), "sack", seg=18)
    # squash and lump it
    for i in range(len(g.V)):
        v = g.V[i]
        g.V[i] = np.array([v[0] * 1.15, v[1] * 0.82, v[2]]) + r.normal(0, 0.004, 3)
    g.transform(R=rot_z(r.uniform(0, 360)), T=c)
    return g


def sacks():
    g = Geo("sacks")
    for k, (x, y, s) in enumerate(((-0.25, 0.0, 1.0), (0.28, 0.05, 0.95), (0.0, 0.05, 0.9))):
        g.merge(sack((x, y, 0.0 if k < 2 else 0.5), s, seed=k + 1))
    return g, {}


def crate():
    g = Geo("crate")
    W, D, H = 0.6, 0.45, 0.42
    for z in (0.05, 0.2, 0.35):
        for y in (-D / 2 + 0.01, D / 2 - 0.01):
            g.box((0, y, z), (W, 0.018, 0.1), "wood_old")
        for x in (-W / 2 + 0.01, W / 2 - 0.01):
            g.box((x, 0, z), (0.018, D, 0.1), "wood_old")
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.03), sy * (D / 2 - 0.03), H / 2), (0.04, 0.04, H), "wood_old")
    g.box((0, 0, H - 0.01), (W, D, 0.02), "wood_old")
    return g, {}


def buckets():
    g = Geo("buckets")
    for k, (x, y, m) in enumerate(((-0.2, 0.0, "steel"), (0.22, 0.05, "plastic_blue"))):
        g.lathe([(0.0, 0.0), (0.12, 0.0), (0.155, 0.3), (0.165, 0.31), (0.16, 0.315), (0.148, 0.3), (0.112, 0.012), (0.0, 0.012)], (x, y, 0),
                m, seg=22)
    g.cyl((0.55, 0.15, 0.0), (0.6, 0.18, 1.3), 0.012, "wood_old", seg=8)
    g.lathe([(0.0, 0.0), (0.09, 0.02), (0.07, 0.25), (0.02, 0.3)], (0.55, 0.15, 0.0), "broom", seg=12)
    return g, {}


def sinks():
    g = Geo("sinks")
    for k in range(3):
        x = -1.1 + k * 1.1
        g.lathe([(0.0, 0.0), (0.16, 0.0), (0.23, 0.12), (0.24, 0.16), (0.22, 0.16), (0.15, 0.03), (0.0, 0.03)], (x, -0.24, 0.72),
                "ceramic", seg=24)
        g.box((x, -0.02, 0.6), (0.06, 0.06, 0.2), "rust")
        g.cyl((x, 0.0, 1.0), (x, -0.12, 1.0), 0.012, "steel", seg=10)
        g.cyl((x, -0.12, 1.0), (x, -0.12, 0.95), 0.01, "steel", seg=10)
    g.box((0, 0.0, 1.45), (3.0, 0.01, 0.6), "mirror")
    return g, {}


def stalls():
    g = Geo("stalls")
    for k in range(3):
        y = -1.2 + k * 1.2
        g.box((-0.9, y, 1.0), (1.8, 0.04, 2.0), "wood_painted_green")
    for k in range(2):
        y0 = -1.2 + k * 1.2
        d = Geo()
        d.box((0.0, 0.55, 0.95), (0.03, 1.1, 1.75), "wood_painted_green")
        d.transform(R=rot_z(-35 if k == 0 else -70), T=(-1.8, y0 + 0.02, 0.0))
        g.merge(d)
        g.box((-0.9, y0 + 0.6, 0.02), (0.5, 0.35, 0.04), "ceramic")
    return g, {}


# ------------------------------------------------------------------------------------------------ hall / kitchen
def stage():
    g = Geo("stage")
    W, D, H = 6.0, 2.4, 0.75
    g.box((0, 0, H / 2), (W, D, H), "wood_old", mats=["plaster", "plaster", "plaster", "plaster", "wood_old", "wood_old"])
    for k in range(3):
        h = H * (3 - k) / 4
        g.box((0, -D / 2 - 0.14 - k * 0.28, h / 2), (1.4, 0.28, h), "concrete")
    # curtain backdrop: folds as a zig-zag strip
    n = 40
    for i in range(n):
        x0 = -W / 2 + i * W / n
        x1 = x0 + W / n
        y0 = D / 2 - 0.05 + (0.06 if i % 2 else 0.0)
        y1 = D / 2 - 0.05 + (0.0 if i % 2 else 0.06)
        g.quad((x0, y0, H), (x1, y1, H), (x1, y1, H + 2.5), (x0, y0, H + 2.5), "curtain",
               uvs=[(i / n * 3, 0), ((i + 1) / n * 3, 0), ((i + 1) / n * 3, 2.5), (i / n * 3, 2.5)])
    return g, {}


def harmonium():
    g = Geo("harmonium")
    z0 = 0.75
    g.box((0, 0, z0 + 0.12), (0.62, 0.34, 0.24), "wood_dark")
    for k in range(24):
        g.box((-0.27 + k * 0.0235, -0.1, z0 + 0.245), (0.02, 0.1, 0.012), "ivory")
    for k in range(10):
        g.box((-0.26 + k * 0.05, -0.08, z0 + 0.258), (0.012, 0.055, 0.012), "metal_black")
    for k in range(6):
        g.box((0, 0.19 + k * 0.012, z0 + 0.12), (0.6, 0.012, 0.22 - (k % 2) * 0.02), "cardboard")
    return g, {}


def mats():
    g = Geo("mats")
    g.box((0, 0, 0.004), (2.2, 0.62, 0.008), "fabric_mat")
    return g, {}


def chulha():
    g = Geo("chulha")
    g.box((0, 0.25, 0.25), (0.9, 0.12, 0.5), "brick_soot")
    for sx in (-1, 1):
        g.box((sx * 0.39, 0.0, 0.25), (0.12, 0.6, 0.5), "brick_soot")
    g.box((0, 0, 0.02), (0.66, 0.5, 0.04), "ash")
    prof = [(0.0, 0.0), (0.2, 0.0), (0.28, 0.12), (0.3, 0.3), (0.27, 0.42), (0.26, 0.46), (0.28, 0.48), (0.25, 0.48), (0.24, 0.46)]
    g.lathe(prof, (0, 0.02, 0.5), "aluminium_soot", seg=26)
    return g, {}


def vessels():
    g = Geo("vessels")
    for k, (x, s) in enumerate(((-0.45, 1.0), (0.1, 0.8), (0.55, 0.65))):
        prof = [(0.0, 0.0), (0.18 * s, 0.0), (0.24 * s, 0.1 * s), (0.25 * s, 0.35 * s), (0.23 * s, 0.4 * s), (0.25 * s, 0.42 * s),
                (0.22 * s, 0.42 * s)]
        g.lathe(prof, (x, 0, 0), "aluminium", seg=24)
    for k in range(8):
        g.lathe([(0.0, 0.0), (0.12, 0.0), (0.15, 0.02), (0.14, 0.022), (0.11, 0.004), (0.0, 0.004)], (0.0, -0.2, 0.42 * 0.8 + 0.02 * k),
                "steel", seg=20)
    return g, {}


def kitchen_table():
    g = Geo("kitchen_table")
    W, D, H = 1.6, 0.7, 0.8
    g.box((0, 0, H - 0.02), (W, D, 0.04), "steel")
    for sx in (-1, 1):
        for sy in (-1, 1):
            g.box((sx * (W / 2 - 0.04), sy * (D / 2 - 0.04), (H - 0.04) / 2), (0.04, 0.04, H - 0.04), "steel")
    g.box((0, 0, 0.2), (W - 0.08, D - 0.08, 0.02), "steel")
    for k in range(4):
        g.lathe([(0.0, 0.0), (0.03, 0.0), (0.036, 0.09), (0.033, 0.09), (0.027, 0.004), (0.0, 0.004)], (-0.5 + k * 0.25, 0.1, H), "steel", seg=12)
    return g, {}


def gas_cylinder():
    g = Geo("gas_cylinder")
    prof = [(0.0, 0.0), (0.13, 0.0), (0.15, 0.04), (0.15, 0.55), (0.12, 0.64), (0.05, 0.68), (0.03, 0.7), (0.0, 0.7)]
    g.lathe(prof, (0, 0, 0), "paint_red", seg=24)
    g.lathe([(0.15, 0.0), (0.16, 0.0), (0.16, 0.05), (0.15, 0.05)], (0, 0, 0), "paint_red", seg=24)
    g.lathe([(0.11, 0.62), (0.12, 0.62), (0.12, 0.75), (0.11, 0.75)], (0, 0, 0), "paint_red", seg=20)
    g.cyl((0, 0, 0.7), (0, 0, 0.77), 0.02, "brass", seg=10)
    return g, {}


# ------------------------------------------------------------------------------------------------ courtyard / yard
def flag_platform():
    g = Geo("flag_platform")
    for k, (s, h) in enumerate(((2.2, 0.15), (1.6, 0.15), (1.0, 0.15))):
        g.box((0, 0, h / 2 + k * 0.15), (s, s, h), "concrete")
    g.cyl((0, 0, 0.45), (0, 0, 6.5), 0.035, "steel", seg=12, r1=0.022)
    g.lathe([(0.0, 6.5), (0.05, 6.5), (0.05, 6.56), (0.0, 6.6)], (0, 0, 0), "brass", seg=12)
    g.cyl((0.04, 0, 1.0), (0.04, 0, 6.45), 0.003, "rope", seg=5)
    return g, {}


def hand_pump():
    """An India Mark II hand pump on its concrete apron."""
    g = Geo("hand_pump")
    g.box((0, 0, 0.06), (1.2, 1.2, 0.12), "concrete")
    g.box((0, 0, 0.1), (0.9, 0.9, 0.04), "concrete_wet")
    g.lathe([(0.0, 0.12), (0.2, 0.12), (0.16, 0.2), (0.07, 0.22), (0.07, 0.62), (0.09, 0.64), (0.09, 0.66), (0.0, 0.66)], (0, 0, 0),
            "metal_green", seg=18)
    g.lathe([(0.08, 0.66), (0.08, 1.02), (0.1, 1.04), (0.1, 1.08), (0.0, 1.1)], (0, 0, 0), "metal_green", seg=18)
    g.cyl((0, -0.07, 0.7), (0, -0.32, 0.62), 0.028, "metal_green", seg=10, r1=0.022)
    g.box((0.0, 0.1, 1.07), (0.06, 0.12, 0.08), "metal_green")
    h = Geo()
    h.cyl((0, 0, 0), (0, 0.85, 0), 0.022, "metal_green", seg=10, r1=0.016)
    h.transform(R=rot_x(18), T=(0.0, 0.14, 1.08))
    g.merge(h)
    return g, {}


def water_tank():
    g = Geo("water_tank")
    W, D, H = 2.2, 0.8, 1.05
    g.box((0, 0, H / 2), (W, D, H), "concrete", mats=["plaster_ext", "plaster_ext", "plaster_ext", "plaster_ext", "concrete", "concrete"])
    for k in range(4):
        x = -0.8 + k * 0.53
        g.cyl((x, -D / 2, 0.5), (x, -D / 2 - 0.1, 0.5), 0.012, "brass", seg=10)
        g.cyl((x, -D / 2 - 0.1, 0.5), (x, -D / 2 - 0.1, 0.45), 0.01, "brass", seg=10)
    g.box((0, -D / 2 - 0.2, 0.06), (W, 0.4, 0.12), "concrete_wet")
    return g, {}


def neem_tree(seed=11):
    """A big old neem in the courtyard: a twisted trunk, branches, and leaf cards."""
    g = Geo("neem_tree")
    r = _rng(seed)
    leaves = Geo("neem_leaves")

    def branch(p, d, length, rad, depth):
        n = max(3, int(length / 0.4))
        pts = [np.asarray(p, float)]
        dd = np.asarray(d, float)
        for i in range(n):
            dd = dd + r.normal(0, 0.12, 3) + np.array([0, 0, 0.05 if depth < 2 else -0.02])
            dd /= np.linalg.norm(dd)
            pts.append(pts[-1] + dd * length / n)
        for i in range(n):
            t0 = i / n
            t1 = (i + 1) / n
            g.cyl(pts[i], pts[i + 1], rad * (1 - 0.6 * t0), "bark", seg=10 if depth < 2 else 6, r1=rad * (1 - 0.6 * t1), caps=False)
        if depth >= 3 or rad < 0.02:
            for k in range(6):
                q = pts[-1] + r.normal(0, 0.45, 3)
                s = r.uniform(0.7, 1.1)
                R = rot_z(r.uniform(0, 360)) @ rot_x(r.uniform(-40, 40))
                a = q + R @ np.array([-0.45 * s, 0, -0.3 * s])
                b = q + R @ np.array([0.45 * s, 0, -0.3 * s])
                c = q + R @ np.array([0.45 * s, 0, 0.3 * s])
                e = q + R @ np.array([-0.45 * s, 0, 0.3 * s])
                leaves.quad(a, b, c, e, "leaves", uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
            return
        for k in range(2 if depth > 0 else 4):
            nd = dd + r.normal(0, 0.55, 3)
            nd[2] = abs(nd[2]) + 0.25
            nd /= np.linalg.norm(nd)
            branch(pts[-1] if depth > 0 else pts[int(n * r.uniform(0.55, 0.95))], nd, length * r.uniform(0.55, 0.75), rad * 0.55,
                   depth + 1)
    branch((0, 0, 0), (0.05, 0.02, 1.0), 4.2, 0.28, 0)
    return g, {"leaves": (leaves, (0, 0, 0))}


def gate():
    g = Geo("gate")
    for sx in (-1, 1):
        g.box((sx * 1.95, 0, 1.2), (0.6, 0.6, 2.4), "plaster_ext")
        g.box((sx * 1.95, 0, 2.45), (0.7, 0.7, 0.1), "concrete")
    leaves = {}
    for side, sx in (("L", -1), ("R", 1)):
        d = Geo("gate_" + side)
        w = 1.6
        for k in range(11):
            x = -sx * (0.05 + k * (w - 0.1) / 10)
            d.cyl((x, 0, 0.08), (x, 0, 1.95), 0.012, "rust", seg=6)
        for z in (0.12, 1.0, 1.9):
            d.box((-sx * w / 2, 0, z), (w, 0.03, 0.05), "rust")
        leaves["leaf_" + side] = (d, (sx * 1.65, 0, 0))
    return g, leaves


FURN = {
    "desk_bench": desk_bench, "blackboard": blackboard, "dais": dais, "teacher_table": teacher_table,
    "teacher_chair": lambda: chair(1.0, arms=True), "almirah": almirah, "fan": fan, "principal_desk": principal_desk,
    "office_chair": lambda: chair(1.15, seed=4, arms=True), "visitor_chair": lambda: chair(0.9, seed=5), "file_rack": file_rack,
    "wall_clock": wall_clock, "long_table": long_table, "lockers": lockers, "matka_stand": matka_stand, "bench": bench,
    "notice_board": notice_board, "school_bell": school_bell, "trophy_case": trophy_case, "bookshelf": bookshelf,
    "reading_table": reading_table, "broken_desks": broken_desks, "sacks": sacks, "crate": crate, "buckets": buckets,
    "sinks": sinks, "stalls": stalls, "stage": stage, "harmonium": harmonium, "mats": mats, "chulha": chulha,
    "vessels": vessels, "kitchen_table": kitchen_table, "gas_cylinder": gas_cylinder, "flag_platform": flag_platform,
    "hand_pump": hand_pump, "water_tank": water_tank, "neem_tree": neem_tree, "gate": gate,
}

# footprint (width along local x, depth along local y) for collisions and the walk grid; None = walk-through
FOOTPRINT = {
    "desk_bench": (1.12, 0.86, 0.75, 0.21), "blackboard": None, "dais": None, "teacher_table": (1.2, 0.72, 0.76, 0.0),
    "teacher_chair": (0.5, 0.5, 0.5, 0.0), "almirah": (0.92, 0.5, 1.86, 0.0), "fan": None, "principal_desk": (1.5, 0.82, 0.78, 0.0),
    "office_chair": (0.5, 0.5, 0.5, 0.0), "visitor_chair": (0.48, 0.48, 0.5, 0.0), "file_rack": (0.9, 0.4, 1.85, 0.0),
    "wall_clock": None, "long_table": (2.4, 0.9, 0.76, 0.0), "lockers": (1.2, 0.45, 1.82, 0.0), "matka_stand": (0.42, 0.42, 1.1, 0.0),
    "bench": (1.5, 0.36, 0.46, 0.0), "notice_board": None, "school_bell": None, "trophy_case": (1.1, 0.42, 1.7, 0.0),
    "bookshelf": (1.0, 0.36, 2.05, 0.0), "reading_table": (2.0, 0.9, 0.76, 0.0), "broken_desks": (2.2, 1.0, 1.6, 0.0),
    "sacks": (0.95, 0.5, 0.9, 0.0), "crate": (0.6, 0.45, 0.42, 0.0), "buckets": (1.0, 0.45, 0.4, 0.0), "sinks": (3.0, 0.5, 0.9, -0.15),
    "stalls": (1.8, 2.4, 2.0, 0.0), "stage": (6.0, 2.4, 0.75, 0.0), "harmonium": None, "mats": None, "chulha": (0.9, 0.62, 0.95, 0.0),
    "vessels": (1.4, 0.6, 0.45, 0.0), "kitchen_table": (1.6, 0.7, 0.8, 0.0), "gas_cylinder": (0.34, 0.34, 0.77, 0.0),
    "flag_platform": (2.2, 2.2, 0.45, 0.0), "hand_pump": (0.5, 1.2, 1.1, 0.25), "water_tank": (2.2, 0.8, 1.05, 0.0),
    "neem_tree": (0.6, 0.6, 3.0, 0.0), "gate": None,
}
# height of the surface an item can rest on (for item spots)
TOP_Z = {"desk_bench": 0.756, "teacher_table": 0.78, "long_table": 0.78, "reading_table": 0.78, "kitchen_table": 0.82,
         "principal_desk": 0.79, "stage": 0.75, "crate": 0.43, "almirah": 1.535}
