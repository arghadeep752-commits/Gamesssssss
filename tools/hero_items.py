"""Chaya - the six ritual items, modelled in Blender in detail (used by tools/build_map.py).

    kalash    hammered-smooth brass pot with bead rings, kumkum dots, a red-and-yellow mauli thread round the neck,
              five curved mango leaves (with a folded midrib) and a husked coconut on top
    diya      hand-pressed clay lamp with a pinched spout, a pool of oil and a twisted cotton wick (burnt tip)
    coconut   husked brown coconut: three ridges, fibre grooves, a coir tuft, the three eyes, mauli and a kumkum tilak
              with rice grains
    kumkum    turned brass katori with a foot ring and bead bands, heaped with grainy kumkum powder
    kapoor    brass aarti plate with a scalloped rim and engraved rings, a pile of camphor tablets
    gangajal  hammered copper lota with a flared lip, water inside, mauli round the neck and kumkum dots

Every item is built at the origin (bottom centre, Blender z up) and joined into ONE mesh object with several
material slots, so the game sees the same node as before (item_<id>) - just far more detailed.
The diya also gets an empty "diya_flame_anchor" child at the wick tip (where the ritual lights the flame).
"""
import math
import random

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Vector

TAU = 2.0 * math.pi


class Kit:
    def __init__(self, get_material, collection, seed=11):
        self.mat = get_material
        self.col = collection
        self.rng = random.Random(seed)

    # ----------------------------------------------------------------------------------------------- mesh plumbing
    def mesh(self, name, V, F, UV, material, smooth=True, fix_normals=True):
        me = bpy.data.meshes.new(name)
        me.from_pydata([tuple(v) for v in V], [], [tuple(f) for f in F])
        me.update()
        uv = me.uv_layers.new(name="UVMap")
        if UV is not None and len(UV):
            vi = np.empty(len(me.loops), dtype=np.int64)
            me.loops.foreach_get("vertex_index", vi)
            uv.data.foreach_set("uv", np.asarray(UV, dtype=np.float32)[vi].reshape(-1))
        me.materials.append(self.mat(material))
        if fix_normals:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        me.polygons.foreach_set("use_smooth", np.full(len(me.polygons), smooth, dtype=np.bool_))
        me.validate()
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        return ob

    def revolve(self, name, prof, seg, material, rmod=None, disp=None, uv_scale=2.0, smooth=True):
        """Turned shape. prof = [(r, z), ...]; r = 0 points become poles. rmod(a, z) scales the radius,
        disp(a, z, r) adds metres along the radius (dents, fibres, spouts)."""
        S1 = seg + 1
        V, UV, rings = [], [], []
        acc = [0.0]
        for i in range(1, len(prof)):
            acc.append(acc[-1] + math.dist(prof[i - 1], prof[i]))
        rmax = max(r for r, _ in prof)
        for i, (r, z) in enumerate(prof):
            if r <= 1e-7:
                idx = len(V)
                V.append((0.0, 0.0, z))
                UV.append((0.5 * TAU * rmax * uv_scale, acc[i] * uv_scale))
                rings.append([idx] * S1)
                continue
            ring = []
            for k in range(S1):
                a = TAU * (k % seg) / seg
                rr = r * (rmod(a, z) if rmod else 1.0) + (disp(a, z, r) if disp else 0.0)
                ring.append(len(V))
                V.append((rr * math.cos(a), rr * math.sin(a), z))
                UV.append((k / seg * TAU * rmax * uv_scale, acc[i] * uv_scale))
            rings.append(ring)
        F = []
        for i in range(len(prof) - 1):
            A, B = rings[i], rings[i + 1]
            for k in range(seg):
                q = []
                for v in (A[k], A[k + 1], B[k + 1], B[k]):
                    if v not in q:
                        q.append(v)
                if len(q) >= 3:
                    F.append(q)
        return self.mesh(name, V, F, UV, material, smooth)

    def tube(self, name, pts, radius, material, sides=6, radii=None, twist=0.0, ripple=0.0):
        """Round strand along a polyline (threads, wick, coir fibres), parallel-transported frames."""
        pts = [Vector(p) for p in pts]
        n = len(pts)
        T = [(pts[min(i + 1, n - 1)] - pts[max(i - 1, 0)]).normalized() for i in range(n)]
        ref = Vector((0, 0, 1)) if abs(T[0].z) < 0.9 else Vector((1, 0, 0))
        N = T[0].cross(ref).normalized()
        V, UV, F = [], [], []
        acc = 0.0
        for i in range(n):
            if i:
                N = (N - T[i] * N.dot(T[i])).normalized()
                acc += (pts[i] - pts[i - 1]).length
            B = T[i].cross(N)
            r = radii[i] if radii else radius
            for k in range(sides + 1):
                a = TAU * k / sides + twist * acc
                rr = r * (1.0 + ripple * math.cos(2 * a))
                d = N * math.cos(a) + B * math.sin(a)
                V.append(pts[i] + d * rr)
                UV.append((k / sides, acc * 20.0))
        for i in range(n - 1):
            for k in range(sides):
                a0 = i * (sides + 1) + k
                F.append((a0, a0 + 1, a0 + sides + 2, a0 + sides + 1))
        c0 = len(V)                                      # close both ends with a centre vertex
        V.append(pts[0])
        UV.append((0.5, 0.0))
        c1 = len(V)
        V.append(pts[-1])
        UV.append((0.5, acc * 20.0))
        last = (n - 1) * (sides + 1)
        for k in range(sides):
            F.append((c0, k + 1, k))
            F.append((c1, last + k, last + k + 1))
        return self.mesh(name, V, F, UV, material, True)

    def ring(self, name, R, r, z, material, seg=96, sides=8, wobble=0.0, phase=0.0, center=(0.0, 0.0)):
        V, UV, F = [], [], []
        for i in range(seg + 1):
            a = TAU * (i % seg) / seg
            radial = Vector((math.cos(a), math.sin(a), 0.0))
            c = Vector((center[0], center[1], z + wobble * math.sin(3 * a + phase))) + radial * R
            for k in range(sides + 1):
                b = TAU * k / sides
                V.append(c + (radial * math.cos(b) + Vector((0, 0, 1)) * math.sin(b)) * r)
                UV.append((i / seg * 8.0, k / sides))
        for i in range(seg):
            for k in range(sides):
                a0 = i * (sides + 1) + k
                F.append((a0, a0 + sides + 1, a0 + sides + 2, a0 + 1))
        return self.mesh(name, V, F, UV, material, True)

    def blob(self, name, center, radii, material, normal=None, seg=16, rings=10, noise=0.0):
        """Small ellipsoid (dots, grains, eyes); z axis of the radii is turned onto `normal`."""
        V, F, UV = [], [], []
        for i in range(rings + 1):
            th = math.pi * i / rings
            for k in range(seg + 1):
                ph = TAU * (k % seg) / seg
                n = 1.0 + (noise * (self.rng.random() - 0.5) if 0 < i < rings else 0.0)
                V.append(Vector((radii[0] * math.sin(th) * math.cos(ph) * n, radii[1] * math.sin(th) * math.sin(ph) * n,
                                 radii[2] * math.cos(th))))
                UV.append((k / seg, i / rings))
        for i in range(rings):
            for k in range(seg):
                a0 = i * (seg + 1) + k
                F.append((a0, a0 + 1, a0 + seg + 2, a0 + seg + 1))
        rot = Matrix.Identity(3)
        if normal is not None:
            rot = Vector((0, 0, 1)).rotation_difference(Vector(normal).normalized()).to_matrix()
        c = Vector(center)
        V = [c + rot @ v for v in V]
        return self.mesh(name, V, F, UV, material, True)

    def rounded_box(self, name, size, loc, material, bevel=0.003, rot_z=0.0, tilt=(0.0, 0.0), lumpy=0.0):
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        ob = bpy.context.active_object
        ob.name = name
        ob.data.transform(Matrix.Diagonal((size[0], size[1], size[2], 1.0)))
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        self.col.objects.link(ob)
        ob.data.materials.clear()
        ob.data.materials.append(self.mat(material))
        m = ob.modifiers.new("bevel", "BEVEL")
        m.width = bevel
        m.segments = 3
        if lumpy > 0:
            tex = bpy.data.textures.new(name + "_lumps", "CLOUDS")
            tex.noise_scale = 0.004
            sub = ob.modifiers.new("sub", "SUBSURF")
            sub.levels = 1
            sub.render_levels = 1
            dm = ob.modifiers.new("lumps", "DISPLACE")
            dm.texture = tex
            dm.strength = lumpy
        ob.location = loc
        ob.rotation_euler = (tilt[0], tilt[1], rot_z)
        for p in ob.data.polygons:
            p.use_smooth = True
        return ob

    def leaf(self, name, base, azimuth, length, width, droop, material, nl=16, nw=4, lift=35.0):
        """Mango leaf: pointed lanceolate blade, the two halves folded up along the midrib, arching outward."""
        fwd = Vector((math.cos(azimuth), math.sin(azimuth), 0.0))
        side = Vector((-math.sin(azimuth), math.cos(azimuth), 0.0))
        up = Vector((0.0, 0.0, 1.0))
        centers, tans = [], []
        p = Vector(base)
        th0, th1 = math.radians(lift), math.radians(lift + droop)
        ds = length / nl
        for i in range(nl + 1):
            t = i / nl
            th = th0 + (th1 - th0) * t ** 1.4
            tan = fwd * math.sin(th) + up * math.cos(th)
            centers.append(p.copy())
            tans.append(tan)
            p = p + tan * ds
        V, UV, F = [], [], []
        for i in range(nl + 1):
            t = i / nl
            w = width * math.sin(math.pi * min(1.0, t ** 0.72)) ** 0.85 * (1.0 - 0.12 * t)
            w = max(w, 0.004 if t < 0.08 else 0.0)
            nrm = side.cross(tans[i]).normalized()
            for j in range(-nw, nw + 1):
                u = j / nw
                fold = 0.0045 * abs(u) * (1.0 - 0.6 * t) - 0.0025 * u * u * (1.0 - t)
                V.append(centers[i] + side * (u * w * 0.5) + nrm * fold)
                UV.append(((u + 1) * 0.5, t))
        cols = 2 * nw + 1
        for i in range(nl):
            for j in range(cols - 1):
                a0 = i * cols + j
                F.append((a0, a0 + 1, a0 + cols + 1, a0 + cols))
        return self.mesh(name, V, F, UV, material, True, fix_normals=False)

    def join(self, parts, name):
        parts = [p for p in parts if p is not None]
        bpy.ops.object.select_all(action="DESELECT")
        for p in parts:
            p.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.convert(target="MESH")
        bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = name
        ob.data.name = name
        me = ob.data
        bm = bmesh.new()                                 # weld the seams so smooth shading runs across them
        bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
        bm.to_mesh(me)
        bm.free()
        if hasattr(me, "use_auto_smooth"):
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.radians(48.0)
        return ob

    # ----------------------------------------------------------------------------------------------- details
    def mauli(self, name, radius_at, z0, turns=4, r=0.0019, tail=True):
        """Kalava / mauli: the red-and-yellow sacred thread, wound a few times and knotted."""
        parts = []
        for i in range(turns):
            z = z0 + (i - (turns - 1) / 2.0) * 0.0034
            R = radius_at(z) + r * 0.6
            parts.append(self.ring("%s_turn%d" % (name, i), R, r, z, "thread_red" if i % 2 == 0 else "thread_yellow",
                                   seg=96, sides=6, wobble=0.0008, phase=i))
        if tail:
            R = radius_at(z0) + r
            for j, (da, col) in enumerate(((0.06, "thread_red"), (-0.05, "thread_yellow"))):
                a = 0.3 + da
                pts = []
                for k in range(7):
                    t = k / 6
                    rr = R + 0.004 * math.sin(t * math.pi) + 0.002 * t
                    pts.append((rr * math.cos(a + 0.05 * t), rr * math.sin(a + 0.05 * t), z0 - 0.045 * t - 0.002 * j))
                parts.append(self.tube("%s_tail%d" % (name, j), pts, r * 0.9, col, sides=5))
            parts.append(self.blob(name + "_knot", (R * math.cos(0.3), R * math.sin(0.3), z0), (0.0035, 0.0035, 0.003), "thread_red",
                                   normal=(math.cos(0.3), math.sin(0.3), 0.0), seg=10, rings=6))
        return parts

    def dots(self, name, radius_at, z, angles, size=0.0075, material="kumkum_red"):
        parts = []
        for i, a in enumerate(angles):
            R = radius_at(z) + 0.0004
            parts.append(self.blob("%s_%d" % (name, i), (R * math.cos(a), R * math.sin(a), z), (size, size, size * 0.2), material,
                                   normal=(math.cos(a), math.sin(a), 0.0), seg=14, rings=6))
        return parts


