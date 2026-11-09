"""Chaya - the game icon, modelled, lit and rendered in Blender (Cycles).

    blender -b -P tools/logo/make_icon.py -- <rocketbox dir> <baked tex dir> <MX font .ttf> <out.png> [size]

Chaya's face fills the icon: ashen skin, black sunken eyes that glow red, blood tears, long black hair with sindoor in
the parting and a bindi, lit from below like a candle with a red rim from behind. An orange 3D "MX" sits in the lower
right corner, inside the area launchers never crop.
"""
import math
import os
import random
import sys
import time

import bpy
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
RB, TEX, FONT, OUT = (os.path.abspath(a) for a in argv[:4])
SIZE = int(argv[4]) if len(argv) > 4 else 1024
t0 = time.time()
rng = random.Random(11)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# ------------------------------------------------------------------------------------------------ Chaya
bpy.ops.import_scene.fbx(filepath=os.path.join(RB, "Medical_Female_01.fbx"), use_anim=False, ignore_leaf_bones=True)
arm = next(o for o in scene.objects if o.type == "ARMATURE")
body = next(o for o in scene.objects if o.type == "MESH")
print("imported", arm.name, body.name, [m.name for m in body.data.materials])


def img(path, non_color=False):
    im = bpy.data.images.load(path, check_existing=True)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    return im


