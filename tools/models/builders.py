"""
Granny Dimnight model kit: one function per kind of object. Each gets a Ctx (see build.py) with the object's size and
fills ctx.m in the builder frame: x across (-w/2..w/2), y up (0..h), z depth (-d/2..d/2), front facing +z. Objects that
are not furniture-shaped set ctx.raw and build straight in the object's canonical bounds (fr.cmin..fr.cmax).
"""
import math
import re

import numpy as np

from mesh import Mesh, rot_x, rot_y, rot_z, translate
from materials import tile

# ----------------------------------------------------------------------------------------------- helpers
def T(mat):
    return tile(mat)


def raw_box(ctx, mat, inset=0.0):
    ctx.raw = True
    mn = ctx.fr.cmin + inset
    mx = ctx.fr.cmax - inset
    ctx.m.box(mn, mx, mat, T(mat))


SURFACE_MAP = [
    # original texture/material name -> new material (the room's colour family, clean)
    (r"royal-purple|^wall2$", "wallpaper_rose"),
    (r"^wall3$|^wall$|^Wall$", "plaster_cream"),
    (r"^wall5$", "plaster_peach"),
    (r"^wall6$", "plaster_green"),
    (r"^wall7$", "plaster_blue"),
    (r"^wall8$", "plaster_peach"),
    (r"^wall9$", "plaster_white"),
    (r"^wall10$|secret_room", "wood_panel_dark"),
    (r"Bathroom_wall", "tiles_white"),
    (r"outsidewall|outside_wallroom|outside_roomwall|storage_roomwall|nor_wall_wooden", "wood_panel_wall"),
    (r"^underwall2$", "plaster_grey"),
    (r"^underwall$", "stone_wall"),
    (r"stair_block|stair_wood|floor_new|^floor$|WoodPlanksClean", "floor_wood"),
    (r"bathroom_floor", "tiles_floor"),
    (r"garage_?floor|garage_floor", "floor_concrete"),
    (r"07c2b8bcad9fb6a6ef|grass", "grass"),
    (r"walltext|the-rich-dark", "wood_walnut"),
    (r"wood_text|WoodFinedark|TexturesCom_Wood", "wood_walnut"),
    (r"WoodFineLight|tabletext", "wood_oak"),
    (r"^images$", "plaster_cream"),
    (r"^Lit$", "floor_wood"),
    (r"^door$|main_door|wooden_door", "wood_door"),
    (r"^wood$|wardrobe", "wood_walnut"),
    (r"F2244|Fabric", "fabric_beige"),
    (r"window", "trim_white"),
]


def surface_material(ctx, default="plaster_cream"):
    for m in ctx.mats:
        for pat, key in SURFACE_MAP:
            if re.search(pat, m):
                return key
    return default


# ----------------------------------------------------------------------------------------------- house parts
def surface(ctx):
    """Walls, floors, ceilings, steps, trims: a clean box of the same size, in the room's material."""
    mat = surface_material(ctx)
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    # paper-thin planes get a little thickness so they light properly
    for i in range(3):
        if mx[i] - mn[i] < 0.004:
            mn[i] -= 0.002
            mx[i] += 0.002
    ctx.m.box(mn, mx, mat, T(mat))


def floor_plane(ctx):
    surface(ctx)


def surface_or_columns(ctx):
    if (ctx.e.get("tris") or 0) > 16 and not ctx.e.get("builtin"):
        return columns(ctx)
    return surface(ctx)


def stair_ramp(ctx):
    """The invisible-ish ramps under the steps (Stair1/Stair2): keep the walking surface, in floor wood."""
    surface(ctx)


def door_frame_post(ctx):
    ctx.raw = True
    ctx.m.bevel_box(ctx.fr.cmin, ctx.fr.cmax, "trim_white", 0.01, T("trim_white"))


def house_door(ctx):
    """A wooden door with two raised panels and a brass knob on both sides."""
    thin = ctx.thin_axis()
    ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    wood = "wood_door" if "main" not in ctx.mat0 else "wood_walnut"
    m.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), wood, T(wood))
    # raised panels on both faces
    for s in (1, -1):
        z = s * d / 2
        for (y0, y1) in ((0.12 * h, 0.45 * h), (0.55 * h, 0.9 * h)):
            for (x0, x1) in ((-0.38 * w, -0.04 * w), (0.04 * w, 0.38 * w)):
                m.box((x0, y0, min(z, z + s * 0.012)), (x1, y1, max(z, z + s * 0.012)), wood, T(wood))
    hinge = ctx.hinge_side()
    kx = (0.38 * w) if hinge == "left" else (-0.38 * w)
    for s in (1, -1):
        z = s * d / 2
        m.cylinder((kx, 0.47 * h, z), 0.022, s * 0.05, "brass", axis="z", segs=10) if s > 0 else \
            m.cylinder((kx, 0.47 * h, z - 0.05), 0.022, 0.05, "brass", axis="z", segs=10)
        m.sphere((kx, 0.47 * h, z + s * 0.06), 0.032, "brass", segs=10, rings=6)


def garage_door(ctx):
    thin = ctx.thin_axis()
    ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "paint_green", T("paint_green"))
    for i in range(1, 6):
        y = h * i / 6
        for s in (1, -1):
            m.box((-w / 2 + 0.03, y - 0.01, s * d / 2 - 0.005), (w / 2 - 0.03, y + 0.01, s * d / 2 + 0.005), "paint_green")
    m.box((w * 0.28, 0.45 * h, d / 2), (w * 0.36, 0.48 * h, d / 2 + 0.03), "steel_dark")


def rolling_shutter(ctx):
    thin = ctx.thin_axis()
    ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    slats = max(8, int(h / 0.09))
    for i in range(slats):
        y0 = h * 0.85 * i / slats
        m.box((-w / 2 + 0.05, y0, -0.02), (w / 2 - 0.05, y0 + h * 0.85 / slats * 0.85, 0.02), "steel", 1.0)
    m.box((-w / 2, h * 0.85, -d / 2), (w / 2, h, d / 2), "steel_dark")
    for s in (-1, 1):
        m.box((s * w / 2 - 0.05 if s > 0 else -w / 2, 0, -0.04), (w / 2 if s > 0 else -w / 2 + 0.05, h * 0.85, 0.04), "steel_dark")


def window_frame(ctx):
    """Painted window frame with a cross (four panes), like a farmhouse window."""
    thin = ctx.thin_axis()
    ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    t = min(0.06, w * 0.06)
    mat = "trim_white"
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, t, d / 2), mat, 0.006)
    m.bevel_box((-w / 2, h - t, -d / 2), (w / 2, h, d / 2), mat, 0.006)
    m.bevel_box((-w / 2, 0, -d / 2), (-w / 2 + t, h, d / 2), mat, 0.006)
    m.bevel_box((w / 2 - t, 0, -d / 2), (w / 2, h, d / 2), mat, 0.006)
    m.bevel_box((-t * 0.4, t, -d * 0.35), (t * 0.4, h - t, d * 0.35), mat, 0.004)
    m.bevel_box((-w / 2 + t, h / 2 - t * 0.4, -d * 0.35), (w / 2 - t, h / 2 + t * 0.4, d * 0.35), mat, 0.004)
    # sill
    m.bevel_box((-w / 2 - 0.03, -0.03, -d / 2 - 0.04), (w / 2 + 0.03, 0.0, d / 2 + 0.04), mat, 0.006)


def window_glass(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    i = int(np.argmin(mx - mn))
    c = (mn[i] + mx[i]) / 2
    mn[i], mx[i] = c - 0.003, c + 0.003
    ctx.m.box(mn, mx, "glass")


# ----------------------------------------------------------------------------------------------- kitchen
def cabinet_body(ctx, mat=None):
    """Cupboard carcass: sides, top, bottom, back, inner shelf - the doors are separate objects."""
    front = ctx.front_by_walls("+z")
    pc = None
    ctx.set_front(front)
    w, h, d = ctx.dims
    m = ctx.m
    mat = mat or ("paint_cream" if re.search(r"Cupboard_Upper_01|Cupboard_Upper_02|Cupboard_Big", ctx.mat0) else "wood_oak")
    t = 0.018
    m.box((-w / 2, 0, -d / 2), (-w / 2 + t, h, d / 2 - 0.004), mat)
    m.box((w / 2 - t, 0, -d / 2), (w / 2, h, d / 2 - 0.004), mat)
    m.box((-w / 2, h - t, -d / 2), (w / 2, h, d / 2 - 0.004), mat)
    m.box((-w / 2, 0, -d / 2), (w / 2, t, d / 2 - 0.004), mat)
    m.box((-w / 2, 0, -d / 2), (w / 2, h, -d / 2 + t), mat)
    m.box((-w / 2 + t, h * 0.5 - t / 2, -d / 2 + t), (w / 2 - t, h * 0.5 + t / 2, d / 2 - 0.03), mat)


def cabinet_door(ctx, mat=None):
    """Shaker-style cupboard door with a metal handle on the side away from the hinge."""
    pc = ctx.parent_center()
    thin = ctx.thin_axis()
    if pc is not None:
        ctx.set_front(ctx.front_away_from(pc, axes=(thin,)))
    else:
        ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    mat = mat or ("paint_cream" if re.search(r"Cupboard_Upper_01|Cupboard_Upper_02|Cupboard_Big|Gas", ctx.mat0 + " ".join(ctx.mats)) else "wood_oak")
    fr_w = min(0.06, w * 0.14)
    m.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2 - 0.006), mat)
    # frame rails on the front
    z0, z1 = d / 2 - 0.006, d / 2
    m.box((-w / 2, 0, z0), (-w / 2 + fr_w, h, z1), mat)
    m.box((w / 2 - fr_w, 0, z0), (w / 2, h, z1), mat)
    m.box((-w / 2 + fr_w, 0, z0), (w / 2 - fr_w, fr_w, z1), mat)
    m.box((-w / 2 + fr_w, h - fr_w, z0), (w / 2 - fr_w, h, z1), mat)
    hinge = ctx.hinge_side()
    hx = (w / 2 - fr_w * 0.6) if hinge == "left" else (-w / 2 + fr_w * 0.6)
    hy0, hy1 = (h * 0.62, h * 0.82) if h > 0.6 else (h * 0.35, h * 0.65)
    if ctx.e["path"].count("Upper") or ctx.fr.cmin[1] > 1.0:
        hy0, hy1 = h * 0.1, h * 0.3
    m.box((hx - 0.008, hy0, z1), (hx + 0.008, hy1, z1 + 0.012), "steel")
    m.box((hx - 0.008, hy0, z1 + 0.012), (hx + 0.008, hy0 + 0.012, z1 + 0.025), "steel")
    m.box((hx - 0.008, hy1 - 0.012, z1 + 0.012), (hx + 0.008, hy1, z1 + 0.025), "steel")
    m.box((hx - 0.008, hy0, z1 + 0.025), (hx + 0.008, hy1, z1 + 0.035), "steel")


