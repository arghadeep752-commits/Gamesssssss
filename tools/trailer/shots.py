"""The trailer's shots, in Blender coordinates (x east, y north into the school, z up; metres) and seconds.

Each shot: name, dur, lens, cam keys [(t, eye, target[, roll]), ...], optional shake (radians), ease, Moulika's moves
[{move, at, toward, speed, phase, from, to}], lights [{kind, at, aim, energy, color, size, follow, flicker}], and
flicker {room: [(t, power), ...]} for the room's baked light (1 = as baked).
"""
FPS = 24
EXPOSURE = -0.25
SKY_STRENGTH = 0.12
FOG_COLOR = (0.03, 0.04, 0.055, 1.0)
FOG_AMOUNT = 0.6
F_STOP = 2.8

CLIPS = {
    "idle": ["human_000050", 0.0, 0.0],      # sad idle, head bowed
    "walk": ["human_000089", 0.0, 0.0],      # walking
    "run": ["human_000049", 0.0, 0.0],       # running, hands reaching forward
    "attack": ["human_000064", 0.35, 1.25],  # raising a hand and striking
    "point": ["human_000041", 1.3, 3.2],     # raising her arm and pointing
}

COLD = (0.62, 0.78, 1.0)
PALE = (0.85, 0.92, 1.0)

# where the items lie for their close-ups, and the door that stands open in the short trailer
ITEMS = {
    "item_main_key": (-4.895, -4.067, 0.777, 25.0),
    "item_hammer": (10.42, 10.961, 0.411, -30.0),
}
OPEN_DOORS = [("door_class8", "y_min", -105.0)]

# a failing tube: full, out, flickers back
FAIL = [(0.0, 1.0), (0.55, 0.12), (0.62, 1.0), (1.1, 0.08), (1.16, 0.85), (1.22, 0.1), (1.3, 1.0), (2.45, 0.15),
        (2.52, 1.0), (3.1, 0.05), (3.18, 0.9), (3.6, 0.3), (3.66, 1.0)]

