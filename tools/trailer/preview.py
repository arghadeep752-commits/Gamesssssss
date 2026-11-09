"""Quick look at the trailer scene: render a few frames small and noisy-but-denoised.

    blender -b trailer.blend --python-exit-code 1 -P tools/trailer/preview.py -- <out dir> <f1,f2,...> [percent] [samples]
"""
import os
import sys
import time

import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out = os.path.abspath(argv[0])
frames = [int(x) for x in argv[1].split(",") if x]
pct = int(argv[2]) if len(argv) > 2 else 50
spp = int(argv[3]) if len(argv) > 3 else 16
os.makedirs(out, exist_ok=True)
scene = bpy.context.scene
scene.render.resolution_percentage = pct
scene.cycles.samples = spp
scene.cycles.adaptive_min_samples = min(8, spp)
scene.render.use_persistent_data = True
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 90
markers = sorted((m for m in scene.timeline_markers if m.camera), key=lambda m: m.frame)
for f in frames:
    t0 = time.time()
    scene.frame_set(f)
    cam = None
    for m in markers:
        if m.frame <= f:
            cam = m.camera
    if cam is not None:
        scene.camera = cam
    scene.render.filepath = os.path.join(out, "p_%04d.jpg" % f)
    bpy.ops.render.render(write_still=True)
    print("[preview] frame %d (%s) %.1fs" % (f, scene.camera.name, time.time() - t0), flush=True)
