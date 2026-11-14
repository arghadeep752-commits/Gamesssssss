"""Builds ADARSH VIDYALAYA - the school - in Blender and exports it for Godot.

    blender -b -noaudio -P tools/school/build_school.py -- OUT_DIR [--tex DOWNLOADED_TEXTURES] [--no-bake] [--quick]

* geometry from tools/school/layout.py, architecture.py, furniture.py and items.py (all modelled from code); furniture
  kinds that have a Hyper3D (Rodin) model in rodin_models.json use that model instead (see rodin.py)
* painted room labels and chalk writing on the blackboards as 3D text
* one object per room for the building and one for its furniture, so each gets its own baked lightmap
* night lighting (tube lights, bare bulbs, moonlight) baked in Cycles into lightmaps (second UV set)
* doors, almirah doors, fan rotors, the planks and padlock, the gate and the items stay separate (they move)
* exports school.glb, school_meta.json, lightmaps/*.png, school.blend and preview renders
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
import numpy as np
from mathutils import Euler, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))
import layout  # noqa: E402
import rodin  # noqa: E402
import architecture  # noqa: E402
import furniture  # noqa: E402
import items as item_models  # noqa: E402
import navigation  # noqa: E402
from geo import Geo, rot_z  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build/school"]
OUT = os.path.abspath(argv[0])
TEX = os.path.abspath(argv[argv.index("--tex") + 1]) if "--tex" in argv else None
DO_BAKE = "--no-bake" not in argv
QUICK = "--quick" in argv
os.makedirs(os.path.join(OUT, "lightmaps"), exist_ok=True)
T0 = time.time()
_logf = open(os.path.join(OUT, "build_log.txt"), "w")
LM_SCALE = 4.0


def log(*a):
    s = "[%6.1fs] " % (time.time() - T0) + " ".join(str(x) for x in a)
    print(s, flush=True)
    _logf.write(s + "\n")
    _logf.flush()


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
view_layer = bpy.context.view_layer
COL = bpy.data.collections.new("School")
scene.collection.children.link(COL)

# ================================================================================================ materials
BASE = {
    "plaster": (0.72, 0.69, 0.61), "plaster_ext": (0.62, 0.5, 0.3), "ceiling": (0.75, 0.74, 0.69), "plinth": (0.32, 0.2, 0.16),
    "floor_cement": (0.38, 0.38, 0.36), "floor_terrazzo": (0.48, 0.46, 0.42), "floor_tiles": (0.72, 0.72, 0.7),
    "floor_kota": (0.34, 0.38, 0.34), "floor_veranda": (0.42, 0.2, 0.15), "dado_green": (0.15, 0.28, 0.22),
    "dado_blue": (0.19, 0.27, 0.36), "dado_red": (0.36, 0.14, 0.1), "dado_brown": (0.28, 0.19, 0.12), "dado_tiles": (0.72, 0.72, 0.7),
    "wood": (0.42, 0.28, 0.16), "wood_dark": (0.2, 0.13, 0.08), "wood_old": (0.33, 0.25, 0.18), "wood_painted_blue": (0.19, 0.28, 0.4),
    "wood_painted_green": (0.19, 0.33, 0.24), "wood_door_main": (0.26, 0.17, 0.1), "wood_plank": (0.38, 0.29, 0.19),
    "metal_green": (0.17, 0.28, 0.21), "metal_grey": (0.38, 0.4, 0.4), "metal_white": (0.75, 0.75, 0.73), "metal_black": (0.03, 0.03, 0.03),
    "rust": (0.28, 0.14, 0.07), "steel": (0.55, 0.55, 0.55), "aluminium": (0.6, 0.6, 0.61), "brass": (0.55, 0.42, 0.14),
    "chalkboard": (0.05, 0.08, 0.065), "chalk": (0.85, 0.85, 0.8), "felt": (0.23, 0.26, 0.23), "felt_green": (0.16, 0.27, 0.18),
    "glass": (0.18, 0.22, 0.22), "glass_dirty": (0.22, 0.26, 0.26), "mirror": (0.28, 0.3, 0.31), "ceramic": (0.8, 0.8, 0.77),
    "concrete": (0.42, 0.41, 0.39), "concrete_wet": (0.28, 0.28, 0.27), "ground_dirt": (0.26, 0.21, 0.16), "ground_court": (0.3, 0.25, 0.19),
    "brick_path": (0.38, 0.19, 0.13), "roof": (0.38, 0.38, 0.36), "clay": (0.5, 0.28, 0.17), "sack": (0.46, 0.39, 0.28),
    "paper": (0.75, 0.73, 0.66), "cardboard": (0.46, 0.35, 0.23), "register_red": (0.45, 0.09, 0.09), "register_blue": (0.11, 0.18, 0.42),
    "file_cloth": (0.5, 0.14, 0.11), "cane": (0.46, 0.37, 0.23), "clock_face": (0.8, 0.78, 0.7), "book_red": (0.45, 0.08, 0.07),
    "book_blue": (0.1, 0.16, 0.38), "book_green": (0.1, 0.28, 0.14), "book_brown": (0.33, 0.21, 0.12), "book_black": (0.05, 0.05, 0.05),
    "plastic_blue": (0.08, 0.26, 0.55), "broom": (0.55, 0.45, 0.28), "curtain": (0.36, 0.04, 0.05), "ivory": (0.8, 0.77, 0.66),
    "fabric_mat": (0.42, 0.32, 0.18), "brick_soot": (0.16, 0.11, 0.09), "ash": (0.28, 0.28, 0.28), "aluminium_soot": (0.18, 0.18, 0.18),
    "paint_red": (0.55, 0.07, 0.05), "rope": (0.55, 0.45, 0.32), "bark": (0.22, 0.18, 0.14), "leaves": (0.12, 0.22, 0.08),
    "cable": (0.04, 0.04, 0.04), "tube_glow": (0.95, 0.97, 1.0), "tube_dead": (0.6, 0.6, 0.6), "bulb_glow": (1.0, 0.8, 0.5),
    "paint_white": (0.8, 0.8, 0.76), "paint_black": (0.04, 0.04, 0.04), "wood_handle": (0.5, 0.33, 0.18), "steel_face": (0.7, 0.7, 0.7),
    "iron_old": (0.2, 0.18, 0.16), "tag_white": (0.85, 0.83, 0.75), "tag_yellow": (0.85, 0.7, 0.2), "string": (0.7, 0.65, 0.55),
    "blood": (0.25, 0.01, 0.01),
}
EMIT = {"tube_glow": 6.0, "bulb_glow": 8.0}
METAL = {"steel", "aluminium", "brass", "steel_face", "metal_grey", "mirror"}
MATS = {}
_dummy_lm = bpy.data.images.new("lm_dummy", 4, 4, alpha=False, float_buffer=False)
_dummy_lm.pixels.foreach_set(np.full(64, 0.5, np.float32))
_gltf_group = None


def gltf_output_group():
    """Blender's glTF exporter reads an 'Occlusion' input from a node group with this name; we use it so the
    lightmap UV set (LM) is exported as TEXCOORD_1."""
    global _gltf_group
    if _gltf_group is not None:
        return _gltf_group
    ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    try:
        ng.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    except Exception:       # noqa: BLE001  (older Blender)
        ng.inputs.new("NodeSocketFloat", "Occlusion")
    _gltf_group = ng
    return ng


RODIN_TEX = {}       # material name -> (image bytes, mime) of a Hyper3D model's base colour
TEXD = os.path.join(OUT, "rodin_tex")


def rodin_image(name):
    """The model's own texture, at most 1024 px, saved as JPEG so it embeds small in school.glb."""
    data, mime = RODIN_TEX[name]
    os.makedirs(TEXD, exist_ok=True)
    src = os.path.join(TEXD, name + ("_src.jpg" if "jpeg" in (mime or "") else "_src.png"))
    open(src, "wb").write(data)
    img = bpy.data.images.load(src)
    w, h = img.size
    if max(w, h) > 1024:
        f = 1024.0 / max(w, h)
        img.scale(max(1, int(w * f)), max(1, int(h * f)))
    out = os.path.join(TEXD, name + ".jpg")
    img.file_format = "JPEG"
    img.filepath_raw = out
    img.save()
    img.name = name
    return img