def profile_radius(prof):
    """r(z) along the outer (rising) part of a lathe profile - for placing things on the surface."""
    imax = max(range(len(prof)), key=lambda i: prof[i][1])
    pts = []
    for r, z in prof[:imax + 1]:
        if pts and z <= pts[-1][1] + 1e-9:
            pts[-1] = (max(pts[-1][0], r), pts[-1][1])          # same height: keep the outermost
        else:
            pts.append((r, z))

    def f(z):
        for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
            if z0 <= z <= z1:
                return r0 + (r1 - r0) * (z - z0) / max(1e-9, z1 - z0)
        return pts[-1][0] if z > pts[-1][1] else pts[0][0]
    return f


def fibres(seed, n=7, kmin=22, kmax=64):
    """Long vertical grooves that wander a little - husk fibres running from crown to base."""
    r = random.Random(seed)
    comps = [(r.randint(kmin, kmax), r.uniform(0, TAU), r.uniform(0.4, 1.6), r.uniform(20.0, 60.0)) for _ in range(n)]

    def f(a, z):
        return sum(math.sin(k * a + p + w * math.sin(c * z)) for k, p, w, c in comps) / n
    return f


def wave(seed, n=6, fmin=2.0, fmax=9.0):
    """Smooth pseudo-noise on (a, z): a sum of random sinusoids (deterministic, no texture needed)."""
    r = random.Random(seed)
    comps = [(r.randint(int(fmin), int(fmax)), r.uniform(5.0, 40.0), r.uniform(0, TAU), r.uniform(0, TAU)) for _ in range(n)]

    def f(a, z):
        return sum(math.sin(k * a + p1) * math.sin(zf * z + p2) for k, zf, p1, p2 in comps) / n
    return f


