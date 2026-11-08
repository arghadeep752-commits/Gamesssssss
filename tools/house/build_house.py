"""
Procedural modern two-storey house with a modular kitchen, furnished rooms and a landscaped plot.

Run inside Blender (bakes the lighting and renders previews):
    blender -b --factory-startup -P tools/house/build_house.py -- <out_dir> [--samples N] [--quick]
Run with plain Python for a quick geometry export without the bake:
    python3 tools/house/build_house.py <out_dir>
"""
import os
import sys
import time
import math

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import numpy as np
import hlib as H
from hlib import Geo, material, place, emit, log
from arch import Wall, build_walls, window, door, straight_stair, glass_railing, downlight, floor, ceiling, \
    rect_subtract, vrect, hrect, srect, P
import furn as F

# ------------------------------------------------------------------------------------------ levels
T_EXT, T_INT = 0.25, 0.15
Z_GF, Z_GC = 0.30, 3.30          # ground floor finished level / ceiling
Z_FF, Z_FC = 3.50, 6.50          # first floor finished level / ceiling
Z_ROOF, Z_PAR = 6.75, 7.25
HX, HY = 14.0, 10.0
H_GF, H_FF = Z_GC - Z_GF, Z_FC - Z_FF
PLOT = (-6.0, -11.0, 22.0, 15.0)     # inside faces of the compound wall
STAIR_Y0, STAIR_Y1 = 8.55, 9.75
STAIR_X0 = 2.75
RISERS, TREAD = 18, 0.28
VOID = (2.45, STAIR_Y0, STAIR_X0 + (RISERS - 1) * TREAD, STAIR_Y1)   # stair void through the first floor