def material(name):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    c = BASE.get(name, (0.5, 0.5, 0.5))
    b.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
    if name in RODIN_TEX:
        try:
            uv0 = nt.nodes.new("ShaderNodeUVMap")
            uv0.uv_map = "UVMap"
            bc = nt.nodes.new("ShaderNodeTexImage")
            bc.name = "RODIN_BASE"
            bc.image = rodin_image(name)
            nt.links.new(uv0.outputs["UV"], bc.inputs["Vector"])
            nt.links.new(bc.outputs["Color"], b.inputs["Base Color"])
        except Exception as e:      # noqa: BLE001
            log("rodin texture failed for", name, e)
    b.inputs["Roughness"].default_value = 0.35 if name in METAL else 0.85
    b.inputs["Metallic"].default_value = 0.0
    if name in EMIT:
        key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[key].default_value = (c[0], c[1], c[2], 1.0)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = EMIT[name]
    # lightmap hook: UV map "LM" -> image -> glTF occlusion
    try:
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "LM"
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.name = "LM_EXPORT"
        tn.image = _dummy_lm
        nt.links.new(uvn.outputs["UV"], tn.inputs["Vector"])
        gn = nt.nodes.new("ShaderNodeGroup")
        gn.node_tree = gltf_output_group()
        nt.links.new(tn.outputs["Color"], gn.inputs[0])
        bk = nt.nodes.new("ShaderNodeTexImage")
        bk.name = "LM_BAKE"
    except Exception as e:      # noqa: BLE001
        log("lightmap hook failed for", name, e)
    m.use_backface_culling = name not in ("leaves", "curtain", "glass_dirty", "glass", "paper", "tag_white", "tag_yellow")
    MATS[name] = m
    return m


