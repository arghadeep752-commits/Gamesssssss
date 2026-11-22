#!/usr/bin/env python3
"""Turns the Hyper3D Rodin models into glTF files the Godot game imports directly.

    convert_models.py --rodin DIR --models tools/rodin/models.json --out godot/gen/models [--preview DIR]

  <out>/chars/<name>.glb      character, auto-rigged (tools/rig/autorig.py), with its animations
  <out>/vehicles/<name>.glb   body in metres: wheels on the ground at y = 0, front towards -Z (Godot's forward)
  <out>/weapons/<name>.glb    grip at the origin, barrel / blade towards -Z
  <out>/props/<name>.glb      street props and shop-houses: standing on y = 0, centred, front towards -Z
  <out>/models.json           sizes, wheels, seats, exits, lights, muzzles, clip lengths ... in Godot coordinates

The fitting code (wheels, seats, grips ...) is shared with the Unity converter and works in Unity's left-handed
frame; the results are mirrored on z here (front +Z -> -Z) and written as right-handed glTF.
"""
import argparse
import io
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rig"))
sys.path.insert(0, os.path.join(HERE, "..", "unity"))
import autorig  # noqa: E402
import convert_models as UC  # noqa: E402  (the Unity converter: vehicle / weapon / prop fitting)

TEX_MAX = {"character": 1024, "vehicle": 1024, "weapon": 512, "wheel": 512, "prop": 1024, "building": 1024}
LOOP = {"idle", "walk", "run", "sprint", "fall", "aim_pistol", "aim_rifle", "drive", "ride", "swim", "cower"}


def zmirror(v):
    v = np.array(v, np.float64, copy=True)
    v[..., 2] *= -1
    return v


def zm3(p):
    return [round(float(p[0]), 4), round(float(p[1]), 4), round(-float(p[2]), 4)]


