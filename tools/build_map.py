"""Chaya - builds the house in Blender and exports it for Godot.

    blender -b -P tools/build_map.py -- layout.json out_dir [--no-bake]

* tools/mazegeo.py supplies the geometry of every wall, floor, door, pedestal and ritual object as numpy arrays
  (Godot axes: x east, y up, z south).
* This script turns it into real Blender meshes (one object per chunk of the house, one per door, one per item),
  gives every surface a named Principled material, bakes ambient occlusion into vertex colours with Cycles,
  saves chaya_map.blend and exports maze.glb (with tangents and the baked colours) plus meta.json.
"""
import json
import os
import sys
import time

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mazegeo  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
layout_path, out_dir = argv[0], argv[1]
DO_BAKE = "--no-bake" not in argv
os.makedirs(out_dir, exist_ok=True)

t0 = time.time()
L = json.load(open(layout_path))
objs, meta = mazegeo.build(L)
print("geometry: %d objects, %d triangles" % (len(objs), sum(len(i) // 3 for o in objs for (_, _, _, i) in o.prims.values())))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ----------------------------------------------------------------------------------------------- materials
BASE_COLOR = {
    "floor_wood": (0.30, 0.20, 0.12), "floor_stone": (0.35, 0.33, 0.30), "wall_wood": (0.22, 0.14, 0.09),
    "wall_plaster": (0.45, 0.40, 0.33), "ceiling_wood": (0.20, 0.13, 0.08), "trim_wood": (0.16, 0.10, 0.06),
    "door_wood": (0.20, 0.12, 0.07), "brass": (0.80, 0.60, 0.20), "stone_altar": (0.50, 0.45, 0.40),
    "red_cloth": (0.60, 0.05, 0.05), "clay": (0.55, 0.28, 0.16), "coconut": (0.32, 0.20, 0.10),
    "kumkum_red": (0.80, 0.04, 0.03), "camphor_white": (0.92, 0.92, 0.88), "copper": (0.72, 0.40, 0.25),
    "leaf_green": (0.14, 0.32, 0.10), "lantern_glow": (1.0, 0.6, 0.25), "lantern_metal": (0.10, 0.09, 0.08),
    "rope": (0.45, 0.35, 0.22),
}
METAL = {"brass", "copper", "lantern_metal"}
mat_cache = {}


def get_material(name):
    if name in mat_cache:
        return mat_cache[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf is not None:
        c = BASE_COLOR.get(name, (0.5, 0.5, 0.5))
        bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
        bsdf.inputs["Roughness"].default_value = 0.4 if name in METAL else 0.9
        bsdf.inputs["Metallic"].default_value = 0.9 if name in METAL else 0.0
    m.diffuse_color = (*BASE_COLOR.get(name, (0.5, 0.5, 0.5)), 1.0)
    mat_cache[name] = m
    return m


# ----------------------------------------------------------------------------------------------- meshes
def to_blender(v):
    """glTF/Godot (x, y, z) -> Blender (x, -z, y). The glTF exporter converts it back."""
    v = np.asarray(v, dtype=np.float64)
    return np.stack([v[:, 0], -v[:, 2], v[:, 1]], axis=1)


collection = bpy.data.collections.new("ChayaHouse")
scene.collection.children.link(collection)
blender_objs = []
use_custom_normals = True

for o in objs:
    verts, norms, uvs, faces, mat_idx = [], [], [], [], []
    mats = list(o.prims.keys())
    off = 0
    for mi, m in enumerate(mats):
        P, N, UV, I = o.prims[m]
        verts.append(to_blender(P))
        norms.append(to_blender(N))
        uvs.append(np.asarray(UV, dtype=np.float64))
        f = (np.asarray(I, dtype=np.int64) + off).reshape(-1, 3)
        faces.append(f)
        mat_idx.append(np.full(len(f), mi, dtype=np.int32))
        off += len(P)
    V = np.concatenate(verts)
    Nn = np.concatenate(norms)
    UVv = np.concatenate(uvs)
    F = np.concatenate(faces)
    MI = np.concatenate(mat_idx)

    mesh = bpy.data.meshes.new(o.name)
    mesh.from_pydata(V.tolist(), [], F.tolist())
    mesh.update()
    for m in mats:
        mesh.materials.append(get_material(m))
    mesh.polygons.foreach_set("material_index", MI)
    # UVs: loop k*3+j belongs to face k, corner j
    uv_layer = mesh.uv_layers.new(name="UVMap")
    loop_uv = UVv[F.reshape(-1)]
    loop_uv = np.stack([loop_uv[:, 0], 1.0 - loop_uv[:, 1]], axis=1)    # glTF v points down, Blender v up
    uv_layer.data.foreach_set("uv", loop_uv.reshape(-1).astype(np.float32))
    # keep the hand-authored normals (flat boxes, smooth lathes)
    try:
        if hasattr(mesh, "use_auto_smooth"):
            mesh.use_auto_smooth = True
        mesh.polygons.foreach_set("use_smooth", np.ones(len(F), dtype=np.bool_))
        mesh.normals_split_custom_set_from_vertices([tuple(n) for n in Nn.tolist()])
    except Exception as e:      # noqa: BLE001
        if use_custom_normals:
            print("custom normals unavailable (%s) - using computed normals" % e)
            use_custom_normals = False
    ob = bpy.data.objects.new(o.name, mesh)
    ob.location = (float(o.origin[0]), float(-o.origin[2]), float(o.origin[1]))
    collection.objects.link(ob)
    blender_objs.append(ob)

print("blender objects: %d (%.1fs)" % (len(blender_objs), time.time() - t0))

# ----------------------------------------------------------------------------------------------- hand-modelled props
# Furniture for the rooms and the player's candle, modelled here in Blender (bevelled wood, turned legs, clay pots,
# brass ware, a dripping wax candle in a brass chamberstick). Each prop is an Empty with its parts as children.
import math
import random

from mathutils import Matrix, Vector

for _n, _c in {"candle_wax": (0.93, 0.87, 0.74), "wick": (0.04, 0.035, 0.03), "wick_ember": (1.0, 0.35, 0.08),
               "sack": (0.55, 0.45, 0.3), "iron": (0.12, 0.11, 0.1), "wood_old": (0.25, 0.16, 0.1), "rope": (0.45, 0.35, 0.22)}.items():
    BASE_COLOR.setdefault(_n, _c)
rng = random.Random(7)
prop_collection = bpy.data.collections.new("ChayaProps")
scene.collection.children.link(prop_collection)


def _smooth(ob, angle=35.0):
    me = ob.data
    for p in me.polygons:
        p.use_smooth = True
    try:
        if hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(angle)
        else:                                       # Blender 4.1+: "smooth by angle" is a modifier
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True)
            bpy.context.view_layer.objects.active = ob
            bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:       # noqa: BLE001
        pass


def _bevel(ob, width=0.006, segments=2):
    m = ob.modifiers.new("bevel", "BEVEL")
    m.width = width
    m.segments = segments
    m.limit_method = "ANGLE"
    try:
        m.harden_normals = False
    except Exception:       # noqa: BLE001
        pass
    return m


def _finish(ob, parent, material, bevel=0.0):
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    prop_collection.objects.link(ob)
    ob.data.materials.clear()
    ob.data.materials.append(get_material(material))
    if bevel > 0:
        _bevel(ob, bevel)
    _smooth(ob)
    ob.parent = parent
    return ob


def p_box(parent, name, size, loc, material, bevel=0.006, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cube_add(size=1.0)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
    ob.location = loc
    ob.rotation_euler = rot
    return _finish(ob, parent, material, bevel)


def p_cyl(parent, name, r, h, loc, material, verts=20, bevel=0.003, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=h)
    ob = bpy.context.active_object
    ob.name = name
    ob.location = loc
    ob.rotation_euler = rot
    return _finish(ob, parent, material, bevel)


def p_sphere(parent, name, r, scale, loc, material, seg=24, rings=14, rot=(0.0, 0.0, 0.0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg, ring_count=rings, radius=r)
    ob = bpy.context.active_object
    ob.name = name
    ob.data.transform(Matrix.Diagonal((scale[0], scale[1], scale[2], 1.0)))
    ob.location = loc
    ob.rotation_euler = rot
    return _finish(ob, parent, material)


def p_torus(parent, name, R, r, loc, material, rot=(0.0, 0.0, 0.0), seg=(32, 10)):
    bpy.ops.mesh.primitive_torus_add(major_radius=R, minor_radius=r, major_segments=seg[0], minor_segments=seg[1])
    ob = bpy.context.active_object
    ob.name = name
    ob.location = loc
    ob.rotation_euler = rot
    return _finish(ob, parent, material)


def p_lathe(parent, name, profile, loc, material, segments=40):
    """Turned shape: profile = [(radius, z), ...] bottom to top, capped at both ends."""
    verts, faces = [], []
    n = len(profile)
    for (r, z) in profile:
        for k in range(segments):
            a = 2.0 * math.pi * k / segments
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(n - 1):
        for k in range(segments):
            k2 = (k + 1) % segments
            faces.append((i * segments + k, i * segments + k2, (i + 1) * segments + k2, (i + 1) * segments + k))
    faces.append(tuple(reversed(range(segments))))
    faces.append(tuple(range((n - 1) * segments, n * segments)))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    me.uv_layers.new(name="UVMap")
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    scene.collection.objects.link(ob)
    return _finish(ob, parent, material)


def new_prop(name):
    e = bpy.data.objects.new(name, None)
    prop_collection.objects.link(e)
    return e


# --- each builder works in prop space: back against the wall = +Y (y = 0.45), front into the room = -Y, up = +Z
def build_charpai(e):
    L_, W_, H_ = 1.7, 0.74, 0.44
    y0 = 0.45 - W_ / 2.0
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * (L_ / 2 - 0.05), y0 + sy * (W_ / 2 - 0.05)
            p_lathe(e, "leg", [(0.03, 0.0), (0.036, 0.04), (0.028, 0.1), (0.04, 0.17), (0.026, 0.25), (0.034, 0.33), (0.03, H_)], (x, y, 0.0), "wood_old", 16)
    for sy in (-1, 1):
        p_box(e, "rail", (L_, 0.055, 0.07), (0.0, y0 + sy * (W_ / 2 - 0.05), H_ - 0.06), "wood_old", 0.008)
    for sx in (-1, 1):
        p_box(e, "rail", (0.055, W_, 0.07), (sx * (L_ / 2 - 0.05), y0, H_ - 0.06), "wood_old", 0.008)
    # woven rope bed: one mesh of thin cords both ways, sagging a little in the middle
    verts, faces = [], []

    def cord(a, b, sag):
        segs, r = 10, 0.007
        base = len(verts)
        for i in range(segs + 1):
            t = i / segs
            p = a.lerp(b, t)
            p.z -= sag * math.sin(math.pi * t)
            d = (b - a).normalized()
            side = Vector((-d.y, d.x, 0.0))
            for k in range(4):
                ang = k * math.pi / 2
                off = side * (r * math.cos(ang)) + Vector((0, 0, r * math.sin(ang)))
                verts.append(tuple(p + off))
        for i in range(segs):
            for k in range(4):
                k2 = (k + 1) % 4
                faces.append((base + i * 4 + k, base + i * 4 + k2, base + (i + 1) * 4 + k2, base + (i + 1) * 4 + k))
    zc = H_ - 0.05
    for i in range(11):
        y = y0 - W_ / 2 + 0.08 + i * (W_ - 0.16) / 10
        cord(Vector((-L_ / 2 + 0.07, y, zc)), Vector((L_ / 2 - 0.07, y, zc)), 0.035)
    for i in range(26):
        x = -L_ / 2 + 0.09 + i * (L_ - 0.18) / 25
        cord(Vector((x, y0 - W_ / 2 + 0.07, zc + 0.008)), Vector((x, y0 + W_ / 2 - 0.07, zc + 0.008)), 0.03)
    me = bpy.data.meshes.new("rope_bed")
    me.from_pydata(verts, [], faces)
    me.update()
    me.uv_layers.new(name="UVMap")
    ob = bpy.data.objects.new("rope_bed", me)
    scene.collection.objects.link(ob)
    _finish(ob, e, "rope")
    # a crumpled old red quilt at one end
    p_sphere(e, "quilt", 0.22, (1.0, 1.4, 0.28), (L_ / 2 - 0.3, y0, H_ + 0.02), "red_cloth", rot=(0.0, 0.0, 0.3))
    return (L_, W_, H_)


def build_chest(e):
    W_, D_, H_ = 0.92, 0.5, 0.5
    y0 = 0.45 - D_ / 2.0
    p_box(e, "body", (W_, D_, H_ - 0.08), (0, y0, 0.06 + (H_ - 0.08) / 2), "door_wood", 0.012)
    p_box(e, "lid", (W_ + 0.03, D_ + 0.03, 0.08), (0, y0, H_ - 0.0), "door_wood", 0.015)
    for x in (-W_ / 2 + 0.1, 0.0, W_ / 2 - 0.1):
        p_box(e, "band", (0.035, D_ + 0.04, 0.012), (x, y0, H_ + 0.042), "iron", 0.003)
        p_box(e, "band", (0.035, 0.012, H_ - 0.02), (x, y0 - D_ / 2 - 0.006, H_ / 2 + 0.03), "iron", 0.003)
    p_box(e, "lock", (0.09, 0.015, 0.11), (0, y0 - D_ / 2 - 0.012, H_ - 0.08), "brass", 0.004)
    p_torus(e, "lock_ring", 0.022, 0.005, (0, y0 - D_ / 2 - 0.03, H_ - 0.15), "brass", rot=(math.pi / 2, 0, 0), seg=(20, 8))
    for sx in (-1, 1):
        for sy in (-1, 1):
            p_box(e, "foot", (0.07, 0.07, 0.06), (sx * (W_ / 2 - 0.06), y0 + sy * (D_ / 2 - 0.06), 0.03), "wood_old", 0.006)
    return (W_ + 0.03, D_ + 0.03, H_ + 0.04)


def _matka(e, name, x, y, s):
    prof = [(0.06, 0.0), (0.13, 0.03), (0.2, 0.12), (0.22, 0.2), (0.2, 0.29), (0.14, 0.36), (0.085, 0.4), (0.075, 0.43), (0.095, 0.45), (0.1, 0.47), (0.07, 0.47)]
    p_lathe(e, name, [(r * s, z * s) for (r, z) in prof], (x, y, 0.0), "clay", 36)


def build_pots(e):
    _matka(e, "matka", -0.18, 0.2, 1.0)
    _matka(e, "matka", 0.24, 0.24, 0.8)
    _matka(e, "matka", 0.02, 0.0, 0.62)
    p_lathe(e, "lid", [(0.11, 0.0), (0.12, 0.01), (0.09, 0.04), (0.02, 0.055), (0.0, 0.06)], (-0.18, 0.2, 0.47), "clay", 28)
    return (0.75, 0.62, 0.48)


def build_shelf(e):
    W_, D_, H_ = 1.0, 0.3, 1.25
    y0 = 0.45 - D_ / 2.0
    for sx in (-1, 1):
        p_box(e, "side", (0.035, D_, H_), (sx * (W_ / 2 - 0.0175), y0, H_ / 2), "wood_old", 0.006)
    for z in (0.08, 0.48, 0.86, 1.22):
        p_box(e, "board", (W_, D_, 0.03), (0, y0, z), "wood_old", 0.005)
    p_box(e, "back", (W_, 0.012, H_), (0, 0.45 - 0.006, H_ / 2), "wood_old", 0.0)
    # brass and copper ware
    lota = [(0.035, 0.0), (0.06, 0.03), (0.07, 0.07), (0.055, 0.12), (0.03, 0.15), (0.032, 0.17), (0.04, 0.18), (0.03, 0.18)]
    p_lathe(e, "lota", lota, (-0.3, y0, 0.495), "brass", 28)
    p_lathe(e, "lota", [(r * 0.8, z * 0.8) for r, z in lota], (0.32, y0 - 0.02, 0.875), "copper", 28)
    thali = [(0.0, 0.0), (0.13, 0.0), (0.15, 0.012), (0.155, 0.02), (0.145, 0.02), (0.13, 0.008), (0.0, 0.008)]
    ob = p_lathe(e, "thali", thali, (0.05, 0.45 - 0.07, 0.6), "brass", 36)
    ob.rotation_euler = (math.radians(-72), 0, 0)
    p_lathe(e, "bowl", [(0.03, 0.0), (0.06, 0.01), (0.075, 0.05), (0.07, 0.05), (0.055, 0.015), (0.0, 0.015)], (0.28, y0, 0.495), "brass", 28)
    p_lathe(e, "diya", [(0.02, 0.0), (0.04, 0.008), (0.05, 0.025), (0.044, 0.026), (0.03, 0.012), (0.0, 0.012)], (-0.25, y0, 0.875), "clay", 20)
    p_lathe(e, "jar", [(0.05, 0.0), (0.07, 0.04), (0.07, 0.16), (0.05, 0.19), (0.045, 0.22), (0.0, 0.22)], (-0.05, y0, 1.235), "clay", 24)
    return (W_, D_, H_)


def build_sacks(e):
    for i, (x, y, s) in enumerate(((-0.22, 0.2, 1.0), (0.2, 0.22, 0.85))):
        p_sphere(e, "sack", 0.24 * s, (1.0, 0.85, 1.55), (x, y, 0.32 * s), "sack", rot=(0, 0, rng.uniform(-0.4, 0.4)))
        p_sphere(e, "sack_top", 0.08 * s, (1.0, 1.0, 1.3), (x, y, 0.69 * s), "sack")
        p_torus(e, "tie", 0.055 * s, 0.012, (x, y, 0.62 * s), "rope", seg=(20, 6))
    return (0.8, 0.6, 0.75)


BUILDERS = {"charpai": build_charpai, "chest": build_chest, "pots": build_pots, "shelf": build_shelf, "sacks": build_sacks}
PLAN = {"bedroom": ["charpai", "chest", "pots"], "kitchen": ["pots", "shelf", "sacks"], "store": ["sacks", "chest", "pots"],
        "hall": ["chest", "shelf", "pots"], "study": ["shelf", "chest", "sacks"]}
prop_meta = []
try:
    # keep props out of doorways, away from the ritual items and from each other
    keep_out = []
    for d in L["doorways"]:
        if d["o"] == "h":
            keep_out.append((d["c"] - 1.0, d["c"] + 1.0, d["p"] - 1.25, d["p"] + 1.25))
        else:
            keep_out.append((d["p"] - 1.25, d["p"] + 1.25, d["c"] - 1.0, d["c"] + 1.0))
    item_xz = [(it["pos"][0], it["pos"][2]) for it in meta["items"]]
    used, count = [], {}
    for k, slot in enumerate(L["props"]):
        x, z = slot["pos"]
        if any(math.hypot(x - ux, z - uz) < 1.5 for ux, uz in used):
            continue
        if any(math.hypot(x - ix, z - iz) < 1.2 for ix, iz in item_xz):
            continue
        plan = PLAN.get(slot["kind"], ["chest"])
        kind = plan[count.get(slot["room"], 0) % len(plan)]
        yaw = math.radians(slot["yaw"])
        half = {"charpai": 0.9, "chest": 0.5, "pots": 0.4, "shelf": 0.5, "sacks": 0.42}[kind]
        ax, az = math.cos(yaw), -math.sin(yaw)          # prop x axis in world (x, z)
        ends = [(x + ax * half, z + az * half), (x - ax * half, z - az * half), (x, z)]
        if any(x0 <= px <= x1 and z0 <= pz <= z1 for (x0, x1, z0, z1) in keep_out for (px, pz) in ends):
            continue
        e = new_prop("prop_%d_%s" % (k, kind))
        size = BUILDERS[kind](e)
        e.location = (x, -z, 0.0)
        e.rotation_euler = (0.0, 0.0, yaw)
        used.append((x, z))
        count[slot["room"]] = count.get(slot["room"], 0) + 1
        prop_meta.append({"name": e.name, "kind": kind, "pos": [x, z], "yaw": slot["yaw"], "size": [size[0], size[1]], "h": size[2],
                          "back": 0.45})
    print("props placed: %d (%s)" % (len(prop_meta), ", ".join(p["kind"] for p in prop_meta)))
except Exception as ex:     # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("PROPS FAILED:", ex)

# --- the player's candle: a dripping wax candle in a brass chamberstick (exported on its own as candle.glb)
candle_root = None
try:
    candle_root = new_prop("candle")
    p_lathe(candle_root, "holder", [(0.003, 0.0), (0.05, 0.0), (0.056, 0.003), (0.059, 0.011), (0.056, 0.013), (0.052, 0.008),
                                    (0.022, 0.006), (0.0195, 0.008), (0.0175, 0.03), (0.0198, 0.032), (0.0198, 0.035),
                                    (0.0172, 0.035), (0.0172, 0.013), (0.002, 0.013)], (0, 0, 0), "brass", 48)
    p_torus(candle_root, "handle", 0.015, 0.0034, (0.071, 0.0, 0.01), "brass", rot=(math.pi / 2, 0, 0), seg=(28, 10))
    wax = p_lathe(candle_root, "wax", [(0.0166, 0.013), (0.0168, 0.05), (0.0166, 0.088), (0.0172, 0.0925), (0.0158, 0.0948),
                                       (0.012, 0.0925), (0.006, 0.0912), (0.001, 0.091)], (0, 0, 0), "candle_wax", 40)
    tex = bpy.data.textures.new("wax_noise", "CLOUDS")
    tex.noise_scale = 0.008
    dm = wax.modifiers.new("lumps", "DISPLACE")
    dm.texture = tex
    dm.strength = 0.0007
    for i in range(6):                                   # wax drips running down from the rim
        a = i * 2 * math.pi / 6 + rng.uniform(-0.3, 0.3)
        ln = rng.uniform(0.012, 0.03)
        cx, cy = math.cos(a) * 0.0168, math.sin(a) * 0.0168
        p_sphere(candle_root, "drip", 0.0028, (1.0, 0.8, ln / 0.0056), (cx, cy, 0.092 - ln / 2), "candle_wax", seg=12, rings=8, rot=(0, 0, a))
        p_sphere(candle_root, "drip_end", 0.0033, (1.0, 1.0, 0.9), (cx * 1.03, cy * 1.03, 0.092 - ln), "candle_wax", seg=12, rings=8)
    p_sphere(candle_root, "wax_pool", 0.026, (1.0, 1.0, 0.16), (0.0, 0.0, 0.035), "candle_wax", seg=28, rings=10)
    p_cyl(candle_root, "wick", 0.0011, 0.013, (0.0008, 0.0, 0.0975), "wick", verts=8, bevel=0.0, rot=(0.0, 0.22, 0.0))
    p_sphere(candle_root, "ember", 0.0014, (1.0, 1.0, 1.3), (0.0022, 0.0, 0.1038), "wick_ember", seg=10, rings=6)
    anchor = bpy.data.objects.new("flame_anchor", None)
    prop_collection.objects.link(anchor)
    anchor.parent = candle_root
    anchor.location = (0.0024, 0.0, 0.1155)
    candle_root.location = (0.0, 0.0, -60.0)           # out of the way of the AO bake
    print("candle modelled")
except Exception as ex:     # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("CANDLE FAILED:", ex)
    candle_root = None

# ----------------------------------------------------------------------------------------------- AO bake
baked = False
if DO_BAKE:
    try:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = 24
        try:
            scene.cycles.use_denoising = False
        except Exception:    # noqa: BLE001
            pass
        try:
            scene.world = bpy.data.worlds.new("w")
            scene.world.light_settings.distance = 0.9
        except Exception as e:      # noqa: BLE001
            print("AO distance not set:", e)
        for ob in blender_objs:
            me = ob.data
            attr = me.color_attributes.new("AO", "FLOAT_COLOR", "POINT")
            me.color_attributes.active_color = attr
            me.color_attributes.render_color_index = list(me.color_attributes).index(attr)
        bpy.ops.object.select_all(action="DESELECT")
        for ob in blender_objs:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = blender_objs[0]
        t1 = time.time()
        bpy.ops.object.bake(type="AO", target="VERTEX_COLORS", use_clear=True)
        print("AO bake done in %.1fs" % (time.time() - t1))
        baked = True
    except Exception as e:      # noqa: BLE001
        print("AO bake failed:", repr(e))

if baked:
    # Soften: AO is only a hint on top of the real-time lighting (brighten and keep a floor).
    vals = []
    for ob in blender_objs:
        me = ob.data
        attr = me.color_attributes.get("AO")
        if attr is None:
            continue
        n = len(attr.data)
        arr = np.zeros(n * 4, dtype=np.float32)
        attr.data.foreach_get("color", arr)
        arr = arr.reshape(-1, 4)
        ao = np.clip(arr[:, :3].mean(axis=1), 0.0, 1.0)
        ao = 0.42 + 0.58 * ao ** 0.7
        arr[:, 0] = arr[:, 1] = arr[:, 2] = ao
        arr[:, 3] = 1.0
        attr.data.foreach_set("color", arr.reshape(-1))
        vals.append(ao)
    if vals:
        a = np.concatenate(vals)
        print("AO values: min %.2f mean %.2f max %.2f" % (a.min(), a.mean(), a.max()))

# ----------------------------------------------------------------------------------------------- save + export
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "chaya_map.blend"))

gltf_keys = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()


def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.select_set(True)
    kw = dict(filepath=path, export_format="GLB", export_yup=True, export_apply=True, use_selection=True,
              export_texcoords=True, export_normals=True, export_materials="EXPORT", export_cameras=False,
              export_lights=False, export_animations=False)
    if "export_tangents" in gltf_keys:
        kw["export_tangents"] = True
    if "export_vertex_color" in gltf_keys:
        kw["export_vertex_color"] = "ACTIVE"
        if "export_active_vertex_color_when_no_material" in gltf_keys:
            kw["export_active_vertex_color_when_no_material"] = True
    elif "export_colors" in gltf_keys:
        kw["export_colors"] = True
    kw = {k: v for k, v in kw.items() if k in gltf_keys}
    print("glTF export:", os.path.basename(path), len(objects), "objects")
    bpy.ops.export_scene.gltf(**kw)


candle_objs = set()
if candle_root is not None:
    candle_root.location = (0.0, 0.0, 0.0)
    candle_objs = {candle_root} | set(candle_root.children_recursive)
house = [ob for ob in scene.objects if ob not in candle_objs]
export_glb(os.path.join(out_dir, "maze.glb"), house)
if candle_objs:
    try:
        export_glb(os.path.join(out_dir, "candle.glb"), list(candle_objs))
    except Exception as ex:     # noqa: BLE001
        print("CANDLE EXPORT FAILED:", ex)
meta["props"] = prop_meta
json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"))
print("done in %.1fs, glb %.1f MB, AO baked: %s" % (time.time() - t0, os.path.getsize(os.path.join(out_dir, "maze.glb")) / 1e6, baked))
