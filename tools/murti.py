"""Hanuman ji's murti for the pooja ghar (called from tools/build_map.py).

In village shrines Hanuman ji is worshipped under thick layers of sindoor mixed in oil, so every detail of the stone
softens into one shining orange mass, with silver foil eyes, a silver mukut and a silver-capped gada. The murti is
modelled the same way: Veer Hanuman standing, the right hand raised in blessing, the gada over the left shoulder, the
tail rising behind him and curling over the mukut. Body, limbs, gada and tail are metaballs, so they fuse like coated
stone; a fine noise gives the uneven sindoor coat. Silver eyes with black pupils, a marigold mala, a lotus pedestal
and a geru-red shrine niche with a lime-plaster arch on the wall behind him complete it.

Coordinates: metres, the murti's own frame - origin on the top of the platform, +Z up, he faces -Y, the wall is +Y.
"""
import math

import bpy
import bmesh
from mathutils import Vector

THRESH = 0.6
FEET = 0.105                                     # the figure stands on a lotus pedestal this high
GADA = Vector((0.2, 0.034, 0.812))               # centre of the gada head (figure frame, feet at z = 0)
GADA_DIR = (GADA - Vector((0.146, -0.1, 0.53))).normalized()
MUKUT = [(0.0, 0.834), (0.069, 0.834), (0.074, 0.84), (0.071, 0.848), (0.074, 0.854), (0.068, 0.862), (0.062, 0.874),
         (0.066, 0.88), (0.058, 0.887), (0.052, 0.902), (0.056, 0.908), (0.048, 0.915), (0.042, 0.929), (0.046, 0.935),
         (0.038, 0.942), (0.031, 0.955), (0.035, 0.96), (0.027, 0.966), (0.019, 0.978), (0.023, 0.988), (0.017, 0.998),
         (0.008, 1.008), (0.012, 1.017), (0.0, 1.032)]
SLAB_Y = 0.112                                   # middle of the stone slab the figure is carved on


def _radius(v, stiff):
    """Element radius whose surface, alone, has radius v at the threshold (field = s * (1 - d^2 / r^2)^3)."""
    return v / math.sqrt(1.0 - (THRESH / stiff) ** (1.0 / 3.0))


class _Meta:
    def __init__(self, name, coll, res):
        self.mb = bpy.data.metaballs.new(name)
        self.mb.resolution = res
        self.mb.render_resolution = res
        self.mb.threshold = THRESH
        self.ob = bpy.data.objects.new(name, self.mb)
        coll.objects.link(self.ob)

    def _el(self, kind, co, v, stiff):
        e = self.mb.elements.new(type=kind)
        e.co = Vector(co)
        e.radius = _radius(v, stiff)
        e.stiffness = stiff
        return e

    def ball(self, co, v, stiff=3.0):
        return self._el("BALL", co, v, stiff)

    def ell(self, co, v, size, stiff=3.0):
        e = self._el("ELLIPSOID", co, v, stiff)
        e.size_x, e.size_y, e.size_z = size
        return e

    def cube(self, co, v, size, stiff=3.0):
        e = self._el("CUBE", co, v, stiff)
        e.size_x, e.size_y, e.size_z = size
        return e

    def cap(self, a, b, v, stiff=3.0):
        a, b = Vector(a), Vector(b)
        e = self._el("CAPSULE", (a + b) / 2, v, stiff)
        e.size_x = max((b - a).length / 2, 1e-4)
        e.rotation = Vector((1.0, 0.0, 0.0)).rotation_difference((b - a).normalized())
        return e

    def chain(self, pts, v0, v1, step=0.011, stiff=3.0):
        """Balls along a Catmull-Rom curve through pts, the radius going from v0 to v1."""
        P = [Vector(p) for p in pts]
        P = [P[0]] + P + [P[-1]]
        samples = []
        for i in range(1, len(P) - 2):
            p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
            for k in range(16):
                t = k / 16.0
                samples.append(0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
                                      + (3.0 * p1 - p0 - 3.0 * p2 + p3) * t * t * t))
        samples.append(P[-2])
        acc = [0.0]
        for a, b in zip(samples, samples[1:]):
            acc.append(acc[-1] + (b - a).length)
        n = max(2, int(acc[-1] / step))
        j = 0
        for k in range(n + 1):
            s = acc[-1] * k / n
            while j < len(acc) - 2 and acc[j + 1] < s:
                j += 1
            u = (s - acc[j]) / max(acc[j + 1] - acc[j], 1e-9)
            self.ball(samples[j].lerp(samples[j + 1], u), v0 + (v1 - v0) * k / n, stiff)


