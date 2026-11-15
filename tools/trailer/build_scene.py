"""Builds the Moulika trailer scene in Blender.

    blender -b -P tools/trailer/build_scene.py -- ASSETS_DIR OUT.blend [preview]

ASSETS_DIR holds school/ (school.glb, school_meta.json, lightmaps/), tex/ (the photo textures), sky/night.hdr and
moulika.glb. The school is lit the way the game lights it: every surface shows its photo texture times its baked
lightmap, so the rooms look exactly like the game, render without noise, and cost almost nothing. Moulika is a real
Cycles character lit by per-shot lights. Shots come from shots.py: each has its own camera (bound to a timeline
marker), Moulika's clip, path and lights, and optional light flicker. The compositor adds depth haze, bloom, depth
of field and motion blur; grading and grain are added when the frames are put together.
"""
import bpy
import json
import math
import os
import sys

import numpy as np
from mathutils import Vector, Euler

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import shots as SH  # noqa: E402

FPS = SH.FPS
HEIGHT = 1.68


def log(*a):
    print("[trailer]", *a, flush=True)


# --------------------------------------------------------------------------------------------- the game's materials
MAP = {
    "plaster": ["plaster", 0.75], "plaster_ext": ["plaster_rough", 0.8], "ceiling": ["plaster", 0.85], "plinth": ["plaster_rough", 0.85],
    "floor_cement": ["concrete_floor", 0.35], "floor_terrazzo": ["terrazzo", 0.3], "floor_tiles": ["tiles_white", 0.2],
    "floor_kota": ["stone_floor", 0.5], "floor_veranda": ["red_tiles", 0.45], "dado_green": ["paint_chipped", 0.9],
    "dado_blue": ["paint_chipped", 0.9], "dado_red": ["paint_chipped", 0.9], "dado_brown": ["paint_chipped", 0.9],
    "dado_tiles": ["tiles_white", 0.2], "wood": ["wood", 0.6], "wood_dark": ["wood", 0.85], "wood_old": ["wood_old", 0.4],
    "wood_painted_blue": ["wood_painted", 0.9], "wood_painted_green": ["wood_painted", 0.9], "wood_door_main": ["wood_old", 0.7],
    "wood_plank": ["wood_old", 0.35], "wood_handle": ["wood", 0.6], "metal_green": ["metal_painted", 0.9],
    "metal_grey": ["metal_painted", 0.92], "metal_white": ["metal_painted", 0.95], "rust": ["rust", 0.25],
    "steel": ["metal_brushed", 0.7], "steel_face": ["metal_brushed", 0.7], "aluminium": ["metal_brushed", 0.6],
    "aluminium_soot": ["metal_brushed", 0.9], "brass": ["metal_brushed", 0.92], "iron_old": ["rust", 0.8],
    "chalkboard": ["slate", 0.85], "concrete": ["concrete", 0.3], "concrete_wet": ["concrete", 0.6], "ground_dirt": ["ground_dirt", 0.3],
    "ground_court": ["ground_court", 0.4], "brick_path": ["brick", 0.4], "brick_soot": ["brick", 0.85], "roof": ["concrete", 0.5],
    "sack": ["hessian", 0.4], "fabric_mat": ["hessian", 0.7], "curtain": ["fabric", 0.92], "felt": ["fabric", 0.95],
    "felt_green": ["fabric", 0.95], "file_cloth": ["fabric", 0.95], "bark": ["bark", 0.3], "cardboard": ["cardboard", 0.5],
    "paper": ["cardboard", 0.97], "register_red": ["cardboard", 0.95], "register_blue": ["cardboard", 0.95], "book_red": ["cardboard", 0.95],
    "book_blue": ["cardboard", 0.95], "book_green": ["cardboard", 0.95], "book_brown": ["cardboard", 0.9], "book_black": ["cardboard", 0.97],
    "clay": ["concrete", 0.92], "ceramic": ["tiles_white", 0.9], "ash": ["concrete", 0.6], "broom": ["hessian", 0.6],
    "rope": ["hessian", 0.7], "cane": ["wood", 0.8], "tag_white": ["cardboard", 0.95], "tag_yellow": ["cardboard", 0.95],
}
AMBIENT = (0.012, 0.014, 0.02)


