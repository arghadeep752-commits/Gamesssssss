#!/usr/bin/env python3
"""Rigs and animates the Hyper3D Rodin characters without Rodin's rigging service.

A Rodin character stands in an A-pose facing +Z (glTF). We cut the mesh into horizontal slices, find the arms, legs,
torso and head in every slice, place a humanoid skeleton (hips, spine, chest, neck, head, shoulders, arms, legs, feet),
skin the mesh to it (region-aware weights, smoothed over the surface) and write hand-keyed animation clips (idle, walk,
run, sprint, jump, punch, swing, aim, shoot, hit, death, drive, ride, swim, cower ...).

Everything is in Unity space (X = the character's right, Y up, Z forward); every bone's rest rotation is the identity,
so a clip's local rotations are plain axis-angle turns (pitch about X: negative = forward for limbs hanging down).

    python3 tools/rig/autorig.py IN.glb OUT.bytes --height 1.74 [--skirt] [--preview DIR]
"""
import argparse
import io
import json
import math
import os
import struct
import sys

import numpy as np

BONES = ["Hips", "Spine", "Chest", "Neck", "Head",
         "Shoulder.R", "UpperArm.R", "LowerArm.R", "Hand.R",
         "Shoulder.L", "UpperArm.L", "LowerArm.L", "Hand.L",
         "UpperLeg.R", "LowerLeg.R", "Foot.R",
         "UpperLeg.L", "LowerLeg.L", "Foot.L"]
PARENT = {"Hips": None, "Spine": "Hips", "Chest": "Spine", "Neck": "Chest", "Head": "Neck",
          "Shoulder.R": "Chest", "UpperArm.R": "Shoulder.R", "LowerArm.R": "UpperArm.R", "Hand.R": "LowerArm.R",
          "Shoulder.L": "Chest", "UpperArm.L": "Shoulder.L", "LowerArm.L": "UpperArm.L", "Hand.L": "LowerArm.L",
          "UpperLeg.R": "Hips", "LowerLeg.R": "UpperLeg.R", "Foot.R": "LowerLeg.R",
          "UpperLeg.L": "Hips", "LowerLeg.L": "UpperLeg.L", "Foot.L": "LowerLeg.L"}
BI = {b: i for i, b in enumerate(BONES)}
FPS = 30.0


# =============================================================================================== glTF
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load_glb(path):
    b = open(path, "rb").read()
    _, _, ln = struct.unpack_from("<4sII", b, 0)
    o, js, binc = 12, None, None
    while o < ln:
        cl, ct = struct.unpack_from("<II", b, o)
        o += 8
        if ct == 0x4E4F534A:
            js = json.loads(b[o:o + cl])
        else:
            binc = b[o:o + cl]
        o += cl

    def acc(i):
        a = js["accessors"][i]
        bv = js["bufferViews"][a["bufferView"]]
        dt = np.dtype(CT[a["componentType"]])
        n = NC[a["type"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 0)
        if stride and stride != dt.itemsize * n:
            raw = np.frombuffer(binc, np.uint8, stride * (a["count"] - 1) + dt.itemsize * n, off)
            arr = np.lib.stride_tricks.as_strided(raw, (a["count"], dt.itemsize * n), (stride, 1)).copy().view(dt).reshape(a["count"], n)
        else:
            arr = np.frombuffer(binc, dt, a["count"] * n, off).reshape(a["count"], n).copy()
        return arr

    def img(ti):
        im = js["images"][js["textures"][ti]["source"]]
        bv = js["bufferViews"][im["bufferView"]]
        s = bv.get("byteOffset", 0)
        return binc[s:s + bv["byteLength"]], im.get("mimeType", "image/png")

    Ps, Ns, UVs, Is = [], [], [], []
    base = 0
    tex = {}
    for m in js["meshes"]:
        for pr in m["primitives"]:
            at = pr["attributes"]
            P = acc(at["POSITION"]).astype(np.float64)
            N = acc(at["NORMAL"]).astype(np.float64) if "NORMAL" in at else None
            UV = acc(at["TEXCOORD_0"]).astype(np.float64) if "TEXCOORD_0" in at else np.zeros((len(P), 2))
            I = acc(pr["indices"]).astype(np.int64).reshape(-1) if "indices" in pr else np.arange(len(P))
            Ps.append(P)
            Ns.append(N if N is not None else np.zeros_like(P))
            UVs.append(UV)
            Is.append(I + base)
            base += len(P)
            if "material" in pr and not tex:
                mat = js["materials"][pr["material"]]
                pbr = mat.get("pbrMetallicRoughness", {})
                for key, ref in (("albedo", pbr.get("baseColorTexture")), ("normal", mat.get("normalTexture")),
                                 ("mr", pbr.get("metallicRoughnessTexture"))):
                    if ref is not None:
                        tex[key] = img(ref["index"])
    P = np.vstack(Ps)
    N = np.vstack(Ns)
    UV = np.vstack(UVs)
    I = np.concatenate(Is).reshape(-1, 3)
    if not np.any(N):
        N = vertex_normals(P, I)
    return P, N, UV, I, tex


def vertex_normals(P, I):
    fn = np.cross(P[I[:, 1]] - P[I[:, 0]], P[I[:, 2]] - P[I[:, 0]])
    N = np.zeros_like(P)
    for k in range(3):
        np.add.at(N, I[:, k], fn)
    return N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)


def to_unity(P, N, UV, I):
    """glTF (right-handed, Y up) -> Unity (left-handed, Y up): (x, y, z) -> (-x, y, z), winding reversed, v flipped."""
    P = P * np.array([-1.0, 1.0, 1.0])
    N = N * np.array([-1.0, 1.0, 1.0])
    UV = np.c_[UV[:, 0], 1.0 - UV[:, 1]]
    I = I[:, [0, 2, 1]]
    return P, N, UV, I


