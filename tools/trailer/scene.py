"""Chaya - cinematic trailer scene, built in Blender and rendered with Cycles.

    blender -b --python-exit-code 1 -P tools/trailer/scene.py -- <map dir> <baked chaya tex dir> <assets dir> <out .blend>

Everything comes from the game: the Blender-built house (maze.glb, candle.glb), its CC0 photo textures, and Microsoft
Rocketbox's avatar + mocap for Chaya (re-shaded: ashen skin, blood tears, glowing eyes, long black hair, sindoor).
One scene, eight camera shots switched by timeline markers (frames and events in timeline.json):

  S1  corridor push-in, lanterns flicker - a figure at the far end
  S2  your candle; a door creaks open - she is standing behind it
  S3  slow orbit round the pooja altar with the six holy items and a ring of diyas
  S4  a long corridor - each time the lamps die she is closer
  S5  she limps towards you, eyes burning, low angle
  S6  close on the candle flame - it gutters and dies
  S7  her face rushes out of the dark
  S8  3D CHAYA title (Biro Script lettering) in firelight with rising embers
"""
import json
import math
import os
import random
import sys

import bpy
from mathutils import Euler, Matrix, Quaternion, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tl  # noqa: E402

argv = sys.argv[sys.argv.index("--") + 1:]
MAP, CTEX, ASSETS, OUT = (os.path.abspath(a) for a in argv[:4])
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
T = tl.load()
FPS = T["fps"]
EV = T["events"]
SHOTS = {s["id"]: (s["f0"], s["f1"]) for s in T["shots"]}
END = T["frames"]
FAR = Vector((0.0, 0.0, -80.0))
rng = random.Random(16112026)

L = json.load(open(os.path.join(MAP, "layout.json")))
META = json.load(open(os.path.join(MAP, "meta.json")))
CELL, X0, Z0 = L["cell"], L["x0"], L["z0"]


def log(*a):
    print("[trailer]", *a, flush=True)


def G(x, y, z):
    """Godot / glTF coordinates (x east, y up, z south) -> Blender (z up)."""
    return Vector((x, -z, y))


def cell(i, j, h=0.0):
    return G(X0 + (i + 0.5) * CELL, h, Z0 + (j + 0.5) * CELL)


bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def set_fps():
    scene.render.fps = FPS
    scene.render.fps_base = 1.0


set_fps()
scene.frame_start, scene.frame_end = 1, END

# ================================================================================================ materials
TEX = os.path.join(ASSETS, "downloaded", "tex")
# material -> (texture slot, tint, roughness scale, metallic)  - the game's Mats table
LOOK = {
    "floor_wood": ("wood_floor", (0.62, 0.55, 0.5), 1.0, 0.0), "floor_stone": ("stone_floor", (0.62, 0.6, 0.58), 1.0, 0.0),
    "wall_wood": ("wood_wall", (0.5, 0.45, 0.4), 1.0, 0.0), "wall_plaster": ("plaster", (0.66, 0.6, 0.5), 1.0, 0.0),
    "ceiling_wood": ("wood_ceiling", (0.45, 0.4, 0.36), 1.0, 0.0), "trim_wood": ("wood_dark", (0.5, 0.42, 0.36), 0.9, 0.0),
    "door_wood": ("wood_door", (0.55, 0.46, 0.38), 0.9, 0.0), "brass": ("brass", (1.0, 0.82, 0.5), 0.55, 0.95),
    "copper": ("copper", (1.0, 0.6, 0.4), 0.55, 0.95), "stone_altar": ("stone_floor", (0.75, 0.7, 0.66), 0.9, 0.0),
    "red_cloth": ("fiber", (0.8, 0.1, 0.08), 1.0, 0.0), "clay": ("clay", (0.9, 0.55, 0.4), 1.0, 0.0),
    "coconut": ("fiber", (0.75, 0.55, 0.38), 1.0, 0.0), "rope": ("fiber", (0.85, 0.72, 0.52), 1.0, 0.0),
    "sack": ("fiber", (0.9, 0.8, 0.62), 1.0, 0.0), "iron": ("copper", (0.32, 0.3, 0.28), 0.8, 0.6),
    "wood_old": ("wood_dark", (0.62, 0.52, 0.42), 0.95, 0.0),
}
FLAT = {"kumkum_red": ((0.6, 0.02, 0.02), 0.9, 0.0), "camphor_white": ((0.92, 0.9, 0.85), 0.6, 0.0),
        "leaf_green": ((0.1, 0.28, 0.06), 0.6, 0.0), "candle_wax": ((0.93, 0.87, 0.74), 0.45, 0.0),
        "wick": ((0.04, 0.035, 0.03), 1.0, 0.0)}
_mats = {}


def tex_path(slot, kind):
    for ext in ("jpg", "png"):
        p = os.path.join(TEX, slot, kind + "." + ext)
        if os.path.exists(p):
            return p
    return None


def image(path, non_color=False):
    im = bpy.data.images.load(path, check_existing=True)
    if non_color:
        im.colorspace_settings.name = "Non-Color"
    return im


def principled(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def no_emission_sampling(m):
    try:
        m.cycles.emission_sampling = "NONE"
    except Exception:       # noqa: BLE001
        pass


def seen_only(nt, shader_socket):
    """Camera and glossy rays see the shader; diffuse and shadow rays pass through. For small glowing things whose
    light is carried by a real lamp inside them (lantern glass, flames, eyes, embers): no noise, no swallowed lamps."""
    lp = nt.nodes.new("ShaderNodeLightPath")
    mx_ = nt.nodes.new("ShaderNodeMath")
    mx_.operation = "MAXIMUM"
    nt.links.new(lp.outputs["Is Camera Ray"], mx_.inputs[0])
    nt.links.new(lp.outputs["Is Glossy Ray"], mx_.inputs[1])
    tr_ = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mx_.outputs[0], mix.inputs[0])
    nt.links.new(tr_.outputs[0], mix.inputs[1])
    nt.links.new(shader_socket, mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])


def no_shadow(nt, shader_socket):
    """Shadow rays pass through (a lantern's frame must not swallow the lamp inside it)."""
    lp = nt.nodes.new("ShaderNodeLightPath")
    tr_ = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(lp.outputs["Is Shadow Ray"], mix.inputs[0])
    nt.links.new(shader_socket, mix.inputs[1])
    nt.links.new(tr_.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], nt.nodes["Material Output"].inputs["Surface"])


def glow(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for nd in list(nt.nodes):
        if nd.type != "OUTPUT_MATERIAL":
            nt.nodes.remove(nd)
    em_ = nt.nodes.new("ShaderNodeEmission")
    em_.inputs["Color"].default_value = (*color, 1)
    em_.inputs["Strength"].default_value = strength
    seen_only(nt, em_.outputs[0])
    no_emission_sampling(m)
    return m


def flat(name, color, rough, metal=0.0):
    m, nt, b = principled(name)
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    return m


def textured(name, box=False):
    """Photo-textured material in the game's look; box=True projects the photos (props have no metric UVs)."""
    key = name + ("_box" if box else "")
    if key in _mats:
        return _mats[key]
    if name == "lantern_glow":
        m = glow(key, (1.0, 0.62, 0.28), 8.0)
    elif name == "lantern_metal":
        m, nt, b = principled(key)
        b.inputs["Base Color"].default_value = (0.06, 0.055, 0.05, 1)
        b.inputs["Roughness"].default_value = 0.5
        b.inputs["Metallic"].default_value = 0.8
        no_shadow(nt, b.outputs["BSDF"])
    elif name == "wick_ember":
        m = glow(key, (1.0, 0.35, 0.08), 4.0)
    elif name in FLAT:
        m = flat(key, *FLAT[name])
    else:
        slot, tint, rs, metal = LOOK.get(name, ("wood_dark", (0.55, 0.47, 0.4), 1.0, 0.0))
        m, nt, b = principled(key)
        b.inputs["Metallic"].default_value = metal
        vec = None
        if box:
            tcn = nt.nodes.new("ShaderNodeTexCoord")
            mp = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Scale"].default_value = (1.6, 1.6, 1.6)
            nt.links.new(tcn.outputs["Object"], mp.inputs["Vector"])
            vec = mp.outputs["Vector"]

        def tex_node(path, nc):
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = image(path, nc)
            if box:
                t.projection = "BOX"
                t.projection_blend = 0.3
                nt.links.new(vec, t.inputs["Vector"])
            return t
        d = tex_path(slot, "diff")
        if d:
            t = tex_node(d, False)
            mul_ = nt.nodes.new("ShaderNodeVectorMath")
            mul_.operation = "MULTIPLY"
            mul_.inputs[1].default_value = tint
            nt.links.new(t.outputs["Color"], mul_.inputs[0])
            nt.links.new(mul_.outputs["Vector"], b.inputs["Base Color"])
        else:
            b.inputs["Base Color"].default_value = (*[c * 0.45 for c in tint], 1)
        n = tex_path(slot, "nor")
        if n:
            t = tex_node(n, True)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = 1.0
            nt.links.new(t.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], b.inputs["Normal"])
        rp = tex_path(slot, "rough")
        if rp:
            t = tex_node(rp, True)
            mm = nt.nodes.new("ShaderNodeMath")
            mm.operation = "MULTIPLY"
            mm.inputs[1].default_value = rs
            nt.links.new(t.outputs["Color"], mm.inputs[0])
            nt.links.new(mm.outputs[0], b.inputs["Roughness"])
        else:
            b.inputs["Roughness"].default_value = 0.8 * rs
    _mats[key] = m
    return m