def base_name(n):
    return n.split(".")[0] if "." in n and n.rsplit(".", 1)[1].isdigit() else n


class Lib:
    def __init__(self, A, meta):
        self.A = A
        self.meta = meta
        self.photos = {}
        self.avg = {}
        self.lms = {}
        self.mats = {}
        self.gain = float(meta.get("lm_scale", 4.0)) * 0.62
        self.base = meta.get("base_colors", {})
        self.emit = meta.get("emit", {})
        # one value per room that scales its light (for flickering tubes); the materials read it through a driver
        self.room_power = {}

    def photo(self, slot):
        if slot in self.photos:
            return self.photos[slot]
        img = None
        for ext in ("jpg", "png"):
            p = os.path.join(self.A, "tex", slot, "diff." + ext)
            if os.path.exists(p):
                img = bpy.data.images.load(p, check_existing=True)
                break
        self.photos[slot] = img
        if img is not None:
            w, h = img.size
            px = np.empty(w * h * 4, np.float32)
            img.pixels.foreach_get(px)
            rgb = px.reshape(-1, 4)[:, :3]
            lin = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
            self.avg[slot] = max(float(lin.mean()), 0.03)
        return img

    def lightmap(self, obj_name):
        e = self.meta.get("lightmaps", {}).get(obj_name)
        if not e:
            return None
        f = e["file"]
        if f not in self.lms:
            p = os.path.join(self.A, "school", f)
            self.lms[f] = bpy.data.images.load(p, check_existing=True) if os.path.exists(p) else None
            if self.lms[f] is not None:
                self.lms[f].colorspace_settings.name = "sRGB"
        return self.lms[f]

    def material(self, mname, own_img, lm_img, flat, uv0, uv1, room):
        key = (mname, own_img.name if own_img else "", lm_img.name if lm_img else "flat%.3f" % flat, room, uv0, uv1)
        if key in self.mats:
            return self.mats[key]
        m = bpy.data.materials.new("env_%s_%s" % (mname, lm_img.name if lm_img else "flat"))
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        L = nt.links
        if mname in ("glass", "glass_dirty"):
            tr = nt.nodes.new("ShaderNodeBsdfTransparent")
            em = nt.nodes.new("ShaderNodeEmission")
            em.inputs["Color"].default_value = (0.25, 0.32, 0.34, 1)
            em.inputs["Strength"].default_value = 0.35
            mix = nt.nodes.new("ShaderNodeMixShader")
            mix.inputs["Fac"].default_value = 0.22 if mname == "glass" else 0.4
            L.new(tr.outputs[0], mix.inputs[1])
            L.new(em.outputs[0], mix.inputs[2])
            L.new(mix.outputs[0], out.inputs["Surface"])
            self.mats[key] = m
            return m
        uvn0 = nt.nodes.new("ShaderNodeUVMap")
        uvn0.uv_map = uv0
        info = MAP.get(mname, ["", 1.0])
        base = self.base.get(mname, [0.5, 0.5, 0.5])
        if own_img is not None:
            img, tint, base = own_img, 0.0, [0.5, 0.5, 0.5]
        elif mname == "leaves":
            img, tint, base = None, 1.0, [0.3, 0.45, 0.2]
        else:
            img = self.photo(info[0]) if info[0] else None
            tint = info[1]
        if img is not None:
            tex = nt.nodes.new("ShaderNodeTexImage")
            tex.image = img
            tex.interpolation = "Linear"
            L.new(uvn0.outputs["UV"], tex.inputs["Vector"])
            tcol = tex.outputs["Color"]
        else:
            rgb = nt.nodes.new("ShaderNodeRGB")
            rgb.outputs[0].default_value = (1, 1, 1, 1)
            tcol = rgb.outputs[0]
        basen = nt.nodes.new("ShaderNodeRGB")
        basen.outputs[0].default_value = (base[0], base[1], base[2], 1)
        if tint > 0.0:
            dot = nt.nodes.new("ShaderNodeVectorMath")
            dot.operation = "DOT_PRODUCT"
            dot.inputs[1].default_value = (1 / 3, 1 / 3, 1 / 3)
            L.new(tcol, dot.inputs[0])
            div = nt.nodes.new("ShaderNodeMath")
            div.operation = "DIVIDE"
            div.inputs[1].default_value = self.avg.get(info[0], 0.5) if img is not None else 1.0
            L.new(dot.outputs["Value"], div.inputs[0])
            clamp = nt.nodes.new("ShaderNodeClamp")
            clamp.inputs["Min"].default_value = 0.0
            clamp.inputs["Max"].default_value = 2.2
            L.new(div.outputs[0], clamp.inputs["Value"])
            scl = nt.nodes.new("ShaderNodeVectorMath")
            scl.operation = "SCALE"
            L.new(basen.outputs[0], scl.inputs[0])
            L.new(clamp.outputs[0], scl.inputs["Scale"])
            mix = nt.nodes.new("ShaderNodeMix")
            mix.data_type = "RGBA"
            mix.inputs["Factor"].default_value = tint
            L.new(tcol, mix.inputs[6])
            L.new(scl.outputs[0], mix.inputs[7])
            col = mix.outputs[2]
        else:
            col = tcol
        # light: the baked lightmap (second UV set) or a flat value, scaled per room for flicker
        if lm_img is not None:
            uvn1 = nt.nodes.new("ShaderNodeUVMap")
            uvn1.uv_map = uv1
            lmt = nt.nodes.new("ShaderNodeTexImage")
            lmt.image = lm_img
            lmt.interpolation = "Linear"
            lmt.extension = "EXTEND"
            L.new(uvn1.outputs["UV"], lmt.inputs["Vector"])
            light = lmt.outputs["Color"]
            g = self.gain
        else:
            fl = nt.nodes.new("ShaderNodeRGB")
            fl.outputs[0].default_value = (flat, flat, flat * 1.05, 1)
            light = fl.outputs[0]
            g = 1.0
        power = nt.nodes.new("ShaderNodeValue")
        power.name = "room_power"
        power.outputs[0].default_value = 1.0
        if room:
            fc = power.outputs[0].driver_add("default_value")
            fc.driver.type = "AVERAGE"
            var = fc.driver.variables.new()
            var.type = "SINGLE_PROP"
            var.targets[0].id_type = "SCENE"
            var.targets[0].id = bpy.context.scene
            var.targets[0].data_path = '["power_%s"]' % room
        gmul = nt.nodes.new("ShaderNodeMath")
        gmul.operation = "MULTIPLY"
        gmul.inputs[1].default_value = g
        L.new(power.outputs[0], gmul.inputs[0])
        lsc = nt.nodes.new("ShaderNodeVectorMath")
        lsc.operation = "SCALE"
        L.new(light, lsc.inputs[0])
        L.new(gmul.outputs[0], lsc.inputs["Scale"])
        amb = nt.nodes.new("ShaderNodeVectorMath")
        amb.operation = "ADD"
        amb.inputs[1].default_value = AMBIENT
        L.new(lsc.outputs[0], amb.inputs[0])
        lit = nt.nodes.new("ShaderNodeVectorMath")
        lit.operation = "MULTIPLY"
        L.new(col, lit.inputs[0])
        L.new(amb.outputs[0], lit.inputs[1])
        final = lit.outputs[0]
        glow = float(self.emit.get(mname, 0.0)) * 0.25
        if glow > 0:
            gl = nt.nodes.new("ShaderNodeVectorMath")
            gl.operation = "SCALE"
            gl.inputs["Scale"].default_value = glow * 1.6
            L.new(basen.outputs[0], gl.inputs[0])
            gm = nt.nodes.new("ShaderNodeVectorMath")
            gm.operation = "MULTIPLY"
            L.new(gl.outputs[0], gm.inputs[0])
            L.new(power.outputs[0], gm.inputs[1])
            add = nt.nodes.new("ShaderNodeVectorMath")
            add.operation = "ADD"
            L.new(final, add.inputs[0])
            L.new(gm.outputs[0], add.inputs[1])
            final = add.outputs[0]
        em = nt.nodes.new("ShaderNodeEmission")
        em.inputs["Strength"].default_value = 1.0
        L.new(final, em.inputs["Color"])
        L.new(em.outputs[0], out.inputs["Surface"])
        # the walls only show their baked light: they never need to be sampled as lamps
        try:
            m.cycles.emission_sampling = "NONE"
        except Exception:
            pass
        self.mats[key] = m
        return m


