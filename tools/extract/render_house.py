"""Renders the original house from AssetRipper's .glb of the scene, so the layout and the 3D style can be checked.

    blender -b -noaudio -P render_house.py -- <scene.glb> <out dir>

Writes into <out dir>:
  plan_<n>.jpg      top-down cut through each floor (camera 1.8 m above the floor, everything above it left out)
  outside_<n>.jpg   the house from outside
  spawn_<dir>.jpg   eye-height views from the player's start (if an object named like the player is found)
  room_<n>.jpg      eye-height views from spread-out spots on the floors
  enemy.jpg         a look at the enemy model (if one named like Granny is found)
  renders.json      camera positions of every image
Every surface shows its own texture colour (no lights needed), shaded with ambient occlusion so shapes read.
"""
import collections
import json
import math
import os
import re
import sys
import time

import bpy
from mathutils import Vector, Euler

argv = sys.argv[sys.argv.index("--") + 1:]
GLB, OUT = argv[0], argv[1]
os.makedirs(OUT, exist_ok=True)
T0 = time.time()


def log(*a):
    print("[render] %5.0fs" % (time.time() - T0), *a, flush=True)


bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=GLB)
scene = bpy.context.scene
meshes = [o for o in scene.objects if o.type == "MESH"]
log("imported %d mesh objects from %s" % (len(meshes), os.path.basename(GLB)))
if not meshes:
    raise SystemExit("no meshes in the glb")


