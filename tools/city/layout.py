"""The DANGA map: a compressed, game-sized Agartala (Tripura).

Unity space: X east, Z north, metres; origin = the Mughal garden in front of Ujjayanta Palace.
Real places are kept in their real directions from the palace, at game distances (like GTA's cities): Akhaura check
post to the west, Kunjaban and the airport to the north, Old Agartala and MBB College to the east, the Haora river,
Battala and the railway station to the south. Neermahal (Rudrasagar lake) and Tripura Sundari temple are pulled in
from their real 50 km; the sea along the south edge is the game's own coast.
"""
import math

import numpy as np

HALF = 1100.0                      # the world is 2200 m x 2200 m
SEA_LEVEL = -1.0
RIVER_LEVEL = -2.6
POND_LEVEL = -0.8
LAKE_LEVEL = -1.0


def coast_z(x):
    """Where the sea meets the beach."""
    return -845.0 + 18.0 * math.sin(x / 170.0) + 9.0 * math.sin(x / 61.0 + 1.3)


# ----------------------------------------------------------------------------------------------------- junctions
N = {
    "Post Office Chowmuhani": (0, -150), "Orient Chowmuhani": (-260, -150), "Melarmath": (150, -150),
    "Durga Chowmuhani": (260, -150), "Kaman Chowmuhani": (330, 270), "Paradise Chowmuhani": (260, 40),
    "Ramnagar": (-480, 40), "Shibnagar": (-370, 250), "Radhanagar": (-600, 400), "Joynagar": (-140, 330),
    "Kunjaban": (0, 520), "Airport Gate": (0, 760), "Battala": (-340, -330), "Motor Stand": (60, -290),
    "Lake Chowmuhani": (330, -330), "Banamalipur": (560, 70), "Badharghat": (90, -560), "College Tilla": (650, 420),
    "Old Agartala": (930, 230), "Jogendranagar": (520, -560), "Khayerpur": (760, 160), "Abhoynagar": (420, 140),
    "Dhaleswar": (480, -150), "Indranagar": (-150, 640),
}


def P(name):
    return N[name]


# ----------------------------------------------------------------------------------------------------- roads
# class: A = 4 lanes (two each way), B = 2 lanes with parking, C = narrow lane
ROAD_W = {"A": 14.0, "B": 9.5, "C": 6.5}
WALK_W = {"A": 3.0, "B": 2.5, "C": 1.4}
LANES = {"A": 2, "B": 1, "C": 1}