def room_of(meta, x, y):
    for r in meta["rooms"]:
        x0, y0, x1, y1 = r["rect"]
        if x0 <= x <= x1 and y0 <= y <= y1:
            return r["name"]
    return None


def import_school(A, lib):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(A, "school", "school.glb"))
    objs = [o for o in bpy.data.objects if o not in before]
    n_mat = 0
    for o in objs:
        if o.type != "MESH":
            continue
        uvs = [u.name for u in o.data.uv_layers]
        uv0 = uvs[0] if uvs else ""
        uv1 = uvs[1] if len(uvs) > 1 else uv0
        nm = base_name(o.name)
        lm = lib.lightmap(nm)
        flat = 0.03 if nm == "arch_roof" else 0.16
        # flicker groups: the room a chunk belongs to (arch_class5, furn_class5 -> class5)
        room = nm.split("_", 1)[1] if nm.startswith(("arch_", "furn_")) else None
        for slot in o.material_slots:
            m0 = slot.material
            mname = base_name(m0.name) if m0 else "plaster"
            own = None
            if mname.startswith("rodin_") and m0 and m0.use_nodes:
                for n in m0.node_tree.nodes:
                    if n.type == "TEX_IMAGE" and n.image is not None:
                        # the base colour texture is the one wired to Base Color
                        if any(l.to_socket.name == "Base Color" for l in n.outputs["Color"].links):
                            own = n.image
                            break
            slot.material = lib.material(mname, own, lm, flat, uv0, uv1 if lm else uv0, room)
            n_mat += 1
    log("school imported: %d objects, %d material slots, %d shared materials" % (len(objs), n_mat, len(lib.mats)))
    return objs