def base_name(mat):
    return mat.name.split(".")[0] if mat else ""


def under_prop(ob):
    p = ob
    while p is not None:
        if p.name.startswith("prop_") or p.name.startswith("candle"):
            return True
        p = p.parent
    return False


def shade(objs):
    for ob in objs:
        if ob.type != "MESH":
            continue
        box = under_prop(ob)
        for slot in ob.material_slots:
            slot.material = textured(base_name(slot.material), box)


def new_objects(before_):
    return [o for o in bpy.data.objects if o not in before_]


# ================================================================================================ the house
before = set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=os.path.join(MAP, "maze.glb"))
house = new_objects(before)
shade(house)
for ob in house:
    if ob.rotation_mode != "XYZ":
        ob.rotation_mode = "XYZ"
log("house:", len(house), "objects,", len(_mats), "materials:", sorted(_mats))

world = bpy.data.worlds.new("night")
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.003, 0.0035, 0.005, 1)
world.mist_settings.start = 3.0
world.mist_settings.depth = 16.0
world.mist_settings.falloff = "QUADRATIC"
scene.world = world


def key_energy(light_ob, frame, value):
    light_ob.data.energy = max(0.0, value)
    light_ob.data.keyframe_insert("energy", frame=frame)


def set_interp(idb, fn):
    ad_ = idb.animation_data
    if ad_ and ad_.action:
        for fc in ad_.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = fn(int(round(kp.co.x)))


def linear_keys(idb):
    set_interp(idb, lambda x: "LINEAR")


def point(name, pos, energy, color, radius=0.05):
    ld = bpy.data.lights.new(name, "POINT")
    ld.energy = energy
    ld.color = color
    ld.shadow_soft_size = radius
    lo = bpy.data.objects.new(name, ld)
    lo.location = pos
    lo.visible_camera = False
    scene.collection.objects.link(lo)
    return lo


def area(name, pos, target, energy, color, size):
    ld = bpy.data.lights.new(name, "AREA")
    ld.energy = energy
    ld.color = color
    ld.size = size
    lo = bpy.data.objects.new(name, ld)
    lo.location = pos
    lo.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler()
    lo.visible_camera = False
    scene.collection.objects.link(lo)
    return lo


def shot_light(lo, shot, value):
    """a light that only shines during one shot"""
    f0_, f1_ = SHOTS[shot]
    key_energy(lo, 1, 0.0)
    key_energy(lo, f0_ - 1, 0.0)
    key_energy(lo, f0_, value)
    key_energy(lo, f1_, value)
    key_energy(lo, f1_ + 1, 0.0)
    set_interp(lo.data, lambda x: "CONSTANT")


# ------------------------------------------------------------------------------------------------ hanging lanterns
LAMP_E = 34.0
lamps = [point("lamp_%d" % k, G(*l["pos"]), LAMP_E, (1.0, 0.62, 0.32), 0.05) for k, l in enumerate(L["lights"])]
ROW3 = (cell(5, 3), cell(11, 3))
ROW10 = (cell(5, 10), cell(11, 10))


def near_segment(p, seg, d):
    a, b = seg
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    q = a + ab * t
    return (Vector((p.x - q.x, p.y - q.y, 0.0))).length < d


def stutter(f, a, b, seed):
    """lamp brightness factor during a power stutter between frames a and b"""
    r_ = random.Random(seed * 7919 + f)
    if f < a or f > b:
        return 1.0
    u = (f - a) / max(1.0, b - a)
    return 0.0 if r_.random() < 0.35 + 0.5 * u else 0.25 + 0.75 * r_.random()


def lamp_factor(k, lo, f):
    p = lo.location
    n = 1.0 + 0.06 * math.sin(f * 0.37 + k * 1.7) + 0.04 * math.sin(f * 1.31 + k * 0.6)
    s1a, s1b = EV["s1_flicker"]
    if near_segment(p, ROW3, 5.0) and s1a <= f <= s1b:
        n *= stutter(f, s1a, s1b, k)
    if near_segment(p, ROW10, 5.0):
        for jf in (EV["s4_jump1"], EV["s4_jump2"]):
            if jf - 4 <= f <= jf + 3:
                n *= 0.0 if jf - 2 <= f <= jf + 1 else 0.3
        f5a = SHOTS["S5"][0]
        die = EV["s5_lamps_die"]
        if f5a + 50 <= f < die:
            n *= stutter(f, f5a + 50, die + 30, k + 50)
        if f >= die:
            n = 0.0
    if f >= SHOTS["S7"][0]:
        n = 0.0
    return n


for k, lo in enumerate(lamps):
    for f in range(1, END + 1):
        key_energy(lo, f, LAMP_E * lamp_factor(k, lo, f))
    linear_keys(lo.data)
# the lantern glass is one shared material: it follows the lamps that are in view in each shot
glow_m = _mats.get("lantern_glow")
if glow_m is not None:
    em_node = next(nd for nd in glow_m.node_tree.nodes if nd.type == "EMISSION")
    grp3 = [(k, lo) for k, lo in enumerate(lamps) if near_segment(lo.location, ROW3, 5.0)]
    grp10 = [(k, lo) for k, lo in enumerate(lamps) if near_segment(lo.location, ROW10, 5.0)]
    for f in range(1, END + 1):
        grp = grp3 if SHOTS["S1"][0] <= f <= SHOTS["S1"][1] else (grp10 if SHOTS["S4"][0] <= f <= SHOTS["S7"][1] else None)
        fac = sum(lamp_factor(k, lo, f) for k, lo in grp) / len(grp) if grp else 1.0
        em_node.inputs["Strength"].default_value = 8.0 * fac
        em_node.inputs["Strength"].keyframe_insert("default_value", frame=f)
    linear_keys(glow_m.node_tree)
log("lamps:", len(lamps))

# ================================================================================================ flames
flame_mat = bpy.data.materials.new("flame")
flame_mat.use_nodes = True
fnt = flame_mat.node_tree
for nd in list(fnt.nodes):
    if nd.type != "OUTPUT_MATERIAL":
        fnt.nodes.remove(nd)
