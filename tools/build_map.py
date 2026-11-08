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
            scene.world.light_settings.distance = 1.8
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
        ao = 0.25 + 0.75 * ao ** 0.8
        arr[:, 0] = arr[:, 1] = arr[:, 2] = ao
        arr[:, 3] = 1.0
        attr.data.foreach_set("color", arr.reshape(-1))
        vals.append(ao)
    if vals:
        a = np.concatenate(vals)
        print("AO values: min %.2f mean %.2f max %.2f" % (a.min(), a.mean(), a.max()))

# ----------------------------------------------------------------------------------------------- save + export
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out_dir, "chaya_map.blend"))

props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
kw = dict(filepath=os.path.join(out_dir, "maze.glb"), export_format="GLB", export_yup=True, export_apply=True,
          export_texcoords=True, export_normals=True, export_materials="EXPORT", export_cameras=False,
          export_lights=False, export_animations=False)
if "export_tangents" in props:
    kw["export_tangents"] = True
if "export_vertex_color" in props:
    kw["export_vertex_color"] = "ACTIVE"
    if "export_active_vertex_color_when_no_material" in props:
        kw["export_active_vertex_color_when_no_material"] = True
elif "export_colors" in props:
    kw["export_colors"] = True
kw = {k: v for k, v in kw.items() if k in props}
print("glTF export options:", kw)
bpy.ops.export_scene.gltf(**kw)

json.dump(meta, open(os.path.join(out_dir, "meta.json"), "w"))
print("done in %.1fs, glb %.1f MB, AO baked: %s" % (time.time() - t0, os.path.getsize(os.path.join(out_dir, "maze.glb")) / 1e6, baked))
