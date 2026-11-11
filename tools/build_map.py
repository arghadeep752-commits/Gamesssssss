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
SCANS = argv[argv.index("--scans") + 1] if "--scans" in argv else os.path.join(HERE, "..", "assets", "downloaded", "scans")
os.makedirs(out_dir, exist_ok=True)
import scan_props  # noqa: E402
scan_props.setup(os.path.abspath(SCANS))
SCANS_OK = scan_props.available("Lantern_01") or scan_props.available("GothicBed_01")
print("scanned models:", "yes" if SCANS_OK else "NO (hand-modelled fallback)", os.path.abspath(SCANS))

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

# ----------------------------------------------------------------------------------------------- hero ritual items
# The six items are remodelled in detail in Blender (tools/hero_items.py) and take the place of the simple lathe
# versions under the same names, so the game picks them up unchanged.
for _n, _c in {"coir": (0.45, 0.3, 0.16), "coconut_dark": (0.1, 0.06, 0.035), "thread_red": (0.7, 0.04, 0.03),
               "thread_yellow": (0.9, 0.65, 0.1), "oil": (0.3, 0.19, 0.04), "water": (0.06, 0.09, 0.1),
               "wick_cotton": (0.9, 0.86, 0.76), "rice": (0.95, 0.93, 0.86), "wick": (0.04, 0.035, 0.03),
               "wick_ember": (1.0, 0.35, 0.08)}.items():
    BASE_COLOR.setdefault(_n, _c)
try:
    import hero_items
    hero = hero_items.build_all(get_material, collection, [it["id"] for it in meta["items"]])
    for it in meta["items"]:
        old = bpy.data.objects.get(it["name"])
        if it["id"] not in hero or old is None:
            continue
        loc = old.location.copy()
        if old in blender_objs:
            blender_objs.remove(old)
        bpy.data.objects.remove(old, do_unlink=True)
        hob, extras = hero[it["id"]]
        hob.name = it["name"]
        hob.location = loc
        for ename, epos in extras.items():
            em = bpy.data.objects.new(ename, None)
            collection.objects.link(em)
            em.parent = hob
            em.location = epos
    print("hero items in place: %s (%.1fs)" % (", ".join(sorted(hero)), time.time() - t0))
except Exception as ex:     # noqa: BLE001
    import traceback
    traceback.print_exc()
    print("HERO ITEMS FAILED:", ex)

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
    """Turned shape: profile = [(radius, z), ...] bottom to top; triangle-fan caps and cylindrical UVs (so the
    exporter can compute tangents)."""
    verts, faces, uvs = [], [], []
    n = len(profile)
    S1 = segments + 1                                    # one extra column so the UV seam is clean
    for (r, z) in profile:
        for k in range(S1):
            a = 2.0 * math.pi * (k % segments) / segments
            verts.append((r * math.cos(a), r * math.sin(a), z))
    for i in range(n - 1):
        for k in range(segments):
            faces.append((i * S1 + k, i * S1 + k + 1, (i + 1) * S1 + k + 1, (i + 1) * S1 + k))
    cb = len(verts)
    verts.append((0.0, 0.0, profile[0][1]))
    ct = len(verts)
    verts.append((0.0, 0.0, profile[-1][1]))
    for k in range(segments):
        faces.append((cb, k + 1, k))
        faces.append((ct, (n - 1) * S1 + k, (n - 1) * S1 + k + 1))
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    uv = me.uv_layers.new(name="UVMap")
    circ = 2.0 * math.pi * max(r for r, _ in profile)
    for poly in me.polygons:
        for li in poly.loop_indices:
            vi = me.loops[li].vertex_index
            if vi >= cb:
                uv.data[li].uv = (0.5, 0.5)
            else:
                k = vi % S1
                uv.data[li].uv = (k / segments * circ * 2.0, verts[vi][2] * 2.0)
    me.validate()
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
def place_procedural_props():
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

# ----------------------------------------------------------------------------------------------- real scanned models
# Furniture, lanterns, pedestals, the brass ritual vessels and the player's candle are real photo-scanned objects
# (Poly Haven, CC0 - see tools/fetch_scans.py), cleaned up and decimated here (tools/scan_props.py).
TAU = 2.0 * math.pi
for _n, _c in {"stone_base": (0.42, 0.4, 0.37), "pillar_wood": (0.2, 0.12, 0.07), "beam_wood": (0.18, 0.11, 0.07),
               "shutter_wood": (0.25, 0.17, 0.1), "lantern_glow": (1.0, 0.6, 0.25)}.items():
    BASE_COLOR.setdefault(_n, _c)