tc = fnt.nodes.new("ShaderNodeTexCoord")
sep = fnt.nodes.new("ShaderNodeSeparateXYZ")
ramp = fnt.nodes.new("ShaderNodeValToRGB")
els = ramp.color_ramp.elements
els[0].position, els[0].color = 0.0, (0.25, 0.35, 1.0, 1)          # blue root
els[1].position, els[1].color = 1.0, (1.0, 0.3, 0.04, 1)           # orange tip
e = els.new(0.12)
e.color = (1.0, 0.92, 0.7, 1)                                      # white-hot core
e = els.new(0.5)
e.color = (1.0, 0.72, 0.28, 1)
em = fnt.nodes.new("ShaderNodeEmission")
em.inputs["Strength"].default_value = 26.0
lw = fnt.nodes.new("ShaderNodeLayerWeight")
lw.inputs["Blend"].default_value = 0.45
trn = fnt.nodes.new("ShaderNodeBsdfTransparent")
soft = fnt.nodes.new("ShaderNodeMixShader")
fnt.links.new(tc.outputs["Generated"], sep.inputs["Vector"])
fnt.links.new(sep.outputs["Z"], ramp.inputs["Fac"])
fnt.links.new(ramp.outputs["Color"], em.inputs["Color"])
fnt.links.new(lw.outputs["Facing"], soft.inputs[0])
fnt.links.new(em.outputs[0], soft.inputs[1])
fnt.links.new(trn.outputs[0], soft.inputs[2])
seen_only(fnt, soft.outputs[0])
no_emission_sampling(flame_mat)


def flame_profile(t):
    if t < 0.35:
        return math.sin(0.5 * math.pi * t / 0.35) ** 0.6
    return max(0.0, 1.0 - (t - 0.35) / 0.65) ** 1.4


def make_flame(name, parent, local_pos, size=1.0, energy=2.0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=1.0)
    fl = bpy.context.active_object
    fl.name = name
    for v in fl.data.vertices:                 # teardrop: round base, long narrow tip, ~3 cm tall
        t = (v.co.z + 1.0) / 2.0
        rxy = math.hypot(v.co.x, v.co.y)
        rad = 0.0062 * size * flame_profile(t)
        if rxy > 1e-6:
            v.co.x, v.co.y = v.co.x / rxy * rad, v.co.y / rxy * rad
        v.co.z = t * 0.03 * size - 0.004 * size
    bpy.ops.object.shade_smooth()
    fl.data.materials.append(flame_mat)
    fl.visible_shadow = False
    fl.parent = parent
    fl.location = local_pos
    li = point(name + "_light", Vector((0, 0, 0)), energy, (1.0, 0.56, 0.24), 0.012 * size)
    li.parent = parent
    li.location = local_pos + Vector((0, 0, 0.014 * size))
    return fl, li


def flame_life(fl, li, f0_, f1_, energy, seed, die_at=None):
    r_ = random.Random(seed)
    for f in range(f0_, f1_ + 1):
        s = 1.0 + 0.1 * (r_.random() - 0.5) + 0.05 * math.sin(f * 0.9 + seed)
        if die_at is not None and f >= die_at:
            s *= max(0.0, 1.0 - (f - die_at) / 7.0) * (1.0 + 0.6 * math.sin(f * 2.3))
        s = max(0.0, s)
        fl.scale = (1.0 + 0.08 * (r_.random() - 0.5), 1.0 + 0.08 * (r_.random() - 0.5), max(0.001, s))
        fl.rotation_euler = (0.05 * (r_.random() - 0.5), 0.05 * (r_.random() - 0.5), 0.0)
        fl.keyframe_insert("scale", frame=f)
        fl.keyframe_insert("rotation_euler", frame=f)
        key_energy(li, f, energy * s * (0.92 + 0.16 * r_.random()))
    linear_keys(fl)
    linear_keys(li.data)


# ================================================================================================ Chaya
RB = os.path.join(ASSETS, "downloaded", "chaya")
before = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=os.path.join(RB, "Medical_Female_01.fbx"), use_anim=False, ignore_leaf_bones=True)
chaya = new_objects(before)
arm = next(o for o in chaya if o.type == "ARMATURE")
body = next(o for o in chaya if o.type == "MESH")
actions, anim_fps = {}, {}


def retarget(src_obj, src_act, dst_obj, name):
    """Bake a mocap clip onto Chaya's own skeleton. Blender stores pose keys relative to each file's rest pose, and the
    clip files rest in a different pose than the avatar (arms down vs arms out), so the keys are converted through the
    absolute parent-relative bone transforms (what the game's Godot import applies):  P_dst = R_dst^-1 R_src P_src."""
    sd, dd = src_obj.data, dst_obj.data
    corr = {}
    for b in dd.bones:
        sb = sd.bones.get(b.name)
        if sb is None:
            continue
        rd = (b.parent.matrix_local.inverted() @ b.matrix_local) if b.parent else b.matrix_local.copy()
        rs = (sb.parent.matrix_local.inverted() @ sb.matrix_local) if sb.parent else sb.matrix_local.copy()
        corr[b.name] = rd.inverted() @ rs
    curves, obj_curves = {}, []
    for fc in src_act.fcurves:
        dp = fc.data_path
        if dp.startswith('pose.bones["'):
            bn = dp.split('"')[1]
            curves.setdefault(bn, {}).setdefault(dp.rsplit(".", 1)[1], {})[fc.array_index] = fc
        else:
            obj_curves.append(fc)
    a0, a1 = src_act.frame_range
    frames = list(range(int(round(a0)), int(round(a1)) + 1))
    out = bpy.data.actions.new("chaya_" + name)
    out.use_fake_user = True
    for fc in obj_curves:
        nf = out.fcurves.new(fc.data_path, index=fc.array_index)
        nf.keyframe_points.add(len(frames))
        nf.keyframe_points.foreach_set("co", [v for f in frames for v in (f, fc.evaluate(f))])
        nf.update()
    for bn, props in curves.items():
        if bn not in corr:
            continue
        c = corr[bn]

        def ev(prop, idx, f, default):
            fc_ = props.get(prop, {}).get(idx)
            return fc_.evaluate(f) if fc_ is not None else default
        vals = {"location": [], "rotation_quaternion": [], "scale": []}
        prev = None
        for f in frames:
            loc = Vector((ev("location", 0, f, 0.0), ev("location", 1, f, 0.0), ev("location", 2, f, 0.0)))
            if "rotation_quaternion" in props:
                q = Quaternion((ev("rotation_quaternion", 0, f, 1.0), ev("rotation_quaternion", 1, f, 0.0),
                                ev("rotation_quaternion", 2, f, 0.0), ev("rotation_quaternion", 3, f, 0.0))).normalized()
            elif "rotation_euler" in props:
                q = Euler((ev("rotation_euler", 0, f, 0.0), ev("rotation_euler", 1, f, 0.0), ev("rotation_euler", 2, f, 0.0))).to_quaternion()
            else:
                q = Quaternion()
            scl = Vector((ev("scale", 0, f, 1.0), ev("scale", 1, f, 1.0), ev("scale", 2, f, 1.0)))
            l2, q2, s2 = (c @ Matrix.LocRotScale(loc, q, scl)).decompose()
            if prev is not None and prev.dot(q2) < 0.0:
                q2 = -q2
            prev = q2
            vals["location"].append(l2)
            vals["rotation_quaternion"].append(q2)
            vals["scale"].append(s2)
        for prop, seq in vals.items():
            for idx in range(4 if prop == "rotation_quaternion" else 3):
                nf = out.fcurves.new('pose.bones["%s"].%s' % (bn, prop), index=idx, action_group=bn)
                nf.keyframe_points.add(len(frames))
                nf.keyframe_points.foreach_set("co", [v for f, x in zip(frames, seq) for v in (f, x[idx])])
                nf.update()
    for pb in dst_obj.pose.bones:
        pb.rotation_mode = "QUATERNION"
    log("retargeted", name, "bones", len([b for b in curves if b in corr]), "of", len(dd.bones), "frames", len(frames))
    return out