# =============================================================================================== the items
def coconut_parts(kit, name, scale=1.0, tilak=True, thread=True):
    s = scale
    H, R = 0.2 * s, 0.083 * s
    ridge_phase = kit.rng.uniform(0, TAU)
    fib = fibres(31)
    lump = wave(32, 5, 2, 5)
    prof = []
    n = 34
    for i in range(n + 1):
        t = i / n
        th = math.pi * (1.0 - t)
        z = H * (0.5 - 0.5 * math.cos(math.pi * t ** 0.92))
        r = R * math.sin(th) ** 0.9 * (1.0 + 0.1 * (0.5 - abs(t - 0.45)))
        prof.append((r if 0 < i < n else 0.0, z))

    def disp(a, z, r):
        t = z / H
        ridge = 0.0045 * s * max(0.0, math.cos(3 * (a + ridge_phase))) ** 6 * math.sin(math.pi * t)
        return ridge + 0.0026 * s * fib(a, z / s) + 0.002 * s * lump(a, z * 8.0 / s)
    parts = [kit.revolve(name + "_husk", prof, 72, "coconut", disp=disp)]
    top = H
    for k in range(70):                                  # the coir tuft at the crown
        a = kit.rng.uniform(0, TAU)
        rr = kit.rng.uniform(0.0, 0.018 * s)
        h = kit.rng.uniform(0.022, 0.06) * s
        lean = kit.rng.uniform(0.15, 0.6)
        pts = []
        for j in range(6):
            t = j / 5
            out = rr + lean * h * t * t
            pts.append((out * math.cos(a + 0.4 * t), out * math.sin(a + 0.4 * t), top - 0.006 * s + h * t))
        parts.append(kit.tube("%s_coir%d" % (name, k), pts, kit.rng.uniform(0.0007, 0.0012) * s, "coir", sides=4,
                              radii=[0.0011 * s * (1.0 - 0.7 * j / 5) for j in range(6)]))
    for k in range(3):                                   # the three eyes, just below the tuft
        a = ridge_phase + TAU * k / 3 + math.pi / 3
        zz = H * 0.9
        rz = R * 0.42
        parts.append(kit.blob("%s_eye%d" % (name, k), (rz * math.cos(a), rz * math.sin(a), zz), (0.0065 * s, 0.0065 * s, 0.0025 * s),
                              "coconut_dark", normal=(math.cos(a) * 0.6, math.sin(a) * 0.6, 0.8), seg=12, rings=6))
    if thread:
        parts += kit.mauli(name + "_mauli", lambda z: R * 1.05 + 0.002 * s, H * 0.47, turns=3, r=0.0017 * s, tail=False)
    if tilak:
        a = ridge_phase + math.pi / 3
        zt = H * 0.62
        rt = R * 0.97
        parts.append(kit.blob(name + "_tilak", (rt * math.cos(a), rt * math.sin(a), zt), (0.011 * s, 0.006 * s, 0.0016 * s), "kumkum_red",
                              normal=(math.cos(a), math.sin(a), 0.25), seg=16, rings=6))
        for g in range(4):
            da = kit.rng.uniform(-0.08, 0.08)
            dz = kit.rng.uniform(-0.006, 0.006) * s
            parts.append(kit.blob("%s_rice%d" % (name, g), ((rt + 0.0018 * s) * math.cos(a + da), (rt + 0.0018 * s) * math.sin(a + da), zt + dz),
                                  (0.0012 * s, 0.0032 * s, 0.0012 * s), "rice", normal=(math.cos(a + da), math.sin(a + da), 0.2), seg=8, rings=5))
    return parts