# key: (model, triangle budget, extra turn, longest side along the wall, fit (x, y, z) or None, exact height or None)
SCAN = {
    "bed": ("GothicBed_01", 7000, 0, True, (2.0, 1.55, 1.9), None),
    "daybed": ("vintage_day_bed", 2715, 0, True, (1.9, 0.9, 1.2), None),
    "almirah": ("painted_wooden_cabinet_02", 1000, 0, False, (1.1, 0.8, 2.15), None),
    "cabinet_low": ("painted_wooden_cabinet", 2300, 0, False, (1.2, 0.65, 1.3), None),
    "commode": ("GothicCommode_01", 3900, 0, False, (1.2, 0.6, 1.25), None),
    "sofa": ("chinese_sofa", 800, 0, True, (2.0, 1.0, 1.0), None),
    "rocking": ("Rockingchair_01", 5000, 0, False, (0.8, 0.9, 1.05), None),
    "armchair": ("chinese_armchair", 2700, 0, False, (0.85, 0.8, 1.4), None),
    "round_table": ("round_wooden_table_01", 4000, 0, False, (0.95, 0.95, 0.8), None),
    "clock": ("vintage_grandfather_clock_01", 5000, 0, False, (0.8, 0.65, 2.2), None),
    "carved_cabinet": ("chinese_cabinet", 6000, 0, False, (1.0, 0.5, 2.2), None),
    "bench": ("painted_wooden_bench", 700, 0, True, (1.2, 0.55, 0.95), None),
    "vase_big": ("antique_ceramic_vase_01", 3000, 0, False, (0.3, 0.3, 0.5), None),
    "rack": ("wooden_bookshelf_worn", 6000, 0, False, (1.3, 0.6, 2.0), None),
    "low_table": ("WoodenTable_01", 960, 0, True, (1.6, 0.66, 0.6), None),
    "pickle_jar": ("ceramic_pot", 2500, 0, False, (0.6, 0.5, 0.4), None),
    "clay_pot": ("planter_pot_clay", 1600, 0, False, (0.3, 0.3, 0.25), None),
    "bucket": ("wooden_bucket_01", 2500, 0, False, (0.4, 0.4, 0.55), None),
    "basket": ("wicker_basket_02", 3000, 0, False, (0.4, 0.3, 0.25), None),
    "basket_flat": ("wicker_basket_01", 3000, 0, False, (0.4, 0.3, 0.13), None),
    "jug": ("metal_jug", 1500, 0, False, (0.2, 0.2, 0.29), None),
    "brass_vase": ("brass_vase_01", 3000, 0, False, None, 0.6),
    "brass_vase2": ("brass_vase_02", 2500, 0, False, None, 0.4),
    "stool": ("wooden_stool_01", 2500, 0, False, (0.45, 0.45, 0.45), None),
    "chest": ("treasure_chest", 6000, 0, True, (1.0, 0.6, 0.7), None),
    "crate": ("wooden_crate_01", 2000, 0, True, (0.85, 0.45, 0.4), None),
    "barrel": ("wine_barrel_01", 4000, 0, False, (0.7, 0.7, 0.85), None),
    "ladder": ("wooden_ladder", 3000, 0, True, (1.0, 0.55, 1.4), None),
    "broom": ("wooden_broom", 2000, 0, True, (0.5, 0.15, 1.45), None),
    "desk": ("small_wooden_table_01", 2500, 0, True, (0.95, 0.5, 0.75), None),
    "chair": ("painted_wooden_chair_02", 1250, 0, False, (0.65, 0.67, 1.27), None),
    "charkha": ("spinning_wheel_01", 6000, 0, True, (1.05, 0.55, 1.0), None),
    "drawer": ("vintage_wooden_drawer_01", 4000, 0, True, (1.6, 0.9, 1.1), None),
    "oil_lamp": ("vintage_oil_lamp", 4000, 0, False, None, 0.45),
    "elephant": ("carved_wooden_elephant", 2752, 0, False, None, 0.24),
    "diya_lantern": ("brass_diya_lantern", 5000, 0, False, None, 0.42),
    "pomegranate": ("food_pomegranate_01", 1500, 0, False, None, 0.1),
    "apple": ("food_apple_01", 1500, 0, False, None, 0.08),
    "lemon": ("lemon", 1000, 0, False, None, 0.065),
    "lantern": ("Lantern_01", 3500, 0, False, None, 0.32),
    "ped_a": ("ClassicNightstand_01", 2000, 0, False, None, 0.74),
    "ped_b": ("WoodenTable_02", 1514, 0, False, None, 0.74),
}