ROADS = [
    # the roads around the palace compound
    ("Palace Road South", "A", [(-478, -150), P("Orient Chowmuhani"), P("Post Office Chowmuhani"), P("Melarmath"), P("Durga Chowmuhani"), P("Dhaleswar"), (700, -150)]),
    ("Palace Road West", "B", [P("Orient Chowmuhani"), (-260, 40), (-260, 210)]),
    ("Palace Road East", "B", [P("Durga Chowmuhani"), P("Paradise Chowmuhani"), (260, 210)]),
    ("Palace Road North", "B", [(-260, 210), (0, 210), (260, 210)]),
    # arterials
    ("Akhaura Road", "A", [(-1100, 40), (-820, 42), P("Ramnagar"), (-260, 40)]),
    ("HGB Road", "A", [(0, 210), (0, 330), (0, 430), P("Kunjaban"), (0, 640), P("Airport Gate"), (0, 795)]),
    ("Assam-Agartala Road", "A", [P("Paradise Chowmuhani"), P("Abhoynagar"), P("Banamalipur"), P("Khayerpur"), P("Old Agartala"), (1100, 250)]),
    ("Station Road", "A", [P("Post Office Chowmuhani"), P("Motor Stand"), (75, -420), (85, -480), P("Badharghat"), (110, -640), (140, -720), (190, -790)]),
    ("Coastal Road", "B", [(-1000, -775), (-600, -782), (-200, -785), (190, -790), (600, -790), (1000, -785)]),
    # second rank
    ("VIP Road", "B", [(0, 430), (330, 430), P("College Tilla"), (900, 560), (1080, 640)]),
    ("Kaman Road", "B", [(260, 210), P("Kaman Chowmuhani"), (330, 430)]),
    ("Radhanagar Road", "B", [(-260, 210), P("Shibnagar"), (-470, 320), P("Radhanagar"), (-800, 560), (-950, 760)]),
    ("Battala Road", "B", [P("Orient Chowmuhani"), (-300, -240), P("Battala"), (-340, -420), (-340, -480), (-330, -560)]),
    ("Kunjaban Road", "B", [P("Kunjaban"), (-300, 520), P("Radhanagar")]),
    ("Dhaleswar Road", "B", [P("Dhaleswar"), (500, -330), (520, -420), (525, -470), P("Jogendranagar")]),
    ("Lake Road", "B", [P("Durga Chowmuhani"), (300, -240), P("Lake Chowmuhani"), (500, -330)]),
    ("Badharghat Road", "B", [(-330, -560), P("Badharghat"), (300, -560), P("Jogendranagar"), (760, -515), (920, -480), (1080, -440)]),
    ("Sundari Road", "C", [(830, -500), (830, -548)]),
    ("College Gate Lane", "C", [P("College Tilla"), (642, 488)]),
    ("Rudrasagar Road", "B", [(-330, -560), (-345, -600), (-330, -640)]),
    ("Airport Road", "B", [(-560, 760), P("Airport Gate"), (560, 760)]),
    ("Indranagar Road", "B", [(-260, 430), (-150, 430), (0, 430)]),
    ("Hospital Road", "C", [(-260, 430), (-260, 520)]),
    ("Old Agartala Lane", "C", [(985, 236), (1000, 120), (980, 30)]),
    ("Abhoynagar Road", "B", [P("Abhoynagar"), (420, -40), (480, -150)]),
    ("Harbor Lane", "C", [(190, -790), (250, -818)]),
    ("Lighthouse Lane", "C", [(600, -790), (690, -820)]),
    ("College Lane", "C", [P("College Tilla"), (650, 300), P("Khayerpur")]),
    ("Ramnagar Road", "B", [P("Ramnagar"), (-480, -100), (-470, -330), (-560, -400)]),
    ("Ramnagar North", "C", [P("Ramnagar"), (-470, 180), (-470, 320)]),
    ("Joynagar Lane", "C", [(-370, 330), (-260, 330), P("Joynagar"), (0, 330), (150, 330), (330, 330)]),
    ("Motor Stand Lane", "C", [P("Motor Stand"), (-120, -290), (-300, -240)]),
    ("Melarmath Lane", "C", [P("Melarmath"), (150, -290), (300, -290)]),
    ("Krishnanagar Lane", "C", [(150, -220), (300, -220)]),
    ("Riverside Lane", "C", [(-470, -330), (-340, -330)]),
    ("Banamalipur Lane", "C", [P("Banamalipur"), (560, -60), (480, -150)]),
    ("Kunjaban Lane", "C", [(0, 640), (200, 640), (330, 560), (330, 430)]),
    ("Shibnagar Lane", "C", [P("Shibnagar"), (-370, 430), (-260, 430)]),
    ("Akhaura Lane", "C", [(-820, 42), (-820, 220), (-700, 330), P("Radhanagar")]),
    ("Akhaura South", "C", [(-820, 42), (-820, -150), (-720, -330)]),
    ("Border Lane", "C", [(-650, 42), (-650, -150), (-480, -100)]),
    ("Station East", "C", [(300, -560), (300, -700), (190, -790)]),
    ("Beach Lane", "C", [(-200, -785), (-260, -700), (-330, -560)]),
    ("Indranagar Lane", "C", [(-150, 430), P("Indranagar"), (0, 640)]),
    ("Abhoynagar North", "C", [P("Abhoynagar"), (500, 330), (330, 330)]),
    ("Ramnagar Lane", "C", [(-650, 42), (-650, 200), (-470, 180)]),
]

# ----------------------------------------------------------------------------------------------------- water
RIVER = [(1150, -340), (900, -330), (700, -310), (520, -360), (330, -395), (150, -420), (0, -440), (-200, -440),
         (-340, -450), (-520, -430), (-700, -395), (-900, -372), (-1150, -355)]
RIVER_W = 46.0
RAIL_Z = -662.0                    # the railway runs east-west south of the station
RAIL_X = (-260.0, 1100.0)
PONDS = [   # name, centre, size (x, z), corner radius, water level
    ("Palace Pond West", (-115, -35), (110, 78), 14, POND_LEVEL),
    ("Palace Pond East", (115, -35), (110, 78), 14, POND_LEVEL),
    ("Kalyan Sagar", (965, -600), (120, 70), 10, POND_LEVEL),
    ("Chaturdash Dighi", (930, 115), (70, 40), 8, POND_LEVEL),
    ("Lake Chowmuhani Dighi", (400, -255), (70, 46), 8, POND_LEVEL),
    ("Ramnagar Dighi", (-560, 170), (64, 44), 8, POND_LEVEL),
    ("Heritage Park Lake", (-300, 600), (70, 40), 10, POND_LEVEL),
    ("Rabindra Kanan Pond", (200, 520), (44, 30), 8, POND_LEVEL),
]
LAKE = ("Rudrasagar Lake", (-600, -640), (250, 140), LAKE_LEVEL)       # ellipse: centre, radii

