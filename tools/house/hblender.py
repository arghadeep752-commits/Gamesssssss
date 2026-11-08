"""Blender side of the house build: turns the generated geometry into Blender meshes and materials, sets up
sun, sky and lamps, bakes the lighting (direct + bounced) into per-corner colours with Cycles, bakes a grid of
light probes for moving objects, and renders preview images (full path-traced and 'game look')."""
import os
import math
import time
import numpy as np
import bpy
from mathutils import Vector

import hlib as H

PROBE_SIZE = 0.03


def lin(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _inp(node, *names):
    for n in names:
        if n in node.inputs:
            return node.inputs[n]
    return None


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.images):
        for item in list(coll):
            try:
                coll.remove(item)
            except Exception:
                pass


def load_image(name, data=False):
    path = os.path.join(H.TEX, name + ".png")
    img = bpy.data.images.load(path, check_existing=True)
    if data:
        img.colorspace_settings.name = "Non-Color"
    return img


def make_material(m):
    mat = bpy.data.materials.new(m["name"])
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    out = nt.nodes.get("Material Output")
    c = lin(m["color"])
    bsdf.inputs["Base Color"].default_value = (c[0], c[1], c[2], 1.0)
    bsdf.inputs["Roughness"].default_value = 1.0 - m["smoothness"]
    bsdf.inputs["Metallic"].default_value = m["metallic"]
    if m["albedo"] or m["normal"]:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        s = 1.0 / max(m["tile"], 1e-3)
        mp.inputs["Scale"].default_value = (s, s, 1.0)
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        if m["albedo"]:
            t = nt.nodes.new("ShaderNodeTexImage")
            t.image = load_image(m["albedo"])
            nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
            nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
        if m["normal"]:
            tn = nt.nodes.new("ShaderNodeTexImage")
            tn.image = load_image(m["normal"], data=True)
            nm = nt.nodes.new("ShaderNodeNormalMap")
            nm.inputs["Strength"].default_value = 0.8 * m["normalStrength"]
            nt.links.new(mp.outputs["Vector"], tn.inputs["Vector"])
            nt.links.new(tn.outputs["Color"], nm.inputs["Color"])
            nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    if m["emissionStrength"] > 0:
        e = lin(m["emission"])
        ec = _inp(bsdf, "Emission Color", "Emission")
        if ec is not None:
            ec.default_value = (e[0], e[1], e[2], 1.0)
        es = _inp(bsdf, "Emission Strength")
        if es is not None:
            es.default_value = m["emissionStrength"]
    if m["kind"] == "glass":
        bsdf.inputs["Alpha"].default_value = m["alpha"]
        bsdf.inputs["Roughness"].default_value = 0.02
        try:
            mat.blend_method = "BLEND"
        except Exception:
            pass
    return mat


def make_game_material(m, base):
    """Emission-only copy that shows albedo x baked light: what the game's shader draws."""
    mat = bpy.data.materials.new(m["name"] + "__game")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    if m["kind"] == "glass":
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        gl = nt.nodes.new("ShaderNodeBsdfGlossy")
        gl.inputs["Roughness"].default_value = 0.02
        mix = nt.nodes.new("ShaderNodeMixShader")
        mix.inputs["Fac"].default_value = 0.12
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(gl.outputs[0], mix.inputs[2])
        nt.links.new(mix.outputs[0], out.inputs["Surface"])
        return mat
    em = nt.nodes.new("ShaderNodeEmission")
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "Light"
    mul = nt.nodes.new("ShaderNodeVectorMath")
    mul.operation = "MULTIPLY"
    if m["albedo"]:
        tc = nt.nodes.new("ShaderNodeTexCoord")
        mp = nt.nodes.new("ShaderNodeMapping")
        s = 1.0 / max(m["tile"], 1e-3)
        mp.inputs["Scale"].default_value = (s, s, 1.0)
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image = load_image(m["albedo"])
        nt.links.new(tc.outputs["UV"], mp.inputs["Vector"])
        nt.links.new(mp.outputs["Vector"], t.inputs["Vector"])
        nt.links.new(t.outputs["Color"], mul.inputs[0])
    else:
        c = lin(m["color"])
        mul.inputs[0].default_value = (c[0], c[1], c[2])
    nt.links.new(attr.outputs["Color"], mul.inputs[1])
    if m["emissionStrength"] > 0:
        add = nt.nodes.new("ShaderNodeVectorMath")
        add.operation = "ADD"
        e = lin(m["emission"]) * m["emissionStrength"] * 0.25
        add.inputs[1].default_value = (e[0], e[1], e[2])
        nt.links.new(mul.outputs[0], add.inputs[0])
        nt.links.new(add.outputs[0], em.inputs["Color"])
    else:
        nt.links.new(mul.outputs[0], em.inputs["Color"])
    em.inputs["Strength"].default_value = 1.0
    nt.links.new(em.outputs[0], out.inputs["Surface"])
    return mat