# ------------------------------------------------------------------------------------------ materials
def make_materials():
    t = {}
    log("generating textures")
    t["paint"] = H.tex_paint("paint", (0.93, 0.915, 0.885), seed=1)
    t["paint_accent"] = H.tex_paint("paint_accent", (0.74, 0.70, 0.64), seed=2)
    t["ceiling"] = H.tex_paint("ceiling", (0.95, 0.95, 0.94), seed=4, amount=0.015)
    t["render"] = H.tex_render("render", (0.90, 0.89, 0.86))
    t["plinth_ext"] = H.tex_concrete("plinth_ext", (0.30, 0.30, 0.31), seed=5)
    t["marble_floor"] = H.tex_marble_tiles("marble_floor", (0.93, 0.92, 0.895), (0.66, 0.64, 0.62), tiles=2, seed=12)
    t["oak_floor"] = H.tex_planks("oak_floor", (0.62, 0.47, 0.33), planks=8, rows=2, seed=33, contrast=0.6)
    t["bath_floor"] = H.tex_marble_tiles("bath_floor", (0.52, 0.52, 0.52), (0.36, 0.36, 0.37), tiles=2, seed=14,
                                         grout=(0.42, 0.42, 0.42), vein_amount=0.5)
    t["bath_wall"] = H.tex_marble_tiles("bath_wall", (0.88, 0.87, 0.85), (0.62, 0.6, 0.58), tiles=2, seed=15,
                                        grout=(0.78, 0.77, 0.75), vein_amount=0.55)
    t["subway"] = H.tex_subway("subway", (0.95, 0.95, 0.93))
    t["walnut"] = H.tex_veneer("walnut", (0.36, 0.24, 0.16), seed=41)
    t["oak"] = H.tex_veneer("oak", (0.68, 0.53, 0.38), seed=42)
    t["deck"] = H.tex_boards("deck", (0.52, 0.36, 0.23), boards=6, seed=101)
    t["cladding"] = H.tex_boards("cladding", (0.50, 0.34, 0.21), boards=8, seed=102, horizontal=True)
    t["sofa"] = H.tex_fabric("fabric_sofa", (0.62, 0.60, 0.56), seed=51)
    t["sofa_alt"] = H.tex_fabric("fabric_sage", (0.42, 0.48, 0.43), seed=52)
    t["chair"] = H.tex_fabric("fabric_cream", (0.80, 0.76, 0.68), seed=53, weave=90, heather=0.14)
    t["linen"] = H.tex_fabric("linen", (0.94, 0.93, 0.9), seed=54, weave=160)
    t["throw"] = H.tex_fabric("throw", (0.60, 0.40, 0.27), seed=55, weave=60, heather=0.12)
    t["headboard"] = H.tex_fabric("headboard", (0.62, 0.58, 0.52), seed=56)
    t["pillow_a"] = H.tex_fabric("pillow_sage", (0.45, 0.52, 0.46), seed=57)
    t["pillow_b"] = H.tex_fabric("pillow_ochre", (0.80, 0.64, 0.42), seed=58)
    t["towel"] = H.tex_fabric("towel", (0.9, 0.88, 0.84), seed=59, weave=70, heather=0.15)
    t["curtain"] = H.tex_fabric("curtain", (0.93, 0.92, 0.88), seed=60, weave=140, heather=0.04)
    t["rug"] = H.tex_rug("rug")
    t["quartz"] = H.tex_slab("quartz", (0.95, 0.945, 0.93), (0.66, 0.64, 0.62), seed=21, vein_amount=0.6)
    t["marble"] = H.tex_slab("marble_top", (0.95, 0.94, 0.92), (0.42, 0.42, 0.44), seed=22, scale=2.4)
    t["steel"] = H.tex_brushed("steel", (0.78, 0.78, 0.79))
    t["grass"] = H.tex_grass("grass")
    t["pavers"] = H.tex_pavers("pavers", (0.62, 0.6, 0.57))
    t["stone_slab"] = H.tex_concrete("stone_slab", (0.72, 0.71, 0.68), seed=7, rough=0.6)
    t["concrete"] = H.tex_concrete("concrete", (0.66, 0.65, 0.63), seed=8)
    t["asphalt"] = H.tex_asphalt("asphalt")
    t["ledgestone"] = H.tex_ledgestone("ledgestone")
    t["leaf"] = H.tex_leaf("leaf", (0.20, 0.36, 0.12))
    t["foliage"] = H.tex_foliage("foliage", (0.20, 0.34, 0.13))
    t["art1"] = H.tex_art("art1", [(0.92, 0.89, 0.83), (0.78, 0.55, 0.38), (0.36, 0.42, 0.4), (0.85, 0.75, 0.6), (0.2, 0.22, 0.24)], seed=151, style=0)
    t["art2"] = H.tex_art("art2", [(0.86, 0.8, 0.7), (0.72, 0.62, 0.5), (0.5, 0.56, 0.6), (0.3, 0.36, 0.42)], seed=152, style=1)
    t["art3"] = H.tex_art("art3", [(0.93, 0.92, 0.9), (0.1, 0.1, 0.1), (0.75, 0.42, 0.25), (0.45, 0.5, 0.45)], seed=153, style=2)

    m = {}

    def mat(key, *a, **k):
        m[key] = material(key, *a, **k)
    # architecture
    mat("paint", (0.93, 0.915, 0.885), t["paint"], rough=0.85, tile=2.0)
    mat("paint_accent", (0.74, 0.7, 0.64), t["paint_accent"], rough=0.85, tile=2.0)
    mat("ceiling", (0.95, 0.95, 0.94), t["ceiling"], rough=0.9, tile=2.0)
    mat("render", (0.9, 0.89, 0.86), t["render"], rough=0.9, tile=2.5)
    mat("plinth_ext", (0.3, 0.3, 0.31), t["plinth_ext"], rough=0.85, tile=1.5)
    mat("cladding", (0.5, 0.34, 0.21), t["cladding"], rough=0.7, tile=1.2)
    mat("ledgestone", (0.6, 0.58, 0.55), t["ledgestone"], rough=0.9, tile=1.8)
    mat("trim_dark", (0.22, 0.22, 0.23), rough=0.6)
    mat("coping", (0.8, 0.79, 0.77), t["concrete"], rough=0.8, tile=1.5)
    mat("roof", (0.52, 0.52, 0.52), t["concrete"], rough=0.9, tile=2.0)
    mat("floor_marble", (0.93, 0.92, 0.9), t["marble_floor"], rough=0.12, tile=1.6)
    mat("floor_oak", (0.6, 0.45, 0.31), t["oak_floor"], rough=0.45, tile=1.28)
    mat("floor_bath", (0.52, 0.52, 0.52), t["bath_floor"], rough=0.35, tile=1.2)
    mat("wall_bath", (0.88, 0.87, 0.85), t["bath_wall"], rough=0.18, tile=1.2)
    mat("subway", (0.95, 0.95, 0.93), t["subway"], rough=0.12, tile=0.6)
    mat("skirting", (0.94, 0.94, 0.93), rough=0.45)
    mat("frame", (0.12, 0.12, 0.13), rough=0.45, metal=0.4)
    mat("glass", (0.78, 0.86, 0.88), rough=0.02, alpha=0.16, kind="glass", baked=False)
    mat("glass_rail", (0.72, 0.86, 0.84), rough=0.02, alpha=0.22, kind="glass", baked=False)
    mat("glass_tint", (0.3, 0.32, 0.33), rough=0.05, alpha=0.55, kind="glass", baked=False)
    mat("mirror", (0.92, 0.92, 0.92), rough=0.02, metal=1.0, kind="mirror")
    mat("sill", (0.74, 0.73, 0.7), t["stone_slab"], rough=0.45, tile=1.0)
    mat("door_leaf", (0.36, 0.24, 0.16), t["walnut"], rough=0.45, tile=1.2)
    mat("door_frame", (0.36, 0.24, 0.16), t["walnut"], rough=0.45, tile=1.2)
    mat("threshold", (0.94, 0.94, 0.92), t["marble"], rough=0.15, tile=0.8)
    mat("groove", (0.1, 0.07, 0.05), rough=0.7)
    mat("handle", (0.05, 0.05, 0.05), rough=0.4, metal=0.6)
    mat("riser", (0.93, 0.92, 0.9), rough=0.6)
    mat("tread", (0.68, 0.53, 0.38), t["oak"], rough=0.4, tile=1.0)
    mat("stair_side", (0.93, 0.915, 0.885), t["paint"], rough=0.85, tile=2.0)
    mat("rail", (0.06, 0.06, 0.06), rough=0.35, metal=0.7)
    mat("trim_white", (0.95, 0.95, 0.95), rough=0.4)
    mat("lamp", (1.0, 0.95, 0.86), emission=(1.0, 0.9, 0.76), emission_strength=6.0, rough=0.5)
    mat("lamp_strip", (1.0, 0.95, 0.86), emission=(1.0, 0.9, 0.76), emission_strength=4.0, rough=0.5)
    mat("bulb", (1.0, 0.95, 0.86), emission=(1.0, 0.86, 0.66), emission_strength=12.0, rough=0.5)
    mat("shade", (0.92, 0.89, 0.82), t["linen"], emission=(1.0, 0.85, 0.65), emission_strength=0.6, rough=0.9, tile=0.5)
    mat("shade_inner", (0.95, 0.92, 0.85), emission=(1.0, 0.85, 0.65), emission_strength=2.5, rough=0.9)
    mat("display", (0.1, 0.1, 0.1), emission=(0.75, 0.85, 1.0), emission_strength=0.8)
    mat("screen", (0.015, 0.015, 0.018), rough=0.05)
    mat("screen_on", (0.2, 0.22, 0.25), emission=(0.62, 0.72, 0.85), emission_strength=1.2, rough=0.1)
    mat("tv_frame", (0.03, 0.03, 0.03), rough=0.4)
    # materials and metals
    mat("metal_black", (0.05, 0.05, 0.05), rough=0.45, metal=0.6)
    mat("steel", (0.78, 0.78, 0.79), t["steel"], rough=0.3, metal=1.0, tile=0.6)
    mat("steel_dark", (0.4, 0.4, 0.41), rough=0.4, metal=1.0)
    mat("chrome", (0.86, 0.86, 0.87), rough=0.08, metal=1.0)
    mat("brass", (0.8, 0.62, 0.33), rough=0.3, metal=1.0)
    mat("aluminium", (0.72, 0.73, 0.74), rough=0.35, metal=1.0)
    mat("black_glass", (0.02, 0.02, 0.02), rough=0.05)
    mat("oven_window", (0.008, 0.008, 0.008), rough=0.05)
    mat("hob_glass", (0.012, 0.012, 0.012), rough=0.05)
    mat("burner", (0.28, 0.28, 0.29), rough=0.4, metal=0.8)
    mat("cast_iron", (0.05, 0.05, 0.05), rough=0.7, metal=0.3)
    mat("filter", (0.5, 0.5, 0.52), rough=0.5, metal=1.0)
    mat("drain", (0.05, 0.05, 0.05), rough=0.5)
    mat("sink", (0.74, 0.74, 0.75), t["steel"], rough=0.25, metal=1.0, tile=0.6)
    mat("quartz", (0.95, 0.945, 0.93), t["quartz"], rough=0.12, tile=1.6)
    mat("marble", (0.95, 0.94, 0.92), t["marble"], rough=0.1, tile=0.8)
    mat("walnut", (0.36, 0.24, 0.16), t["walnut"], rough=0.45, tile=1.0)
    mat("oak", (0.68, 0.53, 0.38), t["oak"], rough=0.45, tile=1.0)
    mat("teak", (0.52, 0.36, 0.23), t["deck"], rough=0.6, tile=0.9)
    mat("cab_low", (0.21, 0.28, 0.25), rough=0.55)
    mat("cab_up", (0.91, 0.9, 0.87), rough=0.35)
    mat("carcass", (0.86, 0.85, 0.83), rough=0.6)
    mat("plinth", (0.07, 0.07, 0.07), rough=0.6)
    mat("handle_black", (0.04, 0.04, 0.04), rough=0.35, metal=0.7)
    mat("wardrobe", (0.68, 0.53, 0.38), t["oak"], rough=0.45, tile=1.2)
    # soft furnishings
    mat("sofa", (0.62, 0.6, 0.56), t["sofa"], rough=0.95, tile=0.5)
    mat("sofa_alt", (0.42, 0.48, 0.43), t["sofa_alt"], rough=0.95, tile=0.5)
    mat("chair", (0.8, 0.76, 0.68), t["chair"], rough=0.95, tile=0.4)
    mat("linen", (0.94, 0.93, 0.9), t["linen"], rough=0.95, tile=0.6)
    mat("duvet", (0.95, 0.94, 0.92), t["linen"], rough=0.95, tile=0.6)
    mat("mattress", (0.95, 0.95, 0.94), t["linen"], rough=0.95, tile=0.6)
    mat("pillow", (0.95, 0.94, 0.92), t["linen"], rough=0.95, tile=0.5)
    mat("pillow_a", (0.45, 0.52, 0.46), t["pillow_a"], rough=0.95, tile=0.4)
    mat("pillow_b", (0.8, 0.64, 0.42), t["pillow_b"], rough=0.95, tile=0.4)
    mat("throw", (0.6, 0.4, 0.27), t["throw"], rough=0.95, tile=0.5)
    mat("headboard", (0.62, 0.58, 0.52), t["headboard"], rough=0.95, tile=0.5)
    mat("curtain", (0.93, 0.92, 0.88), t["curtain"], rough=0.95, tile=0.8)
    mat("towel", (0.9, 0.88, 0.84), t["towel"], rough=0.95, tile=0.4)
    mat("rug", (0.7, 0.68, 0.64), t["rug"], rough=0.95, tile=1.0)
    mat("leather", (0.48, 0.32, 0.22), rough=0.5)
    mat("fabric_dark", (0.14, 0.14, 0.15), rough=0.9)
    mat("mesh", (0.09, 0.09, 0.1), rough=0.8)
    mat("cushion_out", (0.88, 0.86, 0.82), t["linen"], rough=0.95, tile=0.5)
    # decor
    mat("ceramic_white", (0.92, 0.91, 0.88), rough=0.15)
    mat("ceramic_dark", (0.2, 0.19, 0.18), rough=0.3)
    mat("white_gloss", (0.95, 0.95, 0.95), rough=0.12)
    mat("pot", (0.85, 0.83, 0.78), rough=0.6)
    mat("pot_dark", (0.2, 0.2, 0.2), rough=0.6)
    mat("soil", (0.17, 0.12, 0.08), rough=1.0)
    mat("bark", (0.33, 0.25, 0.18), rough=0.9)
    mat("leaf", (0.2, 0.36, 0.12), t["leaf"], rough=0.55, tile=0.25)
    mat("leaf_snake", (0.22, 0.36, 0.16), t["leaf"], rough=0.5, tile=0.3)
    mat("foliage", (0.2, 0.34, 0.13), t["foliage"], rough=0.85, tile=1.0)
    mat("hedge", (0.19, 0.33, 0.12), t["foliage"], rough=0.85, tile=0.8)
    mat("frame_black", (0.05, 0.05, 0.05), rough=0.5)
    mat("passepartout", (0.95, 0.95, 0.93), rough=0.9)
    mat("art1", (1, 1, 1), t["art1"], rough=0.8)
    mat("art2", (1, 1, 1), t["art2"], rough=0.8)
    mat("art3", (1, 1, 1), t["art3"], rough=0.8)
    for k, c in (("book_a", (0.55, 0.16, 0.12)), ("book_b", (0.13, 0.25, 0.4)), ("book_c", (0.86, 0.81, 0.7)),
                 ("book_d", (0.2, 0.34, 0.25)), ("book_e", (0.88, 0.6, 0.22))):
        mat(k, c, rough=0.7)
    mat("fruit_a", (0.85, 0.45, 0.1), rough=0.4)
    mat("fruit_b", (0.72, 0.1, 0.08), rough=0.35)
    # outdoor
    mat("grass", (0.3, 0.42, 0.2), t["grass"], rough=0.95, tile=2.5)
    mat("ground_far", (0.33, 0.42, 0.22), t["grass"], rough=0.95, tile=7.0)
    mat("pavers", (0.62, 0.6, 0.57), t["pavers"], rough=0.8, tile=1.6)
    mat("stone_slab", (0.72, 0.71, 0.68), t["stone_slab"], rough=0.75, tile=1.2)
    mat("concrete", (0.66, 0.65, 0.63), t["concrete"], rough=0.85, tile=2.0)
    mat("asphalt", (0.22, 0.22, 0.22), t["asphalt"], rough=0.9, tile=4.0)
    mat("road_line", (0.92, 0.92, 0.9), rough=0.7)
    mat("deck", (0.52, 0.36, 0.23), t["deck"], rough=0.65, tile=0.9)
    mat("concrete_planter", (0.62, 0.61, 0.59), t["concrete"], rough=0.85, tile=1.0)
    mat("gate", (0.08, 0.08, 0.08), rough=0.5, metal=0.6)
    mat("glass_dark", (0.2, 0.22, 0.24), rough=0.05, alpha=0.6, kind="glass", baked=False)
    return m


