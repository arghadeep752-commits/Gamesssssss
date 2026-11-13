"""Ragini's body, sculpted as signed distance fields (see tools/common/sdf.py) - numpy only.

A gaunt, tall woman (1.72 m) in an A-pose: sunken eyes, hollow cheeks, a jaw dropped open in a scream, long
bony fingers with long nails, and the chudail's feet turned backwards. The right hand is closed in a grip
around her wooden scale; the left hand is a claw.

Blender axes: +X is her left, -Y is in front of her, +Z is up. Units: metres.
Every shape names the bone it moves with; tools/common/sdf.bone_weights() turns that into skin weights.
"""
import math

import numpy as np

from sdf import Shape, frame

V3 = lambda *a: np.array(a, float)      # noqa: E731


def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _rodrigues(axis, ang):
    a = _n(axis)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


class Body:
    def __init__(self):
        self.shapes = []          # body skin
        self.teeth = []
        self.eyes = []
        self.bones = {}           # name -> (head, tail, parent)
        self.marks = {}           # named points used by textures, garments and props

    # -------------------------------------------------------------------- helpers
    def cone(self, a, b, r1, r2, bone, k=0.02, op="add", tag="", group=None):
        s = Shape("cone", op=op, k=k, bone=bone, tag=tag, a=a, b=b, r1=r1, r2=r2)
        (self.teeth if group == "teeth" else self.shapes).append(s)
        return s

    def ell(self, c, r, bone, k=0.02, R=None, op="add", tag="", group=None):
        s = Shape("ell", op=op, k=k, bone=bone, tag=tag, c=c, r=r, R=np.eye(3) if R is None else R)
        (self.teeth if group == "teeth" else self.shapes).append(s)
        return s

    def sph(self, c, r, bone, k=0.01, op="add", tag=""):
        s = Shape("sphere", op=op, k=k, bone=bone, tag=tag, c=c, r=r)
        self.shapes.append(s)
        return s

    def box(self, c, h, R, rad, bone, k=0.01, op="add", tag=""):
        s = Shape("box", op=op, k=k, bone=bone, tag=tag, c=c, h=h, R=R, rad=rad)
        self.shapes.append(s)
        return s

    def bone(self, name, head, tail, parent=None):
        self.bones[name] = (np.asarray(head, float), np.asarray(tail, float), parent)


