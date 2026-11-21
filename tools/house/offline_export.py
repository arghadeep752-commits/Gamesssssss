"""A Blender-free stand-in for build_house.py, for checking the pipeline on a machine without Blender: the same
architecture, code-built furniture (no Hyper3D models, no baked light), written as house.glb + house_meta.json +
flat grey lightmaps.   python3 offline_export.py OUT_DIR"""
import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "common"))
import architecture  # noqa: E402
import house_meta  # noqa: E402
import layout as LY  # noqa: E402
import navigation  # noqa: E402
import props  # noqa: E402
from geo import Geo, rot_z  # noqa: E402

BASE = {}


def tri_arrays(g, origin):
    """Flat-shaded triangle soup per material: {mat: (pos, nrm, uv)} in glTF space."""
    V = np.asarray(g.V, float) - np.asarray(origin, float)
    out = {}
    for f, uv, m in zip(g.F, g.UV, g.M):
        P = V[f]
        n = np.cross(P[1] - P[0], P[2] - P[0])
        if len(f) > 3:
            n = n + np.cross(P[2] - P[0], P[3] - P[0])
        ln = np.linalg.norm(n)
        n = n / ln if ln > 1e-12 else np.array([0, 0, 1.0])
        for k in range(1, len(f) - 1):
            for idx in (0, k, k + 1):
                p = P[idx]
                d = out.setdefault(m, ([], [], []))
                d[0].append((p[0], p[2], -p[1]))
                d[1].append((n[0], n[2], -n[1]))
                d[2].append((uv[idx][0], 1.0 - uv[idx][1]))
    return out