# ================================================================================================ geometry -> Blender
def geo_object(geo, name, origin=(0, 0, 0)):
    """Blender mesh object from a Geo (vertices in world space; the object's origin is placed at `origin`)."""
    if len(geo) == 0:
        return None
    o = np.asarray(origin, float)
    V = (np.array(geo.V) - o).tolist()
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], geo.F)
    names = []
    idx = {}
    for mname in geo.M:
        if mname not in idx:
            idx[mname] = len(names)
            names.append(mname)
    for mname in names:
        me.materials.append(material(mname))
    me.polygons.foreach_set("material_index", np.array([idx[m] for m in geo.M], dtype=np.int32))
    smooth = np.array([m.startswith("rodin_") for m in geo.M], dtype=bool)
    if smooth.any():                                   # Hyper3D models are organic meshes: shade them smooth
        me.polygons.foreach_set("use_smooth", smooth)
    uvl = me.uv_layers.new(name="UVMap")
    flat = np.array([uv for f in geo.UV for uv in f], dtype=np.float32).ravel()
    if len(flat) == len(me.loops) * 2:
        uvl.data.foreach_set("uv", flat)
    me.uv_layers.new(name="LM")
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    ob.location = Vector(o)
    return ob


def text_object(body, size, loc, normal, mat, extrude=0.0015, font_scale=1.0):
    """Painted / chalk lettering facing `normal` (horizontal), converted to a mesh object."""
    cu = bpy.data.curves.new("txt", "FONT")
    cu.body = body
    cu.size = size
    cu.extrude = extrude
    cu.align_x = "CENTER"
    cu.align_y = "CENTER"
    cu.space_line = 1.1
    ob = bpy.data.objects.new("txt", cu)
    COL.objects.link(ob)
    yaw = math.atan2(normal[0], -normal[1])
    ob.rotation_euler = Euler((math.radians(90), 0.0, yaw))
    ob.location = Vector(loc)
    ob.data.materials.append(material(mat))
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    me.transform(ob.matrix_world)
    bpy.data.objects.remove(ob, do_unlink=True)
    mo = bpy.data.objects.new("txt_mesh", me)
    COL.objects.link(mo)
    return mo