# ---- flat 'texture colour x ambient occlusion' look ---------------------------------------------------------------
def flatten(mat):
    if mat is None:
        return
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next((n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"), None)
    out = next((n for n in nt.nodes if n.type == "OUTPUT_MATERIAL"), None) or nt.nodes.new("ShaderNodeOutputMaterial")
    color_src, alpha_src, base = None, None, (0.8, 0.8, 0.8, 1.0)
    alpha_val = 1.0
    if bsdf is not None:
        bc = bsdf.inputs["Base Color"]
        base = tuple(bc.default_value)
        if bc.is_linked:
            color_src = bc.links[0].from_socket
        al = bsdf.inputs.get("Alpha")
        if al is not None:
            alpha_val = al.default_value
            if al.is_linked:
                alpha_src = al.links[0].from_socket
    ao = nt.nodes.new("ShaderNodeAmbientOcclusion")
    ao.samples = 8
    ao.inputs["Distance"].default_value = 0.6
    if color_src is not None:
        nt.links.new(color_src, ao.inputs["Color"])
    else:
        ao.inputs["Color"].default_value = base
    soft = nt.nodes.new("ShaderNodeMath")
    soft.operation = "MULTIPLY_ADD"
    soft.inputs[1].default_value = 0.6
    soft.inputs[2].default_value = 0.4
    nt.links.new(ao.outputs["AO"], soft.inputs[0])
    em = nt.nodes.new("ShaderNodeEmission")
    if color_src is not None:
        nt.links.new(color_src, em.inputs["Color"])
    else:
        em.inputs["Color"].default_value = base
    nt.links.new(soft.outputs[0], em.inputs["Strength"])
    if alpha_src is not None or alpha_val < 0.999:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mix = nt.nodes.new("ShaderNodeMixShader")
        if alpha_src is not None:
            nt.links.new(alpha_src, mix.inputs["Fac"])
        else:
            mix.inputs["Fac"].default_value = alpha_val
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(em.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
    else:
        nt.links.new(em.outputs[0], out.inputs["Surface"])


for m in bpy.data.materials:
    try:
        flatten(m)
    except Exception as e:  # noqa: BLE001
        log("material", m.name, "kept as is:", e)
default_mat = bpy.data.materials.new("untextured")
default_mat.use_nodes = True
flatten(default_mat)
for o in meshes:
    if not o.material_slots:
        o.data.materials.append(default_mat)

world = bpy.data.worlds.new("sky")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.55, 0.62, 0.70, 1.0)
scene.world = world
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 16
scene.cycles.use_denoising = True
try:
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
except Exception:  # noqa: BLE001
    pass
scene.cycles.max_bounces = 1
scene.cycles.transparent_max_bounces = 12
scene.view_settings.view_transform = "Standard"
scene.render.image_settings.file_format = "JPEG"
scene.render.image_settings.quality = 85
scene.render.threads_mode = "AUTO"

cam_data = bpy.data.cameras.new("cam")
cam = bpy.data.objects.new("cam", cam_data)
scene.collection.objects.link(cam)
scene.camera = cam
depsgraph = bpy.context.evaluated_depsgraph_get()
RENDERS = []


def render(name, w, h, note=""):
    scene.render.resolution_x, scene.render.resolution_y = w, h
    scene.render.filepath = os.path.join(OUT, name + ".jpg")
    t = time.time()
    bpy.ops.render.render(write_still=True)
    RENDERS.append({"file": name + ".jpg", "camera": [round(v, 2) for v in cam.location],
                    "rotation_deg": [round(math.degrees(a), 1) for a in cam.rotation_euler],
                    "ortho": cam_data.type == "ORTHO", "note": note})
    log("%s.jpg (%.0fs) %s" % (name, time.time() - t, note))


def ray(origin, direction, dist=60.0):
    hit, loc, normal, _i, obj, _m = scene.ray_cast(depsgraph, origin, direction.normalized(), distance=dist)
    return (loc, normal, obj) if hit else (None, None, None)


# ---- object boxes and floor levels ---------------------------------------------------------------------------------
boxes = []
for o in meshes:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    boxes.append((o, lo, hi))


def house_region(bxs):
    """The house and its yard: the densest cluster of objects (far-away sets, terrain and sky left out)."""
    # objects left at the world origin (skinned meshes in bind pose, unplaced parts) are not the house
    small = [b for b in bxs if (b[2] - b[1]).length < 120 and ((b[1] + b[2]) / 2).length > 1.5]
    pts = [((lo.x + hi.x) / 2, (lo.y + hi.y) / 2) for _o, lo, hi in small]
    if not pts:
        return bxs, None
    cells = collections.Counter((math.floor(x / 8), math.floor(y / 8)) for x, y in pts)
    best = max(cells, key=lambda k: sum(cells.get((k[0] + i, k[1] + j), 0) for i in (-1, 0, 1) for j in (-1, 0, 1)))
    c = ((best[0] + 0.5) * 8, (best[1] + 0.5) * 8)
    for _ in range(8):
        near = [p for p in pts if math.hypot(p[0] - c[0], p[1] - c[1]) < 30]
        if not near:
            break
        c = (sum(p[0] for p in near) / len(near), sum(p[1] for p in near) / len(near))
    d = sorted(math.hypot(p[0] - c[0], p[1] - c[1]) for p in pts if math.hypot(p[0] - c[0], p[1] - c[1]) < 80)
    r = max(10.0, d[int(0.9 * (len(d) - 1))] + 3.0) if d else 40.0
    inner = [b for b, p in zip(small, pts) if math.hypot(p[0] - c[0], p[1] - c[1]) <= r]
    return inner, (c, r)


house, hreg = house_region(boxes)
if hreg:
    log("house region: centre (%.1f, %.1f), radius %.1f m, %d of %d objects" % (hreg[0][0], hreg[0][1], hreg[1], len(house), len(boxes)))


def in_house(v):
    return hreg is None or math.hypot(v.x - hreg[0][0], v.y - hreg[0][1]) <= hreg[1]

up_area = collections.Counter()
floor_spots = collections.defaultdict(list)
for o in meshes:
    mw = o.matrix_world
    nm = mw.to_3x3().inverted_safe().transposed()
    k = abs(mw.to_3x3().determinant()) ** (2.0 / 3.0)
    me = o.data
    if len(me.polygons) > 400000:
        continue
    for p in me.polygons:
        n = (nm @ p.normal)
        if n.length == 0:
            continue
        n.normalize()
        if n.z > 0.9:
            c = mw @ p.center
            a = p.area * k
            if a > 400 or not in_house(c):
                continue
            lvl = round(c.z * 4) / 4
            up_area[lvl] += a
            if 0.3 < a < 400:
                floor_spots[lvl].append((c.copy(), a))
total = sum(up_area.values()) or 1.0
levels = []
for lvl, a in sorted(up_area.items(), key=lambda kv: -kv[1]):
    if a < 0.03 * total:
        break
    if all(abs(lvl - x) >= 2.0 for x in levels):
        levels.append(lvl)
    if len(levels) >= 5:
        break
levels.sort()
log("floor levels (m):", levels, "of", len(up_area), "heights")


def pct(vals, f):
    vals = sorted(vals)
    return vals[min(len(vals) - 1, max(0, int(f * len(vals))))]


def bounds(sel):
    return (Vector((pct([b[1].x for b in sel], .02), pct([b[1].y for b in sel], .02), pct([b[1].z for b in sel], .02))),
            Vector((pct([b[2].x for b in sel], .98), pct([b[2].y for b in sel], .98), pct([b[2].z for b in sel], .98))))


# ---- plans ----------------------------------------------------------------------------------------------------------
for i, lvl in enumerate(levels):
    sel = [b for b in house if b[1].z < lvl + 1.8 and b[2].z > lvl - 0.3]
    if len(sel) < 3:
        continue
    lo, hi = bounds(sel)
    pad = 1.5
    cam_data.type = "ORTHO"
    cam_data.ortho_scale = max(hi.x - lo.x, hi.y - lo.y) + 2 * pad
    cam_data.clip_start = 0.01
    cam_data.clip_end = 1.8 + 50.0
    cam.location = Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lvl + 1.8))
    cam.rotation_euler = Euler((0.0, 0.0, 0.0))
    render("plan_%d" % (i + 1), 1400, 1400, "floor at %.2f m, %.0f x %.0f m" % (lvl, hi.x - lo.x, hi.y - lo.y))

