#!/usr/bin/env python3
"""
Granny Dimnight: builds a new model for every visible object of the original scenes - same place, same size, same kind
of thing, made from scratch in a low-poly style - and writes them for the Unity build (ModelSwap.cs swaps them in by
GameObject file id). Granny herself (and the characters) keep their own models.

usage: build.py <catalog dir> <out dir> [--preview <obj dir>] [--scenes Main,...]
  <catalog dir>/<scene>.json   from catalog.py
  <out dir>/<scene>.dmodel     meshes in each object's own space
  <out dir>/materials.json     the materials the meshes use
  <out dir>/<scene>_report.txt what each object became
"""
import json
import math
import os
import random
import re
import struct
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mesh import Mesh, rot_y, translate  # noqa: E402
import materials  # noqa: E402
import builders  # noqa: E402


# ---------------------------------------------------------------------------------------------------------------
class Frame:
    """Maps a canonical frame (x, y = world up, z; metres) onto the object's own axes and scale."""

    def __init__(self, e):
        mw = np.array(e["world"], dtype=np.float64)
        self.mw = mw
        sc = np.linalg.norm(mw[:3, :3], axis=0)
        sc[sc < 1e-12] = 1e-12
        self.scale = sc
        R = mw[:3, :3] / sc
        self.R = R
        up = int(np.argmax(np.abs(R[1, :])))
        up_sign = 1.0 if R[1, up] >= 0 else -1.0
        rest = [i for i in range(3) if i != up]
        # x_c: the remaining local axis closest to world x; z_c the other
        a, b = rest
        if abs(R[0, a]) + 1e-9 < abs(R[0, b]):
            a, b = b, a
        sa = 1.0 if R[0, a] >= 0 else -1.0
        sb = 1.0 if R[2, b] >= 0 else -1.0
        self.c2l = [(a, sa), (up, up_sign), (b, sb)]
        M = np.zeros((3, 3))
        for k, (ax, s) in enumerate(self.c2l):
            M[ax, k] = s
        self.M = M                      # local_metric = M @ canonical
        lo = np.array(e["local_min"], float) * sc
        hi = np.array(e["local_max"], float) * sc
        corners = np.array([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])
        cc = corners @ M                # canonical = M.T @ local  (rows)
        self.cmin = cc.min(axis=0)
        self.cmax = cc.max(axis=0)
        # world direction of each canonical axis
        self.world_dir = [R @ M[:, k] for k in range(3)]

    def to_local(self, p):
        return (self.M @ np.asarray(p, float)) / self.scale

    def normal_to_local(self, n):
        v = (self.M @ np.asarray(n, float)) * self.scale
        l = np.linalg.norm(v)
        return v / l if l > 1e-12 else v

    def canon_of_local_metric(self, p):
        return self.M.T @ np.asarray(p, float)


# ---------------------------------------------------------------------------------------------------------------
def aabb_ray(o, d, mn, mx):
    tmin, tmax = -1e9, 1e9
    for i in range(3):
        if abs(d[i]) < 1e-12:
            if o[i] < mn[i] or o[i] > mx[i]:
                return None
        else:
            t1, t2 = (mn[i] - o[i]) / d[i], (mx[i] - o[i]) / d[i]
            t1, t2 = min(t1, t2), max(t1, t2)
            tmin, tmax = max(tmin, t1), min(tmax, t2)
            if tmin > tmax:
                return None
    return tmin if tmin >= 0 else (0.0 if tmax >= 0 else None)


class Scene:
    def __init__(self, cat):
        self.entries = [e for e in cat["renderers"]]
        self.by_path = {}
        for e in self.entries:
            self.by_path.setdefault(e["path"], e)
        self.walls = []
        for e in self.entries:
            if not e.get("world_min") or e.get("skinned"):
                continue
            mn, mx = np.array(e["world_min"]), np.array(e["world_max"])
            ext = mx - mn
            if (e.get("tris") or 99) <= 12 and ext[1] > 1.2 and min(ext[0], ext[2]) < 0.4 and max(ext[0], ext[2]) > 0.6:
                self.walls.append((mn, mx, e["id"]))

    def wall_distances(self, e, fr):
        """Distance from the object's sides to the nearest wall for canonical +x, -x, +z, -z."""
        mn, mx = np.array(e["world_min"]), np.array(e["world_max"])
        c = (mn + mx) / 2
        out = {}
        for key, k, s in (("+x", 0, 1), ("-x", 0, -1), ("+z", 2, 1), ("-z", 2, -1)):
            d = fr.world_dir[k] * s
            d = d / (np.linalg.norm(d) or 1)
            best = None
            for off in (-0.25, 0.0, 0.25):
                o = c.copy()
                o[1] = mn[1] + (mx[1] - mn[1]) * (0.5 + off)
                for wmn, wmx, wid in self.walls:
                    if wid == e["id"]:
                        continue
                    t = aabb_ray(o, d, wmn - 0.01, wmx + 0.01)
                    if t is not None and (best is None or t < best):
                        best = t
            half = abs(np.dot((mx - mn) / 2, np.abs(d)))
            out[key] = None if best is None else max(0.0, best - half)
        return out