for nm, fn in (("idle", "idle.fbx"), ("walk", "walk.fbx")):
    p = os.path.join(RB, "anims", fn)
    if not os.path.exists(p):
        log("missing anim", p)
        continue
    acts0 = set(bpy.data.actions)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=p, ignore_leaf_bones=True)
    anim_fps[nm] = scene.render.fps / scene.render.fps_base
    new = [a for a in bpy.data.actions if a not in acts0]
    imported = new_objects(before)
    src_arm = next((o for o in imported if o.type == "ARMATURE"), None)
    if new and src_arm is not None:
        act = max(new, key=lambda a: len(a.fcurves))
        actions[nm] = retarget(src_arm, act, arm, nm)
    for ob in imported:
        bpy.data.objects.remove(ob, do_unlink=True)
set_fps()
log("actions:", {k: (tuple(round(x) for x in v.frame_range), anim_fps.get(k)) for k, v in actions.items()})
if arm.rotation_mode != "XYZ":
    arm.rotation_mode = "XYZ"


def skin_material(name, color_png, normal_tga, sss, rough):
    m, nt, b = principled(name)
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = image(color_png)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    if os.path.exists(normal_tga):
        nmt = nt.nodes.new("ShaderNodeTexImage")
        nmt.image = image(normal_tga, True)
        nm_ = nt.nodes.new("ShaderNodeNormalMap")
        nm_.inputs["Strength"].default_value = 0.8
        nt.links.new(nmt.outputs["Color"], nm_.inputs["Color"])
        nt.links.new(nm_.outputs["Normal"], b.inputs["Normal"])
    b.inputs["Roughness"].default_value = rough
    b.inputs["Subsurface Weight"].default_value = sss
    b.inputs["Subsurface Radius"].default_value = (0.012, 0.004, 0.003)
    return m


rtex = os.path.join(RB, "tex")
head_mat = skin_material("chaya_head", os.path.join(CTEX, "head_chaya.png"), os.path.join(rtex, "f152_head_normal.tga"), 0.07, 0.5)
body_mat = skin_material("chaya_body", os.path.join(CTEX, "body_chaya.png"), os.path.join(rtex, "f152_body_normal.tga"), 0.0, 0.75)
op, ont, ob_ = principled("chaya_opacity")
ot = ont.nodes.new("ShaderNodeTexImage")
ot.image = image(os.path.join(rtex, "f152_opacity_color.tga"))
mul = ont.nodes.new("ShaderNodeVectorMath")
mul.operation = "MULTIPLY"
mul.inputs[1].default_value = (0.12, 0.1, 0.1)
ont.links.new(ot.outputs["Color"], mul.inputs[0])
ont.links.new(mul.outputs["Vector"], ob_.inputs["Base Color"])
ont.links.new(ot.outputs["Alpha"], ob_.inputs["Alpha"])
log("chaya materials:", [base_name(s.material) for s in body.material_slots])
for i, slot in enumerate(body.material_slots):
    nm = base_name(slot.material).lower()
    slot.material = head_mat if "head" in nm else (op if "opacity" in nm else body_mat)

# pose her (idle, frame 1) away from the house and measure her head
arm.location = Vector((100.0, 0.0, 0.0))
ad = arm.animation_data_create()
if "idle" in actions:
    ad.action = actions["idle"]
scene.frame_set(1)
bpy.context.view_layer.update()
rest_rot = arm.rotation_euler.copy()
root_now = arm.matrix_world.translation.copy()


def bone_head(name):
    return arm.matrix_world @ arm.pose.bones[name].head


E = (bone_head("Bip01 REye") + bone_head("Bip01 LEye")) / 2
neck = bone_head("Bip01 Head")
F = E - neck
F.z = 0.0
F.normalize()
U = Vector((0, 0, 1))
S = F.cross(U).normalized()
EYE_OFF = E - root_now                       # root -> eyes, at the rest heading
ROOT_Z = Vector((0.0, 0.0, root_now.z))      # the clip keys the armature object at hip height above her feet
ks = E.z / 1.612
H = E - F * (0.064 * ks) + U * (0.024 * ks)
log("root", tuple(round(c, 3) for c in root_now), "eyes offset", tuple(round(c, 3) for c in EYE_OFF), "k %.3f" % ks)
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
R_HEAD = 0.088 * ks
log("head radii up %.3f back %.3f side %.3f front %.3f" % (R_UP, R_BACK, R_SIDE, R_FRONT))


def sph(phi, elev, r_):
    off = r_ - R_HEAD
    n = math.cos(elev) * (math.cos(phi) * F + math.sin(phi) * S) + math.sin(elev) * U
    hit = probe(H + n * 0.45, -n)
    if hit is not None and (hit - H).length < 0.2:
        return hit + n * off
    f_, sd, u = math.cos(elev) * math.cos(phi), math.cos(elev) * math.sin(phi), math.sin(elev)
    return H + F * (f_ * (R_FRONT if f_ > 0 else R_BACK)) + S * (sd * R_SIDE) + U * (u * (R_UP if u > 0 else R_SIDE * 0.95)) + n * off


def clear_face(p):
    d = p - E
    lat, fwd, up = d.dot(S), d.dot(F), d.dot(U)
    if -0.15 < up < 0.055 and fwd > -0.04 and abs(lat) < 0.078:
        return E + S * math.copysign(0.078, lat if abs(lat) > 1e-4 else 1.0) + F * fwd + U * up
    return p


def hairline(phi_deg):
    a = abs(phi_deg)
    return 36.0 - 48.0 * (a / 90.0) if a <= 90 else -12.0 - 33.0 * ((a - 90.0) / 90.0)


strands = []
N = 11000
for i in range(N):
    z = 1 - 2 * (i + 0.5) / N
    phi = (i * 2.399963) % (2 * math.pi)
    if phi > math.pi:
        phi -= 2 * math.pi
    elev = math.asin(z)
    if math.degrees(elev) < hairline(math.degrees(phi)) + rng.uniform(-2, 2):
        continue
    pts = []
    front = abs(phi) < math.radians(75)
    phi_t = math.copysign(math.radians(rng.uniform(70, 88)), phi if abs(phi) > 1e-3 else 1.0) if front else phi
    e_end = math.radians(rng.uniform(-22, -10))
    for k in range(9):
        s = k / 8
        ph = phi + (phi_t - phi) * (1.0 - (1.0 - s) ** 2.6)
        el = elev + (e_end - elev) * s
        pts.append(clear_face(sph(ph, el, R_HEAD + 0.004 + 0.016 * s)))
    q = pts[-1]
    outward = q - H
    outward.z = 0.0
    outward.normalize()
    Lh = rng.uniform(0.42, 0.72) * (1.0 if abs(phi) > math.radians(100) else 0.85)
    w1, w2 = rng.uniform(9, 16), rng.uniform(0, 6.28)
    side = outward.cross(U)
    for k in range(1, 13):
        t = k / 12
        p = q - U * (Lh * t) + outward * (0.012 + 0.05 * t ** 1.3) + side * (0.006 * math.sin(w1 * t + w2) * t)
        if abs(phi) < math.radians(120):
            p += F * (0.03 * t * t)
        pts.append(clear_face(p))
    strands.append(pts)
hair_mat = bpy.data.materials.new("hair")
hair_mat.use_nodes = True
hn = hair_mat.node_tree
for nd in list(hn.nodes):
    if nd.type != "OUTPUT_MATERIAL":
        hn.nodes.remove(nd)
dif = hn.nodes.new("ShaderNodeBsdfDiffuse")
dif.inputs["Color"].default_value = (0.004, 0.0035, 0.0035, 1)
glo = None
for idn in ("ShaderNodeBsdfGlossy", "ShaderNodeBsdfAnisotropic"):
    try:
        glo = hn.nodes.new(idn)
        break
    except Exception:       # noqa: BLE001
        continue
glo.inputs["Color"].default_value = (0.09, 0.075, 0.075, 1)
if "Roughness" in glo.inputs:
    glo.inputs["Roughness"].default_value = 0.3