FULL = [
    {"name": "ext", "dur": 4.5, "lens": 30,
     "cam": [(0.0, (1.3, -16.2, 1.25), (0.0, -6.0, 2.2)), (4.5, (0.45, -11.6, 1.5), (0.0, -6.0, 2.45))]},
    {"name": "veranda", "dur": 4.0, "lens": 28, "ease": "LINEAR",
     "cam": [(0.0, (-5.6, 2.0, 1.55), (-3.0, 9.0, 1.5)), (4.0, (-2.6, 2.1, 1.55), (0.0, 9.0, 1.5))]},
    {"name": "class", "dur": 4.0, "lens": 35,
     "cam": [(0.0, (-8.0, -0.9, 1.4), (-13.0, -3.0, 1.2)), (4.0, (-9.8, -1.8, 1.35), (-13.05, -3.05, 1.25))],
     "moulika": [{"move": "idle", "at": (-13.1, -3.1, 0.2), "toward": (-8.0, -1.2, 0.0), "phase": 0.1}],
     "lights": [{"kind": "AREA", "at": (-13.9, -3.7, 2.7), "aim": (-13.1, -3.1, 1.5), "energy": 45, "color": COLD, "size": 0.8, "flicker": True},
                {"kind": "AREA", "at": (-11.6, -5.2, 2.0), "aim": (-13.1, -3.1, 1.2), "energy": 18, "color": PALE, "size": 1.2, "flicker": True}],
     "flicker": {"class5": FAIL}},
    {"name": "feet", "dur": 3.0, "lens": 50, "focus_k": 1.0,
     "cam": [(0.0, (1.1, 1.95, 0.14), (-3.0, 2.25, 0.15)), (3.0, (1.1, 1.95, 0.14), (-0.6, 2.25, 0.18))],
     "moulika": [{"move": "walk", "at": (-3.7, 2.25, 0.0), "toward": (5.0, 2.25, 0.0), "speed": 0.75}],
     "lights": [{"kind": "SPOT", "at": (-1.2, 3.4, 0.7), "aim": (-1.6, 2.2, 0.08), "energy": 90, "color": PALE, "size": 70}]},
    {"name": "corridor", "dur": 4.5, "lens": 40,
     "cam": [(0.0, (-7.8, 4.8, 1.55), (-7.8, 13.0, 1.35)), (4.5, (-7.75, 3.2, 1.5), (-7.8, 5.9, 1.4))],
     "moulika": [{"move": "walk", "at": (-7.8, 13.0, 0.0), "toward": (-7.8, 0.0, 0.0)}],
     "lights": [{"kind": "SPOT", "at": (-0.5, 2.0, 2.4), "aim": (0.0, 0.0, 1.2), "energy": 260, "color": COLD, "size": 55, "follow": True},
                {"kind": "AREA", "at": (0.7, -1.5, 2.3), "aim": (0.0, 0.0, 1.3), "energy": 30, "color": PALE, "size": 1.0, "follow": True}]},
    {"name": "hide", "dur": 3.0, "lens": 28, "slit": 0.016,
     "cam": [(0.0, (-6.08, -0.62, 1.5), (-3.0, -2.6, 1.25)), (3.0, (-6.08, -0.6, 1.49), (-3.0, -1.9, 1.25))],
     "moulika": [{"move": "walk", "at": (-3.3, -3.8, 0.0), "toward": (-3.3, 5.0, 0.0), "speed": 0.7}],
     "lights": [{"kind": "AREA", "at": (-4.3, -2.2, 3.0), "aim": (-3.3, -2.0, 1.2), "energy": 45, "color": PALE, "size": 1.2}]},
    {"name": "door", "dur": 1.0, "lens": 32,
     "cam": [(0.0, (0.5, -3.3, 1.55), (0.0, -6.0, 1.35)), (1.0, (0.35, -3.9, 1.5), (0.0, -6.0, 1.35))]},
    {"name": "padlock", "dur": 1.0, "lens": 50,
     "cam": [(0.0, (0.2, -5.5, 1.22), (0.0, -5.93, 1.13)), (1.0, (0.16, -5.58, 1.2), (0.0, -5.93, 1.13))],
     "lights": [{"kind": "SPOT", "at": (-0.4, -5.3, 1.9), "aim": (0.0, -5.93, 1.12), "energy": 25, "color": PALE, "size": 40}]},
    {"name": "key", "dur": 1.0, "lens": 50,
     "cam": [(0.0, (-4.58, -3.72, 0.98), (-4.895, -4.067, 0.79)), (1.0, (-4.62, -3.78, 0.95), (-4.895, -4.067, 0.79))],
     "lights": [{"kind": "SPOT", "at": (-5.2, -3.7, 1.7), "aim": (-4.895, -4.067, 0.78), "energy": 30, "color": (1.0, 0.85, 0.65), "size": 45}]},
    {"name": "hammer", "dur": 1.0, "lens": 40,
     "cam": [(0.0, (10.0, 10.45, 0.8), (10.42, 10.961, 0.43)), (1.0, (10.05, 10.52, 0.76), (10.42, 10.961, 0.43))],
     "lights": [{"kind": "SPOT", "at": (10.9, 10.4, 1.6), "aim": (10.42, 10.961, 0.42), "energy": 30, "color": PALE, "size": 45}]},
    {"name": "hall", "dur": 4.0, "lens": 40,
     "cam": [(0.0, (-2.4, 15.8, 1.5), (-4.5, 20.4, 1.6)), (4.0, (-3.0, 16.9, 1.45), (-4.5, 20.4, 1.65))],
     "moulika": [{"move": "idle", "at": (-4.5, 20.4, 0.534), "toward": (-3.0, 16.0, 0.534), "to": 1.6, "phase": 1.0},
                 {"move": "point", "at": (-4.5, 20.4, 0.534), "toward": (-3.0, 16.0, 0.534), "from": 1.6}],
     "lights": [{"kind": "SPOT", "at": (-4.5, 22.0, 3.2), "aim": (-4.5, 20.4, 1.4), "energy": 320, "color": COLD, "size": 50},
                {"kind": "AREA", "at": (-6.2, 18.0, 2.5), "aim": (-4.5, 20.4, 1.4), "energy": 55, "color": PALE, "size": 1.2}]},
    {"name": "chase_a", "dur": 2.5, "lens": 28, "shake": 0.012, "ease": "LINEAR",
     "cam": [(0.0, (-1.5, 2.15, 1.45), (-6.0, 2.2, 1.25)), (2.5, (3.2, 2.2, 1.4), (1.2, 2.2, 1.3))],
     "moulika": [{"move": "run", "at": (-6.0, 2.2, 0.0), "toward": (10.0, 2.2, 0.0), "speed": 1.1}],
     "lights": [{"kind": "SPOT", "at": (-1.8, 0.4, 2.6), "aim": (0.0, 0.0, 1.2), "energy": 260, "color": COLD, "size": 55, "follow": True},
                {"kind": "AREA", "at": (1.6, -0.6, 2.0), "aim": (0.0, 0.0, 1.3), "energy": 30, "color": PALE, "size": 1.0, "follow": True}]},
    {"name": "chase_b", "dur": 2.5, "lens": 24, "shake": 0.015, "ease": "LINEAR",
     "cam": [(0.0, (4.8, 1.85, 0.45), (0.0, 2.2, 1.1)), (2.5, (4.8, 1.85, 0.47), (3.0, 2.2, 1.2))],
     "moulika": [{"move": "run", "at": (-2.6, 2.2, 0.0), "toward": (10.0, 2.2, 0.0), "speed": 1.1}],
     "lights": [{"kind": "SPOT", "at": (-1.8, 0.4, 2.6), "aim": (0.0, 0.0, 1.2), "energy": 260, "color": COLD, "size": 55, "follow": True},
                {"kind": "AREA", "at": (1.4, -0.7, 1.2), "aim": (0.0, 0.0, 1.3), "energy": 25, "color": PALE, "size": 1.0, "follow": True}]},
    {"name": "lunge", "dur": 1.5, "lens": 32, "shake": 0.02, "shake_scale": 4.0,
     "cam": [(0.0, (2.05, 2.2, 1.55), (0.9, 2.2, 1.5)), (1.5, (2.0, 2.2, 1.55), (0.9, 2.2, 1.52))],
     "moulika": [{"move": "attack", "at": (0.95, 2.2, 0.0), "toward": (3.0, 2.2, 0.0), "speed": 1.15}],
     "lights": [{"kind": "AREA", "at": (1.75, 2.65, 0.95), "aim": (0.95, 2.2, 1.55), "energy": 22, "color": COLD, "size": 0.6},
                {"kind": "SPOT", "at": (-0.6, 2.0, 2.6), "aim": (0.95, 2.2, 1.4), "energy": 200, "color": COLD, "size": 50}]},
]