# =============================================================================================== analysis
def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0 + 1e-12), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def slice_components(P, I, y, res=0.01, ext=0.6):
    """Cross-section of the mesh at height y: outline pixels labelled by connected component."""
    from scipy import ndimage
    A, B, C = P[I[:, 0]], P[I[:, 1]], P[I[:, 2]]
    ys = np.stack([A[:, 1], B[:, 1], C[:, 1]], 1)
    hit = (ys.min(1) <= y) & (ys.max(1) >= y)
    segs = []
    for tri in np.nonzero(hit)[0]:
        v = [A[tri], B[tri], C[tri]]
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            ya, yb = v[a][1], v[b][1]
            if (ya - y) * (yb - y) <= 0 and ya != yb:
                t = (y - ya) / (yb - ya)
                pts.append(v[a] + (v[b] - v[a]) * t)
        if len(pts) >= 2:
            segs.append((pts[0], pts[1]))
    n = int(2 * ext / res)
    grid = np.zeros((n, n), bool)
    for p, q in segs:
        L = max(1, int(np.linalg.norm(q[[0, 2]] - p[[0, 2]]) / (res * 0.5)) + 1)
        for t in np.linspace(0, 1, L + 1):
            r = p + (q - p) * t
            i = int((r[0] + ext) / res)
            j = int((r[2] + ext) / res)
            if 0 <= i < n and 0 <= j < n:
                grid[j, i] = True
    grid = ndimage.binary_dilation(grid, iterations=1)
    lab, k = ndimage.label(grid, structure=np.ones((3, 3)))
    comps = []
    for c in range(1, k + 1):
        jj, ii = np.nonzero(lab == c)
        if len(ii) < 4:
            continue
        xs = ii * res - ext + res / 2
        zs = jj * res - ext + res / 2
        comps.append({"id": c, "cx": float(xs.mean()), "cz": float(zs.mean()), "xmin": float(xs.min()), "xmax": float(xs.max()),
                      "zmin": float(zs.min()), "zmax": float(zs.max()), "n": int(len(ii))})
    return lab, comps


def _track(slices, start_idx, comp, reject_fn, max_jump=0.06, max_miss=7, y_max=1e9):
    """Follow one cross-section piece upwards from slice start_idx, tolerating short stretches where it touches the
    body (reject_fn(comp) -> True for pieces that are not this limb, e.g. the torso)."""
    chain = [(slices[start_idx][0], comp)]
    prev = comp
    miss = 0
    for y, lab, comps in slices[start_idx + 1:]:
        if y > y_max:
            break
        cands = [c for c in comps if not reject_fn(c) and abs(c["cx"] - prev["cx"]) < max_jump * (1 + miss * 0.3)
                 and abs(c["cz"] - prev["cz"]) < max_jump * 1.5 * (1 + miss * 0.3)]
        if not cands:
            miss += 1
            if miss > max_miss:
                break
            continue
        c = min(cands, key=lambda q: (q["cx"] - prev["cx"]) ** 2 + (q["cz"] - prev["cz"]) ** 2)
        chain.append((y, c))
        prev = c
        miss = 0
    return chain


