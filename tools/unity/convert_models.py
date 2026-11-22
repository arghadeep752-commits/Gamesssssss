#!/usr/bin/env python3
"""Turns the Hyper3D Rodin models into files the Unity project builds from.

    convert_models.py --rodin DIR --models tools/rodin/models.json --out UNITY_PROJECT [--preview DIR]

  Assets/Resources/Gen/Chars/<name>.bytes      rigged + animated character (tools/rig/autorig.py)
  Assets/Resources/Gen/Vehicles/<name>.bytes   body mesh in metres (front = +Z, wheels on the ground at y = 0)
  Assets/Resources/Gen/Weapons/<name>.bytes    weapon mesh with its grip at the origin, barrel / blade along +Z
  Assets/Resources/Gen/<kind>/<name>_albedo.png, _normal.png, _mr.png   the model's own textures
  Assets/Resources/models.json        per model: sizes, wheels, seats, exits, lights, grip and muzzle points ...
"""
import argparse
import io
import json
import math
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "rig"))
import autorig  # noqa: E402

WHEEL_R = {"car_hatch": 0.30, "car_sedan": 0.31, "car_suv": 0.38, "auto_rickshaw": 0.22, "e_rickshaw": 0.25, "bus": 0.50, "truck": 0.50,
           "police_jeep": 0.37, "sports_car": 0.33, "motorbike": 0.33, "scooter": 0.24, "van": 0.29}
TYRE_W = {"bike": 0.11, "trike": 0.13, "car": 0.21}
GRIP = {"revolver": 0.22, "pistol": 0.25, "smg": 0.40, "shotgun": 0.27, "bat": 0.07, "knife": 0.14, "ak47": 0.36, "sniper": 0.34}
TEX_MAX = {"character": 1024, "vehicle": 1024, "weapon": 512, "wheel": 512, "prop": 512, "building": 1024}


def load(path):
    P, N, UV, I, tex = autorig.load_glb(path)
    return autorig.to_unity(P, N, UV, I) + (tex,)


def save_tex(tex, out_dir, name, kind):
    from PIL import Image
    files = {}
    for key, (data, mime) in tex.items():
        im = Image.open(io.BytesIO(data))
        m = TEX_MAX[kind]
        if max(im.size) > m:
            im = im.resize((m, m), Image.LANCZOS)
        fn = "%s_%s.png" % (name, key)
        if key == "albedo":
            im = im.convert("RGBA" if im.mode in ("RGBA", "LA") else "RGB")
        else:
            im = im.convert("RGB")
        im.save(os.path.join(out_dir, fn))
        files[key] = fn
    return files


def write_mesh(path, P, N, UV, I):
    with open(path, "wb") as f:
        f.write(struct.pack("<iii", 0x534D4744, 1, len(P)))      # 'DGMS'
        f.write(np.asarray(P, "<f4").tobytes())
        f.write(np.asarray(N, "<f4").tobytes())
        f.write(np.asarray(UV, "<f4").tobytes())
        f.write(struct.pack("<i", I.size))
        f.write(np.asarray(I, "<i4").reshape(-1).tobytes())


# ------------------------------------------------------------------------------------------------- vehicles
def find_axles(P, cls, length, r):
    """Axle positions along Z from where the tyres touch the ground (lowest points on the outer sides)."""
    hw = (P[:, 0].max() - P[:, 0].min()) / 2
    outer = P[np.abs(P[:, 0]) > (0.0 if cls == "bike" else 0.35 * hw)] if cls != "bike" else P[np.abs(P[:, 0]) < 0.25 * hw + 0.05]
    zs = np.arange(P[:, 2].min(), P[:, 2].max(), 0.02)
    low = []
    for z in zs:
        sel = outer[np.abs(outer[:, 2] - z) < 0.012]
        low.append(sel[:, 1].min() if len(sel) else 9.0)
    low = np.array(low)
    touch = low < 0.035
    ranges = []
    k = 0
    while k < len(zs):
        if touch[k]:
            j = k
            while j < len(zs) and touch[j]:
                j += 1
            ranges.append((zs[k], zs[j - 1]))
            k = j
        else:
            k += 1
    centres = [(a + b) / 2 for a, b in ranges if (b - a) < 3 * r]
    # merge contacts that belong to one tyre
    merged = []
    for c in sorted(centres):
        if merged and c - merged[-1][-1] < 1.2 * r:
            merged[-1].append(c)
        else:
            merged.append([c])
    axles = [float(np.mean(m)) for m in merged]
    return axles