def make_mesh_object(name, P, N, UV, sizes, fm, mats, bmats, coll, custom_normals=True):
    me = bpy.data.meshes.new(name)
    starts = np.concatenate([[0], np.cumsum(sizes)[:-1]])
    faces = [list(range(s, s + k)) for s, k in zip(starts.tolist(), sizes.tolist())]
    me.from_pydata(P.tolist(), [], faces)
    for m in mats:
        me.materials.append(bmats[m])
    me.polygons.foreach_set("material_index", fm.astype(np.int32))
    uv = me.uv_layers.new(name="UVMap")
    uv.data.foreach_set("uv", UV.astype(np.float32).ravel())
    if custom_normals:
        try:
            me.polygons.foreach_set("use_smooth", np.ones(len(sizes), bool))
            me.normals_split_custom_set(N.tolist())
        except Exception as e:
            H.log("custom normals not applied on", name, ":", e)
    me.update()
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    return ob


def probe_grid():
    x0, y0, x1, y1 = H.INFO["plot"]
    xs = np.arange(x0 + 0.5, x1 - 0.49, 1.0)
    ys = np.arange(y0 + 0.5, y1 - 0.49, 1.0)
    lv = H.INFO["levels"]
    zs = np.array([lv["ground"] + 1.2, lv["first"] + 1.2])
    return xs, ys, zs


def probe_mesh(xs, ys, zs):
    """Tiny cubes, one per probe; face order +x -x +y -y +z -z (Blender axes)."""
    h = PROBE_SIZE * 0.5
    corners = {
        0: [(h, -h, -h), (h, h, -h), (h, h, h), (h, -h, h)],
        1: [(-h, h, -h), (-h, -h, -h), (-h, -h, h), (-h, h, h)],
        2: [(h, h, -h), (-h, h, -h), (-h, h, h), (h, h, h)],
        3: [(-h, -h, -h), (h, -h, -h), (h, -h, h), (-h, -h, h)],
        4: [(-h, -h, h), (h, -h, h), (h, h, h), (-h, h, h)],
        5: [(-h, h, -h), (h, h, -h), (h, -h, -h), (-h, -h, -h)],
    }
    cube = np.array([corners[k] for k in range(6)], float).reshape(24, 3)
    centers = np.array([(x, y, z) for z in zs for y in ys for x in xs], float)
    P = (centers[:, None, :] + cube[None, :, :]).reshape(-1, 3)
    return centers, P