def build_coconut(kit):
    return kit.join(coconut_parts(kit, "coconut"), "hero_coconut"), {}


def build_kalash(kit):
    prof = [(0.0, 0.0), (0.05, 0.0), (0.058, 0.002), (0.059, 0.006), (0.055, 0.011), (0.061, 0.016), (0.085, 0.032),
            (0.111, 0.06), (0.13, 0.098), (0.139, 0.138), (0.135, 0.178), (0.12, 0.212), (0.096, 0.238), (0.077, 0.256),
            (0.069, 0.266), (0.067, 0.276), (0.073, 0.286), (0.092, 0.297), (0.103, 0.303), (0.104, 0.308), (0.099, 0.311),
            (0.088, 0.307), (0.074, 0.297), (0.064, 0.285), (0.06, 0.27)]
    soft = wave(41, 6, 2, 6)
    parts = [kit.revolve("kalash_body", prof, 96, "brass", disp=lambda a, z, r: 0.0006 * soft(a, z * 20.0))]
    rad = profile_radius(prof)
    for z in (0.06, 0.098, 0.212):                                   # raised bead bands
        parts.append(kit.ring("kalash_band%.3f" % z, rad(z) + 0.0004, 0.0021, z, "brass", seg=96, sides=8))
    parts += kit.mauli("kalash_mauli", rad, 0.271, turns=4)
    parts += kit.dots("kalash_dot", rad, 0.15, [0.0, TAU / 3, 2 * TAU / 3])
    for k in range(5):                                               # mango leaves round the mouth
        az = TAU * k / 5 + 0.2
        base = (0.052 * math.cos(az), 0.052 * math.sin(az), 0.29)
        parts.append(kit.leaf("kalash_leaf%d" % k, base, az, kit.rng.uniform(0.15, 0.18), kit.rng.uniform(0.044, 0.052),
                              kit.rng.uniform(55.0, 75.0), "leaf_green"))
    nut = coconut_parts(kit, "kalash_nut", scale=0.82, tilak=True, thread=False)
    for p in nut:
        p.location = (0.0, 0.0, 0.272)
    parts += nut
    return kit.join(parts, "hero_kalash"), {}