def analyse(P, I, H, skirt=False):
    """Joint positions (Unity space) and a region label per vertex."""
    from scipy import ndimage
    res, ext = 0.01, 0.6
    step = 0.015
    ys = np.arange(0.02, H * 0.97, step)
    slices = []
    for y in ys:
        lab, comps = slice_components(P, I, y, res, ext)
        slices.append((y, lab, comps))
    yidx = {round(y, 4): k for k, (y, _, _) in enumerate(slices)}

    def k_at(y):
        return int(np.argmin(np.abs(ys - y)))
    # --- legs: from the ankles up, as long as nothing crosses the middle line (x = 0) the legs are apart
    def centre_empty(lab):
        mid = int(ext / res)
        return not lab[:, mid - 1:mid + 1].any()
    def apart(comps):
        """Two legs side by side: the two biggest pieces are of a similar size, do not overlap, and both reach in
        close to the middle (unlike the torso and a hand)."""
        big = sorted(comps, key=lambda c: -c["n"])[:2]
        if len(big) < 2:
            return False
        a, b = sorted(big, key=lambda c: c["cx"])
        if max(a["n"], b["n"]) > 1.8 * min(a["n"], b["n"]) or a["xmax"] >= b["xmin"]:
            return False
        mid = (a["xmax"] + b["xmin"]) / 2
        return abs(mid) < 0.06 and (b["xmin"] - a["xmax"]) < 0.12
    sep = [(y, apart(comps)) for y, lab, comps in slices]
    # the highest gap between the legs below the torso (scanning down from the waist): trousers part at the crotch,
    # a kurta, dhoti or sari only below its hem
    leg_top = None
    for y, e in sorted(sep, key=lambda t: -t[0]):
        if y > 0.56 * H:
            continue
        if e:
            leg_top = y
            break
    if skirt or leg_top is None:
        leg_top = 0.1 * H if leg_top is None else leg_top
    crotch = leg_top
    skirt_mode = skirt or crotch < 0.32 * H
    if skirt_mode:
        crotch = 0.47 * H                  # under a sari, kurta or dhoti: the usual proportions
    legs = {"R": [], "L": []}
    for y, lab, comps in slices:
        if y > min(leg_top, crotch) or y < 0.02:
            continue
        for side, sgn in (("R", 1.0), ("L", -1.0)):
            cs = [c for c in comps if sgn * c["cx"] > 0.005 and c["n"] > 10]
            if cs:
                legs[side].append((y, max(cs, key=lambda c: c["n"])))
    # --- torso pieces (the one around x = 0 above the crotch)
    torso_c = {}
    for y, lab, comps in slices:
        if y >= crotch and comps:
            span = [c for c in comps if c["xmin"] <= 0.0 <= c["xmax"]]
            torso_c[round(y, 4)] = max(span, key=lambda c: c["n"]) if span else min(comps, key=lambda c: abs(c["cx"]))

    def torso_z(y):
        ks = sorted(torso_c)
        if not ks:
            return 0.0
        k = min(ks, key=lambda q: abs(q - y))
        return torso_c[k]["cz"]
    # --- arms: the lowest pieces hanging outside the legs / torso (the hands), followed up until they join the torso
    arm = {"R": [], "L": []}
    leg_ids = {side: {round(y, 4): c["id"] for y, c in legs[side]} for side in legs}
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        start = None
        for k, (y, lab, comps) in enumerate(slices):
            if y < 0.3 * H or y > 0.74 * H:
                continue
            core = [c for c in comps if c["xmin"] <= 0.0 <= c["xmax"]] + [c for c in comps if c["id"] in (leg_ids["R"].get(round(y, 4)), leg_ids["L"].get(round(y, 4)))]
            if skirt_mode and y < crotch:
                core = [max(comps, key=lambda c: c["n"])] if comps else []
            edge = max([sgn * (c["xmax"] if sgn > 0 else c["xmin"]) for c in core] or [0.06 * H])
            side_c = [c for c in comps if c not in core and c["n"] >= 4
                      and sgn * (c["xmin"] if sgn > 0 else c["xmax"]) > edge - 0.006]
            if side_c:
                start = (k, max(side_c, key=lambda c: c["n"]))
                break
        if start is None:
            continue

        def reject(c, sgn=sgn):
            return c["xmin"] <= 0.0 <= c["xmax"] or sgn * c["cx"] < 0.05 * H
        arm[side] = _track(slices, start[0], start[1], reject, y_max=0.86 * H)
    # an arm that could not be followed (it touches the body all the way): mirror the other one
    good = {side: len([1 for y, c in arm[side] if c is not None]) for side in arm}
    for side, other in (("R", "L"), ("L", "R")):
        if good[side] < 6 and good[other] >= 8:
            arm[side] = [(y, dict(c, cx=-c["cx"], xmin=-c["xmax"], xmax=-c["xmin"], id=-1)) for y, c in arm[other] if c is not None]
    J = {}
    hip_y = crotch + 0.055 * H
    J["Hips"] = np.array([0.0, hip_y, torso_z(hip_y)])
    J["Spine"] = np.array([0.0, max(hip_y + 0.05 * H, 0.63 * H), torso_z(0.63 * H)])
    J["Chest"] = np.array([0.0, 0.73 * H, torso_z(0.73 * H)])
    J["Neck"] = np.array([0.0, 0.835 * H, torso_z(0.835 * H)])
    J["Head"] = np.array([0.0, 0.875 * H, torso_z(0.875 * H)])
    J["HeadTop"] = np.array([0.0, H, torso_z(0.92 * H)])
    arm_top = {}
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        chain = arm[side]
        # shoulder: from the chest width just under the shoulders
        chest = torso_c.get(min(torso_c, key=lambda q: abs(q - 0.79 * H))) if torso_c else None
        half = (chest["xmax"] if sgn > 0 else -chest["xmin"]) if chest else 0.2 * H
        sh = np.array([sgn * (half - 0.045 * H), 0.815 * H, torso_z(0.8 * H)])
        if len(chain) >= 4:
            cl = np.array([[c["cx"], y, c["cz"]] for y, c in chain[::-1]])     # top to bottom
            tip = np.array([chain[0][1]["cx"], chain[0][0] - step, chain[0][1]["cz"]])
            arm_top[side] = (chain[-1][0], chain[-1][1])
            sh[0] = sgn * max(sgn * sh[0], sgn * cl[0, 0] - 0.01 * H)
        else:
            cl = np.array([[sgn * 0.21 * H, 0.6 * H, 0.0]])
            tip = np.array([sgn * 0.22 * H, 0.4 * H, 0.02])
            arm_top[side] = (0.62 * H, None)
        path = np.vstack([sh, cl, tip])
        seg = np.linalg.norm(np.diff(path, axis=0), axis=1)
        sc = np.concatenate([[0], np.cumsum(seg)])
        total = sc[-1]

        def at(f):
            return np.array([np.interp(f * total, sc, path[:, k]) for k in range(3)])
        J["UpperArm." + side] = sh
        J["LowerArm." + side] = at(0.43)
        J["Hand." + side] = at(0.76)
        J["HandTip." + side] = tip
        J["Shoulder." + side] = np.array([sgn * 0.035 * H, 0.80 * H, torso_z(0.8 * H)])
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        if legs[side]:
            lc = legs[side]

            def leg_at(y):
                yy, c = min(lc, key=lambda t: abs(t[0] - y))
                return np.array([c["cx"], y, c["cz"]])
            top = leg_at(crotch - 0.03 * H)
            knee = leg_at(0.285 * H)
            if skirt_mode:
                top = np.array([sgn * 0.085 * H, crotch - 0.03 * H, torso_z(crotch)])
                if leg_top < 0.3 * H:
                    knee = np.array([sgn * 0.075 * H, 0.285 * H, torso_z(0.3 * H) + 0.01])
            top[0] = sgn * min(max(sgn * top[0], 0.055 * H), 0.11 * H)
        else:
            top = np.array([sgn * 0.085 * H, crotch - 0.03 * H, torso_z(crotch)])
            knee = np.array([sgn * 0.08 * H, 0.285 * H, torso_z(0.3 * H) + 0.01])
        side_v = P[(P[:, 0] * sgn > 0.005) & (P[:, 1] < 0.06 * H)]
        if len(side_v) > 10:
            ank = np.array([np.median(side_v[:, 0]), 0.05 * H, np.percentile(side_v[:, 2], 30)])
            toe = np.array([np.median(side_v[:, 0]), 0.015 * H, side_v[:, 2].max()])
        else:
            ank = np.array([sgn * 0.08 * H, 0.05 * H, 0.0])
            toe = np.array([sgn * 0.08 * H, 0.015 * H, 0.1 * H])
        J["UpperLeg." + side] = np.array([top[0], hip_y - 0.02 * H, top[2]])
        J["LowerLeg." + side] = knee
        J["Foot." + side] = ank
        J["Toe." + side] = toe
    # --- labels per vertex
    lab_v = np.full(len(P), "torso", dtype=object)
    arm_ids = {side: {round(y, 4): c["id"] for y, c in arm[side]} for side in arm}
    for y, lab, comps in slices:
        sel = np.abs(P[:, 1] - y) <= step / 2 + 1e-9
        if not sel.any():
            continue
        yk = round(y, 4)
        idmap = {}
        for side in ("R", "L"):
            if yk in arm_ids[side]:
                idmap[arm_ids[side][yk]] = "arm_" + side
            if yk in leg_ids[side]:
                idmap[leg_ids[side][yk]] = "leg_" + side
        dist, (jj, ii) = ndimage.distance_transform_edt(lab == 0, return_indices=True)
        vi = np.nonzero(sel)[0]
        gi = np.clip(((P[vi, 0] + ext) / res).astype(int), 0, lab.shape[1] - 1)
        gj = np.clip(((P[vi, 2] + ext) / res).astype(int), 0, lab.shape[0] - 1)
        cid = lab[jj[gj, gi], ii[gj, gi]]
        for k, v in enumerate(vi):
            l = idmap.get(int(cid[k]))
            if l is None:
                if y <= leg_top:
                    l = "leg_R" if P[v, 0] > 0 else "leg_L"
                elif y < crotch:
                    l = "skirt"
                else:
                    l = "torso"
            lab_v[v] = l
    # the feet below the first slice belong to the legs
    low = P[:, 1] < ys[0] + step / 2
    lab_v[low & (P[:, 0] > 0)] = "leg_R"
    lab_v[low & (P[:, 0] <= 0)] = "leg_L"
    # the whole arm, also where it touches the body (hands on the hips, upper arm against the chest): everything
    # outside the arm's inner edge, interpolated between the slices where the arm hangs free
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        ch = [(y, c) for y, c in arm[side] if c is not None]
        if len(ch) < 2:
            continue
        yy = np.array([y for y, c in ch])
        inner = np.array([(c["xmin"] if sgn > 0 else -c["xmax"]) for y, c in ch])
        sel = (P[:, 1] >= yy.min() - step) & (P[:, 1] <= yy.max())
        edge = np.interp(P[:, 1], yy, inner)
        m = sel & (sgn * P[:, 0] > edge - 0.012)
        lab_v[m] = "arm_" + side
    # upper arm where it touches the body: lateral vertices between the arm's top and the shoulder
    for side, sgn in (("R", 1.0), ("L", -1.0)):
        y_top, c_top = arm_top[side]
        x_in_low = sgn * (c_top["xmin"] if (c_top and sgn > 0) else (c_top["xmax"] if c_top else sgn * 0.17 * H))
        x_in_high = sgn * J["UpperArm." + side][0] - 0.03 * H
        y_hi = J["UpperArm." + side][1] + 0.01 * H
        sel = (P[:, 1] >= y_top) & (P[:, 1] <= y_hi)
        f = np.clip((P[:, 1] - y_top) / max(1e-6, y_hi - y_top), 0, 1)
        x_in = x_in_low + (x_in_high - x_in_low) * f
        m = sel & (sgn * P[:, 0] > x_in)
        lab_v[m] = "arm_" + side
    info = {"crotch": crotch, "leg_top": leg_top, "skirt": skirt_mode, "arm_pts": {s: len(arm[s]) for s in arm}, "leg_pts": {s: len(legs[s]) for s in legs},
            "arm_top": {s: round(arm_top[s][0], 3) for s in arm_top}}
    return J, lab_v, info