# ---------------------------------------------------------------------------------------------------------------
class Ctx:
    def __init__(self, e, scene, fr):
        self.e = e
        self.scene = scene
        self.fr = fr
        self.name = e["name"]
        self.mats = [m or "" for m in e.get("materials") or []]
        self.mat0 = self.mats[0] if self.mats else ""
        self.rng = random.Random(int(e["id"]) & 0xFFFFFFFF)
        self.m = Mesh()
        size = fr.cmax - fr.cmin
        self.sx, self.sy, self.sz = [float(v) for v in size]
        self.front = "+z"
        self.raw = False

    def set_front(self, front):
        self.front = front

    @property
    def dims(self):
        """(w, h, d) in the builder frame, front facing +z."""
        if self.front in ("+z", "-z"):
            return self.sx, self.sy, self.sz
        return self.sz, self.sy, self.sx

    def front_by_walls(self, default="+z", max_gap=1.2):
        wd = self.scene.wall_distances(self.e, self.fr)
        known = {k: v for k, v in wd.items() if v is not None and v <= max_gap}
        if not known:
            return default
        back = min(known, key=known.get)
        return {"+x": "-x", "-x": "+x", "+z": "-z", "-z": "+z"}[back]

    def front_by_height(self, default=None):
        """The tall side (backrest, headboard) is the back."""
        hm = np.array(self.e.get("hmap_max") or [[-1]], float)
        if hm.ndim != 2 or hm.shape[0] < 4:
            return default
        half = hm.shape[0] // 2 + 1
        # rows: local z, cols: local x  ->  convert to canonical via the frame mapping
        vals = {}
        loc_axes = {0: hm.max(axis=0), 2: hm.max(axis=1)}  # per local x column / per local z row
        for key, k, s in (("+x", 0, 1), ("-x", 0, -1), ("+z", 2, 1), ("-z", 2, -1)):
            ax, sign = self.fr.c2l[k]
            if ax == 1:
                return default
            prof = loc_axes[ax]
            if sign * s < 0:
                prof = prof[::-1]
            vals[key] = float(np.mean(prof[half:]))   # the half towards +direction
        hi = max(vals, key=vals.get)
        lo = min(vals, key=vals.get)
        if vals[hi] - vals[lo] < 0.12:
            return default
        return {"+x": "-x", "-x": "+x", "+z": "-z", "-z": "+z"}[hi]

    def front_away_from(self, point_world, axes=("x", "z")):
        mn, mx = np.array(self.e["world_min"]), np.array(self.e["world_max"])
        c = (mn + mx) / 2
        v = c - np.asarray(point_world)
        best, key = -1e9, "+z"
        for k_name, k in (("x", 0), ("z", 2)):
            if k_name not in axes:
                continue
            dot = float(np.dot(v, self.fr.world_dir[k]))
            for s in (1, -1):
                if dot * s > best:
                    best, key = dot * s, ("+" if s > 0 else "-") + k_name
        return key

    def parent_center(self):
        p = self.e["path"].rsplit("/", 1)[0] if "/" in self.e["path"] else None
        while p:
            pe = self.scene.by_path.get(p)
            if pe and pe.get("world_min"):
                return (np.array(pe["world_min"]) + np.array(pe["world_max"])) / 2
            p = p.rsplit("/", 1)[0] if "/" in p else None
        return None

    def thin_axis(self):
        sizes = {"x": self.sx, "z": self.sz}
        return min(sizes, key=sizes.get)

    def hinge_side(self):
        """For a door panel built with front +z: which builder-frame x side the pivot (object origin) is on."""
        o = np.zeros(3) - self.fr.cmin - (self.fr.cmax - self.fr.cmin) / 2   # origin relative to the bounds centre
        ang = {"+z": 0, "-z": 180, "+x": 90, "-x": -90}[self.front]
        inv = rot_y(-ang)
        ob = inv[:3, :3] @ o
        return "left" if ob[0] < 0 else "right"

    def place(self):
        """Builder-frame mesh -> canonical metric mesh inside the object's bounds."""
        if self.raw:
            return self.m
        ang = {"+z": 0, "-z": 180, "+x": 90, "-x": -90}[self.front]
        c = (self.fr.cmin + self.fr.cmax) / 2
        T = translate(c[0], self.fr.cmin[1], c[2]) @ rot_y(ang)
        out = Mesh()
        out.add(self.m, T)
        return out


