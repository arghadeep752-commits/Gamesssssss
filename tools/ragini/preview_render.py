"""Cycles preview renders of Ragini (for checking the build; not part of the game)."""
import math
import os

import bpy
from mathutils import Vector

import animate


def _look(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def _area(name, loc, target, energy, size, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.size = size
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    _look(ob, target)
    return ob


def render_all(scene, arm, meshes, out, log, quick=False):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 16 if quick else 40
    try:
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:       # noqa: BLE001
        pass
    scene.render.resolution_x = 640 if quick else 760
    scene.render.resolution_y = 860 if quick else 1020
    scene.render.film_transparent = False
    scene.view_settings.view_transform = "AgX" if "AgX" in [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items] else "Filmic"
    world = bpy.data.worlds.new("preview_world")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.012, 0.012, 0.016, 1.0)
    bg.inputs[1].default_value = 1.0
    _area("key", (-1.3, -2.2, 2.5), (0, 0, 1.2), 520, 1.6, (1.0, 0.92, 0.85))
    _area("fill", (1.8, -1.6, 1.3), (0, 0, 1.1), 140, 2.0, (0.75, 0.82, 1.0))
    _area("rim", (0.6, 2.0, 2.2), (0, 0, 1.3), 380, 1.2, (1.0, 0.75, 0.7))
    floor_me = bpy.data.meshes.new("floor")
    floor_me.from_pydata([(-3, -3, 0), (3, -3, 0), (3, 3, 0), (-3, 3, 0)], [], [(0, 1, 2, 3)])
    floor = bpy.data.objects.new("floor", floor_me)
    scene.collection.objects.link(floor)
    fm = bpy.data.materials.new("floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.05, 0.045, 0.04, 1)
    floor_me.materials.append(fm)
    cd = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    if arm.animation_data:
        for tr in arm.animation_data.nla_tracks:
            tr.mute = True
    shots = [
        ("01_full_front", (0.0, -4.4, 1.05), (0, 0, 0.92), 42, None),
        ("02_full_quarter", (2.6, -3.4, 1.2), (0, 0, 0.92), 42, None),
        ("03_face", (0.28, -0.78, 1.63), (0, -0.03, 1.575), 70, None),
        ("04_face_front", (0.0, -0.72, 1.6), (0, -0.03, 1.58), 75, None),
        ("05_back", (-1.0, 4.0, 1.25), (0, 0, 0.95), 42, None),
        ("06_walk", (2.8, -3.0, 1.1), (0, 0, 0.9), 42, lambda: animate.walk(0.3, 1.2)),
        ("07_attack", (2.0, -2.8, 1.4), (0, 0, 1.1), 40, lambda: animate.attack(0.33, 1.3)),
        ("08_scream", (0.4, -1.5, 1.55), (0, 0, 1.45), 55, lambda: animate.scream(0.6, 1.6)),
        ("09_run", (-2.8, -3.2, 1.1), (0, 0, 0.9), 42, lambda: animate.run(0.1, 0.7)),
    ]
    if quick:
        shots = shots[:4] + shots[5:7]
    for name, cp, tgt, lens, posefn in shots:
        animate.apply(arm, posefn() if posefn else animate.base(animate.Pose()))
        bpy.context.view_layer.update()
        cam.location = cp
        cd.lens = lens
        _look(cam, tgt)
        scene.render.filepath = os.path.join(out, "preview_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        log("rendered", name)
    animate.apply(arm, animate.Pose())
    if arm.animation_data:
        for tr in arm.animation_data.nla_tracks:
            tr.mute = False
    for ob in list(scene.objects):
        if ob.name in ("key", "fill", "rim", "floor", "cam"):
            bpy.data.objects.remove(ob, do_unlink=True)