# =============================================================================================== weights
def chain_weights(p, chain, names, blend):
    """Weights of points p along a chain of joints (len(names) = len(chain) - 1 segments)."""
    n = len(names)
    best_t = np.zeros(len(p))
    best_d = np.full(len(p), 1e9)
    cum = [0.0]
    for k in range(n):
        cum.append(cum[-1] + float(np.linalg.norm(chain[k + 1] - chain[k])))
    for k in range(n):
        a, b = chain[k], chain[k + 1]
        d = b - a
        L2 = float(d @ d) + 1e-12
        t = np.clip(((p - a) @ d) / L2, 0, 1)
        q = a + t[:, None] * d
        dist = np.linalg.norm(p - q, axis=1)
        better = dist < best_d
        best_d[better] = dist[better]
        best_t[better] = cum[k] + t[better] * (cum[k + 1] - cum[k])
    W = np.zeros((len(p), n))
    for k in range(n):
        lo = cum[k]
        hi = cum[k + 1]
        w = smoothstep(lo - blend, lo + blend, best_t) if k > 0 else np.ones(len(p))
        w2 = 1 - smoothstep(hi - blend, hi + blend, best_t) if k < n - 1 else np.ones(len(p))
        W[:, k] = w * w2
    W /= W.sum(1, keepdims=True) + 1e-12
    return W


def skin(P, I, J, labels, H, leg_top=0.0):
    nb = len(BONES)
    W = np.zeros((len(P), nb))
    lab = np.asarray(labels)
    # torso: hips -> spine -> chest -> neck -> head by height
    t = lab == "torso"
    if t.any():
        y = P[t, 1]
        ys = [J["Hips"][1] - 0.2, J["Spine"][1], J["Chest"][1], J["Neck"][1], J["Head"][1]]
        names = ["Hips", "Spine", "Chest", "Neck", "Head"]
        Wt = np.zeros((t.sum(), 5))
        bl = 0.035 * H
        for k in range(5):
            lo = ys[k]
            hi = ys[k + 1] if k < 4 else 99
            a = smoothstep(lo - bl, lo + bl, y) if k > 0 else np.ones_like(y)
            b = 1 - smoothstep(hi - bl, hi + bl, y) if k < 4 else np.ones_like(y)
            Wt[:, k] = a * b
        Wt /= Wt.sum(1, keepdims=True) + 1e-12
        for k, n in enumerate(names):
            W[t, BI[n]] = Wt[:, k]
        # shoulders: torso next to the shoulder joint follows the arm a little
        for side in ("R", "L"):
            d = np.linalg.norm(P[t] - J["UpperArm." + side], axis=1)
            w = 1 - smoothstep(0.03 * H, 0.085 * H, d)
            sgn = 1 if side == "R" else -1
            w *= (P[t, 0] * sgn > 0.06 * H)
            W[t] *= (1 - w[:, None] * 0.75)
            W[t, BI["UpperArm." + side]] += w * 0.5
            W[t, BI["Shoulder." + side]] += w * 0.25
    for side in ("R", "L"):
        a = lab == ("arm_" + side)
        if a.any():
            chain = [J["Shoulder." + side], J["UpperArm." + side], J["LowerArm." + side], J["Hand." + side], J["HandTip." + side]]
            Wa = chain_weights(P[a], chain, ["Shoulder." + side, "UpperArm." + side, "LowerArm." + side, "Hand." + side], 0.03 * H)
            for k, n in enumerate(["Shoulder." + side, "UpperArm." + side, "LowerArm." + side, "Hand." + side]):
                W[a, BI[n]] = Wa[:, k]
        l = lab == ("leg_" + side)
        if l.any():
            chain = [J["Hips"], J["UpperLeg." + side], J["LowerLeg." + side], J["Foot." + side], J["Toe." + side]]
            Wl = chain_weights(P[l], chain, ["Hips", "UpperLeg." + side, "LowerLeg." + side, "Foot." + side], 0.035 * H)
            for k, n in enumerate(["Hips", "UpperLeg." + side, "LowerLeg." + side, "Foot." + side]):
                W[l, BI[n]] += Wl[:, k]
    s = lab == "skirt"
    if s.any():
        x, y = P[s, 0], P[s, 1]
        wr = smoothstep(-0.05 * H, 0.05 * H, x)
        down = 1 - smoothstep(max(0.08 * H, leg_top), J["Hips"][1], y)       # 1 at the hem, 0 at the waist
        W[s, BI["Hips"]] = 1 - down * 0.85
        W[s, BI["UpperLeg.R"]] = down * 0.55 * wr
        W[s, BI["UpperLeg.L"]] = down * 0.55 * (1 - wr)
        W[s, BI["LowerLeg.R"]] = down * down * 0.3 * wr
        W[s, BI["LowerLeg.L"]] = down * down * 0.3 * (1 - wr)
        feet = y < 0.07 * H
        W[s & False] = 0
        idx = np.nonzero(s)[0][feet]
        W[idx] = 0
        W[idx, np.where(P[idx, 0] > 0, BI["Foot.R"], BI["Foot.L"])] = 1.0
    # smooth over the surface (welded by position)
    key = np.round(P / 0.002).astype(np.int64)
    _, inv = np.unique(key, axis=0, return_inverse=True)
    inv = inv.reshape(-1)
    nw = inv.max() + 1
    Wu = np.zeros((nw, nb))
    np.add.at(Wu, inv, W)
    cnt = np.bincount(inv, minlength=nw)[:, None]
    Wu /= np.maximum(cnt, 1)
    Iu = inv[I]
    edges = np.vstack([Iu[:, [0, 1]], Iu[:, [1, 2]], Iu[:, [2, 0]]])
    # keep the arms' weights off the body where they merely touch it (hands on hips, inner arm on the chest)
    lab_u = np.empty(nw, dtype=object)
    lab_u[inv] = lab
    Pu = np.zeros((nw, 3))
    Pu[inv] = P
    is_arm = np.array([str(x).startswith("arm") for x in lab_u])
    near_sh = (np.linalg.norm(Pu - J["UpperArm.R"], axis=1) < 0.09 * H) | (np.linalg.norm(Pu - J["UpperArm.L"], axis=1) < 0.09 * H)
    ok = ~((is_arm[edges[:, 0]] != is_arm[edges[:, 1]]) & ~near_sh[edges[:, 0]] & ~near_sh[edges[:, 1]])
    edges = edges[ok]
    edges = np.vstack([edges, edges[:, ::-1]])
    deg = np.bincount(edges[:, 0], minlength=nw)[:, None]
    for _ in range(6):
        acc = np.zeros_like(Wu)
        np.add.at(acc, edges[:, 0], Wu[edges[:, 1]])
        Wu = 0.5 * Wu + 0.5 * acc / np.maximum(deg, 1)
    W = Wu[inv]
    # top 4
    order = np.argsort(-W, axis=1)[:, :4]
    w4 = np.take_along_axis(W, order, 1)
    w4 /= w4.sum(1, keepdims=True) + 1e-12
    return order.astype(np.int32), w4.astype(np.float32)


