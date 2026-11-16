#!/usr/bin/env python3
"""Turns the Godot game's assets into files the Unity project builds from.

    convert_assets.py --school DIR --moulika FILE --tex DIR --sounds DIR --fonts DIR [DIR] --ui DIR --out UNITY_PROJECT

The school (school.glb + school_meta.json + lightmaps/) and Moulika (moulika_rigged.glb) are the same files the
Godot build uses. Godot and glTF are right-handed with Y up; Unity is left-handed with Y up. Everything is mirrored
on Z (x, y, z) -> (x, y, -z), triangle winding is reversed and rotations become (-x, -y, z, w).

Writes:
  Assets/Game/School/school.bytes          meshes of every school object (see write_school for the layout)
  Assets/Game/School/Textures/*.jpg         the Hyper3D models' own colour textures
  Assets/Game/School/Photos/<slot>.jpg       photographed surface textures (tinted per material in the shader)
  Assets/Game/School/Lightmaps/<name>.png    the night lighting baked in Blender
  Assets/Game/School/materials.json          per material: photo slot, tint, average brightness of the photo, ...
  Assets/Game/Moulika/moulika.bytes          skinned mesh, skeleton and the five moves (see write_moulika)
  Assets/Game/Moulika/*.png                  her textures
  Assets/Resources/school_meta.json          doors, items, rooms, lights, walk grid ... (read by the game)
  Assets/Resources/Sounds/*.ogg, Fonts/*, UI/*.png
"""
import argparse
import json
import math
import os
import shutil
import struct
import sys

import numpy as np

try:
    from PIL import Image
except ImportError:  # only needed for the average brightness of the photos and the leaf texture
    Image = None


# ------------------------------------------------------------------------------------------------ glTF reading
def load_glb(path):
    b = open(path, "rb").read()
    magic, _ver, length = struct.unpack_from("<4sII", b, 0)
    assert magic == b"glTF", path
    o, js, binc = 12, None, None
    while o < length:
        cl, ct = struct.unpack_from("<II", b, o)
        o += 8
        if ct == 0x4E4F534A:
            js = json.loads(b[o:o + cl])
        elif ct == 0x004E4942:
            binc = b[o:o + cl]
        o += cl
    return js, binc


COMP = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def accessor(js, binc, i):
    a = js["accessors"][i]
    bv = js["bufferViews"][a["bufferView"]]
    dt = np.dtype(COMP[a["componentType"]])
    n = NCOMP[a["type"]]
    off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = bv.get("byteStride", 0)
    count = a["count"]
    if stride and stride != dt.itemsize * n:
        raw = np.frombuffer(binc, dtype=np.uint8, count=stride * (count - 1) + dt.itemsize * n, offset=off)
        arr = np.lib.stride_tricks.as_strided(raw, shape=(count, dt.itemsize * n), strides=(stride, 1)).copy()
        arr = arr.view(dt).reshape(count, n)
    else:
        arr = np.frombuffer(binc, dtype=dt, count=count * n, offset=off).reshape(count, n).copy()
    if a.get("normalized"):
        if dt == np.uint8:
            arr = arr.astype(np.float32) / 255.0
        elif dt == np.uint16:
            arr = arr.astype(np.float32) / 65535.0
    return arr if n > 1 else arr[:, 0]


def image_bytes(js, binc, img_index):
    im = js["images"][img_index]
    bv = js["bufferViews"][im["bufferView"]]
    o = bv.get("byteOffset", 0)
    return binc[o:o + bv["byteLength"]], im.get("mimeType", "image/png")


# ------------------------------------------------------------------------------------------------ writing helpers
class Out:
    def __init__(self):
        self.parts = []

    def i32(self, v):
        self.parts.append(struct.pack("<i", int(v)))

    def f32(self, *v):
        self.parts.append(struct.pack("<%df" % len(v), *[float(x) for x in v]))

    def s(self, t):
        b = t.encode("utf-8")
        self.i32(len(b))
        self.parts.append(b)

    def arr(self, a, dtype):
        self.parts.append(np.ascontiguousarray(a, dtype=dtype).tobytes())

    def save(self, path):
        with open(path, "wb") as f:
            for p in self.parts:
                f.write(p)


def mirror_v3(a):
    a = np.array(a, dtype=np.float32, copy=True)
    a[..., 2] *= -1.0
    return a