mixs = hn.nodes.new("ShaderNodeMixShader")
mixs.inputs[0].default_value = 0.22
hn.links.new(dif.outputs[0], mixs.inputs[1])
hn.links.new(glo.outputs[0], mixs.inputs[2])
hn.links.new(mixs.outputs[0], hn.nodes["Material Output"].inputs["Surface"])
cu = bpy.data.curves.new("ChayaHair", "CURVE")
cu.dimensions = "3D"
cu.bevel_depth = 0.0006
cu.bevel_resolution = 0
cu.use_fill_caps = False
for s_ in strands:
    sp = cu.splines.new("POLY")
    sp.points.add(len(s_) - 1)
    for k, p in enumerate(s_):
        sp.points[k].co = (p.x, p.y, p.z, 1.0)
        sp.points[k].radius = 1.0 - 0.6 * k / (len(s_) - 1)
cu.materials.append(hair_mat)
hair = bpy.data.objects.new("ChayaHair", cu)
scene.collection.objects.link(hair)
log("hair strands:", len(strands))
cap_v, cap_f, grid = [], [], {}
NPH, NEL = 120, 48
for a in range(NPH):
    ph = -math.pi + 2 * math.pi * a / NPH
    for b in range(NEL):
        el = math.radians(-50 + 140 * b / (NEL - 1))
        if math.degrees(el) >= hairline(math.degrees(ph)) + 5:
            grid[(a, b)] = len(cap_v)
            cap_v.append(tuple(sph(ph, el, R_HEAD + 0.0025)))
for a in range(NPH):
    for b in range(NEL - 1):
        qd = [(a, b), ((a + 1) % NPH, b), ((a + 1) % NPH, b + 1), (a, b + 1)]
        if all(k in grid for k in qd):
            cap_f.append(tuple(grid[k] for k in qd))
cap_me = bpy.data.meshes.new("scalp_cap")
cap_me.from_pydata(cap_v, [], cap_f)
cap_me.update()
for poly in cap_me.polygons:
    poly.use_smooth = True
cap_me.materials.append(flat("scalp", (0.006, 0.005, 0.005), 0.6))
cap = bpy.data.objects.new("scalp_cap", cap_me)
scene.collection.objects.link(cap)
sc = bpy.data.curves.new("sindoor", "CURVE")
sc.dimensions = "3D"
sc.bevel_depth = 0.0012
sp = sc.splines.new("POLY")
sp.points.add(13)
for k in range(14):
    p = sph(0.0, math.radians(34 + 34 * k / 13), R_HEAD + 0.0045)
    sp.points[k].co = (p.x, p.y, p.z, 1.0)
sc.materials.append(flat("sindoor", (0.62, 0.0, 0.02), 0.6))
sindoor = bpy.data.objects.new("sindoor", sc)
scene.collection.objects.link(sindoor)


def stick_to_bone(ob, bone):
    mw = ob.matrix_world.copy()
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = bone
    bpy.context.view_layer.update()
    ob.matrix_world = mw


for ob in (hair, cap, sindoor):
    stick_to_bone(ob, "Bip01 Head")
eye_mat = glow("eye_glow", (1.0, 0.04, 0.012), 14.0)
for bn in ("Bip01 REye", "Bip01 LEye"):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=10, radius=0.0118, location=bone_head(bn) + F * 0.004)
    eo = bpy.context.active_object
    eo.data.materials.append(eye_mat)
    bpy.ops.object.shade_smooth()
    stick_to_bone(eo, bn)
    elo = point("eye_spill", bone_head(bn) + F * 0.03, 0.3, (1.0, 0.08, 0.03), 0.004)
    stick_to_bone(elo, bn)

# ------------------------------------------------------------------------------------------------ her performance
ad.action = None


def strip(name, f0_, f1_, speed=1.0):
    act_ = actions.get(name)
    if act_ is None:
        return
    trk = ad.nla_tracks.new()
    trk.name = "%s_%d" % (name, f0_)
    st = trk.strips.new(trk.name, int(f0_), act_)
    a0, a1 = act_.frame_range
    ln = max(1.0, a1 - a0)
    st.extrapolation = "NOTHING"
    st.blend_type = "REPLACE"
    st.scale = (FPS / anim_fps.get(name, FPS)) / speed
    st.repeat = max(1.0, (f1_ + 1 - f0_) / (ln * st.scale))
    log("strip", name, f0_, f1_, "scale %.3f repeat %.2f end %.1f" % (st.scale, st.repeat, st.frame_end))


def clip_z(name, f, f0_, speed=1.0):
    """height the clip gives the armature object at scene frame f (the walk's bounce), for a strip starting at f0_"""
    act_ = actions.get(name)
    fc = act_.fcurves.find("location", index=2) if act_ is not None else None
    if fc is None:
        return ROOT_Z.z
    a0, a1 = act_.frame_range
    sc = (FPS / anim_fps.get(name, FPS)) / speed
    return fc.evaluate(a0 + ((f - f0_) / sc) % max(1.0, a1 - a0))


def face_yaw(direction):
    """yaw so that her face (F at the rest heading) looks along `direction`"""
    return rest_rot.z + math.atan2(direction.y, direction.x) - math.atan2(F.y, F.x)


def root_for_eyes(eyes, direction):
    off = Matrix.Rotation(face_yaw(direction) - rest_rot.z, 3, "Z") @ EYE_OFF
    return eyes - off


CH = {}


def ch_key(f, loc, direction, interp="CONSTANT"):
    CH[int(f)] = (loc.copy(), face_yaw(direction), interp)


def ch_flush():
    for f in sorted(CH):
        loc, yaw, _ = CH[f]
        arm.location = loc
        arm.rotation_euler = (rest_rot.x, rest_rot.y, yaw)
        arm.keyframe_insert("location", frame=f)
        arm.keyframe_insert("rotation_euler", frame=f)
    set_interp(arm, lambda x: CH.get(x, (None, None, "CONSTANT"))[2])


# ================================================================================================ cameras
cams = {}


def camera(name, lens, fstop=None):
    cd = bpy.data.cameras.new(name)
    cd.lens = lens
    cd.sensor_width = 36.0
    cd.clip_start = 0.02
    cd.clip_end = 250.0
    if fstop:
        cd.dof.use_dof = True
        cd.dof.aperture_fstop = fstop
    co = bpy.data.objects.new(name, cd)
    co.rotation_mode = "XYZ"
    scene.collection.objects.link(co)
    cams[name] = co
    return co


def aim(co, f, pos, target):
    co.location = pos
    prev = co.rotation_euler.copy()
    co.rotation_euler = (target - pos).to_track_quat("-Z", "Y").to_euler("XYZ", prev)
    co.keyframe_insert("location", frame=f)
    co.keyframe_insert("rotation_euler", frame=f)


def finish_cam(co, shot, far=False):
    """linear keys inside the shot; optionally parked far away outside it (it carries a candle)"""
    f0_, f1_ = SHOTS[shot]
    if far:
        co.location = FAR
        co.keyframe_insert("location", frame=f0_ - 1)
        co.keyframe_insert("location", frame=f1_ + 1)
    set_interp(co, lambda x: "CONSTANT" if (x < f0_ or x >= f1_) else "LINEAR")


def sway(f, amp, seed):
    r_ = random.Random(seed * 1000 + f)
    return Vector((amp * math.sin(f * 0.11 + seed) + amp * 0.3 * math.sin(f * 0.37 + 2 * seed) + amp * 0.1 * (r_.random() - 0.5),
                   amp * math.cos(f * 0.09 + seed) + amp * 0.3 * math.sin(f * 0.29 + seed) + amp * 0.1 * (r_.random() - 0.5),
                   amp * 0.7 * math.sin(f * 0.07 + 2 * seed)))


def key_focus(co, f, dist):
    co.data.dof.focus_distance = dist
    co.data.dof.keyframe_insert("focus_distance", frame=f)


def import_candle(tag):
    before_ = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(MAP, "candle.glb"))
    objs = new_objects(before_)
    shade(objs)
    root = next(o for o in objs if o.parent is None)
    anchor = next((o for o in objs if o.name.startswith("flame_anchor")), None)
    log("candle", tag, root.name, "parts", len(objs), "anchor", anchor.name if anchor else None)
    return root, anchor, objs


