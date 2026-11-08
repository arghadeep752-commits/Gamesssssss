"""Architecture: walls with openings (auto-trimmed at junctions), floors, ceilings, windows, sliding doors,
hinged doors, stairs and glass railings. All walls are axis-aligned."""
import math
import numpy as np
from hlib import Geo, DOORS, LIGHTS, emit, rotz, roty, round_path

CELL_WALL = 0.36
CELL_FLOOR = 0.36
CELL_CEIL = 0.6


def P(axis, s, w, z):
    return np.array((s, w, z), float) if axis == "x" else np.array((w, s, z), float)


def S(axis):
    return np.array((1.0, 0.0, 0.0)) if axis == "x" else np.array((0.0, 1.0, 0.0))


def W(axis):
    return np.array((0.0, 1.0, 0.0)) if axis == "x" else np.array((1.0, 0.0, 0.0))


def grid_facing(g, o, du, dv, want, mat, cell=None):
    o, du, dv = np.asarray(o, float), np.asarray(du, float), np.asarray(dv, float)
    if np.dot(np.cross(du, dv), want) < 0:
        o = o + du
        du = -du
    g.grid(o, du, dv, mat, cell)


def vrect(g, axis, w, a, b, c, d, sign, mat, cell=None):
    """Vertical rectangle on the plane w = const (s in [a, b], z in [c, d]) facing sign * W."""
    if b - a < 1e-5 or d - c < 1e-5:
        return
    grid_facing(g, P(axis, a, w, c), S(axis) * (b - a), (0, 0, d - c), W(axis) * sign, mat, cell)


def srect(g, axis, s, a, b, c, d, sign, mat, cell=None):
    """Vertical rectangle on the plane s = const (w in [a, b], z in [c, d]) facing sign * S."""
    if b - a < 1e-5 or d - c < 1e-5:
        return
    grid_facing(g, P(axis, s, a, c), W(axis) * (b - a), (0, 0, d - c), S(axis) * sign, mat, cell)


def hrect(g, axis, z, a, b, c, d, sign, mat, cell=None):
    """Horizontal rectangle at height z (s in [a, b], w in [c, d]) facing up (sign 1) or down (-1)."""
    if b - a < 1e-5 or d - c < 1e-5:
        return
    grid_facing(g, P(axis, a, c, z), S(axis) * (b - a), W(axis) * (d - c), (0, 0, sign), mat, cell)


def bands_of(c, d, bands):
    if isinstance(bands, str):
        return [(c, d, bands)]
    out, lo = [], c
    for zt, m in bands:
        hi = min(d, zt)
        if hi > lo + 1e-6:
            out.append((lo, hi, m))
        lo = max(lo, zt)
        if lo >= d - 1e-6:
            break
    if lo < d - 1e-6:
        out.append((lo, d, bands[-1][1]))
    return out


def floor(g, x0, y0, x1, y1, z, mat, cell=CELL_FLOOR):
    g.grid((x0, y0, z), (x1 - x0, 0, 0), (0, y1 - y0, 0), mat, cell)


def ceiling(g, x0, y0, x1, y1, z, mat, cell=CELL_CEIL):
    grid_facing(g, (x0, y0, z), (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, -1), mat, cell)


def rect_subtract(rect, holes):
    """Axis-aligned rectangle minus holes -> list of rectangles (x0, y0, x1, y1)."""
    x0, y0, x1, y1 = rect
    xs = sorted(set([x0, x1] + [min(max(h[0], x0), x1) for h in holes] + [min(max(h[2], x0), x1) for h in holes]))
    out = []
    for i in range(len(xs) - 1):
        a, b = xs[i], xs[i + 1]
        if b - a < 1e-6:
            continue
        m = (a + b) * 0.5
        cuts = sorted([(h[1], h[3]) for h in holes if h[0] < m < h[2]])
        lo = y0
        for c0, c1 in cuts:
            c0, c1 = max(c0, y0), min(c1, y1)
            if c0 > lo + 1e-6:
                out.append((a, lo, b, c0))
            lo = max(lo, c1)
        if y1 > lo + 1e-6:
            out.append((a, lo, b, y1))
    return out


# =====================================================================================  walls