# ---------------------------------------------------------------------------------------------------------------
def classify(e):
    """-> builder name for an entry (rules in builders.RULES, first match wins)."""
    name = re.sub(r"\s*\(\d+\)", "", e["name"])
    name = re.sub(r"death$", "", name)
    name = re.sub(r"\.\d+$", "", name)
    mats = " ".join(m or "" for m in (e.get("materials") or []))
    path = e["path"]
    for rule in builders.RULES:
        pat_name, pat_mat, pat_path, fn = rule
        if pat_name and not re.search(pat_name, name):
            continue
        if pat_mat and not re.search(pat_mat, mats):
            continue
        if pat_path and not re.search(pat_path, path):
            continue
        return fn
    return None


KEEP = re.compile(r"^(Granny|Hair|Eyes|Tand|GrannyLleg2|GrannyRleg2|NOS|MomShadow|EyeLock[LR])$")


def write_dmodel(path, meshes):
    """Binary for ModelSwap.cs: 'DMDL', version, count, then per mesh: file id, sub-meshes (material, triangles),
    vertices (positions, normals, uvs in the object's own space)."""
    with open(path, "wb") as f:
        f.write(b"DMDL")
        f.write(struct.pack("<ii", 1, len(meshes)))
        for fid, pos, nor, uvs, subs in meshes:
            f.write(struct.pack("<q", int(fid)))
            f.write(struct.pack("<i", len(subs)))
            for mat, tris in subs:
                b = mat.encode("utf-8")
                f.write(struct.pack("<h", len(b)))
                f.write(b)
            f.write(struct.pack("<i", len(pos)))
            f.write(np.asarray(pos, "<f4").tobytes())
            f.write(np.asarray(nor, "<f4").tobytes())
            f.write(np.asarray(uvs, "<f4").tobytes())
            for mat, tris in subs:
                t = np.asarray(tris, "<i4").reshape(-1)
                f.write(struct.pack("<i", len(t)))
                f.write(t.tobytes())


def finish(ctx, fr):
    """Canonical mesh -> object's own space, per material, flattened."""
    m = ctx.place()
    pos, nor, uvs, subs = [], [], [], []
    for mat, (p, n, uv, tr) in m.parts.items():
        if not tr:
            continue
        base = len(pos)
        for v in p:
            pos.append(fr.to_local(v))
        for v in n:
            nor.append(fr.normal_to_local(v))
        uvs.extend(uv)
        # the canonical -> local map can be a mirror (det -1): keep the outside out
        flip = np.linalg.det(fr.M) < 0
        subs.append((mat, [(a + base, c + base, b + base) if flip else (a + base, b + base, c + base) for a, b, c in tr]))
    return pos, nor, uvs, subs


def preview_lines(ctx, fr, vcount_base, mats_used):
    """OBJ lines (world space, Blender-friendly: x, z, y) for the local preview."""
    m = ctx.place()
    lines, n = [], vcount_base
    for mat, (p, nr, uv, tr) in m.parts.items():
        if not tr:
            continue
        mats_used.add(mat)
        lines.append("usemtl %s" % mat)
        base = n
        for v in p:
            lm = fr.M @ np.asarray(v, float)
            w = fr.R @ lm + fr.mw[:3, 3]
            lines.append("v %.4f %.4f %.4f" % (w[0], w[1], -w[2]))
            n += 1
        flip = np.linalg.det(fr.M) * np.linalg.det(fr.R) < 0
        for a, b, c in tr:
            # Unity (left-handed) -> Blender (right-handed) swaps the winding once more
            if flip:
                lines.append("f %d %d %d" % (a + base + 1, b + base + 1, c + base + 1))
            else:
                lines.append("f %d %d %d" % (a + base + 1, c + base + 1, b + base + 1))
    return lines, n