def setup_world_and_sun(sun_dir, sun_strength=4.0):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Sky")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background")
    out = nt.nodes.get("World Output")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    mr = nt.nodes.new("ShaderNodeMapRange")
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    nt.links.new(tc.outputs["Generated"], sep.inputs[0])
    nt.links.new(sep.outputs["Z"], mr.inputs["Value"])
    mr.inputs["From Min"].default_value = -1.0
    mr.inputs["From Max"].default_value = 1.0
    nt.links.new(mr.outputs["Result"], ramp.inputs["Fac"])
    els = ramp.color_ramp.elements
    els[0].position = 0.0
    els[0].color = (0.10, 0.095, 0.085, 1.0)
    els[1].position = 1.0
    els[1].color = (0.16, 0.30, 0.72, 1.0)
    for pos, colr in ((0.495, (0.30, 0.28, 0.25, 1.0)), (0.505, (0.78, 0.86, 1.0, 1.0)), (0.62, (0.42, 0.58, 0.92, 1.0))):
        e = els.new(pos)
        e.color = colr
    nt.links.new(ramp.outputs["Color"], bg.inputs["Color"])
    bg.inputs["Strength"].default_value = 1.0
    ld = bpy.data.lights.new("Sun", type="SUN")
    ld.energy = sun_strength
    ld.angle = math.radians(1.2)
    ld.color = (1.0, 0.94, 0.86)
    sun = bpy.data.objects.new("Sun", ld)
    sun.rotation_mode = "QUATERNION"
    sun.rotation_quaternion = Vector(tuple(float(v) for v in sun_dir)).to_track_quat("Z", "Y")
    scene.collection.objects.link(sun)


def add_lamps(coll):
    n = 0
    for i, l in enumerate(H.LIGHTS):
        kind = l.get("kind", "point")
        ld = bpy.data.lights.new("Lamp%03d" % i, type="SPOT" if kind == "spot" else "POINT")
        ld.energy = float(l["power"])
        ld.color = tuple(float(c) for c in l.get("color", (1.0, 0.85, 0.66)))
        ld.shadow_soft_size = float(l.get("radius", 0.04))
        if kind == "spot":
            ld.spot_size = math.radians(float(l.get("spot", 110.0)))
            ld.spot_blend = 0.6
        ob = bpy.data.objects.new("Lamp%03d" % i, ld)
        ob.location = tuple(float(v) for v in l["pos"])
        if "dir" in l:
            ob.rotation_mode = "QUATERNION"
            ob.rotation_quaternion = Vector(tuple(float(v) for v in l["dir"])).to_track_quat("-Z", "Y")
        coll.objects.link(ob)
        n += 1
    return n


def cycles_setup(samples, bounces=4):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    cy = scene.cycles
    cy.device = "CPU"
    cy.samples = samples
    cy.max_bounces = bounces
    cy.diffuse_bounces = 3
    cy.glossy_bounces = 2
    cy.transmission_bounces = 4
    cy.transparent_max_bounces = 12
    cy.volume_bounces = 0
    for attr, val in (("caustics_reflective", False), ("caustics_refractive", False), ("blur_glossy", 1.0),
                      ("sample_clamp_indirect", 6.0), ("use_light_tree", True)):
        try:
            setattr(cy, attr, val)
        except Exception:
            pass
    scene.render.threads_mode = "AUTO"


def bake(bake_objs, samples):
    scene = bpy.context.scene
    cycles_setup(samples)
    cy = scene.cycles
    cy.use_denoising = False
    scene.render.bake.target = "VERTEX_COLORS"
    for ob in bake_objs:
        me = ob.data
        a = me.color_attributes.get("Light") or me.color_attributes.new("Light", "FLOAT_COLOR", "CORNER")
        me.color_attributes.active_color = a
        try:
            me.attributes.active_color = a
        except Exception:
            pass
    bpy.ops.object.select_all(action="DESELECT")
    for ob in bake_objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = bake_objs[0]
    t = time.time()
    bpy.ops.object.bake(type="DIFFUSE", pass_filter={"DIRECT", "INDIRECT"}, target="VERTEX_COLORS", use_clear=True)
    H.log("bake: %d objects, %d samples, %.1f s" % (len(bake_objs), samples, time.time() - t))


def read_light(ob):
    a = ob.data.color_attributes.get("Light")
    n = len(a.data)
    arr = np.empty(n * 4, np.float32)
    a.data.foreach_get("color", arr)
    return arr.reshape(-1, 4)[:, :3].astype(float)


