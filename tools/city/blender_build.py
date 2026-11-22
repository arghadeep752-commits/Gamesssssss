"""Assembles the generated Agartala map in Blender: every 128 m chunk becomes an object (roads, buildings, trees,
water, ground), coloured by its surface layer, saved as city.blend with aerial preview renders.

    blender -b --factory-startup -P tools/city/blender_build.py -- <Assets/Game/City dir> <out dir>
"""
import math
import os
import struct
import sys

import bpy
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
CITY, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
VERT = np.dtype([("p", "<f4", 3), ("n", "i1", 4), ("c", "u1", 4), ("uv", "<f4", 2), ("x", "u1", 4)])
NAMES = {0: "world", 1: "foliage", 2: "water", 3: "terrain"}


def layer_colours():
    """Average colour of each surface photo (Layers/NN_name.png) so the Blender scene looks like the game."""
    cols = {}
    d = os.path.join(CITY, "Layers")
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if f.endswith("_n.png"):
            continue
        try:
            i = int(f[:2])
            img = bpy.data.images.load(os.path.join(d, f))
            img.scale(16, 16)
            px = np.array(img.pixels[:], np.float32).reshape(-1, 4)
            a = px[:, 3:4]
            cols[i] = (px[:, :3] * a).sum(0) / max(1e-3, float(a.sum()))
            bpy.data.images.remove(img)
        except Exception as e:  # noqa: BLE001
            print("layer", f, e)
    return cols


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cols = layer_colours()
    data = open(os.path.join(CITY, "chunks.bytes"), "rb").read()
    magic, ver, size, half, count = struct.unpack_from("<iiffi", data, 0)
    p = 20
    coll = bpy.data.collections.new("Agartala")
    bpy.context.scene.collection.children.link(coll)
    mat = bpy.data.materials.new("city")
    mat.use_nodes = True
    nt = mat.node_tree
    attr = nt.nodes.new("ShaderNodeVertexColor")
    attr.layer_name = "Col"
    nt.links.new(attr.outputs["Color"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    total = 0
    for _ in range(count):
        ix, iz, ng = struct.unpack_from("<iii", data, p)
        p += 12
        for _g in range(ng):
            gid, = struct.unpack_from("<i", data, p)
            p += 4
            nv, = struct.unpack_from("<i", data, p)
            if gid == 4:
                p += 4 + nv * 12
                ni, = struct.unpack_from("<i", data, p)
                p += 4 + ni * 4
                continue
            p += 4 + 24
            v = np.frombuffer(data, VERT, nv, p)
            p += nv * 32
            ni, isz = struct.unpack_from("<ii", data, p)
            p += 8
            idx = np.frombuffer(data, "<u2" if isz == 2 else "<i4", ni, p).astype(np.int64)
            p += ni * isz + (2 if isz == 2 and ni % 2 else 0)
            P = v["p"][:, [0, 2, 1]].astype(np.float64)               # Unity (x, y up, z) -> Blender (x, y, z up)
            m = bpy.data.meshes.new("c%d_%d_%s" % (ix, iz, NAMES.get(gid, gid)))
            m.vertices.add(nv)
            m.vertices.foreach_set("co", P.ravel())
            nt_ = ni // 3
            m.loops.add(ni)
            m.loops.foreach_set("vertex_index", idx)
            m.polygons.add(nt_)
            m.polygons.foreach_set("loop_start", np.arange(0, ni, 3))
            m.polygons.foreach_set("loop_total", np.full(nt_, 3))
            m.update()
            base = np.array([cols.get(int(s), np.array([0.6, 0.6, 0.6])) for s in v["x"][:, 0]], np.float32)
            rgb = base * (v["c"][:, :3].astype(np.float32) / 255.0) * (0.35 + 0.65 * v["x"][:, 1:2].astype(np.float32) / 255.0)
            if gid == 2:
                rgb[:] = (0.08, 0.22, 0.28)
            ca = m.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
            ca.data.foreach_set("color", np.hstack([rgb, np.ones((nv, 1), np.float32)]).ravel())
            m.materials.append(mat)
            ob = bpy.data.objects.new(m.name, m)
            coll.objects.link(ob)
            total += nt_
    print("blender: %d chunks, %d triangles" % (count, total))
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "VERTEX"
    sc.display.shading.show_shadows = True
    sc.display.shading.show_cavity = True
    sc.render.resolution_x, sc.render.resolution_y = 1600, 900
    sc.world = bpy.data.worlds.new("sky")
    sc.world.color = (0.55, 0.65, 0.78)
    cam = bpy.data.cameras.new("aerial")
    cam.clip_end = 6000
    co = bpy.data.objects.new("aerial", cam)
    sc.collection.objects.link(co)
    sc.camera = co
    views = {"aerial_palace": ((0, -380, 260), (62, 0, 0)), "aerial_city": ((300, -1500, 900), (58, 0, -12)), "top": ((0, 0, 2600), (0, 0, 0))}
    for name, (loc, rot) in views.items():
        co.location = loc
        co.rotation_euler = [math.radians(a) for a in rot]
        cam.lens = 30 if name != "top" else 50
        sc.render.filepath = os.path.join(OUT, name + ".png")
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "city.blend"), compress=True)


main()