# ---- outside --------------------------------------------------------------------------------------------------------
lo, hi = bounds(house)
center = (lo + hi) / 2
diag = max((hi - lo).length, 8.0)
cam_data.type = "PERSP"
cam_data.lens = 30
cam_data.clip_start = 0.05
cam_data.clip_end = 2000
for i, az in enumerate((45, 225)):
    a, el = math.radians(az), math.radians(28)
    cam.location = center + Vector((math.cos(a) * math.cos(el), math.sin(a) * math.cos(el), math.sin(el))) * diag * 1.05
    cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()
    render("outside_%d" % (i + 1), 1280, 720, "azimuth %d" % az)


def eye_views(prefix, origin, dirs, lens=16, note=""):
    cam_data.type = "PERSP"
    cam_data.lens = lens
    cam_data.clip_start = 0.02
    for name, yaw in dirs:
        cam.location = origin
        cam.rotation_euler = Euler((math.radians(90), 0.0, math.radians(yaw)))
        render("%s_%s" % (prefix, name), 1280, 720, note)


def floor_below(p):
    loc, _n, _o = ray(p + Vector((0, 0, 0.3)), Vector((0, 0, -1)), 6.0)
    return loc.z if loc is not None else p.z


def best_yaw(origin):
    best, best_d = 0, -1.0
    for k in range(16):
        yaw = k * 22.5
        d = Vector((-math.sin(math.radians(yaw)), math.cos(math.radians(yaw)), 0.0))
        loc, _n, _o = ray(origin, d, 25.0)
        dist = (loc - origin).length if loc is not None else 25.0
        if dist > best_d:
            best, best_d = yaw, dist
    return best, best_d