def build_diya(kit):
    prof = [(0.0, 0.0), (0.03, 0.0), (0.035, 0.003), (0.033, 0.008), (0.048, 0.014), (0.066, 0.026), (0.078, 0.04),
            (0.083, 0.05), (0.083, 0.054), (0.079, 0.0565), (0.075, 0.053), (0.069, 0.043), (0.056, 0.031), (0.036, 0.023), (0.0, 0.02)]
    hand = wave(51, 6, 2, 7)

    def spout(a, z):
        g = math.exp(-((math.atan2(math.sin(a), math.cos(a))) / 0.42) ** 2)
        return 1.0 + 0.62 * g * max(0.0, min(1.0, (z - 0.006) / 0.045)) ** 1.3
    parts = [kit.revolve("diya_bowl", prof, 84, "clay", rmod=spout, disp=lambda a, z, r: 0.0007 * hand(a, z * 40.0))]
    oil_z = 0.038
    oprof = [(0.0, oil_z), (0.06, oil_z), (0.064, oil_z + 0.0005)]
    parts.append(kit.revolve("diya_oil", oprof, 84, "oil", rmod=lambda a, z: spout(a, z) * 0.985))
    # twisted cotton wick: lies in the oil, rises over the spout lip
    tip_x = 0.083 * spout(0.0, 0.054) - 0.004
    pts = [(0.0, 0.0, oil_z + 0.001)]
    for k in range(1, 11):
        t = k / 10
        x = tip_x * t
        z = oil_z + 0.0015 + 0.022 * max(0.0, (t - 0.55) / 0.45) ** 1.6
        pts.append((x, 0.002 * math.sin(t * 7.0), z))
    parts.append(kit.tube("diya_wick", pts, 0.0028, "wick_cotton", sides=6, twist=260.0, ripple=0.18,
                          radii=[0.0028 * (1.0 - 0.45 * (k / 10) ** 2) for k in range(11)]))
    tip = Vector(pts[-1])
    parts.append(kit.blob("diya_wick_tip", tip + Vector((0.0008, 0.0, 0.0012)), (0.0022, 0.0022, 0.0034), "wick", seg=10, rings=6))
    parts.append(kit.blob("diya_ember", tip + Vector((0.0012, 0.0, 0.003)), (0.0012, 0.0012, 0.0016), "wick_ember", seg=8, rings=5))
    for k in range(12):                                              # pressed dots round the rim
        a = TAU * k / 12 + math.pi / 12
        if abs(math.atan2(math.sin(a), math.cos(a))) < 0.7:
            continue
        r = 0.081 * spout(a, 0.05)
        parts.append(kit.blob("diya_dot%d" % k, (r * math.cos(a), r * math.sin(a), 0.047), (0.0028, 0.0028, 0.0012), "clay",
                              normal=(math.cos(a), math.sin(a), 0.0), seg=10, rings=5))
    ob = kit.join(parts, "hero_diya")
    return ob, {"diya_flame_anchor": tuple(tip + Vector((0.001, 0.0, 0.006)))}