def join_into(target, others):
    others = [o for o in others if o is not None]
    if not others:
        return target
    for o in list(scene.objects):
        o.select_set(False)
    for o in others:
        o.select_set(True)
    target.select_set(True)
    view_layer.objects.active = target
    bpy.ops.object.join()
    return target


def ensure_lm(ob):
    me = ob.data
    if "LM" not in me.uv_layers:
        me.uv_layers.new(name="LM")


# ================================================================================================ build
L = layout.build()
log("layout: %d walls, %d doors, %d windows, %d furniture, %d lights" % (len(L["walls"]), len(L["doors"]), len(L["windows"]),
                                                                        len(L["furniture"]), len(L["lights"])))
chunks, dyn = architecture.build(L)
static_objs = {}
for name, g in chunks.items():
    ob = geo_object(g, "arch_" + name)
    if ob is not None:
        static_objs[ob.name] = ob
log("architecture objects:", len(static_objs))

# furniture: static parts per room, moving parts on their own
furn_by_room = {}
dyn_meta = []
dyn_objs = {}
counters = {}
RODIN = rodin.available()
rodin_done = {}
rodin_info = {}
log("hyper3d models available: %d (%s)" % (len(RODIN), ", ".join(sorted(RODIN))))
for i, f in enumerate(L["furniture"]):
    fn = furniture.FURN.get(f["kind"])
    if fn is None:
        continue
    try:
        if f["kind"] in RODIN:
            if f["kind"] not in rodin_done:
                rg, rparts, info = rodin.load(f["kind"], RODIN[f["kind"]], fn)
                raw = info.pop("raw")
                if raw["image"]:
                    RODIN_TEX["rodin_" + f["kind"]] = (raw["image"], raw["mime"])
                rodin_done[f["kind"]] = (rg, rparts)
                rodin_info[f["kind"]] = info
                log("  hyper3d %-15s %6d tris, turned %5.0f deg, fit scores %s" % (f["kind"], info["tris"], info["yaw"], info["scores"]))
            g, parts = rodin_done[f["kind"]]
        else:
            g, parts = fn()
    except Exception as e:      # noqa: BLE001
        traceback.print_exc()
        log("FURNITURE FAILED", f["kind"], e)
        try:
            g, parts = fn()
        except Exception:       # noqa: BLE001
            continue
    R = rot_z(f["yaw"])
    base = np.array([f["x"], f["y"], f.get("z", 0.0)])
    room_key = f["room"] if f["room"] not in ("court",) else "veranda"
    fg = furn_by_room.setdefault(room_key, Geo("furn_" + room_key))
    fg.merge(g, R=R, T=base)
    for pname, (pg, off) in parts.items():
        k = counters.get(f["kind"], 0)
        oname = "%s_%d_%s" % (f["kind"], k, pname)
        pivot = base + R @ np.asarray(off, float)
        world = Geo(oname)
        world.merge(pg, R=R, T=pivot)
        ob = geo_object(world, oname, origin=pivot)
        if ob is not None:
            dyn_objs[oname] = ob
            dyn_meta.append({"name": oname, "kind": f["kind"], "part": pname, "furn": i, "pivot": navigation.to_godot(*pivot),
                             "yaw": f["yaw"]})
    if parts:
        counters[f["kind"]] = counters.get(f["kind"], 0) + 1
# light fixtures
for li, lt in enumerate(L["lights"]):
    if lt["room"] == "yard":
        continue
    g, _ = furniture.tube_light(lt["kind"] == "dead") if lt["kind"] in ("tube", "dead") else furniture.bulb()
    yaw = 0.0
    rk = lt["room"]
    if rk in [r["name"] for r in L["rooms"]]:
        rr = [r for r in L["rooms"] if r["name"] == rk][0]["rect"]
        yaw = 0.0 if (rr[2] - rr[0]) >= (rr[3] - rr[1]) else 90.0
    fg = furn_by_room.setdefault(rk, Geo("furn_" + rk))
    fg.merge(g, R=rot_z(yaw), T=(lt["x"], lt["y"], L["ceil_h"]))