def write_glb(path, objects):
    """objects: [(name, Geo, origin)]"""
    buf = bytearray()
    views, accs, meshes, nodes, mats = [], [], [], [], []
    mat_idx = {}

    def add(arr, target, comp, typ):
        data = np.ascontiguousarray(arr).tobytes()
        while len(buf) % 4:
            buf.append(0)
        off = len(buf)
        buf.extend(data)
        views.append({"buffer": 0, "byteOffset": off, "byteLength": len(data), **({"target": target} if target else {})})
        a = {"bufferView": len(views) - 1, "componentType": comp, "count": len(arr), "type": typ}
        if typ == "VEC3" and comp == 5126:
            a["min"] = np.asarray(arr).min(0).tolist()
            a["max"] = np.asarray(arr).max(0).tolist()
        accs.append(a)
        return len(accs) - 1

    for name, g, origin in objects:
        prims = []
        for m, (P, N, UV) in tri_arrays(g, origin).items():
            if m not in mat_idx:
                mat_idx[m] = len(mats)
                c = BASE.get(m, (0.5, 0.5, 0.5))
                mats.append({"name": m, "pbrMetallicRoughness": {"baseColorFactor": [c[0], c[1], c[2], 1.0]}})
            P = np.array(P, np.float32)
            n = len(P)
            prims.append({"attributes": {"POSITION": add(P, 34962, 5126, "VEC3"), "NORMAL": add(np.array(N, np.float32), 34962, 5126, "VEC3"),
                                         "TEXCOORD_0": add(np.array(UV, np.float32), 34962, 5126, "VEC2"),
                                         "TEXCOORD_1": add(np.array(UV, np.float32), 34962, 5126, "VEC2")},
                          "indices": add(np.arange(n, dtype=np.uint32), 34963, 5125, "SCALAR"), "material": mat_idx[m]})
        if not prims:
            continue
        meshes.append({"name": name, "primitives": prims})
        o = origin
        nodes.append({"name": name, "mesh": len(meshes) - 1, "translation": [o[0], o[2], -o[1]]})
    js = {"asset": {"version": "2.0", "generator": "offline_export"}, "scene": 0, "scenes": [{"nodes": list(range(len(nodes)))}],
          "nodes": nodes, "meshes": meshes, "materials": mats, "accessors": accs, "bufferViews": views,
          "buffers": [{"byteLength": len(buf)}]}
    jb = json.dumps(js).encode()
    while len(jb) % 4:
        jb += b" "
    while len(buf) % 4:
        buf.append(0)
    total = 12 + 8 + len(jb) + 8 + len(buf)
    with open(path, "wb") as f:
        f.write(struct.pack("<4sII", b"glTF", 2, total))
        f.write(struct.pack("<II", len(jb), 0x4E4F534A))
        f.write(jb)
        f.write(struct.pack("<II", len(buf), 0x004E4942))
        f.write(bytes(buf))


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "build/house_offline")
    os.makedirs(os.path.join(out, "lightmaps"), exist_ok=True)
    L = LY.build()
    chunks, dyn, coll, extra = architecture.build(L)
    objects = [(k, g, (0, 0, 0)) for k, g in chunks.items()]
    furn = {}
    dyn_meta = []
    heights = {}
    for f in L["furniture"]:
        g, parts = props.BUILDERS[f["kind"]]()
        R = rot_z(f["yaw"])
        base = np.array([f["x"], f["y"], f["z"]])
        furn.setdefault(f["room"], Geo("furn_" + f["room"])).merge(g, R=R, T=base)
        if len(g.V):
            heights[f["kind"]] = float(np.asarray(g.V)[:, 2].max())
        for pname, (pg, off) in parts.items():
            pivot = base + R @ np.asarray(off, float)
            w = Geo(pname)
            w.merge(pg, R=R, T=pivot)
            objects.append((pname, w, tuple(pivot)))
            dyn_meta.append({"name": pname, "kind": f["kind"], "part": pname, "pivot": navigation.U(*pivot), "yaw": f["yaw"], "room": f["room"]})
    for rk, g in furn.items():
        objects.append(("furn_" + rk, g, (0, 0, 0)))
    for name, d in dyn.items():
        g = d.get("geo") or props.item_geo("padlock")
        w = Geo(name)
        w.merge(g, T=d["pivot"])
        objects.append((name, w, tuple(d["pivot"])))
        m = {k: v for k, v in d.items() if k != "geo"}
        m["name"] = name
        m["pivot"] = navigation.U(*d["pivot"])
        if "leaf_dir" in m:
            m["leaf_dir"] = [m["leaf_dir"][0], 0.0, m["leaf_dir"][1]]
        if "into" in m:
            m["into"] = [m["into"][0], 0.0, m["into"][1]]
        dyn_meta.append(m)
    for name in ("garage_key", "gold_key", "silver_key", "drawer_key", "hammer", "fuse"):
        objects.append(("item_" + name, props.item_geo(name), (0, 0, 0)))
    write_glb(os.path.join(out, "house.glb"), objects)
    lightmaps = {}
    from PIL import Image
    for k, g, _o in objects:
        if k.startswith("arch_") or k.startswith("furn_"):
            Image.new("RGB", (64, 64), (150, 150, 150)).save(os.path.join(out, "lightmaps", k + ".png"))
            lightmaps[k] = {"file": "lightmaps/%s.png" % k, "size": 64, "mean": 0.25}
            if k in ("arch_trading", "furn_trading", "arch_corridor"):
                Image.new("RGB", (64, 64), (190, 170, 220)).save(os.path.join(out, "lightmaps", k + "_on.png"))
                lightmaps[k]["on"] = "lightmaps/%s_on.png" % k
                lightmaps[k]["mean_on"] = 0.35
    meta, G = house_meta.make(L, coll, extra, dyn_meta, {}, heights, lightmaps, BASE, {"bulb_glow": 6.0}, (0.3, -0.5, -0.8))
    json.dump(meta, open(os.path.join(out, "house_meta.json"), "w"))
    print("objects %d, glb %.1f MB, meta %.0f kB" % (len(objects), os.path.getsize(os.path.join(out, "house.glb")) / 1e6,
                                                     os.path.getsize(os.path.join(out, "house_meta.json")) / 1e3))


if __name__ == "__main__":
    main()
