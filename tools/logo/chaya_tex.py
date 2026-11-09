#!/usr/bin/env python3
"""Chaya's look for the Blender logo render: the same treatment the game shader applies, baked into textures.

    python3 tools/logo/chaya_tex.py <rocketbox tex dir> <out dir>

head: ashen skin, black sunken eye sockets, blood tears, dark lips (UV regions match the game's head shader)
body: ashen skin, the clothes recoloured to a dirty blood-red saree
"""
import os
import sys

import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
PALLOR = np.array([0.62, 0.70, 0.82], np.float32)
SAREE = np.array([0.24, 0.006, 0.016], np.float32)


def load(name):
    im = Image.open(os.path.join(src, name)).convert("RGB")
    return np.asarray(im).astype(np.float32) / 255.0


def noise(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    g = rng.random((int(h / scale) + 2, int(w / scale) + 2)).astype(np.float32)
    im = Image.fromarray((g * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255.0


def skin_of(c):
    lum = (c * np.array([0.299, 0.587, 0.114], np.float32)).sum(-1, keepdims=True)
    return (lum * 0.5 + c * 0.5) * PALLOR * 0.85, lum


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------------------------------------ head
c = load("f152_head_color.tga")
h, w, _ = c.shape
v, u = np.mgrid[0:h, 0:w].astype(np.float32)
u = (u + 0.5) / w
v = (v + 0.5) / h                      # image row 0 = UV v 0 in Godot's convention (top)
skin, lum = skin_of(c)
gold = ((c[..., 0] > 0.5) & (c[..., 1] > 0.38) & (c[..., 2] < 0.3) & ((u < 0.27) | (u > 0.73))).astype(np.float32)[..., None]
skin = skin * (1 - gold) + 0.015 * gold
d1 = np.hypot((u - 0.430) / 0.062, (v - 0.283) / 0.036)
d2 = np.hypot((u - 0.570) / 0.062, (v - 0.283) / 0.036)
sock = (1.0 - smoothstep(0.45, 1.3, np.minimum(d1, d2)))[..., None]
skin = skin * (1.0 - sock * 0.9)
# blood tears: thin wandering streaks from the lower lids, thicker drops where they stop
tr = np.zeros_like(u)
for x0, ph, end in ((0.428, 0.0, 0.47), (0.572, 2.1, 0.445), (0.446, 4.0, 0.39), (0.556, 1.3, 0.37)):
    cx = x0 + 0.0035 * np.sin(v * 38.0 + ph) + 0.0015 * np.sin(v * 91.0 + ph * 2.0)
    wid = 0.0028 + 0.0016 * np.sin(v * 23.0 + ph) + 0.004 * smoothstep(end - 0.03, end, v)
    streak = smoothstep(wid, wid * 0.35, np.abs(u - cx)) * smoothstep(0.30, 0.318, v) * (1.0 - smoothstep(end, end + 0.012, v))
    tr = np.maximum(tr, streak * (0.75 if x0 in (0.446, 0.556) else 1.0))
tr = tr[..., None]
blood = np.array([0.33, 0.0, 0.01], np.float32) * (0.75 + 0.25 * noise(h, w, 4, 9)[..., None])
skin = skin * (1 - tr * 0.96) + blood * tr * 0.96
lip = (1.0 - smoothstep(0.5, 1.2, np.hypot((u - 0.5) / 0.055, (v - 0.412) / 0.016)))[..., None]
skin = skin * (1 - lip * 0.8) + np.array([0.10, 0.04, 0.07], np.float32) * lip * 0.8
# faint dark veins and grime
g = noise(h, w, 9, 3)[..., None] * 0.6 + noise(h, w, 3, 4)[..., None] * 0.4
skin *= 0.88 + 0.12 * g
Image.fromarray((np.clip(skin, 0, 1) ** (1 / 1.0) * 255).astype(np.uint8)).save(os.path.join(out, "head_chaya.png"))

# ------------------------------------------------------------------------------------------------ body
c = load("f152_body_color.tga")
h, w, _ = c.shape
skin, lum = skin_of(c)
mx = c.max(-1)
mn = c.min(-1)
sat = mx - mn
coat = (smoothstep(0.26, 0.10, sat) * smoothstep(0.30, 0.55, mx))[..., None]
grime = noise(h, w, 22, 5)[..., None] * 0.6 + noise(h, w, 8, 6)[..., None] * 0.4
cloth = SAREE * (0.35 + 0.9 * lum) * (1.0 - 0.65 * smoothstep(0.5, 0.85, grime))
col = skin * (1 - coat) + cloth * coat
Image.fromarray((np.clip(col, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, "body_chaya.png"))
print("textures written to", out)