class Wall:
    """Axis-aligned wall: s along the wall in [s0, s1], w across in [w0, w1], body z in [z0, z1].
    Side 0 is the w0 face (facing -W), side 1 the w1 face (facing +W). Each side has its own material
    (or vertical bands [(z_top, mat), ...]), height range, and optional skirting."""

    def __init__(self, axis, s0, s1, w0, w1, z0, z1, mat0, mat1, zr0=None, zr1=None, name="wall",
                 end_mat=None, top_mat=None, top=False, collide=True, skirt0=None, skirt1=None):
        self.axis, self.s0, self.s1, self.w0, self.w1, self.z0, self.z1 = axis, s0, s1, w0, w1, z0, z1
        self.mat = [mat0, mat1]
        self.zr = [zr0 or (z0, z1), zr1 or (z0, z1)]
        self.name = name
        self.end_mat = end_mat
        self.top_mat = top_mat
        self.top = top
        self.collide = collide
        self.skirt = [skirt0, skirt1]
        self.openings = []
        self.hide = [[], []]
        self.ends = [True, True]

    def opening(self, a, b, zb, zt, kind="window", reveal=None):
        self.openings.append(dict(a=a, b=b, zb=zb, zt=zt, kind=kind, reveal=reveal))
        return self

    def _intervals(self, a, b, hidden=()):
        cuts = {a, b}
        for o in self.openings:
            for v in (o["a"], o["b"]):
                if a < v < b:
                    cuts.add(v)
        for h0, h1 in hidden:
            for v in (h0, h1):
                if a < v < b:
                    cuts.add(v)
        cuts = sorted(cuts)
        out = []
        for i in range(len(cuts) - 1):
            sa, sb = cuts[i], cuts[i + 1]
            if sb - sa < 1e-6:
                continue
            m = (sa + sb) * 0.5
            if any(h0 - 1e-6 <= m <= h1 + 1e-6 for h0, h1 in hidden):
                continue
            op = next((o for o in self.openings if o["a"] < m < o["b"]), None)
            out.append((sa, sb, op))
        return out

    def build(self, g, cell=CELL_WALL):
        ax = self.axis
        for k in (0, 1):
            w = self.w0 if k == 0 else self.w1
            sign = -1 if k == 0 else 1
            zl, zh = self.zr[k]
            if zh - zl < 1e-6:
                continue
            for sa, sb, op in self._intervals(self.s0, self.s1, self.hide[k]):
                spans = [(zl, zh)] if op is None else [(zl, min(op["zb"], zh)), (max(op["zt"], zl), zh)]
                for c, d in spans:
                    for c2, d2, m in bands_of(c, d, self.mat[k]):
                        vrect(g, ax, w, sa, sb, c2, d2, sign, m, cell)
                # skirting along the visible wall at floor level
                sk = self.skirt[k]
                if sk is not None and (op is None or op["zb"] > zl + 0.1):
                    mat, h, t = sk
                    wf = w + sign * t
                    vrect(g, ax, wf, sa, sb, zl, zl + h, sign, mat)
                    hrect(g, ax, zl + h, sa, sb, min(w, wf), max(w, wf), 1, mat)
            # skirting end caps next to openings
            sk = self.skirt[k]
            if sk is not None:
                mat, h, t = sk
                lo, hi = (w - t, w) if k == 0 else (w, w + t)
                for o in self.openings:
                    if o["zb"] <= zl + 0.1:
                        if o["a"] > self.s0 + 1e-3:
                            srect(g, ax, o["a"], lo, hi, zl, zl + h, 1, mat)
                        if o["b"] < self.s1 - 1e-3:
                            srect(g, ax, o["b"], lo, hi, zl, zl + h, -1, mat)
        # reveals
        for o in self.openings:
            if o["kind"] in ("door", "none"):
                continue
            rm = o["reveal"] or (self.mat[1] if isinstance(self.mat[1], str) else self.mat[1][-1][1])
            srect(g, ax, o["a"], self.w0, self.w1, o["zb"], o["zt"], 1, rm)
            srect(g, ax, o["b"], self.w0, self.w1, o["zb"], o["zt"], -1, rm)
            if o["zt"] < self.z1 - 1e-4:
                hrect(g, ax, o["zt"], o["a"], o["b"], self.w0, self.w1, -1, rm)
            if o["zb"] > self.z0 + 1e-4:
                hrect(g, ax, o["zb"], o["a"], o["b"], self.w0, self.w1, 1, rm)
        em = self.end_mat or (self.mat[0] if isinstance(self.mat[0], str) else self.mat[0][-1][1])
        if self.ends[0]:
            for c, d, m in bands_of(self.z0, self.z1, self.mat[0] if self.end_mat is None else self.end_mat):
                srect(g, ax, self.s0, self.w0, self.w1, c, d, -1, m, cell)
        if self.ends[1]:
            for c, d, m in bands_of(self.z0, self.z1, self.mat[0] if self.end_mat is None else self.end_mat):
                srect(g, ax, self.s1, self.w0, self.w1, c, d, 1, m, cell)
        if self.top:
            hrect(g, ax, self.z1, self.s0, self.s1, self.w0, self.w1, 1, self.top_mat or em)
        if self.collide:
            for sa, sb, op in self._intervals(self.s0, self.s1):
                spans = [(self.z0, self.z1)] if op is None else [(self.z0, op["zb"]), (op["zt"], self.z1)]
                for c, d in spans:
                    if d - c > 0.02:
                        g.collide(np.minimum(P(ax, sa, self.w0, c), P(ax, sb, self.w1, d)),
                                  np.maximum(P(ax, sa, self.w0, c), P(ax, sb, self.w1, d)))


