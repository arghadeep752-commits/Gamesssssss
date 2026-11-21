"""Builds the trader's house in Blender and exports it for Unity.

    blender -b -noaudio -P tools/house/build_house.py -- OUT_DIR [--no-bake] [--quick] [--no-previews]

* walls, floors, ceilings, stair, windows, doors and the plot from architecture.py; furniture from props.py, with
  the Hyper3D (Rodin) models fitted into their footprints where present (rodin_fit.py)
* one object per room for the building and one for its furniture, so each gets its own baked lightmap
* night lighting (downlights, pendants, lamps, moonlight, garden and street lights) baked in Cycles into lightmaps
  on a second UV set; the trading room is baked twice: without power and with power (lights, LED cove, monitors)
* doors, the main door's planks / padlocks / keypad light, the safe door, the locked drawer, the fuse box door, the
  six monitor screens, the LED strip and the items stay separate objects (they move or change)
* exports house.glb, house_meta.json, lightmaps/*.png, house.blend and preview renders
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
import architecture  # noqa: E402
import layout as LY  # noqa: E402
import navigation  # noqa: E402
import props  # noqa: E402
import rodin_fit  # noqa: E402
from geo import Geo, rot_z  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build/house"]
OUT = os.path.abspath(argv[0])
DO_BAKE = "--no-bake" not in argv
QUICK = "--quick" in argv
PREVIEWS = "--no-previews" not in argv
os.makedirs(os.path.join(OUT, "lightmaps"), exist_ok=True)
T0 = time.time()
_logf = open(os.path.join(OUT, "build_log.txt"), "w")
LM_SCALE = 4.0
ENERGY = 2.0          # all bake lights are scaled by this


def log(*a):
    s = "[%6.1fs] " % (time.time() - T0) + " ".join(str(x) for x in a)
    print(s, flush=True)
    _logf.write(s + "\n")
    _logf.flush()


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
view_layer = bpy.context.view_layer
COL = bpy.data.collections.new("House")
scene.collection.children.link(COL)

# ================================================================================================ materials
BASE = {
    "wall_plaster": (0.8, 0.78, 0.74), "wall_concrete": (0.52, 0.52, 0.5), "wall_tiles": (0.82, 0.82, 0.8),
    "wall_dark": (0.13, 0.13, 0.15), "wall_ext": (0.85, 0.84, 0.8), "cladding": (0.45, 0.3, 0.18),
    "ceiling": (0.86, 0.86, 0.84), "ceiling_dark": (0.1, 0.1, 0.11), "floor_oak": (0.55, 0.4, 0.27),
    "floor_dark": (0.22, 0.15, 0.1), "floor_stone": (0.62, 0.6, 0.57), "floor_tiles": (0.75, 0.75, 0.73),
    "floor_concrete": (0.45, 0.45, 0.43), "threshold": (0.3, 0.3, 0.3), "reveal": (0.8, 0.78, 0.74),
    "sill": (0.9, 0.9, 0.88), "door_frame": (0.86, 0.86, 0.84), "door_white": (0.88, 0.88, 0.86),
    "door_wood": (0.3, 0.2, 0.12), "frame_alu": (0.06, 0.06, 0.065), "shutter": (0.5, 0.5, 0.52),
    "stair_oak": (0.55, 0.4, 0.27), "stair_riser": (0.86, 0.86, 0.84), "stair_side": (0.8, 0.78, 0.74),
    "roof": (0.4, 0.4, 0.38), "concrete": (0.5, 0.5, 0.48), "grass": (0.13, 0.2, 0.08), "paving": (0.45, 0.43, 0.4),
    "hedge": (0.08, 0.16, 0.05), "glass": (0.2, 0.25, 0.27), "keypad_face": (0.05, 0.06, 0.07),
    "keypad_led": (0.9, 0.1, 0.05), "wood_plank": (0.42, 0.32, 0.2), "steel": (0.6, 0.6, 0.6),
    "marble": (0.88, 0.87, 0.85), "marble_black": (0.05, 0.05, 0.05), "cabinet_white": (0.86, 0.86, 0.84),
    "cabinet_oak": (0.5, 0.36, 0.23), "wood_walnut": (0.28, 0.18, 0.11), "wood_oak": (0.55, 0.4, 0.26),
    "wood_handle": (0.5, 0.33, 0.18), "fabric_grey": (0.42, 0.42, 0.41), "fabric_light": (0.6, 0.58, 0.55),
    "rug_fabric": (0.55, 0.52, 0.47), "rug_dark": (0.12, 0.12, 0.13), "lampshade": (0.85, 0.8, 0.7),
    "bulb_glow": (1.0, 0.85, 0.6), "led": (0.55, 0.35, 1.0), "screen": (0.02, 0.025, 0.035),
    "metal_black": (0.03, 0.03, 0.03), "metal_brushed": (0.6, 0.6, 0.6), "metal_painted": (0.4, 0.42, 0.43),
    "safe_steel": (0.12, 0.12, 0.13), "felt_dark": (0.08, 0.05, 0.05), "ceramic_white": (0.88, 0.88, 0.87),
    "appliance_white": (0.86, 0.86, 0.85), "glass_black": (0.02, 0.02, 0.02), "glass_rgb": (0.25, 0.1, 0.35),
    "plastic_black": (0.03, 0.03, 0.03), "plastic_grey": (0.3, 0.3, 0.3), "plastic_blue": (0.1, 0.25, 0.55),
    "cardboard": (0.45, 0.34, 0.22), "pegboard": (0.55, 0.45, 0.3), "leather_black": (0.04, 0.04, 0.04),
    "leather_red": (0.5, 0.04, 0.03), "paint_red": (0.6, 0.05, 0.03), "brass": (0.6, 0.45, 0.15),
    "gold": (0.8, 0.6, 0.15), "mirror": (0.3, 0.32, 0.33), "sink_dark": (0.05, 0.05, 0.05),
    "deskmat": (0.03, 0.03, 0.035), "fuse_panel": (0.2, 0.2, 0.2), "bedding_white": (0.85, 0.85, 0.84),
    "bark": (0.25, 0.18, 0.12), "leaves": (0.1, 0.25, 0.08),
}
EMIT = {"bulb_glow": 6.0, "keypad_led": 2.0}
METAL = {"steel", "metal_brushed", "brass", "gold", "mirror", "safe_steel"}
TWO_SIDED = {"glass", "leaves", "hedge"}
MATS = {}
_dummy_lm = bpy.data.images.new("lm_dummy", 4, 4, alpha=False, float_buffer=False)
_dummy_lm.pixels.foreach_set(np.full(64, 0.5, np.float32))
_gltf_group = None
RODIN_TEX = {}
TEXD = os.path.join(OUT, "rodin_tex")


def gltf_output_group():
    """Blender's glTF exporter reads an 'Occlusion' input from a node group with this name; it carries the
    lightmap UV set (LM) out as TEXCOORD_1."""
    global _gltf_group
    if _gltf_group is not None:
        return _gltf_group
    ng = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
    try:
        ng.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
    except Exception:       # noqa: BLE001
        ng.inputs.new("NodeSocketFloat", "Occlusion")
    _gltf_group = ng
    return ng


def rodin_image(name):
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
    b.inputs["Roughness"].default_value = 0.35 if name in METAL else 0.8
    b.inputs["Metallic"].default_value = 0.0
    if name in EMIT:
        key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
        b.inputs[key].default_value = (c[0], c[1], c[2], 1.0)
        if "Emission Strength" in b.inputs:
            b.inputs["Emission Strength"].default_value = EMIT[name]
    if name == "glass":
        try:
            b.inputs["Alpha"].default_value = 0.15
            m.blend_method = "BLEND"
        except Exception:       # noqa: BLE001
            pass
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
    m.use_backface_culling = name not in TWO_SIDED
    MATS[name] = m
    return m


def set_emission(name, strength, color=None):
    m = MATS.get(name)
    if m is None:
        return
    b = m.node_tree.nodes.get("Principled BSDF")
    key = "Emission Color" if "Emission Color" in b.inputs else "Emission"
    c = color or BASE.get(name, (1, 1, 1))
    b.inputs[key].default_value = (c[0], c[1], c[2], 1.0)
    if "Emission Strength" in b.inputs:
        b.inputs["Emission Strength"].default_value = strength


# ================================================================================================ geometry -> Blender
def geo_object(geo, name, origin=(0, 0, 0)):
    if geo is None or len(geo) == 0:
        return None
    o = np.asarray(origin, float)
    V = (np.array(geo.V) - o).tolist()
    me = bpy.data.meshes.new(name)
    me.from_pydata(V, [], geo.F)
    names, idx = [], {}
    for mname in geo.M:
        if mname not in idx:
            idx[mname] = len(names)
            names.append(mname)
    for mname in names:
        me.materials.append(material(mname))
    me.polygons.foreach_set("material_index", np.array([idx[m] for m in geo.M], dtype=np.int32))
    smooth = np.array([m.startswith("rodin_") for m in geo.M], dtype=bool)
    if smooth.any():
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


def ensure_lm(ob):
    if "LM" not in ob.data.uv_layers:
        ob.data.uv_layers.new(name="LM")


# ================================================================================================ build
L = LY.build()
chunks, dyn, coll, extra = architecture.build(L)
RODIN = rodin_fit.available()
log("layout: %d rooms, %d walls, %d doors, %d windows, %d furniture" % (len(L["rooms"]), len(L["walls"]), len(L["doors"]),
                                                                        len(L["windows"]), len(L["furniture"])))
log("hyper3d models available: %d (%s)" % (len(RODIN), ", ".join(sorted(RODIN))))

static_objs = {}
for name, g in chunks.items():
    ob = geo_object(g, name)
    if ob is not None:
        static_objs[name] = ob
log("architecture objects:", len(static_objs))

# ---------------------------------------------------------------------------------------------- furniture
furn_by_room = {}
dyn_objs = {}
dyn_meta = []
fitted = {}          # kind -> (geo, parts, info)
hyper_info = {}
heights = {}


def piece(kind):
    if kind in fitted:
        return fitted[kind]
    model = props.RODIN.get(kind)
    g, parts, info = None, {}, None
    if model and model in RODIN:
        try:
            w, d, h, _ = props.FOOTPRINT[kind]
            g, info = rodin_fit.fit_furniture(model, RODIN[model], w, d, h, kind)
            r = rodin_fit.raw(model, RODIN[model])
            if r["image"] and "rodin_" + model not in RODIN_TEX:
                RODIN_TEX["rodin_" + model] = (r["image"], r["mime"])
            hyper_info[kind] = info
            log("  hyper3d %-14s %6d tris, turned %4.0f deg, scale %s" % (kind, info["tris"], info["turn"], info["scale"]))
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("HYPER3D FAILED", kind, e)
            g = None
    if g is None:
        fn = props.BUILDERS.get(kind)
        if fn is None:
            fitted[kind] = (None, {}, None)
            return fitted[kind]
        g, parts = fn()
    fitted[kind] = (g, parts, info)
    return fitted[kind]


for i, f in enumerate(L["furniture"]):
    try:
        g, parts, info = piece(f["kind"])
    except Exception as e:      # noqa: BLE001
        traceback.print_exc()
        log("FURNITURE FAILED", f["kind"], e)
        continue
    R = rot_z(f["yaw"])
    base = np.array([f["x"], f["y"], f["z"]])
    if g is not None and len(g):
        fg = furn_by_room.setdefault(f["room"], Geo("furn_" + f["room"]))
        fg.merge(g, R=R, T=base)
        V = np.asarray(g.V, float)
        heights[f["kind"]] = float(V[:, 2].max()) if len(V) else 0.0
    for pname, (pg, off) in parts.items():
        pivot = base + R @ np.asarray(off, float)
        world = Geo(pname)
        world.merge(pg, R=R, T=pivot)
        ob = geo_object(world, pname, origin=pivot)
        if ob is not None:
            dyn_objs[pname] = ob
            dyn_meta.append({"name": pname, "kind": f["kind"], "part": pname, "pivot": navigation.U(*pivot), "yaw": f["yaw"],
                             "room": f["room"]})
for rk, g in furn_by_room.items():
    ob = geo_object(g, "furn_" + rk)
    if ob is not None:
        static_objs[ob.name] = ob
log("furniture objects:", len(furn_by_room), "moving parts:", len(dyn_objs))

# items lying on Hyper3D furniture: put them on the model's real surface
for ik, iv in L["items"].items():
    for sp in iv["spots"]:
        kind = sp.get("on")
        if kind in (None, "floor") or kind not in fitted or fitted[kind][2] is None:
            continue
        cands = [f for f in L["furniture"] if f["kind"] == kind]
        if not cands:
            continue
        f = min(cands, key=lambda f: (f["x"] - sp["x"]) ** 2 + (f["y"] - sp["y"]) ** 2)
        R = rot_z(f["yaw"])
        base = np.array([f["x"], f["y"], f["z"]])
        loc = R.T @ (np.array([sp["x"], sp["y"], sp["z"]]) - base)
        zs = rodin_fit.surface_z(fitted[kind][0], loc[0], loc[1], zmax=loc[2] + 0.45)
        if zs is not None:
            log("  %s on %s: height %.3f -> %.3f" % (ik, kind, sp["z"], base[2] + zs + 0.004))
            sp["z"] = float(base[2] + zs + 0.004)

# ---------------------------------------------------------------------------------------------- the main door's dynamic parts
for name, d in dyn.items():
    g = d.get("geo")
    if name.startswith("padlock_"):
        try:
            if "padlock" in RODIN:
                g = rodin_fit.fit_box("padlock", RODIN["padlock"], props.ITEM_BOX["padlock"], name)
                r = rodin_fit.raw("padlock", RODIN["padlock"])
                if r["image"] and "rodin_padlock" not in RODIN_TEX:
                    RODIN_TEX["rodin_padlock"] = (r["image"], r["mime"])
            else:
                g = props.item_geo("padlock")
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("PADLOCK FAILED", e)
            g = props.item_geo("padlock")
    if g is None:
        continue
    world = Geo(name)
    world.merge(g, T=d["pivot"])
    ob = geo_object(world, name, origin=d["pivot"])
    if ob is None:
        continue
    dyn_objs[name] = ob
    m = {k: v for k, v in d.items() if k not in ("geo",)}
    m["name"] = name
    m["pivot"] = navigation.U(*d["pivot"])
    if "leaf_dir" in m:
        m["leaf_dir"] = [m["leaf_dir"][0], 0.0, m["leaf_dir"][1]]
    if "into" in m:
        m["into"] = [m["into"][0], 0.0, m["into"][1]]
    dyn_meta.append(m)

# ---------------------------------------------------------------------------------------------- items (at the origin; the game places them)
item_objs = {}
for name in ("garage_key", "gold_key", "silver_key", "drawer_key", "hammer", "fuse"):
    g = None
    model = props.ITEM_RODIN.get(name)
    if model in RODIN:
        try:
            g = rodin_fit.fit_box(model, RODIN[model], props.ITEM_BOX[name], "item_" + name)
            r = rodin_fit.raw(model, RODIN[model])
            if r["image"] and "rodin_" + model not in RODIN_TEX:
                RODIN_TEX["rodin_" + model] = (r["image"], r["mime"])
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("HYPER3D ITEM FAILED", name, e)
            g = None
    if g is None:
        g = props.item_geo(name)
    ob = geo_object(g, "item_" + name)
    if ob is not None:
        item_objs[name] = ob
        ob.location = Vector((0, 0, -50))
log("items:", ", ".join(item_objs))
for ob in list(static_objs.values()) + list(dyn_objs.values()) + list(item_objs.values()):
    ensure_lm(ob)

# ================================================================================================ lights
LIGHT_OBJS = {"house": [], "trading": [], "outside": []}


def add_light(group, kind, loc, energy, color, size=None, rot=None, spot=None):
    ld = bpy.data.lights.new("L", kind)
    ld.energy = energy * ENERGY
    ld.color = color
    if kind == "AREA":
        ld.shape = "RECTANGLE"
        ld.size, ld.size_y = size
    elif kind in ("POINT", "SPOT"):
        ld.shadow_soft_size = 0.05
    if kind == "SPOT":
        ld.spot_size = math.radians(spot or 120.0)
        ld.spot_blend = 0.55
    if kind == "SUN":
        ld.angle = math.radians(1.0)
    ob = bpy.data.objects.new("light", ld)
    scene.collection.objects.link(ob)
    ob.location = loc
    if rot is not None:
        ob.rotation_euler = rot
    LIGHT_OBJS[group].append(ob)
    return ob


def make_light(group, lt):
    k, x, y, z, e, c = lt["kind"], lt["x"], lt["y"], lt["z"], lt["energy"], tuple(lt["color"])
    if k == "down":
        add_light(group, "SPOT", (x, y, z), e * 1.6, c, spot=125.0)
    elif k in ("pendant", "lamp", "ceiling", "garden"):
        add_light(group, "POINT", (x, y, z), e, c)
    elif k == "tube":
        add_light(group, "AREA", (x, y, z), e, c, (1.2, 0.08))
    elif k == "strip":
        w, d = 8.3, 5.9
        for (px, py, sx, sy) in ((x, y - d / 2, w, 0.05), (x, y + d / 2, w, 0.05), (x - w / 2, y, 0.05, d), (x + w / 2, y, 0.05, d)):
            add_light(group, "AREA", (px, py, z), e / 4.0, c, (sx, sy))
    elif k == "screen":
        add_light(group, "AREA", (x, y, z), e, c, (2.0, 0.8), Euler((math.radians(-90), 0, 0)))   # faces south
    elif k == "street":
        add_light(group, "SPOT", (x, y + 0.3, z), e, c, spot=100.0)


for lt in L["lights"]:
    make_light("house", lt)
for lt in L["trading_lights"]:
    make_light("trading", lt)
for lt in L["outside_lights"]:
    make_light("outside", lt)
moon = add_light("outside", "SUN", (0, 0, 30), 0.12, (0.55, 0.66, 1.0), rot=Euler((math.radians(52), math.radians(-18), math.radians(32))))
scene.world = bpy.data.worlds.new("night")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
bg.inputs[0].default_value = (0.008, 0.011, 0.022, 1.0)
bg.inputs[1].default_value = 1.0
log("bake lights: house %d, trading %d, outside %d" % tuple(len(LIGHT_OBJS[k]) for k in ("house", "trading", "outside")))


def trading_power(on):
    """The trading room's lights, LED cove and monitors: off until the fuse goes in."""
    for ob in LIGHT_OBJS["trading"]:
        ob.hide_render = not on
    set_emission("led", 5.0 if on else 0.0)
    set_emission("screen", 2.5 if on else 0.0, (0.25, 0.55, 1.0))


