"""The DANGA map: a compressed, game-sized Agartala (Tripura).

Unity space: X east, Z north, metres; origin = the Mughal garden in front of Ujjayanta Palace.
Real places are kept in their real directions from the palace, at game distances (like GTA's cities): Akhaura check
post to the west, Kunjaban and the airport to the north, Old Agartala and MBB College to the east, the Haora river,
Battala and the railway station to the south. Neermahal (Rudrasagar lake) and Tripura Sundari temple are pulled in
from their real 50 km; the sea along the south edge is the game's own coast.
"""
import math

import numpy as np

HALF = 650.0                       # the world is 1300 m x 1300 m: a dense town, the beach and the sea in the south
SEA_LEVEL = -1.0
RIVER_LEVEL = -2.6
POND_LEVEL = -0.8
LAKE_LEVEL = -1.0


def coast_z(x):
    """Where the sea meets the beach."""
    return -545.0 + 10.0 * math.sin(x / 150.0) + 5.0 * math.sin(x / 53.0 + 1.3)


# ----------------------------------------------------------------------------------------------------- junctions
N = {
    "Post Office Chowmuhani": (0, -150), "Orient Chowmuhani": (-260, -150), "Melarmath": (150, -150),
    "Durga Chowmuhani": (260, -150), "Kaman Chowmuhani": (330, 270), "Paradise Chowmuhani": (260, 40),
    "Ramnagar": (-480, 40), "Shibnagar": (-370, 250), "Radhanagar": (-600, 400), "Joynagar": (-140, 330),
    "Kunjaban": (0, 520), "Airport Gate": (0, 760), "Battala": (-340, -330), "Motor Stand": (60, -290),
    "Lake Chowmuhani": (330, -330), "Banamalipur": (560, 70), "Badharghat": (90, -560), "College Tilla": (650, 420),
    "Old Agartala": (930, 230), "Jogendranagar": (520, -560), "Khayerpur": (760, 160), "Abhoynagar": (420, 140),
    "Dhaleswar": (480, -150), "Indranagar": (-150, 600),
}


def P(name):
    return N[name]


# ----------------------------------------------------------------------------------------------------- roads
# class: A = 4 lanes (two each way), B = 2 lanes with parking, C = narrow lane
ROAD_W = {"A": 11.0, "B": 7.5, "C": 5.0}       # narrow Indian streets
WALK_W = {"A": 2.2, "B": 1.6, "C": 1.0}
LANES = {"A": 2, "B": 1, "C": 1}

ROADS = [
    # the roads around the palace compound
    ("Palace Road South", "A", [(-478, -150), P("Orient Chowmuhani"), P("Post Office Chowmuhani"), P("Melarmath"), P("Durga Chowmuhani"), P("Dhaleswar"), (632, -150)]),
    ("Palace Road West", "B", [P("Orient Chowmuhani"), (-260, 40), (-260, 210)]),
    ("Palace Road East", "B", [P("Durga Chowmuhani"), P("Paradise Chowmuhani"), (260, 210)]),
    ("Palace Road North", "B", [(-260, 210), (0, 210), (260, 210)]),
    # arterials
    ("Akhaura Road", "A", [(-632, 40), P("Ramnagar"), (-260, 40)]),
    ("HGB Road", "A", [(0, 210), (0, 330), (0, 430), P("Kunjaban"), (0, 600)]),
    ("Assam-Agartala Road", "A", [P("Paradise Chowmuhani"), P("Abhoynagar"), P("Banamalipur"), (632, 66)]),
    ("Station Road", "A", [P("Post Office Chowmuhani"), P("Motor Stand"), (75, -420), (85, -480), (90, -505)]),
    ("Coastal Road", "B", [(-632, -500), (-340, -505), (90, -505), (525, -505), (632, -500)]),
    # second rank
    ("VIP Road", "B", [(0, 430), (330, 430), (632, 420)]),
    ("Kaman Road", "B", [(260, 210), P("Kaman Chowmuhani"), (330, 430)]),
    ("Radhanagar Road", "B", [(-260, 210), P("Shibnagar"), (-470, 320), P("Radhanagar"), (-632, 430)]),
    ("Battala Road", "B", [P("Orient Chowmuhani"), (-300, -240), P("Battala"), (-340, -420), (-340, -505)]),
    ("Kunjaban Road", "B", [P("Kunjaban"), (-300, 520), P("Radhanagar")]),
    ("Dhaleswar Road", "B", [P("Dhaleswar"), (500, -330), (520, -420), (525, -505)]),
    ("Lake Road", "B", [P("Durga Chowmuhani"), (300, -240), P("Lake Chowmuhani"), (500, -330)]),
    ("Indranagar Road", "B", [(-260, 430), (-150, 430), (0, 430)]),
    ("Hospital Road", "C", [(-260, 430), (-260, 520)]),
    ("Abhoynagar Road", "B", [P("Abhoynagar"), (420, -40), (480, -150)]),
    ("Harbor Lane", "C", [(250, -505), (282, -525)]),
    ("Lighthouse Lane", "C", [(470, -505), (505, -530)]),
    ("Ramnagar Road", "B", [P("Ramnagar"), (-480, -100), (-470, -330), (-560, -400)]),
    ("Ramnagar North", "C", [P("Ramnagar"), (-470, 180), (-470, 320)]),
    ("Joynagar Lane", "C", [(-370, 330), (-260, 330), P("Joynagar"), (0, 330), (150, 330), (330, 330)]),
    ("Motor Stand Lane", "C", [P("Motor Stand"), (-120, -290), (-300, -240)]),
    ("Melarmath Lane", "C", [P("Melarmath"), (150, -290), (300, -290)]),
    ("Krishnanagar Lane", "C", [(150, -220), (300, -220)]),
    ("Riverside Lane", "C", [(-470, -330), (-340, -330)]),
    ("Banamalipur Lane", "C", [P("Banamalipur"), (560, -60), (480, -150)]),
    ("Kunjaban Lane", "C", [(0, 600), (200, 600), (330, 560), (330, 430)]),
    ("Helipad Lane", "C", [(330, 500), (410, 520)]),
    ("Shibnagar Lane", "C", [P("Shibnagar"), (-370, 430), (-260, 430)]),
    ("Border Lane", "C", [(-610, 40), (-610, -150), (-480, -100)]),
    ("Indranagar Lane", "C", [(-150, 430), P("Indranagar"), (0, 600)]),
    ("Abhoynagar North", "C", [P("Abhoynagar"), (500, 330), (330, 330)]),
    ("Ramnagar Lane", "C", [(-610, 40), (-610, 200), (-470, 180)]),
    ("Beach Lane West", "C", [(-560, -400), (-540, -505)]),
    ("Sea Front", "C", [(-200, -440), (-200, -505)]),
]

