"""Six 90-degree camera views -> one equirectangular panorama in Godot's sky layout.

Godot's panorama sky looks up a direction d with
    u = atan2(d.x, -d.z) / 2pi   (wrapped to 0..1, u = 0 is -Z, u = 0.25 is +X)
    v = acos(d.y) / pi            (v = 0 is straight up)
Usage: python3 cube_to_panorama.py faces.json out.png [width]
"""
import json
import sys
import numpy as np
from PIL import Image


def main():
    spec = json.load(open(sys.argv[1]))
    out_path = sys.argv[2]
    width = int(sys.argv[3]) if len(sys.argv) > 3 else 1024
    height = width // 2
    faces = []
    for f in spec["faces"]:
        img = np.asarray(Image.open(f["path"]).convert("RGB")).astype(np.float32)
        faces.append((img, np.array(f["right"]), np.array(f["up"]), np.array(f["forward"])))
    t = np.tan(np.radians(spec["fov"]) / 2.0)

    u = (np.arange(width) + 0.5) / width
    v = (np.arange(height) + 0.5) / height
    uu, vv = np.meshgrid(u, v)
    theta = uu * 2.0 * np.pi
    phi = vv * np.pi
    d = np.stack([np.sin(phi) * np.sin(theta), np.cos(phi), -np.sin(phi) * np.cos(theta)], -1)

    out = np.zeros((height, width, 3), np.float32)
    best = np.full((height, width), -np.inf)
    for img, right, up, fwd in faces:
        h, w, _ = img.shape
        z = d @ fwd
        x = (d @ right) / np.maximum(z, 1e-6) / t
        y = (d @ up) / np.maximum(z, 1e-6) / t
        use = (z > best) & (z > 0)
        best = np.where(use, z, best)
        px = np.clip((x + 1.0) * 0.5 * w - 0.5, 0, w - 1.001)
        py = np.clip((1.0 - y) * 0.5 * h - 0.5, 0, h - 1.001)
        x0 = np.floor(px).astype(int)
        y0 = np.floor(py).astype(int)
        fx = (px - x0)[..., None]
        fy = (py - y0)[..., None]
        s = (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x0 + 1] * fx * (1 - fy)
             + img[y0 + 1, x0] * (1 - fx) * fy + img[y0 + 1, x0 + 1] * fx * fy)
        out = np.where(use[..., None], s, out)
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8)).save(out_path)
    print("panorama", out_path, width, "x", height, "mean", round(float(out.mean()), 1))


if __name__ == "__main__":
    main()