def cut_seams(P, N, UV, I, labels, bi, bw, J, H):
    """Where an arm only touches the body (not at the shoulder), split the surface so the arm can move away without
    dragging a sheet of stretched triangles with it."""
    lab = np.asarray(labels)
    arm = np.array([str(x).startswith("arm") for x in lab])
    near = (np.linalg.norm(P - J["UpperArm.R"], axis=1) < 0.1 * H) | (np.linalg.norm(P - J["UpperArm.L"], axis=1) < 0.1 * H)
    newP, newN, newUV, newbi, newbw = [P], [N], [UV], [bi], [bw]
    I = I.copy()
    n = len(P)
    cut = 0
    dup = {}
    for t in range(len(I)):
        a = arm[I[t]]
        if a.all() or not a.any() or near[I[t]].any():
            continue
        maj = a.sum() >= 2                       # True: the triangle goes with the arm
        rep = I[t][a == maj][0]
        for k in range(3):
            v = I[t][k]
            if arm[v] == maj:
                continue
            key = (v, rep if maj else -1, maj)
            if key not in dup:
                dup[key] = n
                newP.append(P[v:v + 1])
                newN.append(N[v:v + 1])
                newUV.append(UV[v:v + 1])
                newbi.append(bi[rep:rep + 1])
                newbw.append(bw[rep:rep + 1])
                n += 1
            I[t][k] = dup[key]
            cut += 1
    return np.vstack(newP), np.vstack(newN), np.vstack(newUV), I, np.vstack(newbi), np.vstack(newbw), cut


# =============================================================================================== animation
def qaxis(axis, deg):
    a = math.radians(deg) / 2
    ax = np.asarray(axis, float)
    return np.array([ax[0] * math.sin(a), ax[1] * math.sin(a), ax[2] * math.sin(a), math.cos(a)])


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
                     aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz])


def euler(pitch=0.0, yaw=0.0, roll=0.0):
    """Unity-style: yaw (Y) * pitch (X) * roll (Z)."""
    return qmul(qmul(qaxis((0, 1, 0), yaw), qaxis((1, 0, 0), pitch)), qaxis((0, 0, 1), roll))