# groups: [(key, x offset, where, turn degrees)]; where = wall (back against the wall), top (on the first piece),
# front (on the floor in front of the first piece)
GROUPS = {
    "bed": [("bed", 0.0, "wall", 0)],
    "daybed": [("daybed", 0.0, "wall", 0)],
    "almirah": [("almirah", 0.0, "wall", 0)],
    "cabinet_low": [("cabinet_low", 0.0, "wall", 0), ("brass_vase2", -0.3, "top", 0)],
    "commode": [("commode", 0.0, "wall", 0), ("oil_lamp", -0.35, "top", 0), ("jug", 0.35, "top", 20)],
    "pots": [("pickle_jar", -0.2, "wall", 0), ("clay_pot", 0.32, "wall", 30), ("clay_pot", 0.12, "front", 70)],
    "rack": [("rack", 0.0, "wall", 0)],
    "kitchen_table": [("low_table", 0.0, "wall", 0), ("jug", -0.5, "top", 0), ("basket_flat", 0.15, "top", 10), ("brass_vase2", 0.6, "top", 0)],
    "bucket_basket": [("bucket", -0.25, "wall", 0), ("basket", 0.25, "wall", 15), ("stool", 0.0, "front", 10)],
    "chest": [("chest", 0.0, "wall", 0)],
    "crates": [("crate", 0.0, "wall", 0), ("crate", 0.05, "top", 7), ("basket", 0.0, "front", 0)],
    "barrel": [("barrel", 0.0, "wall", 0), ("broom", 0.62, "wall", 0)],
    "ladder": [("ladder", 0.0, "wall", 0)],
    "sofa": [("sofa", 0.0, "wall", 0)],
    "clock": [("clock", 0.0, "wall", 0)],
    "rocking": [("rocking", 0.0, "wall", 0)],
    "carved_cabinet": [("carved_cabinet", 0.0, "wall", 0)],
    "bench": [("bench", 0.0, "wall", 0), ("vase_big", 0.78, "wall", 0)],
    "round_table": [("round_table", 0.0, "wall", 0), ("elephant", 0.0, "top", 20)],
    "bookshelf": [("rack", 0.0, "wall", 0)],
    "desk": [("desk", 0.0, "wall", 0), ("oil_lamp", -0.25, "top", 0), ("chair", 0.0, "front", 180)],
    "charkha": [("charkha", 0.0, "wall", 0)],
    "drawer": [("drawer", 0.0, "wall", 0), ("brass_vase", 0.5, "top", 0)],
    "armchair": [("armchair", 0.0, "wall", 0)],
    "brass": [("brass_vase", -0.15, "wall", 0), ("brass_vase2", 0.2, "wall", 0)],
    "start_bench": [("bench", 0.0, "wall", 0), ("broom", -0.85, "wall", 0)],
}
PLAN = {
    "bedroom": ["bed", "almirah", "commode", "daybed", "cabinet_low", "pots", "brass"],
    "kitchen": ["rack", "kitchen_table", "pots", "bucket_basket", "brass", "pots"],
    "store": ["chest", "crates", "barrel", "ladder", "pots", "bucket_basket"],
    "hall": ["daybed", "clock", "rocking", "carved_cabinet", "bench", "round_table", "brass"],
    "study": ["bookshelf", "desk", "charkha", "drawer", "armchair", "brass"],
    "start": ["start_bench", "pots"],
}
ROOM_MAX = {"start": 2}
scan_meta = {"extra_lights": [], "paintings": []}


def tmpl(key):
    if key not in SCAN:
        return None
    mid, budget, rot, long_x, fit, height = SCAN[key]
    return scan_props.template(mid, budget, rot, long_x, fit, height, key=key)