def _sculpt(M):
    """Veer Hanuman in high relief on an arched stone slab (figure frame: feet at z = 0, facing -Y, his left is +X)."""
    # the slab: a rounded upright block with an arched top - the figure fuses into it like carved, coated stone
    M.cube((0.0, SLAB_Y, 0.47), 0.032, (0.2, 0.004, 0.43))
    M.ell((0.0, SLAB_Y, 0.955), 0.232, (1.0, 0.15, 0.44))
    for s in (1.0, -1.0):
        M.ball((s * 0.076, -0.03, 0.236), 0.041)                                # knee
        M.cap((s * 0.076, -0.022, 0.23), (s * 0.08, -0.002, 0.075), 0.036)      # shin
        M.ell((s * 0.08, 0.012, 0.165), 0.037, (1.0, 1.1, 1.6))                 # calf
        M.ball((s * 0.08, -0.002, 0.058), 0.029)                                # ankle
        M.ell((s * 0.084, -0.036, 0.022), 0.032, (1.05, 1.9, 0.72))             # foot
        M.cap((s * 0.06, 0.0, 0.42), (s * 0.074, -0.024, 0.26), 0.05)           # thigh, under the dhoti
    M.ell((0.0, -0.006, 0.355), 0.098, (1.32, 0.74, 1.02))                      # dhoti from the waist to the knees
    M.ell((0.0, -0.068, 0.3), 0.034, (1.5, 0.34, 3.0))                          # its pleats hanging in front
    M.ell((0.0, -0.012, 0.458), 0.076, (1.16, 0.9, 0.22))                       # waistband
    M.ell((0.0, -0.012, 0.51), 0.066, (1.05, 0.85, 0.95))                       # belly
    M.ell((0.0, -0.006, 0.598), 0.09, (1.36, 0.74, 0.86))                       # chest
    for s in (1.0, -1.0):
        M.ell((s * 0.05, -0.04, 0.625), 0.046, (1.2, 0.58, 0.72))               # pectorals
        M.ball((s * 0.132, 0.0, 0.652), 0.05)                                   # shoulders
    M.ell((0.0, 0.02, 0.66), 0.064, (1.65, 0.8, 0.6))                           # upper back
    M.cap((0.0, 0.0, 0.67), (0.0, -0.008, 0.715), 0.043)                        # neck
    M.ball((0.0, 0.004, 0.782), 0.068)                                          # head
    M.ell((0.0, -0.058, 0.75), 0.047, (1.12, 0.9, 0.75))                        # muzzle
    M.ell((0.0, -0.047, 0.726), 0.04, (1.32, 0.9, 0.7))                         # the swollen jaw (hanu)
    for s in (1.0, -1.0):
        M.ball((s * 0.039, -0.042, 0.775), 0.032)                               # cheeks
        M.ell((s * 0.071, 0.0, 0.784), 0.022, (0.6, 1.0, 1.3))                  # ears
    M.ell((0.0, -0.054, 0.806), 0.027, (2.0, 0.7, 0.6))                         # brow
    M.ell((0.0, 0.004, 0.846), 0.063, (1.0, 1.0, 0.55))                         # top of the head, under the mukut
    # right arm raised in blessing, palm forward
    M.cap((-0.135, 0.0, 0.65), (-0.198, -0.014, 0.545), 0.04)
    M.ell((-0.165, -0.026, 0.6), 0.036, (1.0, 1.0, 1.35))                       # biceps
    M.ball((-0.198, -0.014, 0.545), 0.033)
    M.cap((-0.198, -0.014, 0.545), (-0.198, -0.074, 0.665), 0.032)
    M.ell((-0.198, -0.088, 0.705), 0.031, (1.0, 0.45, 1.5))                     # hand
    # left arm, the fist round the gada
    M.cap((0.135, 0.0, 0.65), (0.192, -0.002, 0.545), 0.04)
    M.ell((0.165, -0.022, 0.6), 0.036, (1.0, 1.0, 1.35))
    M.ball((0.192, -0.002, 0.545), 0.033)
    M.cap((0.192, -0.002, 0.545), (0.152, -0.074, 0.598), 0.032)
    M.ball((0.148, -0.086, 0.6), 0.035)
    # the gada: the handle through the fist, the head resting against the left shoulder
    M.cap((0.146, -0.1, 0.53), tuple(GADA - GADA_DIR * 0.05), 0.015, stiff=4.0)
    M.ell(tuple(GADA), 0.068, (1.0, 1.0, 1.12), stiff=4.0)
    M.ball(tuple(GADA + Vector((0.0, 0.0, 0.088))), 0.017)
    # the tail rising from behind his right hip along the slab, curling at the top
    M.chain([(-0.09, 0.05, 0.4), (-0.165, 0.058, 0.5), (-0.215, 0.056, 0.64), (-0.228, 0.052, 0.78), (-0.205, 0.048, 0.89),
             (-0.15, 0.046, 0.935), (-0.118, 0.046, 0.9), (-0.13, 0.046, 0.865)], 0.027, 0.015)
    # the base the feet stand in, coated with them
    M.ell((0.0, 0.02, -0.004), 0.17, (1.15, 0.9, 0.13))