# ----------------------------------------------------------------------------------------------------- hills
HILLS = [   # centre, radius, height
    ((830, -585), 75, 9.0), ((640, 525), 85, 8.0), ((70, 600), 70, 5.0), ((1020, 620), 260, 26.0), ((1060, -60), 210, 18.0),
    ((-980, 920), 260, 22.0), ((920, -700), 200, 14.0), ((-900, -620), 150, 10.0), ((420, 980), 240, 16.0),
]

# ----------------------------------------------------------------------------------------------------- places
# name: centre, yaw (degrees, the way its front faces: 0 = north, 90 = east, 180 = south), footprint (x, z) kept clear
SITES = {
    "Ujjayanta Palace": ((0, 95), 180, (300, 120)),
    "Mughal Garden": ((0, -45), 180, (100, 150)),
    "Jagannath Temple": ((-195, 130), 90, (60, 60)),
    "Lakshmi Narayan Temple": ((195, 130), 270, (46, 46)),
    "Ummaneshwar Temple": ((-200, -90), 90, (30, 30)),
    "Gedu Mia Mosque": ((-380, 330), 90, (90, 80)),
    "Kunjaban Palace": ((90, 600), 180, (90, 60)),
    "Heritage Park": ((-300, 590), 180, (200, 120)),
    "Rabindra Kanan": ((200, 525), 180, (150, 100)),
    "Malancha Niwas": ((240, 685), 180, (36, 26)),
    "AGMC Hospital": ((-330, 460), 90, (100, 50)),
    "West Agartala Police Station": ((-110, -195), 0, (46, 30)),
    "City Centre": ((360, 5), 0, (80, 56)),
    "MBB College": ((640, 525), 180, (90, 60)),
    "Chaturdash Devta Temple": ((930, 190), 180, (50, 46)),
    "Tripura Sundari Temple": ((830, -585), 0, (60, 60)),
    "Agartala Railway Station": ((205, -615), 0, (150, 44)),
    "Neermahal": ((-600, -640), 90, (130, 70)),
    "MBB Airport": ((0, 830), 180, (160, 60)),
    "Helipad": ((200, 830), 0, (40, 40)),
    "Akhaura Check Post": ((-1035, 40), 90, (60, 80)),
    "Harbour": ((280, -860), 180, (160, 60)),
    "Lighthouse": ((720, -850), 0, (30, 30)),
    "Battala Bazaar": ((-260, -300), 0, (60, 40)),
    "Motor Stand": ((-40, -335), 0, (70, 40)),
    "Danga Arms": ((-560, 18), 0, (26, 18)),            # gun shop on Akhaura Road
    "Fashion Point": ((30, 360), 270, (22, 18)),          # clothes shop on HGB Road
    "Player House": ((225, -248), 0, (24, 26)),           # your house in Krishnanagar
    "Ghat": ((-260, -405), 180, (30, 20)),                # river steps at Battala
    "Swami Vivekananda Maidan": ((-150, 470), 0, (120, 66)),
}

# the districts (shown when you enter them, like GTA's area names) - centre, radius
ZONES = [
    ("Palace Compound", (0, 30), 230), ("Post Office Chowmuhani", (0, -170), 70), ("Battala", (-340, -320), 130),
    ("Melarmath", (150, -200), 90), ("Krishnanagar", (230, -250), 110), ("Durga Chowmuhani", (300, -120), 80),
    ("Ramnagar", (-520, 60), 200), ("Akhaura", (-950, 40), 180), ("Shibnagar", (-380, 300), 120),
    ("Radhanagar", (-620, 420), 160), ("Joynagar", (-130, 340), 120), ("Kunjaban", (40, 560), 170),
    ("Indranagar", (-180, 650), 150), ("MBB Airport", (0, 870), 260), ("Kaman Chowmuhani", (330, 280), 110),
    ("Abhoynagar", (430, 120), 130), ("Banamalipur", (560, 20), 130), ("College Tilla", (650, 440), 160),
    ("Old Agartala", (920, 200), 180), ("Dhaleswar", (480, -180), 110), ("Jogendranagar", (530, -540), 160),
    ("Badharghat", (120, -600), 180), ("Rudrasagar", (-600, -640), 260), ("Udaipur Hills", (850, -580), 170),
    ("Agartala Beach", (0, -830), 900), ("Haora River", (0, -440), 60),
]