def main():
    args = sys.argv[1:]
    cat_dir, out_dir = args[0], args[1]
    preview = args[args.index("--preview") + 1] if "--preview" in args else None
    scenes = args[args.index("--scenes") + 1].split(",") if "--scenes" in args else ["Main", "EscapeCutScene", "Scene_BalloonEscape", "GameOverScene"]
    os.makedirs(out_dir, exist_ok=True)
    used_mats = set()
    for scene_name in scenes:
        cp = os.path.join(cat_dir, scene_name + ".json")
        if not os.path.exists(cp):
            continue
        cat = json.load(open(cp))
        scene = Scene(cat)
        meshes, report, obj = [], [], []
        vbase, mats_prev = 0, set()
        counts = {}
        for e in scene.entries:
            if e.get("skinned") or e.get("local_min") is None:
                continue
            if KEEP.match(e["name"]):
                report.append("%-10s %s" % ("keep", e["path"]))
                continue
            fn_name = classify(e)
            if fn_name is None:
                report.append("%-10s %s  (mats %s, size %s)" % ("UNMAPPED", e["path"], e.get("materials"), e.get("size_m")))
                continue
            fr = Frame(e)
            ctx = Ctx(e, scene, fr)
            try:
                getattr(builders, fn_name)(ctx)
            except Exception as ex:  # noqa: BLE001
                report.append("%-10s %s  (%s: %s)" % ("FAILED", e["path"], fn_name, ex))
                continue
            if ctx.m.vertex_count() == 0:
                report.append("%-10s %s  (%s made nothing)" % ("EMPTY", e["path"], fn_name))
                continue
            pos, nor, uvs, subs = finish(ctx, fr)
            meshes.append((e["id"], pos, nor, uvs, subs))
            for mat, _ in subs:
                used_mats.add(mat)
            counts[fn_name] = counts.get(fn_name, 0) + 1
            report.append("%-10s %s -> %s (%d verts)" % ("ok", e["path"], fn_name, len(pos)))
            if preview and e.get("active") and e.get("enabled", True):
                lines, vbase = preview_lines(ctx, fr, vbase, mats_prev)
                obj.append("o %s_%s" % (re.sub(r"\W", "_", e["name"])[:30], e["id"]))
                obj.extend(lines)
        write_dmodel(os.path.join(out_dir, scene_name + ".dmodel"), meshes)
        with open(os.path.join(out_dir, scene_name + "_report.txt"), "w") as f:
            f.write("\n".join(report) + "\n\n" + json.dumps(counts, indent=1, sort_keys=True))
        if preview:
            os.makedirs(preview, exist_ok=True)
            with open(os.path.join(preview, scene_name + ".obj"), "w") as f:
                f.write("mtllib materials.mtl\n" + "\n".join(obj) + "\n")
        n_un = sum(1 for r in report if r.startswith("UNMAPPED"))
        n_fail = sum(1 for r in report if r.startswith(("FAILED", "EMPTY")))
        print("[models] %s: %d new models, %d kept, %d unmapped, %d failed" % (
            scene_name, len(meshes), sum(1 for r in report if r.startswith("keep")), n_un, n_fail))
    mats_out = {}
    for k in sorted(used_mats):
        slot, col, tile, smooth, metal, opts = materials.M.get(k, materials.M["plaster_white"])
        mats_out[k] = {"slot": slot, "color": list(col), "tile": tile, "smoothness": smooth, "metallic": metal, **opts}
    with open(os.path.join(out_dir, "materials.json"), "w") as f:
        json.dump(mats_out, f, indent=1)
    if preview:
        with open(os.path.join(preview, "materials.mtl"), "w") as f:
            for k, v in mats_out.items():
                c = [x / 255.0 for x in v["color"]]
                f.write("newmtl %s\nKd %.3f %.3f %.3f\n" % (k, c[0], c[1], c[2]))
                if v.get("transparent") is not None:
                    f.write("d %.2f\n" % max(0.15, v["transparent"]))
    print("[models] materials:", len(mats_out))


if __name__ == "__main__":
    main()