def _bands(fig, coll, mat):
    """Silver armlets and bracelets round the coated arms."""
    def ring(name, a, b, t, r):
        a, b = Vector(a), Vector(b)
        c = a.lerp(b, t)
        me = bpy.data.meshes.new(name)
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=False, segments=14, radius1=r, radius2=r, depth=0.014)
        bm.to_mesh(me)
        bm.free()
        for p in me.polygons:
            p.use_smooth = True
        me.materials.append(mat("silver"))
        ob = bpy.data.objects.new(name, me)
        coll.objects.link(ob)
        ob.parent = fig
        ob.location = c
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Vector((0.0, 0.0, 1.0)).rotation_difference((b - a).normalized())
        sol = ob.modifiers.new("t", "SOLIDIFY")
        sol.thickness = 0.005
        sol.offset = 1.0
    for s in (1.0, -1.0):
        ring("murti_armlet", (s * 0.135, 0.0, 0.65), (s * (0.198 if s < 0 else 0.192), -0.014, 0.545), 0.46, 0.047)
    ring("murti_bracelet", (-0.198, -0.014, 0.545), (-0.198, -0.074, 0.665), 0.86, 0.035)
    ring("murti_bracelet", (0.192, -0.002, 0.545), (0.152, -0.074, 0.598), 0.8, 0.035)


def _is_silver(c):
    d = c - GADA
    if d.length < 0.084 and d.dot(GADA_DIR) > -0.062 and c.y < SLAB_Y - 0.032:
        return True
    return (c - (GADA + Vector((0.0, 0.0, 0.088)))).length < 0.032 and c.y < SLAB_Y - 0.03


def _apply_mods(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def _sphere(parent, coll, name, loc, scale, mat, seg=16, rings=10, rot=None):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    ob.location = loc
    ob.scale = scale
    if rot is not None:
        ob.rotation_euler = rot
    return ob


def _box(parent, coll, name, center, size, material, bevel=0.008):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * size[0], v.co.y * size[1], v.co.z * size[2]))
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=2, affect="EDGES")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(material)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    ob.location = center
    return ob


def _ray(ob, origin, direction):
    """Hit point and normal on ob (object space), or None."""
    ok, loc, nrm, _ = ob.ray_cast(Vector(origin), Vector(direction), distance=2.0)
    return (loc, nrm) if ok else None