def vehicle(name, spec, P, N, UV, I):
    cls = spec.get("cls", "car")
    L0 = spec["length"]
    s_len = L0 / (P[:, 2].max() - P[:, 2].min())
    s = s_len
    fit = spec.get("fit")
    if fit:
        axis = {"width": 0, "height": 1, "length": 2}[fit[0]]
        s = fit[1] / (P[:, axis].max() - P[:, axis].min())
    P = P * s
    L = float(P[:, 2].max() - P[:, 2].min())
    rscale = s / s_len
    P[:, 1] -= P[:, 1].min()
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2
    P[:, 2] -= (P[:, 2].max() + P[:, 2].min()) / 2
    W = float(P[:, 0].max() - P[:, 0].min())
    H = float(P[:, 1].max())
    info = {"name": name, "cls": cls, "length": round(L, 3), "width": round(W, 3), "height": round(H, 3), "mass": spec.get("mass", 1000),
            "top": spec.get("top", 120), "police": bool(spec.get("police", False))}
    wheels = []
    if cls in ("car", "trike", "bike"):
        r = round(WHEEL_R.get(name, 0.3) * rscale, 3)
        axles = find_axles(P, cls, L, r)
        if cls == "trike":
            # the single front wheel sits in the middle: look for its ground contact there
            front = find_axles(P, "bike", L, r)
            rear = [z for z in axles if z < 0.1 * L]
            fz = [z for z in front if z > 0.1 * L]
            if rear and fz:
                axles = [min(rear), max(fz)]
        if len(axles) < 2:
            axles = [-0.32 * L, 0.32 * L] if cls != "bike" else [-0.36 * L, 0.36 * L]
            info["axles_guessed"] = True
        axles = sorted(axles)
        front, rear = axles[-1], axles[0]
        tw = TYRE_W[cls]
        for az in axles:
            is_front = az == front
            near = P[(np.abs(P[:, 2] - az) < r * 0.7) & (P[:, 1] > r * 0.3) & (P[:, 1] < r * 1.7)]
            if cls == "bike" or (cls == "trike" and is_front):
                wheels.append({"x": 0.0, "y": r, "z": round(az, 3), "r": r, "w": tw, "steer": is_front, "drive": not is_front})
                continue
            for sgn in (1, -1):
                side = near[near[:, 0] * sgn > 0]
                xo = float(np.abs(side[:, 0]).max()) if len(side) else W / 2 - 0.05
                wheels.append({"x": round(sgn * max(0.2, xo - tw / 2 - 0.005), 3), "y": r, "z": round(az, 3), "r": r, "w": tw,
                               "steer": bool(is_front), "drive": not is_front or name in ("car_suv", "police_jeep")})
        info["wheelbase"] = round(front - rear, 3)
    info["wheels"] = wheels
    # driver: India drives on the left, so cars are right-hand drive (the seat is on the right, +X)
    seat = {"car": (0.27 * W, 0.42 * H, 0.04 * L), "bike": (0.0, 0.72 if name == "motorbike" else 0.68, -0.08 * L),
            "trike": (0.0, 0.62, 0.12 * L), "heli": (0.24, 0.82, 0.22 * L), "boat": (0.18, 0.62, -0.12 * L)}[cls]
    if name == "bus":
        seat = (0.32 * W, 1.25, 0.42 * L)
    if name == "truck":
        seat = (0.28 * W, 1.45, 0.38 * L)
    if name == "sports_car":
        seat = (0.24 * W, 0.32 * H, -0.02 * L)
    info["seat"] = [round(v, 3) for v in seat]
    info["exit"] = [round(W / 2 + 0.7, 3) if cls not in ("bike",) else 0.8, 0.0, round(seat[2], 3)]
    info["open"] = cls in ("bike", "trike", "boat")            # the driver can be seen
    info["lights"] = [[round(sx * 0.33 * W, 3), round(0.36 * H if cls == "car" else 0.6 * H, 3), round(L / 2 - 0.08, 3)] for sx in (1, -1)]
    if cls == "bike":
        info["lights"] = [[0.0, round(0.62 * H, 3), round(L / 2 - 0.15, 3)]]
    if cls == "heli":
        top = P[P[:, 1] > 0.85 * H]
        info["rotor"] = [round(float(np.median(top[:, 0])), 3), round(float(top[:, 1].max()), 3), round(float(np.median(top[:, 2])), 3), round(0.46 * L, 3)]
        tail = P[P[:, 2] < P[:, 2].min() + 0.1 * L]
        info["tail_rotor"] = [round(float(tail[:, 0].max()) + 0.05, 3), round(float(np.median(tail[:, 1])), 3), round(float(P[:, 2].min()) + 0.4, 3), 0.75]
    if cls == "boat":
        info["waterline"] = round(0.32 * H, 3)
        info["motor"] = [0.0, round(0.3 * H, 3), round(float(P[:, 2].min()) + 0.2, 3)]
    info["box"] = [round(W * 0.92, 3), round(H * (0.85 if cls == "car" else 0.9), 3), round(L * 0.94, 3)]
    return P, info