g, _ = furniture.bulb()
furn_by_room.setdefault("yard", Geo("furn_yard")).merge(g, T=(0.0, -6.45, 3.25))
for rk, g in furn_by_room.items():
    ob = geo_object(g, "furn_" + rk)
    if ob is not None:
        static_objs[ob.name] = ob
log("furniture objects:", len(furn_by_room), "moving parts:", len(dyn_objs))


def _surface_z(g, lx, ly):
    """Height of the highest surface of g straight below (lx, ly), or None."""
    V = np.asarray(g.V, float)
    tris = np.array([(f[0], f[i], f[i + 1]) for f in g.F for i in range(1, len(f) - 1)])
    if not len(tris):
        return None
    A, B, C = V[tris[:, 0]], V[tris[:, 1]], V[tris[:, 2]]
    v0, v1 = B[:, :2] - A[:, :2], C[:, :2] - A[:, :2]
    v2 = np.array([lx, ly]) - A[:, :2]
    den = v0[:, 0] * v1[:, 1] - v1[:, 0] * v0[:, 1]
    ok = np.abs(den) > 1e-12
    den = np.where(ok, den, 1.0)
    b1 = (v2[:, 0] * v1[:, 1] - v1[:, 0] * v2[:, 1]) / den
    b2 = (v0[:, 0] * v2[:, 1] - v2[:, 0] * v0[:, 1]) / den
    inside = ok & (b1 >= 0) & (b2 >= 0) & (b1 + b2 <= 1)
    if not inside.any():
        return None
    z = A[:, 2] + b1 * (B[:, 2] - A[:, 2]) + b2 * (C[:, 2] - A[:, 2])
    return float(z[inside].max())


# items lying on Hyper3D furniture: put them on the model's real surface (and in front of a closed almirah)
for ik, iv in L["items"].items():
    for sp in iv["spots"]:
        kind = sp.get("on")
        if kind not in rodin_done:
            continue
        cands = [f for f in L["furniture"] if f["kind"] == kind]
        if not cands:
            continue
        f = min(cands, key=lambda f: (f["x"] - sp["x"]) ** 2 + (f["y"] - sp["y"]) ** 2)
        R = rot_z(f["yaw"])
        base = np.array([f["x"], f["y"], f.get("z", 0.0)])
        if kind == "almirah":
            w = base + R @ np.array([0.0, -0.62, 0.0])
            sp.update(x=float(w[0]), y=float(w[1]), z=0.0, on="floor")
            log("  %s: spot moved in front of the almirah (its doors no longer open)" % ik)
            continue
        loc = R.T @ (np.array([sp["x"], sp["y"], sp["z"]]) - base)
        zs = _surface_z(rodin_done[kind][0], loc[0], loc[1])
        if zs is not None:
            log("  %s on %s: height %.3f -> %.3f" % (ik, kind, sp["z"], base[2] + zs + 0.004))
            sp["z"] = float(base[2] + zs + 0.004)

# doors, planks, padlock (from the architecture)
for name, d in dyn.items():
    world = Geo(name)
    world.merge(d["geo"], T=d["pivot"])
    ob = geo_object(world, name, origin=d["pivot"])
    if ob is None:
        continue
    dyn_objs[name] = ob
    m = {k: v for k, v in d.items() if k != "geo"}
    m["name"] = name
    m["pivot"] = navigation.to_godot(*d["pivot"])
    dyn_meta.append(m)

# items (placed at the origin; the game puts each on one of its spots)
item_objs = {}
for name, g in item_models.all_items().items():
    ob = geo_object(g, name)
    if ob is not None:
        item_objs[name] = ob
        ob.location = Vector((0, 0, -50))           # out of the way of the bake
log("items:", ", ".join(item_objs))