def group_layout(gname):
    """Pieces of a group in prop space -> ([(key, x, y, z, turn)], (xmin, xmax, ymin, ymax, h)) or None."""
    out = []
    first = None
    xmin = ymin = 1e9
    xmax = ymax = -1e9
    h = 0.0
    for (key, dx, where, turn) in GROUPS[gname]:
        t = tmpl(key)
        if t is None:
            if first is None:
                return None
            continue
        ob, size = t
        ang = math.radians(turn)
        w = abs(size.x * math.cos(ang)) + abs(size.y * math.sin(ang))
        d = abs(size.x * math.sin(ang)) + abs(size.y * math.cos(ang))
        if where == "wall" or first is None:
            y = 0.45 - 0.02 - d / 2
            z = 0.0
        elif where == "top":
            fk, fx, fy, fz, fsize = first
            y = fy
            z = fz + fsize.z
            surf = scan_props.surface_z(tmpl(fk)[0], (dx - fx), 0.0, above=fsize.z + 1.0)
            if surf is not None:
                z = fz + surf
        else:                                                  # front
            fk, fx, fy, fz, fsize = first
            y = fy - fsize.y / 2 - d / 2 - 0.08
            z = 0.0
        out.append((key, dx, y, z, ang))
        if first is None:
            first = (key, dx, y, z, size)
        if where != "top":
            xmin, xmax = min(xmin, dx - w / 2), max(xmax, dx + w / 2)
            ymin, ymax = min(ymin, y - d / 2), max(ymax, y + d / 2)
        h = max(h, z + size.z)
    return out, (xmin, xmax, ymin, ymax, h)


def world_rect(x, z, yaw, r):
    """Prop-space rectangle -> world (x0, x1, z0, z1). Prop +x = world (cos yaw, -sin yaw), prop +y = (-sin yaw, -cos yaw)."""
    xmin, xmax, ymin, ymax, _ = r
    pts = []
    for px in (xmin, xmax):
        for py in (ymin, ymax):
            wx = x + px * math.cos(yaw) - py * math.sin(yaw)
            wz = z - px * math.sin(yaw) - py * math.cos(yaw)
            pts.append((wx, wz))
    return (min(p[0] for p in pts), max(p[0] for p in pts), min(p[1] for p in pts), max(p[1] for p in pts))


def overlaps(a, b, m=0.0):
    return a[0] < b[1] + m and b[0] < a[1] + m and a[2] < b[3] + m and b[2] < a[3] + m


def place_scanned_props():
    """Furnish every room: try each closed stretch of wall (sliding along it) with the room's next group."""
    keep_out = []
    for d in L["doorways"]:
        if d["o"] == "h":
            keep_out.append((d["c"] - 0.95, d["c"] + 0.95, d["p"] - 1.1, d["p"] + 1.1))
        else:
            keep_out.append((d["p"] - 1.1, d["p"] + 1.1, d["c"] - 0.95, d["c"] + 0.95))
    for it in meta["items"]:
        x, _, z = it["pos"]
        keep_out.append((x - 0.7, x + 0.7, z - 0.7, z + 0.7))
    for (px, pz) in meta.get("pillars", []):
        keep_out.append((px - 0.32, px + 0.32, pz - 0.32, pz + 0.32))
    S_, x0_, z0_ = L["cell"], L["x0"], L["z0"]
    C_, R_ = L["cols"], L["rows"]
    edges = set((min(a, b), max(a, b)) for a, b in L["edges"])
    st = [r for r in L["rooms"] if r["kind"] == "start"][0]
    # the spawn point and the front door stay clear
    sx, sz = L["spawn"]["pos"]
    keep_out.append((sx - 0.9, sx + 0.9, sz - 0.9, sz + 0.9))
    fx = x0_ + (st["i0"] + 1.5) * S_
    fz = z0_ + (st["j0"] + st["h"]) * S_
    keep_out.append((fx - 1.2, fx + 1.2, fz - 1.0, fz + 0.2))
    off = S_ / 2 - L["wall_t"] / 2 - 0.45
    rnd = random.Random(5)
    placed = []
    for room in L["rooms"]:
        kind = room["kind"]
        if kind == "pooja" or kind not in PLAN:
            continue
        walls = []
        for j in range(room["j0"], room["j0"] + room["h"]):
            for i in range(room["i0"], room["i0"] + room["w"]):
                for di, dj in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                    ni, nj = i + di, j + dj
                    if room["i0"] <= ni < room["i0"] + room["w"] and room["j0"] <= nj < room["j0"] + room["h"]:
                        continue
                    if 0 <= ni < C_ and 0 <= nj < R_ and (min(j * C_ + i, nj * C_ + ni), max(j * C_ + i, nj * C_ + ni)) in edges:
                        continue                                  # an opening: keep it clear
                    walls.append((i, j, di, dj))
        rnd.shuffle(walls)
        plan = PLAN[kind]
        limit = ROOM_MAX.get(kind, len(plan))
        n_done = 0
        gi = 0
        tried = 0
        while n_done < limit and tried < len(plan) * 2 and walls:
            gname = plan[gi % len(plan)]
            gi += 1
            tried += 1
            lay = group_layout(gname)
            if lay is None:
                continue
            pieces, rect = lay
            ok = None
            for (i, j, di, dj) in walls:
                yaw = math.atan2(-di, -dj)
                along = (dj, di)
                for t in (0.0, -0.45, 0.45, -0.8, 0.8):
                    x = x0_ + (i + 0.5) * S_ + di * off + along[0] * t
                    z = z0_ + (j + 0.5) * S_ + dj * off + along[1] * t
                    wr = world_rect(x, z, yaw, rect)
                    if any(overlaps(wr, ko) for ko in keep_out) or any(overlaps(wr, pr, 0.1) for pr in placed):
                        continue
                    ok = (x, z, yaw, wr, (i, j, di, dj))
                    break
                if ok:
                    break
            if not ok:
                continue
            x, z, yaw, wr, wall = ok
            walls.remove(wall)
            e = new_prop("prop_%s_%d_%s" % (room["name"], n_done, gname))
            for (key, px, py, pz, ang) in pieces:
                scan_props.instance(key, "%s_%s" % (e.name, key), prop_collection, parent=e, loc=(px, py, pz), rot_z=ang)
            e.location = (x, -z, 0.0)
            e.rotation_euler = (0.0, 0.0, yaw)
            placed.append(wr)
            xmin, xmax, ymin, ymax, h = rect
            prop_meta.append({"name": e.name, "kind": gname, "pos": [x, z], "yaw": math.degrees(yaw), "size": [xmax - xmin, ymax - ymin],
                              "h": h, "back": ymax, "cx": (xmin + xmax) / 2})
            n_done += 1
        print("  %-10s %-8s %d groups" % (room["name"], kind, n_done))
    print("scanned props placed: %d (%s)" % (len(prop_meta), ", ".join(p["kind"] for p in prop_meta)))
    return placed