HAND = Matrix.Translation((0.2, -0.205, -0.38)) @ Matrix.Rotation(math.radians(-12), 4, "Y") @ Matrix.Rotation(math.radians(-90), 4, "X")


def hold(root, co, m):
    root.parent = co
    root.matrix_parent_inverse = Matrix.Identity(4)
    root.matrix_basis = m


to_east = Vector((1, 0, 0))

# ------------------------------------------------------------------------------------------------ S1  corridor push-in
f0, f1 = SHOTS["S1"]
c1 = camera("cam_S1", 24.0)
x_a, x_b = 10.1, 7.0
far_x = -5.4
row3_y = cell(0, 3).y
for f in range(f0, f1 + 1):
    t = (f - f0) / (f1 - f0)
    e_ = t * t * (3 - 2 * t)
    pos = Vector((x_a + (x_b - x_a) * (0.15 * t + 0.85 * e_), row3_y, 1.58)) + sway(f, 0.01, 1)
    aim(c1, f, pos, Vector((far_x, row3_y + 0.05, 1.3)) + sway(f, 0.04, 2))
finish_cam(c1, "S1")
fa, fb = EV["s1_figure"]
ch_key(fa, Vector((far_x - 0.3, row3_y, 0.0)) + ROOT_Z, to_east)
ch_key(fb + 1, FAR, to_east)
strip("idle", fa, fb)
s1_back = point("S1_back", Vector((far_x - 0.9, row3_y, 2.6)), 90.0, (0.55, 0.65, 1.0), 0.25)
shot_light(s1_back, "S1", 90.0)

# ------------------------------------------------------------------------------------------------ S2  candle, the door, she is behind it
f0, f1 = SHOTS["S2"]
c2 = camera("cam_S2", 26.0)
door_x = cell(0, 3).x
y_start, y_stop = G(0, 0, -2.0).y, G(0, 0, -4.6).y
walk_end = EV["s2_walk_end"]
for f in range(f0, f1 + 1):
    if f <= walk_end:
        t = (f - f0) / (walk_end - f0)
        prog = 1.0 - (1.0 - t) ** 1.8
        bob = 0.014 * abs(math.sin(t * math.pi * 4.0)) * (1.0 - t)
    else:
        prog, bob = 1.0, 0.0
    pos = Vector((door_x + 0.05, y_start + (y_stop - y_start) * prog, 1.56 + bob)) + sway(f, 0.006, 3)
    aim(c2, f, pos, Vector((door_x - 0.05, pos.y + 3.0, 1.38)) + sway(f, 0.02, 4))
    if f >= f1 - 44:
        c2.data.lens = 26.0 + 6.0 * ((f - (f1 - 44)) / 44.0) ** 1.5
        c2.data.keyframe_insert("lens", frame=f)
finish_cam(c2, "S2", far=True)
linear_keys(c2.data)
cand2, anchor2, cand2_objs = import_candle("hand")
hold(cand2, c2, HAND)
fl2, fli2 = make_flame("flame_hand", anchor2 or cand2, Vector((0, 0, 0)) if anchor2 else Vector((0.0024, 0, 0.1155)), 1.0, 2.0)
flame_life(fl2, fli2, f0, f1, 2.0, 21)
fill2 = point("S2_fill", Vector((0, 0, 0)), 0.0, (1.0, 0.55, 0.25), 0.06)
excluded = False
try:
    col = bpy.data.collections.new("not_lit_by_fill")
    for ob in cand2_objs + [fl2]:
        if ob.type == "MESH":
            col.objects.link(ob)
    fill2.light_linking.receiver_collection = col
    for it in col.collection_objects:
        it.light_linking.link_state = "EXCLUDE"
    excluded = True
except Exception as ex:     # noqa: BLE001
    log("light linking unavailable:", ex)
    try:
        fill2.light_linking.receiver_collection = None
    except Exception:       # noqa: BLE001
        pass
if excluded:                                 # the candle lights the room, but does not burn itself out white
    fill2.parent = anchor2 or cand2
    fill2.location = Vector((0, 0, 0.03))
    shot_light(fill2, "S2", 20.0)
else:
    fill2.parent = c2
    fill2.location = Vector((0.15, 0.25, 0.15))
    shot_light(fill2, "S2", 7.0)
log("S2 fill light linked:", excluded)
door = bpy.data.objects.get("door_3")
d0, d1 = EV["s2_door"]
if door is not None:
    r0 = door.rotation_euler.copy()
    cam_end = Vector((door_x, y_stop, 1.5))
    best, best_d = 1.0, -1.0
    for sgn in (1.0, -1.0):
        door.rotation_euler = (r0.x, r0.y, r0.z + sgn * math.radians(95))
        bpy.context.view_layer.update()
        ctr = door.matrix_world @ (sum((Vector(c) for c in door.bound_box), Vector()) / 8.0)
        d = (ctr - cam_end).length
        if d > best_d:
            best, best_d = sgn, d
    door.rotation_euler = r0
    door.keyframe_insert("rotation_euler", frame=1)
    door.keyframe_insert("rotation_euler", frame=d0)
    door.rotation_euler = (r0.x, r0.y, r0.z + best * math.radians(28))
    door.keyframe_insert("rotation_euler", frame=d0 + 22)
    door.rotation_euler = (r0.x, r0.y, r0.z + best * math.radians(96))
    door.keyframe_insert("rotation_euler", frame=d1)
    log("door_3 swings", best)
else:
    log("WARNING: no door_3")
ch_key(f0, Vector((door_x - 0.12, G(0, 0, -8.05).y, 0.0)) + ROOT_Z, Vector((0, -1, 0)))
ch_key(f1 + 1, FAR, to_east)
strip("idle", f0, f1, 0.8)

# ------------------------------------------------------------------------------------------------ S3  the pooja altar
f0, f1 = SHOTS["S3"]
c3 = camera("cam_S3", 35.0, 2.8)
altar = G(*META["altar"]["pos"])
order = ["kalash", "diya", "coconut", "kumkum", "kapoor", "gangajal"]
diya_item = None
for it in META["items"]:
    ob = bpy.data.objects.get(it.get("name", "item_" + it["id"]))
    if ob is None:
        log("missing item", it)
        continue
    k = order.index(it["id"]) if it["id"] in order else 0
    if it["id"] == "kalash":
        p = altar + Vector((0.0, 0.08, 0.0))
    else:
        a = math.radians(-150 + (k - 1) * 30)
        p = altar + Vector((math.cos(a) * 0.36, 0.08 + math.sin(a) * 0.3, 0.0))
    ob.location = p
    ob.scale = (1.2, 1.2, 1.2)
    if it["id"] == "diya":
        diya_item = ob
flames3 = []
if diya_item is not None:
    flames3.append(make_flame("diya_flame", diya_item, Vector((0.0, 0.0, 0.078)), 1.0, 2.5))
    for k in range(8):
        a = k * math.pi / 4
        rr = 0.875 / max(abs(math.cos(a)), abs(math.sin(a)))
        dy = bpy.data.objects.new("diya_ring_%d" % k, diya_item.data)
        scene.collection.objects.link(dy)
        dy.location = Vector((altar.x + math.cos(a) * rr, altar.y + math.sin(a) * rr, 0.18))
        dy.rotation_euler = (0, 0, rng.uniform(0, 6.28))
        flames3.append(make_flame("ring_flame_%d" % k, dy, Vector((0.0, 0.0, 0.078)), 0.9, 1.6))
for k, (fl, li) in enumerate(flames3):
    flame_life(fl, li, f0, f1, li.data.energy, 30 + k)
for f in range(f0, f1 + 1):
    t = (f - f0) / (f1 - f0)
    a = math.radians(212 + 64 * t)
    rad = 2.15 - 0.3 * t
    pos = altar + Vector((math.cos(a) * rad, math.sin(a) * rad, 0.5 + 0.3 * t))
    tgt = altar + Vector((0, 0.05, 0.16))
    aim(c3, f, pos, tgt)
    key_focus(c3, f, (tgt - pos).length)