# ------------------------------------------------------------------------------------------------ glTF writer
class GLB:
    def __init__(self):
        self.js = {"asset": {"version": "2.0", "generator": "danga tools/godot"}, "scene": 0, "scenes": [{"nodes": []}],
                   "nodes": [], "meshes": [], "accessors": [], "bufferViews": [], "buffers": [{"byteLength": 0}]}
        self.bin = bytearray()

    def _view(self, data, target=None):
        while len(self.bin) % 4:
            self.bin.append(0)
        v = {"buffer": 0, "byteOffset": len(self.bin), "byteLength": len(data)}
        if target:
            v["target"] = target
        self.bin += data
        self.js["bufferViews"].append(v)
        return len(self.js["bufferViews"]) - 1

    def accessor(self, arr, typ, ctype, target=None, minmax=False, normalized=False):
        arr = np.ascontiguousarray(arr)
        view = self._view(arr.tobytes(), target)
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[typ]
        a = {"bufferView": view, "componentType": ctype, "count": int(arr.size // n), "type": typ}
        if normalized:
            a["normalized"] = True
        if minmax:
            r = arr.reshape(-1, n)
            a["min"] = [float(x) for x in r.min(0)]
            a["max"] = [float(x) for x in r.max(0)]
        self.js["accessors"].append(a)
        return len(self.js["accessors"]) - 1

    def image(self, data, mime):
        self.js.setdefault("images", []).append({"bufferView": self._view(data), "mimeType": mime})
        self.js.setdefault("samplers", [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}])
        self.js.setdefault("textures", []).append({"sampler": 0, "source": len(self.js["images"]) - 1})
        return len(self.js["textures"]) - 1

    def material(self, name, tex, kind):
        m = {"name": name, "pbrMetallicRoughness": {"metallicFactor": 0.0, "roughnessFactor": 0.85}}
        if "albedo" in tex:
            m["pbrMetallicRoughness"]["baseColorTexture"] = {"index": self.image(*tex["albedo"])}
        if "mr" in tex:
            m["pbrMetallicRoughness"]["metallicRoughnessTexture"] = {"index": self.image(*tex["mr"])}
            m["pbrMetallicRoughness"]["metallicFactor"] = 1.0
            m["pbrMetallicRoughness"]["roughnessFactor"] = 1.0
        if "normal" in tex:
            m["normalTexture"] = {"index": self.image(*tex["normal"])}
        self.js.setdefault("materials", []).append(m)
        return len(self.js["materials"]) - 1

    def mesh(self, name, P, N, UV, I, mat, joints=None, weights=None):
        attrs = {"POSITION": self.accessor(P.astype("<f4"), "VEC3", 5126, 34962, minmax=True),
                 "NORMAL": self.accessor(N.astype("<f4"), "VEC3", 5126, 34962),
                 "TEXCOORD_0": self.accessor(UV.astype("<f4"), "VEC2", 5126, 34962)}
        if joints is not None:
            attrs["JOINTS_0"] = self.accessor(joints.astype("<u2"), "VEC4", 5123, 34962)
            attrs["WEIGHTS_0"] = self.accessor(weights.astype("<f4"), "VEC4", 5126, 34962)
        prim = {"attributes": attrs, "indices": self.accessor(I.reshape(-1).astype("<u4"), "SCALAR", 5125, 34963), "material": mat}
        self.js["meshes"].append({"name": name, "primitives": [prim]})
        return len(self.js["meshes"]) - 1

    def node(self, d, root=False):
        self.js["nodes"].append(d)
        i = len(self.js["nodes"]) - 1
        if root:
            self.js["scenes"][0]["nodes"].append(i)
        return i

    def save(self, path):
        while len(self.bin) % 4:
            self.bin.append(0)
        self.js["buffers"][0]["byteLength"] = len(self.bin)
        j = json.dumps(self.js, separators=(",", ":")).encode()
        j += b" " * ((4 - len(j) % 4) % 4)
        with open(path, "wb") as f:
            f.write(struct.pack("<4sII", b"glTF", 2, 12 + 8 + len(j) + 8 + len(self.bin)))
            f.write(struct.pack("<I4s", len(j), b"JSON") + j)
            f.write(struct.pack("<I4s", len(self.bin), b"BIN\0") + bytes(self.bin))


def textures(tex, kind):
    """Model textures, resized for phones: albedo and metal/rough as JPEG, normal map as PNG."""
    from PIL import Image
    out = {}
    m = TEX_MAX[kind]
    for key, (data, mime) in tex.items():
        im = Image.open(io.BytesIO(data))
        if max(im.size) > m:
            im = im.resize((m, m), Image.LANCZOS)
        buf = io.BytesIO()
        if key == "albedo" and im.mode in ("RGBA", "LA") and np.asarray(im.convert("RGBA"))[..., 3].min() < 250:
            im.convert("RGBA").save(buf, "PNG")
            out[key] = (buf.getvalue(), "image/png")
        elif key == "normal":
            im.convert("RGB").save(buf, "PNG")
            out[key] = (buf.getvalue(), "image/png")
        else:
            im.convert("RGB").save(buf, "JPEG", quality=90)
            out[key] = (buf.getvalue(), "image/jpeg")
    return out


def to_gltf(P, N, UV, I):
    """Unity frame (left-handed, front +Z, v flipped) -> glTF / Godot frame (right-handed, front -Z)."""
    return zmirror(P), zmirror(N), np.c_[UV[:, 0], 1.0 - UV[:, 1]], np.asarray(I).reshape(-1, 3)[:, [0, 2, 1]]


def static_glb(path, name, P, N, UV, I, tex, kind):
    P, N, UV, I = to_gltf(P, N, UV, I)
    g = GLB()
    mat = g.material(name, textures(tex, kind), kind)
    mi = g.mesh(name, P, N, UV, I, mat)
    g.node({"name": name, "mesh": mi}, root=True)
    g.save(path)


def character_glb(path, name, r):
    """Skinned character: one joint node per bone (rest rotations are identity), its clips as glTF animations."""
    P, N, UV, I = to_gltf(r["P"], r["N"], r["UV"], r["I"])
    g = GLB()
    mat = g.material(name, textures(r["tex"], "character"), "character")
    bones = autorig.BONES
    J = {k: zmirror(v) for k, v in r["J"].items()}
    names = [b.replace(".", "_") for b in bones]
    first = len(g.js["nodes"])
    for bi, b in enumerate(bones):
        par = autorig.PARENT[b]
        local = J[b] - (J[par] if par else np.zeros(3))
        g.node({"name": names[bi], "translation": [float(x) for x in local]})
    for bi, b in enumerate(bones):
        kids = [first + k for k, c in enumerate(bones) if autorig.PARENT[c] == b]
        if kids:
            g.js["nodes"][first + bi]["children"] = kids
    ibm = np.zeros((len(bones), 16), np.float32)
    for bi, b in enumerate(bones):
        m = np.eye(4, dtype=np.float32)
        m[:3, 3] = -J[b]
        ibm[bi] = m.T.reshape(-1)                       # column-major
    skin = {"joints": [first + k for k in range(len(bones))], "skeleton": first,
            "inverseBindMatrices": g.accessor(ibm, "MAT4", 5126)}
    g.js["skins"] = [skin]
    bw = np.asarray(r["bw"], np.float32)
    bw = bw / np.maximum(bw.sum(1, keepdims=True), 1e-6)
    mi = g.mesh(name, P, N, UV, I, mat, joints=np.asarray(r["bi"], np.uint16), weights=bw)
    mesh_node = g.node({"name": name + "_mesh", "mesh": mi, "skin": 0})
    g.node({"name": name, "children": [first, mesh_node]}, root=True)
    anims = []
    info = {}
    for cname, T, loop, nat, frames, Pc, Rc in r["clips"]:
        times = (np.arange(frames, dtype=np.float32) / autorig.FPS).clip(0, T)
        tin = g.accessor(times, "SCALAR", 5126, minmax=True)
        samplers, channels = [], []
        for bi, b in enumerate(bones):
            q = np.asarray(Rc[bi], np.float32).copy()
            q[:, 0] *= -1                                 # mirror z: (x, y, z, w) -> (-x, -y, z, w)
            q[:, 1] *= -1
            samplers.append({"input": tin, "output": g.accessor(q, "VEC4", 5126), "interpolation": "LINEAR"})
            channels.append({"sampler": len(samplers) - 1, "target": {"node": first + bi, "path": "rotation"}})
            if b == "Hips":
                t = zmirror(Pc[bi]).astype(np.float32)
                samplers.append({"input": tin, "output": g.accessor(t, "VEC3", 5126), "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1, "target": {"node": first + bi, "path": "translation"}})
        anims.append({"name": cname, "samplers": samplers, "channels": channels})
        info[cname] = {"length": round(float(T), 3), "loop": bool(loop) or cname in LOOP, "speed": float(nat)}
    g.js["animations"] = anims
    g.save(path)
    pts = {"hand_r": zm3(r["J"]["Hand.R"]), "hand_tip_r": zm3(r["J"]["HandTip.R"]), "hand_l": zm3(r["J"]["Hand.L"]),
           "head_top": zm3(r["J"]["HeadTop"])}
    return info, pts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rodin", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    man = json.load(open(a.models))["models"]
    files = {f.split("__")[0]: os.path.join(a.rodin, f) for f in os.listdir(a.rodin) if f.endswith(".glb") and "__" in f}
    meta = {"characters": {}, "vehicles": {}, "weapons": {}, "props": {}, "wheel": None, "frame": "godot"}
    for d in ("chars", "vehicles", "weapons", "props"):
        os.makedirs(os.path.join(a.out, d), exist_ok=True)
    for name, spec in man.items():
        if a.only and name not in a.only.split(","):
            continue
        path = files.get(name)
        if not path:
            print("MISSING model file:", name)
            continue
        kind = spec["kind"]
        try:
            if kind == "character":
                r = autorig.rig(path, spec.get("height", 1.72), spec.get("skirt", False), spec.get("sex") == "f")
                clips, pts = character_glb(os.path.join(a.out, "chars", name + ".glb"), name, r)
                meta["characters"][name] = {"role": spec.get("role"), "outfit": spec.get("outfit"), "height": spec.get("height"),
                                            "female": spec.get("sex") == "f", "arms": r["info"].get("arms", True), "clips": clips, "points": pts}
                print("character %-14s %d vertices, %d clips" % (name, len(r["P"]), len(clips)))
                continue
            P, N, UV, I, tex = UC.load(path)
            if kind == "vehicle":
                P, info = UC.vehicle(name, spec, P, N, UV, I)
                for w in info["wheels"]:
                    w["z"] = -w["z"]
                for k in ("seat", "exit", "rotor", "tail_rotor", "motor"):
                    if k in info:
                        info[k] = zm3(info[k]) + info[k][3:]
                info["lights"] = [zm3(l) for l in info["lights"]]
                static_glb(os.path.join(a.out, "vehicles", name + ".glb"), name, P, N, UV, I, tex, kind)
                meta["vehicles"][name] = info
                print("vehicle   %-14s %.2f x %.2f x %.2f m, %d wheels" % (name, info["width"], info["height"], info["length"], len(info["wheels"])))
            elif kind == "wheel":
                P, N, info = UC.wheel_mesh(P, N, UV, I)
                static_glb(os.path.join(a.out, "vehicles", "wheel.glb"), "wheel", P, N, UV, I, tex, kind)
                meta["wheel"] = info
                print("wheel     width ratio %.3f" % info["width"])
            elif kind in ("prop", "building"):
                P, N, info = UC.prop(name, spec, P, N)
                static_glb(os.path.join(a.out, "props", name + ".glb"), name, P, N, UV, I, tex, kind)
                meta["props"][name] = info
                print("%-9s %-14s %.1f x %.1f x %.1f m" % (kind, name, *info["size"]))
            elif kind == "weapon":
                P, N, info = UC.weapon(name, spec, P, N, UV, I)
                info["muzzle"] = zm3(info["muzzle"])
                static_glb(os.path.join(a.out, "weapons", name + ".glb"), name, P, N, UV, I, tex, kind)
                meta["weapons"][name] = info
                print("weapon    %-14s muzzle %s" % (name, info["muzzle"]))
        except Exception as e:      # noqa: BLE001
            import traceback
            traceback.print_exc()
            print("FAILED", name, e)
    with open(os.path.join(a.out, "models.json"), "w") as f:
        json.dump(meta, f, indent=1)


if __name__ == "__main__":
    main()
