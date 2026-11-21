"""Blender scene builder for the Mahabharata trailer (Blender 4.2, Cycles CPU).
Run:  blender -b -P scenes.py -- --shot NAME --models DIR --out DIR [--preview] [--frames A-B]
Shots: army_aerial army_low crown wheel_dust wheel_alpha krishna_wheel arjuna_run
Models are the Hyper3D Rodin GLBs (soldier, chariot, horse, crown, wheel, krishna, arjuna)."""
import bpy, sys, os, math, random, argparse
from mathutils import Vector, Euler, Matrix

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--shot", required=True)
ap.add_argument("--models", default=os.path.expanduser("~/mb/models"))
ap.add_argument("--out", default="out")
ap.add_argument("--preview", action="store_true")
ap.add_argument("--frames", default=None)
ap.add_argument("--samples", type=int, default=0)
ap.add_argument("--scale", type=float, default=1.0)
A = ap.parse_args(argv)
os.makedirs(A.out, exist_ok=True)
random.seed(11)


# ------------------------------------------------------------------ helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = 24
    return sc


def import_glb(name):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(A.models, name + ".glb"))
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None]
    root = bpy.data.objects.new(name + "_root", None)
    bpy.context.scene.collection.objects.link(root)
    for o in roots:
        o.parent = root
    return root, new


def world_bbox(objs):
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    mn = np.array([1e9, 1e9, 1e9]); mx = np.array([-1e9, -1e9, -1e9])
    for o in objs:
        if o.type != "MESH":
            continue
        oe = o.evaluated_get(dg)
        me = oe.to_mesh()
        n = len(me.vertices)
        if n:
            co = np.empty(n * 3, np.float32)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3).astype(np.float64)
            M = np.array(oe.matrix_world)
            w = co @ M[:3, :3].T + M[:3, 3]
            mn = np.minimum(mn, w.min(0)); mx = np.maximum(mx, w.max(0))
        oe.to_mesh_clear()
    return Vector(mn.tolist()), Vector(mx.tolist())


def fit(root, objs, height=None, length=None, axis="z", ground=True):
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    size = mx - mn
    if height:
        s = height / max(size.z, 1e-6)
    elif length:
        s = length / max(max(size.x, size.y), 1e-6)
    else:
        s = 1.0
    root.scale = (s, s, s)
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    c = (mn + mx) / 2
    root.location.x -= c.x
    root.location.y -= c.y
    if ground:
        root.location.z -= mn.z
    bpy.context.view_layer.update()
    return s


def set_action(objs, action_prefix, frame):
    arm = next((o for o in objs if o.type == "ARMATURE"), None)
    if not arm:
        return None
    act = next((a for a in bpy.data.actions if a.name.startswith(action_prefix)), None)
    if act:
        if not arm.animation_data:
            arm.animation_data_create()
        # drop NLA tracks so only our action plays
        for tr in list(arm.animation_data.nla_tracks):
            arm.animation_data.nla_tracks.remove(tr)
        arm.animation_data.action = act
    bpy.context.scene.frame_set(int(frame))
    return arm


def mat_simple(name, color, rough=0.8, metal=0.0, emit=None, strength=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*color, 1)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = (*emit, 1)
        b.inputs["Emission Strength"].default_value = strength
    return m


def ground_plane(size=3000, color=(0.33, 0.24, 0.16), scale=0.02, disp=True):
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, 0))
    g = bpy.context.active_object
    g.name = "ground"
    m = bpy.data.materials.new("ground")
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    tex = nt.nodes.new("ShaderNodeTexNoise"); tex.inputs["Scale"].default_value = 0.35 / max(scale, 1e-3) * 0.02
    tex.inputs["Detail"].default_value = 8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].color = (color[0] * 0.55, color[1] * 0.5, color[2] * 0.45, 1)
    ramp.color_ramp.elements[1].color = (color[0] * 1.25, color[1] * 1.2, color[2] * 1.1, 1)
    nt.links.new(tex.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.96
    bump = nt.nodes.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35
    tex2 = nt.nodes.new("ShaderNodeTexNoise"); tex2.inputs["Scale"].default_value = 40; tex2.inputs["Detail"].default_value = 6
    nt.links.new(tex2.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], b.inputs["Normal"])
    g.data.materials.append(m)
    return g