def write_light(ob, L):
    a = ob.data.color_attributes.get("Light")
    out = np.concatenate([L, np.ones((len(L), 1))], 1).astype(np.float32)
    a.data.foreach_set("color", out.ravel())


def solid_test(points):
    """True for points inside any static collider box (probes stuck in walls or furniture)."""
    inside = np.zeros(len(points), bool)
    for c, s, rot, layer in H.COLLIDERS:
        d = points - c
        if rot is not None:
            d = d @ rot
        inside |= np.all(np.abs(d) < s * 0.5 + 0.02, axis=1)
    return inside


def finish_probes(centers, L, xs, ys, zs):
    n = len(centers)
    faces = L.reshape(n, 6, 4, 3).mean(axis=2)            # +x -x +y -y +z -z (Blender)
    lum = faces.mean(axis=(1, 2))
    bad = (lum < 0.003) | solid_test(centers)
    vals = faces.copy()
    nx, ny, nz = len(xs), len(ys), len(zs)
    grid = vals.reshape(nz, ny, nx, 6, 3)
    ok = (~bad).reshape(nz, ny, nx)
    for _ in range(60):
        if ok.all():
            break
        acc = np.zeros_like(grid)
        cnt = np.zeros(ok.shape)
        for axis in range(3):
            for sh in (-1, 1):
                rg = np.roll(grid, sh, axis=axis)
                ro = np.roll(ok, sh, axis=axis)
                edge = np.zeros(ok.shape, bool)
                idx = [slice(None)] * 3
                idx[axis] = 0 if sh == 1 else -1
                edge[tuple(idx)] = True
                ro = ro & ~edge
                acc += rg * ro[..., None, None]
                cnt += ro
        fill = (~ok) & (cnt > 0)
        grid[fill] = acc[fill] / cnt[fill][..., None, None]
        ok = ok | fill
    # reorder to Unity axes: +X -X +Y(up) -Y +Z(north) -Z
    u = grid[..., [0, 1, 4, 5, 2, 3], :]
    data = np.round(u.reshape(-1), 4).tolist()
    org = H.to_unity((xs[0], ys[0], zs[0]))
    spacing = [float(xs[1] - xs[0]) if nx > 1 else 1.0, float(zs[1] - zs[0]) if nz > 1 else 1.0, float(ys[1] - ys[0]) if ny > 1 else 1.0]
    H.log("probes: %d, %d were inside geometry and got filled" % (n, int(bad.sum())))
    return dict(origin=[float(v) for v in org], spacing=spacing, dims=[nx, nz, ny], data=data)


def camera_for(view, coll):
    cd = bpy.data.cameras.new("Cam_" + view["name"])
    cd.sensor_fit = "VERTICAL"
    cd.angle = math.radians(view.get("fov", 62.0))
    cd.clip_start = 0.05
    cd.clip_end = 500.0
    cam = bpy.data.objects.new("Cam_" + view["name"], cd)
    eye = Vector(tuple(float(v) for v in view["eye"]))
    tgt = Vector(tuple(float(v) for v in view["target"]))
    cam.location = eye
    cam.rotation_mode = "QUATERNION"
    cam.rotation_quaternion = (tgt - eye).to_track_quat("-Z", "Y")
    coll.objects.link(cam)
    return cam


def render_views(views, folder, prefix, samples, exposure_for, denoise, coll, res=(960, 540)):
    scene = bpy.context.scene
    os.makedirs(folder, exist_ok=True)
    scene.render.resolution_x, scene.render.resolution_y = res
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.cycles.samples = samples
    scene.cycles.use_denoising = denoise
    try:
        scene.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    for v in views:
        cam = camera_for(v, coll)
        scene.camera = cam
        scene.view_settings.exposure = exposure_for(v)
        scene.render.filepath = os.path.join(folder, "%s_%s.png" % (prefix, v["name"]))
        t = time.time()
        bpy.ops.render.render(write_still=True)
        H.log("rendered %s_%s in %.1f s" % (prefix, v["name"], time.time() - t))