def wheel_mesh(P, N, UV, I):
    """Unit wheel: radius 1, axle along X (glTF Z), outer face towards +X."""
    # in the Rodin model the axle is glTF Z (still Z in Unity space): turn it to X (outer face at +X)
    R = np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]], float)           # (x, y, z) -> (z, y, -x)
    P = P @ R.T
    N = N @ R.T
    c = (P.max(0) + P.min(0)) / 2
    P -= c
    rad = max(P[:, 1].max(), P[:, 2].max())
    P /= rad
    return P, N, {"width": round(float(P[:, 0].max() - P[:, 0].min()), 3)}


# ------------------------------------------------------------------------------------------------- weapons
def weapon(name, spec, P, N, UV, I):
    def rotx(P, deg):
        a = math.radians(deg)
        c, s = math.cos(a), math.sin(a)
        Rm = np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
        return P @ Rm.T
    if name == "bat":
        P, N = rotx(P, 90), rotx(N, 90)          # fat end (+Y) -> forward (+Z)
    if name == "knife":
        P, N = rotx(P, -90), rotx(N, -90)        # blade (-Y) -> forward (+Z)
    L = spec["length"]
    s = L / (P[:, 2].max() - P[:, 2].min())
    P = P * s
    zmin, zmax = P[:, 2].min(), P[:, 2].max()
    ymin, ymax = P[:, 1].min(), P[:, 1].max()
    gz = zmin + GRIP.get(name, 0.3) * (zmax - zmin)
    win = P[np.abs(P[:, 2] - gz) < 0.03 * L + 0.01]
    if name in ("bat", "knife"):
        gy = float(np.median(win[:, 1])) if len(win) else 0.0
        gx = float(np.median(win[:, 0])) if len(win) else 0.0
    else:
        low = win[win[:, 1] < ymin + 0.65 * (ymax - ymin)]
        gy = float(np.median(low[:, 1])) if len(low) else ymin + 0.3 * (ymax - ymin)
        gx = float(np.median(low[:, 0])) if len(low) else 0.0
    grip = np.array([gx, gy, gz])
    front = P[P[:, 2] > zmax - 0.02]
    muzzle = np.array([float(np.median(front[:, 0])), float(np.median(front[:, 1])), float(zmax)])
    P = P - grip
    return P, N, {"name": name, "length": L, "muzzle": [round(v, 4) for v in (muzzle - grip)], "height": round(float(ymax - ymin), 3)}


# ------------------------------------------------------------------------------------------------- props and buildings
def prop(name, spec, P, N):
    """Street props and Indian shop-house buildings: real size, standing on y = 0, centred, front towards +Z."""
    kind, val = spec.get("size", ["height", 2.0])
    ext = P.max(0) - P.min(0)
    if kind == "height":
        s = val / max(1e-6, ext[1])
    else:
        s = val / max(1e-6, max(ext[0], ext[2]))
    P = P * s
    P[:, 1] -= P[:, 1].min()
    P[:, 0] -= (P[:, 0].max() + P[:, 0].min()) / 2
    P[:, 2] -= (P[:, 2].max() + P[:, 2].min()) / 2
    size = P.max(0) - P.min(0)
    return P, N, {"name": name, "kind": spec["kind"], "size": [round(float(v), 3) for v in size]}