# ----------------------------------------------------------------------------------------------------- road graph
def _seg_inter(p, p2, q, q2):
    r = (p2[0] - p[0], p2[1] - p[1])
    s = (q2[0] - q[0], q2[1] - q[1])
    rxs = r[0] * s[1] - r[1] * s[0]
    if abs(rxs) < 1e-9:
        return None
    qp = (q[0] - p[0], q[1] - p[1])
    t = (qp[0] * s[1] - qp[1] * s[0]) / rxs
    u = (qp[0] * r[1] - qp[1] * r[0]) / rxs
    if -1e-6 <= t <= 1 + 1e-6 and -1e-6 <= u <= 1 + 1e-6:
        return t, u
    return None


class Graph:
    """Planar road graph: nodes (junctions / bends / ends) and edges (straight pieces) with a class."""

    def __init__(self):
        self.nodes = []          # (x, z)
        self.edges = []          # dict(a, b, cls, road)
        self.adj = {}

    def node(self, p, snap=4.0):
        for i, q in enumerate(self.nodes):
            if (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2 < snap * snap:
                return i
        self.nodes.append((float(p[0]), float(p[1])))
        return len(self.nodes) - 1

    def build(self, roads):
        segs = []   # (p0, p1, cls, road)
        for name, cls, pts in roads:
            for i in range(len(pts) - 1):
                segs.append((tuple(map(float, pts[i])), tuple(map(float, pts[i + 1])), cls, name))
        # snap dangling ends onto nearby segments (T junctions)
        ends = {}
        for k, (a, b, c, n) in enumerate(segs):
            ends.setdefault(a, []).append(k)
            ends.setdefault(b, []).append(k)
        snapped = []
        for k, (a, b, cls, name) in enumerate(segs):
            na, nb = a, b
            for which in (0, 1):
                p = (a, b)[which]
                if len(ends[p]) > 1:
                    continue
                best = None
                for j, (c, d, _, _) in enumerate(segs):
                    if j == k:
                        continue
                    # projection of p on cd
                    dx, dz = d[0] - c[0], d[1] - c[1]
                    L2 = dx * dx + dz * dz
                    if L2 < 1e-6:
                        continue
                    t = max(0.0, min(1.0, ((p[0] - c[0]) * dx + (p[1] - c[1]) * dz) / L2))
                    q = (c[0] + t * dx, c[1] + t * dz)
                    dd = math.hypot(q[0] - p[0], q[1] - p[1])
                    if dd < 9.0 and (best is None or dd < best[0]):
                        best = (dd, q)
                if best:
                    if which == 0:
                        na = best[1]
                    else:
                        nb = best[1]
            snapped.append((na, nb, cls, name))
        segs = snapped
        # split every segment at all intersections
        cuts = [[0.0, 1.0] for _ in segs]
        for i in range(len(segs)):
            for j in range(i + 1, len(segs)):
                r = _seg_inter(segs[i][0], segs[i][1], segs[j][0], segs[j][1])
                if r:
                    cuts[i].append(min(1.0, max(0.0, r[0])))
                    cuts[j].append(min(1.0, max(0.0, r[1])))
        for (a, b, cls, name), cs in zip(segs, cuts):
            cs = sorted(set(round(c, 6) for c in cs))
            pts = [(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t) for t in cs]
            for i in range(len(pts) - 1):
                if math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) < 1.0:
                    continue
                ia, ib = self.node(pts[i]), self.node(pts[i + 1])
                if ia == ib:
                    continue
                if any((e["a"], e["b"]) in ((ia, ib), (ib, ia)) for e in self.adj.get(ia, [])):
                    continue
                e = {"a": ia, "b": ib, "cls": cls, "road": name, "id": len(self.edges)}
                self.edges.append(e)
                self.adj.setdefault(ia, []).append(e)
                self.adj.setdefault(ib, []).append(e)
        return self

    def degree(self, i):
        return len(self.adj.get(i, []))

    def width_at(self, i):
        return max([ROAD_W[e["cls"]] for e in self.adj.get(i, [])] or [6.0])


def build_graph():
    return Graph().build(ROADS)