# --------------------------------------------------------------------------------------------- Moulika
class Moulika:
    def __init__(self, A):
        before = set(bpy.data.objects)
        acts_before = set(bpy.data.actions)
        bpy.ops.import_scene.gltf(filepath=os.path.join(A, "moulika.glb"))
        objs = [o for o in bpy.data.objects if o not in before]
        self.arm = next(o for o in objs if o.type == "ARMATURE")
        # her skinned body; anything else in the file (a helper icosphere) stays out of the render
        self.meshes = [o for o in objs if o.type == "MESH" and any(m.type == "ARMATURE" for m in o.modifiers)]
        self.others = [o for o in objs if o not in self.meshes and o is not self.arm]
        for o in self.others:
            o.hide_render = True
            o.hide_viewport = True
        # the import may leave the armature under an empty: use the topmost object as the mover
        top = self.arm
        while top.parent is not None:
            top = top.parent
        self.root = top
        # her height: the bind-pose mesh bounds in world space
        bpy.context.view_layer.update()
        zs = []
        for m in self.meshes:
            mw = m.matrix_world
            zs.extend((mw @ v.co).z for v in m.data.vertices)
        h = max(zs) - min(zs)
        self.scale = HEIGHT / h
        self.floor = min(zs)
        self.root.scale = self.root.scale * self.scale
        self.root.rotation_mode = "XYZ"
        self.rot0 = self.root.rotation_euler.copy()
        self.actions = {a.name: a for a in bpy.data.actions if a not in acts_before}
        if self.arm.animation_data is None:
            self.arm.animation_data_create()
        self.arm.animation_data.action = None
        # Rodin characters face glTF +Z, which the importer turns into Blender -Y
        self.facing = Vector((0, -1, 0))
        self.clips = {}
        for move, (aid, t0, t1) in SH.CLIPS.items():
            act = self._find(aid)
            if act is None:
                log("  missing clip", aid)
                continue
            self.clips[move] = self._prepare(move, act, t0, t1)
        log("Moulika: scale %.3f, clips %s" % (self.scale, {k: (round(v["len"], 1), round(v["speed"], 2)) for k, v in self.clips.items()}))
        self.tracks = 0

    def _find(self, aid):
        for n, a in self.actions.items():
            if n.startswith(aid):
                return a
        return None

    def _prepare(self, move, act, t0, t1):
        """An in-place copy of the clip (forward travel removed from the hips), looping clips made cyclic."""
        a = act.copy()
        a.name = "clip_" + move
        f0, f1 = a.frame_range
        if t1 > t0:
            f0, f1 = act.frame_range[0] + t0 * FPS, act.frame_range[0] + t1 * FPS
        travel = 0.0
        loc = [fc for fc in a.fcurves if fc.data_path.endswith('"Hips"].location')]
        if loc:
            ends = []
            for fc in loc:
                ends.append(fc.evaluate(f1) - fc.evaluate(f0))
            d = Vector(ends)
            if d.length > 0.05 and move in ("walk", "run"):
                travel = d.length
                for fc, di in zip(loc, ends):
                    for kp in fc.keyframe_points:
                        k = (kp.co.x - f0) / (f1 - f0)
                        off = di * k
                        kp.co.y -= off
                        kp.handle_left.y -= off
                        kp.handle_right.y -= off
        looping = move in ("walk", "run", "idle")
        if looping:
            for fc in a.fcurves:
                fc.modifiers.new("CYCLES")
        secs = (f1 - f0) / FPS
        return {"action": a, "f0": f0, "f1": f1, "len": secs, "loop": looping,
                "speed": travel / secs * self.scale if secs > 0 else 0.0}

    def place(self, frame0, frame1, move, start, end_or_dir, speed=1.0, phase=0.0):
        """Moulika plays `move` from frame0 to frame1 (inclusive), walking from `start` toward `end_or_dir` at the clip's
        own pace times `speed` (moving clips), or standing at `start` facing `end_or_dir` (a point to face)."""
        c = self.clips[move]
        n = frame1 - frame0 + 1
        start = Vector(start)
        tgt = Vector(end_or_dir)
        d = (tgt - start)
        d.z = 0
        d.normalize()
        yaw = math.atan2(d.y, d.x) - math.atan2(self.facing.y, self.facing.x)
        dist = c["speed"] * speed * (n - 1) / FPS if move in ("walk", "run") else 0.0
        # the root sits at her middle: lift it so her feet stand on `start`
        p0 = Vector((start.x, start.y, start.z - self.floor * self.scale))
        p1 = p0 + d * dist
        r = self.root
        for f, p in ((frame0, p0), (frame1, p1)):
            r.location = (p.x, p.y, p.z)
            r.rotation_euler = (self.rot0.x, self.rot0.y, self.rot0.z + yaw)
            r.keyframe_insert("location", frame=f)
            r.keyframe_insert("rotation_euler", frame=f)
        if r.animation_data and r.animation_data.action:
            for fc in r.animation_data.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        self.path = (Vector((start.x, start.y, start.z)), Vector((start.x, start.y, start.z)) + d * dist)
        # the clip on its own NLA track, active only during this shot
        tr = self.arm.animation_data.nla_tracks.new()
        tr.name = "shot_%d" % frame0
        a = c["action"]
        st = tr.strips.new("s%d" % frame0, frame0, a)
        span = (n / FPS) * speed * FPS
        st.action_frame_start = c["f0"] + phase * FPS
        st.action_frame_end = st.action_frame_start + span
        if not c["loop"]:
            st.action_frame_end = min(st.action_frame_end, c["f1"])
        st.scale = n / max(st.action_frame_end - st.action_frame_start, 1e-3)
        st.extrapolation = "NOTHING"
        st.blend_in = st.blend_out = 0.0
        st.use_auto_blend = False
        self.tracks += 1

    def show(self, frame, on):
        """visibility from `frame` on"""
        for o in self.meshes:
            o.hide_render = not on
            o.hide_viewport = not on
            o.keyframe_insert("hide_render", frame=frame)
            o.keyframe_insert("hide_viewport", frame=frame)


