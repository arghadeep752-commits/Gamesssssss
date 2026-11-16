#!/usr/bin/env python3
"""
Granny Dimnight: catalogue of every visible model in the original scenes, so each one can be replaced by a new model
of the same kind and size.

For every MeshRenderer it writes the GameObject's file id (the key the Unity build uses to swap the model), its path,
world matrix (Unity coordinates), the mesh, the materials, and the exact bounds of its geometry in the object's own
space ("local bounds", in local units) - read from the exported Unity mesh assets, including the statically batched
"Combined Mesh" pieces, whose vertices are stored in world space.

usage: catalog.py <ExportedProject dir> <scene name> <out.json> [scene json from original/scenes for material names]
"""
import json
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "extract"))
from report import unity_docs, ref_of, vec  # noqa: E402

BUILTIN = {10202: "builtin:Cube", 10206: "builtin:Cylinder", 10207: "builtin:Sphere", 10208: "builtin:Capsule",
           10209: "builtin:Plane", 10210: "builtin:Quad"}
BUILTIN_BOUNDS = {"builtin:Cube": ((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)), "builtin:Cylinder": ((-0.5, -1, -0.5), (0.5, 1, 0.5)),
                  "builtin:Sphere": ((-0.5, -0.5, -0.5), (0.5, 0.5, 0.5)), "builtin:Capsule": ((-0.5, -1, -0.5), (0.5, 1, 0.5)),
                  "builtin:Plane": ((-5, 0, -5), (5, 0, 5)), "builtin:Quad": ((-0.5, -0.5, 0), (0.5, 0.5, 0))}
DUMP = {} if os.environ.get("CATALOG_DUMP") else None   # local analysis only: geometry for reference thumbnails
FORMAT_SIZE = {0: 4, 1: 2, 2: 1, 3: 1, 4: 2, 5: 2, 6: 1, 7: 1, 8: 2, 9: 2, 10: 4, 11: 4}


def trs(p, q, s):
    x, y, z, w = q
    n = (x * x + y * y + z * z + w * w) ** 0.5 or 1.0
    x, y, z, w = x / n, y / n, z / n, w / n
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r @ np.diag(s)
    m[:3, 3] = p
    return m


class MeshStore:
    def __init__(self, project):
        self.root = os.path.join(project, "Assets")
        self.by_guid = {}
        for dp, _dn, fn in os.walk(self.root):
            for f in fn:
                if f.endswith(".asset.meta"):
                    with open(os.path.join(dp, f), encoding="utf-8", errors="replace") as fh:
                        for line in fh:
                            if line.startswith("guid:"):
                                self.by_guid[line.split(":", 1)[1].strip()] = os.path.join(dp, f[:-5])
                                break
        self.cache = {}

    def get(self, guid):
        if guid in self.cache:
            return self.cache[guid]
        path = self.by_guid.get(guid)
        m = None
        if path and os.path.exists(path):
            with open(path, encoding="utf-8", errors="replace") as fh:
                text = fh.read()
            # hex blobs are read straight from the text: the YAML loader turns all-digit ones into numbers
            ib = re.search(r"^\s*m_IndexBuffer: *([0-9a-fA-F]*)\s*$", text, re.M)
            vd = re.search(r"^\s*_typelessdata: *([0-9a-fA-F]*)\s*$", text, re.M)
            for cid, _fid, _s, _t, body in unity_docs(path):
                if cid == 43:
                    body["m_IndexBuffer"] = ib.group(1) if ib else ""
                    if vd and isinstance(body.get("m_VertexData"), dict):
                        body["m_VertexData"]["_typelessdata"] = vd.group(1)
                    m = self._decode(body, os.path.splitext(os.path.basename(path))[0])
                    break
        self.cache[guid] = m
        return m

    @staticmethod
    def _decode(body, name):
        vd = body.get("m_VertexData") or {}
        n = int(vd.get("m_VertexCount") or 0)
        raw = bytes.fromhex(str(vd.get("_typelessdata") or ""))
        chans = vd.get("m_Channels") or []
        pos = None
        if n and raw and chans:
            streams = {}
            for ch in chans:
                st, off, fmt, dim = int(ch.get("stream", 0)), int(ch.get("offset", 0)), int(ch.get("format", 0)), int(ch.get("dimension", 0)) & 0xF
                if dim:
                    streams[st] = max(streams.get(st, 0), off + FORMAT_SIZE.get(fmt, 4) * dim)
            start, offsets = 0, {}
            for st in sorted(streams):
                offsets[st] = start
                start += streams[st] * n
                start = (start + 15) // 16 * 16
            c0 = chans[0]
            st, off, fmt, dim = int(c0.get("stream", 0)), int(c0.get("offset", 0)), int(c0.get("format", 0)), int(c0.get("dimension", 0)) & 0xF
            if fmt == 0 and dim >= 3 and st in streams:
                stride = streams[st]
                base = offsets[st] + off
                buf = np.frombuffer(raw, dtype=np.uint8)
                idx = base + np.arange(n)[:, None] * stride + np.arange(12)[None, :]
                if idx.max() < len(buf):
                    pos = buf[idx].copy().view("<f4").reshape(n, 3).astype(np.float64)
        ib = bytes.fromhex(str(body.get("m_IndexBuffer") or ""))
        idx_dtype = "<u2" if int(body.get("m_IndexFormat") or 0) == 0 else "<u4"
        indices = np.frombuffer(ib, dtype=idx_dtype).astype(np.int64) if ib else np.zeros(0, np.int64)
        subs = []
        for sm in body.get("m_SubMeshes") or []:
            isz = 2 if idx_dtype == "<u2" else 4
            first = int(sm.get("firstByte", 0)) // isz
            cnt = int(sm.get("indexCount", 0))
            subs.append((first, cnt, int(sm.get("baseVertex", 0))))
        return {"name": name, "pos": pos, "indices": indices, "subs": subs}