def build_kumkum(kit):
    prof = [(0.0, 0.0), (0.03, 0.0), (0.034, 0.003), (0.032, 0.008), (0.04, 0.012), (0.056, 0.024), (0.067, 0.04),
            (0.072, 0.052), (0.0735, 0.0565), (0.0695, 0.058), (0.066, 0.0535), (0.06, 0.04), (0.046, 0.025), (0.026, 0.016), (0.0, 0.014)]
    parts = [kit.revolve("kumkum_bowl", prof, 96, "brass")]
    rad = profile_radius(prof)
    for z in (0.028, 0.046):
        parts.append(kit.ring("kumkum_band%.3f" % z, rad(z) + 0.0003, 0.0016, z, "brass", seg=96, sides=6))
    grain = wave(61, 8, 10, 30)
    fine = wave(62, 8, 30, 70)
    heap = []
    n = 22
    for i in range(n + 1):
        t = i / n                                                    # rim of the heap -> peak
        r = 0.0615 * (1.0 - t)
        z = 0.047 + 0.03 * (1.0 - (1.0 - t) ** 2) ** 0.85
        heap.append((r if i < n else 0.0, z))
    parts.append(kit.revolve("kumkum_powder", heap, 80, "kumkum_red",
                             disp=lambda a, z, r: 0.0011 * grain(a, z * 60.0) + 0.0006 * fine(a, z * 150.0)))
    return kit.join(parts, "hero_kumkum"), {}


