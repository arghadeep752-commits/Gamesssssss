"""Builds the game's PBR texture sets from the three photos the developer supplied.

  door.jpg  -> door_albedo / door_normal / door_rough
  wall.jpg  -> wall_albedo / wall_normal / wall_rough
  floor.jpg -> floor_albedo / floor_normal / floor_rough  (made tileable first, see make_tileable.py)

The normal and roughness maps are derived from the photos themselves (height = brightness),
so nothing is generated or downloaded. Run:  python3 tools/make_textures.py
"""
import os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "source_images")
OUT = os.path.join(HERE, "..", "assets", "textures")


def lum(rgb):
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def blur(a, radius, wrap):
    """Gaussian blur of a float image; wrap=True keeps tileable textures tileable."""
    if radius <= 0:
        return a
    pad = int(radius * 3) + 1
    p = np.pad(a, pad, mode="wrap" if wrap else "edge")
    fy = np.fft.fftfreq(p.shape[0])[:, None]
    fx = np.fft.fftfreq(p.shape[1])[None, :]
    g = np.exp(-2.0 * np.pi ** 2 * radius ** 2 * (fx ** 2 + fy ** 2))
    return np.fft.ifft2(np.fft.fft2(p) * g).real[pad:-pad, pad:-pad]


def normal_from_height(h, strength, wrap):
    if wrap:
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
        dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    else:
        dy, dx = np.gradient(h)
    nx = -dx * strength
    ny = dy * strength          # Godot expects OpenGL-style (Y+) normal maps
    nz = np.ones_like(h)
    n = np.stack([nx, ny, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return Image.fromarray(((n * 0.5 + 0.5) * 255).round().astype(np.uint8), "RGB")


def save_gray(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255).round().astype(np.uint8), "L").save(os.path.join(OUT, name))


def build(name, src_img, size, wrap, normal_strength, rough_fn, height_blur=1.0, brighten=1.0):
    img = src_img.convert("RGB").resize(size, Image.LANCZOS)
    if brighten != 1.0:
        # the door photo is under-exposed (white paint shows as grey); lift it a little
        img = Image.fromarray(np.clip(np.asarray(img).astype(np.float64) * brighten, 0, 255).astype(np.uint8))
    img.save(os.path.join(OUT, name + "_albedo.png"))
    a = np.asarray(img).astype(np.float64) / 255.0
    L = lum(a)
    h = blur(L, height_blur, wrap)
    normal_from_height(h, normal_strength, wrap).save(os.path.join(OUT, name + "_normal.png"))
    save_gray(rough_fn(L, wrap), name + "_rough.png")
    print(name, size)


def floor_rough(L, wrap):
    # varnished parquet: glossy planks, rough dark gaps between them
    local = blur(L, 18, wrap)
    gaps = np.clip((local - L) * 9.0, 0, 1)            # thin dark lines between planks
    grain = np.clip(1.0 - (L - L.min()) / (np.ptp(L) + 1e-6), 0, 1)
    return np.clip(0.26 + 0.18 * grain + 0.55 * gaps, 0.2, 0.95)


def wall_rough(L, wrap):
    # matte paper; the printed (darker) ink is a little smoother
    ink = np.clip((L.max() - L) / (np.ptp(L) + 1e-6), 0, 1)
    return np.clip(0.82 - 0.16 * ink, 0.5, 0.9)


def door_rough(L, wrap):
    # semi-gloss white paint, the moulding grooves collect dust
    local = blur(L, 10, wrap)
    grooves = np.clip((local - L) * 6.0, 0, 1)
    return np.clip(0.36 + 0.35 * grooves, 0.3, 0.8)


def main():
    os.makedirs(OUT, exist_ok=True)
    # floor: cut to an exact repeat of the herringbone first so it tiles without seams
    import subprocess, sys
    tile = os.path.join(HERE, "floor_tile.png")
    subprocess.check_call([sys.executable, os.path.join(HERE, "make_tileable.py"),
                           os.path.join(SRC, "floor.jpg"), tile, "619", "401"])
    build("floor", Image.open(tile), (1024, 664), True, 6.0, floor_rough)
    os.remove(tile)
    build("wall", Image.open(os.path.join(SRC, "wall.jpg")), (1024, 1152), True, 2.5, wall_rough)
    build("door", Image.open(os.path.join(SRC, "door.jpg")), (512, 1372), False, 5.0, door_rough, 1.4, brighten=1.18)


if __name__ == "__main__":
    main()