# ------------------------------------------------------------------------------------------ helpers
def add_room(name, level, x0, y0, x1, y1, z0, z1, patrol=True, reflection=True, interior=True):
    H.ROOMS.append(dict(name=name, level=level, min=(x0, y0, z0), max=(x1, y1, z1), patrol=patrol,
                        reflection=reflection, interior=interior))


def downlights(g, M, pts, zc, power=12.0):
    for x, y in pts:
        downlight(g, x, y, zc, M, power=power)


def art_on_wall(g, M, x, y, z, yaw, w, h, art):
    place(g, F.frame_art(M, w, h, art), x, y, z, yaw)


def curtains_pair(g, M, x0, x1, y_face, zc, inward=1, seed=1, width=0.75):
    """Two open curtain panels at both ends of a window run along x (room on the +y side if inward=1)."""
    yaw = 0 if inward > 0 else 180
    y = y_face + 0.14 * inward
    h = zc - 0.12
    for i, xc in enumerate((x0 + width * 0.5 - 0.15, x1 - width * 0.5 + 0.15)):
        place(g, F.curtain(M, width, h - 0.02, seed=seed + i), xc, y, 0.0, yaw)
    place(g, F.curtain_rod(M, x1 - x0 + 0.3), (x0 + x1) * 0.5, y, h + 0.04, 0)


def curtains_pair_y(g, M, y0, y1, x_face, zc, inward=1, seed=1, width=0.7):
    """Same for a window run along y (room on the +x side if inward=1)."""
    yaw = -90 if inward > 0 else 90
    x = x_face + 0.14 * inward
    h = zc - 0.12
    for i, yc in enumerate((y0 + width * 0.5 - 0.15, y1 - width * 0.5 + 0.15)):
        place(g, F.curtain(M, width, h - 0.02, seed=seed + i), x, yc, 0.0, yaw)
    place(g, F.curtain_rod(M, y1 - y0 + 0.3), x, (y0 + y1) * 0.5, h + 0.04, 90)