def sky(sc, elev_deg=4.0, rot_deg=0.0, strength=1.0, dust=4.0, air=1.0):
    w = bpy.data.worlds.new("sky"); sc.world = w; w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes["Background"]
    st = nt.nodes.new("ShaderNodeTexSky")
    st.sky_type = "NISHITA"
    st.sun_elevation = math.radians(elev_deg)
    st.sun_rotation = math.radians(rot_deg)
    st.dust_density = dust
    st.air_density = air
    st.sun_intensity = 1.0
    nt.links.new(st.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = strength
    return w


def dark_world(sc, color=(0.012, 0.01, 0.012), strength=1.0):
    w = bpy.data.worlds.new("dark"); sc.world = w; w.use_nodes = True
    w.node_tree.nodes["Background"].inputs[0].default_value = (*color, 1)
    w.node_tree.nodes["Background"].inputs[1].default_value = strength
    return w


def sun_light(elev_deg, rot_deg, energy=4.0, color=(1.0, 0.72, 0.45), angle=1.5):
    ld = bpy.data.lights.new("sun", "SUN"); ld.energy = energy; ld.color = color
    ld.angle = math.radians(angle)
    o = bpy.data.objects.new("sun", ld); bpy.context.scene.collection.objects.link(o)
    # sun shines FROM direction (elev, rot) towards origin. Blender sun points along -Z of object.
    e, r = math.radians(elev_deg), math.radians(rot_deg)
    d = Vector((math.sin(r) * math.cos(e), math.cos(r) * math.cos(e), math.sin(e)))  # direction to the sun (+Y = rot 0)
    o.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    return o


def area(name, loc, target, energy, size=2.0, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, "AREA"); ld.energy = energy; ld.size = size; ld.color = color
    o = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def spot(name, loc, target, energy, size_deg=40, blend=0.6, color=(1, 1, 1), radius=0.2):
    ld = bpy.data.lights.new(name, "SPOT"); ld.energy = energy; ld.spot_size = math.radians(size_deg)
    ld.spot_blend = blend; ld.color = color; ld.shadow_soft_size = radius
    o = bpy.data.objects.new(name, ld); bpy.context.scene.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    return o


def camera(loc, target, lens=35, dof=None, fstop=2.8, sensor=36):
    cd = bpy.data.cameras.new("cam"); cd.lens = lens; cd.sensor_width = sensor
    cd.clip_start = 0.05; cd.clip_end = 5000
    c = bpy.data.objects.new("cam", cd); bpy.context.scene.collection.objects.link(c)
    c.location = loc
    c.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    if dof:
        cd.dof.use_dof = True
        cd.dof.focus_distance = dof
        cd.dof.aperture_fstop = fstop
    bpy.context.scene.camera = c
    return c


def render_settings(sc, res=(1920, 804), samples=48, transparent=False, mist=None, fog_color=(0.9, 0.6, 0.35),
                    fog_amount=0.0, glare=0.0, look="AgX - Medium High Contrast", exposure=0.0):
    if A.preview:
        res = (int(res[0] * 0.28) // 2 * 2, int(res[1] * 0.28) // 2 * 2)
        samples = 8
    if A.samples:
        samples = A.samples
    res = (int(res[0] * A.scale) // 2 * 2, int(res[1] * A.scale) // 2 * 2)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.03
    sc.cycles.use_denoising = True
    sc.cycles.denoiser = "OPENIMAGEDENOISE"
    sc.cycles.max_bounces = 6
    sc.cycles.diffuse_bounces = 3
    sc.cycles.glossy_bounces = 3
    sc.cycles.transparent_max_bounces = 6
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.use_persistent_data = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.view_settings.view_transform = "AgX"
    try:
        sc.view_settings.look = look
    except Exception:
        pass
    sc.view_settings.exposure = exposure
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA" if transparent else "RGB"
    sc.render.image_settings.color_depth = "8"
    if mist or glare:
        vl = sc.view_layers[0]
        sc.use_nodes = True
        nt = sc.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        rl = nt.nodes.new("CompositorNodeRLayers")
        comp = nt.nodes.new("CompositorNodeComposite")
        cur = rl.outputs["Image"]
        if mist:
            vl.use_pass_mist = True
            sc.world.mist_settings.start = mist[0]
            sc.world.mist_settings.depth = mist[1]
            sc.world.mist_settings.falloff = "QUADRATIC"
            mix = nt.nodes.new("CompositorNodeMixRGB"); mix.blend_type = "MIX"
            mul = nt.nodes.new("CompositorNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = fog_amount
            nt.links.new(rl.outputs["Mist"], mul.inputs[0])
            nt.links.new(mul.outputs[0], mix.inputs["Fac"])
            nt.links.new(cur, mix.inputs[1])
            mix.inputs[2].default_value = (*fog_color, 1)
            cur = mix.outputs["Image"]
        if glare:
            gl = nt.nodes.new("CompositorNodeGlare"); gl.glare_type = "FOG_GLOW"; gl.quality = "MEDIUM"
            gl.mix = -1 + glare; gl.threshold = 0.9; gl.size = 8
            nt.links.new(cur, gl.inputs["Image"])
            cur = gl.outputs["Image"]
        nt.links.new(cur, comp.inputs["Image"])
        if A.preview is False and sc.render.film_transparent:
            nt.links.new(rl.outputs["Alpha"], comp.inputs["Alpha"])


def do_render(sc, name, frames=None):
    if frames is None:
        sc.render.filepath = os.path.join(A.out, name + ".png")
        bpy.ops.render.render(write_still=True)
    else:
        a, b = frames
        if A.frames:
            a, b = map(int, A.frames.split("-"))
        for f in range(a, b + 1):
            sc.frame_set(f)
            sc.render.filepath = os.path.join(A.out, f"{name}_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
            print(f"frame {f} done", flush=True)


def points_object(name, pts):
    me = bpy.data.meshes.new(name)
    me.from_pydata(pts, [], [])
    o = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(o)
    return o


def scatter(objs, pts, name, rot_z=0.0, jitter=0.15, scale_j=0.06, seed=0):
    """Instance objs (moved to an excluded collection) on every point via Geometry Nodes."""
    coll = bpy.data.collections.new(name + "_src")
    bpy.context.scene.collection.children.link(coll)
    for o in objs:
        for c in list(o.users_collection):
            c.objects.unlink(o)
        coll.objects.link(o)
    bpy.context.view_layer.layer_collection.children[coll.name].exclude = True
    holder = points_object(name, pts)
    mod = holder.modifiers.new("inst", "NODES")
    ng = bpy.data.node_groups.new(name + "_ng", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    gi = ng.nodes.new("NodeGroupInput"); go = ng.nodes.new("NodeGroupOutput")
    ci = ng.nodes.new("GeometryNodeCollectionInfo")
    ci.inputs["Collection"].default_value = coll
    ci.transform_space = "ORIGINAL"
    iop = ng.nodes.new("GeometryNodeInstanceOnPoints")
    rv = ng.nodes.new("FunctionNodeRandomValue"); rv.data_type = "FLOAT_VECTOR"
    rv.inputs[0].default_value = (0.0, 0.0, rot_z - jitter)
    rv.inputs[1].default_value = (0.0, 0.0, rot_z + jitter)
    rv.inputs["Seed"].default_value = seed
    rs = ng.nodes.new("FunctionNodeRandomValue"); rs.data_type = "FLOAT"
    rs.inputs[2].default_value = 1.0 - scale_j
    rs.inputs[3].default_value = 1.0 + scale_j
    rs.inputs["Seed"].default_value = seed + 7
    ng.links.new(gi.outputs[0], iop.inputs["Points"])
    ng.links.new(ci.outputs[0], iop.inputs["Instance"])
    ng.links.new(rv.outputs[0], iop.inputs["Rotation"])
    ng.links.new(rs.outputs[1], iop.inputs["Scale"])
    ng.links.new(iop.outputs[0], go.inputs[0])
    mod.node_group = ng
    return holder


def all_children(root):
    out = [root]
    for c in root.children:
        out += all_children(c)
    return out


def army_points(x0, x1, y0, y1, spacing=1.6, block=(24, 16), lane=7.0, jitter=0.35, keep=0.97):
    pts = []
    bx, by = block
    bw, bh = bx * spacing, by * spacing
    y = y0
    while y + bh <= y1:
        x = x0
        while x + bw <= x1:
            for i in range(bx):
                for j in range(by):
                    if random.random() > keep:
                        continue
                    pts.append((x + i * spacing + random.uniform(-jitter, jitter),
                                y + j * spacing + random.uniform(-jitter, jitter), 0.0))
            x += bw + lane + random.uniform(-2, 2)
        y += bh + lane * 1.4
    return pts


def flag_object(color, h=7.0, fw=1.8, fh=1.1):
    bpy.ops.mesh.primitive_cylinder_add(radius=0.05, depth=h, location=(0, 0, h / 2), vertices=8)
    pole = bpy.context.active_object
    pole.data.materials.append(mat_simple("pole", (0.12, 0.08, 0.05), 0.7))
    bpy.ops.mesh.primitive_plane_add(size=1, location=(fw / 2, 0, h - fh / 2))
    fl = bpy.context.active_object
    fl.scale = (fw, 1, fh)
    fl.rotation_euler = (math.radians(90), 0, 0)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    sub = fl.modifiers.new("sub", "SUBSURF"); sub.levels = 3; sub.render_levels = 3; sub.subdivision_type = "SIMPLE"
    wv = fl.modifiers.new("wave", "WAVE"); wv.height = 0.18; wv.width = 0.9; wv.narrowness = 1.2; wv.use_normal = False
    wv.use_y = False
    m = mat_simple("flag", color, 0.75)
    m.node_tree.nodes["Principled BSDF"].inputs["Subsurface Weight"].default_value = 0.0
    fl.data.materials.append(m)
    root = bpy.data.objects.new("flag_root", None); bpy.context.scene.collection.objects.link(root)
    pole.parent = root; fl.parent = root
    return root


# ------------------------------------------------------------------ shots
def build_battlefield(sc, sun_elev=3.0, sun_rot=0.0):
    ground_plane(4000)
    sky(sc, sun_elev, sun_rot, strength=1.0, dust=6.0, air=1.2)
    sun_light(sun_elev, sun_rot, energy=3.2, color=(1.0, 0.62, 0.36), angle=1.2)
    sold_root, sold_objs = import_glb("soldier")
    fit(sold_root, sold_objs, height=1.8)
    p1 = army_points(-360, 360, 60, 230, block=(26, 14))
    p2 = army_points(-380, 380, 330, 520, block=(26, 14))
    src_objs = all_children(sold_root)
    scatter(src_objs, p1, "army1", rot_z=math.pi, seed=1)        # near army faces +Y (away from camera)
    # second army: share the same source collection by instancing the collection again
    scatter_coll = bpy.data.collections["army1_src"]
    h2 = points_object("army2", p2)
    mod = h2.modifiers.new("inst", "NODES")
    ng = bpy.data.node_groups["army1_ng"].copy()
    for n in ng.nodes:
        if n.bl_idname == "FunctionNodeRandomValue" and n.data_type == "FLOAT_VECTOR":
            n.inputs[0].default_value = (0.0, 0.0, -0.15)
            n.inputs[1].default_value = (0.0, 0.0, 0.15)
    mod.node_group = ng
    print("soldiers:", len(p1) + len(p2), flush=True)
    cols = [(0.85, 0.32, 0.05), (0.75, 0.08, 0.04), (0.9, 0.62, 0.1), (0.95, 0.45, 0.08)]
    for k, (y0, y1) in enumerate([(60, 230), (330, 520)]):
        for j in range(2):
            fr = flag_object(cols[(k * 2 + j) % 4])
            fpts = [(random.uniform(-350, 350), random.uniform(y0, y1), 0) for _ in range(110)]
            scatter(all_children(fr), fpts, f"flags{k}{j}", rot_z=0.0, jitter=0.5, scale_j=0.12, seed=10 + k * 2 + j)
    for k, (y0, y1) in enumerate([(60, 230), (330, 520)]):
        fr = flag_object((0.8, 0.5, 0.08) if k == 0 else (0.6, 0.06, 0.05), h=9.0, fw=2.4, fh=1.4)
        fpts = [(random.uniform(-340, 340), random.uniform(y0 + 5, y0 + 40), 0) for _ in range(60)]
        scatter(all_children(fr), fpts, f"bigflags{k}", rot_z=0.0, jitter=0.4, scale_j=0.1, seed=30 + k)


def shot_army_aerial():
    sc = reset()
    build_battlefield(sc, sun_elev=3.0, sun_rot=4.5)
    camera((-30, -120, 95), (12, 560, 0), lens=30)
    render_settings(sc, res=(2880, 1206), samples=40, mist=(80, 1400), fog_color=(0.95, 0.62, 0.38), fog_amount=0.5,
                    glare=0.3, look="AgX - Medium High Contrast", exposure=-0.4)
    do_render(sc, "army_aerial")


def shot_army_low():
    sc = reset()
    build_battlefield(sc, sun_elev=1.6, sun_rot=-1.8)
    camera((14, 40, 1.65), (2, 420, 6), lens=105, dof=200, fstop=4.0)
    render_settings(sc, res=(2880, 1206), samples=40, mist=(40, 700), fog_color=(0.98, 0.66, 0.4), fog_amount=0.55,
                    glare=0.4, look="AgX - Medium High Contrast", exposure=-0.7)
    do_render(sc, "army_low")


def shot_army_mid():
    sc = reset()
    build_battlefield(sc, sun_elev=3.0, sun_rot=-17.0)
    camera((60, 196, 9), (20, 330, 3), lens=45, dof=95, fstop=5.6)
    render_settings(sc, res=(2880, 1206), samples=40, mist=(40, 600), fog_color=(0.96, 0.64, 0.4), fog_amount=0.5,
                    glare=0.35, look="AgX - Medium High Contrast", exposure=-0.5)
    do_render(sc, "army_mid")


def shot_crown():
    sc = reset()
    root, objs = import_glb("crown")
    fit(root, objs, height=0.42)
    dark_world(sc, (0.01, 0.008, 0.008), 1.0)
    # turntable empty
    pivot = bpy.data.objects.new("pivot", None); sc.collection.objects.link(pivot)
    root.parent = pivot
    pivot.rotation_euler = (0, 0, math.radians(-14))
    pivot.keyframe_insert("rotation_euler", frame=1)
    pivot.rotation_euler = (0, 0, math.radians(10))
    pivot.keyframe_insert("rotation_euler", frame=60)
    for fc in pivot.animation_data.action.fcurves:
        for k in fc.keyframe_points:
            k.interpolation = "SINE"
    spot("key", (0.55, -0.7, 0.75), (0, 0, 0.28), 140, 34, 0.7, (1.0, 0.78, 0.5), 0.12)
    area("rim", (-0.55, 0.65, 0.55), (0, 0, 0.3), 90, 0.6, (1.0, 0.55, 0.22))
    area("rim2", (0.6, 0.55, 0.35), (0, 0, 0.25), 45, 0.5, (1.0, 0.7, 0.4))
    area("fill", (-0.8, -0.6, 0.2), (0, 0, 0.2), 6, 1.2, (0.55, 0.65, 1.0))
    c = camera((0.0, -3.1, 0.27), (0, 0, 0.22), lens=85, dof=3.0, fstop=4.0)
    c.keyframe_insert("location", frame=1)
    c.location = (0.0, -2.75, 0.26)
    c.keyframe_insert("location", frame=60)
    render_settings(sc, res=(1920, 804), samples=56, glare=0.35, look="AgX - Medium High Contrast", exposure=0.4)
    do_render(sc, "crown", frames=(1, 60))


def shot_wheel_dust():
    sc = reset()
    ground_plane(800, color=(0.26, 0.19, 0.13))
    sky(sc, 2.5, 10.0, strength=1.0, dust=7.0)
    sun_light(2.5, 10.0, energy=3.0, color=(1.0, 0.6, 0.34), angle=1.0)
    root, objs = import_glb("wheel")
    fit(root, objs, height=1.6, ground=True)
    root.rotation_euler = (math.radians(-62), math.radians(8), math.radians(-28))
    bpy.context.view_layer.update()
    mn, mx = world_bbox(objs)
    root.location.z -= mn.z + 0.12
    # some scattered broken spokes/debris (simple cylinders)
    for i in range(9):
        bpy.ops.mesh.primitive_cylinder_add(radius=0.035, depth=random.uniform(0.4, 0.9), vertices=6,
                                            location=(random.uniform(-2.5, 2.5), random.uniform(-1.5, 3), 0.03),
                                            rotation=(math.radians(90), 0, random.uniform(0, 3.14)))
        bpy.context.active_object.data.materials.append(mat_simple("deb", (0.16, 0.1, 0.06), 0.8))
    camera((1.2, -3.4, 0.55), (0, 0.3, 0.45), lens=42, dof=3.4, fstop=2.8)
    render_settings(sc, res=(2880, 1206), samples=48, mist=(6, 160), fog_color=(0.95, 0.6, 0.36), fog_amount=0.5,
                    glare=0.4, exposure=-0.4)
    do_render(sc, "wheel_dust")


def shot_wheel_alpha():
    sc = reset()
    root, objs = import_glb("wheel")
    fit(root, objs, height=1.0, ground=False)
    dark_world(sc, (0.0, 0.0, 0.0), 0.0)
    area("key", (-1.2, -2.0, 1.4), (0, 0, 0), 120, 1.0, (1.0, 0.8, 0.55))
    area("rim", (1.5, 1.2, 0.8), (0, 0, 0), 220, 0.8, (1.0, 0.62, 0.3))
    area("rim2", (-1.4, 1.0, -0.6), (0, 0, 0), 160, 0.8, (1.0, 0.7, 0.4))
    cd = camera((0, -6.0, 0), (0, 0, 0), lens=120)
    render_settings(sc, res=(2048, 2048), samples=48, transparent=True, look="AgX - Medium High Contrast", exposure=0.3)
    do_render(sc, "wheel_alpha")


def find_arms_up_frame(arm, act_prefix):
    act = next((a for a in bpy.data.actions if a.name.startswith(act_prefix)), None)
    if not act:
        return 1
    a, b = map(int, act.frame_range)
    best, bf = -1e9, a
    for f in range(a, b + 1, 2):
        bpy.context.scene.frame_set(f)
        lh = arm.matrix_world @ arm.pose.bones["LeftHand"].head
        rh = arm.matrix_world @ arm.pose.bones["RightHand"].head
        hd = arm.matrix_world @ arm.pose.bones["Head"].head
        score = min(lh.z, rh.z) - hd.z - 0.3 * abs(lh.x - rh.x)
        if score > best:
            best, bf = score, f
    return bf


def shot_krishna_wheel():
    sc = reset()
    ground_plane(800, color=(0.3, 0.22, 0.15))
    w = sky(sc, 1.5, -5.5, strength=0.42, dust=8.0)
    for n in w.node_tree.nodes:
        if n.bl_idname == "ShaderNodeTexSky":
            n.sun_disc = False
    root, objs = import_glb("krishna")
    arm = set_action(objs, "human_000000", 1)
    f = find_arms_up_frame(arm, "human_000000") if arm else 1
    sc.frame_set(f)
    fit(root, objs, height=1.85)
    bpy.context.view_layer.update()
    lh = arm.matrix_world @ arm.pose.bones["LeftHand"].head
    rh = arm.matrix_world @ arm.pose.bones["RightHand"].head
    top = (lh + rh) / 2
    wr, wobjs = import_glb("wheel")
    fit(wr, wobjs, height=1.35, ground=False)
    hub = Vector((top.x, top.y, top.z + 0.62))
    wr.location = hub
    cam_loc = Vector((0.6, -6.2, 0.55))
    camera(tuple(cam_loc), (0, 0, 1.9), lens=40, dof=6.2, fstop=4)
    d = (hub - cam_loc).normalized()
    # sun disc right behind the wheel hub
    bpy.ops.mesh.primitive_uv_sphere_add(radius=5.5, location=tuple(cam_loc + d * 140), segments=32, ring_count=16)
    disc = bpy.context.active_object
    disc.data.materials.append(mat_simple("sundisc", (1, 0.85, 0.6), 1.0, 0.0, (1.0, 0.82, 0.55), 60.0))
    disc.visible_shadow = False
    # backlight from the disc direction + faint warm fill from the camera side
    ld = bpy.data.lights.new("back", "SUN"); ld.energy = 5.0; ld.color = (1.0, 0.7, 0.42); ld.angle = math.radians(3)
    lo = bpy.data.objects.new("back", ld); sc.collection.objects.link(lo)
    lo.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    area("fill", (2, -6, 2), (0, 0, 1.4), 30, 3, (1.0, 0.6, 0.35))
    render_settings(sc, res=(2880, 1206), samples=48, mist=(8, 200), fog_color=(0.9, 0.55, 0.32), fog_amount=0.25,
                    glare=0.5, exposure=-0.2)
    print("arms-up frame", f, flush=True)
    do_render(sc, "krishna_wheel")


def shot_arjuna_run():
    sc = reset()
    ground_plane(2000, color=(0.33, 0.24, 0.16))
    sky(sc, 2.0, 0.0, strength=1.0, dust=8.0)
    sun_light(2.0, 0.0, energy=2.8, color=(1.0, 0.6, 0.36), angle=1.5)
    root, objs = import_glb("arjuna")
    arm = set_action(objs, "human_000067", 1)
    fit(root, objs, height=1.82)
    root.rotation_euler.z = math.radians(-90)  # run toward +X
    # camera tracks alongside: parent camera to an empty that follows the hips X
    c = camera((0, -6.5, 1.1), (0, 0, 1.0), lens=50, dof=6.5, fstop=3.2)
    con = c.constraints.new("COPY_LOCATION")
    con.target = arm
    con.subtarget = "Hips"
    con.use_y = False
    con.use_z = False
    con.use_offset = True
    render_settings(sc, res=(1920, 804), samples=32, mist=(8, 180), fog_color=(0.98, 0.66, 0.4), fog_amount=0.4,
                    glare=0.4, exposure=-1.4)
    do_render(sc, "arjuna_run", frames=(1, 40))


SHOTS = {k[5:]: v for k, v in globals().items() if k.startswith("shot_")}
SHOTS[A.shot]()
print("SHOT DONE", A.shot, flush=True)