def place_lanterns():
    t = tmpl("lantern")
    if t is None:
        return 0
    H_ = L["wall_h"]
    n = 0
    for li, l in enumerate(L["lights"]):
        x, y, z = l["pos"]
        old = bpy.data.objects.get("lamp_%d" % li)
        if old is not None:
            if old in blender_objs:
                blender_objs.remove(old)
            bpy.data.objects.remove(old, do_unlink=True)
        e = new_prop("lamp_%d" % li)
        e.location = (x, -z, 0.0)
        bottom = y - 0.15
        scan_props.instance("lantern", "lamp_%d_lantern" % li, prop_collection, parent=e, loc=(0.0, 0.0, bottom), rot_z=rng.uniform(0, TAU))
        top = bottom + t[1].z
        p_cyl(e, "lamp_%d_chain" % li, 0.004, (H_ - 0.09) - top + 0.01, (0.0, 0.0, (top + H_ - 0.09) / 2), "lantern_metal", verts=6, bevel=0.0)
        p_sphere(e, "lamp_%d_flame" % li, 0.011, (1.0, 1.0, 1.9), (0.0, 0.0, bottom + 0.085), "lantern_glow", seg=10, rings=6)
        n += 1
    print("hurricane lanterns hung: %d" % n)
    return n


def place_pedestals():
    n = 0
    for k, it in enumerate(meta["items"]):
        key = "ped_a" if k % 2 == 0 else "ped_b"
        t = tmpl(key)
        if t is None:
            continue
        old = bpy.data.objects.get("pedestal_" + it["id"])
        if old is not None:
            if old in blender_objs:
                blender_objs.remove(old)
            bpy.data.objects.remove(old, do_unlink=True)
        x, top, z = it["pos"]
        fx, fz = it.get("face", [0, 1])
        yaw = math.atan2(fx, fz)
        e = new_prop("pedestal_%s" % it["id"])
        scan_props.instance(key, "pedestal_%s_%s" % (it["id"], key), prop_collection, parent=e)
        e.location = (x, -z, 0.0)
        e.rotation_euler = (0.0, 0.0, yaw)
        it["ped"] = [round(t[1].x, 3), round(t[1].y, 3)]
        it["ped_yaw"] = math.degrees(yaw)
        n += 1
    print("scanned pedestals: %d" % n)


