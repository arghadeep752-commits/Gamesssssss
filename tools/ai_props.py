"""Chaya - AI-generated 3D models (Hyper3D Rodin) made ready for the game.

    blender -b -P tools/ai_props.py -- <rodin_<name>.glb ...> <out dir, e.g. tools/ai3d>

For each model: join it into one mesh, put its origin at the bottom centre (front facing -Y), scale it to its real
size, keep it inside a phone triangle budget, shrink its PBR textures (colour and normal 1024, metal/roughness 512),
and save a small GLB whose material is named scan_ai_<name> (the game keeps its textures as they are).
tools/build_map.py picks the files up from tools/ai3d/ on every build.
"""
import os
import sys

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
FILES, OUT = argv[:-1], argv[-1]
os.makedirs(OUT, exist_ok=True)

# name: (height in metres, triangle budget)
SPEC = {"murti": (1.0, 14000), "kalash": (0.30, 6000)}


def tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def bbox(me):
    xs = [v.co for v in me.vertices]
    return (Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs))),
            Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs))))


def process(src):
    name = os.path.splitext(os.path.basename(src))[0].replace("rodin_", "")
    height, budget = SPEC.get(name, (0.5, 6000))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=src)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in list(bpy.data.objects):
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    me = ob.data
    t0 = tris(me)
    if t0 > budget:
        mod = ob.modifiers.new("dec", "DECIMATE")
        mod.ratio = budget / t0
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        ob.modifiers.clear()
        ob.data = me2
        me = me2
    mn, mx = bbox(me)
    me.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    me.transform(Matrix.Scale(height / max(mx.z - mn.z, 1e-6), 4))
    for p in me.polygons:
        p.use_smooth = True
    ob.name = me.name = "ai_" + name
    for m in me.materials:
        if m is None:
            continue
        m.name = "scan_ai_" + name
        for n in (m.node_tree.nodes if m.use_nodes else []):
            img = getattr(n, "image", None)
            if n.type != "TEX_IMAGE" or img is None:
                continue
            low = img.name.lower()
            kind = "nor" if "normal" in low else ("arm" if ("metal" in low or "rough" in low) else "diff")
            size = 512 if kind == "arm" else 1024
            if img.size[0] > size:
                img.scale(size, size)
            img.name = "ai_%s_%s_1k" % (name, kind)
    mn, mx = bbox(me)
    out = os.path.join(OUT, name + ".glb")
    bpy.ops.export_scene.gltf(filepath=out, export_format="GLB", use_selection=False, export_apply=True,
                              export_image_format="JPEG", export_jpeg_quality=90, export_cameras=False, export_lights=False)
    print("AI %-8s %6d -> %6d tris, %.2f x %.2f x %.2f m, %d KB" % (name, t0, tris(me), *(mx - mn), os.path.getsize(out) // 1024))


for f in FILES:
    process(f)