# ---- player start ---------------------------------------------------------------------------------------------------
pat = re.compile(r"(^player$|fps|first ?person|playercontroller|^player[ _]|spawn|character ?controller)", re.I)
bad = re.compile(r"(trigger|sound|audio|canvas|text|light|ui|button|cam(era)?$|icon)", re.I)
cands = [o for o in scene.objects if pat.search(o.name) and not bad.search(o.name) and in_house(o.matrix_world.translation)]
cands.sort(key=lambda o: (o.name.lower() != "player", len(o.name)))
if cands:
    p = cands[0].matrix_world.translation.copy()
    eye = Vector((p.x, p.y, floor_below(p) + 1.6))
    log("player start: %s at %s" % (cands[0].name, tuple(round(v, 2) for v in eye)))
    eye_views("spawn", eye, (("north", 0), ("west", 90), ("south", 180), ("east", 270)), 16, "from " + cands[0].name)
else:
    log("no object named like the player found")

# ---- rooms: spread-out spots on each floor --------------------------------------------------------------------------
spots = []
for lvl in levels:
    for key, items in floor_spots.items():
        if abs(key - lvl) <= 0.3:
            spots += [c for c, _a in items]
inside = []
for c in [c for c in spots if in_house(c)][:6000]:
    above, _n, _o = ray(c + Vector((0, 0, 0.2)), Vector((0, 0, 1)), 4.5)
    if above is None:
        continue
    e = c + Vector((0, 0, 1.6))
    clear = min(((ray(e, Vector((math.cos(a), math.sin(a), 0)), 3.0)[0] or (e + Vector((3, 0, 0)))) - e).length
                for a in [k * math.pi / 4 for k in range(8)])
    if clear >= 1.0:
        inside.append(e)
chosen = []
if inside:
    chosen.append(min(inside, key=lambda v: (v - center).length))
    while len(chosen) < 8 and len(chosen) < len(inside):
        far = max(inside, key=lambda v: min((v - c).length for c in chosen))
        if min((far - c).length for c in chosen) < 2.5:
            break
        chosen.append(far)
log("room views:", len(chosen), "of", len(inside), "inside spots")
for i, e in enumerate(chosen):
    yaw, dist = best_yaw(e)
    eye_views("room_%d" % (i + 1), e, (("view", yaw),), 18, "at %s looking %.0f deg (%.1f m free)" % (tuple(round(v, 1) for v in e), yaw, dist))

# ---- the enemy ------------------------------------------------------------------------------------------------------
epat = re.compile(r"(granny|grandma|grandpa|enemy|nun|slendrina|monster|killer|ghost)", re.I)
enemies = [b for b in house if (epat.search(b[0].name) or (b[0].parent and epat.search(b[0].parent.name))) and 0.8 < (b[2].z - b[1].z) < 3.5]
if enemies:
    o, elo, ehi = max(enemies, key=lambda b: (b[2] - b[1]).length)
    c = (elo + ehi) / 2
    height = ehi.z - elo.z
    best, best_d = None, 0
    for k in range(12):
        a = k * math.pi / 6
        d = Vector((math.cos(a), math.sin(a), 0.0))
        loc, _n, _o = ray(c + d * 0.6, d, 6.0)
        dist = (loc - c).length if loc is not None else 6.0
        if dist > best_d:
            best, best_d = d, dist
    dist = min(max(height * 1.4, 1.6), max(best_d - 0.2, 1.0))
    cam_data.type = "PERSP"
    cam_data.lens = 35
    cam.location = c + best * dist + Vector((0, 0, height * 0.1))
    cam.rotation_euler = (c - cam.location).to_track_quat("-Z", "Y").to_euler()
    render("enemy", 1280, 720, "%s (%.2f m tall)" % (o.name, height))
else:
    log("no enemy-like object found")

with open(os.path.join(OUT, "renders.json"), "w") as f:
    json.dump({"glb": os.path.basename(GLB), "levels": levels, "renders": RENDERS}, f, indent=1)
log("done: %d images" % len(RENDERS))
