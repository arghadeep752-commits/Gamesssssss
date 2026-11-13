"""Cycles preview renders of the school with its night lighting (build check only)."""
import os

import bpy
from mathutils import Vector

VIEWS = [
    ("school_01_classroom", (-8.2, -2.5, 1.6), (-14.0, -2.6, 1.3)),
    ("school_02_main_door", (0.0, 0.2, 1.6), (0.0, -6.0, 1.3)),
    ("school_03_veranda", (-7.8, 2.2, 1.6), (8.0, 2.2, 1.3)),
    ("school_04_courtyard", (6.2, 13.6, 1.7), (-3.0, 7.0, 1.6)),
    ("school_05_principal", (-3.1, -0.4, 1.6), (-5.4, -4.6, 0.9)),
    ("school_06_front", (3.5, -15.5, 1.7), (0.0, -6.0, 2.6)),
    ("school_07_store", (9.7, 9.7, 1.6), (13.2, 9.3, 0.5)),
    ("school_08_hall", (2.0, 16.0, 1.7), (-6.0, 21.0, 1.4)),
    ("school_09_class7", (-11.5, 7.4, 1.6), (-11.5, 1.0, 1.3)),
]


def render_all(scene, L, out, log, quick=False):
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 12 if quick else 28
    try:
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:       # noqa: BLE001
        pass
    scene.render.resolution_x = 640 if quick else 960
    scene.render.resolution_y = 360 if quick else 540
    names = [i.identifier for i in scene.view_settings.bl_rna.properties["view_transform"].enum_items]
    scene.view_settings.view_transform = "AgX" if "AgX" in names else "Filmic"
    scene.view_settings.exposure = 0.6
    cd = bpy.data.cameras.new("preview_cam")
    cd.lens = 20
    cam = bpy.data.objects.new("preview_cam", cd)
    scene.collection.objects.link(cam)
    scene.camera = cam
    views = VIEWS[:4] if quick else VIEWS
    for name, p, t in views:
        cam.location = Vector(p)
        cam.rotation_euler = (Vector(t) - Vector(p)).to_track_quat("-Z", "Y").to_euler()
        scene.render.filepath = os.path.join(out, "preview_%s.png" % name)
        bpy.ops.render.render(write_still=True)
        log("rendered", name)
    bpy.data.objects.remove(cam, do_unlink=True)