SHORT = [
    {"name": "s_walk", "dur": 5.0, "lens": 32, "shake": 0.006, "shake_scale": 16.0, "ease": "LINEAR",
     "cam": [(0.0, (7.8, 3.0, 1.55), (7.8, 12.0, 1.45)), (5.0, (7.75, 6.2, 1.55), (7.7, 13.0, 1.45))],
     "moulika": [{"move": "walk", "at": (9.4, 14.0, 0.0), "toward": (0.0, 14.0, 0.0), "speed": 0.9, "from": 2.9}],
     "lights": [{"kind": "SPOT", "at": (8.5, 15.3, 2.8), "aim": (7.8, 14.0, 1.2), "energy": 120, "color": COLD, "size": 70}]},
    {"name": "s_class", "dur": 3.5, "lens": 30, "shake": 0.005, "shake_scale": 16.0,
     "cam": [(0.0, (8.3, 4.45, 1.55), (13.0, 4.0, 1.4)), (3.5, (10.3, 4.4, 1.5), (13.6, 4.2, 1.35))]},
    {"name": "s_scare", "dur": 2.7, "lens": 28, "shake": 0.016, "shake_scale": 3.5,
     "cam": [(0.0, (10.3, 4.4, 1.5), (13.6, 4.2, 1.35)), (0.45, (10.3, 4.4, 1.5), (13.6, 4.15, 1.35)),
             (1.45, (10.3, 4.4, 1.52), (9.4, 4.45, 1.5)), (2.7, (10.35, 4.42, 1.5), (9.4, 4.45, 1.55))],
     "moulika": [{"move": "idle", "at": (9.62, 4.45, 0.0), "toward": (11.0, 4.4, 0.0), "to": 1.15},
                 {"move": "attack", "at": (9.62, 4.45, 0.0), "toward": (11.0, 4.4, 0.0), "speed": 1.3, "from": 1.15}],
     "lights": [{"kind": "AREA", "at": (10.0, 4.65, 0.9), "aim": (9.62, 4.45, 1.55), "energy": 22, "color": COLD, "size": 0.6},
                {"kind": "SPOT", "at": (8.6, 4.2, 2.4), "aim": (9.62, 4.45, 1.4), "energy": 160, "color": COLD, "size": 50}]},
]

START = {"full": 1, "short": 1001}
SEQUENCES = {"full": FULL, "short": SHORT}
