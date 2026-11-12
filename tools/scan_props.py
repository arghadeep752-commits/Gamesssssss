"""Chaya - real scanned models (Poly Haven, CC0) turned into game props inside Blender.

Used by tools/build_map.py. For each model: import the glTF, join its parts, bake the transforms, decimate it to a
phone-friendly triangle budget, put its origin at the bottom centre (front facing -Y, Blender's front view), scale it
to the size it has in the house, and rename its materials scan_<name> (the game keeps their photo textures as they
are, instead of swapping in the house materials).
"""
import glob
import math
import os

import bmesh
import bpy
from mathutils import Matrix, Vector

ROOT = ""
_templates = {}
_failed = set()


def setup(scans_dir):
    global ROOT
    ROOT = scans_dir


def available(mid):
    return bool(ROOT) and bool(glob.glob(os.path.join(ROOT, "models", mid, "*.gltf")))


def _tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def _select_only(obs, active):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active


def _smooth(me, angle=40.0):
    for p in me.polygons:
        p.use_smooth = True
    try:
        if hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(angle)
        elif hasattr(me, "set_sharp_from_angle"):
            me.set_sharp_from_angle(angle=math.radians(angle))
    except Exception:       # noqa: BLE001
        pass


def import_raw(mid):
    """Import a model and join it into one mesh object with transforms applied (still at its own scale/place)."""
    files = glob.glob(os.path.join(ROOT, "models", mid, "*.gltf"))
    if not files:
        raise RuntimeError("model %s not downloaded" % mid)
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=files[0])
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("model %s has no meshes" % mid)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    for o in meshes:                                       # own mesh data, transforms baked in
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(o.matrix_world)
        o.matrix_world = Matrix.Identity(4)
    _select_only(meshes, meshes[0])
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = "scan_" + mid
    ob.data.name = "scan_" + mid
    for m in ob.data.materials:
        if m is not None and not m.name.startswith("scan_"):
            m.name = "scan_" + m.name
    return ob