def pose_fn(name, female=False):
    """Returns f(t) -> ({bone: (pitch, yaw, roll)}, hips offset (x, y, z)), the clip length and whether it loops."""
    amp = 0.72 if female else 1.0
    s, c, pi = math.sin, math.cos, math.pi

    def arms_rest(d):
        d.setdefault("UpperArm.R", [0, 0, 0])
        d.setdefault("UpperArm.L", [0, 0, 0])

    if name == "idle":
        def f(t):
            p = 2 * pi * t / 3.0
            return ({"Spine": (1.0 * s(p), 0, 0), "Chest": (1.2 * s(p), 0, 0), "Neck": (0, 4 * s(p * 0.5), 0), "Head": (2 * s(p * 0.7), 3 * s(p * 0.5), 0),
                     "UpperArm.R": (2 * s(p), 0, 3 + 1.5 * s(p)), "UpperArm.L": (2 * s(p), 0, -3 - 1.5 * s(p)),
                     "LowerArm.R": (-8, 0, 0), "LowerArm.L": (-8, 0, 0)}, (0, 0.004 * s(p), 0))
        return f, 3.0, True
    if name in ("walk", "run", "sprint", "swim"):
        T = {"walk": 1.0, "run": 0.72, "sprint": 0.56, "swim": 1.6}[name]
        th = {"walk": 26, "run": 42, "sprint": 52, "swim": 20}[name] * amp
        kn = {"walk": 48, "run": 95, "sprint": 110, "swim": 40}[name] * (0.85 if female else 1.0)
        arm = {"walk": 18, "run": 40, "sprint": 55, "swim": 10}[name] * amp
        elb = {"walk": 12, "run": 85, "sprint": 95, "swim": 40}[name]
        lean = {"walk": 3, "run": 10, "sprint": 16, "swim": 6}[name]
        bob = {"walk": 0.022, "run": 0.05, "sprint": 0.06, "swim": 0.01}[name]

        def f(t):
            p = 2 * pi * t / T
            d = {}
            for side, ph in (("R", 0.0), ("L", pi)):
                q = p + ph
                d["UpperLeg." + side] = (-th * s(q) - (6 if name != "walk" else 2), 0, 0)
                knee = 5 + kn * max(0.0, s(q + pi * 0.62)) ** 1.4 * (0.95 if name == "walk" else 1.0)
                d["LowerLeg." + side] = (knee, 0, 0)
                d["Foot." + side] = (-0.4 * knee + th * 0.25 * s(q), 0, 0)
                sgn = 1 if side == "R" else -1
                d["UpperArm." + side] = (arm * s(q), 0, sgn * (4 if name == "walk" else 10))
                d["LowerArm." + side] = (-elb - (10 * max(0.0, -s(q)) if name == "walk" else 8 * s(q)), 0, 0)
            d["Spine"] = (lean * 0.6, -3 * s(p) * amp, 0)
            d["Chest"] = (lean * 0.4, -3 * s(p) * amp, 0)
            d["Hips"] = (0, 5 * s(p) * amp, 2 * c(p) * amp)
            d["Head"] = (-lean * 0.6, 3 * s(p) * amp, 0)
            if name == "swim":
                d["UpperArm.R"] = (-70 + 50 * s(p), 0, 20 + 30 * c(p))
                d["UpperArm.L"] = (-70 + 50 * s(p), 0, -20 - 30 * c(p))
            return d, (0.012 * s(p) * amp, -bob * c(2 * p) - (0.02 if name != "walk" else 0.0), 0)
        return f, T, True
    if name == "jump":
        def f(t):
            k = min(1.0, t / 0.6)
            crouch = s(pi * k)
            d = {"UpperLeg.R": (-30 - 25 * crouch, 0, 0), "UpperLeg.L": (-15 - 20 * crouch, 0, 0), "LowerLeg.R": (40 + 45 * crouch, 0, 0),
                 "LowerLeg.L": (30 + 40 * crouch, 0, 0), "UpperArm.R": (-40 * crouch, 0, 25), "UpperArm.L": (-40 * crouch, 0, -25),
                 "LowerArm.R": (-30, 0, 0), "LowerArm.L": (-30, 0, 0), "Spine": (8, 0, 0)}
            return d, (0, -0.05 * crouch, 0)
        return f, 0.6, False
    if name == "fall":
        def f(t):
            p = 2 * pi * t / 0.8
            return ({"UpperLeg.R": (-35 + 8 * s(p), 0, 4), "UpperLeg.L": (-20 - 8 * s(p), 0, -4), "LowerLeg.R": (50, 0, 0), "LowerLeg.L": (45, 0, 0),
                     "UpperArm.R": (-30 + 10 * s(p), 0, 55), "UpperArm.L": (-30 - 10 * s(p), 0, -55), "LowerArm.R": (-25, 0, 0),
                     "LowerArm.L": (-25, 0, 0)}, (0, 0, 0))
        return f, 0.8, True
    if name == "punch":
        def f(t):
            k = t / 0.55
            hit = s(pi * min(1.0, k / 0.55)) if k < 0.55 else max(0.0, 1 - (k - 0.55) / 0.45) * 0.0
            ext = smoothstep(0.0, 0.35, k) * (1 - smoothstep(0.55, 1.0, k))
            d = {"UpperArm.R": (-80 * ext - 20, -10 * ext, 15 - 10 * ext), "LowerArm.R": (-100 * (1 - ext) - 10, 0, 0),
                 "UpperArm.L": (-55, 15, -10), "LowerArm.L": (-115, 0, 0), "Chest": (4, -22 * ext + 8, 0), "Spine": (5, -8 * ext, 0),
                 "UpperLeg.R": (6, 0, 0), "UpperLeg.L": (-14, 0, 0), "LowerLeg.L": (14, 0, 0), "LowerLeg.R": (6, 0, 0)}
            return d, (0, -0.02, 0.03 * ext)
        return f, 0.55, False
    if name == "swing":
        def f(t):
            k = t / 0.7
            wind = smoothstep(0.0, 0.3, k) * (1 - smoothstep(0.3, 0.55, k))
            sw = smoothstep(0.3, 0.6, k) * (1 - smoothstep(0.75, 1.0, k))
            yaw = 45 * wind - 55 * sw
            d = {"Chest": (5, yaw, 0), "Spine": (5, yaw * 0.4, 0), "UpperArm.R": (-75, -30 * sw + 25 * wind, 20), "LowerArm.R": (-40, 0, 0),
                 "UpperArm.L": (-70, 30 * sw, -10), "LowerArm.L": (-55, 0, 0), "UpperLeg.L": (-15, 0, 0), "LowerLeg.L": (15, 0, 0)}
            return d, (0, -0.02, 0)
        return f, 0.7, False
    if name in ("aim_pistol", "shoot_pistol", "aim_rifle", "shoot_rifle"):
        rifle = "rifle" in name
        shoot = "shoot" in name
        T = 0.22 if shoot else 1.5

        def f(t):
            kick = s(pi * min(1.0, t / 0.22)) * (8 if rifle else 12) if shoot else 0.0
            br = 0.8 * s(2 * pi * t / 1.5) if not shoot else 0.0
            if rifle:
                d = {"UpperArm.R": (-55 - kick * 0.4 + br, 10, 35), "LowerArm.R": (-75, 0, 0), "UpperArm.L": (-78 - kick + br, -20, -15),
                     "LowerArm.L": (-30, 0, 0), "Chest": (2, -12, 0), "Head": (2, 10, 0), "Neck": (0, 4, 0)}
            else:
                d = {"UpperArm.R": (-86 - kick + br, -6, 6), "LowerArm.R": (-4, 0, 0), "UpperArm.L": (-80 - kick + br, 28, -6),
                     "LowerArm.L": (-28, 0, 0), "Chest": (-2 - kick * 0.2, -6, 0), "Head": (2, 6, 0)}
            return d, (0, 0, 0)
        return f, T, not shoot
    if name == "hit":
        def f(t):
            k = s(pi * min(1.0, t / 0.35))
            return ({"Chest": (-14 * k, 6 * k, 0), "Spine": (-6 * k, 0, 0), "Head": (-12 * k, 0, 0), "UpperArm.R": (-20 * k, 0, 20 * k),
                     "UpperArm.L": (-20 * k, 0, -20 * k)}, (0, 0, -0.06 * k))
        return f, 0.35, False
    if name == "death":
        def f(t):
            k = smoothstep(0.0, 1.0, t / 1.2)
            knee = 70 * s(pi * min(1.0, k * 1.4))
            d = {"Hips": (-88 * k, 0, 0), "Spine": (10 * k, 0, 0), "Head": (-15 * k, 20 * k, 0), "UpperLeg.R": (-20 * k, 0, 5),
                 "UpperLeg.L": (-35 * k, 0, -8), "LowerLeg.R": (knee * 0.7, 0, 0), "LowerLeg.L": (knee, 0, 0),
                 "UpperArm.R": (-30 * k, 0, 60 * k), "UpperArm.L": (-40 * k, 0, -55 * k), "LowerArm.R": (-20, 0, 0), "LowerArm.L": (-30, 0, 0)}
            return d, (0, -0.8 * k, -0.25 * k)
        return f, 1.4, False
    if name == "drive":
        def f(t):
            p = 2 * pi * t / 2.0
            return ({"UpperLeg.R": (-82, 0, 4), "UpperLeg.L": (-82, 0, -4), "LowerLeg.R": (80, 0, 0), "LowerLeg.L": (80, 0, 0),
                     "Foot.R": (-10, 0, 0), "Foot.L": (-10, 0, 0), "Spine": (-6, 0, 0), "UpperArm.R": (-48, -8, 8), "UpperArm.L": (-48, 8, -8),
                     "LowerArm.R": (-38, 0, 0), "LowerArm.L": (-38, 0, 0), "Head": (0, 3 * s(p), 0)}, (0, -0.42, -0.05))
        return f, 2.0, True
    if name == "ride":
        def f(t):
            return ({"UpperLeg.R": (-62, 0, 12), "UpperLeg.L": (-62, 0, -12), "LowerLeg.R": (80, 0, 0), "LowerLeg.L": (80, 0, 0),
                     "Spine": (14, 0, 0), "Chest": (6, 0, 0), "Head": (-14, 0, 0), "UpperArm.R": (-62, -12, 10), "UpperArm.L": (-62, 12, -10),
                     "LowerArm.R": (-25, 0, 0), "LowerArm.L": (-25, 0, 0)}, (0, -0.36, -0.03))
        return f, 2.0, True
    if name == "cower":
        def f(t):
            p = 2 * pi * t / 0.5
            return ({"UpperLeg.R": (-95, 0, 8), "UpperLeg.L": (-95, 0, -8), "LowerLeg.R": (130, 0, 0), "LowerLeg.L": (130, 0, 0),
                     "Foot.R": (-30, 0, 0), "Foot.L": (-30, 0, 0), "Spine": (25, 0, 0), "Chest": (15, 0, 0), "Head": (20, 0, 0),
                     "UpperArm.R": (-140 + 3 * s(p), 0, 30), "UpperArm.L": (-140 - 3 * s(p), 0, -30), "LowerArm.R": (-120, 0, 0),
                     "LowerArm.L": (-120, 0, 0)}, (0, -0.55, -0.05))
        return f, 0.5, True
    if name == "phone":
        def f(t):
            return ({"UpperArm.R": (-30, -20, 10), "LowerArm.R": (-110, 0, 0), "Head": (14, 0, 0)}, (0, 0, 0))
        return f, 1.0, True
    raise KeyError(name)