def mirror_q(q):
    q = np.array(q, dtype=np.float32, copy=True)
    q[..., 0] *= -1.0
    q[..., 1] *= -1.0
    return q


def flip_uv(uv):
    uv = np.array(uv, dtype=np.float32, copy=True)
    uv[:, 1] = 1.0 - uv[:, 1]
    return uv


def flip_winding(idx):
    t = np.array(idx, dtype=np.int64).reshape(-1, 3)
    return t[:, [0, 2, 1]].reshape(-1)


def srgb_to_linear(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def ensure(d):
    os.makedirs(d, exist_ok=True)
    return d


# ------------------------------------------------------------------------------------------------ the school
# material -> [photo slot, how much of the paint colour replaces the photo's own colour]  (game/scripts/mats.gd)
MAP = {
    "plaster": ["plaster", 0.75], "plaster_ext": ["plaster_rough", 0.8], "ceiling": ["plaster", 0.85], "plinth": ["plaster_rough", 0.85],
    "floor_cement": ["concrete_floor", 0.35], "floor_terrazzo": ["terrazzo", 0.3], "floor_tiles": ["tiles_white", 0.2],
    "floor_kota": ["stone_floor", 0.5], "floor_veranda": ["red_tiles", 0.45], "dado_green": ["paint_chipped", 0.9],
    "dado_blue": ["paint_chipped", 0.9], "dado_red": ["paint_chipped", 0.9], "dado_brown": ["paint_chipped", 0.9],
    "dado_tiles": ["tiles_white", 0.2], "wood": ["wood", 0.6], "wood_dark": ["wood", 0.85], "wood_old": ["wood_old", 0.4],
    "wood_painted_blue": ["wood_painted", 0.9], "wood_painted_green": ["wood_painted", 0.9], "wood_door_main": ["wood_old", 0.7],
    "wood_plank": ["wood_old", 0.35], "wood_handle": ["wood", 0.6], "metal_green": ["metal_painted", 0.9],
    "metal_grey": ["metal_painted", 0.92], "metal_white": ["metal_painted", 0.95], "rust": ["rust", 0.25],
    "steel": ["metal_brushed", 0.7], "steel_face": ["metal_brushed", 0.7], "aluminium": ["metal_brushed", 0.6],
    "aluminium_soot": ["metal_brushed", 0.9], "brass": ["metal_brushed", 0.92], "iron_old": ["rust", 0.8],
    "chalkboard": ["slate", 0.85], "concrete": ["concrete", 0.3], "concrete_wet": ["concrete", 0.6], "ground_dirt": ["ground_dirt", 0.3],
    "ground_court": ["ground_court", 0.4], "brick_path": ["brick", 0.4], "brick_soot": ["brick", 0.85], "roof": ["concrete", 0.5],
    "sack": ["hessian", 0.4], "fabric_mat": ["hessian", 0.7], "curtain": ["fabric", 0.92], "felt": ["fabric", 0.95],
    "felt_green": ["fabric", 0.95], "file_cloth": ["fabric", 0.95], "bark": ["bark", 0.3], "cardboard": ["cardboard", 0.5],
    "paper": ["cardboard", 0.97], "register_red": ["cardboard", 0.95], "register_blue": ["cardboard", 0.95], "book_red": ["cardboard", 0.95],
    "book_blue": ["cardboard", 0.95], "book_green": ["cardboard", 0.95], "book_brown": ["cardboard", 0.9], "book_black": ["cardboard", 0.97],
    "clay": ["concrete", 0.92], "ceramic": ["tiles_white", 0.9], "ash": ["concrete", 0.6], "broom": ["hessian", 0.6],
    "rope": ["hessian", 0.7], "cane": ["wood", 0.8], "tag_white": ["cardboard", 0.95], "tag_yellow": ["cardboard", 0.95],
}
TWO_SIDED = ["leaves", "curtain", "paper", "tag_white", "tag_yellow", "glass", "glass_dirty"]


def photo_average(path):
    """dot(average colour, 1/3) of a photo in linear light (the shader's textureLod(tex, UV, 9.0) in mats.gd)."""
    if Image is None or not os.path.exists(path):
        return 0.5
    im = Image.open(path).convert("RGB")
    im.thumbnail((256, 256))
    a = np.asarray(im, dtype=np.float64) / 255.0
    mean_srgb = a.reshape(-1, 3).mean(0)
    return float(srgb_to_linear(mean_srgb).mean())


def make_leaves(path):
    """Neem leaflets with alpha (Mats._make_leaves)."""
    if Image is None:
        return
    import random
    n = 128
    img = np.zeros((n, n, 4), dtype=np.float32)
    rng = random.Random(7)
    for _ in range(90):
        cx, cy = rng.uniform(8, n - 8), rng.uniform(8, n - 8)
        ang = rng.uniform(0, math.pi)
        ln, wd, g = rng.uniform(7, 13), rng.uniform(1.6, 2.8), rng.uniform(0.55, 1.0)
        for i in range(-14, 15):
            for j in range(-14, 15):
                x = i * math.cos(ang) + j * math.sin(ang)
                y = -i * math.sin(ang) + j * math.cos(ang)
                if abs(x) < ln and abs(y) < wd * (1.0 - abs(x) / ln):
                    px, py = int(cx) + i, int(cy) + j
                    if 0 <= px < n and 0 <= py < n:
                        img[py, px] = (0.5 * g, 0.75 * g, 0.35 * g, 1.0)
    Image.fromarray((img * 255).astype(np.uint8), "RGBA").save(path)


def convert_school(school_dir, tex_dir, out_root):
    js, binc = load_glb(os.path.join(school_dir, "school.glb"))
    meta = json.load(open(os.path.join(school_dir, "school_meta.json")))
    sdir = ensure(os.path.join(out_root, "Assets", "Game", "School"))
    tdir = ensure(os.path.join(sdir, "Textures"))
    pdir = ensure(os.path.join(sdir, "Photos"))
    ldir = ensure(os.path.join(sdir, "Lightmaps"))

    # materials: the Hyper3D ones carry their own texture, the others a photo slot tinted to the paint colour
    mats = []
    used_slots = set()
    for m in js["materials"]:
        name = m.get("name", "plaster")
        pbr = m.get("pbrMetallicRoughness", {})
        col = pbr.get("baseColorFactor", [0.5, 0.5, 0.5, 1.0])
        tex = ""
        if "baseColorTexture" in pbr:
            img = js["textures"][pbr["baseColorTexture"]["index"]]["source"]
            data, mime = image_bytes(js, binc, img)
            ext = ".jpg" if "jpeg" in mime else ".png"
            tex = (js["images"][img].get("name") or name) + ext
            with open(os.path.join(tdir, tex), "wb") as f:
                f.write(data)
        info = MAP.get(name, ["", 1.0])
        if not tex and info[0]:
            used_slots.add(info[0])
        mats.append({"name": name, "color": [float(c) for c in col[:3]], "texture": tex,
                     "slot": info[0] if not tex else "", "tint": float(info[1]) if not tex else 0.0,
                     "two_sided": name in TWO_SIDED})

    photo_avg = {}
    for slot in sorted(used_slots):
        src = None
        for ext in ("jpg", "png"):
            p = os.path.join(tex_dir, slot, "diff." + ext)
            if os.path.exists(p):
                src = p
                break
        if src is None:
            print("  photo missing:", slot)
            continue
        dst = os.path.join(pdir, slot + os.path.splitext(src)[1])
        shutil.copyfile(src, dst)
        photo_avg[slot] = photo_average(src)
    make_leaves(os.path.join(pdir, "leaves.png"))
    for m in mats:
        m["photo"] = ""
        if m["slot"] and m["slot"] in photo_avg:
            m["photo"] = next(f for f in os.listdir(pdir) if os.path.splitext(f)[0] == m["slot"])
            m["avg"] = photo_avg[m["slot"]]
        else:
            m["avg"] = 0.5

    # lightmaps
    lms = meta.get("lightmaps", {})
    for node, e in lms.items():
        src = os.path.join(school_dir, e["file"])
        if os.path.exists(src):
            shutil.copyfile(src, os.path.join(ldir, node + ".png"))
        else:
            print("  lightmap missing:", src)

    # meshes, one per node (each glTF primitive becomes a sub-mesh)
    o = Out()
    o.i32(0x4843534D)
    o.i32(1)
    nodes = js["nodes"]
    o.i32(len(nodes))
    total_v = 0
    for n in nodes:
        mesh = js["meshes"][n["mesh"]]
        pos_l, nrm_l, uv0_l, uv1_l, subs = [], [], [], [], []
        base = 0
        for p in mesh["primitives"]:
            at = p["attributes"]
            pos = accessor(js, binc, at["POSITION"])
            nrm = accessor(js, binc, at["NORMAL"]) if "NORMAL" in at else np.zeros_like(pos)
            uv0 = accessor(js, binc, at["TEXCOORD_0"]) if "TEXCOORD_0" in at else np.zeros((len(pos), 2), np.float32)
            uv1 = accessor(js, binc, at["TEXCOORD_1"]) if "TEXCOORD_1" in at else uv0
            idx = accessor(js, binc, p["indices"]) if "indices" in p else np.arange(len(pos))
            pos_l.append(mirror_v3(pos))
            nrm_l.append(mirror_v3(nrm))
            uv0_l.append(flip_uv(uv0))
            uv1_l.append(flip_uv(uv1))
            subs.append((p.get("material", 0), flip_winding(idx) + base))
            base += len(pos)
        t = n.get("translation", [0.0, 0.0, 0.0])
        o.s(n.get("name", "node"))
        o.f32(t[0], t[1], -t[2])
        o.i32(base)
        o.arr(np.concatenate(pos_l), np.float32)
        o.arr(np.concatenate(nrm_l), np.float32)
        o.arr(np.concatenate(uv0_l), np.float32)
        o.arr(np.concatenate(uv1_l), np.float32)
        o.i32(len(subs))
        for mi, idx in subs:
            o.i32(mi)
            o.i32(len(idx))
            o.arr(idx, np.int32)
        total_v += base
    o.save(os.path.join(sdir, "school.bytes"))

    json.dump({"materials": mats, "lm_gain": float(meta.get("lm_scale", 4.0)) * 0.62,
               "lightmapped": sorted(lms.keys())},
              open(os.path.join(sdir, "materials.json"), "w"), indent=1)
    rdir = ensure(os.path.join(out_root, "Assets", "Resources"))
    shutil.copyfile(os.path.join(school_dir, "school_meta.json"), os.path.join(rdir, "school_meta.json"))
    print("school: %d objects, %d vertices, %d materials, %d photos, %d lightmaps"
          % (len(nodes), total_v, len(mats), len(photo_avg), len(lms)))


# ------------------------------------------------------------------------------------------------ Moulika
HEIGHT = 1.68
# which Rodin animation plays as which move: clip, from s, to s (0 = whole clip), loops (game/scripts/ragini.gd)
CLIPS = [
    ("idle", "human_000050", 0.0, 0.0, True),
    ("walk", "human_000089", 0.0, 0.0, True),
    ("run", "human_000049", 0.0, 0.0, True),
    ("attack", "human_000064", 0.35, 1.25, False),
    ("scream", "human_000041", 1.3, 3.2, False),
]
FPS = 30.0


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by,
                     aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw,
                     aw * bw - ax * bx - ay * by - az * bz])