def import_glb(path, name):
    """Import a ready-made GLB (tools/ai3d: AI models already scaled, origin at the bottom centre, front -Y) as one
    mesh object with its own materials and textures."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    meshes = [o for o in new if o.type == "MESH"]
    if not meshes:
        raise RuntimeError("no mesh in %s" % path)
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        if o.data.users > 1:
            o.data = o.data.copy()
        o.data.transform(mw)
        o.matrix_world = Matrix.Identity(4)
    for o in new:
        if o.type != "MESH":
            bpy.data.objects.remove(o, do_unlink=True)
    _select_only(meshes, meshes[0])
    if len(meshes) > 1:
        bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    for c in list(ob.users_collection):
        c.objects.unlink(ob)
    for m in ob.data.materials:
        if m is not None and not m.name.startswith("scan_"):
            m.name = "scan_" + m.name
    return ob


def decimate(ob, budget):
    me = ob.data
    t = _tris(me)
    if t <= budget * 1.15:
        return t, t
    mod = ob.modifiers.new("dec", "DECIMATE")
    mod.ratio = max(0.01, budget / float(t))
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.clear()
    old = ob.data
    ob.data = me2
    me2.name = old.name
    bpy.data.meshes.remove(old)
    try:                                                   # custom normals do not survive decimation
        if me2.has_custom_normals:
            _select_only([ob], ob)
            bpy.ops.mesh.customdata_custom_splitnormals_clear()
    except Exception as ex:     # noqa: BLE001
        print("  (custom normals kept: %s)" % ex)
    _smooth(me2)
    return t, _tris(me2)


def bbox(me):
    xs = [v.co for v in me.vertices]
    mn = Vector((min(v.x for v in xs), min(v.y for v in xs), min(v.z for v in xs)))
    mx = Vector((max(v.x for v in xs), max(v.y for v in xs), max(v.z for v in xs)))
    return mn, mx


def normalise(ob, rot=0.0, long_x=False, fit=None, height=None):
    """Origin at the bottom centre; optional turn about Z; scale so it fits `fit` = (max x, max y, max z) or has
    exactly `height`. Returns the size (x, y, z)."""
    me = ob.data
    if long_x:
        mn, mx = bbox(me)
        if (mx.y - mn.y) > (mx.x - mn.x) * 1.08:
            rot += 90.0
    if rot:
        me.transform(Matrix.Rotation(math.radians(rot), 4, "Z"))
    mn, mx = bbox(me)
    me.transform(Matrix.Translation((-(mn.x + mx.x) / 2, -(mn.y + mx.y) / 2, -mn.z)))
    size = mx - mn
    s = 1.0
    if height:
        s = height / max(size.z, 1e-6)
    elif fit:
        for k in range(3):
            if fit[k] and size[k] > fit[k]:
                s = min(s, fit[k] / size[k])
    if abs(s - 1.0) > 1e-4:
        me.transform(Matrix.Scale(s, 4))
    me.update()
    mn, mx = bbox(me)
    return mx - mn


def template(mid, budget=4000, rot=0.0, long_x=False, fit=None, height=None, key=None):
    """A processed copy of the model kept out of the scene; instances share its mesh. None if unavailable."""
    key = key or mid
    if key in _templates:
        return _templates[key]
    if key in _failed or not available(mid):
        return None
    try:
        ob = import_raw(mid)
        t0, t1 = decimate(ob, budget)
        size = normalise(ob, rot, long_x, fit, height)
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        ob.name = "tmpl_" + key
        print("scan %-28s %6d -> %5d tris  size %.2f x %.2f x %.2f  mats %s" % (
            key, t0, t1, size.x, size.y, size.z, [m.name for m in ob.data.materials if m]))
        _templates[key] = (ob, size)
        return _templates[key]
    except Exception as ex:     # noqa: BLE001
        import traceback
        traceback.print_exc()
        print("SCAN %s FAILED: %s" % (key, ex))
        _failed.add(key)
        return None


def instance(key, name, collection, parent=None, loc=(0.0, 0.0, 0.0), rot_z=0.0, scale=1.0):
    t = _templates.get(key)
    if t is None:
        return None
    ob = bpy.data.objects.new(name, t[0].data)
    collection.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.rotation_euler = (0.0, 0.0, rot_z)
    ob.scale = (scale, scale, scale)
    return ob


def surface_z(ob, x, y, above=2.0):
    """Height of the first surface straight below (x, y) in the object's own space (None if nothing there)."""
    try:
        ok, loc, _n, _i = ob.ray_cast(Vector((x, y, above)), Vector((0.0, 0.0, -1.0)))
        return loc.z if ok else None
    except Exception:       # noqa: BLE001 - not in the scene: no evaluated mesh to hit
        return None


def rim_radius(me, frac=0.93):
    """Widest radius of the top few percent of a vessel (its mouth)."""
    mn, mx = bbox(me)
    zc = mn.z + (mx.z - mn.z) * frac
    rs = [math.hypot(v.co.x, v.co.y) for v in me.vertices if v.co.z >= zc]
    return max(rs) if rs else (mx.x - mn.x) / 2