# --------------------------------------------------------------------------------------------- cameras and lights
def look_rot(eye, target, roll=0.0):
    d = Vector(target) - Vector(eye)
    q = d.to_track_quat("-Z", "Y")
    e = q.to_euler("XYZ")
    if roll:
        e.rotate_axis("Z", math.radians(roll))
    return e


def make_camera(name, shot, f0, f1):
    cd = bpy.data.cameras.new(name)
    cd.lens = shot.get("lens", 35)
    cd.sensor_width = 36
    cd.clip_start = 0.03
    cd.clip_end = 200
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    keys = shot["cam"]                      # [(t, eye, target, roll?), ...] times in seconds from the shot start
    prev = None
    for k in keys:
        t, eye, tgt = k[0], k[1], k[2]
        roll = k[3] if len(k) > 3 else 0.0
        f = f0 + round(t * FPS)
        cam.location = eye
        e = look_rot(eye, tgt, roll)
        if prev is not None:
            # keep the yaw continuous so a long pan turns the short way round the intended direction
            for i in range(3):
                while e[i] - prev[i] > math.pi:
                    e[i] -= 2 * math.pi
                while e[i] - prev[i] < -math.pi:
                    e[i] += 2 * math.pi
        cam.rotation_euler = e
        prev = e.copy()
        cam.keyframe_insert("location", frame=f)
        cam.keyframe_insert("rotation_euler", frame=f)
        cd.dof.focus_distance = max((Vector(tgt) - Vector(eye)).length * shot.get("focus_k", 1.0), 0.1)
        cd.keyframe_insert("dof.focus_distance", frame=f)
    ease = shot.get("ease", "BEZIER")
    for fc in (cam.animation_data.action.fcurves if cam.animation_data else []):
        for kp in fc.keyframe_points:
            kp.interpolation = ease
    shake = shot.get("shake", 0.0)
    if shake > 0 and cam.animation_data:
        for fc in cam.animation_data.action.fcurves:
            if fc.data_path == "rotation_euler":
                mod = fc.modifiers.new("NOISE")
                mod.scale = shot.get("shake_scale", 9.0)
                mod.strength = shake * (1.0 if fc.array_index != 2 else 0.5)
                mod.phase = 7.0 * (fc.array_index + 1) + f0 * 0.37
                mod.use_restricted_range = True
                mod.frame_start = f0
                mod.frame_end = f1
    return cam