# lettering: room names over the doors (veranda side), chalk on the boards, the school's name outside
texts = {}
for d in L["doors"]:
    r = [x for x in L["rooms"] if x["name"] == d["room"]][0]
    if d["kind"] in ("arch",) or d["room"] == "entrance":
        continue
    ix, iy = d["into"]
    n = (-ix, -iy)
    loc = (d["x"] + n[0] * (L["wall_t"] / 2 + 0.004), d["y"] + n[1] * (L["wall_t"] / 2 + 0.004), 2.55)
    sp = architecture.space_at(L, d["x"] + n[0] * 0.5, d["y"] + n[1] * 0.5)
    key = architecture.chunk_of(L, sp)
    try:
        texts.setdefault(key, []).append(text_object(r["label"], 0.13, loc, n, "paint_black"))
    except Exception as e:      # noqa: BLE001
        log("label failed", r["label"], e)
BOARD_TEXT = {"class5": "13-11-1998\nSILENCE !!", "class6": "DON'T LOOK BACK", "class7": "RAGINI MA'AM\nIS WATCHING",
              "class8": "3 DAYS"}
for f in L["furniture"]:
    if f["kind"] != "blackboard" or f["room"] not in BOARD_TEXT:
        continue
    a = math.radians(f["yaw"])
    n = (math.sin(a), -math.cos(a))                 # the board faces local -Y
    loc = (f["x"] + n[0] * 0.018, f["y"] + n[1] * 0.018, 1.62)
    try:
        texts.setdefault("furn_" + f["room"], []).append(text_object(BOARD_TEXT[f["room"]], 0.17, loc, n, "chalk", extrude=0.0005))
    except Exception as e:      # noqa: BLE001
        log("board text failed", e)
try:
    sign = Geo("sign")
    sign.box((0, -6.0 - L["wall_t"] / 2 - 0.05, 3.0), (4.6, 0.06, 0.62), "paint_white")
    so = geo_object(sign, "sign_board")
    t1 = text_object("ADARSH VIDYALAYA", 0.3, (0, -6.0 - L["wall_t"] / 2 - 0.085, 3.06), (0, -1), "paint_black", extrude=0.004)
    t2 = text_object("GOVT. SCHOOL   EST. 1962", 0.11, (0, -6.0 - L["wall_t"] / 2 - 0.085, 2.82), (0, -1), "paint_black", extrude=0.003)
    texts.setdefault("arch_outside", []).extend([so, t1, t2])
except Exception as e:      # noqa: BLE001
    log("sign failed", e)
for key, objs in texts.items():
    tgt = static_objs.get(key) or static_objs.get("arch_" + key)
    if tgt is None:
        continue
    join_into(tgt, objs)
for ob in list(static_objs.values()) + list(dyn_objs.values()) + list(item_objs.values()):
    ensure_lm(ob)
log("lettering joined")

# ================================================================================================ lights for the bake
LIGHT_OBJS = []


def add_light(kind, loc, energy, color, size=None, rot=None):
    ld = bpy.data.lights.new("L", kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
    elif kind == "POINT":
        ld.shadow_soft_size = 0.05
    elif kind == "SUN":
        ld.angle = math.radians(1.0)
    ob = bpy.data.objects.new("light", ld)
    scene.collection.objects.link(ob)
    ob.location = loc
    if rot is not None:
        ob.rotation_euler = rot
    LIGHT_OBJS.append(ob)
    return ob


E_TUBE, E_BULB = 34.0, 22.0
for lt in L["lights"]:
    if lt["kind"] == "dead":
        continue
    if lt["kind"] == "tube":
        rk = lt["room"]
        rr = [r for r in L["rooms"] if r["name"] == rk][0]["rect"]
        yaw = 0.0 if (rr[2] - rr[0]) >= (rr[3] - rr[1]) else math.radians(90)
        add_light("AREA", (lt["x"], lt["y"], L["ceil_h"] - 0.08), E_TUBE, (0.9, 0.96, 1.0), (1.2, 0.06), Euler((0, 0, yaw)))
    else:
        z = L["ceil_h"] - 0.46 if lt["room"] != "yard" else 3.0
        add_light("POINT", (lt["x"], lt["y"], z), E_BULB if lt["room"] != "yard" else 30.0, (1.0, 0.72, 0.42))
moon = add_light("SUN", (0, 0, 20), 0.22, (0.55, 0.66, 1.0), rot=Euler((math.radians(38), math.radians(-24), math.radians(28))))
scene.world = bpy.data.worlds.new("night")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.010, 0.013, 0.024, 1.0)
bg.inputs[1].default_value = 1.0
log("bake lights:", len(LIGHT_OBJS))