def _tube(parent, coll, name, pts, radius, mat, cyclic=False, lumps=0.0, lump_scale=0.012):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.resolution_u = 6
    cu.bevel_depth = radius
    cu.bevel_resolution = 2
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for p, c in zip(sp.points, pts):
        p.co = (c[0], c[1], c[2], 1.0)
    sp.order_u = 4
    sp.use_cyclic_u = cyclic
    sp.use_endpoint_u = not cyclic
    co = bpy.data.objects.new(name + "_curve", cu)
    coll.objects.link(co)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(co.evaluated_get(dg))
    bpy.data.objects.remove(co)
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    ob.parent = parent
    if lumps > 0.0:
        tex = bpy.data.textures.new(name + "_lumps", "VORONOI")
        tex.noise_scale = lump_scale
        dis = ob.modifiers.new("lumps", "DISPLACE")
        dis.texture = tex
        dis.texture_coords = "LOCAL"
        dis.strength = lumps
        dis.mid_level = 0.5
        _apply_mods(ob)
    me = ob.data
    me.materials.clear()
    me.materials.append(mat)
    for p in me.polygons:
        p.use_smooth = True
    return ob


def build(root, coll, mat, lathe, res=0.0068, target_tris=11000):
    """Build the murti under the empty `root` (origin on the platform top). mat(name) -> material,
    lathe(parent, name, profile, loc, material_name) -> object. Returns the coated body (for the AO bake)."""
    fig = bpy.data.objects.new("murti_figure", None)
    coll.objects.link(fig)
    fig.parent = root
    fig.location = (0.0, 0.0, FEET)
    M = _Meta("murti_meta", coll, res)
    _sculpt(M)
    M.ob.parent = fig
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(M.ob.evaluated_get(dg))
    bpy.data.objects.remove(M.ob)
    body = bpy.data.objects.new("murti_body", me)
    coll.objects.link(body)
    body.parent = fig
    print("murti: metaball surface %d tris" % sum(len(p.vertices) - 2 for p in me.polygons))
    # the uneven coat of sindoor, then down to a phone budget
    tex = bpy.data.textures.new("sindoor_coat", "CLOUDS")
    tex.noise_scale = 0.022
    tex.noise_depth = 2
    dis = body.modifiers.new("coat", "DISPLACE")
    dis.texture = tex
    dis.texture_coords = "LOCAL"
    dis.strength = 0.0026
    dis.mid_level = 0.5
    drip = bpy.data.objects.new("murti_drip_space", None)          # stretches the second noise downwards: drips
    coll.objects.link(drip)
    drip.parent = fig
    drip.scale = (1.0, 1.0, 5.0)
    tex2 = bpy.data.textures.new("sindoor_drips", "CLOUDS")
    tex2.noise_scale = 0.012
    dis2 = body.modifiers.new("drips", "DISPLACE")
    dis2.texture = tex2
    dis2.texture_coords = "OBJECT"
    dis2.texture_coords_object = drip
    dis2.strength = 0.0022
    dis2.mid_level = 0.5
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    if tris > target_tris:
        dec = body.modifiers.new("dec", "DECIMATE")
        dec.ratio = target_tris / tris
    _apply_mods(body)
    bpy.data.objects.remove(drip)
    me = body.data
    # clean boundaries for the silver parts, the back of the slab (against the wall) dropped, then the two materials
    me.materials.clear()
    me.materials.append(mat("sindoor"))
    me.materials.append(mat("silver"))
    me.materials.append(mat("sindoor_old"))                      # the slab behind him: older, darker layers
    bm = bmesh.new()
    bm.from_mesh(me)
    back = [f for f in bm.faces if f.calc_center_median().y > SLAB_Y + 0.012 and f.normal.y > 0.55]
    bmesh.ops.delete(bm, geom=back, context="FACES")
    for co, no in ((tuple(GADA - GADA_DIR * 0.06), tuple(GADA_DIR)),):
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        bmesh.ops.bisect_plane(bm, geom=geom, plane_co=co, plane_no=no, dist=0.0005)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        c = f.calc_center_median()
        f.material_index = 1 if _is_silver(c) else (2 if c.y > SLAB_Y - 0.044 else 0)
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    print("murti body: %d tris" % len(me.polygons))
    bpy.context.view_layer.update()
    # big silver eyes with black pupils, set on the face where a ray from the front meets it
    for s in (1.0, -1.0):
        hit = _ray(body, (s * 0.027, -0.5, 0.796), (0.0, 1.0, 0.0))
        if hit is None:
            print("murti: eye ray missed")
            continue
        loc, nrm = hit
        nrm = (nrm + Vector((0.0, -1.5, 0.0))).normalized()
        _sphere(fig, coll, "murti_eye", loc + nrm * 0.002, (0.0205, 0.0075, 0.0128), mat("silver"), seg=18, rings=10,
                rot=(0.0, s * math.radians(14.0), 0.0))
        _sphere(fig, coll, "murti_pupil", loc + nrm * 0.0085, (0.0068, 0.003, 0.0068), mat("wick"), seg=12, rings=6)
    _bands(fig, coll, mat)
    # the silver mukut: a band with rims, four tiers and a kalash finial
    lathe(fig, "murti_mukut", MUKUT, (0.0, 0.004, 0.0), "silver")
    # marigold mala from shoulder to shoulder, hanging over the chest
    pts = []
    for k in range(15):
        a = -math.pi / 2 + math.pi * k / 14
        x, z = 0.085 * math.sin(a), 0.7 - 0.19 * math.cos(a)
        hit = _ray(body, (x, -0.5, z), (0.0, 1.0, 0.0))
        y = (hit[0].y if hit else -0.06) - 0.011
        pts.append((x, y, z))
    pts = [(0.1, pts[-1][1] + 0.03, 0.71)] + pts[::-1] + [(-0.1, pts[0][1] + 0.03, 0.71)]
    _tube(fig, coll, "murti_mala", pts, 0.0135, mat("marigold"), lumps=0.009, lump_scale=0.01)
    # the plinth the slab stands on, coated too
    _box(root, coll, "murti_plinth", (0.0, 0.07, 0.025), (0.6, 0.36, 0.05), mat("sindoor"))
    _box(root, coll, "murti_plinth", (0.0, 0.075, 0.0775), (0.53, 0.3, 0.055), mat("sindoor"))
    return body