def resolve_junctions(walls):
    """Hides wall faces covered by abutting walls and drops end caps that butt into other walls."""
    eps = 1e-3
    for A in walls:
        for B in walls:
            if A is B:
                continue
            zlo, zhi = max(A.z0, B.z0), min(A.z1, B.z1)
            if zhi - zlo < 0.3 * (A.z1 - A.z0):
                continue
            if A.axis != B.axis:
                # B runs across A's thickness direction: does one of B's ends touch one of A's faces?
                for k, wa in ((0, A.w0), (1, A.w1)):
                    for end, sb in ((0, B.s0), (1, B.s1)):
                        if abs(sb - wa) < eps and B.w0 < A.s1 - eps and B.w1 > A.s0 + eps:
                            outward = (k == 1 and end == 0) or (k == 0 and end == 1)
                            if outward:
                                A.hide[k].append((max(B.w0, A.s0), min(B.w1, A.s1)))
                                B.ends[end] = False
            else:
                if abs(A.w0 - B.w0) < eps and abs(A.w1 - B.w1) < eps:
                    if abs(A.s1 - B.s0) < eps:
                        A.ends[1] = False
                        B.ends[0] = False
    # L-corners: an end of A lying inside B's footprint (B continues past A's end on its face)
    for A in walls:
        for end, sa in ((0, A.s0), (1, A.s1)):
            for B in walls:
                if B is A or B.axis == A.axis:
                    continue
                if B.s0 - eps <= A.w0 and A.w1 <= B.s1 + eps and B.w0 - eps <= sa <= B.w1 + eps:
                    if min(A.z1, B.z1) - max(A.z0, B.z0) > 0.3 * (A.z1 - A.z0):
                        A.ends[end] = False


def build_walls(g, walls, cell=CELL_WALL):
    resolve_junctions(walls)
    for w in walls:
        w.build(g, cell)


# =====================================================================================  windows