def make_light(name, kind, loc, target, energy, color, size, f0, f1, follow=None, flicker=None):
    ld = bpy.data.lights.new(name, kind)
    ld.energy = energy
    ld.color = color
    if kind == "AREA":
        ld.size = size
    elif kind == "SPOT":
        ld.spot_size = math.radians(size)
        ld.spot_blend = 0.6
        ld.shadow_soft_size = 0.15
    else:
        ld.shadow_soft_size = size
    lo = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(lo)
    if follow is None:
        lo.location = loc
        lo.rotation_euler = look_rot(loc, target)
    else:
        # offsets from her feet, carried along her path through the shot
        for f, p in ((f0, follow[0]), (f1, follow[1])):
            lo.location = p + Vector(loc)
            lo.rotation_euler = look_rot(p + Vector(loc), p + Vector(target))
            lo.keyframe_insert("location", frame=f)
            lo.keyframe_insert("rotation_euler", frame=f)
        for fc in lo.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    if flicker:
        for (t, v) in flicker:
            ld.energy = energy * v
            ld.keyframe_insert("energy", frame=f0 + round(t * FPS))
        for fc in ld.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"
    # only on during its shot
    for f, on in ((0, False), (f0, True), (f1 + 1, False)):
        lo.hide_render = not on
        lo.keyframe_insert("hide_render", frame=max(f, 0))
    return lo


def make_slit(cam, gap, f0, f1):
    """Two dark boards just in front of the lens with a narrow gap: the view from inside a cupboard."""
    mat = bpy.data.materials.new("cupboard_inside")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (0.012, 0.008, 0.006, 1)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    for side in (-1, 1):
        bpy.ops.mesh.primitive_plane_add(size=1.0)
        pl = bpy.context.active_object
        pl.name = "slit_%s_%d" % (cam.name, side)
        pl.scale = (0.25, 0.6, 1.0)
        pl.data.materials.append(mat)
        pl.parent = cam
        pl.location = (side * (gap / 2 + 0.125), 0.0, -0.06)
        pl.rotation_euler = (0, 0, 0)
        for f, on in ((0, False), (f0, True), (f1 + 1, False)):
            pl.hide_render = not on
            pl.keyframe_insert("hide_render", frame=max(f, 0))