finish_cam(c3, "S3")
linear_keys(c3.data)
aura = point("S3_aura", altar + Vector((0.0, 0.3, 1.25)), 26.0, (1.0, 0.6, 0.3), 0.35)
shot_light(aura, "S3", 26.0)
kick = area("S3_kick", altar + Vector((-1.6, 2.4, 2.4)), altar + Vector((0, 0, 0.3)), 60.0, (1.0, 0.75, 0.5), 1.2)
shot_light(kick, "S3", 60.0)

# ------------------------------------------------------------------------------------------------ S4-S7  the long corridor (row 10)
east, west = cell(11, 10), cell(5, 10)
to_cam = (east - west).normalized()          # she faces the camera (east)
to_her = -to_cam


def at(s):
    """point on the corridor floor, `s` metres west of the east cell centre"""
    return east + to_her * s


f0, f1 = SHOTS["S4"]
c4 = camera("cam_S4", 30.0)
for f in range(f0, f1 + 1):
    pos = at(-0.4) + Vector((0, 0.05, 1.56)) + sway(f, 0.005, 5)
    aim(c4, f, pos, at(15.0) + Vector((0, 0.05, 1.22)))
finish_cam(c4, "S4")
j1, j2 = EV["s4_jump1"], EV["s4_jump2"]
ch_key(f0, at(14.0) + ROOT_Z, to_cam)
ch_key(j1, at(9.3) + ROOT_Z, to_cam)
ch_key(j2, at(5.6) + ROOT_Z, to_cam)
strip("idle", f0, f1, 0.7)
back4 = point("S4_back", at(16.2) + Vector((0, 0, 2.3)), 70.0, (1.0, 0.25, 0.1), 0.15)
shot_light(back4, "S4", 70.0)

f0, f1 = SHOTS["S5"]
c5 = camera("cam_S5", 40.0, 2.0)
s_start = 8.6
for f in range(f0, f1 + 1):
    t = (f - f0) / (f1 - f0)
    s_her = s_start - 1.15 * (f - f0) / FPS
    root = at(s_her) + Vector((0, 0, clip_z("walk", f, f0)))
    ch_key(f, root, to_cam, "LINEAR" if f < f1 else "CONSTANT")
    head = root + Vector((0, 0, EYE_OFF.z - 0.02))
    cam = at(0.2 + 0.9 * t) + Vector((0.0, -0.18, 0.92)) + sway(f, 0.005, 6)
    aim(c5, f, cam, head)
    key_focus(c5, f, (head - cam).length)
finish_cam(c5, "S5")
linear_keys(c5.data)
strip("walk", f0, f1)
rim5 = area("S5_rim", at(s_start + 3.0) + Vector((0, 0, 2.2)), at(s_start - 2.0) + Vector((0, 0, 1.4)), 55.0, (1.0, 0.2, 0.08), 0.9)
shot_light(rim5, "S5", 55.0)
s_end = s_start - 1.15 * (f1 - f0) / FPS

f0, f1 = SHOTS["S6"]
c6 = camera("cam_S6", 50.0, 1.6)
for f in range(f0, f1 + 1):
    pos = at(0.5) + Vector((0, 0.05, 1.42)) + sway(f, 0.002, 7)
    aim(c6, f, pos, at(3.0) + Vector((0, 0.05, 1.36)))
    key_focus(c6, f, 0.42)
finish_cam(c6, "S6", far=True)
linear_keys(c6.data)
cand6, anchor6, _ = import_candle("close")
hold(cand6, c6, Matrix.Translation((0.0, -0.105, -0.42)) @ Matrix.Rotation(math.radians(-90), 4, "X"))
fl6, fli6 = make_flame("flame_close", anchor6 or cand6, Vector((0, 0, 0)) if anchor6 else Vector((0.0024, 0, 0.1155)), 1.0, 2.0)
flame_life(fl6, fli6, f0, f1, 2.0, 61, die_at=EV["s6_die"])
fill6 = point("S6_fill", Vector((0.25, 0.3, 0.1)), 4.0, (1.0, 0.5, 0.2), 0.3)
fill6.parent = c6
key_energy(fill6, 1, 0.0)
key_energy(fill6, f0 - 1, 0.0)
key_energy(fill6, f0, 4.0)
key_energy(fill6, EV["s6_die"], 4.0)
key_energy(fill6, EV["s6_die"] + 7, 0.0)
linear_keys(fill6.data)
ch_key(f0, at(min(s_end, 3.4)) + ROOT_Z, to_cam)
strip("idle", f0, f1, 0.6)

f0, f1 = SHOTS["S7"]
c7 = camera("cam_S7", 30.0)
cam7 = at(0.5) + Vector((0, 0.05, 1.55))
lunge, black7 = EV["s7_lunge"], EV["s7_black"]
for f in range(f0, f1 + 1):
    t = max(0.0, min(1.0, (f - lunge) / 7.0))
    d = 1.5 - (1.5 - 0.26) * (1 - (1 - t) ** 3)
    eyes = cam7 + to_her * d + Vector((0, 0, -0.03 + 0.02 * t))
    ch_key(f, root_for_eyes(eyes, to_cam), to_cam, "LINEAR" if f < f1 else "CONSTANT")
    shake = sway(f, 0.002 if f < lunge else 0.012 + 0.02 * (1 - t * 0.5), 8)
    if f >= lunge:
        r7 = random.Random(f)
        shake += Vector((0.02 * (r7.random() - 0.5), 0.02 * (r7.random() - 0.5), 0.02 * (r7.random() - 0.5)))
    aim(c7, f, cam7 + shake, cam7 + to_her * 3.0 + Vector((0, 0, -0.03)))
finish_cam(c7, "S7")
strip("idle", f0, f1, 1.4)
strobe = point("S7_strobe", cam7 + to_her * 0.12 + Vector((0.0, 0.12, -0.32)), 0.0, (1.0, 0.86, 0.8), 0.06)
key_energy(strobe, 1, 0.0)
key_energy(strobe, f0 - 1, 0.0)
r7 = random.Random(77)
for f in range(f0, f1 + 2):
    on = lunge - 2 <= f < black7 and (r7.random() > 0.3 or f in (lunge, lunge + 1, lunge + 6))
    key_energy(strobe, f, 22.0 if on else 0.0)
set_interp(strobe.data, lambda x: "CONSTANT")
glimmer = point("S7_glimmer", cam7 + to_her * 1.0 + Vector((0, 0, 0.2)), 0.0, (1.0, 0.1, 0.05), 0.2)
shot_light(glimmer, "S7", 1.2)

# Chaya stays far away outside her shots
ch_key(1, FAR, to_cam)
ch_key(SHOTS["S3"][0], FAR, to_cam)
ch_key(SHOTS["S8"][0], FAR, to_cam)
ch_flush()

# ================================================================================================ S8  title
f0, f1 = SHOTS["S8"]
TT = Vector((300.0, 0.0, 0.0))
title = json.load(open(os.path.join(REPO, "tools", "logo", "chaya_title.json")))
tcu = bpy.data.curves.new("title", "CURVE")
tcu.dimensions = "2D"
tcu.fill_mode = "BOTH"
tcu.extrude = 0.05
tcu.bevel_depth = 0.01
tcu.bevel_resolution = 4
for contour in title["contours"]:
    sp = tcu.splines.new("BEZIER")
    sp.bezier_points.add(len(contour) - 1)
    for bp in sp.bezier_points:
        bp.handle_left_type = "FREE"
        bp.handle_right_type = "FREE"
    n_ = len(contour)
    for k, seg in enumerate(contour):
        p0, c1_, c2_, p3 = seg
        bp = sp.bezier_points[k]
        bp.co = (p0[0], p0[1], 0.0)
        bp.handle_right = (c1_[0], c1_[1], 0.0)
        sp.bezier_points[(k + 1) % n_].handle_left = (c2_[0], c2_[1], 0.0)
    sp.use_cyclic_u = True