def dress_pooja():
    po = L["pooja"]
    cx, cz = po["center"]
    alt_top = 0.515
    for k, (dx, dz) in enumerate(((-0.5, -0.5), (0.5, -0.5), (-0.5, 0.5), (0.5, 0.5))):
        key = ["pomegranate", "apple", "lemon", "apple"][k]
        if tmpl(key) is None:
            continue
        e = new_prop("offering_%d" % k)
        e.location = (cx + dx, -(cz + dz), alt_top)
        for m in range(2 if key != "pomegranate" else 1):
            scan_props.instance(key, "offering_%d_%d" % (k, m), prop_collection, parent=e, loc=(0.05 * m, 0.03 * m, 0.0), rot_z=rng.uniform(0, TAU))
    for k, (dx, dz) in enumerate(((-0.82, -0.82), (0.82, -0.82), (-0.82, 0.82), (0.82, 0.82))):
        if tmpl("brass_vase2") is None:
            break
        e = new_prop("pooja_vase_%d" % k)
        e.location = (cx + dx, -(cz + dz), 0.18)
        scan_props.instance("brass_vase2", "pooja_vase_%d_v" % k, prop_collection, parent=e, rot_z=rng.uniform(0, TAU))
    t = tmpl("diya_lantern")
    if t is not None:
        H_ = L["wall_h"]
        for k, dx in enumerate((-1.1, 1.1)):
            e = new_prop("pooja_lamp_%d" % k)
            e.location = (cx + dx, -(cz - 0.9), 0.0)
            bottom = 1.75
            scan_props.instance("diya_lantern", "pooja_lamp_%d_l" % k, prop_collection, parent=e, loc=(0, 0, bottom))
            top = bottom + t[1].z
            p_cyl(e, "pooja_lamp_%d_chain" % k, 0.004, (H_ - 0.09) - top + 0.01, (0.0, 0.0, (top + H_ - 0.09) / 2), "lantern_metal", verts=6, bevel=0.0)
            p_sphere(e, "pooja_lamp_%d_flame" % k, 0.008, (1.0, 1.0, 1.8), (0.0, 0.0, bottom + t[1].z * 0.3), "lantern_glow", seg=10, rings=6)
            scan_meta["extra_lights"].append([cx + dx, bottom + t[1].z * 0.3, cz - 0.9, 0.9, 3.6])


