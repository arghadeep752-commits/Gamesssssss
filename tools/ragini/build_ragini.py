"""Builds Ragini - the chudail - in Blender, from scratch, and exports her for Godot.

    blender -b -noaudio -P tools/ragini/build_ragini.py -- OUT_DIR [--tex DOWNLOADED_TEXTURES] [--quick]

1. sculpt   : her body, head, teeth and eyes are signed-distance sculptures (anatomy.py, head.py) meshed at 2.5 mm
2. clothe   : saree skirt with front pleats and a torn hem, pallu over the left shoulder (garments.py)
3. groom    : long black hair as strand cards grown over the skull (hair.py)
4. dress    : bangles, nose ring, mangalsutra, payal with ghungroo bells, her wooden scale (accessories.py)
5. retopo   : a game mesh decimated from the sculpture, UV unwrapped, normal map baked from the sculpture in Cycles
6. paint    : skin, blouse, saree and scale textures painted procedurally (textures.py) + baked ambient occlusion
7. rig      : armature, skin weights from the sculpt itself, idle / walk / run / attack / scream / grab animations
8. export   : ragini.glb (+ ragini.blend, preview renders, build_log.txt)
"""
import json
import math
import os
import sys
import time
import traceback

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "common"))
import sdf  # noqa: E402
import anatomy  # noqa: E402
import garments  # noqa: E402
import hair  # noqa: E402
import accessories  # noqa: E402
import textures  # noqa: E402
import animate  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else ["build/ragini"]
OUT = os.path.abspath(argv[0])
TEX = os.path.abspath(argv[argv.index("--tex") + 1]) if "--tex" in argv else None
QUICK = "--quick" in argv
os.makedirs(OUT, exist_ok=True)
T0 = time.time()
_logf = open(os.path.join(OUT, "build_log.txt"), "w")


def log(*a):
    s = "[%6.1fs] " % (time.time() - T0) + " ".join(str(x) for x in a)
    print(s, flush=True)
    _logf.write(s + "\n")
    _logf.flush()


H_SCULPT = 0.0045 if QUICK else 0.0025
TEX_BODY = 1024 if QUICK else 2048
TARGET_TRIS = 16000

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
view_layer = bpy.context.view_layer
col_main = bpy.data.collections.new("Ragini")
scene.collection.children.link(col_main)


# ================================================================================================ helpers
def mesh_obj(name, V, T, UV=None, smooth=True, collection=None):
    """Blender object from numpy arrays. UV: per-vertex (n, 2) or per-corner (m*3, 2)."""
    me = bpy.data.meshes.new(name)
    me.from_pydata(np.asarray(V, float).tolist(), [], np.asarray(T, int).tolist())
    if UV is not None:
        UV = np.asarray(UV, float)
        uvl = me.uv_layers.new(name="UVMap")
        if len(UV) == len(V):
            per_loop = UV[np.asarray(T, int).ravel()]
        else:
            per_loop = UV
        uvl.data.foreach_set("uv", per_loop.astype(np.float32).ravel())
    me.polygons.foreach_set("use_smooth", np.full(len(me.polygons), smooth, dtype=bool))
    me.validate(clean_customdata=False)
    me.update()
    ob = bpy.data.objects.new(name, me)
    (collection or col_main).objects.link(ob)
    return ob


def deselect_all():
    view_layer.update()
    for o in list(scene.objects):
        if o is not None:
            try:
                o.select_set(False)
            except Exception:       # noqa: BLE001
                pass


def set_active(ob, select_only=True):
    if select_only:
        deselect_all()
    ob.select_set(True)
    view_layer.objects.active = ob