def drawer_box(ctx):
    """A drawer: front panel with a bar handle and the box behind it."""
    pc = ctx.parent_center()
    if pc is not None:
        ctx.set_front(ctx.front_away_from(pc))
    else:
        ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    mat = "paint_cream" if "Cupboard" in ctx.mat0 else ("wood_walnut" if "dark" in ctx.mat0.lower() else "wood_oak")
    ft = min(0.02, d * 0.1)
    m.box((-w / 2, 0, d / 2 - ft), (w / 2, h, d / 2), mat)
    t = 0.012
    m.box((-w / 2 + 0.01, 0.01, -d / 2), (-w / 2 + 0.01 + t, h * 0.8, d / 2 - ft), "wood_pine")
    m.box((w / 2 - 0.01 - t, 0.01, -d / 2), (w / 2 - 0.01, h * 0.8, d / 2 - ft), "wood_pine")
    m.box((-w / 2 + 0.01, 0.01, -d / 2), (w / 2 - 0.01, h * 0.8, -d / 2 + t), "wood_pine")
    m.box((-w / 2 + 0.01, 0.01, -d / 2), (w / 2 - 0.01, 0.01 + t, d / 2 - ft), "wood_pine")
    hw = min(0.18, w * 0.4)
    m.box((-hw / 2, h * 0.5 - 0.008, d / 2), (hw / 2, h * 0.5 + 0.008, d / 2 + 0.03), "steel")


def drawer_chest_body(ctx):
    front = ctx.front_by_walls("+z")
    ctx.set_front(front)
    w, h, d = ctx.dims
    m = ctx.m
    mat = "paint_cream" if "Cupboard" in ctx.mat0 else "wood_walnut" if "dark" in ctx.mat0.lower() else "wood_oak"
    t = 0.02
    m.box((-w / 2, 0, -d / 2), (-w / 2 + t, h, d / 2), mat)
    m.box((w / 2 - t, 0, -d / 2), (w / 2, h, d / 2), mat)
    m.bevel_box((-w / 2 - 0.01, h - 0.03, -d / 2), (w / 2 + 0.01, h, d / 2 + 0.015), mat, 0.006)
    m.box((-w / 2, 0, -d / 2), (w / 2, 0.06, d / 2 - 0.01), mat)
    m.box((-w / 2, 0, -d / 2), (w / 2, h, -d / 2 + t), mat)


def bedside_body(ctx):
    drawer_chest_body(ctx)


def oven_front(ctx):
    pc = ctx.parent_center()
    thin = ctx.thin_axis()
    ctx.set_front(ctx.front_by_walls("+z" if thin == "z" else "+x"))
    if (ctx.front[1] != thin):
        ctx.set_front("+" + thin)
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "steel")
    m.box((-w * 0.38, h * 0.18, d / 2), (w * 0.38, h * 0.7, d / 2 + 0.004), "glass_dark")
    m.cylinder((-w * 0.36, h * 0.82, d / 2 + 0.03), 0.012, w * 0.72, "chrome", axis="x", segs=8)
    for s in (-1, 1):
        m.box((s * w * 0.33 - 0.01, h * 0.8, d / 2), (s * w * 0.33 + 0.01, h * 0.84, d / 2 + 0.03), "chrome")


def cooktop(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "glass_dark")
    for (x, z, r) in ((-0.25, -0.22, 0.09), (0.22, -0.22, 0.07), (-0.25, 0.2, 0.07), (0.22, 0.2, 0.09)):
        m.torus((x * w, h + 0.002, z * d), r * min(w, d) / 0.6, 0.006, "steel_dark", segs=16, tube_segs=4)


def knob(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    c = (mn + mx) / 2
    # a row of knobs along the longest axis
    ax = int(np.argmax(size))
    n = max(1, min(5, int(round(size[ax] / max(1e-3, 2.2 * min(size[(ax + 1) % 3], size[(ax + 2) % 3]))))))
    thin = int(np.argmin(size))
    r = min(size[(ax + 1) % 3] if (ax + 1) % 3 != thin else size[(ax + 2) % 3], size[ax] / n) * 0.42
    for i in range(n):
        p = c.copy()
        p[ax] = mn[ax] + size[ax] * (i + 0.5) / n
        p[thin] = mn[thin]
        ctx.m.cylinder(p, max(r, 0.003), max(size[thin], 0.004), "plastic_black", axis="xyz"[thin], segs=10)


def sink_basin(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    s = "steel"
    m.box((-w / 2, h - 0.012, -d / 2), (w / 2, h, -d * 0.38), s)
    m.box((-w / 2, h - 0.012, d * 0.38), (w / 2, h, d / 2), s)
    m.box((-w / 2, h - 0.012, -d * 0.38), (-w * 0.42, h, d * 0.38), s)
    m.box((w * 0.02, h - 0.012, -d * 0.38), (w * 0.06, h, d * 0.38), s)
    m.box((w * 0.42, h - 0.012, -d * 0.38), (w / 2, h, d * 0.38), s)
    for (x0, x1) in ((-w * 0.42, w * 0.02), (w * 0.06, w * 0.42)):
        m.box((x0, 0, -d * 0.38), (x1, 0.01, d * 0.38), s)
        m.box((x0, 0, -d * 0.38), (x0 + 0.008, h, d * 0.38), s)
        m.box((x1 - 0.008, 0, -d * 0.38), (x1, h, d * 0.38), s)
        m.box((x0, 0, -d * 0.38), (x1, h, -d * 0.38 + 0.008), s)
        m.box((x0, 0, d * 0.38 - 0.008), (x1, h, d * 0.38), s)
        m.cylinder(((x0 + x1) / 2, 0.011, 0), 0.025, 0.002, "steel_dark", segs=10)


def faucet(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) * 0.08
    m.cylinder((0, 0, -d * 0.3), r * 1.6, h * 0.12, "chrome", segs=12)
    m.cylinder((0, h * 0.12, -d * 0.3), r, h * 0.7, "chrome", segs=10)
    m.torus((0, h * 0.82, -d * 0.05), d * 0.25, r, "chrome", axis="x", segs=10, tube_segs=6, arc=math.pi, start=0)
    m.cylinder((0, h * 0.82 - d * 0.0, d * 0.2), r, -h * 0.15, "chrome", segs=10)
    m.box((-w * 0.3, h * 0.6, -d * 0.36), (w * 0.3, h * 0.64, -d * 0.24), "chrome")


def range_hood(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    hb = h * 0.3
    # trapezoid canopy
    pts = [(-w / 2, 0), (w / 2, 0), (w * 0.2, hb), (-w * 0.2, hb)]
    m.extrude([(p[0], p[1]) for p in pts], d, "steel", plane="xy", offset=0)
    m.box((-w * 0.15, hb, -d / 2), (w * 0.15, h, -d / 2 + d * 0.45), "steel")


def countertop(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    top = min(0.04, h)
    m.bevel_box((-w / 2, h - top, -d / 2), (w / 2, h, d / 2), "tiles_floor" if "Table" in ctx.name else "wood_oak", 0.006)
    if h > 0.2:
        m.box((-w / 2 + 0.02, 0, -d / 2 + 0.02), (w / 2 - 0.02, h - top, d / 2 - 0.04), "paint_cream")


def plinth(ctx):
    ctx.raw = True
    ctx.m.box(ctx.fr.cmin, ctx.fr.cmax, "paint_black")


def kitchen_unit(ctx):
    """A full kitchen cabinet (KitchenSet): carcass with doors and a worktop."""
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, 0.08, -d / 2), (w / 2, h - 0.04, d / 2 - 0.02), "wood_oak")
    m.box((-w / 2 + 0.02, 0, -d / 2), (w / 2 - 0.02, 0.08, d / 2 - 0.06), "paint_black")
    m.bevel_box((-w / 2 - 0.01, h - 0.04, -d / 2), (w / 2 + 0.01, h, d / 2 + 0.02), "tiles_floor", 0.006)
    n = max(1, int(round(w / 0.5)))
    for i in range(n):
        x0 = -w / 2 + w * i / n + 0.004
        x1 = -w / 2 + w * (i + 1) / n - 0.004
        m.box((x0, 0.1, d / 2 - 0.02), (x1, h - 0.06, d / 2), "paint_cream")
        hx = x1 - 0.04 if i % 2 == 0 else x0 + 0.04
        m.box((hx - 0.007, h - 0.25, d / 2), (hx + 0.007, h - 0.1, d / 2 + 0.025), "steel")


def gas_pipe(ctx):
    ctx.raw = True
    knob(ctx)


# ----------------------------------------------------------------------------------------------- living
def bed(ctx):
    """Wooden bed: frame, legs, mattress, pillow, folded blanket and a headboard on the tall (or wall) side."""
    f = ctx.front_by_height(None) or ctx.front_by_walls("+z")
    ctx.set_front(f)
    w, h, d = ctx.dims
    if w > d * 1.25:          # the long side must run front to back
        ctx.set_front({"+z": "+x", "-z": "-x", "+x": "+z", "-x": "-z"}[f])
        w, h, d = ctx.dims
    m = ctx.m
    wood = "wood_walnut"
    leg = min(0.07, w * 0.05)
    fh = min(0.42, h * 0.38)
    m.box((-w / 2, fh - 0.14, -d / 2 + 0.06), (w / 2, fh, d / 2), wood)
    for sx in (-1, 1):
        for sz in (-1, 1):
            z = (d / 2 - leg) * sz
            m.box((sx * (w / 2 - leg) - leg / 2 + (0 if sx < 0 else 0), 0, z - leg / 2), (sx * (w / 2 - leg) + leg / 2, fh - 0.1, z + leg / 2), wood)
    mt = min(0.2, h * 0.18)
    m.bevel_box((-w / 2 + 0.03, fh, -d / 2 + 0.08), (w / 2 - 0.03, fh + mt, d / 2 - 0.02), "linen_white", 0.04)
    # pillow at the head (back, -z) and blanket over the foot half
    m.bevel_box((-w * 0.38, fh + mt, -d / 2 + 0.12), (w * 0.38, fh + mt + 0.12, -d / 2 + 0.12 + min(0.45, d * 0.18)), "linen_white", 0.05)
    blanket = "blanket_rose" if ctx.rng.random() < 0.5 else "blanket_blue"
    m.bevel_box((-w / 2 + 0.01, fh + mt - 0.04, -d * 0.05), (w / 2 - 0.01, fh + mt + 0.035, d / 2 - 0.0), blanket, 0.02)
    # headboard
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, h, -d / 2 + 0.06), wood, 0.012)
    m.box((-w / 2 + 0.08, fh + 0.25, -d / 2 + 0.06), (w / 2 - 0.08, h - 0.08, -d / 2 + 0.075), "wood_cherry")
    # footboard (low)
    m.bevel_box((-w / 2, 0, d / 2 - 0.05), (w / 2, fh + 0.18, d / 2), wood, 0.01)