def scan_items():
    """The four brass/wood vessels as real scans (kalash, gangajal, kapoor, kumkum); diya and coconut stay hand-made."""
    import hero_items
    kit = hero_items.Kit(get_material, collection)
    built = {}

    def body(mid, key, budget, height=None, fit=None):
        t = scan_props.template(mid, budget, 0, False, fit, height, key=key)
        if t is None:
            return None, None
        ob = bpy.data.objects.new(key + "_obj", t[0].data.copy())
        collection.objects.link(ob)
        bpy.context.view_layer.update()
        return ob, t[1]

    try:
        ob, size = body("brass_vase_03", "it_kalash", 2616, height=0.25)
        if ob is not None:
            rr = scan_props.rim_radius(ob.data, 0.95)
            H_ = size.z
            parts = [ob]
            for k in range(5):
                az = TAU * k / 5 + 0.2
                base = (rr * 0.75 * math.cos(az), rr * 0.75 * math.sin(az), H_ - 0.006)
                parts.append(kit.leaf("kalash_leaf%d" % k, base, az, kit.rng.uniform(0.13, 0.16), kit.rng.uniform(0.04, 0.048),
                                      kit.rng.uniform(55.0, 75.0), "leaf_green"))
            sc = max(0.55, min(0.85, rr * 1.3 / 0.083))
            nut = hero_items.coconut_parts(kit, "kalash_nut", scale=sc, tilak=True, thread=False)
            for pp in nut:
                pp.location = (0.0, 0.0, H_ - 0.012)
            parts += nut
            built["kalash"] = kit.join(parts, "scan_kalash")
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCAN KALASH FAILED", ex)
    try:
        ob, size = body("brass_pot_01", "it_gangajal", 3760, height=0.2)
        if ob is not None:
            built["gangajal"] = ob
    except Exception as ex:     # noqa: BLE001
        print("SCAN GANGAJAL FAILED", ex)
    try:
        ob, size = body("brass_pot_02", "it_kapoor", 3344, fit=(0.27, 0.27, None))
        if ob is not None:
            parts = [ob]
            spots = [(0.0, 0.0, 0.0), (0.03, 0.006, 0.6), (-0.026, 0.018, 1.1), (0.008, -0.03, 2.0), (-0.012, -0.004, 0.3),
                     (0.022, -0.024, 2.6), (-0.034, -0.022, 1.7)]
            for k, (x, y, rz) in enumerate(spots):
                zf = scan_props.surface_z(ob, x, y, above=1.0)
                zf = zf if zf is not None else 0.02
                stack = 1 if k == 4 else 0
                parts.append(kit.rounded_box("kapoor_tab%d" % k, (0.026, 0.026, 0.011), (x, y, zf + 0.0055 + stack * 0.011),
                                             "camphor_white", bevel=0.0035, rot_z=rz, tilt=(kit.rng.uniform(-0.08, 0.08), kit.rng.uniform(-0.08, 0.08)),
                                             lumpy=0.0006))
            built["kapoor"] = kit.join(parts, "scan_kapoor")
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCAN KAPOOR FAILED", ex)
    try:
        ob, size = body("wooden_bowl_02", "it_kumkum", 4666, fit=(0.15, 0.15, None))
        if ob is not None:
            rr = scan_props.rim_radius(ob.data, 0.9) * 0.9
            z0 = size.z - 0.01
            grain = hero_items.wave(61, 8, 10, 30)
            fine = hero_items.wave(62, 8, 30, 70)
            heap = []
            n = 22
            for i in range(n + 1):
                t = i / n
                heap.append((rr * (1.0 - t) if i < n else 0.0, z0 + 0.03 * (1.0 - (1.0 - t) ** 2) ** 0.85))
            powder = kit.revolve("kumkum_powder", heap, 80, "kumkum_red",
                                 disp=lambda a, z, r: 0.0011 * grain(a, z * 60.0) + 0.0006 * fine(a, z * 150.0))
            built["kumkum"] = kit.join([ob, powder], "scan_kumkum")
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCAN KUMKUM FAILED", ex)
    for iid, nob in built.items():
        it = [i for i in meta["items"] if i["id"] == iid]
        old = bpy.data.objects.get("item_" + iid)
        if not it or old is None:
            bpy.data.objects.remove(nob, do_unlink=True)
            continue
        loc = old.location.copy()
        for ch in list(old.children):
            bpy.data.objects.remove(ch, do_unlink=True)
        if old in blender_objs:
            blender_objs.remove(old)
        bpy.data.objects.remove(old, do_unlink=True)
        nob.name = "item_" + iid
        nob.location = loc
        for c in list(nob.users_collection):
            c.objects.unlink(nob)
        collection.objects.link(nob)
        print("item %-9s is now a real scan (%d tris)" % (iid, sum(len(p.vertices) - 2 for p in nob.data.polygons)))


def scan_candle():
    global candle_root
    res = None
    for fn in (scan_props.candle_from_set, scan_props.candle_wooden):
        try:
            res = fn()
        except Exception as ex:     # noqa: BLE001
            import traceback
            traceback.print_exc()
            print("candle scan attempt failed:", ex)
            res = None
        if res:
            break
    if not res:
        return False
    cob, anchor = res
    if candle_root is not None:
        for ch in list(candle_root.children_recursive):
            bpy.data.objects.remove(ch, do_unlink=True)
        bpy.data.objects.remove(candle_root, do_unlink=True)
    candle_root = new_prop("candle")
    for c in list(cob.users_collection):
        c.objects.unlink(cob)
    prop_collection.objects.link(cob)
    cob.parent = candle_root
    a = bpy.data.objects.new("flame_anchor", None)
    prop_collection.objects.link(a)
    a.parent = candle_root
    a.location = anchor
    candle_root.location = (0.0, 0.0, -60.0)
    print("player candle: real scan, flame at %.3f %.3f %.3f" % tuple(anchor))
    return True