# ------------------------------------------------------------------------------------------ the house
def build():
    M = make_materials()
    skirt = (M["skirting"], 0.08, 0.012)
    paint, tiles = M["paint"], M["wall_bath"]
    gf, ff, roof, ext, glass = Geo(), Geo(), Geo(), Geo(), Geo()
    out_gf = [(Z_GF, M["plinth_ext"]), (99.0, M["render"])]
    stone_gf = [(Z_GF, M["plinth_ext"]), (99.0, M["ledgestone"])]
    bath_gf = [(Z_GF + 1.2, tiles), (99.0, paint)]
    bath_ff = [(Z_FF + 2.4, tiles), (99.0, paint)]
    kitchen_wall = [(Z_GF + 0.9, paint), (Z_GF + 1.5, M["subway"]), (99.0, paint)]

    # ============================================================== ground floor walls
    zi_gf = (Z_GF, Z_GC)
    zo_gf = (0.0, Z_FF)
    S = Wall("x", 0, HX, 0, T_EXT, 0.0, Z_FF, out_gf, paint, zr0=zo_gf, zr1=zi_gf, skirt1=skirt, name="GF south")
    Wl_a = Wall("y", T_EXT, 6.075, 0, T_EXT, 0.0, Z_FF, stone_gf, paint, zr0=zo_gf, zr1=zi_gf, skirt1=skirt, name="GF west living")
    Wl_b = Wall("y", 6.075, HY - T_EXT, 0, T_EXT, 0.0, Z_FF, out_gf, bath_gf, zr0=zo_gf, zr1=zi_gf, name="GF west powder")
    N_a = Wall("x", 0, 2.375, HY - T_EXT, HY, 0.0, Z_FF, bath_gf, out_gf, zr0=zi_gf, zr1=zo_gf, name="GF north powder")
    N_b = Wall("x", 2.375, 9.475, HY - T_EXT, HY, 0.0, Z_FF, paint, out_gf, zr0=zi_gf, zr1=zo_gf, skirt0=skirt, name="GF north hall")
    N_c = Wall("x", 9.475, HX, HY - T_EXT, HY, 0.0, Z_FF, kitchen_wall, out_gf, zr0=zi_gf, zr1=zo_gf, name="GF north kitchen")
    E_a = Wall("y", T_EXT, 4.075, HX - T_EXT, HX, 0.0, Z_FF, paint, out_gf, zr0=zi_gf, zr1=zo_gf, skirt0=skirt, name="GF east guest")
    E_b = Wall("y", 4.075, HY - T_EXT, HX - T_EXT, HX, 0.0, Z_FF, kitchen_wall, out_gf, zr0=zi_gf, zr1=zo_gf, name="GF east kitchen")
    P1 = Wall("x", T_EXT, 2.45, 6.0, 6.15, Z_GF, Z_GC, paint, bath_gf, skirt0=skirt, name="powder south")
    P2 = Wall("y", 6.15, HY - T_EXT, 2.3, 2.45, Z_GF, Z_GC, bath_gf, paint, skirt1=skirt, name="powder east")
    P3 = Wall("x", 9.4, HX - T_EXT, 4.0, 4.15, Z_GF, Z_GC, paint, paint, skirt0=skirt, name="guest north")
    P4 = Wall("y", T_EXT, 4.0, 9.4, 9.55, Z_GF, Z_GC, paint, paint, skirt0=skirt, skirt1=skirt, name="guest west")

    # openings: windows and doors (ground floor)
    window(S, gf, glass, 1.0, 5.4, Z_GF, Z_GF + 2.4, M, outer=0, mullions=2, sliding=True, open_panel=2, sill=False)
    door(S, gf, 7.3, 8.4, Z_GF, 2.4, "Main", M, hinge="a", outside=-1)
    window(S, gf, glass, 10.5, 13.0, Z_GF + 0.8, Z_GF + 2.3, M, outer=0, mullions=1, transom=None)
    window(Wl_a, gf, glass, 0.7, 1.5, Z_GF + 0.3, Z_GF + 2.4, M, outer=0)
    window(Wl_a, gf, glass, 4.7, 5.5, Z_GF + 0.3, Z_GF + 2.4, M, outer=0)
    window(Wl_b, gf, glass, 7.6, 8.4, Z_GF + 1.6, Z_GF + 2.3, M, outer=0, board=False)
    window(N_c, gf, glass, 10.8, 12.6, Z_GF + 1.12, Z_GF + 2.3, M, outer=1, mullions=1, board=False)
    window(N_b, gf, glass, 4.2, 6.2, Z_GF + 1.3, Z_FF, M, outer=1, mullions=1, sill=True, board=False)
    window(E_b, gf, glass, 6.0, 7.2, Z_GF + 1.12, Z_GF + 2.3, M, outer=1, board=False)
    door(P1, gf, 0.75, 1.7, Z_GF, 2.15, "Powder", M, hinge="a", outside=-1)
    door(P4, gf, 2.55, 3.5, Z_GF, 2.15, "Guest", M, hinge="b", outside=-1)
    build_walls(gf, [S, Wl_a, Wl_b, N_a, N_b, N_c, E_a, E_b, P1, P2, P3, P4])

    # the stair window continues on the first floor wall, so the north wall needs no sill/head there
    # floors, thresholds and ceilings (ground)
    hall_rects = [(T_EXT, T_EXT, 9.4, 6.0), (2.45, 6.0, 9.4, STAIR_Y0), (VOID[2], STAIR_Y0, 9.4, HY - T_EXT),
                  (9.4, 4.15, HX - T_EXT, HY - T_EXT)]
    for r in hall_rects:
        floor(gf, r[0], r[1], r[2], r[3], Z_GF, M["floor_marble"])
        ceiling(gf, r[0], r[1], r[2], r[3], Z_GC, M["ceiling"])
    floor(gf, 2.45, STAIR_Y0, VOID[2], HY - T_EXT, Z_GF, M["floor_marble"])     # under the stair (hidden mostly)
    floor(gf, T_EXT, 6.15, 2.3, HY - T_EXT, Z_GF, M["floor_bath"])
    ceiling(gf, T_EXT, 6.15, 2.3, HY - T_EXT, Z_GC, M["ceiling"])
    floor(gf, 9.55, T_EXT, HX - T_EXT, 4.0, Z_GF, M["floor_oak"])
    ceiling(gf, 9.55, T_EXT, HX - T_EXT, 4.0, Z_GC, M["ceiling"])
    gf.collide((T_EXT, T_EXT, -0.2), (HX - T_EXT, HY - T_EXT, Z_GF))
    # slab edge around the stair void and the strips between the floors' wall faces
    vrect(gf, "x", STAIR_Y0, VOID[0], VOID[2], Z_GC, Z_FF, 1, M["ceiling"])
    vrect(gf, "x", HY - T_EXT, VOID[0], VOID[2], Z_GC, Z_FF, -1, paint)
    vrect(gf, "y", 2.45, STAIR_Y0, HY - T_EXT, Z_GC, Z_FF, 1, paint)

    # stair
    stair = Geo()
    xt = straight_stair(stair, STAIR_X0, STAIR_Y0, STAIR_Y1, Z_GF, Z_FF - Z_GF, RISERS, TREAD, M)
    glass_railing(stair, glass, (STAIR_X0 + 0.05, STAIR_Y0 + 0.03), (xt, STAIR_Y0 + 0.03),
                  Z_GF + (Z_FF - Z_GF) / RISERS, Z_FF, 0.95, M, top_clip=Z_GC - 0.03)
    hr = [(STAIR_X0 - 0.2 + i * 0.5, STAIR_Y1 - 0.07, Z_GF + 0.9 + max(0.0, (STAIR_X0 - 0.2 + i * 0.5 - (STAIR_X0 - TREAD))) * (Z_FF - Z_GF) / (RISERS * TREAD))
          for i in range(11)]
    hr = [p for p in hr if p[0] <= xt + 0.3]
    stair.tube(hr, 0.022, M["oak"], seg=10)
    for p in hr[1::3]:
        stair.tube([(p[0], STAIR_Y1, p[2] - 0.02), (p[0], STAIR_Y1 - 0.07, p[2] - 0.02)], 0.008, M["steel"], seg=8)
    emit(stair, "Stair", "GF_shell")

    # ============================================================== first floor walls
    zi_ff = (Z_FF, Z_FC)
    zo_ff = (Z_FF, Z_ROOF)
    clad = [(99.0, M["cladding"])]
    S1 = Wall("x", 0, 6.075, 0, T_EXT, Z_FF, Z_ROOF, clad, paint, zr0=zo_ff, zr1=zi_ff, skirt1=skirt, name="FF south master")
    S2 = Wall("x", 6.075, HX, 0, T_EXT, Z_FF, Z_ROOF, M["render"], paint, zr0=zo_ff, zr1=zi_ff, skirt1=skirt, name="FF south")
    W1 = Wall("y", T_EXT, 4.675, 0, T_EXT, Z_FF, Z_ROOF, clad, paint, zr0=zo_ff, zr1=zi_ff, skirt1=skirt, name="FF west master")
    W2 = Wall("y", 4.675, HY - T_EXT, 0, T_EXT, Z_FF, Z_ROOF, clad, bath_ff, zr0=zo_ff, zr1=zi_ff, name="FF west bath")
    N1 = Wall("x", 0, 2.375, HY - T_EXT, HY, Z_FF, Z_ROOF, bath_ff, M["render"], zr0=zi_ff, zr1=zo_ff, name="FF north bath")
    N2 = Wall("x", 2.375, 11.275, HY - T_EXT, HY, Z_FF, Z_ROOF, paint, M["render"], zr0=zi_ff, zr1=zo_ff, skirt0=skirt, name="FF north lounge")
    N3 = Wall("x", 11.275, HX, HY - T_EXT, HY, Z_FF, Z_ROOF, bath_ff, M["render"], zr0=zi_ff, zr1=zo_ff, name="FF north bath2")
    E1 = Wall("y", T_EXT, 4.675, HX - T_EXT, HX, Z_FF, Z_ROOF, paint, M["render"], zr0=zi_ff, zr1=zo_ff, skirt0=skirt, name="FF east bed2")
    E2 = Wall("y", 4.675, HY - T_EXT, HX - T_EXT, HX, Z_FF, Z_ROOF, bath_ff, M["render"], zr0=zi_ff, zr1=zo_ff, name="FF east bath2")
    Q1a = Wall("x", T_EXT, 2.375, 4.6, 4.75, Z_FF, Z_FC, paint, bath_ff, skirt0=skirt, name="FF mid a")
    Q1b = Wall("x", 2.375, 11.275, 4.6, 4.75, Z_FF, Z_FC, paint, paint, skirt0=skirt, skirt1=skirt, name="FF mid b")
    Q1c = Wall("x", 11.275, HX - T_EXT, 4.6, 4.75, Z_FF, Z_FC, paint, bath_ff, skirt0=skirt, name="FF mid c")
    Q2 = Wall("y", T_EXT, 4.6, 6.0, 6.15, Z_FF, Z_FC, paint, paint, skirt0=skirt, skirt1=skirt, name="master|study")
    Q3 = Wall("y", T_EXT, 4.6, 9.4, 9.55, Z_FF, Z_FC, paint, paint, skirt0=skirt, skirt1=skirt, name="study|bed2")
    Q4 = Wall("y", 4.75, HY - T_EXT, 2.3, 2.45, Z_FF, Z_FC, bath_ff, paint, skirt1=skirt, name="mbath|lounge")
    Q5 = Wall("y", 4.75, HY - T_EXT, 11.2, 11.35, Z_FF, Z_FC, paint, bath_ff, skirt0=skirt, name="lounge|bath2")

    window(S1, ff, glass, 1.2, 5.0, Z_FF, Z_FF + 2.4, M, outer=0, mullions=2, sliding=True, open_panel=1, sill=False)
    window(S2, ff, glass, 6.9, 8.7, Z_FF + 0.9, Z_FF + 2.3, M, outer=0, mullions=1)
    window(S2, ff, glass, 10.5, 13.0, Z_FF + 0.9, Z_FF + 2.3, M, outer=0, mullions=1)
    window(W1, ff, glass, 1.6, 3.4, Z_FF + 0.9, Z_FF + 2.3, M, outer=0, mullions=1)
    window(W2, ff, glass, 7.4, 8.4, Z_FF + 1.4, Z_FF + 2.3, M, outer=0, board=False)
    window(N2, ff, glass, 4.2, 6.2, Z_FF, Z_FF + 2.1, M, outer=1, mullions=1, sill=False, board=False)
    window(N2, ff, glass, 9.3, 10.9, Z_FF + 0.9, Z_FF + 2.3, M, outer=1, mullions=1)
    window(E2, ff, glass, 7.0, 8.0, Z_FF + 1.4, Z_FF + 2.3, M, outer=1, board=False)
    door(Q1a, ff, 0.75, 1.7, Z_FF, 2.15, "Master Bath", M, hinge="a", outside=1)
    door(Q1b, ff, 4.95, 5.9, Z_FF, 2.15, "Master", M, hinge="b", outside=1)
    door(Q1b, ff, 7.35, 8.3, Z_FF, 2.15, "Study", M, hinge="a", outside=1)
    door(Q1b, ff, 9.95, 10.9, Z_FF, 2.15, "Bedroom", M, hinge="a", outside=1)
    door(Q5, ff, 4.95, 5.9, Z_FF, 2.15, "Bath", M, hinge="a", outside=-1)
    build_walls(ff, [S1, S2, W1, W2, N1, N2, N3, E1, E2, Q1a, Q1b, Q1c, Q2, Q3, Q4, Q5])

    ff_rooms = {"master": (T_EXT, T_EXT, 6.0, 4.6, "floor_oak"), "study": (6.15, T_EXT, 9.4, 4.6, "floor_oak"),
                "bed2": (9.55, T_EXT, HX - T_EXT, 4.6, "floor_oak"), "mbath": (T_EXT, 4.75, 2.3, HY - T_EXT, "floor_bath"),
                "bath2": (11.35, 4.75, HX - T_EXT, HY - T_EXT, "floor_bath")}
    for k, (x0, y0, x1, y1, fm) in ff_rooms.items():
        floor(ff, x0, y0, x1, y1, Z_FF, M[fm])
        ceiling(ff, x0, y0, x1, y1, Z_FC, M["ceiling"])
    for r in rect_subtract((2.45, 4.75, 11.2, HY - T_EXT), [VOID]):
        floor(ff, r[0], r[1], r[2], r[3], Z_FF, M["floor_oak"])
    ceiling(ff, 2.45, 4.75, 11.2, HY - T_EXT, Z_FC, M["ceiling"])
    for r in rect_subtract((T_EXT, T_EXT, HX - T_EXT, HY - T_EXT), [VOID]):
        ff.collide((r[0], r[1], Z_GC), (r[2], r[3], Z_FF))
    glass_railing(ff, glass, (VOID[0], STAIR_Y0 - 0.03), (VOID[2], STAIR_Y0 - 0.03), Z_FF, Z_FF, 1.0, M)
    # strip of wall above the stair window head inside the void and the slab edge under the railing
    hrect(ff, "x", Z_FF - 0.0, VOID[0], VOID[2], STAIR_Y0 - 0.0, STAIR_Y0, 1, M["floor_oak"])

    # ============================================================== roof, parapet, façade trims
    hrect(roof, "x", Z_ROOF, T_EXT, HX - T_EXT, T_EXT, HY - T_EXT, 1, M["roof"], cell=1.2)
    roof.collide((T_EXT, T_EXT, Z_FC), (HX - T_EXT, HY - T_EXT, Z_ROOF))
    par = [Wall("x", 0, HX, 0, T_EXT, Z_ROOF, Z_PAR, M["render"], M["render"], top=True, top_mat=M["coping"], name="par S"),
           Wall("x", 0, HX, HY - T_EXT, HY, Z_ROOF, Z_PAR, M["render"], M["render"], top=True, top_mat=M["coping"], name="par N"),
           Wall("y", T_EXT, HY - T_EXT, 0, T_EXT, Z_ROOF, Z_PAR, M["render"], M["render"], top=True, top_mat=M["coping"], name="par W"),
           Wall("y", T_EXT, HY - T_EXT, HX - T_EXT, HX, Z_ROOF, Z_PAR, M["render"], M["render"], top=True, top_mat=M["coping"], name="par E")]
    build_walls(roof, par)
    for lo, hi in (((-0.05, -0.05, Z_PAR), (HX + 0.05, T_EXT + 0.03, Z_PAR + 0.05)),
                   ((-0.05, HY - T_EXT - 0.03, Z_PAR), (HX + 0.05, HY + 0.05, Z_PAR + 0.05)),
                   ((-0.05, T_EXT + 0.03, Z_PAR), (T_EXT + 0.03, HY - T_EXT - 0.03, Z_PAR + 0.05)),
                   ((HX - T_EXT - 0.03, T_EXT + 0.03, Z_PAR), (HX + 0.05, HY - T_EXT - 0.03, Z_PAR + 0.05))):
        roof.box(lo, hi, M["coping"], skip=("nz",))
    # floor band between the storeys
    for lo, hi in (((-0.04, -0.04, Z_GC + 0.1), (HX + 0.04, 0.0, Z_FF + 0.08)),
                   ((-0.04, HY, Z_GC + 0.1), (HX + 0.04, HY + 0.04, Z_FF + 0.08)),
                   ((-0.04, 0.0, Z_GC + 0.1), (0.0, HY, Z_FF + 0.08)),
                   ((HX, 0.0, Z_GC + 0.1), (HX + 0.04, HY, Z_FF + 0.08))):
        roof.box(lo, hi, M["trim_dark"])
    emit(roof, "Roof", "Roof")

    # balcony (first floor, south) with glass railing and a timber soffit
    bal = Geo()
    bx0, bx1, by0 = 0.6, 5.8, -1.5
    bal.box((bx0, by0, Z_GC), (bx1, 0.0, Z_FF), {"pz": M["deck"], "nz": M["cladding"], "default": M["render"]}, skip=("py",))
    bal.collide((bx0, by0, Z_GC), (bx1, 0.0, Z_FF))
    glass_railing(bal, glass, (bx0 + 0.05, by0 + 0.05), (bx1 - 0.05, by0 + 0.05), Z_FF, Z_FF, 1.05, M)
    glass_railing(bal, glass, (bx0 + 0.05, -0.02), (bx0 + 0.05, by0 + 0.05), Z_FF, Z_FF, 1.05, M)
    glass_railing(bal, glass, (bx1 - 0.05, by0 + 0.05), (bx1 - 0.05, -0.02), Z_FF, Z_FF, 1.05, M)
    for x in (1.6, 3.2, 4.8):
        downlight(bal, x, -0.75, Z_GC, M, power=6.0)
    place(bal, F.lounger(M), 4.6, -0.75, Z_FF, -90)
    place(bal, F.side_table(M, 0.2, 0.45), 3.5, -0.8, Z_FF)
    place(bal, F.plant_snake(M, 0.8, seed=21), 1.0, -1.1, Z_FF)
    emit(bal, "Balcony", "Exterior")

    # ============================================================== ground floor interiors
    lv = Geo()     # living + foyer
    zf = Z_GF
    place(lv, F.fluted_panel(M, 2.6, H_GF, M["walnut"]), T_EXT, 3.1, zf, 90)
    place(lv, F.tv_console(M, 2.2), T_EXT + 0.036, 3.1, zf, 90)
    place(lv, F.tv(M), T_EXT + 0.036, 3.1, zf, 90)
    place(lv, F.rug(M, 3.0, 2.5), 2.3, 3.1, zf, 90)
    place(lv, F.sofa(M, 2.9, 0.95, chaise=0.9, chaise_side=1), 3.95, 3.1, zf, -90)
    place(lv, F.coffee_table(M), 2.25, 3.0, zf + 0.012, 90)
    place(lv, F.armchair(M), 1.45, 5.2, zf, 160)
    place(lv, F.side_table(M), 3.95, 4.95, zf)
    place(lv, F.arc_lamp(M, reach=1.5, h=2.05), 4.75, 4.35, zf, -90)
    place(lv, F.plant_fig(M, 1.8, seed=3), 0.62, 0.65, zf)
    place(lv, F.plant_snake(M, 0.95, seed=8), 0.55, 1.95, zf)
    place(lv, F.plant_snake(M, 0.85, seed=9, pot="pot"), 0.55, 4.3, zf)
    curtains_pair(lv, M, 1.0, 5.4, T_EXT, zf + H_GF, inward=1, seed=11, width=0.7)
    downlights(lv, M, [(1.6, 1.5), (1.6, 4.6), (3.3, 1.5), (3.3, 4.6), (5.4, 3.0), (5.4, 5.3)], Z_GC)
    # foyer
    place(lv, F.sideboard(M, 1.4, 0.4), 9.4, 1.5, zf, -90)
    art_on_wall(lv, M, 9.4 - 0.002, 1.5, zf + 1.25, -90, 1.0, 0.7, "art2")
    place(lv, F.rug(M, 1.4, 0.9, "rug"), 7.85, 1.0, zf, 0)
    place(lv, F.plant_snake(M, 0.9, seed=12), 6.85, 0.62, zf)
    downlights(lv, M, [(7.85, 1.2), (7.85, 2.8)], Z_GC)
    emit(lv, "Living", "GF_living")

    dn = Geo()     # dining + stair hall
    place(dn, F.dining_table(M, 2.0, 1.0), 7.9, 6.0, zf, 90)
    for y in (5.35, 6.0, 6.65):
        place(dn, F.dining_chair(M), 7.07, y, zf, 90)
        place(dn, F.dining_chair(M), 8.73, y, zf, -90)
    place(dn, F.pendant_linear(M, 1.3, 0.8, H_GF), 7.9, 6.0, zf, 90)
    place(dn, F.sideboard(M, 1.8, 0.42), 5.4, STAIR_Y0, zf, 0)
    art_on_wall(dn, M, 5.4, STAIR_Y0 - 0.002, zf + 1.15, 0, 1.2, 0.8, "art1")
    place(dn, F.plant_fig(M, 1.6, seed=17, pot_r=0.18), 3.05, 8.15, zf)
    downlights(dn, M, [(3.6, 7.3), (5.6, 7.3), (7.0, 4.6), (8.8, 4.6), (8.6, 9.1)], Z_GC)
    emit(dn, "Dining", "GF_dining")

    kt = Geo()     # kitchen
    north_units = [(0.6, "drawers"), (0.5, "door"), (0.6, "blank"), (0.9, "sink"), (0.6, "drawers"), (0.4, "door"), (0.6, "door")]
    place(kt, F.base_run(M, north_units, sink=3), 9.55, HY - T_EXT - 0.6, zf, 0)
    east_units = [(0.45, "door"), (0.9, "hob"), (0.6, "drawers"), (0.8, "doors"), (0.75, "drawers")]
    place(kt, F.base_run(M, east_units, hob=1), HX - T_EXT - 0.6, HY - T_EXT - 0.6, zf, -90)
    place(kt, F.tall_unit(M, 0.6, 2.3, kind="oven", front="oak"), HX - T_EXT - 0.6, 5.65, zf, -90)
    place(kt, F.fridge(M), HX - T_EXT - 0.68, 5.05, zf, -90)
    kt.box((HX - T_EXT - 0.68, 4.15, zf + 1.85), (HX - T_EXT, 5.05, zf + 2.3), M["oak"], skip=("px",))
    place(kt, F.wall_run(M, [(0.6, "d"), (0.6, "d")], glass=(1,)), 9.55, HY - T_EXT - 0.35, zf + 1.5, 0)
    place(kt, F.wall_run(M, [(0.5, "d"), (0.6, "d")]), 12.65, HY - T_EXT - 0.35, zf + 1.5, 0)
    place(kt, F.hood(M, 0.9, 0.5, z0=1.62, ceiling=H_GF), HX - T_EXT, 8.25, zf, -90)
    island_units = [(0.6, "drawers"), (1.0, "doors"), (0.6, "drawers")]
    isl = F.base_run(M, island_units, depth=0.6, seat_over=0.32, waterfall=(True, True))
    isl.box((0.0, 0.58, 0.0), (2.2, 0.6, 0.87), M["cab_low"], skip=("ny", "nz"))
    place(kt, isl, 12.2, 8.0, zf, 180)
    for x in (10.45, 11.1, 11.75):
        place(kt, F.bar_stool(M), x, 6.78, zf, 180)
        place(kt, F.pendant_dome(M, 0.16, 0.95, H_GF), x, 7.62, zf)
    place(kt, F.kitchen_props(M), 10.25, HY - T_EXT - 0.3, zf + 0.9, 0)
    place(kt, F.plant_snake(M, 0.35, seed=31, pot_r=0.07, pot="pot"), 13.0, HY - T_EXT - 0.25, zf + 0.9)
    downlights(kt, M, [(10.0, 5.2), (12.4, 5.2), (10.4, 8.6), (12.4, 8.6)], Z_GC)
    emit(kt, "Kitchen", "GF_kitchen")

    pw = Geo()     # powder room
    place(pw, F.wc(M), T_EXT, 8.9, zf, 90)
    place(pw, F.vanity(M, 0.8, 0.42, z0=0.42, h=0.42), 2.3, 7.15, zf, -90)
    place(pw, F.towel_rail(M, 0.45, 1.0), 2.3, 8.15, zf, -90)
    downlights(pw, M, [(1.25, 7.2), (1.25, 8.9)], Z_GC, power=9.0)
    emit(pw, "Powder", "GF_powder")

    gr = Geo()     # guest bedroom
    place(gr, F.headboard(M, 2.2, 1.1), HX - T_EXT, 2.1, zf, -90)
    place(gr, F.bed(M, 1.6, 2.05), HX - T_EXT - 0.11, 2.1, zf, -90)
    for y in (0.95, 3.25):
        place(gr, F.nightstand(M), HX - T_EXT - 0.11, y, zf, -90)
        place(gr, F.table_lamp(M), HX - T_EXT - 0.31, y, zf + 0.5)
    place(gr, F.wardrobe(M, 1.8, 2.4), 10.55, 4.0 - 0.6, zf, 0)
    place(gr, F.rug(M, 2.4, 2.0), 11.8, 2.1, zf, 90)
    art_on_wall(gr, M, HX - T_EXT - 0.002, 2.1, zf + 1.55, -90, 1.1, 0.6, "art3")
    curtains_pair(gr, M, 10.5, 13.0, T_EXT, zf + H_GF, inward=1, seed=21, width=0.6)
    downlights(gr, M, [(10.6, 1.4), (12.6, 1.4), (11.6, 3.0)], Z_GC, power=10.0)
    emit(gr, "Guest", "GF_guest")

    # ============================================================== first floor interiors
    zf = Z_FF
    ms = Geo()     # master bedroom
    place(ms, F.headboard(M, 2.6, 1.2), 3.2, 4.6, zf, 0)
    place(ms, F.bed(M, 1.8, 2.1), 3.2, 4.49, zf, 0)
    for x in (1.98, 4.42):
        place(ms, F.nightstand(M), x, 4.49, zf, 0)
        place(ms, F.table_lamp(M), x, 4.29, zf + 0.5)
    place(ms, F.rug(M, 3.2, 2.4), 3.2, 3.0, zf, 0)
    place(ms, F.wardrobe(M, 3.0, 2.6, front="wardrobe"), 5.4, 3.5, zf, -90)
    place(ms, F.desk(M, 1.2, 0.5), T_EXT, 2.5, zf, 90)
    place(ms, F.dining_chair(M), 0.82, 2.5, zf, -90)
    place(ms, F.armchair(M, "sofa_alt"), 0.95, 0.95, zf, 225)
    place(ms, F.plant_fig(M, 1.5, seed=41, pot_r=0.17), 5.5, 0.6, zf)
    curtains_pair(ms, M, 1.2, 5.0, T_EXT, zf + H_FF, inward=1, seed=31, width=0.7)
    downlights(ms, M, [(1.6, 1.5), (4.6, 1.5), (1.6, 3.6), (4.6, 3.6)], Z_FC, power=10.0)
    emit(ms, "Master", "FF_master")

    mb = Geo()     # master bath
    place(mb, F.vanity(M, 1.2, 0.5), 2.3, 6.0, zf, -90)
    place(mb, F.wc(M), T_EXT, 7.1, zf, 90)
    sh, sg = F.shower(M, 2.05, 1.2)
    place(mb, sh, 1.275, HY - T_EXT, zf, 0)
    place(glass, sg, 1.275, HY - T_EXT, zf, 0)
    place(mb, F.towel_rail(M, 0.6, 1.1), 1.7, 4.75, zf, 180)
    place(mb, F.plant_snake(M, 0.6, seed=51, pot_r=0.1), 0.5, 5.05, zf)
    downlights(mb, M, [(1.27, 5.6), (1.27, 7.3), (1.27, 9.1)], Z_FC, power=9.0)
    emit(mb, "Master Bath", "FF_mbath")

    lg = Geo()     # lounge
    place(lg, F.sofa(M, 2.4, 0.92), 8.3, 6.95, zf, 90)
    place(lg, F.tv_console(M, 1.8, 0.4), 11.2, 6.95, zf, -90)
    place(lg, F.tv(M, 1.25, 0.72), 11.2, 6.95, zf, -90)
    place(lg, F.coffee_table(M, 1.1, 0.6), 9.75, 6.95, zf + 0.012, 90)
    place(lg, F.rug(M, 2.8, 2.2), 9.75, 6.95, zf, 90)
    place(lg, F.bookshelf(M, 1.6, 2.3, seed=61), 2.8, 6.6, zf, 90)
    place(lg, F.armchair(M, "sofa_alt"), 3.75, 7.75, zf, -60)
    place(lg, F.arc_lamp(M, reach=0.9, h=1.75), 4.25, 8.25, zf, 140)
    place(lg, F.plant_fig(M, 1.7, seed=71), 10.75, 9.35, zf)
    art_on_wall(lg, M, 3.7, 4.75 + 0.002, zf + 1.3, 180, 1.1, 0.75, "art1")
    art_on_wall(lg, M, 6.6, 4.75 + 0.002, zf + 1.3, 180, 0.6, 0.8, "art3")
    downlights(lg, M, [(3.4, 5.5), (5.4, 5.5), (7.6, 5.5), (9.8, 5.5), (9.6, 8.6), (8.0, 7.5), (5.0, 9.15), (3.2, 9.15)], Z_FC, power=10.0)
    emit(lg, "Lounge", "FF_lounge")

    st = Geo()     # study
    place(st, F.desk(M, 1.4, 0.65), 7.8, 0.3, zf, 180)
    place(st, F.office_chair(M), 7.8, 1.25, zf, 0)
    place(st, F.bookshelf(M, 1.6, 2.3, seed=81, mat="walnut"), 6.5, 2.6, zf, 90)
    place(st, F.armchair(M), 8.75, 3.7, zf, 135)
    place(st, F.rug(M, 2.0, 1.6, "rug"), 7.8, 2.3, zf, 0)
    place(st, F.plant_snake(M, 0.9, seed=91), 9.05, 0.62, zf)
    curtains_pair(st, M, 6.9, 8.7, T_EXT, zf + H_FF, inward=1, seed=41, width=0.55)
    downlights(st, M, [(7.0, 1.6), (8.6, 1.6), (7.8, 3.5)], Z_FC, power=10.0)
    emit(st, "Study", "FF_study")

    b2 = Geo()     # bedroom 2
    place(b2, F.headboard(M, 2.2, 1.1, mat="headboard"), HX - T_EXT, 2.3, zf, -90)
    place(b2, F.bed(M, 1.6, 2.05, throw="pillow_a"), HX - T_EXT - 0.11, 2.3, zf, -90)
    for y in (1.15, 3.45):
        place(b2, F.nightstand(M), HX - T_EXT - 0.11, y, zf, -90)
        place(b2, F.table_lamp(M), HX - T_EXT - 0.31, y, zf + 0.5)
    place(b2, F.wardrobe(M, 2.4, 2.5), 11.2, 4.0, zf, 0)
    place(b2, F.desk(M, 1.2, 0.55), 9.55, 2.0, zf, 90)
    place(b2, F.dining_chair(M), 10.1, 2.0, zf, -90)
    place(b2, F.rug(M, 2.4, 2.0), 12.0, 2.3, zf, 90)
    curtains_pair(b2, M, 10.5, 13.0, T_EXT, zf + H_FF, inward=1, seed=51, width=0.6)
    downlights(b2, M, [(10.6, 1.3), (12.6, 1.3), (11.6, 3.4)], Z_FC, power=10.0)
    emit(b2, "Bedroom 2", "FF_bed2")

    b3 = Geo()     # bath 2
    place(b3, F.vanity(M, 1.0, 0.48), 12.6, 4.75, zf, 180)
    place(b3, F.wc(M), HX - T_EXT, 7.0, zf, -90)
    sh, sg = F.shower(M, 2.4, 1.2)
    place(b3, sh, 12.55, HY - T_EXT, zf, 0)
    place(glass, sg, 12.55, HY - T_EXT, zf, 0)
    place(b3, F.towel_rail(M, 0.6, 1.1), 11.35, 7.6, zf, 90)
    downlights(b3, M, [(12.55, 5.6), (12.55, 7.3), (12.55, 9.1)], Z_FC, power=9.0)
    emit(b3, "Bath 2", "FF_bath2")

    emit(gf, "GF Shell", "GF_shell")
    emit(ff, "FF Shell", "FF_shell")

    # ============================================================== exterior: terrace, porch, carport
    ex = Geo()
    ex.box((0.3, -2.4, 0.0), (6.4, 0.0, Z_GF), {"pz": M["deck"], "default": M["deck"]}, skip=("py", "nz", "px"))
    ex.box((6.4, -2.4, 0.0), (9.6, 0.0, Z_GF), M["stone_slab"], skip=("py", "nz", "nx"))
    ex.box((6.6, -3.0, 0.0), (9.6, -2.4, Z_GF * 0.5), M["stone_slab"], skip=("py", "nz"))
    ex.collide((0.3, -2.4, -0.2), (9.6, 0.0, Z_GF))
    ex.collide((6.6, -3.0, -0.2), (9.6, -2.4, Z_GF * 0.5))
    # entrance canopy with a stone-clad fin
    ex.box((6.4, -1.95, 2.95), (9.9, 0.0, 3.12), {"nz": M["cladding"], "default": M["render"]}, skip=("py",))
    ex.box((9.6, -1.95, 0.0), (9.9, 0.0, 2.95), M["ledgestone"], skip=("py", "nz"))
    ex.collide((9.6, -1.95, 0.0), (9.9, 0.0, 2.95))
    for x in (7.2, 8.6):
        downlight(ex, x, -0.95, 2.95, M, power=5.0)
    place(ex, F.wall_light(M), 6.95, -0.002, 2.0, 0)
    place(ex, F.planter(M, 1.6, 0.45, 0.45, seed=3), 3.0, -2.15, Z_GF, 0)
    place(ex, F.lounger(M), 1.2, -1.15, Z_GF, 0)
    place(ex, F.lounger(M), 2.1, -1.15, Z_GF, 0)
    place(ex, F.side_table(M, 0.22, 0.45), 1.65, -0.35, Z_GF)
    place(ex, F.plant_fig(M, 1.5, seed=101, pot_r=0.2), 9.25, -1.6, Z_GF)
    # car porch: slab on two slim steel columns
    ex.box((HX, 0.6, 2.85), (19.6, 6.4, 3.05), {"nz": M["cladding"], "default": M["render"]})
    for y in (0.9, 6.1):
        ex.box((19.25, y - 0.06, 0.0), (19.37, y + 0.06, 2.85), M["metal_black"], skip=("nz",))
        ex.collide((19.25, y - 0.06, 0.0), (19.37, y + 0.06, 2.85))
    for x, y in ((15.5, 2.0), (17.8, 2.0), (15.5, 5.0), (17.8, 5.0)):
        downlight(ex, x, y, 2.85, M, power=4.0)
    emit(ex, "Terrace", "Exterior")

    # ============================================================== plot: ground, paths, compound wall, garden
    gd = Geo()
    x0, y0, x1, y1 = PLOT
    drive = (14.6, y0, 18.6, 7.0)
    holes = [(0.0, 0.0, HX, HY), (0.3, -2.4, 9.6, 0.0), (6.6, -3.0, 9.6, -2.4), drive, (9.6, -1.95, 9.9, 0.0)]
    for r in rect_subtract(PLOT, holes):
        gd.grid((r[0], r[1], 0.0), (r[2] - r[0], 0, 0), (0, r[3] - r[1], 0), M["grass"], 0.7)
    gd.grid((drive[0], drive[1], 0.0), (drive[2] - drive[0], 0, 0), (0, drive[3] - drive[1], 0), M["pavers"], 0.7)
    # stepping stones from the gate to the porch steps
    yy = y0 + 0.4
    while yy < -3.4:
        gd.rbox((7.25, yy, 0.0), (8.35, yy + 0.55, 0.03), 0.01, M["stone_slab"], seg=1, skip=("nz",))
        yy += 0.75
    # far ground, footpath and road
    far = (-90.0, -90.0, 110.0, 100.0)
    wall_out = (x0 - 0.2, y0 - 0.2, x1 + 0.2, y1 + 0.2)
    road = (far[0], -20.0, far[2], -14.0)
    path = (far[0], -14.0, far[2], y0 - 0.2)
    for r in rect_subtract(far, [wall_out, road, path]):
        size = max(r[2] - r[0], r[3] - r[1])
        gd.grid((r[0], r[1], 0.0), (r[2] - r[0], 0, 0), (0, r[3] - r[1], 0), M["ground_far"], 2.0 if size < 40 else 8.0)
    gd.grid((road[0], road[1], -0.02), (road[2] - road[0], 0, 0), (0, road[3] - road[1], 0), M["asphalt"], 4.0)
    gd.box((path[0], path[1], -0.02), (path[2], path[3], 0.12), {"pz": M["concrete"], "default": M["concrete"]}, skip=("nz", "py"))
    for i in range(-18, 22):
        gd.box((i * 5.0, -17.08, -0.019), (i * 5.0 + 2.5, -16.92, -0.017), M["road_line"], skip=("nz",))
    gd.collide((far[0], far[1], -1.0), (far[2], far[3], 0.0))
    emit(gd, "Ground", "Ground")

    cw = Geo()
    hcw = 1.7
    walls = [Wall("x", x0 - 0.2, x1 + 0.2, y0 - 0.2, y0, 0.0, hcw, M["render"], M["render"], top=True, top_mat=M["coping"], name="cw S"),
             Wall("x", x0 - 0.2, x1 + 0.2, y1, y1 + 0.2, 0.0, hcw, M["render"], M["render"], top=True, top_mat=M["coping"], name="cw N"),
             Wall("y", y0, y1, x0 - 0.2, x0, 0.0, hcw, M["render"], M["render"], top=True, top_mat=M["coping"], name="cw W"),
             Wall("y", y0, y1, x1, x1 + 0.2, 0.0, hcw, M["render"], M["render"], top=True, top_mat=M["coping"], name="cw E")]
    walls[0].opening(7.2, 8.4, 0.0, hcw, kind="void")
    walls[0].opening(14.6, 18.6, 0.0, hcw, kind="void")
    build_walls(cw, walls, cell=0.9)
    for xa, xb in ((6.8, 7.2), (8.4, 8.8), (14.2, 14.6), (18.6, 19.0)):
        cw.box((xa, y0 - 0.25, 0.0), (xb, y0 + 0.05, 1.95), M["ledgestone"], skip=("nz",))
        cw.box((xa - 0.02, y0 - 0.27, 1.95), (xb + 0.02, y0 + 0.07, 2.0), M["coping"], skip=())
        cw.collide((xa, y0 - 0.25, 0.0), (xb, y0 + 0.05, 1.95))
    place(cw, F.gate_slats(M, 1.2, 1.6), 7.2, y0 - 0.1, 0.0, 0)
    place(cw, F.gate_slats(M, 4.0, 1.6), 14.6, y0 - 0.1, 0.0, 0)
    for x in (7.0, 8.6):
        place(cw, F.bollard(M, 0.5), x, y0 + 0.5, 0.0)
    for yb in (-8.5, -6.0):
        place(cw, F.bollard(M), 7.0, yb, 0.0)
        place(cw, F.bollard(M), 8.6, yb, 0.0)
    emit(cw, "Compound Wall", "Exterior")

    gn = Geo()     # garden
    place(gn, F.tree(M, 5.5, seed=11, crown=1.7), -3.2, -6.5, 0.0)
    place(gn, F.tree(M, 5.0, seed=12, crown=1.5), 12.6, -5.2, 0.0)
    place(gn, F.tree(M, 6.0, seed=13, crown=1.9), -2.8, 12.4, 0.0)
    place(gn, F.tree(M, 5.2, seed=14, crown=1.6), 19.5, 12.0, 0.0)
    gn.add(F.hedge(M, 24.0, 0.7, 1.1), 90, (x0 + 0.45, y0 + 1.0, 0.0))
    gn.add(F.hedge(M, 18.5, 0.7, 1.1), 0, (x0 + 1.0, y1 - 0.45, 0.0))
    gn.add(F.hedge(M, 6.6, 0.6, 0.8), 0, (x0 + 1.0, y0 + 0.4, 0.0))
    gn.add(F.hedge(M, 4.6, 0.6, 0.8), 0, (9.0, y0 + 0.4, 0.0))
    for x, y in ((-1.2, -1.2), (10.6, -2.6), (12.8, -2.0), (-1.0, 10.8), (15.6, 11.5), (20.8, -9.0), (20.8, -4.0)):
        place(gn, F.shrub(M, 0.5, seed=int(abs(x * 7 + y * 3))), x, y, 0.0)
    for y in range(-10, 10, 3):
        place(gn, F.bollard(M, 0.45), 19.2, y + 0.5, 0.0)
    emit(gn, "Garden", "Garden")

    emit(glass, "Glass", "Glass", bake=False)

    # ============================================================== rooms, views, spawn points
    add_room("Living", 0, T_EXT, T_EXT, 6.4, 6.0, Z_GF, Z_GC)
    add_room("Foyer", 0, 6.4, T_EXT, 9.4, 3.2, Z_GF, Z_GC)
    add_room("Dining", 0, 5.2, 3.2, 9.4, STAIR_Y0, Z_GF, Z_GC)
    add_room("Kitchen", 0, 9.4, 4.15, HX - T_EXT, HY - T_EXT, Z_GF, Z_GC)
    add_room("Stair Hall", 0, 2.45, 6.0, 5.2, STAIR_Y0, Z_GF, Z_GC)
    add_room("Powder Room", 0, T_EXT, 6.15, 2.3, HY - T_EXT, Z_GF, Z_GC)
    add_room("Guest Bedroom", 0, 9.55, T_EXT, HX - T_EXT, 4.0, Z_GF, Z_GC)
    add_room("Master Bedroom", 1, T_EXT, T_EXT, 6.0, 4.6, Z_FF, Z_FC)
    add_room("Master Bath", 1, T_EXT, 4.75, 2.3, HY - T_EXT, Z_FF, Z_FC)
    add_room("Lounge", 1, 2.45, 4.75, 11.2, HY - T_EXT, Z_FF, Z_FC)
    add_room("Study", 1, 6.15, T_EXT, 9.4, 4.6, Z_FF, Z_FC)
    add_room("Bedroom 2", 1, 9.55, T_EXT, HX - T_EXT, 4.6, Z_FF, Z_FC)
    add_room("Bath 2", 1, 11.35, 4.75, HX - T_EXT, HY - T_EXT, Z_FF, Z_FC)
    add_room("Balcony", 1, 0.65, -1.45, 5.75, 0.0, Z_FF, Z_FF + 2.5, patrol=False, reflection=False, interior=False)
    add_room("Front Yard", 0, x0, y0, x1, -3.0, 0.0, 4.0, reflection=False, interior=False)
    add_room("Back Yard", 0, x0, HY + 0.5, x1, y1, 0.0, 4.0, reflection=False, interior=False)
    add_room("West Yard", 0, x0, -3.0, -0.5, HY + 0.5, 0.0, 4.0, reflection=False, interior=False)
    add_room("East Yard", 0, HX + 0.5, -3.0, x1, HY + 0.5, 0.0, 4.0, reflection=False, interior=False)

    eye = 1.62
    H.VIEWS.extend([
        dict(name="exterior", eye=(10.9, -9.7, eye), target=(5.2, 2.5, 2.9)),
        dict(name="living", eye=(5.9, 0.9, Z_GF + eye), target=(0.6, 4.2, Z_GF + 1.0)),
        dict(name="kitchen", eye=(7.3, 4.4, Z_GF + eye), target=(12.6, 8.6, Z_GF + 1.0)),
        dict(name="stairs", eye=(7.2, 4.2, Z_GF + eye), target=(3.6, 9.6, Z_GF + 2.3)),
        dict(name="master", eye=(4.95, 0.7, Z_FF + eye), target=(2.3, 4.4, Z_FF + 0.85)),
        dict(name="lounge", eye=(3.3, 5.3, Z_FF + eye), target=(10.6, 7.6, Z_FF + 0.9)),
        dict(name="bath", eye=(1.95, 5.0, Z_FF + eye), target=(0.9, 9.2, Z_FF + 1.0)),
        dict(name="aerial", eye=(-10.0, -17.0, 11.0), target=(7.0, 4.0, 2.2), test=False, fov=50.0),
    ])
    H.INFO["spawn"] = dict(pos=[7.8, 0.05, -9.6], yaw=0.0)
    H.INFO["enemySpawn"] = dict(pos=[11.2, Z_GF, 5.4], yaw=-90.0)
    H.INFO["levels"] = dict(ground=Z_GF, first=Z_FF, ceiling=Z_GC)
    H.INFO["sunDir"] = [round(float(v), 5) for v in H.to_unity(SUN_DIR)]
    H.INFO["plot"] = [x0, y0, x1, y1]
    H.INFO["giveUpDistance"] = 17.0
    return M


