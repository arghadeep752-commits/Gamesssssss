"""Ragini's animations, keyframed in Blender from code: idle, walk, run, attack, scream, grab.

Poses are written as rotations about the armature's own axes (degrees), applied bone by bone relative to the
rest pose:  +X rotation bends an upright bone forward and swings a hanging bone backward,
            +Y rotation leans an upright bone to her left (and lowers her left arm),
            +Z rotation turns her to her left.
Bones on her right side mirror the Y and Z rotations.
"""
import math

import bpy
from mathutils import Quaternion, Vector

FPS = 30
X = Vector((1, 0, 0))
Y = Vector((0, 1, 0))
Z = Vector((0, 0, 1))


def _mirror(side, axis, ang):
    """Right-side bones mirror Y and Z rotations."""
    if side == "R" and axis is not X:
        return -ang
    return ang


class Pose:
    def __init__(self):
        self.rot = {}
        self.hips = Vector((0, 0, 0))

    def r(self, bone, axis, ang):
        side = bone.rsplit(".", 1)[1] if "." in bone else ""
        self.rot.setdefault(bone, []).append((axis, _mirror(side, axis, ang)))
        return self


def base(p, hunch=1.0):
    """Her standing posture: hunched, head pushed forward and tilted, arms hanging, the scale held ready."""
    p.r("spine", X, 5 * hunch).r("chest", X, 9 * hunch).r("neck", X, 12 * hunch).r("head", X, -10 * hunch)
    p.r("head", Y, 11)
    p.r("upper_arm.L", Y, 34).r("upper_arm.L", X, -6)
    p.r("upper_arm.R", Y, 30).r("upper_arm.R", X, -12)
    p.r("forearm.L", X, -22).r("forearm.R", X, -48)
    p.r("hand.L", X, -10).r("hand.R", X, 10)
    p.r("thigh.L", X, -2).r("thigh.R", X, -2).r("shin.L", X, 4).r("shin.R", X, 4)
    return p


def idle(t, T):
    w = 2 * math.pi * t / T
    p = base(Pose())
    p.r("chest", X, 1.5 * math.sin(w)).r("spine", X, 0.8 * math.sin(w))
    p.r("head", Y, 4 * math.sin(w)).r("head", Z, 9 * math.sin(w + 1.0)).r("neck", Z, 4 * math.sin(w + 1.0))
    # the scale tapping her palm, twice per loop
    tap = max(0.0, math.sin(2 * w)) ** 3
    p.r("forearm.R", X, -14 * tap).r("hand.R", X, -12 * tap)
    p.r("jaw", X, 3 * math.sin(w * 3))
    p.hips = Vector((0.008 * math.sin(w), 0, -0.004 * (1 - math.cos(2 * w)) * 0.5))
    return p


def walk(t, T):
    w = 2 * math.pi * t / T
    s, c = math.sin(w), math.cos(w)
    p = base(Pose(), 1.25)
    p.r("thigh.L", X, -21 * s).r("thigh.R", X, 21 * s)
    p.r("shin.L", X, 6 + 30 * max(0.0, c) ** 1.5).r("shin.R", X, 6 + 30 * max(0.0, -c) ** 1.5)
    p.r("foot.L", X, 8 * s).r("foot.R", X, -8 * s)
    p.r("hips", Z, 5 * s).r("chest", Z, -6 * s).r("hips", Y, -3 * s)
    p.r("upper_arm.L", X, 15 * s).r("forearm.L", X, -6 * max(0.0, -s))
    p.r("upper_arm.R", X, -5 * s)
    p.r("head", Z, -3 * s).r("head", Y, 3 * math.sin(2 * w))
    p.hips = Vector((0.014 * s, 0, -0.014 * (0.5 + 0.5 * math.cos(2 * w))))
    return p