def show_dynamic(on):
    """Doors, planks, padlocks, the safe door, drawer, screens ... are left out of the bake (they move or open)."""
    for ob in dyn_objs.values():
        ob.hide_render = not on


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


def bake(ob, density, suffix=""):
    area = area_of(ob)
    size = int(2 ** round(math.log2(max(64.0, min(1024.0 if not QUICK else 256.0, math.sqrt(area) * density)))))
    img = bpy.data.images.new("lm_" + ob.name + suffix, size, size, alpha=True, float_buffer=True)
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
    out = bpy.data.images.new("lmo_" + ob.name + suffix, size, size, alpha=False, float_buffer=False)
    rgba = np.ones((size, size, 4), np.float32)
    rgba[..., :3] = enc
    out.pixels.foreach_set(rgba.ravel())
    rel = "lightmaps/%s%s.png" % (ob.name, suffix)
    out.filepath_raw = os.path.join(OUT, rel)
    out.file_format = "PNG"
    out.save()
    bpy.data.images.remove(img)
    bpy.data.images.remove(out)
    mean = float(lm[cov].mean()) if cov.any() else 0.0
    return rel, size, mean


if DO_BAKE:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16 if QUICK else 64
    scene.cycles.max_bounces = 4
    scene.cycles.diffuse_bounces = 3
    try:
        scene.cycles.use_denoising = False
    except Exception:       # noqa: BLE001
        pass
    for ob in item_objs.values():
        ob.hide_render = True
    if "glass" in static_objs:
        static_objs["glass"].hide_render = True
    show_dynamic(False)
    trading_power(False)
    tb = time.time()
    for name, ob in static_objs.items():
        if name == "glass":
            continue
        try:
            lm_unwrap(ob)
            density = 40.0 if name.startswith("furn_") else 20.0
            if name == "arch_outside":
                density = 6.0
            rel, s, mean = bake(ob, density)
            lightmaps[name] = {"file": rel, "size": s, "mean": mean}
            log("  baked %-18s %4d px  mean %.3f" % (name, s, mean))
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("BAKE FAILED", name, e)
    # the trading room again, with the power on
    trading_power(True)
    for name in ("arch_trading", "furn_trading", "arch_corridor"):
        ob = static_objs.get(name)
        if ob is None or name not in lightmaps:
            continue
        try:
            density = 40.0 if name.startswith("furn_") else 20.0
            rel, s, mean = bake(ob, density, "_on")
            lightmaps[name]["on"] = rel
            lightmaps[name]["mean_on"] = mean
            log("  baked %-18s %4d px  mean %.3f (power on)" % (name, s, mean))
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("BAKE FAILED (power on)", name, e)
    log("lightmaps baked: %d in %.0fs" % (len(lightmaps), time.time() - tb))
    for ob in item_objs.values():
        ob.hide_render = False

