"""Minimal glTF-binary (.glb) reader, numpy only, so it runs both in plain Python and inside Blender.

read(path) -> dict with
  V   (n, 3) float  vertex positions in Blender's Z-up frame (glTF is Y-up: (x, y, z) -> (x, -z, y)),
                    with every node transform applied
  F   (m, 3) int    triangles
  UV  (n, 2) float  first UV set in Blender's convention (v up: v_blender = 1 - v_gltf)
  image (bytes or None), mime: the base-colour texture of the first textured material
"""
import json
import struct

import numpy as np

_CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT2": 4, "MAT3": 9, "MAT4": 16}
_NORM = {np.int8: 127.0, np.uint8: 255.0, np.int16: 32767.0, np.uint16: 65535.0}


def _quat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _local(node):
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T          # glTF stores column-major
    M = np.eye(4)
    S = np.diag(list(node.get("scale", [1, 1, 1])) + [1])
    R = np.eye(4)
    R[:3, :3] = _quat(node.get("rotation", [0, 0, 0, 1]))
    T = np.eye(4)
    T[:3, 3] = node.get("translation", [0, 0, 0])
    return T @ R @ S @ M


def read(path):
    data = open(path, "rb").read()
    magic, _ver, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF":
        raise ValueError("not a glb file: " + path)
    off, js, binc = 12, None, b""
    while off < length:
        clen, ctype = struct.unpack_from("<II", data, off)
        off += 8
        chunk = data[off:off + clen]
        off += clen
        if ctype == 0x4E4F534A:
            js = json.loads(chunk.decode("utf-8"))
        elif ctype == 0x004E4942:
            binc = chunk

    def view(i):
        bv = js["bufferViews"][i]
        s = bv.get("byteOffset", 0)
        return binc[s:s + bv["byteLength"]], bv.get("byteStride", 0)

    def acc(i):
        a = js["accessors"][i]
        dt = _CT[a["componentType"]]
        n = _NC[a["type"]]
        cnt = a["count"]
        buf, stride = view(a["bufferView"])
        item = np.dtype(dt).itemsize
        start = a.get("byteOffset", 0)
        if stride and stride != item * n:
            arr = np.ndarray((cnt, n), dt, buf, start, (stride, item))
        else:
            arr = np.frombuffer(buf, dt, cnt * n, start).reshape(cnt, n)
        arr = arr.astype(np.float64) if dt == np.float32 else arr.astype(np.int64)
        if a.get("normalized") and dt in _NORM:
            arr = arr / _NORM[dt]
        return arr

    Vs, Fs, UVs, mats = [], [], [], []
    base = 0

    def visit(ni, parent):
        nonlocal base
        node = js["nodes"][ni]
        W = parent @ _local(node)
        if "mesh" in node:
            for prim in js["meshes"][node["mesh"]]["primitives"]:
                if prim.get("mode", 4) != 4:
                    continue
                P = acc(prim["attributes"]["POSITION"])
                P = (np.c_[P, np.ones(len(P))] @ W.T)[:, :3]
                uv = acc(prim["attributes"]["TEXCOORD_0"]) if "TEXCOORD_0" in prim["attributes"] else np.zeros((len(P), 2))
                idx = acc(prim["indices"]).ravel() if "indices" in prim else np.arange(len(P))
                Vs.append(P)
                UVs.append(uv)
                Fs.append(idx.reshape(-1, 3) + base)
                mats.append(prim.get("material"))
                base += len(P)
        for c in node.get("children", []):
            visit(c, W)

    scene = js.get("scenes", [{"nodes": list(range(len(js.get("nodes", []))))}])[js.get("scene", 0)]
    for ni in scene["nodes"]:
        visit(ni, np.eye(4))
    if not Vs:
        raise ValueError("no triangles in " + path)
    V = np.vstack(Vs)
    V = np.c_[V[:, 0], -V[:, 2], V[:, 1]]                  # Y-up -> Z-up
    UV = np.vstack(UVs)
    UV = np.c_[UV[:, 0], 1.0 - UV[:, 1]]
    image, mime = None, None
    for mi in mats:
        if mi is None:
            continue
        pbr = js["materials"][mi].get("pbrMetallicRoughness", {})
        t = pbr.get("baseColorTexture")
        if t is None:
            continue
        src = js["textures"][t["index"]].get("source")
        if src is None:
            continue
        im = js["images"][src]
        if "bufferView" in im:
            image, _ = view(im["bufferView"])
            image = bytes(image)
            mime = im.get("mimeType", "image/png")
            break
    return {"V": V, "F": np.vstack(Fs).astype(np.int64), "UV": UV, "image": image, "mime": mime,
            "materials": len([m for m in set(mats) if m is not None])}