def quat_rotate(q, v):
    qv = np.array([v[0], v[1], v[2], 0.0])
    qc = np.array([-q[0], -q[1], -q[2], q[3]])
    r = quat_mul(quat_mul(q, qv), qc)
    return r[:3]


def slerp(a, b, t):
    d = float(np.dot(a, b))
    if d < 0.0:
        b, d = -b, -d
    if d > 0.9995:
        r = a + (b - a) * t
        return r / np.linalg.norm(r)
    th = math.acos(min(1.0, d))
    s = math.sin(th)
    return (math.sin((1 - t) * th) * a + math.sin(t * th) * b) / s


def sample(times, values, t, is_rot):
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    k = int(np.searchsorted(times, t) - 1)
    k = max(0, min(k, len(times) - 2))
    t0, t1 = times[k], times[k + 1]
    f = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
    if is_rot:
        return slerp(values[k], values[k + 1], f)
    return values[k] + (values[k + 1] - values[k]) * f


def convert_moulika(glb_path, out_root):
    js, binc = load_glb(glb_path)
    mdir = ensure(os.path.join(out_root, "Assets", "Game", "Moulika"))
    nodes = js["nodes"]
    skin = js["skins"][0]
    joints = skin["joints"]
    jindex = {nid: k for k, nid in enumerate(joints)}
    parent_of = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent_of[c] = i

    # the skinned mesh (any mesh without JOINTS_0 is a helper object and is left out)
    mesh_node = next(i for i, n in enumerate(nodes) if "mesh" in n and "skin" in n)
    prims = [p for p in js["meshes"][nodes[mesh_node]["mesh"]]["primitives"] if "JOINTS_0" in p["attributes"]]
    pos_l, nrm_l, uv_l, bi_l, bw_l, idx_l = [], [], [], [], [], []
    base = 0
    material = None
    for p in prims:
        at = p["attributes"]
        pos = accessor(js, binc, at["POSITION"])
        nrm = accessor(js, binc, at["NORMAL"])
        uv = accessor(js, binc, at["TEXCOORD_0"])
        sets = []
        k = 0
        while "JOINTS_%d" % k in at:
            sets.append((accessor(js, binc, at["JOINTS_%d" % k]).astype(np.int64), accessor(js, binc, at["WEIGHTS_%d" % k]).astype(np.float64)))
            k += 1
        J = np.concatenate([s[0] for s in sets], axis=1)
        W = np.concatenate([s[1] for s in sets], axis=1)
        # keep the four strongest influences per vertex, renormalised
        order = np.argsort(-W, axis=1)[:, :4]
        J4 = np.take_along_axis(J, order, axis=1)
        W4 = np.take_along_axis(W, order, axis=1)
        s = W4.sum(axis=1, keepdims=True)
        s[s <= 0] = 1.0
        W4 = W4 / s
        idx = accessor(js, binc, p["indices"])
        pos_l.append(mirror_v3(pos))
        nrm_l.append(mirror_v3(nrm))
        uv_l.append(flip_uv(uv))
        bi_l.append(J4)
        bw_l.append(W4)
        idx_l.append(flip_winding(idx) + base)
        base += len(pos)
        material = p.get("material", material)
    POS = np.concatenate(pos_l)
    # bind-pose size: scale her to HEIGHT, feet on the floor
    ymin, ymax = float(POS[:, 1].min()), float(POS[:, 1].max())
    scale = HEIGHT / max(ymax - ymin, 0.01)
    y_off = -ymin * scale

    # textures
    tex = {}
    if material is not None:
        m = js["materials"][material]
        pbr = m.get("pbrMetallicRoughness", {})
        for key, ref in (("albedo", pbr.get("baseColorTexture")), ("normal", m.get("normalTexture")), ("mr", pbr.get("metallicRoughnessTexture"))):
            if ref is None:
                continue
            img = js["textures"][ref["index"]]["source"]
            data, mime = image_bytes(js, binc, img)
            fn = "moulika_%s%s" % (key, ".jpg" if "jpeg" in mime else ".png")
            with open(os.path.join(mdir, fn), "wb") as f:
                f.write(data)
            tex[key] = fn

    # skeleton: rest pose (local, Unity space) and bind poses
    ibm = accessor(js, binc, skin["inverseBindMatrices"]).reshape(-1, 4, 4)  # column-major in the file
    S = np.diag([1.0, 1.0, -1.0, 1.0])
    rest = []
    for k, nid in enumerate(joints):
        n = nodes[nid]
        par = parent_of.get(nid)
        pk = jindex.get(par, -1) if par is not None else -1
        t = np.array(n.get("translation", [0, 0, 0]), dtype=np.float64)
        r = np.array(n.get("rotation", [0, 0, 0, 1]), dtype=np.float64)
        sc = np.array(n.get("scale", [1, 1, 1]), dtype=np.float64)
        M = ibm[k].T  # row-major
        Mu = S @ M @ S
        rest.append((n.get("name", "bone%d" % k), pk, mirror_v3(t), mirror_q(r), sc, Mu))
    # anything between the skeleton's top bone and the scene root (the "Armature" node) must be identity
    hips_k = next(k for k, b in enumerate(rest) if b[1] < 0)
    top = parent_of.get(joints[hips_k])
    while top is not None:
        tn = nodes[top]
        if any(k in tn for k in ("translation", "rotation", "scale", "matrix")):
            print("  warning: skeleton parent %s has a transform" % tn.get("name"))
        top = parent_of.get(top)

    # animations
    anims = {a["name"]: a for a in js.get("animations", [])}
    clips_out = []
    for move, src, t0, t1, loop in CLIPS:
        a = anims.get(src)
        if a is None:
            print("  animation missing:", src)
            continue
        tracks = {}
        length = 0.0
        for ch in a["channels"]:
            nid = ch["target"].get("node")
            path = ch["target"]["path"]
            if nid not in jindex or path not in ("translation", "rotation"):
                continue
            smp = a["samplers"][ch["sampler"]]
            times = accessor(js, binc, smp["input"]).astype(np.float64)
            vals = accessor(js, binc, smp["output"]).astype(np.float64)
            tracks[(jindex[nid], path)] = (times, vals)
            length = max(length, float(times[-1]))
        a0, a1 = (t0, t1) if t1 > t0 else (0.0, length)
        frames = int(round((a1 - a0) * FPS)) + 1
        ts = [a0 + min(f / FPS, a1 - a0) for f in range(frames)]
        P = np.zeros((len(joints), frames, 3), np.float64)
        R = np.zeros((len(joints), frames, 4), np.float64)
        for k in range(len(joints)):
            tr = tracks.get((k, "translation"))
            ro = tracks.get((k, "rotation"))
            for f, t in enumerate(ts):
                P[k, f] = sample(tr[0], tr[1], t, False) if tr else rest[k][2] * np.array([1, 1, -1])
                if ro:
                    q = sample(ro[0], ro[1], t, True)
                    if f > 0 and np.dot(q, R[k, f - 1]) < 0:
                        q = -q  # keep neighbouring keys on the same side, so Unity interpolates the short way
                    R[k, f] = q
                else:
                    R[k, f] = rest[k][3] * np.array([-1, -1, 1, 1])
        # walk it in place (the game moves her): take the forward travel out of the hips track
        travel = P[hips_k, -1] - P[hips_k, 0]
        travel[1] = 0.0
        dist = float(np.linalg.norm(travel))
        nat = 0.0
        if dist > 0.05:
            for f in range(frames):
                P[hips_k, f] -= travel * (f / (frames - 1))
            nat = dist / max(a1 - a0, 1e-3) * scale
        clips_out.append((move, a1 - a0, loop, nat, frames, mirror_v3(P), mirror_q(R)))
        print("  move %-6s from %s %.2f-%.2f s, %d frames, travels %.2f m/s" % (move, src, a0, a1, frames, nat))

    o = Out()
    o.i32(0x4C554F4D)
    o.i32(1)
    o.i32(len(POS))
    o.arr(POS, np.float32)
    o.arr(np.concatenate(nrm_l), np.float32)
    o.arr(np.concatenate(uv_l), np.float32)
    o.arr(np.concatenate(bi_l), np.int32)
    o.arr(np.concatenate(bw_l), np.float32)
    IDX = np.concatenate(idx_l)
    o.i32(len(IDX))
    o.arr(IDX, np.int32)
    o.i32(len(rest))
    for name, pk, t, r, sc, Mu in rest:
        o.s(name)
        o.i32(pk)
        o.f32(*t)
        o.f32(*r)
        o.f32(*sc)
        o.arr(Mu.reshape(-1), np.float32)  # row-major 4x4
    o.f32(scale, y_off)
    o.i32(len(clips_out))
    for move, length, loop, nat, frames, P, R in clips_out:
        o.s(move)
        o.f32(length)
        o.i32(1 if loop else 0)
        o.f32(nat)
        o.i32(frames)
        o.f32(FPS)
        o.arr(P, np.float32)  # [bone][frame][3]
        o.arr(R, np.float32)  # [bone][frame][4]
    o.save(os.path.join(mdir, "moulika.bytes"))
    json.dump({"textures": tex, "scale": scale, "y_offset": y_off, "bones": len(rest)},
              open(os.path.join(mdir, "moulika.json"), "w"), indent=1)
    print("moulika: %d vertices, %d triangles, %d bones, scale %.3f, %d moves" % (len(POS), len(IDX) // 3, len(rest), scale, len(clips_out)))


# ------------------------------------------------------------------------------------------------ the night sky
def read_hdr(path):
    """Radiance .hdr (32-bit_rle_rgbe) -> float32 array [h, w, 3]."""
    data = open(path, "rb").read()
    pos = 0
    while True:
        end = data.index(b"\n", pos)
        line = data[pos:end].decode("ascii", "replace")
        pos = end + 1
        if line.startswith("-Y") or line.startswith("+Y"):
            parts = line.split()
            h, w = int(parts[1]), int(parts[3])
            break
    img = np.zeros((h, w, 4), np.uint8)
    for y in range(h):
        if data[pos] == 2 and data[pos + 1] == 2 and (data[pos + 2] << 8 | data[pos + 3]) == w:
            pos += 4
            for c in range(4):
                x = 0
                while x < w:
                    n = data[pos]
                    pos += 1
                    if n > 128:
                        n -= 128
                        img[y, x:x + n, c] = data[pos]
                        pos += 1
                    else:
                        img[y, x:x + n, c] = np.frombuffer(data, np.uint8, n, pos)
                        pos += n
                    x += n
        else:  # flat scanline
            img[y] = np.frombuffer(data, np.uint8, w * 4, pos).reshape(w, 4)
            pos += w * 4
    e = img[..., 3].astype(np.int32)
    scale = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0)
    return img[..., :3].astype(np.float32) * scale[..., None]


def filmic(c):
    A, B, C, D, E, F, W = 0.22 * 4.0, 0.30 * 2.0, 0.10, 0.20, 0.01, 0.30, 1.0
    t = ((c * (A * c + C * B) + D * E) / (c * (A * c + B) + D * F)) - E / F
    w = ((W * (A * W + C * B) + D * E) / (W * (A * W + B) + D * F)) - E / F
    return t / w


def convert_sky(hdr_path, out_root):
    """The Godot sky (night.hdr panorama at energy 0.5, filmic tone curve) as an ordinary picture for Unity's
    panoramic skybox. Flipped left to right like everything else (the Z mirror)."""
    if not hdr_path or not os.path.exists(hdr_path) or Image is None:
        print("sky: none")
        return
    rgb = read_hdr(hdr_path) * 0.5
    out = filmic(np.maximum(rgb, 0.0))
    srgb = np.where(out <= 0.0031308, out * 12.92, 1.055 * np.power(np.clip(out, 0, None), 1 / 2.4) - 0.055)
    srgb = np.clip(srgb, 0.0, 1.0)[:, ::-1]
    d = ensure(os.path.join(out_root, "Assets", "Game", "Sky"))
    Image.fromarray((srgb * 255.0 + 0.5).astype(np.uint8), "RGB").save(os.path.join(d, "night_sky.png"))
    print("sky: %dx%d" % (srgb.shape[1], srgb.shape[0]))


# ------------------------------------------------------------------------------------------------ the rest
def copy_dir(src, dst, exts):
    ensure(dst)
    n = 0
    for f in sorted(os.listdir(src)) if os.path.isdir(src) else []:
        if os.path.splitext(f)[1].lower() in exts:
            shutil.copyfile(os.path.join(src, f), os.path.join(dst, f))
            n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--school", required=True)
    ap.add_argument("--moulika", required=True)
    ap.add_argument("--tex", required=True)
    ap.add_argument("--sounds", required=True)
    ap.add_argument("--fonts", nargs="+", required=True)
    ap.add_argument("--ui", required=True)
    ap.add_argument("--icons", default="")
    ap.add_argument("--sky", default="")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    convert_school(a.school, a.tex, a.out)
    convert_moulika(a.moulika, a.out)
    convert_sky(a.sky, a.out)
    res = os.path.join(a.out, "Assets", "Resources")
    n = copy_dir(a.sounds, os.path.join(res, "Sounds"), {".ogg", ".wav"})
    for extra in ("CREDITS_SOUNDS.md",):
        if os.path.exists(os.path.join(a.sounds, extra)):
            shutil.copyfile(os.path.join(a.sounds, extra), os.path.join(a.out, "Assets", "Game", extra))
    print("sounds:", n)
    nf = 0
    for d in a.fonts:
        nf += copy_dir(d, os.path.join(res, "Fonts"), {".ttf", ".otf"})
    print("fonts:", nf)
    print("ui images:", copy_dir(a.ui, os.path.join(res, "UI"), {".png"}))
    if a.icons:
        print("icons:", copy_dir(a.icons, os.path.join(a.out, "Assets", "Game", "Icons"), {".png"}))


if __name__ == "__main__":
    sys.exit(main())