AZIMUTH, ELEVATION = 218.0, 38.0       # sun from the south-west, low enough to reach into the rooms
SUN_DIR = np.array((math.sin(math.radians(AZIMUTH)) * math.cos(math.radians(ELEVATION)),
                    math.cos(math.radians(AZIMUTH)) * math.cos(math.radians(ELEVATION)),
                    math.sin(math.radians(ELEVATION))))          # unit vector pointing towards the sun


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    out = argv[0] if argv and not argv[0].startswith("--") else os.path.join(HERE, "out")
    samples = 192
    quick = "--quick" in argv
    if "--samples" in argv:
        samples = int(argv[argv.index("--samples") + 1])
    H.set_output(out)
    t0 = time.time()
    build()
    objects = H.merged_objects()
    tris = 0
    for o in objects:
        tris += sum(len(f[0]) - 2 for f in o["geo"].F)
    log("built %d objects (%d triangles, %d colliders, %d lights, %d doors) in %.1f s" % (
        len(objects), tris, len(H.COLLIDERS), len(H.LIGHTS), len(H.DOORS), time.time() - t0))
    try:
        import bpy  # noqa: F401
        in_blender = True
    except ImportError:
        in_blender = False
    light, extra = None, {}
    if in_blender:
        import hblender
        light, extra = hblender.run(objects, SUN_DIR, samples=samples, quick=quick)
    H.export(objects, light, extra)
    log("done in %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
