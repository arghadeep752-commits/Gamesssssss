#!/usr/bin/env python3
"""Local development only: procedural stand-ins for the photographic textures that CI downloads."""
import os, sys
import numpy as np
from PIL import Image

out = sys.argv[1] if len(sys.argv) > 1 else "assets/downloaded/tex"
rng = np.random.default_rng(3)

def noise(n, cells, oct=3):
    a = np.zeros((n, n))
    for o in range(oct):
        c = cells * 2 ** o
        g = rng.random((c, c))
        a += np.kron(g, np.ones((n // c + 1, n // c + 1)))[:n, :n] * 0.5 ** o
    return a / a.max()

def planks(base, n=512, rows=6, vertical=False):
    img = np.zeros((n, n, 3))
    nz = noise(n, 8)
    for r in range(rows):
        y0, y1 = r * n // rows, (r + 1) * n // rows
        shade = 0.75 + rng.random() * 0.4
        grain = noise(n, 4)[y0:y1]
        img[y0:y1] = np.array(base)[None, None] * (shade * (0.7 + 0.5 * grain))[..., None]
        img[y0:y0 + 3] *= 0.3
    if vertical:
        img = img.transpose(1, 0, 2)
    return np.clip(img * (0.8 + 0.4 * nz[..., None]), 0, 1)

def flat(base, n=512, var=0.25):
    nz = noise(n, 10)
    return np.clip(np.array(base)[None, None] * (1 - var + 2 * var * nz[..., None]), 0, 1)

slots = {
    "wood_floor": planks((0.45, 0.30, 0.18)),
    "stone_floor": flat((0.55, 0.53, 0.5), var=0.3),
    "wood_wall": planks((0.4, 0.27, 0.16), vertical=True),
    "plaster": flat((0.7, 0.66, 0.58), var=0.2),
    "wood_ceiling": planks((0.38, 0.26, 0.15)),
    "wood_dark": planks((0.3, 0.2, 0.12)),
    "wood_door": planks((0.4, 0.26, 0.15), vertical=True, rows=4),
    "brass": flat((0.8, 0.6, 0.25), var=0.1),
    "cloth": flat((0.8, 0.2, 0.2), var=0.15),
    "clay": flat((0.75, 0.4, 0.28), var=0.15),
    "fiber": flat((0.5, 0.36, 0.22), var=0.3),
    "copper": flat((0.8, 0.45, 0.3), var=0.1),
}
for s, a in slots.items():
    d = os.path.join(out, s)
    os.makedirs(d, exist_ok=True)
    Image.fromarray((a * 255).astype(np.uint8)).save(os.path.join(d, "diff.png"))
print("dev textures:", ", ".join(slots))