def build():
    b = Body()
    S = 1.0
    # ============================================================== skeleton (rest pose)
    hips_c = V3(0, 0.0, 0.93)
    b.bone("root", V3(0, 0, 0), V3(0, 0.0, 0.12))
    b.bone("hips", hips_c, V3(0, 0.005, 1.03), "root")
    b.bone("spine", V3(0, 0.005, 1.03), V3(0, 0.014, 1.17), "hips")
    b.bone("chest", V3(0, 0.014, 1.17), V3(0, 0.024, 1.395), "spine")
    b.bone("neck", V3(0, 0.026, 1.40), V3(0, 0.014, 1.525), "chest")
    b.bone("head", V3(0, 0.014, 1.525), V3(0, 0.014, 1.72), "neck")
    b.bone("jaw", V3(0, 0.004, 1.562), V3(0, -0.066, 1.468), "head")

    arms = {}
    for side, s in (("L", 1.0), ("R", -1.0)):
        sh = V3(s * 0.165, 0.024, 1.386)
        d1 = _n([s * 0.64, -0.10, -0.76])
        d2 = _n([s * 0.60, -0.22, -0.77])
        el = sh + 0.292 * d1
        wr = el + 0.255 * d2
        dh = _n(d2 + V3(s * 0.05, -0.02, -0.08))
        tip = wr + 0.20 * dh
        b.bone("clavicle." + side, V3(s * 0.02, 0.004, 1.405), sh + V3(-s * 0.005, 0, 0.004), "chest")
        b.bone("upper_arm." + side, sh, el, "clavicle." + side)
        b.bone("forearm." + side, el, wr, "upper_arm." + side)
        b.bone("hand." + side, wr, tip, "forearm." + side)
        arms[side] = (sh, el, wr, d1, d2, dh)
        hp = V3(s * 0.088, 0.0, 0.905)
        kn = V3(s * 0.087, -0.010, 0.488)
        an = V3(s * 0.084, 0.020, 0.080)
        b.bone("thigh." + side, hp, kn, "hips")
        b.bone("shin." + side, kn, an, "thigh." + side)
        b.bone("foot." + side, an, an + V3(0, 0.150, -0.055), "shin." + side)     # backwards feet: toes behind her
        b.marks["ankle." + side] = an
        b.marks["knee." + side] = kn
        b.marks["wrist." + side] = wr
        b.marks["elbow." + side] = el
        b.marks["shoulder." + side] = sh

    # ============================================================== torso
    b.ell(V3(0, 0.006, 0.915), V3(0.143, 0.097, 0.100), "hips", k=0.05)
    for s in (1, -1):
        b.ell(V3(s * 0.062, 0.047, 0.874), V3(0.071, 0.060, 0.086), "hips", k=0.045)
    b.ell(V3(0, -0.012, 0.985), V3(0.118, 0.080, 0.074), "hips", k=0.05)
    b.ell(V3(0, 0.004, 1.062), V3(0.100, 0.072, 0.090), "spine", k=0.05)
    b.ell(V3(0, 0.014, 1.215), V3(0.116, 0.087, 0.145), "chest", k=0.05, R=frame([0, 0.12, 1.0], [0, -1, 0]))
    b.ell(V3(0, 0.002, 1.322), V3(0.124, 0.072, 0.072), "chest", k=0.045)
    b.ell(V3(0, 0.012, 1.372), V3(0.090, 0.058, 0.045), "chest", k=0.04)            # base of the neck
    for s in (1, -1):
        b.ell(V3(s * 0.057, -0.058, 1.246), V3(0.050, 0.043, 0.047), "chest", k=0.035)    # breasts (under the blouse)
        b.ell(V3(s * 0.070, 0.060, 1.305), V3(0.048, 0.024, 0.070), "chest", k=0.035)     # shoulder blades
        b.cone(V3(s * 0.024, 0.040, 1.452), V3(s * 0.138, 0.030, 1.404), 0.034, 0.028, "chest", k=0.03)   # trapezius
        b.cone(V3(s * 0.017, -0.034, 1.386), V3(s * 0.148, 0.000, 1.402), 0.0085, 0.0105, "chest", k=0.016, tag="clavicle")
        b.ell(V3(s * 0.172, 0.020, 1.368), V3(0.047, 0.049, 0.062), "upper_arm." + ("L" if s > 0 else "R"), k=0.03,
              R=frame([s * 0.5, 0, -1], [0, -1, 0]))                                      # deltoid
    # blouse: short sleeves and a hem standing a few millimetres off the skin
    for side, s in (("L", 1.0), ("R", -1.0)):
        sh_, el_ = b.bones["upper_arm." + side][0], b.bones["upper_arm." + side][1]
        b.cone(sh_ + (el_ - sh_) * 0.05, sh_ + (el_ - sh_) * 0.42, 0.046, 0.0345, "upper_arm." + side, k=0.006, tag="sleeve")
        b.marks["sleeve_end." + side] = sh_ + (el_ - sh_) * 0.42
    b.ell(V3(0, 0.004, 1.235), V3(0.121, 0.092, 0.072), "chest", k=0.008, tag="blouse")
    b.marks["blouse_bottom"] = 1.168
    # gaunt: the belly falls in under the ribs
    b.ell(V3(0, -0.098, 1.105), V3(0.070, 0.026, 0.050), "spine", k=0.035, op="sub")

    # ============================================================== neck
    b.cone(V3(0, 0.030, 1.392), V3(0, 0.024, 1.530), 0.046, 0.0355, "neck", k=0.022)
    for s in (1, -1):
        b.cone(V3(s * 0.046, 0.026, 1.552), V3(s * 0.012, -0.036, 1.410), 0.0098, 0.0085, "neck", k=0.012, tag="scm")
    b.ell(V3(0, -0.030, 1.465), V3(0.012, 0.010, 0.016), "neck", k=0.012)                # larynx

    # ============================================================== arms and hands
    for side, s in (("L", 1.0), ("R", -1.0)):
        sh, el, wr, d1, d2, dh = arms[side]
        ua, fa, hd = "upper_arm." + side, "forearm." + side, "hand." + side
        b.cone(sh, el, 0.040, 0.0285, ua, k=0.02)
        Rf1 = frame(d1, [0, -1, 0])
        b.ell(sh + 0.46 * (el - sh) + Rf1[:, 1] * 0.006, V3(0.029, 0.031, 0.085), ua, k=0.02, R=Rf1)       # biceps
        b.ell(sh + 0.40 * (el - sh) - Rf1[:, 1] * 0.010, V3(0.030, 0.028, 0.092), ua, k=0.02, R=Rf1)       # triceps
        b.sph(el - Rf1[:, 1] * 0.012, 0.022, fa, k=0.015)                                                    # elbow
        b.cone(el, wr, 0.030, 0.0205, fa, k=0.02)
        Rf2 = frame(d2, [0, -1, 0])
        b.ell(el + 0.28 * (wr - el) + Rf2[:, 0] * s * 0.004, V3(0.033, 0.027, 0.075), fa, k=0.022, R=Rf2)
        b.ell(wr, V3(0.021, 0.0145, 0.016), fa, k=0.014, R=frame(dh, [0, -1, 0]))
        # --- hand frame: f = along the hand, pn = out of the palm, t = towards the thumb
        f = dh
        pn = _n(np.cross(f, V3(0, -1, 0)) * s)               # palm faces her thigh
        pn = _n(pn - f * float(pn @ f))
        if pn[0] * s > 0:
            pn = -pn
        t = _n(np.cross(pn, f))
        if t[1] > 0:
            t = -t                                            # thumb in front
        b.marks["palm_n." + side] = pn
        b.marks["hand_t." + side] = t
        b.marks["hand_f." + side] = f
        Rh = np.stack([t, -pn, f], axis=1)
        b.box(wr + f * 0.047 - pn * 0.002, V3(0.036, 0.012, 0.043), Rh, 0.011, hd, k=0.014)                # palm
        b.ell(wr + f * 0.030 + t * 0.022 + pn * 0.008, V3(0.018, 0.014, 0.026), hd, k=0.012, R=Rh)         # thumb pad
        b.ell(wr + f * 0.038 - t * 0.026 + pn * 0.006, V3(0.012, 0.011, 0.03), hd, k=0.012, R=Rh)          # pinky pad
        grip = side == "R"
        # fingers: offset across the knuckles, segment lengths, curl angles (degrees) for claw / grip
        fingers = [(0.025, (0.048, 0.029, 0.025), 0.0086),
                   (0.008, (0.053, 0.033, 0.027), 0.0088),
                   (-0.009, (0.050, 0.031, 0.026), 0.0083),
                   (-0.025, (0.040, 0.025, 0.023), 0.0074)]
        curl = [(78, 95, 62), (82, 98, 60), (84, 96, 58), (86, 92, 56)] if grip else \
               [(22, 48, 38), (18, 52, 40), (20, 50, 42), (26, 46, 40)]
        spread = [7, 1, -5, -11] if not grip else [2, 0, -2, -4]
        tips = []
        for fi, ((off, segs, r0), cu, sp) in enumerate(zip(fingers, curl, spread)):
            p = wr + f * (0.091 - abs(off) * 0.25) + t * off - pn * 0.001
            d = _rodrigues(pn, math.radians(sp * (1 if side == "L" else 1))) @ f
            r = r0
            for si, L in enumerate(segs):
                d = _rodrigues(t, -math.radians(cu[si])) @ d * 1.0
                d = _n(d)
                q = p + d * L
                b.cone(p, q, r, r * 0.88, hd, k=0.006)
                if si < 2:
                    b.sph(q, r * 0.95, hd, k=0.004)            # knuckle
                p = q
                r *= 0.88
            # long dark nail growing past the fingertip, bending down a little
            nd = _n(d + (_rodrigues(t, -math.radians(25)) @ d) * 0.4)
            b.ell(p + nd * 0.009 + np.cross(t, d) * 0.0015, V3(0.0042, 0.0016, 0.012), hd, k=0.003,
                  R=np.stack([t, _n(np.cross(nd, t)), nd], axis=1), tag="nail")
            tips.append((p, d))
        # thumb
        tb = wr + f * 0.022 + t * 0.030 + pn * 0.004
        td = _n(f * 0.55 + t * 0.62 + pn * (0.45 if grip else 0.25))
        r = 0.0108
        p = tb
        for si, L in enumerate((0.042, 0.032, 0.027)):
            ang = (35, 40, 30)[si] if grip else (8, 22, 18)[si]
            td = _n(_rodrigues(f, math.radians(ang) * (1 if side == "L" else -1)) @ td)
            q = p + td * L
            b.cone(p, q, r, r * 0.88, hd, k=0.008)
            p = q
            r *= 0.88
        b.ell(p + td * 0.008, V3(0.0052, 0.0018, 0.011), hd, k=0.003,
              R=np.stack([_n(np.cross(td, pn)), pn, td], axis=1), tag="nail")
        tips.append((p, td))
        b.marks["fingertips." + side] = tips
        if grip:
            # the scale passes through the fist along the thumb axis
            b.marks["grip_c"] = wr + f * 0.075 + pn * 0.024 + t * 0.002
            b.marks["grip_axis"] = _n(t * 0.95 - f * 0.25)
            b.marks["grip_up"] = pn

    # ============================================================== legs and backward feet
    for side, s in (("L", 1.0), ("R", -1.0)):
        hp, kn = b.bones["thigh." + side][0], b.bones["thigh." + side][1]
        an = b.bones["shin." + side][1]
        th, sn, ft = "thigh." + side, "shin." + side, "foot." + side
        b.cone(hp, kn, 0.077, 0.043, th, k=0.03)
        b.ell(hp + 0.28 * (kn - hp) + V3(s * 0.006, 0.004, 0), V3(0.062, 0.064, 0.13), th, k=0.04)
        b.ell(hp + 0.56 * (kn - hp) + V3(0, -0.018, 0), V3(0.045, 0.040, 0.12), th, k=0.03)
        b.ell(hp + 0.40 * (kn - hp) + V3(-s * 0.026, 0.004, 0), V3(0.042, 0.050, 0.11), th, k=0.03)
        b.ell(kn + V3(0, -0.033, 0.012), V3(0.025, 0.015, 0.029), sn, k=0.014)
        b.cone(kn, an, 0.042, 0.0255, sn, k=0.03)
        b.ell(kn + 0.30 * (an - kn) + V3(-s * 0.004, 0.026, 0), V3(0.043, 0.040, 0.105), sn, k=0.03)
        for m in (1, -1):
            b.sph(an + V3(m * 0.021, 0.0, -0.004), 0.0115, sn, k=0.012)
        # a normal foot turned 180 degrees about the ankle: heel in front (-Y), toes behind (+Y)
        b.ell(an + V3(0, -0.040, -0.048), V3(0.028, 0.034, 0.030), ft, k=0.02)                        # heel
        ball = an + V3(-s * 0.004, 0.118, -0.064)
        b.cone(an + V3(0, -0.022, -0.042), ball, 0.030, 0.025, ft, k=0.02)
        b.ell(an + V3(0, 0.058, -0.034), V3(0.034, 0.068, 0.022), ft, k=0.02)
        b.ell(an + V3(-s * 0.016, 0.070, -0.060), V3(0.026, 0.055, 0.016), ft, k=0.015)                # outer sole
        toe_specs = [(0.029, 0.034, 0.0115), (0.012, 0.028, 0.0085), (-0.002, 0.025, 0.0078), (-0.015, 0.022, 0.0072),
                     (-0.026, 0.018, 0.0068)]
        toes = []
        for (ox, L, r) in toe_specs:
            # turned foot: the big toe ends up on the outside
            base = ball + V3(s * ox, 0.004, 0.002)
            q = base + V3(s * ox * 0.15, L, -0.006)
            b.cone(base, q, r, r * 0.9, ft, k=0.006)
            b.ell(q + V3(0, 0.002, 0.0035), V3(r * 0.7, r * 0.75, 0.0012), ft, k=0.002, tag="toenail")
            toes.append(q)
        b.marks["toes." + side] = toes
        b.marks["heel." + side] = an + V3(0, -0.04, -0.06)

    # ============================================================== head (tools/ragini/head.py)
    import head as _head
    _head.build_head(b)

    return b


def bounds(margin=0.03):
    return V3(-0.68, -0.20, -0.01), V3(0.68, 0.26, 1.75)