# ================================================================================================ meta + export
import house_meta  # noqa: E402
meta, G = house_meta.make(L, coll, extra, dyn_meta, hyper_info, heights, lightmaps, BASE, EMIT,
                          moon.matrix_world.to_quaternion() @ Vector((0, 0, -1)), LM_SCALE)
spawn_c = (int(LY.SPAWN["x"] / G["cell"]), int(LY.SPAWN["y"] / G["cell"]))
log("walk grid %dx%d x3 layers, reachable from the spawn: %d cells" % (G["nx"], G["ny"], len(navigation.reach(G, LY.SPAWN["floor"], spawn_c))))
json.dump(meta, open(os.path.join(OUT, "house_meta.json"), "w"))
for ob in item_objs.values():
    ob.location = Vector((0, 0, 0))
trading_power(False)
for o in list(scene.objects):
    o.select_set(o.type == "MESH")
props_kw = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
kw = dict(filepath=os.path.join(OUT, "house.glb"), export_format="GLB", use_selection=True, export_apply=True, export_yup=True,
          export_texcoords=True, export_normals=True, export_materials="EXPORT", export_cameras=False, export_lights=False,
          export_animations=False, export_image_format="AUTO", export_extras=False)
bpy.ops.export_scene.gltf(**{k: v for k, v in kw.items() if k in props_kw})
log("exported house.glb %.1f MB" % (os.path.getsize(os.path.join(OUT, "house.glb")) / 1e6))

