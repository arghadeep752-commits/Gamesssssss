"""Makes the game's furniture from scratch in Blender: a three-seat sofa and a chest of drawers.

Run it with no window (this is what the GitHub workflow does):
    blender -b --python-exit-code 1 -P tools/blender/make_furniture.py -- <output folder>

Everything here is modelled from boxes, bevels and lathe profiles. Every texture is baked from
Blender's own procedural noise (fabric, wood grain, worn edges, dirt in the corners), so there
are no downloaded models, photos or AI images in it.

Output:
    sofa/sofa.gltf   (+ .bin and textures/)   one mesh "Sofa", front facing +Z in Godot
    chest/chest.gltf (+ .bin and textures/)   "Frame" + empties "Drawer1".."Drawer5", each with a
                                              "DrawerNBox" (wood) and "DrawerNKnob" (brass) mesh
    previews/*.jpg                            Cycles renders to check the look
"""
import bpy
import bmesh
import json
import math
import os
import random
import sys
import time

import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(ARGS[0] if ARGS else "furniture_out")
T0 = time.time()
R90 = math.pi / 2.0
INFO = {}
AXES = {'X': Vector((1.0, 0.0, 0.0)), 'Y': Vector((0.0, 1.0, 0.0)), 'Z': Vector((0.0, 0.0, 1.0))}
IDX = {'X': 0, 'Y': 1, 'Z': 2}


def log(*parts):
    print("[furniture %6.1fs]" % (time.time() - T0), *parts, flush=True)


# ---------------------------------------------------------------------------------- scene

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.use_denoising = False
    world = bpy.data.worlds.new("World")
    sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    world.light_settings.distance = 0.12   # reach of the baked ambient occlusion (metres)
    return sc


def select(objs):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objs:
        ob.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


# ---------------------------------------------------------------------------------- meshes

def link_obj(name, bm, mats, loc=(0.0, 0.0, 0.0), rot=(0.0, 0.0, 0.0)):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def bm_box(sx, sy, sz, cuts=0):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if cuts:
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=cuts, use_grid_fill=True)
    bm.normal_update()
    return bm


def bevel(ob, width, segments, limit='ANGLE'):
    m = ob.modifiers.new("Bevel", 'BEVEL')
    m.width = width
    m.segments = segments
    m.limit_method = limit
    if limit == 'ANGLE':
        m.angle_limit = math.radians(30.0)
    m.use_clamp_overlap = True


def subsurf(ob, levels):
    m = ob.modifiers.new("Subsurf", 'SUBSURF')
    m.levels = levels
    m.render_levels = levels