def sofa(ctx, fabric=None):
    f = ctx.front_by_height(None) or ctx.front_by_walls("+z")
    ctx.set_front(f)
    w, h, d = ctx.dims
    m = ctx.m
    fab = fabric or ("fabric_red" if re.search(r"soviet|red", " ".join(ctx.mats + [ctx.e["path"]]), re.I) else "fabric_green")
    seat = min(0.45, h * 0.45)
    arm = min(0.16, w * 0.12)
    back = min(0.22, d * 0.25)
    m.bevel_box((-w / 2, 0.08, -d / 2), (w / 2, seat - 0.12, d / 2), fab, 0.03)
    n = max(1, int(round((w - 2 * arm) / 0.65)))
    for i in range(n):
        x0 = -w / 2 + arm + (w - 2 * arm) * i / n + 0.005
        x1 = -w / 2 + arm + (w - 2 * arm) * (i + 1) / n - 0.005
        m.bevel_box((x0, seat - 0.12, -d / 2 + back), (x1, seat, d / 2 - 0.01), fab, 0.04)
        m.bevel_box((x0, seat, -d / 2 + 0.02), (x1, h - 0.02, -d / 2 + back + 0.02), fab, 0.05)
    m.bevel_box((-w / 2, 0.08, -d / 2), (w / 2, h * 0.92, -d / 2 + back * 0.6), fab, 0.03)
    for s in (-1, 1):
        x0, x1 = (-w / 2, -w / 2 + arm) if s < 0 else (w / 2 - arm, w / 2)
        m.bevel_box((x0, 0.08, -d / 2), (x1, seat + 0.18, d / 2), fab, 0.04)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.cylinder((sx * (w / 2 - 0.06), 0, sz * (d / 2 - 0.06)), 0.025, 0.08, "wood_walnut", segs=8, radius2=0.018)


def armchair(ctx):
    sofa(ctx, fabric="fabric_beige")