# ================================================================================================ previews
VIEWS = [
    ("living", (8.4, 0.9, 1.65), (15.5, 5.0, 0.9)),
    ("kitchen", (9.8, 6.9, 1.7), (15.2, 11.0, 1.0)),
    ("hall_stair", (8.4, 0.8, 1.7), (5.8, 9.0, 2.2)),
    ("trading_room", (9.9, 0.8, 4.95), (13.5, 6.0, 4.2)),
    ("master_bedroom", (10.0, 7.0, 4.95), (14.5, 11.5, 3.9)),
    ("guest_bedroom", (2.9, 1.5, 4.95), (2.6, 6.4, 4.4)),
    ("garage", (4.4, 0.8, 1.75), (0.6, 6.5, 0.9)),
    ("outside_front", (9.0, -9.6, 1.8), (8.5, 0.0, 3.2)),
]


def render_previews():
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 12 if QUICK else 28
    scene.render.resolution_x, scene.render.resolution_y = 960, 540
    scene.render.resolution_percentage = 100
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:       # noqa: BLE001
        try:
            scene.view_settings.view_transform = "Filmic"
        except Exception:       # noqa: BLE001
            pass
    for ob in item_objs.values():
        ob.hide_render = True
    show_dynamic(True)
    if "glass" in static_objs:
        static_objs["glass"].hide_render = False
    cam_d = bpy.data.cameras.new("cam")
    cam_d.lens = 18.0
    cam = bpy.data.objects.new("cam", cam_d)
    scene.collection.objects.link(cam)
    scene.camera = cam
    for name, loc, look in VIEWS:
        try:
            trading_power(name == "trading_room")
            cam.location = Vector(loc)
            d = Vector(look) - Vector(loc)
            cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
            scene.render.filepath = os.path.join(OUT, "preview_%s.png" % name)
            bpy.ops.render.render(write_still=True)
            log("  preview", name)
        except Exception as e:      # noqa: BLE001
            traceback.print_exc()
            log("PREVIEW FAILED", name, e)
    trading_power(False)


if PREVIEWS:
    render_previews()
try:
    bpy.ops.file.pack_all()
except Exception:       # noqa: BLE001
    pass
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "house.blend"), compress=True)
log("saved house.blend - done")