def tri_list(m, first_sub=None, sub_count=None):
    """Triangles (index triples) of the whole mesh or of a submesh range."""
    out = []
    rng = range(len(m["subs"])) if first_sub is None else range(first_sub, min(first_sub + sub_count, len(m["subs"])))
    for si in rng:
        f, c, bv = m["subs"][si]
        idx = m["indices"][f:f + c] + bv
        out.append(idx[: len(idx) // 3 * 3].reshape(-1, 3))
    return np.concatenate(out) if out else np.zeros((0, 3), np.int64)


def height_map(pts, lo, hi, n=8):
    """Max and min height (local Y, 0..1 of the bounds) in an n x n grid over local X (columns) and Z (rows)."""
    size = np.maximum(hi - lo, 1e-9)
    u = np.clip(((pts[:, 0] - lo[0]) / size[0] * n).astype(int), 0, n - 1)
    v = np.clip(((pts[:, 2] - lo[2]) / size[2] * n).astype(int), 0, n - 1)
    h = (pts[:, 1] - lo[1]) / size[1]
    mx = np.full((n, n), -1.0)
    mn = np.full((n, n), 2.0)
    np.maximum.at(mx, (v, u), h)
    np.minimum.at(mn, (v, u), h)
    mx[mx < 0] = -1
    mn[mn > 1.5] = -1
    return np.round(mx, 2).tolist(), np.round(mn, 2).tolist()


def plane_rects(tri_pts, axes, lo, hi, cell):
    """Rasterises triangles projected on two local axes and merges the filled cells into rectangles (greedy)."""
    a, b = axes
    na = max(1, int(np.ceil((hi[a] - lo[a]) / cell)))
    nb = max(1, int(np.ceil((hi[b] - lo[b]) / cell)))
    if na * nb > 400 * 400:
        return None
    grid = np.zeros((na, nb), bool)
    ca = lo[a] + (np.arange(na) + 0.5) * cell
    cb = lo[b] + (np.arange(nb) + 0.5) * cell
    for t in tri_pts:
        p = t[:, [a, b]]
        mn, mx = p.min(axis=0), p.max(axis=0)
        ia0, ia1 = int(max(0, (mn[0] - lo[a]) // cell)), int(min(na - 1, (mx[0] - lo[a]) // cell))
        ib0, ib1 = int(max(0, (mn[1] - lo[b]) // cell)), int(min(nb - 1, (mx[1] - lo[b]) // cell))
        if ia1 < ia0 or ib1 < ib0:
            continue
        A, B = np.meshgrid(ca[ia0:ia1 + 1], cb[ib0:ib1 + 1], indexing="ij")
        (x0, y0), (x1, y1), (x2, y2) = p
        d = (y1 - y2) * (x0 - x2) + (x2 - x1) * (y0 - y2)
        if abs(d) < 1e-12:
            continue
        l0 = ((y1 - y2) * (A - x2) + (x2 - x1) * (B - y2)) / d
        l1 = ((y2 - y0) * (A - x2) + (x0 - x2) * (B - y2)) / d
        l2 = 1 - l0 - l1
        eps = -1e-3
        grid[ia0:ia1 + 1, ib0:ib1 + 1] |= (l0 >= eps) & (l1 >= eps) & (l2 >= eps)
    rects = []
    used = np.zeros_like(grid)
    for i in range(na):
        j = 0
        while j < nb:
            if grid[i, j] and not used[i, j]:
                j1 = j
                while j1 + 1 < nb and grid[i, j1 + 1] and not used[i, j1 + 1]:
                    j1 += 1
                i1 = i
                while i1 + 1 < na and grid[i1 + 1, j:j1 + 1].all() and not used[i1 + 1, j:j1 + 1].any():
                    i1 += 1
                used[i:i1 + 1, j:j1 + 1] = True
                rects.append([round(float(lo[a] + i * cell), 5), round(float(lo[b] + j * cell), 5),
                              round(float(lo[a] + (i1 + 1) * cell), 5), round(float(lo[b] + (j1 + 1) * cell), 5)])
                j = j1 + 1
            else:
                j += 1
    filled = float(grid.mean())
    return {"axes": [int(a), int(b)], "cell": cell, "fill": round(filled, 3), "rects": rects}


def main():
    project, scene_name, out = sys.argv[1], sys.argv[2], sys.argv[3]
    names_json = sys.argv[4] if len(sys.argv) > 4 else None
    scene_path = os.path.join(project, "Assets", "Scenes", scene_name + ".unity")
    store = MeshStore(project)
    docs = {}
    for cid, fid, _stripped, typ, body in unity_docs(scene_path):
        docs[fid] = (cid, typ, body)
    gos, tr_of_go, mf_of_go, mr_of_go, smr_of_go = {}, {}, {}, {}, {}
    for fid, (cid, _typ, body) in docs.items():
        go, _ = ref_of(body.get("m_GameObject"))
        if cid == 1:
            gos[fid] = body
        elif cid in (4, 224):
            tr_of_go[go] = fid
        elif cid == 33:
            mf_of_go[go] = body
        elif cid == 23:
            mr_of_go[go] = body
        elif cid == 137:
            smr_of_go[go] = body

    world = {}

    def world_of(tfid, depth=0):
        if tfid in world:
            return world[tfid]
        t = docs.get(tfid, (0, "", {}))[2]
        lp, lr, ls = vec(t.get("m_LocalPosition")), vec(t.get("m_LocalRotation"), "xyzw", 0.0), vec(t.get("m_LocalScale"), "xyz", 1.0)
        if lr == [0.0, 0.0, 0.0, 0.0]:
            lr = [0.0, 0.0, 0.0, 1.0]
        m = trs(lp, lr, ls)
        father, _ = ref_of(t.get("m_Father"))
        if father and father in docs and depth < 200:
            m = world_of(father, depth + 1) @ m
        world[tfid] = m
        return m

    def active_in_hierarchy(go_fid, depth=0):
        g = gos.get(go_fid) or {}
        if int(g.get("m_IsActive", 1) or 0) == 0:
            return False
        t = docs.get(tr_of_go.get(go_fid, 0), (0, "", {}))[2]
        father, _ = ref_of(t.get("m_Father"))
        if father and depth < 200:
            fgo, _ = ref_of(docs.get(father, (0, "", {}))[2].get("m_GameObject"))
            if fgo in gos:
                return active_in_hierarchy(fgo, depth + 1)
        return True

    def path_name(go_fid, depth=0):
        t = docs.get(tr_of_go.get(go_fid, 0), (0, "", {}))[2]
        father, _ = ref_of(t.get("m_Father"))
        name = str((gos.get(go_fid) or {}).get("m_Name") or "?")
        if father and depth < 60:
            fgo, _ = ref_of(docs.get(father, (0, "", {}))[2].get("m_GameObject"))
            if fgo in gos:
                return path_name(fgo, depth + 1) + "/" + name
        return name

    mat_names = {}
    if names_json and os.path.exists(names_json):
        for o in json.load(open(names_json)).get("objects", []):
            mat_names[int(o.get("id", 0))] = o.get("materials") or []

    entries = []
    for go, mf in mf_of_go.items():
        mr = mr_of_go.get(go)
        if mr is None:
            continue
        mfid, mguid = ref_of(mf.get("m_Mesh"))
        tf = tr_of_go.get(go)
        if tf is None:
            continue
        mw = world_of(tf)
        info = {"id": go, "name": str(gos.get(go, {}).get("m_Name")), "path": path_name(go),
                "active": active_in_hierarchy(go), "enabled": int(mr.get("m_Enabled", 1) or 0) == 1,
                "layer": int(gos.get(go, {}).get("m_Layer", 0) or 0), "world": np.round(mw, 6).tolist(),
                "materials": mat_names.get(go, []), "mesh": None, "local_min": None, "local_max": None}
        sbi = mr.get("m_StaticBatchInfo") or {}
        first_sub, sub_count = int(sbi.get("firstSubMesh", 0) or 0), int(sbi.get("subMeshCount", 0) or 0)
        pts = None
        if mguid in (None, "0000000000000000e000000000000000") and mfid in BUILTIN:
            info["mesh"] = BUILTIN[mfid]
            lo, hi = BUILTIN_BOUNDS[BUILTIN[mfid]]
            info["local_min"], info["local_max"] = list(lo), list(hi)
            info["builtin"] = True
            sc = np.linalg.norm(mw[:3, :3], axis=0)
            corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])], dtype=np.float64)
            info["size_m"] = np.round((np.array(hi) - np.array(lo)) * sc, 4).tolist()
            info["scale"] = np.round(sc, 6).tolist()
            info["tris"] = 12
            info["verts"] = 8
            wpts = (mw[:3, :3] @ corners.T).T + mw[:3, 3]
            info["world_min"] = np.round(wpts.min(axis=0), 3).tolist()
            info["world_max"] = np.round(wpts.max(axis=0), 3).tolist()
        elif mguid:
            m = store.get(mguid)
            if m is not None and m["pos"] is not None:
                info["mesh"] = m["name"]
                if sub_count > 0 and m["name"].startswith("Combined"):
                    vids = set()
                    for si in range(first_sub, min(first_sub + sub_count, len(m["subs"]))):
                        f, c, bv = m["subs"][si]
                        vids.update((m["indices"][f:f + c] + bv).tolist())
                    vids = np.array(sorted(v for v in vids if v < len(m["pos"])), dtype=np.int64)
                    if len(vids):
                        wp = m["pos"][vids]
                        inv = np.linalg.inv(mw)
                        pts = (inv[:3, :3] @ wp.T).T + inv[:3, 3]
                        info["combined"] = True
                else:
                    pts = m["pos"]
                if pts is not None and len(pts):
                    info["local_min"] = np.round(pts.min(axis=0), 6).tolist()
                    info["local_max"] = np.round(pts.max(axis=0), 6).tolist()
                    info["verts"] = int(len(pts))
                    # geometry in the object's own axes but in metres (the transform's scale applied)
                    sc = np.linalg.norm(mw[:3, :3], axis=0)
                    sp = pts * sc
                    lo_m, hi_m = sp.min(axis=0), sp.max(axis=0)
                    info["size_m"] = np.round(hi_m - lo_m, 4).tolist()
                    info["scale"] = np.round(sc, 6).tolist()
                    if info.get("combined"):
                        tris = tri_list(m, first_sub, sub_count)
                        remap = {v: i for i, v in enumerate(vids.tolist())}
                        tris = np.array([[remap.get(v, -1) for v in t] for t in tris.tolist()], dtype=np.int64)
                        tris = tris[(tris >= 0).all(axis=1)]
                    else:
                        tris = tri_list(m)
                    info["tris"] = int(len(tris))
                    samp = sp
                    if len(tris):
                        A, B, C = sp[tris[:, 0]], sp[tris[:, 1]], sp[tris[:, 2]]
                        rng = np.random.default_rng(int(go) & 0xFFFFFFFF)
                        k = 24
                        u = rng.random((len(tris), k, 1))
                        v = rng.random((len(tris), k, 1))
                        flip = (u + v) > 1
                        u = np.where(flip, 1 - u, u)
                        v = np.where(flip, 1 - v, v)
                        pts_s = A[:, None, :] + u * (B - A)[:, None, :] + v * (C - A)[:, None, :]
                        samp = np.concatenate([sp, pts_s.reshape(-1, 3)])
                    hmx, hmn = height_map(samp, lo_m, hi_m, 12)
                    info["hmap_max"], info["hmap_min"] = hmx, hmn
                    if DUMP is not None and len(tris) > 12:
                        DUMP[str(go)] = (sp.astype(np.float32), tris.astype(np.int32))
                    ext = hi_m - lo_m
                    thin = int(np.argmin(ext))
                    big = sorted(set(range(3)) - {thin})
                    if len(tris) > 12 and ext[thin] < 0.25 * min(ext[big[0]], ext[big[1]]) and min(ext[big[0]], ext[big[1]]) > 0.3:
                        cell = float(np.clip(max(ext[big[0]], ext[big[1]]) / 160.0, 0.04, 0.2))
                        pr = plane_rects(sp[tris], big, lo_m, hi_m, cell)
                        if pr is not None:
                            pr["thin_axis"] = thin
                            info["plane"] = pr
                    # coarse height profile along the longer horizontal world axis (for stairs and ramps)
                    wpts = (mw[:3, :3] @ pts.T).T + mw[:3, 3]
                    ext = wpts.max(axis=0) - wpts.min(axis=0)
                    ax = 0 if ext[0] >= ext[2] else 2
                    lo, hi = wpts[:, ax].min(), wpts[:, ax].max()
                    if hi - lo > 1e-6:
                        bins = np.clip(((wpts[:, ax] - lo) / (hi - lo) * 8).astype(int), 0, 7)
                        prof = [float(np.round(wpts[bins == b, 1].max(), 3)) if np.any(bins == b) else None for b in range(8)]
                        info["profile"] = {"axis": "xz"[ax // 2], "heights": prof}
                    info["world_min"] = np.round(wpts.min(axis=0), 3).tolist()
                    info["world_max"] = np.round(wpts.max(axis=0), 3).tolist()
        entries.append(info)
    for go, smr in smr_of_go.items():
        entries.append({"id": go, "name": str(gos.get(go, {}).get("m_Name")), "path": path_name(go), "skinned": True,
                        "active": active_in_hierarchy(go), "world": np.round(world_of(tr_of_go[go]), 6).tolist() if go in tr_of_go else None})
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w") as f:
        json.dump({"scene": scene_name, "renderers": entries}, f, indent=0)
    if DUMP:
        np.savez_compressed(os.environ["CATALOG_DUMP"], **{k + "_v": v[0] for k, v in DUMP.items()}, **{k + "_t": v[1] for k, v in DUMP.items()})
    ok = sum(1 for e in entries if e.get("local_min") is not None)
    print("[catalog] %s: %d renderers, %d with bounds, %d combined, %d skinned" % (
        scene_name, len(entries), ok, sum(1 for e in entries if e.get("combined")), sum(1 for e in entries if e.get("skinned"))))


if __name__ == "__main__":
    main()