def window(wall, g, glass, a, b, zb, zt, M, outer=0, mullions=0, transom=None, sill=True, frame_depth=0.07,
           frame_w=0.055, board=True, reveal=None, open_panel=None, sliding=False):
    """Aluminium window in an opening of `wall`. outer = side (0/1) facing outside. Frames go in g, glass in
    `glass`. Sliding windows/doors get overlapping panels; open_panel leaves one panel slid open."""
    wall.opening(a, b, zb, zt, kind="window", reveal=reveal)
    ax = wall.axis
    wo = wall.w0 if outer == 0 else wall.w1
    inward = 1.0 if outer == 0 else -1.0
    wf = wo + inward * (0.06 + frame_depth * 0.5)           # frame centre plane
    fd, fw = frame_depth, frame_w
    frame = M["frame"]

    def bar(s0, s1, z0, z1, wc, depth):
        lo = np.minimum(P(ax, s0, wc - depth / 2, z0), P(ax, s1, wc + depth / 2, z1))
        hi = np.maximum(P(ax, s0, wc - depth / 2, z0), P(ax, s1, wc + depth / 2, z1))
        g.box(lo, hi, frame)

    def pane(s0, s1, z0, z1, wc):
        for side in (-1, 1):
            wv = wc + side * 0.004
            vrect(glass, ax, wv, s0, s1, z0, z1, side, M["glass"])

    # outer frame
    bar(a, b, zb, zb + fw, wf, fd)
    bar(a, b, zt - fw, zt, wf, fd)
    bar(a, a + fw, zb + fw, zt - fw, wf, fd)
    bar(b - fw, b, zb + fw, zt - fw, wf, fd)
    if sliding:
        n = max(2, mullions + 1)
        width = b - a - 2 * fw
        step = width / n
        lap = 0.04
        tracks = [wf - 0.018, wf + 0.018]
        sw = 0.045
        for i in range(n):
            s0 = a + fw + i * step - (lap * 0.5 if i > 0 else 0.0)
            s1 = a + fw + (i + 1) * step + (lap * 0.5 if i < n - 1 else 0.0)
            if open_panel is not None and i == open_panel:
                shift = -step if i > 0 else step
                s0 += shift
                s1 += shift
            track = tracks[i % 2]
            bar(s0, s1, zb + fw, zb + fw + sw, track, 0.03)
            bar(s0, s1, zt - fw - sw, zt - fw, track, 0.03)
            bar(s0, s0 + sw, zb + fw + sw, zt - fw - sw, track, 0.03)
            bar(s1 - sw, s1, zb + fw + sw, zt - fw - sw, track, 0.03)
            pane(s0 + sw, s1 - sw, zb + fw + sw, zt - fw - sw, track)
            hs = s1 - sw * 0.5 if i % 2 == 0 else s0 + sw * 0.5
            hz = zb + min(1.05, (zt - zb) * 0.5)
            for side in (-1, 1):
                c = P(ax, hs, track + side * 0.028, hz)
                g.rbox(c - np.array((0.008, 0.008, 0.07)), c + np.array((0.008, 0.008, 0.07)), 0.004, frame)
        spans = [(a, b)]
        if open_panel is not None:
            g0 = a + fw + open_panel * step
            spans = [(a, g0), (g0 + step, b)]
        for s0, s1 in spans:
            if s1 - s0 > 0.05:
                glass.collide(np.minimum(P(ax, s0, wf - 0.05, zb), P(ax, s1, wf + 0.05, zt)),
                              np.maximum(P(ax, s0, wf - 0.05, zb), P(ax, s1, wf + 0.05, zt)), layer=1)
    else:
        cols = [a + fw + (b - a - 2 * fw) * i / (mullions + 1) for i in range(mullions + 2)]
        rows = [zb + fw, zt - fw] if transom is None else [zb + fw, transom - fw * 0.4, transom + fw * 0.4, zt - fw]
        for i in range(1, mullions + 1):
            bar(cols[i] - fw * 0.4, cols[i] + fw * 0.4, zb + fw, zt - fw, wf, fd * 0.9)
        if transom is not None:
            bar(a + fw, b - fw, transom - fw * 0.4, transom + fw * 0.4, wf, fd * 0.9)
        for i in range(mullions + 1):
            s0 = cols[i] + (fw * 0.4 if i > 0 else 0.0)
            s1 = cols[i + 1] - (fw * 0.4 if i < mullions else 0.0)
            zs = [(rows[0], rows[1])] if transom is None else [(rows[0], rows[1]), (rows[2], rows[3])]
            for z0, z1 in zs:
                pane(s0, s1, z0, z1, wf)
        glass.collide(np.minimum(P(ax, a, wf - 0.05, zb), P(ax, b, wf + 0.05, zt)),
                      np.maximum(P(ax, a, wf - 0.05, zb), P(ax, b, wf + 0.05, zt)), layer=1)
    if sill and zb > wall.z0 + 0.05:
        # stone sill outside, timber/stone board inside
        so = wo - inward * 0.035
        si = wf - inward * fd * 0.5
        lo = np.minimum(P(ax, a - 0.03, so, zb - 0.03), P(ax, b + 0.03, si, zb + 0.004))
        hi = np.maximum(P(ax, a - 0.03, so, zb - 0.03), P(ax, b + 0.03, si, zb + 0.004))
        g.rbox(lo, hi, 0.006, M["sill"], seg=1)
        if board:
            wi = wall.w1 if outer == 0 else wall.w0
            bi0 = wf + inward * fd * 0.5
            bi1 = wi + inward * 0.025
            lo = np.minimum(P(ax, a - 0.02, bi0, zb - 0.01), P(ax, b + 0.02, bi1, zb + 0.02))
            hi = np.maximum(P(ax, a - 0.02, bi0, zb - 0.01), P(ax, b + 0.02, bi1, zb + 0.02))
            g.rbox(lo, hi, 0.005, M.get("board", M["sill"]), seg=1)