def niche(root, coll, mat, wall_y, half_w=0.42, spring=1.06, base=0.0):
    """The shrine niche on the wall behind the murti: a geru-red arched panel framed by a lime-plaster moulding."""
    pts = []
    n = 18
    pts.append((half_w, base))
    pts.append((half_w, spring))
    for k in range(1, n):
        a = math.pi * k / n
        pts.append((half_w * math.cos(a), spring + half_w * math.sin(a) * 1.05))
    pts.append((-half_w, spring))
    pts.append((-half_w, base))
    me = bpy.data.meshes.new("murti_niche")
    bm = bmesh.new()
    vs = [bm.verts.new((x, wall_y - 0.004, z)) for (x, z) in pts]
    face = bm.faces.new(vs)
    face.normal_update()
    if face.normal.y > 0:
        face.normal_flip()
    uv = bm.loops.layers.uv.new("UVMap")
    for lp in face.loops:
        lp[uv].uv = (lp.vert.co.x / 2.4, lp.vert.co.z / 2.4)
    bmesh.ops.triangulate(bm, faces=[face])
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mat("geru"))
    ob = bpy.data.objects.new("murti_niche", me)
    coll.objects.link(ob)
    ob.parent = root
    frame = [(x * 1.07, wall_y - 0.03, base + (z - base) * 1.0 + (0.03 if z > spring else 0.0)) for (x, z) in pts]
    _tube(root, coll, "murti_niche_frame", frame, 0.032, mat("ext_plaster"))
    return ob