def loose_parts(ob):
    """Split an object into its connected pieces (returns the list of new objects, all in the scene)."""
    _select_only([ob], ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.mesh.separate(type="LOOSE")
    bpy.ops.object.mode_set(mode="OBJECT")
    return [o for o in bpy.context.selected_objects]


def candle_from_set(target_h=0.24):
    """The single brass candlestick at the left of Poly Haven's 'brass candleholders' set, with its white candle.
    Returns (object at the origin, flame anchor position) or None."""
    if not available("brass_candleholders"):
        return None
    ob = import_raw("brass_candleholders")
    parts = loose_parts(ob)
    info = []
    for p in list(parts):
        # the flame cards are part of each candle's mesh: cut them off (the game draws its own flame)
        fl = [i for i, m in enumerate(p.data.materials) if m and "flame" in m.name.lower()]
        if fl:
            bm = bmesh.new()
            bm.from_mesh(p.data)
            dead = [f for f in bm.faces if f.material_index in fl]
            if dead:
                bmesh.ops.delete(bm, geom=dead, context="FACES")
            bm.to_mesh(p.data)
            bm.free()
            p.data.update()
        if len(p.data.polygons) == 0:
            bpy.data.objects.remove(p, do_unlink=True)
            continue
        mn, mx = bbox(p.data)
        used = {pl.material_index for pl in p.data.polygons}          # separate() keeps every slot: look at the faces
        mats = " ".join(p.data.materials[i].name.lower() for i in used if i < len(p.data.materials) and p.data.materials[i])
        info.append([p, mn, mx, mats])
    print("candle set: %d pieces, materials %s" % (len(info), sorted({r[3] for r in info})))
    flames = [r for r in info if "flame" in r[3]]
    for r in flames:
        bpy.data.objects.remove(r[0], do_unlink=True)
    info = [r for r in info if "flame" not in r[3]]
    info.sort(key=lambda r: r[1].x)
    # the left-most cluster of overlapping pieces along x = the single candlestick
    cluster = [info[0]]
    hi = info[0][2].x
    for r in info[1:]:
        if r[1].x <= hi + 0.01:
            cluster.append(r)
            hi = max(hi, r[2].x)
        else:
            break
    rest = [r for r in info if r not in cluster]
    for r in rest:
        bpy.data.objects.remove(r[0], do_unlink=True)
    wax = [r for r in cluster if "candles" in r[3] or "wax" in r[3]]
    obs = [r[0] for r in cluster]
    _select_only(obs, obs[0])
    if len(obs) > 1:
        bpy.ops.object.join()
    cob = bpy.context.view_layer.objects.active
    cob.name = "candle_scan"
    mn, mx = bbox(cob.data)
    top = max(r[2].z for r in wax) if wax else mx.z
    if wax:
        w = max(wax, key=lambda r: r[2].z)
        ax, ay = (w[1].x + w[2].x) / 2, (w[1].y + w[2].y) / 2
    else:
        ax, ay = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    cx, cy = (mn.x + mx.x) / 2, (mn.y + mx.y) / 2
    s = target_h / max(top - mn.z, 1e-6)
    cob.data.transform(Matrix.Scale(s, 4) @ Matrix.Translation((-cx, -cy, -mn.z)))
    decimate(cob, 7000)
    anchor = Vector(((ax - cx) * s, (ay - cy) * s, (top - mn.z) * s + 0.012))
    print("candle from brass_candleholders: %d pieces, %d tris, height %.3f, wax pieces %d" % (
        len(cluster), _tris(cob.data), (top - mn.z) * s, len(wax)))
    return cob, anchor


def candle_wooden(target_h=0.22):
    if not available("wooden_candlestick"):
        return None
    ob = import_raw("wooden_candlestick")
    decimate(ob, 6000)
    size = normalise(ob, height=target_h)
    return ob, Vector((0.0, 0.0, size.z + 0.012))


def render_icon(ob, path, px=256):
    """A transparent-background studio shot of one object (the HUD's list of ritual items)."""
    sc = bpy.data.scenes.new("icon")
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    try:
        sc.cycles.use_denoising = False
    except Exception:       # noqa: BLE001
        pass
    sc.render.resolution_x = sc.render.resolution_y = px
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    try:
        sc.view_settings.view_transform = "Standard"
    except Exception:       # noqa: BLE001
        pass
    w = bpy.data.worlds.new("icon_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.45, 0.4, 0.36, 1.0)
        bg.inputs[1].default_value = 0.3
    sc.world = w
    col = sc.collection
    dup = bpy.data.objects.new("icon_obj", ob.data)
    dup.matrix_world = Matrix.Identity(4)
    col.objects.link(dup)
    kids = []
    for ch in ob.children:
        if ch.type == "MESH":
            k = bpy.data.objects.new("icon_kid", ch.data)
            k.matrix_world = ch.matrix_local.copy()
            col.objects.link(k)
            kids.append(k)
    mn, mx = bbox(ob.data)
    c = (mn + mx) / 2
    sz = mx - mn
    r = max(sz.length / 2, 0.02)
    cam_d = bpy.data.cameras.new("icon_cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = max(sz.x, sz.y * 0.55 + sz.z * 0.85, 0.04) * 1.12
    cam = bpy.data.objects.new("icon_cam", cam_d)
    col.objects.link(cam)
    d = Vector((0.0, -1.0, 0.62)).normalized()
    cam.location = c + d * (r * 6.0)
    cam.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    for (loc, en, sz) in (((-1.2, -1.4, 1.6), 13.0, 1.2), ((1.6, -0.6, 0.9), 4.0, 1.5), ((0.4, 1.6, 1.4), 9.0, 0.8)):
        ld = bpy.data.lights.new("icon_light", "AREA")
        ld.energy = en * (r / 0.15) ** 2
        ld.size = sz * r * 4
        lo = bpy.data.objects.new("icon_light", ld)
        lo.location = c + Vector(loc) * (r * 5.0)
        lo.rotation_euler = (c - lo.location).to_track_quat("-Z", "Y").to_euler()
        col.objects.link(lo)
    sc.render.filepath = path
    win_scene = bpy.context.window.scene if bpy.context.window else None
    try:
        bpy.ops.render.render(write_still=True, scene=sc.name)
    finally:
        if win_scene:
            bpy.context.window.scene = win_scene
    bpy.data.scenes.remove(sc)
    print("icon", os.path.basename(path))


def contact_sheet(keys, path, cols=8, cell=2.0):
    """Every processed template side by side, seen from the front (checks facing and scale in CI)."""
    sc = bpy.data.scenes.new("sheet")
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24
    try:
        sc.cycles.use_denoising = False
    except Exception:       # noqa: BLE001
        pass
    rows = -(-len(keys) // cols)
    sc.render.resolution_x = 1800
    sc.render.resolution_y = int(1800 * rows * 1.15 / cols)
    w = bpy.data.worlds.new("sheet_world")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.5, 0.5, 0.52, 1.0)
        bg.inputs[1].default_value = 1.0
    sc.world = w
    col = sc.collection
    for k, key in enumerate(keys):
        t = _templates.get(key)
        if t is None:
            continue
        ob, size = t
        s = (cell * 0.8) / max(size.x, size.y, size.z, 1e-3)
        x = (k % cols) * cell
        z = -(k // cols) * cell * 1.15
        o = bpy.data.objects.new("sheet_" + key, ob.data)
        o.location = (x, 0.0, z - size.z * s / 2)
        o.scale = (s, s, s)
        col.objects.link(o)
        cu = bpy.data.curves.new("lbl", "FONT")
        cu.body = "%s %.2fx%.2fx%.2f" % (key, size.x, size.y, size.z)
        cu.size = 0.11
        cu.align_x = "CENTER"
        lo = bpy.data.objects.new("lbl", cu)
        lo.location = (x, -1.0, z - cell * 0.52)
        lo.rotation_euler = (math.radians(90), 0, 0)
        col.objects.link(lo)
    cam_d = bpy.data.cameras.new("sheet_cam")
    cam_d.type = "ORTHO"
    cam_d.ortho_scale = cols * cell
    cam = bpy.data.objects.new("sheet_cam", cam_d)
    cam.location = ((cols - 1) * cell / 2, -30.0, -(rows - 1) * cell * 1.15 / 2)
    cam.rotation_euler = (math.radians(90), 0, 0)
    col.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.0
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(60), math.radians(-25), math.radians(-30))
    col.objects.link(so)
    sc.render.filepath = path
    sc.render.image_settings.file_format = "JPEG"
    bpy.ops.render.render(write_still=True, scene=sc.name)
    bpy.data.scenes.remove(sc)
    print("contact sheet", path)