# ================================================================================================ lightmap UVs + bake
lightmaps = {}


def area_of(ob):
    me = ob.data
    a = np.zeros(len(me.polygons))
    me.polygons.foreach_get("area", a)
    return float(a.sum())


def lm_unwrap(ob):
    me = ob.data
    me.uv_layers.active = me.uv_layers["LM"]
    for o in list(scene.objects):
        o.select_set(False)
    ob.select_set(True)
    view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.012, area_weight=0.0, scale_to_bounds=True)
    bpy.ops.object.mode_set(mode="OBJECT")
    me.uv_layers.active = me.uv_layers["UVMap"]


def blur_in_islands(img, cov, it=2):
    for _ in range(it):
        acc = np.zeros_like(img)
        w = np.zeros(cov.shape)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                sc = np.roll(np.roll(cov, dy, 0), dx, 1)
                acc += np.roll(np.roll(img, dy, 0), dx, 1) * sc[..., None]
                w += sc
        img = np.where(cov[..., None], acc / np.maximum(w, 1)[..., None], img)
    return img


def bake(ob, density):
    area = area_of(ob)
    size = int(2 ** round(math.log2(max(64.0, min(1024.0 if not QUICK else 256.0, math.sqrt(area) * density)))))
    img = bpy.data.images.new("lm_" + ob.name, size, size, alpha=True, float_buffer=True)
    for slot in ob.material_slots:
        m = slot.material
        if m is None or not m.use_nodes:
            continue
        n = m.node_tree.nodes.get("LM_BAKE")
        if n is None:
            n = m.node_tree.nodes.new("ShaderNodeTexImage")
            n.name = "LM_BAKE"
        n.image = img
        m.node_tree.nodes.active = n
    me = ob.data
    me.uv_layers.active = me.uv_layers["LM"]
    me.uv_layers["LM"].active_render = True
    for o in list(scene.objects):
        o.select_set(False)
    ob.select_set(True)
    view_layer.objects.active = ob
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, margin=3, use_clear=True, target="IMAGE_TEXTURES")
    me.uv_layers["UVMap"].active_render = True
    me.uv_layers.active = me.uv_layers["UVMap"]
    px = np.zeros(size * size * 4, np.float32)
    img.pixels.foreach_get(px)
    px = px.reshape(size, size, 4)
    cov = px[..., 3] > 0.5
    lm = blur_in_islands(px[..., :3].astype(np.float64), cov, 2)
    enc = np.clip(lm / LM_SCALE, 0.0, 1.0) ** (1.0 / 2.2)
    out = bpy.data.images.new("lmo_" + ob.name, size, size, alpha=False, float_buffer=False)
    rgba = np.ones((size, size, 4), np.float32)
    rgba[..., :3] = enc
    out.pixels.foreach_set(rgba.ravel())
    rel = "lightmaps/%s.png" % ob.name
    out.filepath_raw = os.path.join(OUT, rel)
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(img)
    bpy.data.images.remove(out)
    lightmaps[ob.name] = {"file": rel, "size": size, "mean": float(lm[cov].mean()) if cov.any() else 0.0}
    return size


