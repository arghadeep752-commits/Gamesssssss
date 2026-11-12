"""Chaya - turn the AI pictures into 3D models with TripoSR (MIT, VAST AI + Stability AI) on the CPU of a CI runner.

    python3 tsr_run.py <pictures dir> <out dir> names...
"""
import os
import subprocess
import sys
import time

src, out, names = sys.argv[1], sys.argv[2], sys.argv[3:]
os.makedirs(out, exist_ok=True)
for n in names:
    png = os.path.join(src, n + ".png")
    if not os.path.exists(png):
        print("no picture for", n)
        continue
    t0 = time.time()
    od = os.path.join(out, "tsr_" + n)
    cmd = [sys.executable, "TripoSR/run.py", png, "--device", "cpu", "--output-dir", od, "--mc-resolution", "256",
           "--foreground-ratio", "0.85", "--model-save-format", "obj", "--bake-texture", "--texture-resolution", "1024"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print(n, "bake failed, vertex colours instead:", r.stderr[-600:])
        cmd = [c for c in cmd if c not in ("--bake-texture", "--texture-resolution", "1024")]
        r = subprocess.run(cmd, capture_output=True, text=True)
    print("%s: exit %d in %.0fs" % (n, r.returncode, time.time() - t0))
    print(r.stdout[-500:], r.stderr[-800:])