# ----------------------------------------------------------------------------------------------------- water
RIVER = [(1150, -340), (900, -330), (700, -310), (520, -360), (330, -395), (150, -420), (0, -440), (-200, -440),
         (-340, -450), (-520, -430), (-700, -395), (-900, -372), (-1150, -355)]
RIVER_W = 46.0
RAIL_Z = -662.0                    # (no railway in the smaller town)
RAIL_X = None
PONDS = [   # name, centre, size (x, z), corner radius, water level
    ("Palace Pond West", (-115, -35), (110, 78), 14, POND_LEVEL),
    ("Palace Pond East", (115, -35), (110, 78), 14, POND_LEVEL),
    ("Lake Chowmuhani Dighi", (400, -255), (70, 46), 8, POND_LEVEL),
    ("Ramnagar Dighi", (-560, 170), (64, 44), 8, POND_LEVEL),
    ("Heritage Park Lake", (-300, 600), (70, 40), 10, POND_LEVEL),
    ("Rabindra Kanan Pond", (200, 520), (44, 30), 8, POND_LEVEL),
]
LAKE = ("Rudrasagar Lake", (-5000, -5000), (1, 1), LAKE_LEVEL)       # (the water palace stands in the sea now)

# ----------------------------------------------------------------------------------------------------- hills
HILLS = [   # centre, radius, height (low hills around the town for the skyline)
    ((640, 660), 200, 22.0), ((-660, 650), 200, 18.0), ((690, 120), 120, 10.0), ((-700, -250), 120, 9.0),
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
    "Kunjaban Palace": ((90, 560), 180, (90, 60)),
    "Heritage Park": ((-300, 590), 180, (200, 100)),
    "Rabindra Kanan": ((200, 525), 180, (150, 100)),
    "AGMC Hospital": ((-330, 460), 90, (100, 50)),
    "West Agartala Police Station": ((-110, -195), 0, (46, 30)),
    "City Centre": ((360, 5), 0, (80, 56)),
    "Neermahal": ((-330, -600), 90, (130, 70)),
    "Helipad": ((440, 540), 0, (40, 40)),
    "Akhaura Check Post": ((-600, 40), 90, (60, 80)),
    "Harbour": ((280, coast_z(280) - 15), 180, (160, 60)),
    "Lighthouse": ((520, coast_z(520) - 6), 0, (30, 30)),
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
    ("Ramnagar", (-520, 60), 160), ("Akhaura Check Post", (-600, 40), 60), ("Shibnagar", (-380, 300), 120),
    ("Radhanagar", (-580, 420), 120), ("Joynagar", (-130, 340), 120), ("Kunjaban", (40, 540), 150),
    ("Indranagar", (-180, 600), 110), ("Kaman Chowmuhani", (330, 280), 110), ("Helipad", (440, 540), 60),
    ("Abhoynagar", (430, 120), 130), ("Banamalipur", (560, 20), 110), ("Dhaleswar", (480, -180), 110),
    ("Lake Chowmuhani", (400, -280), 90), ("Agartala Beach", (0, -600), 420), ("Neermahal", (-330, -600), 110),
    ("Harbour", (280, -560), 90), ("Haora River", (0, -440), 60),
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
    if abs(x) > HALF - 40 or z > HALF - 40:
        return "none"
    if z < coast_z(x) + 70:
        return "beach"
    # a small, crowded Indian town: shops and flats almost everywhere, houses towards the edges
    dc = math.hypot(x / 1.1, (z + 60) / 1.0)
    if dc < 520:
        return "core"
    return "town"