def apply_modifiers(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    me.name = ob.name


def hard_shading(ob):
    """Wood: big flat faces stay flat, bevels and curves are smooth, real corners stay sharp."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()

    def flat(f):
        n = f.normal
        return max(abs(n.x), abs(n.y), abs(n.z)) > 0.999

    for f in bm.faces:
        f.smooth = not flat(f)
    for e in bm.edges:
        if len(e.link_faces) != 2:
            e.smooth = False
            continue
        f1, f2 = e.link_faces
        e.smooth = not (flat(f1) or flat(f2)) and e.calc_face_angle(math.pi) < math.radians(40.0)
    bm.to_mesh(ob.data)
    bm.free()


def angle_shading(ob, degrees=45.0):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.normal_update()
    for f in bm.faces:
        f.smooth = True
    for e in bm.edges:
        e.smooth = len(e.link_faces) == 2 and e.calc_face_angle(math.pi) < math.radians(degrees)
    bm.to_mesh(ob.data)
    bm.free()


def soft_shading(ob):
    for p in ob.data.polygons:
        p.use_smooth = True


def turn(ax, ay, az):
    """Rotation that puts the object's own X, Y, Z axes along the given world directions."""
    return Matrix((ax, ay, az)).transposed().to_euler()


def board(name, mat, center, size, grain='X', bev=0.003, segs=2, hook=None):
    """A wooden board. `size` is its extent along world X, Y, Z; `grain` is the direction the wood
    grain runs. The board's own X axis follows the grain and its own Z axis its thickness, so the
    procedural wood (wood_material) cuts the growth rings like a real flat-sawn plank."""
    others = [a for a in 'XYZ' if a != grain]
    thick = min(others, key=lambda a: size[IDX[a]])
    width = [a for a in others if a != thick][0]
    local = (size[IDX[grain]], size[IDX[width]], size[IDX[thick]])
    ax, az = AXES[grain], AXES[thick]
    rot = turn(ax, az.cross(ax), az)
    bm = bm_box(*local)
    if hook:
        hook(bm)
    ob = link_obj(name, bm, [mat], center, rot)
    if bev > 0.0:
        bevel(ob, bev, segs)
    apply_modifiers(ob)
    hard_shading(ob)
    return ob


def profile_board(name, mat, outline, thickness, loc, along, bev=0.003):
    """A board cut to a 2D outline (u along the board, v up), standing upright, running along the
    world direction `along`. Own X = along (grain), own Y = up, own Z = thickness."""
    bm = bmesh.new()
    vs = [bm.verts.new((u, v, -thickness / 2.0)) for u, v in outline]
    face = bm.faces.new(vs)
    res = bmesh.ops.extrude_face_region(bm, geom=[face])
    new_verts = [g for g in res["geom"] if isinstance(g, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=(0.0, 0.0, thickness), verts=new_verts)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ax, ay = Vector(along), AXES['Z']
    ob = link_obj(name, bm, [mat], loc, turn(ax, ay, ax.cross(ay)))
    bevel(ob, bev, 2)
    apply_modifiers(ob)
    hard_shading(ob)
    return ob


def lathe(name, mat, profile, axis='Z', steps=20, loc=(0.0, 0.0, 0.0)):
    """Turned part: `profile` is a list of (radius, height); spun around Z (or out along -Y)."""
    bm = bmesh.new()
    if axis == 'Z':
        vs = [bm.verts.new((r, 0.0, h)) for r, h in profile]
        ax = (0.0, 0.0, 1.0)
    else:
        vs = [bm.verts.new((r, -h, 0.0)) for r, h in profile]
        ax = (0.0, 1.0, 0.0)
    edges = [bm.edges.new((vs[i], vs[i + 1])) for i in range(len(vs) - 1)]
    bmesh.ops.spin(bm, geom=vs + edges, cent=(0.0, 0.0, 0.0), axis=ax, angle=2.0 * math.pi,
                   steps=steps, use_merge=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges[:])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    ob = link_obj(name, bm, [mat], loc)
    angle_shading(ob, 50.0)
    return ob


def puff(ob, axis, amount, half):
    """Cushion bulge: pushes the faces across `axis` outwards, most in the middle."""
    hx, hy, hz = half
    for v in ob.data.vertices:
        x, y, z = v.co
        if axis == 'Z':
            u, w, t = x / hx, y / hy, z / hz
        else:
            u, w, t = x / hx, z / hz, y / hy
        k = max(0.0, 1.0 - u * u) * max(0.0, 1.0 - w * w)
        if axis == 'Z':
            v.co.z = z + amount * k * t
        else:
            v.co.y = y + amount * k * t
    ob.data.update()


def join(objs, name):
    if len(objs) > 1:
        select(objs)
        bpy.ops.object.join()
    ob = objs[0] if len(objs) == 1 else bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


# ---------------------------------------------------------------------------------- shader helpers

def N(nt, typ, **props):
    nd = nt.nodes.new(typ)
    for k, v in props.items():
        setattr(nd, k, v)
    return nd


def put(nt, sock, value):
    if isinstance(value, bpy.types.NodeSocket):
        nt.links.new(value, sock)
    else:
        sock.default_value = value


def noise(nt, vec, scale, detail=2.0, rough=0.5, distortion=0.0):
    nd = N(nt, 'ShaderNodeTexNoise')
    put(nt, nd.inputs['Vector'], vec)
    nd.inputs['Scale'].default_value = scale
    nd.inputs['Detail'].default_value = detail
    nd.inputs['Roughness'].default_value = rough
    nd.inputs['Distortion'].default_value = distortion
    return nd.outputs['Fac']


def mapping(nt, vec, scale=(1.0, 1.0, 1.0), loc=(0.0, 0.0, 0.0)):
    nd = N(nt, 'ShaderNodeMapping')
    put(nt, nd.inputs['Vector'], vec)
    nd.inputs['Scale'].default_value = scale
    nd.inputs['Location'].default_value = loc
    return nd.outputs['Vector']


def fmath(nt, op, a, b=0.0, clamp=False):
    nd = N(nt, 'ShaderNodeMath', operation=op, use_clamp=clamp)
    put(nt, nd.inputs[0], a)
    put(nt, nd.inputs[1], b)
    return nd.outputs['Value']


def remap(nt, x, a, b, c=0.0, d=1.0):
    nd = N(nt, 'ShaderNodeMapRange')
    put(nt, nd.inputs['Value'], x)
    nd.inputs['From Min'].default_value = a
    nd.inputs['From Max'].default_value = b
    nd.inputs['To Min'].default_value = c
    nd.inputs['To Max'].default_value = d
    return nd.outputs['Result']


def vmath(nt, op, a, b=None, scale=None):
    nd = N(nt, 'ShaderNodeVectorMath', operation=op)
    put(nt, nd.inputs[0], a)
    if b is not None:
        put(nt, nd.inputs[1], b)
    if scale is not None:
        put(nt, nd.inputs['Scale'], scale)
    return nd.outputs['Value'] if op == 'DOT_PRODUCT' else nd.outputs['Vector']


def vscale(nt, a, s):
    return vmath(nt, 'SCALE', a, scale=s)


def vmix(nt, a, b, t):
    return vmath(nt, 'ADD', a, vscale(nt, vmath(nt, 'SUBTRACT', b, a), t))


def edge_wear(nt, radius, lo, hi):
    """1 on worn-down edges, 0 on flat surfaces (Cycles bevel normal against the real normal)."""
    bev = N(nt, 'ShaderNodeBevel', samples=4)
    bev.inputs['Radius'].default_value = radius
    geo = N(nt, 'ShaderNodeNewGeometry')
    d = vmath(nt, 'DOT_PRODUCT', bev.outputs['Normal'], geo.outputs['Normal'])
    return remap(nt, d, hi, lo, 0.0, 1.0)


def bump(nt, bsdf, height, strength, distance):
    nd = N(nt, 'ShaderNodeBump')
    nd.inputs['Strength'].default_value = strength
    nd.inputs['Distance'].default_value = distance
    put(nt, nd.inputs['Height'], height)
    nt.links.new(nd.outputs['Normal'], bsdf.inputs['Normal'])


def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    return m, m.node_tree, m.node_tree.nodes["Principled BSDF"]


def object_coords(nt, jitter):
    """Object-space position, shifted by a random amount per object so no two parts look the same."""
    tc = N(nt, 'ShaderNodeTexCoord')
    oi = N(nt, 'ShaderNodeObjectInfo')
    return vmath(nt, 'ADD', tc.outputs['Object'], vscale(nt, jitter, oi.outputs['Random']))


# ---------------------------------------------------------------------------------- materials

def fabric_material():
    """Old faded oxblood upholstery: mottled, rubbed lighter on the edges, a few dark stains."""
    m, nt, b = new_material("Fabric")
    p = object_coords(nt, (3.1, 7.7, 5.3))
    base, faded, dark = (0.105, 0.024, 0.021), (0.20, 0.075, 0.062), (0.038, 0.012, 0.010)
    col = vmix(nt, base, faded, remap(nt, noise(nt, p, 4.0, 6.0, 0.6), 0.35, 0.75, 0.0, 0.55))
    col = vmix(nt, col, faded, fmath(nt, 'MULTIPLY', edge_wear(nt, 0.012, 0.70, 0.985), 0.75))
    fuzz = noise(nt, p, 160.0, 4.0, 0.6)
    col = vscale(nt, col, remap(nt, fuzz, 0.3, 0.7, 0.86, 1.12))
    col = vmix(nt, col, dark, remap(nt, noise(nt, p, 1.8, 3.0, 0.5), 0.60, 0.68, 0.0, 0.6))
    put(nt, b.inputs['Base Color'], col)
    b.inputs['Roughness'].default_value = 0.9
    wrinkles = noise(nt, p, 11.0, 3.0, 0.55, 1.2)
    height = fmath(nt, 'ADD', fmath(nt, 'MULTIPLY', fuzz, 0.35), fmath(nt, 'MULTIPLY', wrinkles, 0.65))
    bump(nt, b, height, 0.35, 0.004)
    return m


def wood_material(name, tone=1.0):
    """Old varnished hardwood. Each board's own X runs along the grain and its own Z is its
    thickness (see board()); the tree's centre sits a little above the board, so the face shows
    flat-sawn "cathedral" figure. Plus long pore streaks, colour streaks and worn lighter edges."""
    m, nt, b = new_material(name)
    tc = N(nt, 'ShaderNodeTexCoord')
    r = N(nt, 'ShaderNodeObjectInfo').outputs['Random']

    def rand(k):
        return fmath(nt, 'FRACT', fmath(nt, 'MULTIPLY', r, k))

    centre = N(nt, 'ShaderNodeCombineXYZ')
    put(nt, centre.inputs['X'], fmath(nt, 'MULTIPLY', r, 9.1))
    put(nt, centre.inputs['Y'], fmath(nt, 'MULTIPLY', fmath(nt, 'SUBTRACT', rand(7.31), 0.5), 0.16))
    put(nt, centre.inputs['Z'], fmath(nt, 'ADD', 0.28, fmath(nt, 'MULTIPLY', rand(3.77), 0.25)))
    p = vmath(nt, 'ADD', tc.outputs['Object'], centre.outputs['Vector'])
    tilt = N(nt, 'ShaderNodeMapping')          # rings rise and fall along the board -> arches
    put(nt, tilt.inputs['Vector'], p)
    tilt.inputs['Rotation'].default_value = (0.0, 0.018, 0.0)
    wave = N(nt, 'ShaderNodeTexWave', wave_type='RINGS', rings_direction='X')
    put(nt, wave.inputs['Vector'], mapping(nt, tilt.outputs['Vector'], (0.25, 1.0, 1.0)))
    wave.inputs['Scale'].default_value = 170.0
    wave.inputs['Distortion'].default_value = 9.0
    wave.inputs['Detail'].default_value = 3.0
    wave.inputs['Detail Scale'].default_value = 0.05
    wave.inputs['Detail Roughness'].default_value = 0.5
    rings = wave.outputs['Fac']
    light = (0.15 * tone, 0.072 * tone, 0.030 * tone)
    darkc = (0.088 * tone, 0.040 * tone, 0.016 * tone)
    col = vmix(nt, light, darkc, remap(nt, rings, 0.6, 1.0))
    streaks = noise(nt, mapping(nt, p, (1.5, 30.0, 30.0)), 1.0, 3.0, 0.5)
    col = vscale(nt, col, remap(nt, streaks, 0.3, 0.7, 0.84, 1.12))
    pores = remap(nt, noise(nt, mapping(nt, p, (6.0, 280.0, 280.0)), 1.0, 2.0, 0.5), 0.5, 0.75)
    col = vscale(nt, col, remap(nt, pores, 0.0, 1.0, 1.0, 0.85))
    big = noise(nt, p, 1.4, 2.0, 0.5)
    col = vscale(nt, col, remap(nt, big, 0.3, 0.7, 0.88, 1.1))
    wear = edge_wear(nt, 0.004, 0.80, 0.985)
    col = vmix(nt, col, vscale(nt, col, 1.7), fmath(nt, 'MULTIPLY', wear, 0.55))
    put(nt, b.inputs['Base Color'], col)
    rough = fmath(nt, 'ADD', 0.34, fmath(nt, 'MULTIPLY', pores, 0.12))
    rough = fmath(nt, 'ADD', rough, fmath(nt, 'MULTIPLY', wear, 0.25))
    rough = fmath(nt, 'ADD', rough, fmath(nt, 'MULTIPLY', fmath(nt, 'SUBTRACT', big, 0.5), 0.1), clamp=True)
    put(nt, b.inputs['Roughness'], rough)
    height = fmath(nt, 'ADD', fmath(nt, 'MULTIPLY', rings, 0.3), fmath(nt, 'MULTIPLY', pores, 0.7))
    bump(nt, b, height, 0.06, 0.0005)
    return m


def brass_material():
    m, nt, b = new_material("Brass")
    b.inputs['Base Color'].default_value = (0.72, 0.50, 0.22, 1.0)
    b.inputs['Metallic'].default_value = 1.0
    b.inputs['Roughness'].default_value = 0.3
    return m


def baked_material(name, albedo, normal, orm=None, rough=0.8):
    """The material that goes into the glTF file: just the baked pictures."""
    m, nt, b = new_material(name)
    t = N(nt, 'ShaderNodeTexImage')
    t.image = albedo
    nt.links.new(t.outputs['Color'], b.inputs['Base Color'])
    tn = N(nt, 'ShaderNodeTexImage')
    tn.image = normal
    nm = N(nt, 'ShaderNodeNormalMap')
    nt.links.new(tn.outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Metallic'].default_value = 0.0
    if orm is not None:
        to = N(nt, 'ShaderNodeTexImage')
        to.image = orm
        sep = N(nt, 'ShaderNodeSeparateColor')
        nt.links.new(to.outputs['Color'], sep.inputs['Color'])
        nt.links.new(sep.outputs['Green'], b.inputs['Roughness'])
        nt.links.new(sep.outputs['Blue'], b.inputs['Metallic'])
    else:
        b.inputs['Roughness'].default_value = rough
    return m


# ---------------------------------------------------------------------------------- UVs and baking

def unwrap(objs, shrink=(), shrink_factor=0.5):
    """One shared texture atlas for all `objs`, islands 1% of the texture apart.
    Parts listed in `shrink` (hidden insides) get less room."""
    select(objs)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=0.003)
    bpy.ops.object.mode_set(mode='OBJECT')
    saved = {}
    for ob in shrink:
        data = ob.data.uv_layers.active.data
        saved[ob.name] = [d.uv.copy() for d in data]
        for d in data:
            d.uv = d.uv * shrink_factor
    try:
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        try:
            bpy.ops.uv.select_all(action='SELECT')
        except Exception as err:   # not needed on every Blender version
            log("uv.select_all skipped:", err)
        try:
            bpy.ops.uv.pack_islands(rotate=True, margin_method='FRACTION', margin=0.01)
        except TypeError:
            bpy.ops.uv.pack_islands(rotate=True, margin=0.01)
        bpy.ops.object.mode_set(mode='OBJECT')
        log("packed the atlas", "(insides at %.2f)" % shrink_factor if shrink else "")
    except Exception as err:
        if bpy.context.object and bpy.context.object.mode != 'OBJECT':
            bpy.ops.object.mode_set(mode='OBJECT')
        log("pack_islands failed, keeping the plain layout:", err)
        for ob in shrink:
            for d, uv in zip(ob.data.uv_layers.active.data, saved[ob.name]):
                d.uv = uv


def new_image(name, size, data, fill=(0.0, 0.0, 0.0)):
    im = bpy.data.images.new(name, size, size, alpha=False)
    if data:
        im.colorspace_settings.name = 'Non-Color'
    im.generated_color = (*fill, 1.0)
    return im


def pixels(im):
    a = np.empty(im.size[0] * im.size[1] * 4, dtype=np.float32)
    im.pixels.foreach_get(a)
    return a.reshape(im.size[1], im.size[0], 4)


def set_pixels(im, arr):
    im.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    im.update()


def blur(a, r=1):
    p = np.pad(a, r, mode='edge')
    out = np.zeros_like(a)
    for dy in range(2 * r + 1):
        for dx in range(2 * r + 1):
            out += p[dy:dy + a.shape[0], dx:dx + a.shape[1]]
    return out / float((2 * r + 1) ** 2)


def bake_atlas(objs, prefix, albedo_size=2048, normal_size=1024, rough_size=1024, ao_size=1024,
               bake_rough=True, ao_strength=0.85, fill=(0.2, 0.1, 0.05)):
    """Bakes colour, normal, roughness and ambient occlusion of `objs` into one atlas.
    The occlusion is multiplied into the colour (phones get no real-time AO in this renderer)."""
    sc = bpy.context.scene
    albedo = new_image(prefix + "_albedo", albedo_size, False, fill)
    normal = new_image(prefix + "_normal", normal_size, True, (0.5, 0.5, 1.0))
    ao = new_image(prefix + "_ao", ao_size, True, (1.0, 1.0, 1.0))
    rough = new_image(prefix + "_rough", rough_size, True, (0.5, 0.5, 0.5)) if bake_rough else None
    mats = []
    for ob in objs:
        for slot in ob.material_slots:
            if slot.material and slot.material not in mats:
                mats.append(slot.material)
    targets = {}
    for m in mats:
        tn = m.node_tree.nodes.new('ShaderNodeTexImage')
        targets[m] = tn
    select(objs)

    def bake(image, kind, samples, **kw):
        for m, tn in targets.items():
            tn.image = image
            m.node_tree.nodes.active = tn
        sc.cycles.samples = samples
        t = time.time()
        bpy.ops.object.bake(type=kind, margin=image.size[0] // 85, use_clear=False, **kw)
        log("baked", kind, image.name, "in %.1fs" % (time.time() - t))

    bake(albedo, 'DIFFUSE', 16, pass_filter={'COLOR'})
    bake(normal, 'NORMAL', 4, normal_space='TANGENT')
    if rough is not None:
        bake(rough, 'ROUGHNESS', 4)
    bake(ao, 'AO', 96)

    # colour x occlusion
    occ = pixels(ao)[:, :, 0]
    k = albedo.size[0] // ao.size[0]
    if k > 1:
        occ = np.repeat(np.repeat(occ, k, axis=0), k, axis=1)
    occ = np.clip(blur(occ, 1), 0.0, 1.0) ** 1.15
    col = pixels(albedo)
    col[:, :, :3] *= (1.0 - ao_strength + ao_strength * occ)[:, :, None]
    set_pixels(albedo, col)

    orm = None
    if rough is not None:
        r = pixels(rough)
        orm_px = np.ones_like(r)
        orm_px[:, :, 1] = r[:, :, 0]
        orm_px[:, :, 2] = 0.0
        orm = new_image(prefix + "_orm", rough_size, True)
        set_pixels(orm, orm_px)

    tex_dir = os.path.join(OUT, "_bakes")
    os.makedirs(tex_dir, exist_ok=True)
    for im in (albedo, normal, ao, orm):
        if im is not None:
            im.filepath_raw = os.path.join(tex_dir, im.name + ".png")
            im.file_format = 'PNG'
            im.save()
    return albedo, normal, orm


def export(objs, name):
    folder = os.path.join(OUT, name)
    os.makedirs(folder, exist_ok=True)
    select(objs)
    bpy.ops.export_scene.gltf(filepath=os.path.join(folder, name + ".gltf"), export_format='GLTF_SEPARATE',
                              export_texture_dir="textures", use_selection=True, export_apply=True,
                              export_yup=True, export_image_format='AUTO')
    log("exported", name)


# ---------------------------------------------------------------------------------- previews

def simple_material(name, color, rough):
    m, nt, b = new_material(name)
    b.inputs['Base Color'].default_value = (*color, 1.0)
    b.inputs['Roughness'].default_value = rough
    return m


def aim(ob, target):
    ob.rotation_euler = (Vector(target) - ob.location).to_track_quat('-Z', 'Y').to_euler()


def preview_stage(wall_y):
    sc = bpy.context.scene
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    link_obj("PreviewFloor", bm, [simple_material("PreviewFloorMat", (0.25, 0.16, 0.09), 0.55)])
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4.0)
    link_obj("PreviewWall", bm, [simple_material("PreviewWallMat", (0.10, 0.17, 0.08), 0.85)],
             (0.0, wall_y, 2.0), (R90, 0.0, 0.0))
    for name, loc, energy, size in (("Key", (2.2, -2.6, 2.8), 500.0, 1.2),
                                    ("Fill", (-2.8, -1.8, 1.4), 140.0, 2.5),
                                    ("Top", (0.0, -0.6, 3.2), 90.0, 2.0)):
        light = bpy.data.lights.new(name, 'AREA')
        light.energy = energy
        light.size = size
        ob = bpy.data.objects.new(name, light)
        sc.collection.objects.link(ob)
        ob.location = loc
        aim(ob, (0.0, 0.0, 0.5))
    cam = bpy.data.objects.new("PreviewCam", bpy.data.cameras.new("PreviewCam"))
    sc.collection.objects.link(cam)
    sc.camera = cam
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.25
    return cam


def render(cam, path, loc, target, lens=40.0, res=(1000, 750)):
    sc = bpy.context.scene
    cam.location = loc
    aim(cam, target)
    cam.data.lens = lens
    sc.cycles.samples = 48
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.image_settings.quality = 90
    sc.render.filepath = path
    t = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered", os.path.basename(path), "in %.1fs" % (time.time() - t))


# ---------------------------------------------------------------------------------- the chest of drawers

LEG_PROFILE = [(0.0, 0.0), (0.016, 0.0), (0.0175, 0.004), (0.019, 0.030), (0.021, 0.055), (0.025, 0.066),
               (0.026, 0.073), (0.024, 0.080), (0.0235, 0.097), (0.026, 0.100), (0.0, 0.100)]
KNOB_PROFILE = [(0.0, 0.0), (0.017, 0.0), (0.017, 0.0025), (0.013, 0.0045), (0.0065, 0.007), (0.006, 0.013),
                (0.009, 0.0165), (0.0135, 0.0215), (0.015, 0.026), (0.0135, 0.0305), (0.009, 0.0335),
                (0.0, 0.035)]


def arch_outline(half, height, foot, rise, radius, steps=8):
    """Plinth board seen from the front: full height at both ends (the feet), an arched gap between."""
    pts = [(-half, 0.0)]
    cx = half - foot - radius
    for i in range(steps + 1):            # left foot curving up into the apron
        a = math.pi - (math.pi / 2.0) * i / steps
        pts.append((-cx + radius * math.cos(a), rise * math.sin(a)))
    for i in range(steps + 1):            # right side curving back down
        a = (math.pi / 2.0) * (1.0 - i / steps)
        pts.append((cx + radius * math.cos(a), rise * math.sin(a)))
    pts += [(half, 0.0), (half, height), (-half, height)]
    return pts


def make_chest():
    reset_scene()
    random.seed(7)
    wood = wood_material("ChestWood")
    brass = brass_material()
    W, H = 0.92, 1.25
    xs = W / 2.0 - 0.022          # inner face of the side panels
    front = -0.24                 # front face of the carcass (Blender -Y is the front)
    frame = []           # carcass parts you see from outside
    hidden = []          # carcass parts nobody looks at closely (smaller share of the texture)

    frame.append(board("Top", wood, (0.0, -0.005, 1.235), (0.955, 0.50, 0.03), 'X', bev=0.007, segs=3))
    for s in (-1, 1):
        frame.append(board("Side", wood, (s * (W / 2.0 - 0.011), -0.005, 0.6475), (0.022, 0.47, 1.145), 'Z'))
    hidden.append(board("Back", wood, (0.0, 0.226, 0.6475), (2 * xs, 0.008, 1.145), 'Z', bev=0.001))
    frame.append(board("Bottom", wood, (0.0, -0.007, 0.095), (2 * xs, 0.466, 0.04), 'X'))
    for z0, z1 in ((0.415, 0.437), (0.707, 0.729), (0.973, 0.995), (1.195, 1.22)):
        frame.append(board("Rail", wood, (0.0, -0.007, (z0 + z1) / 2.0), (2 * xs, 0.466, z1 - z0), 'X'))
    frame.append(board("Muntin", wood, (0.0, -0.007, 1.095), (0.022, 0.466, 0.2), 'Z'))
    # plinth with little bracket feet
    frame.append(profile_board("PlinthFront", wood, arch_outline(0.47, 0.075, 0.085, 0.035, 0.035), 0.018,
                               (0.0, -0.241, 0.0), (1.0, 0.0, 0.0)))
    for s in (-1, 1):
        frame.append(profile_board("PlinthSide", wood, arch_outline(0.236, 0.075, 0.07, 0.03, 0.03), 0.018,
                                   (s * 0.461, 0.004, 0.0), (0.0, 1.0, 0.0)))
    hidden.append(board("PlinthBack", wood, (0.0, 0.231, 0.0375), (0.904, 0.018, 0.075), 'X'))

    rows = ((0.995, 1.195, ((-xs, -0.011), (0.011, xs))),   # two small drawers on top
            (0.729, 0.973, ((-xs, xs),)),
            (0.437, 0.707, ((-xs, xs),)),
            (0.115, 0.415, ((-xs, xs),)))
    drawers = []
    n = 0
    for z0, z1, spans in rows:
        for x0, x1 in spans:
            n += 1
            gap = 0.0025
            fw, fh = (x1 - x0) - 2 * gap, (z1 - z0) - 2 * gap
            cx, cz = (x0 + x1) / 2.0, (z0 + z1) / 2.0
            inset = 0.025 if fh < 0.22 else 0.03

            def raised_panel(bm, inset=inset):
                f = min(bm.faces, key=lambda face: face.normal.z)   # own -Z = world front
                bmesh.ops.inset_individual(bm, faces=[f], thickness=inset, depth=0.005, use_even_offset=True)

            parts = [board("D%dFront" % n, wood, (cx, front + 0.01, cz), (fw, 0.02, fh), 'X', hook=raised_panel)]
            bw, bh, bd = (x1 - x0) - 0.016, (z1 - z0) - 0.035, 0.40
            by0, bz0 = front + 0.02, z0 + 0.006
            box = []
            for s in (-1, 1):
                box.append(board("D%dSide" % n, wood, (cx + s * (bw / 2.0 - 0.006), by0 + bd / 2.0, bz0 + bh / 2.0),
                                 (0.012, bd, bh), 'Y', bev=0.0015))
            box.append(board("D%dBack" % n, wood, (cx, by0 + bd - 0.006, bz0 + bh / 2.0), (bw - 0.024, 0.012, bh),
                             'X', bev=0.0015))
            box.append(board("D%dBottom" % n, wood, (cx, by0 + (bd - 0.012) / 2.0, bz0 + 0.004),
                             (bw - 0.024, bd - 0.012, 0.008), 'X', bev=0.001))
            knob_x = (cx,) if fw < 0.6 else (cx - fw / 4.0, cx + fw / 4.0)
            knobs = [lathe("D%dKnob" % n, brass, KNOB_PROFILE, 'Y', 24, (kx, front - 0.005, cz)) for kx in knob_x]
            for k in knobs:
                k.rotation_euler = (0.0, random.uniform(0, 2 * math.pi), 0.0)
            drawers.append({"n": n, "front": parts, "box": box, "knobs": knobs, "center": (cx, front, cz)})

    boxes = [ob for d in drawers for ob in d["box"]]
    wood_objs = frame + hidden + [d["front"][0] for d in drawers] + boxes
    unwrap(wood_objs, shrink=hidden + boxes, shrink_factor=0.5)

    # a floor to darken the bottom, and the drawers pulled far out so each one only shades itself
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=5.0)
    floor = link_obj("BakeFloor", bm, [])
    for i, d in enumerate(drawers):
        off = Vector((1.3 * (i + 1), 0.0, 2.0))
        for ob in d["front"] + d["box"] + d["knobs"]:
            ob.location += off
    bpy.context.view_layer.update()
    albedo, normal, orm = bake_atlas(wood_objs, "chest", 2048, 1024, 1024, 1024, True, 0.85, (0.12, 0.06, 0.03))
    for i, d in enumerate(drawers):
        off = Vector((1.3 * (i + 1), 0.0, 2.0))
        for ob in d["front"] + d["box"] + d["knobs"]:
            ob.location -= off
    bpy.data.objects.remove(floor)

    final = baked_material("ChestWood", albedo, normal, orm)
    for ob in wood_objs:
        for slot in ob.material_slots:
            if slot.material == wood:
                slot.material = final

    frame_ob = join(frame + hidden, "Frame")
    export_objs = [frame_ob]
    total = tris(frame_ob)
    for d in drawers:
        n = d["n"]
        box_ob = join(d["front"] + d["box"], "Drawer%dBox" % n)
        knob_ob = join(d["knobs"], "Drawer%dKnob" % n)
        empty = bpy.data.objects.new("Drawer%d" % n, None)
        bpy.context.scene.collection.objects.link(empty)
        empty.location = d["center"]
        bpy.context.view_layer.update()
        for child in (box_ob, knob_ob):
            child.parent = empty
            child.matrix_parent_inverse = empty.matrix_world.inverted()
        export_objs += [empty, box_ob, knob_ob]
        total += tris(box_ob) + tris(knob_ob)
    INFO["chest_triangles"] = total
    log("chest triangles:", total)
    export(export_objs, "chest")

    cam = preview_stage(0.30)
    prev = os.path.join(OUT, "previews")
    os.makedirs(prev, exist_ok=True)
    render(cam, os.path.join(prev, "chest_front.jpg"), (1.35, -2.3, 1.45), (0.0, 0.0, 0.62))
    for name, dist in (("Drawer2", 0.28), ("Drawer4", 0.22)):
        bpy.data.objects[name].location.y -= dist
    render(cam, os.path.join(prev, "chest_open.jpg"), (1.0, -1.7, 1.75), (0.0, -0.1, 0.75))
    render(cam, os.path.join(prev, "chest_closeup.jpg"), (0.35, -0.75, 1.25), (0.05, -0.2, 1.0), lens=45.0)


# ---------------------------------------------------------------------------------- the sofa

def cushion(name, mat, size, loc, rot, puff_axis, puff_amount, bev, sag=0.0):
    ob = link_obj(name, bm_box(*size, cuts=3), [mat], loc, rot)
    bevel(ob, bev, 2)
    subsurf(ob, 1)
    apply_modifiers(ob)
    soft_shading(ob)
    hx, hy, hz = size[0] / 2.0, size[1] / 2.0, size[2] / 2.0
    puff(ob, puff_axis, puff_amount, (hx, hy, hz))
    if sag > 0.0:                      # worn dip in the middle of the top
        for v in ob.data.vertices:
            if v.co.z > 0.0:
                d = (v.co.x / (hx * 0.6)) ** 2 + ((v.co.y + hy * 0.1) / (hy * 0.65)) ** 2
                v.co.z -= sag * math.exp(-d) * (v.co.z / hz)
        ob.data.update()
    return ob


def upholstered(name, mat, size, loc, bev):
    ob = link_obj(name, bm_box(*size), [mat], loc)
    bevel(ob, bev, 3, limit='NONE')
    subsurf(ob, 1)
    apply_modifiers(ob)
    soft_shading(ob)
    return ob


def make_sofa():
    reset_scene()
    random.seed(3)
    fabric = fabric_material()
    legs_wood = wood_material("SofaWood", tone=0.6)
    parts = []
    for s in (-1, 1):
        parts.append(upholstered("Arm", fabric, (0.17, 0.80, 0.52), (s * 0.915, -0.03, 0.36), 0.05))
    parts.append(upholstered("Back", fabric, (2.0, 0.20, 0.76), (0.0, 0.33, 0.48), 0.06))
    parts.append(upholstered("Base", fabric, (1.66, 0.66, 0.22), (0.0, -0.10, 0.21), 0.03))
    w = (1.66 - 0.02) / 3.0
    for i in range(3):
        cx = -0.83 + 0.005 + w / 2.0 + i * (w + 0.005)
        jitter = (random.uniform(-0.01, 0.01), random.uniform(-0.01, 0.01), random.uniform(-0.015, 0.015))
        parts.append(cushion("Seat", fabric, (w, 0.60, 0.15), (cx, -0.13, 0.395), jitter, 'Z', 0.02, 0.045,
                             sag=random.uniform(0.012, 0.02)))
        tilt = (-0.17 + random.uniform(-0.03, 0.03), random.uniform(-0.01, 0.01), random.uniform(-0.02, 0.02))
        parts.append(cushion("BackCushion", fabric, (w, 0.17, 0.38), (cx, 0.13, 0.665), tilt, 'Y', 0.025, 0.05))
    for x in (-0.93, 0.93):
        for y in (-0.37, 0.37):
            parts.append(lathe("Leg", legs_wood, LEG_PROFILE, 'Z', 16, (x, y, 0.0)))

    unwrap(parts)
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=5.0)
    floor = link_obj("BakeFloor", bm, [])
    albedo, normal, _ = bake_atlas(parts, "sofa", 2048, 1024, 1024, 1024, False, 0.75, (0.12, 0.03, 0.025))
    bpy.data.objects.remove(floor)

    final = {fabric: baked_material("SofaFabric", albedo, normal, rough=0.9),
             legs_wood: baked_material("SofaLegs", albedo, normal, rough=0.45)}
    for ob in parts:
        for slot in ob.material_slots:
            slot.material = final.get(slot.material, slot.material)
    sofa = join(parts, "Sofa")
    INFO["sofa_triangles"] = tris(sofa)
    log("sofa triangles:", tris(sofa))
    export([sofa], "sofa")

    cam = preview_stage(0.47)
    prev = os.path.join(OUT, "previews")
    os.makedirs(prev, exist_ok=True)
    render(cam, os.path.join(prev, "sofa_front.jpg"), (1.9, -3.2, 1.5), (0.0, 0.0, 0.4))
    render(cam, os.path.join(prev, "sofa_closeup.jpg"), (0.75, -1.25, 0.95), (0.25, 0.0, 0.45), lens=45.0)


# ---------------------------------------------------------------------------------- main

log("Blender", bpy.app.version_string, "->", OUT)
os.makedirs(OUT, exist_ok=True)
make_chest()
make_sofa()
INFO["blender"] = bpy.app.version_string
with open(os.path.join(OUT, "info.json"), "w") as fh:
    json.dump(INFO, fh, indent=1)
log("done")