def build_kapoor(kit):
    prof = [(0.0, 0.0), (0.06, 0.0), (0.065, 0.003), (0.062, 0.006), (0.09, 0.008), (0.132, 0.016), (0.148, 0.025),
            (0.155, 0.033), (0.153, 0.0365), (0.148, 0.0335), (0.132, 0.022), (0.09, 0.0158), (0.0, 0.015)]

    def scallop(a, z):
        return 1.0 + (0.03 * abs(math.cos(8 * a)) ** 0.6 - 0.015) * max(0.0, min(1.0, (z - 0.02) / 0.012))
    parts = [kit.revolve("kapoor_plate", prof, 128, "brass", rmod=scallop)]
    for R in (0.045, 0.098):                                         # engraved rings on the plate
        parts.append(kit.ring("kapoor_ring%.3f" % R, R, 0.0012, 0.0158, "brass", seg=96, sides=6))
    spots = [(0.0, 0.0, 0.0), (0.03, 0.006, 0.6), (-0.026, 0.018, 1.1), (0.008, -0.03, 2.0), (-0.012, -0.004, 0.3),
             (0.022, -0.024, 2.6), (-0.034, -0.022, 1.7)]
    for k, (x, y, rz) in enumerate(spots):
        stack = 1 if k == 4 else 0
        parts.append(kit.rounded_box("kapoor_tab%d" % k, (0.026, 0.026, 0.011), (x, y, 0.0215 + stack * 0.011),
                                     "camphor_white", bevel=0.0035, rot_z=rz, tilt=(kit.rng.uniform(-0.08, 0.08), kit.rng.uniform(-0.08, 0.08)),
                                     lumpy=0.0006))
    for k in range(9):                                               # crumbs
        a = kit.rng.uniform(0, TAU)
        d = kit.rng.uniform(0.04, 0.075)
        parts.append(kit.blob("kapoor_crumb%d" % k, (d * math.cos(a), d * math.sin(a), 0.0166), (0.0025, 0.002, 0.0015), "camphor_white",
                              seg=8, rings=5, noise=0.3))
    return kit.join(parts, "hero_kapoor"), {}


def build_gangajal(kit):
    prof = [(0.0, 0.0), (0.045, 0.0), (0.05, 0.004), (0.046, 0.008), (0.06, 0.015), (0.085, 0.035), (0.1, 0.065),
            (0.104, 0.095), (0.098, 0.125), (0.08, 0.15), (0.055, 0.17), (0.041, 0.184), (0.038, 0.199), (0.044, 0.211),
            (0.056, 0.222), (0.062, 0.228), (0.061, 0.232), (0.055, 0.23), (0.045, 0.222), (0.038, 0.206), (0.035, 0.19)]
    r_ = random.Random(71)
    dents = []
    for i in range(14):                                              # hammer marks on a jittered grid
        for j in range(9):
            dents.append(((i + 0.5 * (j % 2)) / 14 * TAU + r_.uniform(-0.08, 0.08), 0.022 + j * 0.016 + r_.uniform(-0.004, 0.004),
                          r_.uniform(0.7, 1.0)))

    def hammer(a, z, r):
        if z < 0.015 or z > 0.168:
            return 0.0
        d = 0.0
        for (da, dz, w) in dents:
            dd = math.atan2(math.sin(a - da), math.cos(a - da)) * r
            q = (dd * dd + (z - dz) ** 2) / (0.0085 ** 2)
            if q < 6.0:
                d -= 0.0011 * w * math.exp(-q)
        return d
    parts = [kit.revolve("lota_body", prof, 96, "copper", disp=hammer)]
    rad = profile_radius(prof)
    parts.append(kit.revolve("lota_water", [(0.0, 0.213), (0.0405, 0.213)], 64, "water"))
    parts += kit.mauli("lota_mauli", rad, 0.191, turns=3)
    parts += kit.dots("lota_dot", rad, 0.1, [0.4, 0.4 + TAU / 3, 0.4 + 2 * TAU / 3], size=0.0065)
    return kit.join(parts, "hero_gangajal"), {}


BUILDERS = {"kalash": build_kalash, "diya": build_diya, "coconut": build_coconut, "kumkum": build_kumkum,
            "kapoor": build_kapoor, "gangajal": build_gangajal}


def build_all(get_material, collection, ids):
    """-> {id: (object at the origin, {child_empty_name: local position})}"""
    kit = Kit(get_material, collection)
    out = {}
    for i in ids:
        fn = BUILDERS.get(i)
        if fn is None:
            continue
        before = set(bpy.data.objects)
        try:
            ob, extras = fn(kit)
        except Exception as ex:     # noqa: BLE001 - keep the simple item rather than lose the whole map
            import traceback
            traceback.print_exc()
            print("HERO ITEM %s FAILED: %s" % (i, ex))
            for o in [o for o in bpy.data.objects if o not in before]:
                bpy.data.objects.remove(o, do_unlink=True)
            continue
        tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
        print("hero item %-9s %6d triangles, materials %s" % (i, tris, [m.name for m in ob.data.materials]))
        out[i] = (ob, extras)
    return out