def run(objects, sun_dir, samples=192, quick=False):
    t0 = time.time()
    clear_scene()
    scene = bpy.context.scene
    try:
        scene.view_settings.view_transform = "AgX"
    except Exception:
        scene.view_settings.view_transform = "Filmic"
    coll = bpy.data.collections.new("House")
    scene.collection.children.link(coll)
    bmats = {name: make_material(m) for name, m in H.MATS.items()}
    arrays, bobjs = {}, {}
    for oi, o in enumerate(objects):
        if not o["render"]:
            continue
        P, N, UV, sizes, fm, mats = H.object_arrays(o["geo"])
        arrays[oi] = (P, N, sizes)
        bobjs[oi] = make_mesh_object(o["name"], P, N, UV, sizes, fm, mats, bmats, coll)
    xs, ys, zs = probe_grid()
    centers, PP = probe_mesh(xs, ys, zs)
    pmat = bpy.data.materials.new("ProbeMat")
    nprobe = len(PP)
    psizes = np.full(nprobe // 4, 4, np.int32)
    probes = make_mesh_object("Probes", PP, np.zeros_like(PP) + (0, 0, 1), np.zeros((nprobe, 2)), psizes,
                              np.zeros(len(psizes), np.int32), ["ProbeMat"], {"ProbeMat": pmat}, coll, custom_normals=False)
    setup_world_and_sun(sun_dir)
    lamps = add_lamps(coll)
    H.log("blender scene ready: %d meshes, %d lamps, %d probes (%.1f s)" % (len(bobjs), lamps, len(centers), time.time() - t0))

    bake_ids = [oi for oi in bobjs if objects[oi]["bake"]]
    bake([bobjs[oi] for oi in bake_ids] + [probes], samples if not quick else 32)

    light = {}
    stats = {}
    for oi in bake_ids:
        P, N, sizes = arrays[oi]
        raw = read_light(bobjs[oi])
        L = H.smooth_light(P, N, raw, sizes)
        write_light(bobjs[oi], L)
        light[oi] = L.astype(np.float32)
        lum = L.mean(1)
        stats[objects[oi]["name"]] = [round(float(np.percentile(lum, q)), 4) for q in (10, 50, 90, 99)]
    for k, v in stats.items():
        H.log("light %-16s p10 %.3f  p50 %.3f  p90 %.3f  p99 %.3f" % (k, v[0], v[1], v[2], v[3]))
    pdata = finish_probes(centers, read_light(probes), xs, ys, zs)
    probes.hide_render = True

    renders = os.path.join(H.OUT, "Renders")
    views = [v for v in H.VIEWS]

    def exposure(v):
        return 0.0 if v["name"] in ("exterior", "aerial") else 1.0
    if not quick:
        try:
            beauty = [v for v in views if v["name"] in ("aerial", "exterior", "living", "kitchen", "master")]
            cycles_setup(64)
            render_views(beauty, renders, "blender", 64, exposure, True, coll)
        except Exception as e:
            H.log("beauty render failed:", e)
    try:
        gm = {name: make_game_material(m, bmats[name]) for name, m in H.MATS.items()}
        for oi, ob in bobjs.items():
            me = ob.data
            for i, mt in enumerate(me.materials):
                if mt is not None and mt.name in gm:
                    me.materials[i] = gm[mt.name]
        scene.cycles.max_bounces = 0
        scene.cycles.transparent_max_bounces = 8
        render_views(views, renders, "baked", 16, exposure, False, coll, res=(800, 450))
    except Exception as e:
        H.log("baked-look render failed:", e)
    extra = dict(probes=pdata, bake=dict(samples=samples, stats=stats, seconds=round(time.time() - t0, 1)))
    return light, extra