def place_paintings(placed):
    art = sorted(glob.glob(os.path.join(os.path.abspath(SCANS), "art", "*.jpg")))
    if not art:
        print("no paintings downloaded")
        return
    frames = sorted(meta.get("frames", []), key=lambda f: 0 if f["kind"] != "corridor" else 1)
    k = 0
    for fr in frames:
        if k >= len(art):
            break
        x, y, z = fr["pos"]
        if any(overlaps((x - 0.45, x + 0.45, z - 0.45, z + 0.45), pr) for pr in placed):
            continue
        try:
            img = bpy.data.images.load(art[k])
        except Exception as ex:     # noqa: BLE001
            print("painting load failed", ex)
            k += 1
            continue
        w_px, h_px = img.size
        ph = 0.78
        pw = ph * w_px / max(1, h_px)
        mat = bpy.data.materials.new("scan_art_%d" % k)
        mat.use_nodes = True
        nt = mat.node_tree
        bsdf = nt.nodes.get("Principled BSDF")
        tex = nt.nodes.new("ShaderNodeTexImage")
        tex.image = img
        nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.55
        me = bpy.data.meshes.new("canvas_%d" % k)
        me.from_pydata([(-pw / 2, 0, -ph / 2), (pw / 2, 0, -ph / 2), (pw / 2, 0, ph / 2), (-pw / 2, 0, ph / 2)], [], [(0, 1, 2, 3)])
        uv = me.uv_layers.new(name="UVMap")
        for li, co in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
            uv.data[li].uv = co
        me.materials.append(mat)
        bx, by = fr["n"][0], -fr["n"][1]
        e = new_prop("painting_%d" % k)
        e.location = (x + fr["n"][0] * 0.035, -(z + fr["n"][1] * 0.035), y)
        e.rotation_euler = (0.0, 0.0, math.atan2(bx, -by))
        cv = bpy.data.objects.new("painting_%d_canvas" % k, me)
        prop_collection.objects.link(cv)
        cv.parent = e
        cv.location = (0.0, -0.012, 0.0)
        fw = 0.07
        for (sx, sz, lx, lz) in ((pw + 2 * fw, fw, 0, ph / 2 + fw / 2), (pw + 2 * fw, fw, 0, -ph / 2 - fw / 2),
                                 (fw, ph, -pw / 2 - fw / 2, 0), (fw, ph, pw / 2 + fw / 2, 0)):
            p_box(e, "painting_%d_frame" % k, (sx, 0.05, sz), (lx, 0.0, lz), "trim_wood", 0.006)
        scan_meta["paintings"].append(fr)
        k += 1
    print("paintings hung: %d" % k)


import glob  # noqa: E402

if SCANS_OK:
    try:
        scan_items()
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCAN ITEMS FAILED:", ex)
    placed_rects = []
    try:
        placed_rects = place_scanned_props()
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCANNED PROPS FAILED:", ex)
    for fn in (place_lanterns, place_pedestals, dress_pooja, scan_candle):
        try:
            fn()
        except Exception as ex:     # noqa: BLE001
            import traceback
            traceback.print_exc()
            print("%s FAILED: %s" % (fn.__name__, ex))
    try:
        place_paintings(placed_rects)
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("PAINTINGS FAILED:", ex)
else:
    place_procedural_props()

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

# ----------------------------------------------------------------------------------------------- icons + check sheet
os.makedirs(os.path.join(out_dir, "icons"), exist_ok=True)
for it in meta["items"]:
    ob = bpy.data.objects.get(it["name"])
    if ob is None or ob.type != "MESH":
        continue
    try:
        scan_props.render_icon(ob, os.path.join(out_dir, "icons", it["id"] + ".png"))
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("ICON %s FAILED: %s" % (it["id"], ex))
if SCANS_OK:
    try:
        scan_props.contact_sheet(sorted(scan_props._templates.keys()), os.path.join(out_dir, "scans_preview.jpg"))
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("CONTACT SHEET FAILED:", ex)

# ----------------------------------------------------------------------------------------------- save + export
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "chaya_map.blend"))

gltf_keys = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()


def export_glb(path, objects):
    bpy.ops.object.select_all(action="DESELECT")
    for ob in objects:
        ob.select_set(True)
    kw = dict(filepath=path, export_format="GLTF_SEPARATE", export_texture_dir="tex", export_yup=True, export_apply=True, use_selection=True,
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
export_glb(os.path.join(out_dir, "maze.gltf"), house)
if candle_objs:
    try:
        export_glb(os.path.join(out_dir, "candle.gltf"), list(candle_objs))
    except Exception as ex:     # noqa: BLE001
        print("CANDLE EXPORT FAILED:", ex)
meta["props"] = prop_meta
meta["extra_lights"] = scan_meta["extra_lights"]
meta["paintings"] = scan_meta["paintings"]
meta["scanned"] = bool(SCANS_OK)
json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"))
print("done in %.1fs, bin %.1f MB, AO baked: %s" % (time.time() - t0, os.path.getsize(os.path.join(out_dir, "maze.bin")) / 1e6, baked))