if DO_BAKE:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16 if QUICK else 72
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 3
    try:
        scene.cycles.use_denoising = False
    except Exception:       # noqa: BLE001
        pass
    for ob in item_objs.values():
        ob.hide_render = True
    tb = time.time()
    for name, ob in static_objs.items():
        if name in ("arch_roof",):
            continue
        try:
            lm_unwrap(ob)
            density = 44.0 if name.startswith("furn_") else 22.0
            if name == "arch_yard":
                density = 6.0
            s = bake(ob, density)
            log("  baked %-22s %4d px  mean %.3f" % (name, s, lightmaps[name]["mean"]))
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("BAKE FAILED", name, e)
    log("lightmaps baked: %d in %.0fs" % (len(lightmaps), time.time() - tb))
    for ob in item_objs.values():
        ob.hide_render = False

# ================================================================================================ meta + export
G = navigation.grid(L)
st = navigation.cell_of(G, L["ragini_start"]["x"], L["ragini_start"]["y"])
log("walk grid %dx%d, reachable cells %d" % (G["nx"], G["ny"], int(navigation.reach(G, st).sum())))


def gp(x, y, z=0.0):
    return navigation.to_godot(x, y, z)


meta = {
    "lm_scale": LM_SCALE, "lightmaps": lightmaps, "ceil_h": L["ceil_h"], "base_colors": BASE, "emit": EMIT,
    "footprints": {k: v for k, v in furniture.FOOTPRINT.items() if v},
    "hyper3d": rodin_info,
    "colliders": navigation.colliders(L),
    "grid": navigation.export_grid(G),
    "doors": [dict(d, pos=gp(d["x"], d["y"]), into_g=[d["into"][0], 0, -d["into"][1]]) for d in L["doors"]],
    "dynamic": dyn_meta,
    "items": {k: {"label": v["label"], "spots": [dict(s, pos=gp(s["x"], s["y"], s["z"])) for s in v["spots"]]} for k, v in L["items"].items()},
    "lights": [dict(lt, pos=gp(lt["x"], lt["y"], lt["z"])) for lt in L["lights"]],
    "rooms": [dict(r, center=gp((r["rect"][0] + r["rect"][2]) / 2, (r["rect"][1] + r["rect"][3]) / 2)) for r in L["rooms"]],
    "furniture": [dict(f, pos=gp(f["x"], f["y"], f.get("z", 0.0))) for f in L["furniture"]],
    "hides": L["hides"],
    "patrol": [gp(x, y) for (x, y) in L["patrol"]],
    "spawn": dict(L["spawn"], pos=gp(L["spawn"]["x"], L["spawn"]["y"])),
    "ragini_start": gp(L["ragini_start"]["x"], L["ragini_start"]["y"]),
    "outside": {k: gp(v[0], v[1]) for k, v in L["outside"].items()},
    "court": [gp(L["court"][0], L["court"][1]), gp(L["court"][2], L["court"][3])],
    "building": [gp(L["building"][0], L["building"][1]), gp(L["building"][2], L["building"][3])],
    "moon_dir": list(moon.matrix_world.to_quaternion() @ Vector((0, 0, -1))),
}
json.dump(meta, open(os.path.join(OUT, "school_meta.json"), "w"))
for ob in item_objs.values():
    ob.location = Vector((0, 0, 0))
for o in list(scene.objects):
    o.select_set(o.type == "MESH")
props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
kw = dict(filepath=os.path.join(OUT, "school.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
          export_texcoords=True, export_normals=True, export_materials="EXPORT", export_cameras=False, export_lights=False,
          export_animations=False, export_image_format="AUTO", export_extras=False)
bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props})
log("exported school.glb %.1f MB" % (os.path.getsize(os.path.join(OUT, "school.glb")) / 1e6))

# ================================================================================================ previews
try:
    import preview_school
    preview_school.render_all(scene, L, OUT, log, quick=QUICK)
except Exception as e:      # noqa: BLE001
    traceback.print_exc()
    log("PREVIEWS FAILED:", e)
for ob in item_objs.values():
    ob.location = Vector((0, 0, -50))
try:
    bpy.ops.file.pack_all()
except Exception:       # noqa: BLE001
    pass
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "school.blend"), compress=True)
log("saved school.blend - done")