# ------------------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--rodin", required=True)
    ap.add_argument("--models", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", default="")
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    man = json.load(open(a.models))["models"]
    files = {f.split("__")[0]: os.path.join(a.rodin, f) for f in os.listdir(a.rodin) if f.endswith(".glb") and "__" in f}
    out_meta = {"characters": {}, "vehicles": {}, "weapons": {}, "props": {}, "wheel": None}
    dirs = {k: os.path.join(a.out, "Assets", "Resources", "Gen", k) for k in ("Chars", "Vehicles", "Weapons", "Props")}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(a.out, "Assets", "Resources"), exist_ok=True)
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
                autorig.write(r, os.path.join(dirs["Chars"], name + ".bytes"))
                tex = save_tex(r["tex"], dirs["Chars"], name, kind)
                out_meta["characters"][name] = {"role": spec.get("role"), "outfit": spec.get("outfit"), "height": spec.get("height"),
                                                "female": spec.get("sex") == "f", "textures": tex, "arms": r["info"].get("arms", True)}
                print("character %-14s %d vertices, %s" % (name, len(r["P"]), {k: v for k, v in r["info"].items() if k in ("crotch", "skirt", "arms")}))
                if a.preview:
                    autorig.preview(r, os.path.join(a.preview, "rig_%s.png" % name), clips=("walk", "run", "aim_pistol", "drive"))
            else:
                P, N, UV, I, tex = load(path)
                if kind == "vehicle":
                    P, info = vehicle(name, spec, P, N, UV, I)
                    write_mesh(os.path.join(dirs["Vehicles"], name + ".bytes"), P, N, UV, I)
                    info["textures"] = save_tex(tex, dirs["Vehicles"], name, kind)
                    out_meta["vehicles"][name] = info
                    print("vehicle   %-14s %.2f x %.2f x %.2f m, %d wheels %s" % (name, info["width"], info["height"], info["length"], len(info["wheels"]),
                                                                              "(guessed)" if info.get("axles_guessed") else ""))
                    if a.preview:
                        preview_vehicle(P, I, UV, tex, info, os.path.join(a.preview, "veh_%s.png" % name))
                elif kind == "wheel":
                    P, N, info = wheel_mesh(P, N, UV, I)
                    write_mesh(os.path.join(dirs["Vehicles"], "wheel.bytes"), P, N, UV, I)
                    info["textures"] = save_tex(tex, dirs["Vehicles"], "wheel", kind)
                    out_meta["wheel"] = info
                    print("wheel     width ratio %.3f" % info["width"])
                elif kind in ("prop", "building"):
                    P, N, info = prop(name, spec, P, N)
                    write_mesh(os.path.join(dirs["Props"], name + ".bytes"), P, N, UV, I)
                    info["textures"] = save_tex(tex, dirs["Props"], name, kind)
                    out_meta["props"][name] = info
                    print("%-9s %-14s %.1f x %.1f x %.1f m, %d triangles" % (kind, name, info["size"][0], info["size"][1], info["size"][2], I.size // 3))
                elif kind == "weapon":
                    P, N, info = weapon(name, spec, P, N, UV, I)
                    write_mesh(os.path.join(dirs["Weapons"], name + ".bytes"), P, N, UV, I)
                    info["textures"] = save_tex(tex, dirs["Weapons"], name, kind)
                    out_meta["weapons"][name] = info
                    print("weapon    %-14s muzzle %s" % (name, info["muzzle"]))
        except Exception as e:      # noqa: BLE001
            import traceback
            traceback.print_exc()
            print("FAILED", name, e)
    with open(os.path.join(a.out, "Assets", "Resources", "models.json"), "w") as f:
        json.dump(out_meta, f, indent=1)


def preview_vehicle(P, I, UV, tex, info, out):
    from PIL import Image, ImageDraw
    t = np.asarray(Image.open(io.BytesIO(tex["albedo"][0])).convert("RGB"), np.float32) / 255 if "albedo" in tex else None
    k = min(1.0, 4.0 / max(info["length"], 1e-3))
    im = autorig.render_side(P * k, I, UV, t, view="side", W=420, H=200)
    d = ImageDraw.Draw(im)
    S = 200 / 2.1 * k
    for w in info["wheels"]:
        x = 420 / 2 + w["z"] * S
        y = 200 - 8 - w["y"] * S
        r = w["r"] * S
        d.ellipse([x - r, y - r, x + r, y + r], outline=(255, 0, 0), width=2)
    sx = 420 / 2 + info["seat"][2] * S
    sy = 200 - 8 - info["seat"][1] * S
    d.rectangle([sx - 3, sy - 3, sx + 3, sy + 3], fill=(0, 255, 0))
    im.save(out)


if __name__ == "__main__":
    main()