# ----------------------------------------------------------------------------------------------------- terrain
def _sdf_round_rect(px, pz, c, size, rad):
    qx = np.abs(px - c[0]) - (size[0] / 2 - rad)
    qz = np.abs(pz - c[1]) - (size[1] / 2 - rad)
    out = np.hypot(np.maximum(qx, 0), np.maximum(qz, 0))
    return out + np.minimum(np.maximum(qx, qz), 0) - rad


def _dist_polyline(px, pz, pts):
    d = np.full(np.shape(px), 1e9)
    for i in range(len(pts) - 1):
        ax, az = pts[i]
        bx, bz = pts[i + 1]
        dx, dz = bx - ax, bz - az
        L2 = dx * dx + dz * dz
        t = np.clip(((px - ax) * dx + (pz - az) * dz) / L2, 0, 1)
        d = np.minimum(d, np.hypot(px - (ax + t * dx), pz - (az + t * dz)))
    return d


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def water_info(px, pz):
    """(water surface level or NaN, depth below the surface of the bed shape) for arrays of points."""
    px = np.asarray(px, np.float64)
    pz = np.asarray(pz, np.float64)
    level = np.full(px.shape, np.nan)
    # river
    d = _dist_polyline(px, pz, RIVER)
    inside = d < RIVER_W / 2
    level[inside] = RIVER_LEVEL
    for name, c, size, rad, lv in PONDS:
        s = _sdf_round_rect(px, pz, c, size, rad)
        level[s < 0] = lv
    c, r, lv = LAKE[1], LAKE[2], LAKE[3]
    e = np.hypot((px - c[0]) / r[0], (pz - c[1]) / r[1])
    level[e < 1.0] = lv
    cz = np.vectorize(coast_z)(px)
    level[pz < cz] = SEA_LEVEL
    return level


def height(px, pz):
    """Ground height (the bed under water) for arrays of points."""
    px = np.asarray(px, np.float64)
    pz = np.asarray(pz, np.float64)
    h = np.zeros(px.shape)
    for c, r, hh in HILLS:
        d2 = ((px - c[0]) ** 2 + (pz - c[1]) ** 2) / (r * r)
        h += hh * np.exp(-2.2 * d2) * (d2 < 4.0)
    # gentle undulation outside the city (never on roads: the road builder flattens its own strip)
    far = smooth(650, 950, np.maximum(np.abs(px), np.abs(pz)))
    h += far * (1.6 * np.sin(px / 90.0) * np.cos(pz / 110.0) + 0.8 * np.sin(px / 37.0 + pz / 53.0))
    # river: banks drop to the bed
    d = _dist_polyline(px, pz, RIVER)
    h = np.where(d < RIVER_W / 2 + 12, np.minimum(h, -6.0 + 6.5 * smooth(RIVER_W / 2 - 6, RIVER_W / 2 + 12, d)), h)
    for name, c, size, rad, lv in PONDS:
        s = _sdf_round_rect(px, pz, c, size, rad)
        h = np.where(s < 6, np.minimum(h, -3.0 + 3.2 * smooth(-6, 6, s)), h)
    c, r, lv = LAKE[1], LAKE[2], LAKE[3]
    e = (np.hypot((px - c[0]) / r[0], (pz - c[1]) / r[1]) - 1.0) * min(r)
    h = np.where(e < 10, np.minimum(h, -4.0 + 4.2 * smooth(-12, 10, e)), h)
    # the beach and the sea floor
    cz = np.vectorize(coast_z)(px)
    t = pz - cz                       # metres inland from the waterline
    beach = smooth(-5, 55, t)
    sea_floor = -1.25 + t * 0.06       # 6 % slope under water
    h = np.where(t < 55, h * beach + np.minimum(-0.15, -1.25 + 0.022 * (t + 0)) * (1 - beach), h)
    h = np.where(t < 0, np.maximum(-9.0, sea_floor), h)
    return h


def zone_of(x, z):
    best, bd = None, 1e9
    for name, c, r in ZONES:
        d = math.hypot(x - c[0], z - c[1]) / r
        if d < 1.0 and d < bd:
            best, bd = name, d
    return best or "Agartala"


def district(x, z):
    """Kind of town at a point: core (shops, 2-5 floors), town (houses 1-3 floors), outskirts (tin roofs), none."""
    if abs(x) > HALF - 60 or z > HALF - 60:
        return "none"
    if z < coast_z(x) + 70:
        return "beach"
    dc = math.hypot(x / 1.15, (z + 100) / 1.0)
    if dc < 470:
        return "core"
    if -380 < z < 720 and abs(x) < 820:
        return "town"
    if -760 < z < -460 and -260 < x < 640:
        return "town"
    return "outskirts"