def mesh_arrays(ob):
    me = ob.data
    me.calc_loop_triangles()
    V = np.zeros(len(me.vertices) * 3)
    me.vertices.foreach_get("co", V)
    V = V.reshape(-1, 3)
    tris = np.zeros(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", tris)
    loops = np.zeros(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("loops", loops)
    uv = None
    if me.uv_layers.active is not None:
        all_uv = np.zeros(len(me.loops) * 2)
        me.uv_layers.active.data.foreach_get("uv", all_uv)
        uv = all_uv.reshape(-1, 2)[loops]
    return V, tris.reshape(-1, 3), uv


def vertex_normals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    vn = np.zeros_like(V)
    for k in range(3):
        np.add.at(vn, T[:, k], fn)
    return vn / np.maximum(np.linalg.norm(vn, axis=1, keepdims=True), 1e-12)


def save_image(name, arr, filename, non_color=False):
    """numpy (H, W, 3|4), rows bottom-up like Blender/UV space -> PNG + Blender image."""
    arr = np.asarray(arr, np.float32)
    h, w = arr.shape[:2]
    has_alpha = arr.shape[2] == 4
    img = bpy.data.images.new(name, w, h, alpha=has_alpha, float_buffer=False)
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    rgba = np.ones((h, w, 4), np.float32)
    rgba[..., :arr.shape[2]] = np.clip(arr, 0, 1)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = os.path.join(OUT, filename)
    img.file_format = "PNG"
    img.save()
    return img


def load_photo(slot, size=512):
    """A downloaded photographed texture as numpy (h, w, 3) 0..1, or None."""
    if not TEX:
        return None
    for ext in ("jpg", "png"):
        p = os.path.join(TEX, slot, "diff." + ext)
        if os.path.exists(p):
            try:
                img = bpy.data.images.load(p)
                w, h = img.size
                px = np.zeros(w * h * 4, np.float32)
                img.pixels.foreach_get(px)
                arr = px.reshape(h, w, 4)[..., :3]
                bpy.data.images.remove(img)
                step = max(1, w // size)
                log("photo texture", slot, "%dx%d" % (w, h))
                return arr[::step, ::step]
            except Exception as e:      # noqa: BLE001
                log("photo texture failed", slot, e)
    return None


def principled(name, base=None, base_img=None, normal_img=None, rough_img=None, rough=0.6, metal=0.0, emit_img=None,
               emit=None, emit_strength=0.0, alpha_from_base=False, double=False):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if base is not None:
        bsdf.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
    if base_img is not None:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = base_img
        nt.links.new(tn.outputs["Color"], bsdf.inputs["Base Color"])
        if alpha_from_base:
            mn = nt.nodes.new("ShaderNodeMath")
            mn.operation = "ROUND"
            nt.links.new(tn.outputs["Alpha"], mn.inputs[0])
            nt.links.new(mn.outputs[0], bsdf.inputs["Alpha"])
            for attr, val in (("blend_method", "CLIP"), ("shadow_method", "CLIP")):
                try:
                    setattr(m, attr, val)
                except Exception:       # noqa: BLE001
                    pass
    if normal_img is not None:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = normal_img
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if rough_img is not None:
        tn = nt.nodes.new("ShaderNodeTexImage")
        tn.image = rough_img
        sep = nt.nodes.new("ShaderNodeSeparateColor")
        nt.links.new(tn.outputs["Color"], sep.inputs["Color"])
        nt.links.new(sep.outputs["Green"], bsdf.inputs["Roughness"])
        nt.links.new(sep.outputs["Blue"], bsdf.inputs["Metallic"])
    if emit_img is not None or emit is not None:
        key = "Emission Color" if "Emission Color" in bsdf.inputs else "Emission"
        if emit_img is not None:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = emit_img
            nt.links.new(tn.outputs["Color"], bsdf.inputs[key])
        else:
            bsdf.inputs[key].default_value = (emit[0], emit[1], emit[2], 1.0)
        if "Emission Strength" in bsdf.inputs:
            bsdf.inputs["Emission Strength"].default_value = emit_strength
    m.use_backface_culling = not double
    return m


def add_skin(ob, arm, bones, W):
    """Vertex groups + armature modifier. bones: list of names, W: (n_verts, n_bones)."""
    groups = {b: ob.vertex_groups.new(name=b) for b in bones}
    for bi, b in enumerate(bones):
        idx = np.nonzero(W[:, bi] > 1e-4)[0]
        g = groups[b]
        w = W[idx, bi]
        # group by rounded weight to cut down the number of API calls
        q = np.round(w, 3)
        for val in np.unique(q):
            sel = idx[q == val].tolist()
            g.add(sel, float(val), "REPLACE")
    mod = ob.modifiers.new("Armature", "ARMATURE")
    mod.object = arm
    ob.parent = arm


def single_bone(n, bone):
    return [bone], np.ones((n, 1))


# ================================================================================================ 1. sculpt
log("Ragini build - Blender", bpy.app.version_string, "quick" if QUICK else "full")
body = anatomy.build()
lo, hi = anatomy.bounds()
try:
    V, T = sdf.mesh_from_shapes(body.shapes, lo, hi, H_SCULPT, log=log, snap_iters=1)
except MemoryError:
    log("sculpt: out of memory at %.4f, retrying coarser" % H_SCULPT)
    V, T = sdf.mesh_from_shapes(body.shapes, lo, hi, H_SCULPT * 1.4, log=log, snap_iters=1)
log("sculpture: %d verts, %d tris" % (len(V), len(T)))
# legs and hips are hidden under the saree: drop them (no poking through when she walks)
hidden = (V[:, 2] > 0.175) & (V[:, 2] < 0.955) & (np.abs(V[:, 0]) < 0.235)
keep = ~(hidden[T[:, 0]] & hidden[T[:, 1]] & hidden[T[:, 2]])
V, T = sdf.compact(V, T[keep])
log("under-skirt removed: %d verts, %d tris" % (len(V), len(T)))
high = mesh_obj("ragini_sculpt", V, T)
TV, TT = sdf.mesh_from_shapes(body.teeth, np.array([-0.04, -0.1, 1.45]), np.array([0.04, -0.03, 1.56]), 0.0011,
                              snap_iters=1, keep=0)
log("teeth: %d tris" % len(TT))

# ================================================================================================ 2-4. cloth, hair, jewellery
SV, ST, SUV, sk_info = garments.skirt(body)
PV, PT, PUV = garments.pallu(body)
HV, HT, HUV, HROOT = hair.build(body)
JV, JT, JUV, JM, JB = accessories.jewellery(body)
# lay the mangalsutra beads onto her chest
torso_shapes = [s for s in body.shapes if s.bone in ("chest", "neck", "spine")]
bead_mask = np.isin(JM, [accessories.MATERIALS.index("bead_black")])
if bead_mask.any():
    bead_verts = np.unique(JT[bead_mask].ravel())
    pts = JV[bead_verts]
    d = sdf.eval_points(torso_shapes, pts)
    g = sdf.gradient(torso_shapes, pts)
    g /= np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-9)
    JV[bead_verts] = pts - g * (d[:, None] - 0.004)
XV, XT, XUV, xinfo = accessories.scale(body)
log("skirt %d tris, pallu %d, hair %d, jewellery %d, scale %d" % (len(ST), len(PT), len(HT), len(JT), len(XT)))

# ================================================================================================ 5. game mesh
dec = high.modifiers.new("decimate", "DECIMATE")
dec.decimate_type = "COLLAPSE"
dec.ratio = min(1.0, TARGET_TRIS / float(len(T)))
dec.use_symmetry = False
dec.use_collapse_triangulate = True
dg = bpy.context.evaluated_depsgraph_get()
low_me = bpy.data.meshes.new_from_object(high.evaluated_get(dg))
high.modifiers.remove(dec)
low = bpy.data.objects.new("ragini_body", low_me)
col_main.objects.link(low)
low_me.polygons.foreach_set("use_smooth", np.ones(len(low_me.polygons), dtype=bool))
low_me.update()
log("game mesh: %d tris" % len(low_me.polygons))
set_active(low)
bpy.ops.object.mode_set(mode="EDIT")
bpy.ops.mesh.select_all(action="SELECT")
bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.004)
bpy.ops.object.mode_set(mode="OBJECT")
LV, LT, LUV = mesh_arrays(low)
log("unwrapped: %d uv corners" % len(LUV))

# normal map baked from the sculpture
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = 8
try:
    scene.cycles.use_denoising = False
except Exception:       # noqa: BLE001
    pass
nimg = bpy.data.images.new("ragini_body_normal", TEX_BODY, TEX_BODY, alpha=False, float_buffer=False)
nimg.colorspace_settings.name = "Non-Color"
bake_mat = bpy.data.materials.new("bake")
bake_mat.use_nodes = True
bn = bake_mat.node_tree.nodes.new("ShaderNodeTexImage")
bn.image = nimg
bake_mat.node_tree.nodes.active = bn
low.data.materials.append(bake_mat)
normal_ok = False
try:
    deselect_all()
    high.select_set(True)
    low.select_set(True)
    view_layer.objects.active = low
    t1 = time.time()
    bpy.ops.object.bake(type="NORMAL", use_selected_to_active=True, cage_extrusion=0.009, max_ray_distance=0.03,
                        margin=12, normal_space="TANGENT", use_clear=True)
    nimg.filepath_raw = os.path.join(OUT, "ragini_body_normal.png")
    nimg.file_format = "PNG"
    nimg.save()
    normal_ok = True
    log("normal map baked in %.1fs" % (time.time() - t1))
except Exception as e:      # noqa: BLE001
    traceback.print_exc()
    log("NORMAL BAKE FAILED:", e)

# ambient occlusion of the game mesh (deep eye sockets, the mouth, between the fingers)
ao = None
try:
    aimg = bpy.data.images.new("ragini_ao", TEX_BODY // 2, TEX_BODY // 2, alpha=False, float_buffer=True)
    bn.image = aimg
    scene.cycles.samples = 24 if not QUICK else 8
    set_active(low)
    high.hide_render = True
    t1 = time.time()
    bpy.ops.object.bake(type="AO", margin=8, use_clear=True)
    px = np.zeros(aimg.size[0] * aimg.size[1] * 4, np.float32)
    aimg.pixels.foreach_get(px)
    ao = px.reshape(aimg.size[1], aimg.size[0], 4)[..., 0]
    log("AO baked in %.1fs, mean %.2f" % (time.time() - t1, float(ao.mean())))
except Exception as e:      # noqa: BLE001
    traceback.print_exc()
    log("AO BAKE FAILED:", e)
low.data.materials.clear()

# ================================================================================================ 6. paint
log("painting the skin ...")
LN = vertex_normals(LV, LT)
pos, nor, cov = textures.raster(LUV, LT, LV, LN, TEX_BODY)
P = pos[cov]
Nn = nor[cov]
col_px, rough_px = textures.skin(P, Nn, body.marks)
alb = np.zeros((TEX_BODY, TEX_BODY, 3))
alb[cov] = col_px
rgh = np.full((TEX_BODY, TEX_BODY), 0.6)
rgh[cov] = rough_px
if ao is not None:
    a = np.kron(ao, np.ones((2, 2))) if ao.shape[0] * 2 == TEX_BODY else ao
    a = a[:TEX_BODY, :TEX_BODY]
    alb[cov] *= (0.55 + 0.45 * np.clip(a[cov], 0, 1) ** 0.8)[:, None]
alb = textures.dilate(alb, cov, 10)
rough_rgb = np.zeros((TEX_BODY, TEX_BODY, 3))
rough_rgb[..., 1] = textures.dilate(rgh[..., None], cov, 10)[..., 0]
alb_img = save_image("ragini_body_albedo", alb, "ragini_body_albedo.png")
rgh_img = save_image("ragini_body_rough", rough_rgb, "ragini_body_rough.png", non_color=True)
log("skin painted")
m_skin = principled("ragini_skin", base_img=alb_img, normal_img=nimg if normal_ok else None, rough_img=rgh_img)
low.data.materials.append(m_skin)

# saree
weave = load_photo("fabric", 512)
s_len_u = float(np.linalg.norm(np.diff(SV.reshape(sk_info["n_rings"], -1, 3)[-1, :, :2], axis=0), axis=1).sum())
s_len_v = float(np.mean(sk_info["waist_z"] - sk_info["hem"]))
s_alb, s_rgh = textures.fabric(2048 if not QUICK else 1024, 1024 if not QUICK else 512, s_len_u, s_len_v, weave, seed=1,
                               border_edges=("v0",))
p_alb, p_rgh = textures.fabric(1024 if not QUICK else 512, 512 if not QUICK else 256, 1.9, 0.3, weave, seed=2,
                               border_edges=("v0",), pallu_end=True)


def rough_img_from(arr, name):
    rr = np.zeros(arr.shape + (3,))
    rr[..., 1] = arr
    return save_image(name, rr, name + ".png", non_color=True)


m_skirt = principled("ragini_saree", base_img=save_image("ragini_saree", s_alb, "ragini_saree.png"),
                     rough_img=rough_img_from(s_rgh, "ragini_saree_rough"), double=True)
m_pallu = principled("ragini_pallu", base_img=save_image("ragini_pallu", p_alb, "ragini_pallu.png"),
                     rough_img=rough_img_from(p_rgh, "ragini_pallu_rough"), double=True)
saree = mesh_obj("ragini_saree", SV, ST, SUV)
saree.data.materials.append(m_skirt)
pallu = mesh_obj("ragini_pallu", PV, PT, PUV)
pallu.data.materials.append(m_pallu)

# hair
h_tex = hair.texture(512 if not QUICK else 256, 1024 if not QUICK else 512)
m_hair = principled("ragini_hair", base_img=save_image("ragini_hair", h_tex, "ragini_hair.png"), rough=0.75,
                    alpha_from_base=True, double=True)
hair_ob = mesh_obj("ragini_hair", HV, HT, HUV)
hair_ob.data.materials.append(m_hair)

# eyes: proper UV spheres in the sculpted sockets
e_alb, e_emit = textures.eye(256)
m_eye = principled("ragini_eyes", base_img=save_image("ragini_eye", e_alb, "ragini_eye.png"),
                   emit_img=save_image("ragini_eye_glow", e_emit, "ragini_eye_glow.png"), emit_strength=6.0, rough=0.15)
eye_V, eye_T, eye_UV = [], [], []
for s in body.eyes:
    c = s.p["c"]
    r = float(s.p["r"])
    n0 = sum(len(v) for v in eye_V)
    vs, us = [], []
    seg, rings = 20, 14
    for i in range(rings + 1):
        lat = math.pi * (i / rings - 0.5)
        for j in range(seg + 1):
            lon = 2 * math.pi * (j / seg - 0.5)                 # lon 0 looks straight ahead (-Y)
            d = np.array([math.sin(lon) * math.cos(lat), -math.cos(lon) * math.cos(lat), math.sin(lat)])
            vs.append(c + d * r)
            us.append((j / seg, i / rings))
    tri = []
    for i in range(rings):
        for j in range(seg):
            a = i * (seg + 1) + j
            b2 = a + seg + 1
            tri += [(a + n0, b2 + 1 + n0, b2 + n0), (a + n0, a + 1 + n0, b2 + 1 + n0)]
    eye_V.append(np.array(vs))
    eye_T.append(np.array(tri))
    eye_UV.append(np.array(us))
eyes_ob = mesh_obj("ragini_eyes", np.concatenate(eye_V), np.concatenate(eye_T), np.concatenate(eye_UV))
eyes_ob.data.materials.append(m_eye)

teeth_ob = mesh_obj("ragini_teeth", TV, TT)
teeth_ob.data.materials.append(principled("ragini_teeth", base=(0.55, 0.47, 0.30), rough=0.4))

# jewellery
jew = mesh_obj("ragini_jewellery", JV, JT, JUV)
jmats = {
    "gold": principled("gold", base=(0.85, 0.6, 0.22), rough=0.28, metal=1.0),
    "glass_red": principled("glass_red", base=(0.45, 0.01, 0.02), rough=0.08),
    "glass_green": principled("glass_green", base=(0.03, 0.22, 0.05), rough=0.08),
    "bead_black": principled("bead_black", base=(0.015, 0.015, 0.015), rough=0.15),
    "silver": principled("silver", base=(0.72, 0.72, 0.74), rough=0.32, metal=1.0),
}
for mn in accessories.MATERIALS:
    jew.data.materials.append(jmats[mn])
jew.data.polygons.foreach_set("material_index", JM.astype(np.int32))
jew.data.update()

# the scale
wood = load_photo("wood_scale", 512)
x_tex = textures.scale_tex(2048 if not QUICK else 1024, 128, xinfo["length"], wood)
scale_ob = mesh_obj("ragini_scale", XV, XT, XUV, smooth=False)
scale_ob.data.materials.append(principled("ragini_scale", base_img=save_image("ragini_scale", x_tex, "ragini_scale.png"),
                                          rough=0.55))

# ================================================================================================ 7. rig
arm_data = bpy.data.armatures.new("RaginiRig")
arm = bpy.data.objects.new("Ragini", arm_data)
col_main.objects.link(arm)
set_active(arm)
bpy.ops.object.mode_set(mode="EDIT")
ebs = {}
for name, (h, t, parent) in body.bones.items():
    eb = arm_data.edit_bones.new(name)
    eb.head = Vector(h)
    eb.tail = Vector(t)
    d = Vector(t) - Vector(h)
    eb.align_roll(Vector((0, 0, 1)) if abs(d.normalized().y) > 0.85 else Vector((0, -1, 0)))
    ebs[name] = eb
for name, (h, t, parent) in body.bones.items():
    if parent:
        ebs[name].parent = ebs[parent]
        ebs[name].use_connect = False
    ebs[name].use_deform = name != "root"
bpy.ops.object.mode_set(mode="OBJECT")
log("armature: %d bones" % len(arm_data.bones))

# body weights straight from the sculpt
bones_b, W_b = sdf.bone_weights(body.shapes, LV, tau=0.011)
add_skin(low, arm, bones_b, W_b)
# teeth: upper with the head, lower with the jaw
bones_t, W_t = sdf.bone_weights(body.teeth, TV, tau=0.002)
add_skin(teeth_ob, arm, bones_t, W_t)
add_skin(eyes_ob, arm, *single_bone(len(eyes_ob.data.vertices), "head"))


def skirt_weights(Vs):
    z = Vs[:, 2]
    x = Vs[:, 0]
    t = np.clip((0.95 - z) / 0.75, 0, 1)
    u = np.clip((0.52 - z) / 0.38, 0, 1)
    sL = np.clip(0.5 + x / 0.13, 0, 1)
    sR = 1 - sL
    leg = 0.7 * t
    W = np.stack([1 - leg, leg * (1 - u) * sL, leg * u * sL, leg * (1 - u) * sR, leg * u * sR], axis=1)
    W[:, 0] = np.maximum(W[:, 0], 0.0)
    return ["hips", "thigh.L", "shin.L", "thigh.R", "shin.R"], W / W.sum(axis=1, keepdims=True)


add_skin(saree, arm, *skirt_weights(SV))
torso_bones = [s for s in body.shapes if s.bone in ("hips", "spine", "chest", "neck", "clavicle.L", "upper_arm.L")]
bones_p, W_p = sdf.bone_weights(torso_bones, PV, tau=0.03)
hang = (PV[:, 1] > 0.07) & (PV[:, 2] < 1.2)
if hang.any():
    W_p[hang] = 0.0
    W_p[hang, bones_p.index("chest")] = 0.65
    if "spine" in bones_p:
        W_p[hang, bones_p.index("spine")] = 0.35
    W_p /= np.maximum(W_p.sum(axis=1, keepdims=True), 1e-9)
add_skin(pallu, arm, bones_p, W_p)
# hair: the head carries the roots, the lengths settle on the neck, shoulders and back
wh = np.clip(1.0 - (HROOT - 0.09) / 0.14, 0.0, 1.0)
lower = 1 - wh
hb = ["head", "neck", "chest", "spine"]
Wh = np.zeros((len(HV), 4))
Wh[:, 0] = wh
Wh[:, 1] = lower * np.where(HV[:, 2] > 1.38, 0.5, 0.15)
Wh[:, 2] = lower * np.where(HV[:, 2] > 1.38, 0.5, 0.55)
Wh[:, 3] = lower * np.where(HV[:, 2] > 1.38, 0.0, 0.30)
add_skin(hair_ob, arm, hb, Wh / Wh.sum(axis=1, keepdims=True))
jb = sorted(set(JB.tolist()))
Wj = np.zeros((len(JV), len(jb)))
for i, bname in enumerate(JB):
    Wj[i, jb.index(bname)] = 1.0
add_skin(jew, arm, jb, Wj)
add_skin(scale_ob, arm, *single_bone(len(XV), "hand.R"))
log("skinned")

actions = animate.build_actions(arm, log)

# ================================================================================================ 8. export
bpy.data.objects.remove(high, do_unlink=True)
meshes = [low, saree, pallu, hair_ob, eyes_ob, teeth_ob, jew, scale_ob]
deselect_all()
for o in meshes + [arm]:
    o.select_set(True)
view_layer.objects.active = arm
props = bpy.ops.export_scene.gltf.get_rna_type().properties
keys = props.keys()
kw = dict(filepath=os.path.join(OUT, "ragini.glb"), export_format="GLB", use_selection=True, export_apply=False,
          export_animations=True, export_skins=True, export_yup=True, export_texcoords=True, export_normals=True,
          export_materials="EXPORT", export_image_format="AUTO", export_force_sampling=True, export_def_bones=False,
          export_morph=False, export_cameras=False, export_lights=False, export_all_influences=False,
          export_rest_position_armature=True, export_anim_single_armature=True, export_reset_pose_bones=True)
if "export_animation_mode" in keys:
    modes = [i.identifier for i in props["export_animation_mode"].enum_items]
    kw["export_animation_mode"] = "NLA_TRACKS" if "NLA_TRACKS" in modes else "ACTIONS"
    log("animation mode", kw["export_animation_mode"], modes)
elif "export_nla_strips" in keys:
    kw["export_nla_strips"] = True
kw = {k: v for k, v in kw.items() if k in keys}
bpy.ops.export_scene.gltf(**kw)
log("exported ragini.glb %.1f MB" % (os.path.getsize(os.path.join(OUT, "ragini.glb")) / 1e6))
json.dump({"actions": [{"name": n, "frames": f, "loop": lp, "fps": animate.FPS} for n, f, lp in actions],
           "height": 1.72, "eyes": [list(map(float, s.p["c"])) for s in body.eyes],
           "scale_tip": list(map(float, xinfo["start"] + xinfo["axis"] * xinfo["length"]))},
          open(os.path.join(OUT, "ragini_meta.json"), "w"), indent=1)

# ================================================================================================ previews
try:
    import preview_render
    preview_render.render_all(scene, arm, meshes, OUT, log, quick=QUICK)
except Exception as e:      # noqa: BLE001
    traceback.print_exc()
    log("PREVIEWS FAILED:", e)

try:
    bpy.ops.file.pack_all()
except Exception as e:      # noqa: BLE001
    log("pack failed:", e)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "ragini.blend"), compress=True)
log("saved ragini.blend - done")