# =====================================================================================  doors

def door(wall, g, a, b, z, height, name, M, hinge="a", outside=1, leaf_mat=None, frame_mat=None,
         threshold=True, angle=95.0, grooves=True):
    """Hinged door in `wall`: frame and casings go in g, the leaf becomes its own moving object."""
    wall.opening(a, b, z, z + height, kind="door")
    ax = wall.axis
    w0, w1 = wall.w0, wall.w1
    wc = (w0 + w1) * 0.5
    fm = frame_mat or M["door_frame"]
    lm = leaf_mat or M["door_leaf"]
    t = 0.02
    # jamb liners
    for lo, hi in (((a, w0, z), (a + t, w1, z + height)), ((b - t, w0, z), (b, w1, z + height)),
                   ((a, w0, z + height - t), (b, w1, z + height))):
        g.box(np.minimum(P(ax, *lo), P(ax, *hi)), np.maximum(P(ax, *lo), P(ax, *hi)), fm, skip=())
    # casings on both faces
    cw, ct = 0.07, 0.016
    for wface, sign in ((w0, -1), (w1, 1)):
        wa, wb = (wface - ct, wface) if sign < 0 else (wface, wface + ct)
        for lo, hi in (((a - cw + 0.01, wa, z), (a + 0.01, wb, z + height + cw - 0.01)),
                       ((b - 0.01, wa, z), (b + cw - 0.01, wb, z + height + cw - 0.01)),
                       ((a + 0.01, wa, z + height - 0.01), (b - 0.01, wb, z + height + cw - 0.01))):
            g.rbox(np.minimum(P(ax, *lo), P(ax, *hi)), np.maximum(P(ax, *lo), P(ax, *hi)), 0.003, fm, seg=1, skip=("nz",))
    if threshold:
        lo, hi = P(ax, a, w0, z), P(ax, b, w1, z + 0.006)
        g.box(np.minimum(lo, hi), np.maximum(lo, hi), M["threshold"], skip=("nz",))
    # leaf (built in world space, around its hinge axis)
    gap = 0.004
    lt = 0.04
    if hinge == "a":
        sh = a + t + gap
        se = b - t - gap
        latch = S(ax)
    else:
        sh = b - t - gap
        se = a + t + gap
        latch = -S(ax)
    hinge_pos = P(ax, sh, wc, z)
    leaf = Geo()
    s_lo, s_hi = min(sh, se), max(sh, se)
    lo = np.minimum(P(ax, s_lo, wc - lt / 2, z + 0.008), P(ax, s_hi, wc + lt / 2, z + height - t - gap))
    hi = np.maximum(P(ax, s_lo, wc - lt / 2, z + 0.008), P(ax, s_hi, wc + lt / 2, z + height - t - gap))
    leaf.rbox(lo, hi, 0.004, lm, seg=1)
    if grooves:
        for zz in (z + 0.75, z + 1.45):
            for sgn in (-1, 1):
                wv = wc + sgn * (lt / 2 + 0.0006)
                lo = np.minimum(P(ax, s_lo + 0.06, wv - 0.0006, zz), P(ax, s_hi - 0.06, wv + 0.0006, zz + 0.006))
                hi = np.maximum(P(ax, s_lo + 0.06, wv - 0.0006, zz), P(ax, s_hi - 0.06, wv + 0.0006, zz + 0.006))
                leaf.box(lo, hi, M["groove"])
    # lever handles both sides
    hs = se - (0.065 if hinge == "a" else -0.065)
    hz = z + 1.02
    toward_hinge = -latch
    for sgn in (-1, 1):
        wface = wc + sgn * lt / 2
        nrm = W(ax) * sgn
        base = P(ax, hs, wface, hz)
        leaf.tube([base, base + nrm * 0.012], 0.026, M["handle"], seg=16)
        p0 = base + nrm * 0.012
        p1 = base + nrm * 0.055
        p2 = p1 + toward_hinge * 0.12
        leaf.tube(round_path([p0, p1, p2], 0.02, 4), 0.009, M["handle"], seg=10)
        # latch plate / key rose
        kr = base - np.array((0, 0, 0.11))
        leaf.tube([kr, kr + nrm * 0.008], 0.018, M["handle"], seg=12)
    emit(leaf, "Door " + name, "door:" + name, dynamic=True, origin=hinge_pos, collide=False)
    out_dir = W(ax) * (1 if outside > 0 else -1)
    DOORS.append(dict(name=name, obj="Door " + name, hinge=hinge_pos, latch=latch, outside=out_dir,
                      focus=P(ax, (a + b) * 0.5, wc, z + 1.1), width=abs(se - sh), height=height, angle=angle))