def run(t, T):
    w = 2 * math.pi * t / T
    s, c = math.sin(w), math.cos(w)
    p = base(Pose(), 1.0)
    p.r("spine", X, 12).r("chest", X, 10).r("head", X, -12)
    p.r("thigh.L", X, -36 * s - 10).r("thigh.R", X, 36 * s - 10)
    p.r("shin.L", X, 22 + 62 * max(0.0, c) ** 1.2).r("shin.R", X, 22 + 62 * max(0.0, -c) ** 1.2)
    p.r("foot.L", X, 15 * s).r("foot.R", X, -15 * s)
    p.r("hips", Z, 9 * s).r("chest", Z, -11 * s)
    p.r("upper_arm.L", X, 34 * s - 10).r("forearm.L", X, -55)
    # the scale raised high, ready to strike
    p.r("upper_arm.R", X, -95 - 8 * s).r("upper_arm.R", Y, -10).r("forearm.R", X, -35)
    p.hips = Vector((0.01 * s, 0, -0.03 * (0.5 + 0.5 * math.cos(2 * w))))
    return p


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def attack(t, T):
    """Wind up over her shoulder, two vicious swings of the scale, recover."""
    k = t / T
    p = base(Pose(), 1.0)
    up1 = _ease(k / 0.28)
    hit1 = _ease((k - 0.28) / 0.1)
    up2 = _ease((k - 0.45) / 0.12)
    hit2 = _ease((k - 0.57) / 0.09)
    back = _ease((k - 0.72) / 0.28)
    raise_ = max(0.0, up1 - hit1) + max(0.0, up2 - hit2)
    strike = max(0.0, hit1 - up2) + max(0.0, hit2 - back)
    raise_ *= (1 - back)
    p.r("upper_arm.R", X, -150 * raise_ - 55 * strike).r("upper_arm.R", Y, -25 * raise_)
    p.r("forearm.R", X, -65 * raise_ + 30 * strike)
    p.r("hand.R", X, 30 * raise_ - 25 * strike)
    p.r("chest", Z, -16 * raise_ + 14 * strike).r("chest", X, -6 * raise_ + 16 * strike).r("spine", X, 10 * strike)
    p.r("upper_arm.L", X, -45 * (raise_ + strike) * 0.8).r("forearm.L", X, -20)
    p.r("head", X, 10 * strike).r("jaw", X, 6 * strike)
    p.r("thigh.R", X, 10 * strike).r("shin.R", X, 12 * strike)
    p.hips = Vector((0, 0, -0.025 * strike))
    return p


def scream(t, T):
    k = t / T
    p = base(Pose(), 0.6)
    back = _ease(k / 0.18) * (1 - _ease((k - 0.25) / 0.12))
    thrust = _ease((k - 0.25) / 0.12) * (1 - _ease((k - 0.85) / 0.15))
    shake = math.sin(t * 61.0) * 2.5 + math.sin(t * 37.0) * 1.5
    p.r("head", X, -24 * back + 18 * thrust).r("neck", X, 12 * thrust).r("head", Z, shake * thrust)
    p.r("jaw", X, 14 * thrust + 4 * back)
    p.r("chest", X, -12 * back + 6 * thrust)
    p.r("upper_arm.L", Y, -38 * thrust).r("upper_arm.R", Y, -38 * thrust)
    p.r("upper_arm.L", X, -25 * thrust).r("upper_arm.R", X, -20 * thrust)
    p.r("forearm.L", X, 12 * thrust).r("forearm.R", X, 20 * thrust)
    p.hips = Vector((0, 0, -0.01 * thrust))
    return p


def grab(t, T):
    k = _ease(t / T * 1.6)
    p = base(Pose(), 1.0)
    p.r("upper_arm.L", X, -75 * k).r("upper_arm.L", Y, -20 * k).r("forearm.L", X, 15 * k)
    p.r("upper_arm.R", X, -40 * k).r("spine", X, 12 * k).r("head", X, 8 * k).r("jaw", X, 8 * k)
    return p


ACTIONS = [("idle", idle, 2.4, True), ("walk", walk, 1.2, True), ("run", run, 0.7, True),
           ("attack", attack, 1.3, False), ("scream", scream, 1.6, False), ("grab", grab, 1.0, False)]


def apply(arm, pose):
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1, 0, 0, 0))
        pb.location = Vector((0, 0, 0))
    for name, rots in pose.rot.items():
        pb = arm.pose.bones.get(name)
        if pb is None:
            continue
        B = pb.bone.matrix_local.to_quaternion()
        q = Quaternion((1, 0, 0, 0))
        for axis, ang in rots:
            q = Quaternion(axis, math.radians(ang)) @ q
        pb.rotation_quaternion = B.inverted() @ q @ B
    hb = arm.pose.bones.get("hips")
    if hb is not None:
        B = hb.bone.matrix_local.to_quaternion()
        hb.location = B.inverted() @ pose.hips


def build_actions(arm, log=print):
    """One action per clip, each on its own NLA track (exported to glTF as separate animations)."""
    scene = bpy.context.scene
    scene.render.fps = FPS
    if arm.animation_data is None:
        arm.animation_data_create()
    made = []
    for name, fn, T, loop in ACTIONS:
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        n = int(round(T * FPS))
        frames = range(0, n + 1)
        for f in frames:
            t = (f % n) / FPS if loop else min(f, n) / FPS
            apply(arm, fn(t, T))
            for pb in arm.pose.bones:
                pb.keyframe_insert("rotation_quaternion", frame=f + 1, group=pb.name)
                if pb.name == "hips":
                    pb.keyframe_insert("location", frame=f + 1, group=pb.name)
        try:
            for fc in act.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
        except Exception as e:      # noqa: BLE001
            log("interpolation:", e)
        track = arm.animation_data.nla_tracks.new()
        track.name = name
        track.strips.new(name, 1, act)
        arm.animation_data.action = None
        made.append((name, n, loop))
        log("action %-7s %3d frames%s" % (name, n, " (loop)" if loop else ""))
    apply(arm, Pose())
    return made