def cushion(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    r = 0.4 * min(mx - mn)
    ctx.m.bevel_box(mn, mx, "fabric_beige" if "F2244" in ctx.mat0 else "fabric_green", min(0.06, r))


def sofa_part(ctx):
    """Big sofa pieces (Box004 base, back rails): soft boxes."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    mat = "fabric_beige" if "F2244" in ctx.mat0 else "fabric_green"
    ctx.m.bevel_box(mn, mx, mat, min(0.05, 0.3 * min(mx - mn)))


def table(ctx, top_mat=None, leg_mat=None):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    tm = top_mat or ("wood_oak" if re.search(r"Light|tabletext|1001", ctx.mat0) else "wood_walnut")
    lm = leg_mat or tm
    top = min(0.05, h * 0.08)
    m.bevel_box((-w / 2, h - top, -d / 2), (w / 2, h, d / 2), tm, 0.008)
    apron = min(0.08, h * 0.12)
    inset = min(0.06, min(w, d) * 0.08)
    m.box((-w / 2 + inset, h - top - apron, -d / 2 + inset), (w / 2 - inset, h - top, -d / 2 + inset + 0.02), tm)
    m.box((-w / 2 + inset, h - top - apron, d / 2 - inset - 0.02), (w / 2 - inset, h - top, d / 2 - inset), tm)
    leg = min(0.06, min(w, d) * 0.08)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x = sx * (w / 2 - inset - leg / 2)
            z = sz * (d / 2 - inset - leg / 2)
            m.box((x - leg / 2, 0, z - leg / 2), (x + leg / 2, h - top, z + leg / 2), lm)


def tabletop(ctx):
    ctx.raw = True
    ctx.m.bevel_box(ctx.fr.cmin, ctx.fr.cmax, "wood_oak", 0.008)


def round_stool(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.cylinder((0, h - 0.04, 0), r, 0.04, "wood_walnut", segs=16)
    m.cylinder((0, 0.03, 0), r * 0.12, h - 0.07, "iron_black", segs=8)
    for a in (0, 90):
        b = Mesh()
        b.box((-r * 0.9, 0, -0.02), (r * 0.9, 0.03, 0.02), "iron_black")
        m.add(b, rot_y(a + 45))


def small_table_part(ctx):
    """Parts of the bedroom side table (top, shelf, drawer) - soft boxes in walnut."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    if (mx - mn)[1] > 0.3:
        # the frame with legs
        ctx.set_front("+z")
        ctx.raw = False
        w, h, d = ctx.dims
        table(ctx, top_mat="wood_walnut")
        return
    ctx.m.bevel_box(mn, mx, "wood_walnut", 0.006)


def desk(ctx):
    table(ctx, top_mat="wood_oak")


def bookshelf(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    mat = "wood_walnut"
    t = 0.025
    m.box((-w / 2, 0, -d / 2), (-w / 2 + t, h, d / 2), mat)
    m.box((w / 2 - t, 0, -d / 2), (w / 2, h, d / 2), mat)
    m.box((-w / 2, 0, -d / 2), (w / 2, h, -d / 2 + 0.012), mat)
    m.bevel_box((-w / 2 - 0.015, h - t, -d / 2), (w / 2 + 0.015, h, d / 2 + 0.015), mat, 0.006)
    n = max(3, int(round(h / 0.38)))
    for i in range(n):
        y = h * i / n
        m.box((-w / 2 + t, y, -d / 2), (w / 2 - t, y + t, d / 2), mat)


def books(ctx, single=False):
    """A row of books standing up (or one book)."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    size = mx - mn
    cols = ["book_red", "book_green", "book_blue", "book_brown", "book_black"]
    # books stand on y; the row runs along the longer horizontal axis
    ax = 0 if size[0] >= size[2] else 2
    if size[1] < 0.6 * max(size[0], size[2]) and size[1] < 0.08:
        # lying flat: one closed book
        ctx.m.bevel_box(mn, mx, cols[ctx.rng.randrange(len(cols))], 0.003)
        inner_mn, inner_mx = mn.copy(), mx.copy()
        inner_mn[1] += size[1] * 0.12
        inner_mx[1] -= size[1] * 0.12
        o = 2 - ax if ax == 0 else 0
        inner_mx[o] += 0.002
        ctx.m.box(inner_mn, inner_mx, "book_pages")
        return
    n = 1 if single else max(1, int(round(size[ax] / max(0.025, ctx.rng.uniform(0.03, 0.05)))))
    x = mn[ax]
    for i in range(n):
        wdt = size[ax] / n
        bh = size[1] * ctx.rng.uniform(0.78, 1.0) if not single else size[1]
        a = mn.copy()
        b = mx.copy()
        a[ax], b[ax] = x + 0.001, x + wdt - 0.001
        b[1] = mn[1] + bh
        col = cols[ctx.rng.randrange(len(cols))]
        ctx.m.box(a, b, col)
        x += wdt


def book(ctx):
    books(ctx, single=True)


def secret_book(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "book_red", 0.004)
    # gold title band
    size = mx - mn
    ax = int(np.argmax(size))
    a, b = mn.copy(), mx.copy()
    c = (mn[ax] + mx[ax]) / 2
    a[ax], b[ax] = c - size[ax] * 0.06, c + size[ax] * 0.06
    a = a - 0.001
    b = b + 0.001
    ctx.m.box(a, b, "gold")


def lamp_shade(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.lathe([(r, 0), (r * 0.62, h * 0.95), (r * 0.6, h)], (0, 0, 0), "lamp_shade", segs=18, close_bottom=False, close_top=False)
    m.sphere((0, h * 0.35, 0), r * 0.18, "bulb", segs=10, rings=6)


def lamp_table(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.lathe([(r * 0.55, 0), (r * 0.55, h * 0.06), (r * 0.25, h * 0.12), (r * 0.42, h * 0.45), (r * 0.18, h * 0.8),
             (r * 0.08, h * 0.85), (r * 0.06, h)], (0, 0, 0), "enamel_cream", segs=16)


def floor_lamp(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.cylinder((0, 0, 0), r * 0.6, 0.03, "brass", segs=16)
    m.cylinder((0, 0.03, 0), 0.015, h * 0.72, "brass", segs=8)
    m.lathe([(r, h * 0.7), (r * 0.55, h)], (0, 0, 0), "lamp_shade", segs=16, close_top=False, close_bottom=False)
    m.sphere((0, h * 0.78, 0), r * 0.18, "bulb", segs=10, rings=6)


def outdoor_lamp(ctx):
    lamp_shade(ctx)


def clock(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, h) / 2 * 0.9
    m.cylinder((0, h / 2, -d / 2), r, d * 0.8, "wood_cherry", axis="z", segs=20)
    m.cylinder((0, h / 2, -d / 2 + d * 0.8), r * 0.85, 0.004, "enamel_cream", axis="z", segs=20)
    m.box((-0.004, h / 2, d * 0.3 + 0.005), (0.004, h / 2 + r * 0.6, d * 0.3 + 0.01), "black")
    m.box((0, h / 2 - 0.004, d * 0.3 + 0.005), (r * 0.45, h / 2 + 0.004, d * 0.3 + 0.01), "black")


def vase(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.lathe([(r * 0.5, 0), (r * 0.9, h * 0.25), (r, h * 0.45), (r * 0.6, h * 0.75), (r * 0.35, h * 0.88), (r * 0.5, h)],
            (0, 0, 0), "ceramic" if ctx.rng.random() < 0.5 else "paint_blue", segs=16, close_top=False)


def tv_body(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "wood_walnut", 0.02)
    m.box((-w * 0.42, h * 0.14, d / 2), (w * 0.2, h * 0.86, d / 2 + 0.006), "tv_screen")
    for i in range(2):
        m.cylinder((w * 0.33, h * (0.65 - i * 0.25), d / 2), 0.025, 0.03, "plastic_black", axis="z", segs=10)
    m.box((w * 0.24, h * 0.15, d / 2), (w * 0.43, h * 0.3, d / 2 + 0.004), "steel_dark")


def tv_part(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "plastic_black" if (mx - mn).max() < 0.2 else "wood_walnut", 0.004)


def tv_cabinet(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    mat = "wood_walnut"
    m.bevel_box((-w / 2, 0.06, -d / 2), (w / 2, h, d / 2), mat, 0.01)
    n = max(1, int(round(w / 0.6)))
    for i in range(n):
        x0 = -w / 2 + w * i / n + 0.01
        x1 = -w / 2 + w * (i + 1) / n - 0.01
        m.box((x0, 0.1, d / 2), (x1, h - 0.04, d / 2 + 0.012), "wood_cherry")
        m.cylinder(((x0 + x1) / 2, h * 0.55, d / 2 + 0.012), 0.015, 0.02, "brass", axis="z", segs=8)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box((sx * (w / 2 - 0.05) - 0.025, 0, sz * (d / 2 - 0.05) - 0.025), (sx * (w / 2 - 0.05) + 0.025, 0.06, sz * (d / 2 - 0.05) + 0.025), mat)


def wardrobe(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    mat = "wood_walnut"
    m.bevel_box((-w / 2, 0.06, -d / 2), (w / 2, h - 0.05, d / 2), mat, 0.01)
    m.bevel_box((-w / 2 - 0.02, h - 0.05, -d / 2 - 0.01), (w / 2 + 0.02, h, d / 2 + 0.03), mat, 0.01)
    m.box((-w / 2 + 0.02, 0, -d / 2 + 0.02), (w / 2 - 0.02, 0.06, d / 2 - 0.02), mat)
    for s in (-1, 1):
        x0, x1 = (-w / 2 + 0.02, -0.006) if s < 0 else (0.006, w / 2 - 0.02)
        m.box((x0, 0.1, d / 2), (x1, h - 0.1, d / 2 + 0.012), "wood_cherry")
        m.box((x0 + 0.06, 0.2, d / 2 + 0.012), (x1 - 0.06, h - 0.2, d / 2 + 0.02), "wood_walnut")
        m.cylinder((s * 0.05, h * 0.5, d / 2 + 0.012), 0.016, 0.025, "brass", axis="z", segs=8)


def storage_cabinet(ctx):
    tv_cabinet(ctx)


def metal_shelf(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    p = 0.035
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box((sx * (w / 2) - (p if sx > 0 else 0), 0, sz * (d / 2) - (p if sz > 0 else 0)),
                  (sx * (w / 2) + (0 if sx > 0 else p), h, sz * (d / 2) + (0 if sz > 0 else p)), "steel_dark")
    for i in range(5):
        y = 0.08 + (h - 0.12) * i / 4
        m.box((-w / 2, y, -d / 2), (w / 2, y + 0.02, d / 2), "steel")


def rug(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    mx[1] = mn[1] + max(0.008, min(mx[1] - mn[1], 0.015))
    col = "rug_red" if ctx.rng.random() < 0.5 else "rug_blue"
    b = min(0.12, 0.08 * min(mx[0] - mn[0], mx[2] - mn[2]) + 0.05)
    ctx.m.box((mn[0] + b, mn[1], mn[2] + b), (mx[0] - b, mx[1], mx[2] - b), col)
    ctx.m.box(mn, (mx[0], mx[1] - 0.001, mn[2] + b), "rug_border")
    ctx.m.box((mn[0], mn[1], mx[2] - b), (mx[0], mx[1] - 0.001, mx[2]), "rug_border")
    ctx.m.box((mn[0], mn[1], mn[2] + b), (mn[0] + b, mx[1] - 0.001, mx[2] - b), "rug_border")
    ctx.m.box((mx[0] - b, mn[1], mn[2] + b), (mx[0], mx[1] - 0.001, mx[2] - b), "rug_border")


def painting(ctx):
    thin = ctx.thin_axis()
    ctx.set_front(ctx.front_by_walls("+z" if thin == "z" else "+x"))
    if ctx.front[1] != thin:
        ctx.set_front("+" + thin)
    w, h, d = ctx.dims
    m = ctx.m
    f = min(0.06, w * 0.08)
    pick = "painting_%d" % (1 + int(ctx.e["id"]) % 4)
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, f, d / 2), "wood_cherry", 0.006)
    m.bevel_box((-w / 2, h - f, -d / 2), (w / 2, h, d / 2), "wood_cherry", 0.006)
    m.bevel_box((-w / 2, 0, -d / 2), (-w / 2 + f, h, d / 2), "wood_cherry", 0.006)
    m.bevel_box((w / 2 - f, 0, -d / 2), (w / 2, h, d / 2), "wood_cherry", 0.006)
    m.quad((-w / 2 + f, f, 0), (w / 2 - f, f, 0), (w / 2 - f, h - f, 0), (-w / 2 + f, h - f, 0), (0, 0, 1), pick,
           uvs=[(0, 0), (1, 0), (1, 1), (0, 1)])
    m.box((-w / 2 + f, f, -d / 2), (w / 2 - f, h - f, -0.001), "wood_raw")


# ----------------------------------------------------------------------------------------------- storage & outside
def barrel(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    prof = [(r * 0.82, 0), (r * 0.95, h * 0.25), (r, h * 0.5), (r * 0.95, h * 0.75), (r * 0.82, h)]
    m.lathe(prof, (0, 0, 0), "wood_raw", segs=16, close_top=True)
    for y in (0.12, 0.3, 0.7, 0.88):
        rr = np.interp(y * h, [p[1] for p in prof], [p[0] for p in prof])
        m.cylinder((0, y * h - 0.02, 0), rr + 0.006, 0.04, "iron_black", segs=16, caps=False)


def crate(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    t = 0.02
    n = max(3, int(round(h / 0.12)))
    gap = 0.012
    for i in range(n):
        y0 = h * i / n
        y1 = h * (i + 1) / n - gap
        m.box((-w / 2, y0, -d / 2), (w / 2, y1, -d / 2 + t), "wood_raw")
        m.box((-w / 2, y0, d / 2 - t), (w / 2, y1, d / 2), "wood_raw")
        m.box((-w / 2, y0, -d / 2), (-w / 2 + t, y1, d / 2), "wood_raw")
        m.box((w / 2 - t, y0, -d / 2), (w / 2, y1, d / 2), "wood_raw")
    m.box((-w / 2, 0, -d / 2), (w / 2, t, d / 2), "wood_raw")
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.box((sx * w / 2 - (0.05 if sx > 0 else 0) - 0.001 * sx, 0, sz * d / 2 - (0.05 if sz > 0 else 0)),
                  (sx * w / 2 + (0 if sx > 0 else 0.05), h, sz * d / 2 + (0 if sz > 0 else 0.05)), "wood_walnut")


def storage_box(ctx):
    crate(ctx)


def box_pile(ctx):
    """A pile of cardboard boxes filling the original pile's space."""
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    y = 0.0
    layer = 0
    while y < h - 0.15 and layer < 6:
        bh = min(h - y, ctx.rng.uniform(0.35, 0.6))
        x = -w / 2
        shrink = layer * 0.08
        while x < w / 2 - 0.2:
            bw = min(w / 2 - x, ctx.rng.uniform(0.4, 0.8))
            z0 = -d / 2 + ctx.rng.uniform(0, 0.08) + shrink * d * 0.3
            z1 = d / 2 - ctx.rng.uniform(0, 0.1) - shrink * d * 0.2
            if bw > 0.15 and z1 - z0 > 0.2:
                m.box((x + 0.01, y, z0), (x + bw - 0.01, y + bh, z1), "cardboard")
                m.box((x + 0.01 + bw * 0.4, y + bh, z0), (x + bw * 0.6 - 0.01, y + bh + 0.002, z1), "tape_grey")
            x += bw
        y += bh
        layer += 1


def bench_plank(ctx):
    ctx.raw = True
    ctx.m.bevel_box(ctx.fr.cmin, ctx.fr.cmax, "wood_raw", 0.006)


def bench_legs(ctx):
    """The bench's leg frames: two A-shaped legs with a stretcher."""
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    p = 0.06
    for sx in (-1, 1):
        x = sx * (w / 2 - p)
        for sz in (-1, 1):
            z = sz * (d / 2 - p)
            m.box((x - p / 2, 0, z - p / 2), (x + p / 2, h, z + p / 2), "wood_raw")
        m.box((x - p / 2, h * 0.25, -d / 2 + p), (x + p / 2, h * 0.25 + p, d / 2 - p), "wood_raw")
    m.box((-w / 2 + p, h * 0.4, -p / 2), (w / 2 - p, h * 0.4 + p, p / 2), "wood_raw")


def well_bricks(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.cylinder((0, 0, 0), r, h * 0.42, "brick", segs=20, caps=False)
    m.cylinder((0, 0, 0), r * 0.82, h * 0.42, "stone_wall", segs=20, caps=False)
    m.torus((0, h * 0.42, 0), r * 0.91, r * 0.1, "stone_wall", segs=20, tube_segs=6)
    m.cylinder((0, h * 0.2, 0), r * 0.8, 0.01, "water", segs=20)
    for s in (-1, 1):
        m.box((s * r * 0.9 - 0.06, h * 0.4, -0.06), (s * r * 0.9 + 0.06, h, 0.06), "wood_raw")


def well_roller(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    c = (mn + mx) / 2
    r = min(size[(ax + 1) % 3], size[(ax + 2) % 3]) / 2
    p = c.copy()
    p[ax] = mn[ax]
    ctx.m.cylinder(p, r * 0.5, size[ax], "wood_raw", axis="xyz"[ax], segs=12)
    q = c.copy()
    q[ax] = mn[ax] + size[ax] * 0.3
    ctx.m.cylinder(q, r * 0.75, size[ax] * 0.4, "rope", axis="xyz"[ax], segs=12)


def gable_roof(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    pts = [(-w / 2, 0), (w / 2, 0), (0, h)]
    m.extrude([(-w / 2, 0), (-w / 2 + 0.06, 0), (0, h - 0.06), (w / 2 - 0.06, 0), (w / 2, 0), (0, h)], d, "roof_tiles", plane="xy")


def flat_roof(ctx):
    ctx.raw = True
    ctx.m.bevel_box(ctx.fr.cmin, ctx.fr.cmax, "roof_tiles", 0.01)


def fence_panel(ctx):
    thin = ctx.thin_axis()
    ctx.set_front("+z" if thin == "z" else "+x")
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, h - 0.05, -0.02), (w / 2, h, 0.02), "iron_black")
    m.box((-w / 2, 0.08, -0.02), (w / 2, 0.13, 0.02), "iron_black")
    n = max(4, int(w / 0.12))
    for i in range(n + 1):
        x = -w / 2 + w * i / n
        m.box((x - 0.01, 0.0, -0.01), (x + 0.01, h + 0.05, 0.01), "iron_black")
        m.cylinder((x, h + 0.05, 0), 0.02, 0.06, "iron_black", segs=6, radius2=0.0)


def fence_post(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "stone_wall", 0.01)


def bell(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.lathe([(r, 0), (r * 0.92, h * 0.15), (r * 0.6, h * 0.55), (r * 0.45, h * 0.85), (r * 0.2, h)], (0, 0, 0), "brass", segs=16, close_bottom=False)
    m.sphere((0, h * 0.08, 0), r * 0.18, "iron_black", segs=8, rings=5)


def lever_base(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, h, d / 2), "steel_dark", 0.01)
    m.box((-w * 0.3, h * 0.3, d / 2), (w * 0.3, h * 0.7, d / 2 + 0.01), "paint_red")


def lever_stick(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    c = (mn + mx) / 2
    r = max(0.008, min(size[(ax + 1) % 3], size[(ax + 2) % 3]) / 2)
    p = c.copy()
    p[ax] = mn[ax]
    ctx.m.cylinder(p, r * 0.6, size[ax] * 0.78, "steel", axis="xyz"[ax], segs=10)
    q = c.copy()
    q[ax] = mn[ax] + size[ax] * 0.78
    ctx.m.cylinder(q, r, size[ax] * 0.22, "plastic_red", axis="xyz"[ax], segs=10)


# ----------------------------------------------------------------------------------------------- bathroom
def bathtub(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    if d > w:
        ctx.set_front({"+z": "+x", "-z": "-x", "+x": "+z", "-x": "-z"}[ctx.front])
        w, h, d = ctx.dims
    m = ctx.m
    th = h * 0.85
    wall = 0.06
    m.bevel_box((-w / 2, th * 0.12, -d / 2), (w / 2, th * 0.2, d / 2), "enamel_cream", 0.04)
    for (a, b, c2, e2) in ((-w / 2, -d / 2, w / 2, -d / 2 + wall), (-w / 2, d / 2 - wall, w / 2, d / 2),
                           (-w / 2, -d / 2, -w / 2 + wall, d / 2), (w / 2 - wall, -d / 2, w / 2, d / 2)):
        m.bevel_box((a, th * 0.12, b), (c2, th, e2), "enamel_cream", 0.025)
    for sx in (-1, 1):
        for sz in (-1, 1):
            m.sphere((sx * (w / 2 - 0.12), th * 0.06, sz * (d / 2 - 0.1)), th * 0.07, "brass", segs=8, rings=5)
    m.cylinder((-w / 2 + 0.12, th, 0), 0.02, h - th, "chrome", segs=8)
    m.cylinder((-w / 2 + 0.12, h - 0.02, 0), 0.015, 0.12, "chrome", axis="x", segs=8)


def toilet(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    sh = h * 0.38
    m.lathe([(min(w, d) * 0.22, 0), (min(w, d) * 0.26, sh * 0.6), (min(w, d) * 0.36, sh)], (0, 0, d * 0.05), "ceramic", segs=16)
    m.cylinder((0, sh, d * 0.05), min(w, d) * 0.37, 0.03, "plastic_white", segs=16)
    m.bevel_box((-w * 0.42, sh * 0.9, -d / 2), (w * 0.42, h, -d / 2 + d * 0.28), "ceramic", 0.02)
    m.box((w * 0.2, h - 0.08, -d / 2 + d * 0.28), (w * 0.3, h - 0.06, -d / 2 + d * 0.28 + 0.03), "chrome")


def wash_basin(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    m.bevel_box((-w / 2, h * 0.3, -d / 2), (w / 2, h, d / 2), "ceramic", 0.03)
    m.box((-w * 0.35, h - 0.005, -d * 0.3), (w * 0.35, h + 0.001, d * 0.35), "steel_dark")


def basin_cabinet(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    m.box((-w / 2, 0.06, -d / 2), (w / 2, h - 0.08, d / 2), "paint_white")
    m.bevel_box((-w / 2 - 0.01, h - 0.08, -d / 2), (w / 2 + 0.01, h, d / 2 + 0.02), "ceramic", 0.02)
    m.box((-w * 0.32, h - 0.081, -d * 0.25), (w * 0.32, h + 0.001, d * 0.3), "steel_dark")
    for s in (-1, 1):
        m.box((s * w / 4 - w * 0.22, 0.1, d / 2), (s * w / 4 + w * 0.22, h - 0.12, d / 2 + 0.01), "paint_white")


def bath_small(ctx):
    """Taps, holders and small bathroom bits: chrome."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    c = (mn + mx) / 2
    p = c.copy()
    p[ax] = mn[ax]
    r = max(0.005, min(size[(ax + 1) % 3], size[(ax + 2) % 3]) / 2)
    ctx.m.cylinder(p, r, size[ax], "chrome", axis="xyz"[ax], segs=10)


def bath_mat(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    mx[1] = mn[1] + max(0.01, mx[1] - mn[1])
    ctx.m.bevel_box(mn, mx, "fabric_blue", 0.008)


def towel_rack(ctx):
    ctx.set_front(ctx.front_by_walls("+z"))
    w, h, d = ctx.dims
    m = ctx.m
    for s in (-1, 1):
        m.cylinder((s * (w / 2 - 0.02), 0, 0), 0.015, h, "chrome", segs=8)
    for y in (0.35, 0.7, 0.98):
        m.cylinder((-w / 2 + 0.02, h * y, 0), 0.012, w - 0.04, "chrome", axis="x", segs=8)
    m.box((-w * 0.35, h * 0.45, -0.02), (w * 0.35, h * 0.69, 0.02), "linen_white")


def drain(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    c = (mn + mx) / 2
    r = min((mx - mn)[0], (mx - mn)[2]) / 2
    ctx.m.cylinder((c[0], mn[1], c[2]), r, max(0.004, (mx - mn)[1]), "chrome", segs=14)


# ----------------------------------------------------------------------------------------------- car
def car_body(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    if w > d:
        ctx.set_front("+x")
        w, h, d = ctx.dims
    m = ctx.m
    paint = "car_paint"
    # lower body
    m.bevel_box((-w / 2, h * 0.18, -d / 2), (w / 2, h * 0.55, d / 2), paint, 0.06)
    # cabin
    m.bevel_box((-w * 0.45, h * 0.55, -d * 0.2), (w * 0.45, h * 0.95, d * 0.22), paint, 0.05)
    m.box((-w * 0.451, h * 0.6, -d * 0.17), (w * 0.451, h * 0.9, d * 0.19), "glass_dark")
    m.box((-w * 0.42, h * 0.6, d * 0.22), (w * 0.42, h * 0.9, d * 0.225), "glass_dark")
    m.box((-w * 0.42, h * 0.6, -d * 0.205), (w * 0.42, h * 0.9, -d * 0.2), "glass_dark")
    for s in (-1, 1):
        m.box((s * w * 0.32 - 0.12, h * 0.42, d / 2), (s * w * 0.32 + 0.12, h * 0.5, d / 2 + 0.01), "glass")
        m.box((s * w * 0.32 - 0.1, h * 0.42, -d / 2 - 0.01), (s * w * 0.32 + 0.1, h * 0.48, -d / 2), "plastic_red")
    m.box((-w / 2 - 0.01, h * 0.18, d / 2 - 0.05), (w / 2 + 0.01, h * 0.26, d / 2 + 0.04), "chrome")
    m.box((-w / 2 - 0.01, h * 0.18, -d / 2 - 0.04), (w / 2 + 0.01, h * 0.26, -d / 2 + 0.05), "chrome")


def car_wheels(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    if w > d:
        ctx.set_front("+x")
        w, h, d = ctx.dims
    m = ctx.m
    r = h / 2
    tw = min(0.22, w * 0.14)
    for sx in (-1, 1):
        for sz in (-1, 1):
            x0 = sx * w / 2 - (tw if sx > 0 else 0)
            m.cylinder((x0, r, sz * (d / 2 - r)), r, tw, "rubber", axis="x", segs=14)
            m.cylinder((x0 + (tw if sx > 0 else -0.002), r, sz * (d / 2 - r)), r * 0.55, 0.004, "chrome", axis="x", segs=12)


def car_door(ctx):
    thin = ctx.thin_axis()
    pc = ctx.parent_center()
    if pc is not None:
        ctx.set_front(ctx.front_away_from(pc, axes=(thin,)))
    else:
        ctx.set_front("+" + thin)
    w, h, d = ctx.dims
    m = ctx.m
    m.bevel_box((-w / 2, 0, -d / 2), (w / 2, h * 0.55, d / 2), "car_paint", 0.03)
    t = 0.04
    m.box((-w / 2, h * 0.55, -0.02), (-w / 2 + t, h, 0.02), "car_paint")
    m.box((w / 2 - t, h * 0.55, -0.02), (w / 2, h, 0.02), "car_paint")
    m.box((-w / 2, h - t, -0.02), (w / 2, h, 0.02), "car_paint")
    m.box((-w / 2 + t, h * 0.55, -0.005), (w / 2 - t, h - t, 0.005), "glass_dark")
    m.box((w * 0.25, h * 0.42, d / 2), (w * 0.4, h * 0.46, d / 2 + 0.02), "chrome")


def car_panel(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "car_paint", min(0.04, 0.3 * min(mx - mn)))


def car_seats(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    for s in (-1, 1):
        x0, x1 = (-w / 2, -0.03) if s < 0 else (0.03, w / 2)
        m.bevel_box((x0, 0, -d / 2), (x1, h * 0.35, d / 2), "car_interior", 0.04)
        m.bevel_box((x0, h * 0.35, -d / 2), (x1, h, -d / 2 + d * 0.22), "car_interior", 0.05)


def steering_wheel(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    c = (mn + mx) / 2
    R = max(size[(thin + 1) % 3], size[(thin + 2) % 3]) / 2 * 0.88
    ctx.m.torus(c, R, R * 0.09, "rubber", axis="xyz"[thin], segs=20, tube_segs=6)
    p = c.copy()
    p[thin] = mn[thin]
    ctx.m.cylinder(p, R * 0.2, size[thin], "plastic_black", axis="xyz"[thin], segs=10)
    other = [(thin + 1) % 3, (thin + 2) % 3]
    a, b = c.copy(), c.copy()
    a[other[0]] -= R
    b[other[0]] += R
    lo, hi = np.minimum(a, b), np.maximum(a, b)
    lo[other[1]] -= R * 0.05
    hi[other[1]] += R * 0.05
    lo[thin] -= R * 0.04
    hi[thin] += R * 0.04
    ctx.m.box(lo, hi, "plastic_black")


# ----------------------------------------------------------------------------------------------- coffin
def coffin_body(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    if w > d:
        ctx.set_front("+x")
        w, h, d = ctx.dims
    m = ctx.m
    # hexagonal coffin outline (wide at the shoulders)
    poly = [(-w * 0.32, -d / 2), (w * 0.32, -d / 2), (w / 2, d * 0.18), (w * 0.38, d / 2), (-w * 0.38, d / 2), (-w / 2, d * 0.18)]
    hh = h * 0.92
    m.extrude(poly, hh * 0.12, "wood_walnut", plane="xz", offset=0, centered=False)
    inner = [(x * 0.86, z * 0.94) for x, z in poly]
    # walls
    for i in range(len(poly)):
        a, b = poly[i], poly[(i + 1) % len(poly)]
        ia, ib = inner[i], inner[(i + 1) % len(poly)]
        m.extrude([a, b, ib, ia], hh, "wood_walnut", plane="xz", offset=0, centered=False)
    m.extrude(inner, hh * 0.02, "fabric_red", plane="xz", offset=hh * 0.12, centered=False)


def coffin_lid(ctx):
    thin_y = ctx.sy < min(ctx.sx, ctx.sz)
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    other = [i for i in range(3) if i != thin]
    a, b = other
    if size[a] > size[b]:
        a, b = b, a     # a: width, b: length
    poly = [(-0.32, -0.5), (0.32, -0.5), (0.5, 0.18), (0.38, 0.5), (-0.38, 0.5), (-0.5, 0.18)]
    c = (mn + mx) / 2
    pts = []
    for u, v in poly:
        pts.append((u * size[a], v * size[b]))
    plane = {(0, 1): "xy", (0, 2): "xz", (2, 1): "zy", (1, 0): "xy", (2, 0): "xz", (1, 2): "zy"}
    sub = Mesh()
    pl = "xy" if thin == 2 else ("xz" if thin == 1 else "zy")
    ua, va = {"xy": (0, 1), "xz": (0, 2), "zy": (2, 1)}[pl]
    pp = []
    for u, v in pts:
        q = [0.0, 0.0]
        if ua == a:
            q = (u, v)
        else:
            q = (v, u)
        pp.append(q)
    sub.extrude(pp, size[thin], "wood_walnut", plane=pl)
    ctx.m.add(sub, translate(*c))


def coffin_trim(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    lo, hi = mn.copy(), mx.copy()
    # a cross on the lid
    c = (mn + mx) / 2
    others = [i for i in range(3) if i != thin]
    a, b = others if size[others[0]] < size[others[1]] else others[::-1]
    v1 = c.copy(); v2 = c.copy()
    lo1 = c.copy(); hi1 = c.copy()
    lo1[a] -= size[a] * 0.06; hi1[a] += size[a] * 0.06
    lo1[b] -= size[b] * 0.32; hi1[b] += size[b] * 0.32
    lo1[thin] = mn[thin]; hi1[thin] = mx[thin]
    ctx.m.box(lo1, hi1, "brass")
    lo2 = c.copy(); hi2 = c.copy()
    lo2[a] -= size[a] * 0.22; hi2[a] += size[a] * 0.22
    lo2[b] += size[b] * 0.08; hi2[b] += size[b] * 0.18
    lo2[thin] = mn[thin]; hi2[thin] = mx[thin]
    ctx.m.box(lo2, hi2, "brass")


def coffin_handles(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    for t in (0.15, 0.5, 0.85):
        for side in (0, 1):
            c = (mn + mx) / 2
            c[ax] = mn[ax] + size[ax] * t
            o = [i for i in range(3) if i != ax and i != 1]
            if o:
                c[o[0]] = mn[o[0]] if side == 0 else mx[o[0]]
            lo = c - 0.03
            hi = c + 0.03
            lo[ax] -= 0.04
            hi[ax] += 0.04
            ctx.m.box(lo, hi, "brass")


# ----------------------------------------------------------------------------------------------- balloon
def balloon_envelope(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    prof = [(r * 0.12, 0), (r * 0.35, h * 0.12), (r * 0.75, h * 0.35), (r * 0.97, h * 0.58), (r, h * 0.7),
            (r * 0.9, h * 0.84), (r * 0.6, h * 0.95), (r * 0.15, h)]
    gores = 12
    cols = ["balloon_red", "balloon_yellow", "balloon_blue", "balloon_yellow"]
    for gi in range(gores):
        sub = Mesh()
        a0 = 2 * math.pi * gi / gores
        a1 = 2 * math.pi * (gi + 1) / gores
        for k in range(len(prof) - 1):
            (ra, ha), (rb, hb) = prof[k], prof[k + 1]
            for j in range(2):
                b0 = a0 + (a1 - a0) * j / 2
                b1 = a0 + (a1 - a0) * (j + 1) / 2
                pts = [(ra * math.cos(b0), ha, ra * math.sin(b0)), (ra * math.cos(b1), ha, ra * math.sin(b1)),
                       (rb * math.cos(b1), hb, rb * math.sin(b1)), (rb * math.cos(b0), hb, rb * math.sin(b0))]
                bm = (b0 + b1) / 2
                n = (math.cos(bm), (ra - rb) / max(hb - ha, 1e-6) * 0.5, math.sin(bm))
                sub.tri_fan(pts, n, cols[gi % len(cols)], [(0, 0), (1, 0), (1, 1), (0, 1)],
                            smooth_normals=[(math.cos(b0), 0.2, math.sin(b0)), (math.cos(b1), 0.2, math.sin(b1)),
                                            (math.cos(b1), 0.2, math.sin(b1)), (math.cos(b0), 0.2, math.sin(b0))])
        m.add(sub)
    m.cylinder((0, h - 0.02, 0), r * 0.15, 0.02, "balloon_red", segs=12)


def balloon_basket(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    bh = min(1.05, h * 0.42)
    t = 0.05
    m.box((-w / 2, 0, -d / 2), (w / 2, 0.06, d / 2), "wicker")
    for (a, b, c2, e2) in ((-w / 2, -d / 2, w / 2, -d / 2 + t), (-w / 2, d / 2 - t, w / 2, d / 2),
                           (-w / 2, -d / 2, -w / 2 + t, d / 2), (w / 2 - t, -d / 2, w / 2, d / 2)):
        m.box((a, 0, b), (c2, bh, e2), "wicker")
    m.torus((0, bh, 0), 0.01, 0.0, "wicker", segs=4, tube_segs=3) if False else None
    for (a, b, c2, e2) in ((-w / 2 - 0.02, -d / 2 - 0.02, w / 2 + 0.02, -d / 2 + t + 0.02), (-w / 2 - 0.02, d / 2 - t - 0.02, w / 2 + 0.02, d / 2 + 0.02),
                           (-w / 2 - 0.02, -d / 2, -w / 2 + t + 0.02, d / 2), (w / 2 - t - 0.02, -d / 2, w / 2 + 0.02, d / 2)):
        m.bevel_box((a, bh, b), (c2, bh + 0.06, e2), "leather_brown", 0.02)
    # burner frame and ropes up to the envelope
    fy = h * 0.8
    m.box((-w * 0.3, fy, -d * 0.3), (w * 0.3, fy + 0.04, d * 0.3), "steel_dark")
    for sx in (-1, 1):
        for sz in (-1, 1):
            p0 = np.array((sx * (w / 2 - 0.04), bh + 0.06, sz * (d / 2 - 0.04)))
            p1 = np.array((sx * w * 0.28, fy, sz * d * 0.28))
            v = p1 - p0
            L = float(np.linalg.norm(v))
            rope = Mesh()
            rope.cylinder((0, 0, 0), 0.012, L, "rope", segs=6)
            yaxis = v / L
            xaxis = np.cross(yaxis, (0, 0, 1))
            if np.linalg.norm(xaxis) < 1e-6:
                xaxis = np.array((1.0, 0, 0))
            xaxis /= np.linalg.norm(xaxis)
            zaxis = np.cross(xaxis, yaxis)
            M = np.eye(4)
            M[:3, 0], M[:3, 1], M[:3, 2], M[:3, 3] = xaxis, yaxis, zaxis, p0
            m.add(rope, M)
            p2 = np.array((sx * w * 0.6, h, sz * d * 0.6))
            v2 = p2 - p1
            L2 = float(np.linalg.norm(v2))
            r2 = Mesh()
            r2.cylinder((0, 0, 0), 0.008, L2, "rope", segs=6)
            ya = v2 / L2
            xa = np.cross(ya, (0, 0, 1))
            xa = xa / (np.linalg.norm(xa) or 1)
            za = np.cross(xa, ya)
            M2 = np.eye(4)
            M2[:3, 0], M2[:3, 1], M2[:3, 2], M2[:3, 3] = xa, ya, za, p1
            m.add(r2, M2)


def burner_part(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    c = (mn + mx) / 2
    p = c.copy()
    p[ax] = mn[ax]
    r = min(size[(ax + 1) % 3], size[(ax + 2) % 3]) / 2
    mat = "gas_red" if re.search(r"red", ctx.mat0) else ("steel" if re.search(r"window|metal|liger|lighe", ctx.mat0) else "steel_dark")
    ctx.m.cylinder(p, max(r, 0.004), size[ax], mat, axis="xyz"[ax], segs=12)


def gas_cylinder(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    c = (mn + mx) / 2
    r = min(size[(ax + 1) % 3], size[(ax + 2) % 3]) / 2
    L = size[ax]
    sub = Mesh()
    sub.lathe([(r * 0.6, 0), (r, L * 0.06), (r, L * 0.8), (r * 0.7, L * 0.92), (r * 0.25, L * 0.97), (r * 0.25, L)],
              (0, 0, 0), "gas_red", segs=16)
    sub.torus((0, L * 0.995, 0), r * 0.45, r * 0.06, "steel", segs=12, tube_segs=4)
    M = np.eye(4)
    if ax == 0:
        M = rot_z(-90)
    elif ax == 2:
        M = rot_x(90)
    p = c.copy()
    p[ax] = mn[ax]
    ctx.m.add(sub, translate(*p) @ M)


# ----------------------------------------------------------------------------------------------- items
def _flat_frame(ctx):
    """For flat items: returns (center, long axis, wide axis, thin axis, sizes)."""
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    order = list(np.argsort(size))
    thin, wide, long = order[0], order[1], order[2]
    return (mn + mx) / 2, long, wide, thin, size


def _plane_name(a, b):
    s = {frozenset((0, 1)): "xy", frozenset((0, 2)): "xz", frozenset((2, 1)): "zy"}[frozenset((a, b))]
    return s


def _extrude_on(ctx, poly_long_wide, mat, depth_scale=1.0):
    c, long, wide, thin, size = _flat_frame(ctx)
    pl = _plane_name(long, wide)
    ua, va = {"xy": (0, 1), "xz": (0, 2), "zy": (2, 1)}[pl]
    pts = []
    for L, W in poly_long_wide:
        p = {long: L * size[long], wide: W * size[wide]}
        pts.append((p[ua], p[va]))
    sub = Mesh()
    sub.extrude(pts, max(size[thin] * depth_scale, 0.002), mat, plane=pl)
    ctx.m.add(sub, translate(*c))


def key(ctx):
    ctx.raw = True
    mat = "gold" if re.search(r"gold|Gold", ctx.mat0 + ctx.name) else ("brass" if re.search(r"House|Master", ctx.mat0 + ctx.e["path"]) else "steel")
    # bow (ring-ish octagon) at one end, blade with teeth to the other
    bow = [(-0.5 + 0.18 + 0.18 * math.cos(a), 0.42 * math.sin(a) * 1.0) for a in [i * math.pi / 4 for i in range(8)]]
    blade = [(-0.16, -0.1), (0.5, -0.1), (0.5, 0.04), (0.42, 0.04), (0.42, 0.22), (0.34, 0.22), (0.34, 0.04),
             (0.24, 0.04), (0.24, 0.18), (0.16, 0.18), (0.16, 0.04), (-0.16, 0.04)]
    _extrude_on(ctx, bow, mat)
    _extrude_on(ctx, blade, mat, 0.8)


def hammer(ctx):
    ctx.raw = True
    c, long, wide, thin, size = _flat_frame(ctx)
    mn = ctx.fr.cmin
    # handle along the long axis, head across at the + end
    p = c.copy()
    p[long] = mn[long]
    r = min(size[wide], size[thin]) * 0.18
    ctx.m.cylinder(p, max(r, 0.01), size[long] * 0.85, "wood_raw", axis="xyz"[long], segs=10)
    lo, hi = c.copy(), c.copy()
    lo[long] = mn[long] + size[long] * 0.82
    hi[long] = mn[long] + size[long]
    lo[wide] -= size[wide] / 2
    hi[wide] += size[wide] / 2
    lo[thin] -= max(size[thin], 0.03) / 2
    hi[thin] += max(size[thin], 0.03) / 2
    ctx.m.bevel_box(lo, hi, "steel_dark", 0.006)


def bat(ctx):
    ctx.raw = True
    c, long, wide, thin, size = _flat_frame(ctx)
    mn = ctx.fr.cmin
    r = max(size[wide], size[thin]) / 2
    L = size[long]
    sub = Mesh()
    sub.lathe([(r * 0.45, 0), (r * 0.5, L * 0.03), (r * 0.32, L * 0.06), (r * 0.36, L * 0.45), (r * 0.8, L * 0.8),
               (r, L * 0.96), (r * 0.85, L)], (0, 0, 0), "wood_pine", segs=12)
    M = rot_z(-90) if long == 0 else (rot_x(90) if long == 2 else np.eye(4))
    p = c.copy()
    p[long] = mn[long]
    # which end is thick? keep the thick end where the original's geometry was wider (unknown): put it at +end
    ctx.m.add(sub, translate(*p) @ M)


def padlock_body(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "brass", 0.25 * float(np.min(mx - mn)))
    c = (mn + mx) / 2
    size = mx - mn
    thin = int(np.argmin(size))
    p = c.copy()
    p[thin] = mx[thin]
    ctx.m.cylinder(p, min(size) * 0.25, 0.002, "black", axis="xyz"[thin], segs=8)


def shackle(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    c = (mn + mx) / 2
    others = [i for i in range(3) if i != thin]
    R = min(size[others[0]], size[others[1]]) / 2 * 0.8
    r = max(0.004, R * 0.18)
    ctx.m.torus(c, R, r, "steel", axis="xyz"[thin], segs=16, tube_segs=6, arc=math.pi, start=0)


def chain(ctx):
    """Chain links along the longest axis (the cut chain and the hanging chains)."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmax(size))
    link = max(0.05, min(0.09, size[ax] / 10))
    n = max(2, int(size[ax] / (link * 0.8)))
    c = (mn + mx) / 2
    for i in range(n):
        p = c.copy()
        p[ax] = mn[ax] + (i + 0.5) * size[ax] / n
        axis = "xyz"[(ax + 1 + (i % 2)) % 3] if True else "y"
        ctx.m.torus(p, link * 0.35, link * 0.09, "steel_dark", axis=axis, segs=10, tube_segs=4)


def plank(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "wood_raw", 0.006)
    size = mx - mn
    ax = int(np.argmax(size))
    thin = int(np.argmin(size))
    for t in (0.06, 0.94):
        p = (mn + mx) / 2
        p[ax] = mn[ax] + size[ax] * t
        for side in (mn[thin], mx[thin]):
            q = p.copy()
            q[thin] = side
            ctx.m.cylinder(q - (0.006 if side == mn[thin] else 0) * np.eye(3)[thin], 0.008, 0.006, "iron_black", axis="xyz"[thin], segs=6)


def duct_tape(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    c = (mn + mx) / 2
    others = [i for i in range(3) if i != thin]
    R = min(size[others[0]], size[others[1]]) / 2
    p = c.copy()
    p[thin] = mn[thin]
    ctx.m.cylinder(p, R, size[thin], "tape_grey", axis="xyz"[thin], segs=18, caps=False)
    ctx.m.cylinder(p, R * 0.62, size[thin], "cardboard", axis="xyz"[thin], segs=18, caps=False)
    # top and bottom rings
    for side, s in ((mn[thin], -1), (mx[thin], 1)):
        q = c.copy()
        q[thin] = side
        ring = Mesh()
        segs = 18
        ax = thin
        u_ax, v_ax = [(1, 2), (2, 0), (0, 1)][ax]
        for i in range(segs):
            a0 = 2 * math.pi * i / segs
            a1 = 2 * math.pi * (i + 1) / segs
            pts = []
            for rr, aa in ((R, a0), (R, a1), (R * 0.62, a1), (R * 0.62, a0)):
                pp = q.copy()
                pp[u_ax] += rr * math.cos(aa)
                pp[v_ax] += rr * math.sin(aa)
                pts.append(pp)
            n = np.zeros(3)
            n[ax] = s
            ring.tri_fan(pts, n, "tape_grey", [(0, 0), (1, 0), (1, 1), (0, 1)])
        ctx.m.add(ring)


def tape_tab(ctx):
    raw_box(ctx, "tape_grey")


def code_note(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    size = mx - mn
    thin = int(np.argmin(size))
    c = (mn[thin] + mx[thin]) / 2
    mn[thin], mx[thin] = c - 0.0015, c + 0.0015
    others = [i for i in range(3) if i != thin]
    a, b = others
    pl = _plane_name(a, b)
    # paper with the code drawn on it (texture made at build time)
    lo, hi = mn, mx
    corners = []
    for (u, v) in ((0, 0), (1, 0), (1, 1), (0, 1)):
        p = lo.copy()
        p[a] = lo[a] + (hi[a] - lo[a]) * u
        p[b] = lo[b] + (hi[b] - lo[b]) * v
        p[thin] = hi[thin]
        corners.append(p)
    n = np.zeros(3)
    n[thin] = 1
    ctx.m.tri_fan(corners, n, "code_note", [(0, 0), (1, 0), (1, 1), (0, 1)])
    corners_b = [p.copy() for p in corners]
    for p in corners_b:
        p[thin] = lo[thin]
    ctx.m.tri_fan(corners_b, -n, "paper", [(0, 0), (1, 0), (1, 1), (0, 1)])


def digit(ctx):
    """The code padlock's number buttons: a raised square key with the number as a raised bar pattern."""
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.box(mn, mx, "plastic_black")


def small_metal(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    mat = "steel"
    j = " ".join(ctx.mats)
    if re.search(r"blue", j):
        mat = "plastic_blue"
    elif re.search(r"button", j):
        mat = "plastic_black"
    elif re.search(r"pliers", j):
        mat = "plastic_red" if (mx - mn).max() > 0.2 else "steel"
    elif re.search(r"lighter1", j):
        mat = "plastic_yellow"
    elif re.search(r"main2|back-screen", j):
        mat = "steel_dark"
    s = float(np.min(mx - mn))
    if s > 0.01:
        ctx.m.bevel_box(mn, mx, mat, s * 0.2)
    else:
        ctx.m.box(mn, mx, mat)


def small_round(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    ax = int(np.argmin(size)) if size.max() / max(size.min(), 1e-6) > 1.6 else 1
    c = (mn + mx) / 2
    p = c.copy()
    p[ax] = mn[ax]
    others = [i for i in range(3) if i != ax]
    r = min(size[others[0]], size[others[1]]) / 2
    ctx.m.cylinder(p, max(r, 0.002), max(size[ax], 0.002), "steel", axis="xyz"[ax], segs=10)


def wooden_wall(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    thin = int(np.argmin(size))
    long = int(np.argmax([size[i] if i != 1 else -1 for i in range(3)]))
    n = max(3, int(size[1] / 0.15))
    for i in range(n):
        lo, hi = mn.copy(), mx.copy()
        lo[1] = mn[1] + size[1] * i / n
        hi[1] = mn[1] + size[1] * (i + 1) / n - 0.01
        ctx.m.bevel_box(lo, hi, "wood_raw", 0.004)


def dynamite(ctx):
    ctx.raw = True
    c, long, wide, thin, size = _flat_frame(ctx)
    mn = ctx.fr.cmin
    for k in (-1, 0, 1):
        p = c.copy()
        p[long] = mn[long]
        p[wide] += k * size[wide] / 3
        ctx.m.cylinder(p, min(size[wide] / 6, size[thin] / 2), size[long], "plastic_red", axis="xyz"[long], segs=10)


def tree_trunk(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    r = min(w, d) / 2
    ctx.m.lathe([(r, 0), (r * 0.7, h * 0.3), (r * 0.5, h)], (0, 0, 0), "bark", segs=10)


def tree_crown(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    for i in range(3):
        y0 = h * (0.05 + i * 0.28)
        m.cylinder((0, y0, 0), r * (1 - i * 0.25), h * 0.42, "leaves" if i % 2 == 0 else "leaves_dark", segs=10, radius2=r * 0.05)


def bush(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    ctx.m.sphere((0, h / 2, 0), min(w, d) / 2, "leaves", segs=10, rings=6, squash=(1, h / max(min(w, d), 1e-3), 1))


def rocks(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    ctx.m.sphere((0, h / 2, 0), min(w, d) / 2, "rock", segs=8, rings=5, squash=(1, h / max(min(w, d), 1e-3), 1.1))


def grass_tuft(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    for a in (0, 60, 120):
        b = Mesh()
        b.quad((-w / 2, 0, 0), (w / 2, 0, 0), (w / 2, h, 0), (-w / 2, h, 0), (0, 0, 1), "leaves")
        b.quad((-w / 2, 0, 0), (-w / 2, h, 0), (w / 2, h, 0), (w / 2, 0, 0), (0, 0, -1), "leaves")
        m.add(b, rot_y(a))


def column(ctx):
    ctx.set_front("+z")
    w, h, d = ctx.dims
    m = ctx.m
    r = min(w, d) / 2
    m.box((-r, 0, -r), (r, h * 0.06, r), "plaster_white")
    m.cylinder((0, h * 0.06, 0), r * 0.8, h * 0.88, "plaster_white", segs=16)
    m.box((-r, h * 0.94, -r), (r, h, r), "plaster_white")


def balustrade(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    size = mx - mn
    long = 0 if size[0] >= size[2] else 2
    other = 2 - long
    lo, hi = mn.copy(), mx.copy()
    lo[1] = mx[1] - min(0.08, size[1] * 0.12)
    ctx.m.bevel_box(lo, hi, "plaster_white", 0.01)
    lo2, hi2 = mn.copy(), mx.copy()
    hi2[1] = mn[1] + min(0.08, size[1] * 0.12)
    ctx.m.box(lo2, hi2, "plaster_white")
    n = max(2, int(size[long] / 0.16))
    c = (mn + mx) / 2
    for i in range(n):
        p = c.copy()
        p[long] = mn[long] + size[long] * (i + 0.5) / n
        p[1] = mn[1] + min(0.08, size[1] * 0.12)
        ctx.m.lathe([(0.04, 0), (0.05, size[1] * 0.2), (0.025, size[1] * 0.45), (0.045, size[1] * 0.7), (0.03, size[1] * 0.76)],
                    p, "plaster_white", segs=8)


def mansion_part(ctx):
    """Big parts of the ending scene's house: clean boxes in plaster / roof / glass."""
    j = " ".join(ctx.mats) + " " + ctx.name
    mat = "plaster_white"
    if re.search(r"Window", j):
        mat = "glass_dark"
    elif re.search(r"Floor|Base", j):
        mat = "stone_wall"
    elif re.search(r"Roof", j):
        mat = "roof_tiles"
    elif re.search(r"Deco|Column", j):
        mat = "plaster_cream"
    raw_box(ctx, mat)


def generic_wood(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin, ctx.fr.cmax
    ctx.m.bevel_box(mn, mx, "wood_walnut", min(0.01, 0.2 * float(np.min(mx - mn))))


def columns(ctx):
    """Detailed shapes without a dedicated builder: wooden blocks that follow the original's footprint and heights
    (a grid of columns from the lowest to the highest surface in each cell), so tables keep their legs and sparse
    parts stay sparse."""
    ctx.raw = True
    hmx = np.array(ctx.e.get("hmap_max") or [], float)
    hmn = np.array(ctx.e.get("hmap_min") or [], float)
    mat = surface_material(ctx, "wood_walnut")
    if hmx.ndim != 2 or hmx.size == 0:
        return surface(ctx)
    n = hmx.shape[0]
    # local x / z -> canonical axes
    fr = ctx.fr
    lo_l = np.array(ctx.e["local_min"], float) * fr.scale
    hi_l = np.array(ctx.e["local_max"], float) * fr.scale
    for r in range(n):
        for c in range(n):
            if hmx[r, c] < 0:
                continue
            h0 = max(0.0, hmn[r, c]) if hmn[r, c] >= 0 else 0.0
            h1 = hmx[r, c]
            a = lo_l.copy()
            b = hi_l.copy()
            sz = hi_l - lo_l
            a[0] = lo_l[0] + sz[0] * c / n
            b[0] = lo_l[0] + sz[0] * (c + 1) / n
            a[2] = lo_l[2] + sz[2] * r / n
            b[2] = lo_l[2] + sz[2] * (r + 1) / n
            a[1] = lo_l[1] + sz[1] * h0
            b[1] = lo_l[1] + sz[1] * h1
            if b[1] - a[1] < 0.02:
                a[1] = b[1] - 0.02
            ca = fr.canon_of_local_metric(a)
            cb = fr.canon_of_local_metric(b)
            ctx.m.box(np.minimum(ca, cb), np.maximum(ca, cb), mat, T(mat))


def chair_frame(ctx):
    """Dining chair frame (legs, rails and a slatted back); the seat board is a separate object."""
    f = ctx.front_by_height(None) or "+z"
    ctx.set_front(f)
    w, h, d = ctx.dims
    m = ctx.m
    mat = "wood_walnut"
    leg = min(0.05, w * 0.08)
    seat = h * 0.45
    for sx in (-1, 1):
        x = sx * (w / 2 - leg / 2)
        m.box((x - leg / 2, 0, d / 2 - leg), (x + leg / 2, seat, d / 2), mat)
        m.box((x - leg / 2, 0, -d / 2), (x + leg / 2, h, -d / 2 + leg), mat)
        m.box((x - leg / 2, seat * 0.3, -d / 2 + leg), (x + leg / 2, seat * 0.3 + leg * 0.6, d / 2 - leg), mat)
    m.box((-w / 2 + leg, seat - leg, d / 2 - leg), (w / 2 - leg, seat, d / 2), mat)
    m.box((-w / 2 + leg, seat - leg, -d / 2), (w / 2 - leg, seat, -d / 2 + leg), mat)
    for y in (h * 0.62, h * 0.8, h * 0.97):
        m.box((-w / 2 + leg, y - 0.05, -d / 2 + 0.005), (w / 2 - leg, y, -d / 2 + leg - 0.005), mat)


def chair_seat(ctx):
    ctx.raw = True
    ctx.m.bevel_box(ctx.fr.cmin, ctx.fr.cmax, "wood_walnut", 0.008)


def backdrop(ctx):
    ctx.raw = True
    mn, mx = ctx.fr.cmin.copy(), ctx.fr.cmax.copy()
    for i in range(3):
        if mx[i] - mn[i] < 0.01:
            mn[i] -= 0.01
            mx[i] += 0.01
    ctx.m.box(mn, mx, "leaves_dark")


# ----------------------------------------------------------------------------------------------- rules
# (name regex, material regex, path regex, builder) - first match wins
RULES = [
    # characters and invisible helpers are handled elsewhere
    (r"^(playerrromtableInvisible|invisible_)", None, None, "surface"),
    # doors and openings
    (r"^Door$|^Doorshed$", None, r"Door_Pivot", "house_door"),
    (r"^doorlockplank$|^Plank$|^Padlock Plank$|^Plank 2$", None, None, "plank"),
    (r"^door_cut1$", None, None, "garage_door"),
    (r"^RollingShutter$", None, None, "rolling_shutter"),
    (r"^Window_Frame", None, None, "window_frame"),
    (r"^Glass_Glass", None, None, "window_glass"),
    (r"^door_block", None, None, "door_frame_post"),
    # kitchen
    (r"^Cupboard_.*Door|^Cupboard_Big_door", None, None, "cabinet_door"),
    (r"^Cupboard_(Upper|Lower)_0\d$|^Cupboard_Big$|^(bathroom|garage|nosfera)_cupboard$", None, None, "cabinet_body"),
    (r"^0\d_Drawer_0\d$|^Oven_Drawer$", None, None, "drawer_box"),
    (r"^Drawer_0\d_Body$", None, None, "drawer_chest_body"),
    (r"^Oven$", None, None, "oven_front"),
    (r"^Cooktop$", None, None, "cooktop"),
    (r"^Controller", None, None, "knob"),
    (r"^Syphon$", None, None, "sink_basin"),
    (r"^Tap$", None, None, "faucet"),
    (r"^Air_Vent$", None, None, "range_hood"),
    (r"^Table$", None, r"^Kitchen", "countertop"),
    (r"^Basement$", None, None, "plinth"),
    (r"^KitchenSet0\d_0$", None, None, "kitchen_unit"),
    (r"^KitchenSet0\d_1$", None, None, "surface"),
    (r"^KitchenSet0\d_2$", r"F2244", None, "armchair"),
    (r"^KitchenSet0\d_2$", None, None, "knob"),
    # bedrooms and living room
    (r"^bed$|^playerbed$", None, None, "bed"),
    (r"^Sofa_SA$", None, None, "armchair"),
    (r"^Sofa_(fa|wo)_low", None, None, "sofa"),
    (r"^Box00[5-9]$|^Box01[0-3]$", None, r"Sofa", "cushion"),
    (r"^Box004$", None, r"Sofa", "sofa_part"),
    (r"^playerrromtable(death)?$", None, None, "desk"),
    (r"^BasicTable_Low$", None, None, "table"),
    (r"^table_hightop$", None, None, "round_stool"),
    (r"^defaultMaterial$", r"small_table|1001", None, "small_table_part"),
    (r"^defaultMaterial$", r"laamp_cover", None, "lamp_shade"),
    (r"^defaultMaterial$", r"lamp_table", None, "lamp_table"),
    (r"^defaultMaterial$", r"watch", None, "clock"),
    (r"^Object_2$", r"^lamp", None, "floor_lamp"),
    (r"^lampoutsideshade$", None, None, "outdoor_lamp"),
    (r"^Base$", r"WoodFine", r"Bookshelf", "bookshelf"),
    (r"^Base$", None, None, "bookshelf"),
    (r"^BookCollection", None, None, "books"),
    (r"^Book0", None, None, "book"),
    (r"^default$", r"beowulf", None, "book"),
    (r"^default$", r"slen_books", None, "secret_book"),
    (r"^Vase", None, None, "vase"),
    (r"^tv_low", None, None, "tv_body"),
    (r"^(tv-b|h1|h2|h3|sign|top)_low_tv", None, None, "tv_part"),
    (r"^tvcabinet5(death)?$", None, None, "tv_cabinet"),
    (r"^default$", r"tabletext12", r"Cabinet_empty", "wardrobe"),
    (r"^default$", r"TexturesCom_Wood", None, "table"),
    (r"^default$", r"stair_wood", None, "wardrobe"),
    (r"^default$", r"bathroom_floor1", None, "basin_cabinet"),
    (r"^Storage_cabinet$", None, None, "storage_cabinet"),
    (r"^metalshelf$", None, None, "metal_shelf"),
    (r"^prayermat", None, None, "rug"),
    (r"^artframe$", None, None, "painting"),
    (r"^Esfera$", None, None, "drawer_box"),
    (r"^Combined_Mesh \(root: scene\) 8_5$", None, None, "bedside_body"),
    (r"^Cube$", r"tabletext12", r"playerrromtable", "tabletop"),
    # storage, garage, outside
    (r"^barrel_|^mesh0_Barrels", None, None, "barrel"),
    (r"^crate_\d$", None, None, "crate"),
    (r"^Box_(Box|Edges)_0$", None, None, "storage_box"),
    (r"^Box_Lock and Hinges_0$", None, None, "small_metal"),
    (r"^Boxes Scene", None, None, "box_pile"),
    (r"^Plank \d$", None, r"Bench", "bench_plank"),
    (r"^Beams \d$", None, None, "bench_legs"),
    (r"^Bricks_low", None, None, "well_bricks"),
    (r"^Roller_low", None, None, "well_roller"),
    (r"^(SideRoof|RoofWood)_low", None, None, "gable_roof"),
    (r"^TopRoof_low", None, None, "flat_roof"),
    (r"^Fence_lp$", None, None, "fence_panel"),
    (r"^Pillar_Straight", None, None, "fence_post"),
    (r"^bell2$", None, None, "bell"),
    (r"^lever_base$", None, None, "lever_base"),
    (r"^lever$|^LeverHandle", None, None, "lever_stick"),
    (r"^WoodenWall$", None, None, "wooden_wall"),
    (r"^Dynamite$", None, None, "dynamite"),
    # bathroom
    (r"^SM_Bathtub", None, None, "bathtub"),
    (r"^PolyMesh_1_1$", None, None, "toilet"),
    (r"^PolyMesh_2$", None, None, "wash_basin"),
    (r"^PolyMesh_1_7$", None, None, "bath_mat"),
    (r"^PolyMesh", None, None, "bath_small"),
    (r"^towel_rack$", None, None, "towel_rack"),
    (r"^Drain(cover)?$|^fawcetcollar$", None, None, "drain"),
    # car
    (r"^body$", r"carred", None, "car_body"),
    (r"^wheels$", None, None, "car_wheels"),
    (r"^door_(fl|fr|rl|rr)$", None, None, "car_door"),
    (r"^(hood|trunk)$", None, None, "car_panel"),
    (r"^seats$", None, None, "car_seats"),
    (r"^steer$", None, None, "steering_wheel"),
    # coffin
    (r"^Base_base_wood_0$", None, None, "coffin_body"),
    (r"^Coffin Gate$", None, None, "coffin_lid"),
    (r"^(Lid_lid_gold_0|Base_base_gold_0)$", None, None, "coffin_trim"),
    (r"^handles_handle_0$", None, None, "coffin_handles"),
    # balloon
    (r"^balloon$", None, None, "balloon_envelope"),
    (r"^basket$", None, None, "balloon_basket"),
    (r"^Object_4$", r"red_cyinder", None, "gas_cylinder"),
    (r"^Object_[2-5]$", None, r"HotAirBalloon|Cylinder", "burner_part"),
    # items
    (r"^(CarKey|Gold Key)$", None, None, "key"),
    (r"^Object_(66|70)$", None, None, "key"),
    (r"^Object_62$", None, None, "hammer"),
    (r"^BatBloody$", None, None, "bat"),
    (r"^Torus$", r"Material\.001", r"Padlock", "shackle"),
    (r"^Torus$", None, r"Chain", "chain"),
    (r"^Chain$", None, None, "chain"),
    (r"^Torus$", None, None, "shackle"),
    (r"^Padlock Code$", None, None, "code_note"),
    (r"^\d$", None, r"PadlockCode", "digit"),
    (r"^Cylinder$", r"Duct", None, "duct_tape"),
    (r"^Cube_Cube$", None, None, "tape_tab"),
    (r"^Cube$", r"buttons|blue_color|met2|main2|large_pliers|lighermetal|lighter1", None, "small_metal"),
    (r"^Cylinder$|^Vert$", r"lighermetal", None, "small_round"),
    (r"^Cylinder$", None, None, "small_round"),
    # ending scene (outdoors)
    (r"Tree_Trunk", None, None, "tree_trunk"),
    (r"Tree_Branches|Background_Tree", None, None, "tree_crown"),
    (r"^Rocks", None, None, "rocks"),
    (r"^grassAS", None, None, "grass_tuft"),
    (r"Columns", None, None, "column"),
    (r"Balustrade|^Circle\.\d+_Balustrade", None, None, "balustrade"),
    (r"^Main(\.\d+)?_|Deco_0$|^Object_1[234]$", None, None, "mansion_part"),
    (r"^Plane$", r"istockphoto", None, "backdrop"),
    (r"^Plane$", None, None, "surface"),
    (r"^Backplanks_2_low$", None, None, "chair_frame"),
    (r"^Seat_low$", None, None, "chair_seat"),
    # everything box-shaped that is left: walls, floors, steps, trims; detailed leftovers follow their footprint
    (None, None, None, "surface_or_columns"),
]