# =====================================================================================  stairs + railings

def straight_stair(g, x0, y0, y1, z0, rise, risers, tread, M, open_side="ny"):
    """Solid stair along +x starting with its first riser at x0, between y0 and y1, against a wall at y1.
    Returns the x of the last riser (top)."""
    rh = rise / risers
    width = y1 - y0
    nose = 0.025
    xt = x0 + (risers - 1) * tread
    for k in range(1, risers + 1):
        xa = x0 + (k - 1) * tread
        xb = xa + tread if k < risers else xa
        zt = z0 + k * rh
        # riser face
        g.grid((xa, y1, zt - rh), (0, -width, 0), (0, 0, rh), M["riser"])
        if k < risers:
            # tread board with nosing
            g.rbox((xa - nose, y0 - 0.01, zt - 0.035), (xb, y1, zt), 0.006, M["tread"], seg=1, skip=("py",))
            # open side of the solid base: stepped profile
            g.grid((xa, y0 - 0.0, z0), (tread, 0, 0), (0, 0, zt - 0.035 - z0), M["stair_side"], 0.4)
    # end face of the solid base below the top riser
    g.grid((xt, y0, z0), (0, width, 0), (0, 0, rise - rh), M["stair_side"], 0.4)
    # solid base colliders (stepped, kept below the walking ramp) and the walking ramp
    for k in range(1, risers):
        xa = x0 + (k - 1) * tread
        zt = z0 + k * rh
        g.collide((xa, y0, z0), (xa + tread, y1, max(z0 + 0.01, zt - 0.16)))
    run = (risers - 1) * tread + tread       # from one tread in front of the first riser to the top riser
    ang = math.degrees(math.atan2(rise, run))
    extra = 0.3                               # buried in the floor at the bottom, flush at the top
    length = math.hypot(run, rise) + extra
    thick = 0.25
    a = math.radians(ang)
    along = np.array((math.cos(a), 0.0, math.sin(a)))
    nrm = np.array((-math.sin(a), 0.0, math.cos(a)))
    c = np.array((x0 - tread + run * 0.5, (y0 + y1) * 0.5, z0 + rise * 0.5)) - along * extra * 0.5 - nrm * thick * 0.5
    g.collide_obb(c, (length, width, thick), roty(-ang))
    return xt


