"""blender -b trailer.blend -P render_frames.py -- OUT_DIR PERCENT SAMPLES FRAME [FRAME ...]  (one process, many frames)"""
import bpy
import os
import sys

argv = sys.argv[sys.argv.index("--") + 1:]
out, pct, spp = argv[0], int(argv[1]), int(argv[2])
frames = [int(f) for f in argv[3:]]
sc = bpy.context.scene
sc.render.resolution_percentage = pct
sc.cycles.samples = spp
os.makedirs(out, exist_ok=True)
for f in frames:
    sc.frame_set(f)
    sc.render.filepath = os.path.join(out, "f_%04d.png" % f)
    bpy.ops.render.render(write_still=True)
    print("[frame]", f, flush=True)