CLIPS = ["idle", "walk", "run", "sprint", "jump", "fall", "punch", "swing", "aim_pistol", "shoot_pistol", "aim_rifle", "shoot_rifle",
         "hit", "death", "drive", "ride", "swim", "cower"]
SPEED = {"walk": 1.45, "run": 3.9, "sprint": 6.3, "swim": 1.2}


def bake_clips(J, female, arms=True):
    out = []
    for name in CLIPS:
        f0, T, loop = pose_fn(name, female)
        if arms:
            f = f0
        else:
            def f(t, f0=f0):          # arms that could not be separated from the body stay where they are
                d, off = f0(t)
                return {k: v for k, v in d.items() if "Arm" not in k and "Shoulder" not in k}, off
        frames = int(round(T * FPS)) + 1
        P = np.zeros((len(BONES), frames, 3))
        R = np.zeros((len(BONES), frames, 4))
        for fr in range(frames):
            t = min(T, fr / FPS)
            d, off = f(t)
            for b, bname in enumerate(BONES):
                par = PARENT[bname]
                rest = J[bname] - (J[par] if par else np.zeros(3))
                P[b, fr] = rest + (np.asarray(off) if bname == "Hips" else 0.0)
                e = d.get(bname, (0, 0, 0))
                R[b, fr] = euler(e[0], e[1], e[2])
        # keep quaternion neighbours on the same hemisphere
        for b in range(len(BONES)):
            for fr in range(1, frames):
                if np.dot(R[b, fr], R[b, fr - 1]) < 0:
                    R[b, fr] = -R[b, fr]
        out.append((name, T, loop, SPEED.get(name, 0.0), frames, P, R))
    return out


# =============================================================================================== output
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

    def arr(self, a, dt):
        self.parts.append(np.ascontiguousarray(a, dtype=dt).tobytes())

    def save(self, path):
        with open(path, "wb") as f:
            for p in self.parts:
                f.write(p)


def rig(glb, height, skirt=False, female=False):
    P, N, UV, I, tex = load_glb(glb)
    P, N, UV, I = to_unity(P, N, UV, I)
    ymin, ymax = P[:, 1].min(), P[:, 1].max()
    s = height / (ymax - ymin)
    P = (P - np.array([0, ymin, 0])) * s
    band = P[(P[:, 1] > 0.45 * height) & (P[:, 1] < 0.6 * height)]
    ctr = np.array([np.median(band[:, 0]), 0.0, np.median(band[:, 2])]) if len(band) else np.zeros(3)
    P -= ctr
    J, labels, info = analyse(P, I, height, skirt)
    bi, bw = skin(P, I, J, labels, height, info.get("leg_top", 0.0))
    P, N, UV, I, bi, bw, ncut = cut_seams(P, N, UV, I, labels, bi, bw, J, height)
    labels = list(labels) + ["cut"] * (len(P) - len(labels))
    info["cut"] = ncut
    arms = max(info["arm_pts"].values()) >= 6
    info["arms"] = arms
    clips = bake_clips(J, female, arms)
    return dict(P=P, N=N, UV=UV, I=I, tex=tex, J=J, labels=labels, info=info, bi=bi, bw=bw, clips=clips, height=height)


def write(r, path):
    o = Out()
    o.i32(0x48434744)      # 'DGCH'
    o.i32(1)
    P, N, UV, I = r["P"], r["N"], r["UV"], r["I"]
    o.i32(len(P))
    o.arr(P, "<f4")
    o.arr(N, "<f4")
    o.arr(UV, "<f4")
    o.arr(r["bi"], "<i4")
    o.arr(r["bw"], "<f4")
    o.i32(I.size)
    o.arr(I.reshape(-1), "<i4")
    o.i32(len(BONES))
    J = r["J"]
    for bname in BONES:
        par = PARENT[bname]
        o.s(bname)
        o.i32(BI[par] if par else -1)
        local = J[bname] - (J[par] if par else np.zeros(3))
        o.f32(*local)
        o.f32(0, 0, 0, 1)
        o.f32(1, 1, 1)
        bind = np.eye(4)
        bind[:3, 3] = -J[bname]                     # rest rotations are identity: bind = translate(-joint)
        o.arr(bind.reshape(-1), "<f4")
    o.f32(1.0, 0.0)                                  # scale, y offset (already applied)
    o.i32(len(r["clips"]))
    for name, T, loop, nat, frames, Pc, Rc in r["clips"]:
        o.s(name)
        o.f32(T)
        o.i32(1 if loop else 0)
        o.f32(nat)
        o.i32(frames)
        o.f32(FPS)
        o.arr(Pc, "<f4")
        o.arr(Rc, "<f4")
    # extra points: hand grip (right), head top, eye height
    o.f32(*J["Hand.R"], *J["HandTip.R"], *J["Hand.L"], *J["HeadTop"])
    o.save(path)