tm, tnt, tb = principled("title_blood")
tb.inputs["Base Color"].default_value = (0.3, 0.0, 0.008, 1)
tb.inputs["Metallic"].default_value = 0.4
tb.inputs["Roughness"].default_value = 0.25
tb.inputs["Coat Weight"].default_value = 0.7
tb.inputs["Emission Color"].default_value = (0.7, 0.03, 0.0, 1)
tb.inputs["Emission Strength"].default_value = 0.12
tcu.materials.append(tm)
tob = bpy.data.objects.new("CHAYA_title", tcu)
scene.collection.objects.link(tob)
tob.scale = (0.58, 0.58, 0.58)
tob.rotation_euler = (math.radians(90), 0, 0)
tob.location = TT + Vector((0, 0, 1.0))
bpy.ops.mesh.primitive_plane_add(size=14, location=TT + Vector((0, 0, 0.69)))
bpy.context.active_object.data.materials.append(flat("title_floor", (0.018, 0.013, 0.011), 0.3))
bpy.ops.mesh.primitive_plane_add(size=14, location=TT + Vector((0, 3.0, 4.0)), rotation=(math.radians(90), 0, 0))
bpy.context.active_object.data.materials.append(flat("title_back", (0.01, 0.008, 0.008), 0.9))
for k, (dx, e_) in enumerate(((-1.0, 30.0), (1.0, 30.0), (0.0, 20.0))):
    flo = point("fire_%d" % k, TT + Vector((dx, -0.6, 0.75)), e_, (1.0, 0.42, 0.12), 0.25)
    r_ = random.Random(90 + k)
    key_energy(flo, f0 - 1, 0.0)
    for f in range(f0, f1 + 1):
        u = min(1.0, (f - f0) / 10.0)
        key_energy(flo, f, e_ * u * (0.75 + 0.35 * r_.random()))
    linear_keys(flo.data)
rim8 = area("title_rim", TT + Vector((0, 1.6, 2.6)), TT + Vector((0, 0, 1.0)), 90.0, (1.0, 0.16, 0.05), 2.0)
shot_light(rim8, "S8", 90.0)
top8 = area("title_top", TT + Vector((0, -1.2, 3.2)), TT + Vector((0, 0, 1.0)), 18.0, (1.0, 0.8, 0.65), 3.0)
shot_light(top8, "S8", 18.0)
ember_m = glow("ember_glow", (1.0, 0.38, 0.06), 30.0)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=0.006, location=FAR)
ember_src = bpy.context.active_object
ember_src.data.materials.append(ember_m)
er = random.Random(4)
for k in range(150):
    x0_, y0_ = er.uniform(-1.9, 1.9), er.uniform(-1.2, 0.8)
    born = int(er.uniform(f0 - 80, f1 - 20))
    life = int(er.uniform(70, 140))
    sc_ = er.uniform(0.5, 1.7)
    rise = er.uniform(1.6, 2.8)
    a_, b_ = max(f0, born), min(f1 + 1, born + life)
    if b_ - a_ < 6:
        continue
    eo = bpy.data.objects.new("ember_%d" % k, ember_src.data)
    scene.collection.objects.link(eo)
    eo.scale = (sc_, sc_, sc_)
    eo.location = FAR
    eo.keyframe_insert("location", frame=1)
    frames_ = list(range(a_, b_, 3))
    for f in frames_:
        u = (f - born) / life
        eo.location = TT + Vector((x0_ + 0.18 * math.sin(f * 0.05 + k) * u, y0_ + 0.12 * math.cos(f * 0.04 + k) * u, 0.7 + u * rise))
        eo.keyframe_insert("location", frame=f)
    eo.location = FAR
    eo.keyframe_insert("location", frame=b_)
    last = frames_[-1]
    set_interp(eo, lambda x, last=last: "CONSTANT" if (x == 1 or x >= last) else "LINEAR")
c8 = camera("cam_S8", 50.0, 3.2)
for f in range(f0, f1 + 1):
    t = (f - f0) / (f1 - f0)
    e_ = t * t * (3 - 2 * t)
    pos = TT + Vector((0.0, -5.0 + 1.25 * e_, 1.05 + 0.12 * e_))
    aim(c8, f, pos, TT + Vector((0, 0, 1.0)))
    key_focus(c8, f, (TT + Vector((0, 0, 1.0)) - pos).length)
finish_cam(c8, "S8")
linear_keys(c8.data)

# ================================================================================================ edit points + render settings
for name, (a, b) in SHOTS.items():
    mk = scene.timeline_markers.new(name, frame=a)
    mk.camera = cams["cam_" + name]
scene.camera = cams["cam_S1"]

rs_ = scene.render
rs_.engine = "CYCLES"
rs_.resolution_x, rs_.resolution_y, rs_.resolution_percentage = T["width"], T["height"], 100
rs_.use_motion_blur = False             # render time: 20 runners x 4 vCPU
rs_.motion_blur_shutter = 0.5
for owner in (scene.cycles, rs_):
    try:
        owner.motion_blur_position = "START"
        log("motion blur position set on", type(owner).__name__)
        break
    except Exception:       # noqa: BLE001
        continue
rs_.use_persistent_data = True
rs_.image_settings.file_format = "PNG"
rs_.image_settings.color_mode = "RGB"
rs_.image_settings.color_depth = "8"
rs_.filepath = "//frames/f_"
cy = scene.cycles
cy.device = "CPU"
cy.samples = 24
cy.use_adaptive_sampling = True
cy.adaptive_threshold = 0.06
cy.adaptive_min_samples = 10
cy.use_denoising = True
for k_, v_ in (("denoiser", "OPENIMAGEDENOISE"), ("denoising_input_passes", "RGB_ALBEDO_NORMAL"), ("denoising_prefilter", "ACCURATE")):
    try:
        setattr(cy, k_, v_)
    except Exception as ex:     # noqa: BLE001
        log("denoise setting", k_, ex)
cy.max_bounces = 3
cy.diffuse_bounces = 2
cy.glossy_bounces = 1
cy.transmission_bounces = 1
cy.volume_bounces = 0
cy.transparent_max_bounces = 12
cy.sample_clamp_direct = 0.0
cy.sample_clamp_indirect = 6.0
cy.blur_glossy = 1.0
try:
    cy.use_light_tree = True
except Exception:       # noqa: BLE001
    pass
for vt, look in (("AgX", "AgX - Medium High Contrast"), ("AgX", "Medium High Contrast"), ("AgX", "None"), ("Filmic", "Medium High Contrast")):
    try:
        scene.view_settings.view_transform = vt
        scene.view_settings.look = look
        log("view", vt, look)
        break
    except Exception:       # noqa: BLE001
        continue
scene.view_settings.exposure = 0.9
vl = scene.view_layers[0]
vl.use_pass_mist = True
scene.use_nodes = True
tree = scene.node_tree
rl = tree.nodes.get("Render Layers") or tree.nodes.new("CompositorNodeRLayers")
comp = tree.nodes.get("Composite") or tree.nodes.new("CompositorNodeComposite")
fogf = tree.nodes.new("CompositorNodeMath")
fogf.operation = "MULTIPLY"
fogf.inputs[1].default_value = 0.5
fog = tree.nodes.new("CompositorNodeMixRGB")
fog.blend_type = "MIX"
fog.inputs[2].default_value = (0.022, 0.02, 0.024, 1)
glare = tree.nodes.new("CompositorNodeGlare")
glare.glare_type = "FOG_GLOW"
glare.quality = "HIGH"
glare.threshold = 1.2
glare.size = 8
tree.links.new(rl.outputs["Mist"], fogf.inputs[0])
tree.links.new(fogf.outputs[0], fog.inputs[0])
tree.links.new(rl.outputs["Image"], fog.inputs[1])
tree.links.new(fog.outputs[0], glare.inputs["Image"])
tree.links.new(glare.outputs["Image"], comp.inputs["Image"])

json.dump({"shots": SHOTS, "cams": {k: v.name for k, v in cams.items()}}, open(os.path.join(os.path.dirname(OUT), "scene_info.json"), "w"))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=OUT, compress=True)
log("saved", OUT)