# --------------------------------------------------------------------------------------------- scene setup
def setup_render(preview):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.render.fps = FPS
    sc.render.resolution_x = 1920
    sc.render.resolution_y = 1080
    sc.render.resolution_percentage = 33 if preview else 100
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.05
    sc.cycles.samples = 16 if preview else 40
    sc.cycles.adaptive_min_samples = 4 if preview else 8
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.cycles.max_bounces = 4
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 2
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.volume_bounces = 0
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.sample_clamp_indirect = 3.0
    sc.render.use_persistent_data = True
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = SH.EXPOSURE
    sc.view_settings.gamma = 1.0
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGB"
    sc.render.image_settings.color_depth = "8"
    sc.render.use_motion_blur = False
    vl = sc.view_layers[0]
    vl.use_pass_z = True
    vl.use_pass_mist = True
    vl.use_pass_vector = True


def setup_world(A):
    w = bpy.data.worlds.new("night")
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    sky = os.path.join(A, "sky", "night.hdr")
    if os.path.exists(sky):
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        env.image = bpy.data.images.load(sky)
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = SH.SKY_STRENGTH
    w.mist_settings.start = 3.0
    w.mist_settings.depth = 22.0
    w.mist_settings.falloff = "QUADRATIC"


def setup_compositor():
    sc = bpy.context.scene
    sc.use_nodes = True
    nt = sc.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    rl = nt.nodes.new("CompositorNodeRLayers")
    comp = nt.nodes.new("CompositorNodeComposite")
    L = nt.links
    # depth haze: a cold night mist that thickens with distance
    fogc = nt.nodes.new("CompositorNodeRGB")
    fogc.outputs[0].default_value = SH.FOG_COLOR
    mfac = nt.nodes.new("CompositorNodeMath")
    mfac.operation = "MULTIPLY"
    mfac.inputs[1].default_value = SH.FOG_AMOUNT
    L.new(rl.outputs["Mist"], mfac.inputs[0])
    fog = nt.nodes.new("CompositorNodeMixRGB")
    fog.blend_type = "MIX"
    L.new(mfac.outputs[0], fog.inputs["Fac"])
    L.new(rl.outputs["Image"], fog.inputs[1])
    L.new(fogc.outputs[0], fog.inputs[2])
    # bloom on the lamps
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "MEDIUM"
    glare.threshold = 0.75
    glare.size = 8
    glare.mix = -0.55
    L.new(fog.outputs[0], glare.inputs["Image"])
    # depth of field from the depth pass, focused where each shot's camera focuses
    dof = nt.nodes.new("CompositorNodeDefocus")
    dof.use_zbuffer = True
    dof.f_stop = SH.F_STOP
    dof.blur_max = 24
    dof.threshold = 0.5
    L.new(glare.outputs[0], dof.inputs["Image"])
    L.new(rl.outputs["Depth"], dof.inputs["Z"])
    # motion blur from the vector pass
    vb = nt.nodes.new("CompositorNodeVecBlur")
    vb.samples = 16
    vb.factor = 0.22
    vb.speed_max = 24
    L.new(dof.outputs[0], vb.inputs["Image"])
    L.new(rl.outputs["Depth"], vb.inputs["Z"])
    L.new(rl.outputs["Vector"], vb.inputs["Speed"])
    L.new(vb.outputs[0], comp.inputs["Image"])