def glass_railing(g, glass, p0, p1, z_bottom0, z_bottom1, height, M, max_panel=1.2, top_clip=None, rail=True):
    """Frameless glass balustrade from p0 to p1 (xy), bottom heights may slope; top handrail."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    d = p1 - p0
    length = float(np.linalg.norm(d))
    if length < 0.05:
        return
    n = max(1, int(math.ceil(length / max_panel)))
    u = d / length
    nx = np.array((-u[1], u[0]))
    for i in range(n):
        t0 = i / n + (0.004 / length if i > 0 else 0.0)
        t1 = (i + 1) / n - (0.004 / length if i < n - 1 else 0.0)
        a, b = p0 + d * t0, p0 + d * t1
        za0 = z_bottom0 + (z_bottom1 - z_bottom0) * t0
        zb0 = z_bottom0 + (z_bottom1 - z_bottom0) * t1
        za1, zb1 = za0 + height - 0.04, zb0 + height - 0.04
        if top_clip is not None:
            za1, zb1 = min(za1, top_clip), min(zb1, top_clip)
        if za1 - za0 < 0.05 and zb1 - zb0 < 0.05:
            continue
        for side in (-1, 1):
            off = nx * 0.006 * side
            pts = [(a[0] + off[0], a[1] + off[1], za0 + 0.03), (b[0] + off[0], b[1] + off[1], zb0 + 0.03),
                   (b[0] + off[0], b[1] + off[1], zb1), (a[0] + off[0], a[1] + off[1], za1)]
            nn = np.array((nx[0] * side, nx[1] * side, 0.0))
            if np.dot(np.cross(np.subtract(pts[1], pts[0]), np.subtract(pts[3], pts[0])), nn) < 0:
                pts.reverse()
            glass.face(pts, M["glass_rail"])
        # floor clamps
        for t in (0.2, 0.8):
            c = a + (b - a) * t
            zc = za0 + (zb0 - za0) * t
            g.rbox((c[0] - 0.04 * abs(u[0]) - 0.012 * abs(nx[0]), c[1] - 0.04 * abs(u[1]) - 0.012 * abs(nx[1]), zc),
                   (c[0] + 0.04 * abs(u[0]) + 0.012 * abs(nx[0]), c[1] + 0.04 * abs(u[1]) + 0.012 * abs(nx[1]), zc + 0.06),
                   0.004, M["steel"], seg=1)
    if rail:
        k = max(2, n * 2)
        pts = [(p0[0] + d[0] * i / k, p0[1] + d[1] * i / k,
                z_bottom0 + (z_bottom1 - z_bottom0) * i / k + height) for i in range(k + 1)]
        if top_clip is not None:
            pts = [p for p in pts if p[2] <= top_clip + 1e-6]
        if len(pts) >= 2:
            g.tube(pts, 0.022, M["rail"], seg=12)
    # collider (layer 1: the enemy can see through glass)
    zlo = min(z_bottom0, z_bottom1)
    zhi = max(z_bottom0, z_bottom1) + height
    mid = (p0 + p1) * 0.5
    if abs(z_bottom1 - z_bottom0) < 1e-3:
        yaw = math.degrees(math.atan2(u[1], u[0]))
        glass.collide_obb((mid[0], mid[1], (zlo + zhi) * 0.5), (length, 0.06, zhi - zlo), rotz(yaw), layer=1)
    else:
        ang = math.degrees(math.atan2(z_bottom1 - z_bottom0, length))
        yaw = math.degrees(math.atan2(u[1], u[0]))
        R = rotz(yaw) @ roty(-ang)
        hl = math.hypot(length, z_bottom1 - z_bottom0)
        c = np.array((mid[0], mid[1], (z_bottom0 + z_bottom1) * 0.5 + height * 0.5))
        glass.collide_obb(c, (hl, 0.06, height), R, layer=1)


def downlight(g, x, y, zc, M, power=14.0, color=(1.0, 0.86, 0.68), light=True):
    g.cyl((x, y, zc - 0.006), 0.055, 0.006, M["trim_white"], seg=16, bottom=False, top=False)
    g.face([(x + 0.045 * math.cos(t), y + 0.045 * math.sin(t), zc - 0.0075) for t in
            [2 * math.pi * i / 16 for i in reversed(range(16))]], M["lamp"])
    g.face([(x + 0.055 * math.cos(t), y + 0.055 * math.sin(t), zc - 0.006) for t in
            [2 * math.pi * i / 16 for i in reversed(range(16))]], M["trim_white"])
    if light:
        LIGHTS.append(dict(pos=(x, y, zc - 0.08), color=color, power=power, radius=0.04, kind="spot", spot=110.0))