def skin_material(name, color_png, normal_tga, sss=0.06, rough=0.55):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img(color_png)
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    if os.path.exists(normal_tga):
        nmt = nt.nodes.new("ShaderNodeTexImage")
        nmt.image = img(normal_tga, True)
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.inputs["Strength"].default_value = 0.8
        nt.links.new(nmt.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = rough
    for key in ("Subsurface Weight", "Subsurface"):
        if key in bsdf.inputs:
            bsdf.inputs[key].default_value = sss
            break
    if "Subsurface Radius" in bsdf.inputs:
        bsdf.inputs["Subsurface Radius"].default_value = (0.012, 0.004, 0.003)
    return m


def flat_material(name, color, rough=0.5, emit=None, strength=0.0, metal=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if emit is not None:
        for key in ("Emission Color", "Emission"):
            if key in bsdf.inputs:
                bsdf.inputs[key].default_value = (*emit, 1.0)
                break
        bsdf.inputs["Emission Strength"].default_value = strength
    return m


tex_dir = os.path.join(RB, "tex")
head_mat = skin_material("chaya_head", os.path.join(TEX, "head_chaya.png"), os.path.join(tex_dir, "f152_head_normal.tga"), 0.07, 0.5)
body_mat = skin_material("chaya_body", os.path.join(TEX, "body_chaya.png"), os.path.join(tex_dir, "f152_body_normal.tga"), 0.03, 0.7)
# lashes / brows / curly hair cards: alpha-cut, darkened to match the black hair
op = bpy.data.materials.new("chaya_opacity")
op.use_nodes = True
nt = op.node_tree
bsdf = nt.nodes["Principled BSDF"]
ot = nt.nodes.new("ShaderNodeTexImage")
ot.image = img(os.path.join(tex_dir, "f152_opacity_color.tga"))
mul = nt.nodes.new("ShaderNodeMixRGB")
mul.blend_type = "MULTIPLY"
mul.inputs["Fac"].default_value = 1.0
mul.inputs["Color2"].default_value = (0.12, 0.1, 0.1, 1.0)
nt.links.new(ot.outputs["Color"], mul.inputs["Color1"])
nt.links.new(mul.outputs["Color"], bsdf.inputs["Base Color"])
nt.links.new(ot.outputs["Alpha"], bsdf.inputs["Alpha"])
try:
    op.blend_method = "HASHED"
except Exception:       # noqa: BLE001
    pass
head_slot = 0
for i, slot in enumerate(body.material_slots):
    nm = (slot.material.name if slot.material else "").lower()
    if "head" in nm:
        slot.material = head_mat
        head_slot = i
    elif "opacity" in nm:
        slot.material = op
    else:
        slot.material = body_mat

# ------------------------------------------------------------------------------------------------ pose: arms down, head tilted
bpy.context.view_layer.update()
inv = arm.matrix_world.inverted().to_3x3()


def rotate_bone(name, target_dir_world=None, axis_world=None, angle=0.0):
    pb = arm.pose.bones.get(name)
    if pb is None:
        print("no bone", name)
        return
    M = pb.matrix.copy()
    head = M.translation.copy()
    if target_dir_world is not None:
        cur = (pb.tail - pb.head).normalized()
        R = cur.rotation_difference((inv @ target_dir_world).normalized()).to_matrix().to_4x4()
    else:
        R = Matrix.Rotation(angle, 4, (inv @ axis_world).normalized())
    pb.matrix = Matrix.Translation(head) @ R @ Matrix.Translation(-head) @ M
    bpy.context.view_layer.update()


def world_head(name):
    pb = arm.pose.bones[name]
    return arm.matrix_world @ pb.head


eyes0 = (world_head("Bip01 REye") + world_head("Bip01 LEye")) / 2
neck = world_head("Bip01 Head")
F = eyes0 - neck
F.z = 0.0
F.normalize()
U = Vector((0, 0, 1))
S = F.cross(U).normalized()
for side in ("L", "R"):
    sh = world_head("Bip01 %s UpperArm" % side)
    out = 1.0 if (sh - neck).dot(S) > 0 else -1.0
    rotate_bone("Bip01 %s UpperArm" % side, target_dir_world=(S * out * 0.22 - U + F * 0.05))
rotate_bone("Bip01 Head", axis_world=S, angle=math.radians(-7.0))       # chin down a little: looking up at you
rotate_bone("Bip01 Head", axis_world=F, angle=math.radians(9.0))        # and an uneasy tilt
E = (world_head("Bip01 REye") + world_head("Bip01 LEye")) / 2
eye_r, eye_l = world_head("Bip01 REye"), world_head("Bip01 LEye")
print("eyes at", tuple(round(c, 3) for c in E))

# head size from the posed mesh
deps = bpy.context.evaluated_depsgraph_get()
ev = body.evaluated_get(deps)
me = ev.to_mesh()
pts = []
for poly in me.polygons:
    if poly.material_index == head_slot:
        for vi in poly.vertices:
            p = body.matrix_world @ me.vertices[vi].co
            if p.z > E.z - 0.11:
                pts.append(p)
ev.to_mesh_clear()
# skull from the eyes (the head mesh also carries a bun, which would skew a bounding box)
k_scale = E.z / 1.612
H = E - F * (0.064 * k_scale) + U * (0.024 * k_scale)
R_HEAD = 0.088 * k_scale
# measure the real head (it carries a bun and curly hair cards) with rays, and fit the hair shell to it
deps = bpy.context.evaluated_depsgraph_get()


def probe(origin, direction):
    hit, loc, nor, idx, obj, mtx = scene.ray_cast(deps, origin, direction)
    return loc if hit and obj is not None and obj.name == body.name else None


_p = probe(H + U * 0.6, -U)
R_UP = (_p - H).dot(U) if _p else 0.105
_p = probe(H - F * 0.6 + U * 0.02, F)
R_BACK = (H - _p).dot(F) if _p else 0.1
_s = [abs((_q - H).dot(S)) for _q in (probe(H + S * 0.6 + U * 0.03, -S), probe(H - S * 0.6 + U * 0.03, S)) if _q]
R_SIDE = max(_s) if _s else 0.085
_p = probe(H + F * 0.6 + U * 0.06, -F)
R_FRONT = (_p - H).dot(F) if _p else 0.085
R_UP, R_BACK, R_SIDE, R_FRONT = (max(0.06, min(0.16, v)) for v in (R_UP, R_BACK, R_SIDE, R_FRONT))
print("head radii up %.3f back %.3f side %.3f front %.3f" % (R_UP, R_BACK, R_SIDE, R_FRONT))
print("head centre", tuple(round(c, 3) for c in H), "radius", round(R_HEAD, 3))

# ------------------------------------------------------------------------------------------------ glowing eyes
eye_mat = flat_material("eye_glow", (1.0, 0.03, 0.01), 0.4, (1.0, 0.03, 0.01), 14.0)
for p in (eye_r, eye_l):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=0.0118, location=p + F * 0.004)
    o = bpy.context.active_object
    o.data.materials.append(eye_mat)
    bpy.ops.object.shade_smooth()
    lt = bpy.data.lights.new("eye_spill", "POINT")
    lt.energy = 0.25
    lt.color = (1.0, 0.08, 0.03)
    lt.shadow_soft_size = 0.004
    lo = bpy.data.objects.new("eye_spill", lt)
    lo.location = p + F * 0.02
    scene.collection.objects.link(lo)
    try:
        lo.visible_camera = False
    except Exception:       # noqa: BLE001
        pass

# ------------------------------------------------------------------------------------------------ long black hair
def sph(phi, elev, r):
    """A point on the measured head shell; r - R_HEAD is the offset above the scalp."""
    off = r - R_HEAD
    f = math.cos(elev) * math.cos(phi)
    sd = math.cos(elev) * math.sin(phi)
    u = math.sin(elev)
    p = H + F * (f * (R_FRONT if f > 0 else R_BACK)) + S * (sd * R_SIDE) + U * (u * (R_UP if u > 0 else R_SIDE * 0.95))
    n = (math.cos(elev) * (math.cos(phi) * F + math.sin(phi) * S) + math.sin(elev) * U)
    return p + n * off


def clear_face(p):
    """Keep a clean window over the face: no strand may cross in front of it."""
    d = p - E
    lat, fwd, up = d.dot(S), d.dot(F), d.dot(U)
    if -0.15 < up < 0.055 and fwd > -0.04 and abs(lat) < 0.078:
        lat = math.copysign(0.078, lat if abs(lat) > 1e-4 else 1.0)
        return E + S * lat + F * fwd + U * up
    return p


def hairline(phi_deg):
    a = abs(phi_deg)
    return 36.0 - 48.0 * (a / 90.0) if a <= 90 else -12.0 - 33.0 * ((a - 90.0) / 90.0)


strands = []
N = 9000
for i in range(N):
    z = 1 - 2 * (i + 0.5) / N
    phi = (i * 2.399963) % (2 * math.pi)
    if phi > math.pi:
        phi -= 2 * math.pi
    elev = math.asin(z)
    if math.degrees(elev) < hairline(math.degrees(phi)) + rng.uniform(-2, 2):
        continue
    pts_s = []
    front = abs(phi) < math.radians(75)
    phi_t = (math.copysign(math.radians(rng.uniform(70, 88)), phi if abs(phi) > 1e-3 else 1.0) if front else phi)
    e_end = math.radians(rng.uniform(-22, -10))
    nA = 9
    for k in range(nA):
        s = k / (nA - 1)
        sm = 1.0 - (1.0 - s) ** 2.6           # swing to the side early, before dropping past the face
        ph = phi + (phi_t - phi) * sm
        el = elev + (e_end - elev) * s
        pts_s.append(clear_face(sph(ph, el, R_HEAD + 0.004 + 0.016 * s)))
    q = pts_s[-1]
    outward = (q - H)
    outward.z = 0.0
    outward.normalize()
    L = rng.uniform(0.42, 0.72) * (1.0 if abs(phi) > math.radians(100) else 0.85)
    w1, w2 = rng.uniform(9, 16), rng.uniform(0, 6.28)
    side = outward.cross(U)
    nB = 12
    for k in range(1, nB + 1):
        t = k / nB
        p = q - U * (L * t) + outward * (0.012 + 0.05 * t ** 1.3) + side * (0.006 * math.sin(w1 * t + w2) * t)
        if abs(phi) < math.radians(120):
            p += F * (0.03 * t * t)          # side locks fall forward over the shoulders, framing the face
        pts_s.append(clear_face(p))
    strands.append(pts_s)
print("hair strands", len(strands))
hair_mat = bpy.data.materials.new("hair")
hair_mat.use_nodes = True
hn = hair_mat.node_tree
for n in list(hn.nodes):
    if n.type != "OUTPUT_MATERIAL":
        hn.nodes.remove(n)
try:
    hb = hn.nodes.new("ShaderNodeBsdfHairPrincipled")
    try:
        hb.parametrization = "MELANIN"
    except Exception:       # noqa: BLE001
        pass
    for key, val in (("Melanin", 1.0), ("Melanin Redness", 0.05), ("Roughness", 0.28), ("Radial Roughness", 0.35), ("Coat", 0.1)):
        if key in hb.inputs:
            hb.inputs[key].default_value = val
    hn.links.new(hb.outputs[0], hn.nodes["Material Output"].inputs["Surface"])
except Exception as ex:     # noqa: BLE001
    print("hair BSDF fallback:", ex)
    pb_ = hn.nodes.new("ShaderNodeBsdfPrincipled")
    pb_.inputs["Base Color"].default_value = (0.01, 0.008, 0.008, 1)
    pb_.inputs["Roughness"].default_value = 0.35
    hn.links.new(pb_.outputs[0], hn.nodes["Material Output"].inputs["Surface"])
made = False
try:
    hc = bpy.data.hair_curves.new("ChayaHair")
    hc.add_curves([len(s) for s in strands])
    flat = [c for s in strands for p in s for c in (p.x, p.y, p.z)]
    hc.position_data.foreach_set("vector", flat)
    rad = hc.attributes.get("radius") or hc.attributes.new("radius", "FLOAT", "POINT")
    rv = []
    for s in strands:
        n = len(s)
        rv += [0.00055 * (1.0 - 0.6 * k / (n - 1)) for k in range(n)]
    rad.data.foreach_set("value", rv)
    hc.materials.append(hair_mat)
    ho = bpy.data.objects.new("ChayaHair", hc)
    scene.collection.objects.link(ho)
    made = True
    print("hair: curves object")
except Exception as ex:     # noqa: BLE001
    print("hair curves unavailable, using bevelled curves:", ex)
if not made:
    cu = bpy.data.curves.new("ChayaHair", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = 0.0005
    cu.bevel_resolution = 1
    for s in strands[::2]:
        sp = cu.splines.new("POLY")
        sp.points.add(len(s) - 1)
        for k, p in enumerate(s):
            sp.points[k].co = (p.x, p.y, p.z, 1.0)
    cu.materials.append(hair_mat)
    scene.collection.objects.link(bpy.data.objects.new("ChayaHair", cu))

# ------------------------------------------------------------------------------------------------ sindoor and bindi
sind = flat_material("sindoor", (0.62, 0.0, 0.02), 0.6, (0.5, 0.0, 0.01), 0.4)
cu = bpy.data.curves.new("sindoor", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.0016
sp = cu.splines.new("POLY")
n = 14
sp.points.add(n - 1)
for k in range(n):
    el = math.radians(34 + 46 * k / (n - 1))
    p = sph(0.0, el, R_HEAD + 0.006)
    sp.points[k].co = (p.x, p.y, p.z, 1.0)
cu.materials.append(sind)
scene.collection.objects.link(bpy.data.objects.new("sindoor", cu))
deps = bpy.context.evaluated_depsgraph_get()
hit, loc, nor, _, _, _ = scene.ray_cast(deps, E + U * 0.037 + F * 0.25, -F)
if hit:
    bpy.ops.mesh.primitive_cylinder_add(vertices=24, radius=0.0042, depth=0.0009, location=loc + nor * 0.0004)
    bd = bpy.context.active_object
    bd.rotation_euler = nor.to_track_quat("Z", "Y").to_euler()
    bd.data.materials.append(flat_material("bindi", (0.55, 0.0, 0.02), 0.35))
    print("bindi placed")

# ------------------------------------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new("cam")
cam_d.lens = 85.0
cam_d.sensor_width = 36.0
cam_d.sensor_fit = "AUTO"
cam = bpy.data.objects.new("cam", cam_d)
scene.collection.objects.link(cam)
scene.camera = cam
T = E - U * 0.035
cam.location = T + F * 0.86 - U * 0.035
cam.rotation_euler = (T - cam.location).to_track_quat("-Z", "Y").to_euler()
bpy.context.view_layer.update()
cam_fwd = (cam.matrix_world.to_3x3() @ Vector((0, 0, -1))).normalized()
cam_up = (cam.matrix_world.to_3x3() @ Vector((0, 1, 0))).normalized()
cam_right = (cam.matrix_world.to_3x3() @ Vector((1, 0, 0))).normalized()


def area(name, loc, target, size, power, color):
    ld = bpy.data.lights.new(name, "AREA")
    ld.shape = "DISK"
    ld.size = size
    ld.energy = power
    ld.color = color
    lo = bpy.data.objects.new(name, ld)
    lo.location = loc
    lo.rotation_euler = (target - loc).to_track_quat("-Z", "Y").to_euler()
    scene.collection.objects.link(lo)
    try:
        lo.visible_camera = False
    except Exception:       # noqa: BLE001
        pass
    return lo


area("key_candle", T + F * 0.42 - U * 0.33 + S * 0.06, T, 0.22, 26.0, (1.0, 0.55, 0.3))
area("fill", T + F * 0.95 + U * 0.25 - S * 0.15, T, 0.7, 7.0, (0.62, 0.68, 0.85))
for sgn in (1, -1):
    area("rim", H - F * 0.42 + S * 0.33 * sgn + U * 0.22, H + U * 0.02, 0.35, 32.0, (1.0, 0.08, 0.03))
area("top", H + U * 0.6 + F * 0.15, H, 0.5, 9.0, (0.8, 0.3, 0.25))

# backdrop: a red glow behind her head fading to black
bpy.ops.mesh.primitive_plane_add(size=3.0, location=H - F * 0.95)
bd = bpy.context.active_object
bd.rotation_euler = (-F).to_track_quat("-Z", "Y").to_euler()
bm = bpy.data.materials.new("backdrop")
bm.use_nodes = True
bnt = bm.node_tree
for nd in list(bnt.nodes):
    if nd.type != "OUTPUT_MATERIAL":
        bnt.nodes.remove(nd)
tc = bnt.nodes.new("ShaderNodeTexCoord")
gr = bnt.nodes.new("ShaderNodeTexGradient")
gr.gradient_type = "SPHERICAL"
mp = bnt.nodes.new("ShaderNodeMapping")
mp.inputs["Scale"].default_value = (1.6, 1.6, 1.6)
ramp = bnt.nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.elements[0].color = (0.0, 0.0, 0.0, 1)
ramp.color_ramp.elements[1].position = 0.75
ramp.color_ramp.elements[1].color = (0.3, 0.006, 0.004, 1)
nz = bnt.nodes.new("ShaderNodeTexNoise")
nz.inputs["Scale"].default_value = 4.0
mix = bnt.nodes.new("ShaderNodeMixRGB")
mix.blend_type = "MULTIPLY"
mix.inputs["Fac"].default_value = 0.45
em = bnt.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 0.6
bnt.links.new(tc.outputs["Object"], mp.inputs["Vector"])
bnt.links.new(mp.outputs["Vector"], gr.inputs["Vector"])
bnt.links.new(gr.outputs["Fac"], ramp.inputs["Fac"])
bnt.links.new(ramp.outputs["Color"], mix.inputs["Color1"])
bnt.links.new(nz.outputs["Color"], mix.inputs["Color2"])
bnt.links.new(mix.outputs["Color"], em.inputs["Color"])
bnt.links.new(em.outputs["Emission"], bnt.nodes["Material Output"].inputs["Surface"])
bd.data.materials.append(bm)
world = bpy.data.worlds.new("w")
world.color = (0.0, 0.0, 0.0)
scene.world = world

# ------------------------------------------------------------------------------------------------ orange MX
mx_mat = flat_material("mx_orange", (1.0, 0.3, 0.0), 0.35, (1.0, 0.28, 0.0), 0.35)
fc = bpy.data.curves.new("MX", "FONT")
fc.body = "MX"
try:
    fc.font = bpy.data.fonts.load(FONT)
except Exception as ex:     # noqa: BLE001
    print("MX font fallback:", ex)
fc.align_x = "CENTER"
fc.align_y = "CENTER"
fc.size = 0.052
fc.extrude = 0.003
fc.bevel_depth = 0.0016
fc.bevel_resolution = 2
fc.materials.append(mx_mat)
mx = bpy.data.objects.new("MX", fc)
scene.collection.objects.link(mx)
d_mx = 0.5
half = d_mx * math.tan(math.atan(18.0 / 85.0))
mx.matrix_world = Matrix.Translation(cam.location + cam_fwd * d_mx + cam_right * (0.70 * half) + cam_up * (-0.72 * half)) @ cam.matrix_world.to_3x3().to_4x4()

# ------------------------------------------------------------------------------------------------ render
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.render.resolution_x = SIZE
scene.render.resolution_y = SIZE
scene.render.resolution_percentage = 100
# this Blender build has no OpenImageDenoise: more samples, adaptive sampling stops early where it is clean
scene.cycles.use_denoising = False
scene.cycles.samples = 520
try:
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.015
except Exception:       # noqa: BLE001
    pass
try:
    scene.cycles.filter_width = 1.7
except Exception:       # noqa: BLE001
    pass
scene.cycles.max_bounces = 6
scene.cycles.transparent_max_bounces = 16
for vt, look in (("AgX", "AgX - Punchy"), ("AgX", "None"), ("Filmic", "High Contrast"), ("Filmic", "None")):
    try:
        scene.view_settings.view_transform = vt
        scene.view_settings.look = look
        break
    except Exception:       # noqa: BLE001
        continue
scene.view_settings.exposure = 0.0
# glow on the eyes and the MX
scene.use_nodes = True
tree = scene.node_tree
rl = tree.nodes.get("Render Layers") or tree.nodes.new("CompositorNodeRLayers")
comp = tree.nodes.get("Composite") or tree.nodes.new("CompositorNodeComposite")
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 2.5
glare.size = 8
tree.links.new(rl.outputs["Image"], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], comp.inputs["Image"])
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"
scene.render.filepath = OUT
os.makedirs(os.path.dirname(os.path.abspath(OUT)), exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.splitext(OUT)[0] + ".blend")
print("rendering %dx%d ..." % (SIZE, SIZE))
bpy.ops.render.render(write_still=True)
print("done in %.0fs -> %s" % (time.time() - t0, OUT))