# --------------------------------------------------------------------------------------------- the shots
def build_shots(mou, start_frames):
    sc = bpy.context.scene
    markers = sc.timeline_markers
    report = []
    rooms = set()
    for seq_name, shots in SH.SEQUENCES.items():
        f = start_frames[seq_name]
        for sh in shots:
            n = round(sh["dur"] * FPS)
            f0, f1 = f, f + n - 1
            cam = make_camera("cam_%s" % sh["name"], sh, f0, f1)
            mk = markers.new(sh["name"], frame=f0)
            mk.camera = cam
            mou.show(f0, False)
            path = None
            for i, mv in enumerate(sh.get("moulika", [])):
                a0 = f0 + round(mv.get("from", 0.0) * FPS)
                a1 = f0 + round(mv["to"] * FPS) - 1 if "to" in mv else f1
                mou.place(a0, a1, mv["move"], mv["at"], mv["toward"], mv.get("speed", 1.0), mv.get("phase", 0.0))
                mou.show(a0, True)
                if a1 < f1:
                    mou.show(a1 + 1, False)
                if path is None or mv["move"] in ("walk", "run"):
                    path = mou.path
            fl_keys = next(iter(sh.get("flicker", {}).values()), None)
            for j, lt in enumerate(sh.get("lights", [])):
                make_light("lt_%s_%d" % (sh["name"], j), lt["kind"], lt["at"], lt["aim"], lt["energy"], lt.get("color", (1, 1, 1)),
                           lt.get("size", 1.0), f0, f1, follow=path if lt.get("follow") else None,
                           flicker=fl_keys if lt.get("flicker") else None)
            if sh.get("slit"):
                make_slit(cam, sh["slit"], f0, f1)
            for room, keys in sh.get("flicker", {}).items():
                rooms.add(room)
                for (t, v) in keys:
                    sc["power_%s" % room] = v
                    sc.keyframe_insert('["power_%s"]' % room, frame=f0 + round(t * FPS))
            report.append({"seq": seq_name, "name": sh["name"], "f0": f0, "f1": f1})
            f = f1 + 1
        # after the sequence: Moulika hidden, all rooms at full light
        mou.show(f, False)
    # flicker keys hold their values: make them step like a failing tube
    if sc.animation_data and sc.animation_data.action:
        for fc in sc.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"
    return report


def main():
    argv = sys.argv[sys.argv.index("--") + 1:]
    A, out = os.path.abspath(argv[0]), argv[1]
    preview = len(argv) > 2 and argv[2] == "preview"
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    meta = json.load(open(os.path.join(A, "school", "school_meta.json")))
    # every room's light level starts at 1 (flicker keys change it)
    for r in meta["rooms"]:
        sc["power_%s" % r["name"]] = 1.0
    for extra in ("veranda", "outside", "yard"):
        sc["power_%s" % extra] = 1.0
    lib = Lib(A, meta)
    import_school(A, lib)
    mou = Moulika(A)
    setup_render(preview)
    setup_world(A)
    setup_compositor()
    for name, (x, y, z, yaw) in SH.ITEMS.items():
        o = bpy.data.objects.get(name)
        if o is not None:
            o.location = (x, y, z)
            o.rotation_euler = (0, 0, math.radians(yaw))
    for name, side, ang in SH.OPEN_DOORS:
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        bb = [o.matrix_world @ Vector(c) for c in o.bound_box]
        xs, ys = [v.x for v in bb], [v.y for v in bb]
        hinge = {"y_min": (sum(xs) / 8, min(ys)), "y_max": (sum(xs) / 8, max(ys)),
                 "x_min": (min(xs), sum(ys) / 8), "x_max": (max(xs), sum(ys) / 8)}[side]
        piv = bpy.data.objects.new("hinge_" + name, None)
        bpy.context.scene.collection.objects.link(piv)
        piv.location = (hinge[0], hinge[1], 0.0)
        mw = o.matrix_world.copy()
        o.parent = piv
        o.matrix_parent_inverse = piv.matrix_world.inverted()
        bpy.context.view_layer.update()
        o.matrix_world = mw
        piv.rotation_euler = (0, 0, math.radians(ang))
    report = build_shots(mou, SH.START)
    sc.frame_start = 1
    sc.frame_end = max(r["f1"] for r in report)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    # every image goes inside the .blend, so the render machines never look for files that are not there
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(out))
    missing = [i.name for i in bpy.data.images if i.source == "FILE" and not i.packed_file]
    log("images packed; unpacked file images:", missing)
    with open(os.path.splitext(out)[0] + "_shots.json", "w") as fp:
        json.dump(report, fp, indent=1)
    log("saved %s: %d shots, frames %d-%d" % (out, len(report), sc.frame_start, sc.frame_end))


main()