# =============================================================================================== preview
def pose_matrices(J, clip, frame):
    name, T, loop, nat, frames, Pc, Rc = clip
    M = {}
    for b, bname in enumerate(BONES):
        q = Rc[b, frame]
        x, y, z, w = q
        R = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                      [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                      [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        L = np.eye(4)
        L[:3, :3] = R
        L[:3, 3] = Pc[b, frame]
        par = PARENT[bname]
        M[bname] = (M[par] @ L) if par else L
    return M


def deform(r, clip, frame):
    J = r["J"]
    M = pose_matrices(J, clip, frame)
    skinM = np.stack([M[b] @ np.block([[np.eye(3), -J[b][:, None]], [np.zeros((1, 3)), np.ones((1, 1))]]) for b in BONES])
    P4 = np.c_[r["P"], np.ones(len(r["P"]))]
    out = np.zeros((len(P4), 3))
    for k in range(4):
        Mk = skinM[r["bi"][:, k]]
        out += r["bw"][:, k:k + 1] * np.einsum("nij,nj->ni", Mk, P4)[:, :3]
    return out


def preview(r, out_png, clips=("idle", "walk", "run", "punch", "aim_pistol", "swing", "drive", "death")):
    from PIL import Image, ImageDraw
    sys.path.insert(0, "/home/claude/work/tools")
    tex = None
    if "albedo" in r["tex"]:
        tex = np.asarray(Image.open(io.BytesIO(r["tex"]["albedo"][0])).convert("RGB"), np.float32) / 255
    names = [c[0] for c in r["clips"]]
    tiles = []
    for cname in clips:
        clip = r["clips"][names.index(cname)]
        for fr in (0, clip[4] // 3, (2 * clip[4]) // 3):
            V = deform(r, clip, fr)
            tiles.append((cname, fr, render_side(V, r["I"], r["UV"], tex, view="side" if cname in ("walk", "run", "drive", "death") else "front")))
    W = 180
    S = Image.new("RGB", (W * 6, (len(tiles) + 5) // 6 * 220), (30, 30, 34))
    d = ImageDraw.Draw(S)
    for k, (cname, fr, im) in enumerate(tiles):
        x, y = (k % 6) * W, (k // 6) * 220
        S.paste(im, (x, y + 16))
        d.text((x + 3, y + 2), "%s f%d" % (cname, fr), fill=(255, 255, 0))
    S.save(out_png)


def render_side(V, I, UV, tex, view="front", W=180, H=200):
    from PIL import Image
    if view == "front":
        sx, sy, z = -V[:, 0], V[:, 1], -V[:, 2]       # camera in front (at +Z) looking back: character's right on screen left
    else:
        sx, sy, z = V[:, 2], V[:, 1], -V[:, 0]       # camera on the character's left looking right
    sc = H / 2.1
    px = W / 2 + sx * sc
    py = H - 8 - sy * sc
    img = np.zeros((H, W, 3), np.float32) + 0.18
    zb = np.full((H, W), 1e9)
    th, tw = (tex.shape[:2] if tex is not None else (1, 1))
    for a, b, c in I:
        xs = np.array([px[a], px[b], px[c]])
        ys = np.array([py[a], py[b], py[c]])
        x0, x1 = int(max(0, xs.min())), int(min(W - 1, xs.max() + 1))
        y0, y1 = int(max(0, ys.min())), int(min(H - 1, ys.max() + 1))
        if x1 < x0 or y1 < y0:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        dd = (ys[1] - ys[2]) * (xs[0] - xs[2]) + (xs[2] - xs[1]) * (ys[0] - ys[2])
        if abs(dd) < 1e-9:
            continue
        w0 = ((ys[1] - ys[2]) * (gx - xs[2]) + (xs[2] - xs[1]) * (gy - ys[2])) / dd
        w1 = ((ys[2] - ys[0]) * (gx - xs[2]) + (xs[0] - xs[2]) * (gy - ys[2])) / dd
        w2 = 1 - w0 - w1
        m = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
        if not m.any():
            continue
        zz = w0 * z[a] + w1 * z[b] + w2 * z[c]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        m &= zz < sub
        if not m.any():
            continue
        if tex is not None:
            u = w0 * UV[a, 0] + w1 * UV[b, 0] + w2 * UV[c, 0]
            v = w0 * UV[a, 1] + w1 * UV[b, 1] + w2 * UV[c, 1]
            col = tex[np.clip(((1 - v) % 1) * th, 0, th - 1).astype(int), np.clip((u % 1) * tw, 0, tw - 1).astype(int)]
        else:
            col = np.ones(m.shape + (3,)) * 0.7
        sub[m] = zz[m]
        img[y0:y1 + 1, x0:x1 + 1][m] = col[m]
    return Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("glb")
    ap.add_argument("out")
    ap.add_argument("--height", type=float, default=1.72)
    ap.add_argument("--skirt", action="store_true")
    ap.add_argument("--female", action="store_true")
    ap.add_argument("--preview", default="")
    a = ap.parse_args()
    r = rig(a.glb, a.height, a.skirt, a.female)
    write(r, a.out)
    J = r["J"]
    print("rigged %s: %d vertices, crotch %.2f m, skirt %s, arm slices %s" % (os.path.basename(a.glb), len(r["P"]), r["info"]["crotch"],
                                                                             r["info"]["skirt"], r["info"]["arm_pts"]))
    print("  joints: " + ", ".join("%s %s" % (k, np.round(v, 2).tolist()) for k, v in J.items() if k in ("Hips", "UpperArm.R", "Hand.R", "LowerLeg.R", "Foot.R")))
    if a.preview:
        os.makedirs(a.preview, exist_ok=True)
        preview(r, os.path.join(a.preview, os.path.basename(a.out).replace(".bytes", ".png")))


if __name__ == "__main__":
    main()
