"""Roads of the DANGA map: asphalt, markings, raised footpaths with kerbs, junctions, bridges, the traffic lane graph
(India keeps LEFT) and the footpath graph for the pedestrians."""
import math

import numpy as np

import layout as LY
from mesh import L, Mesh, norm, v3

CURB_H = 0.16          # footpath height above the road (A and B roads)
ROAD_LIFT = 0.04       # road surface above the ground it is built on


def _len(pts):
    return sum(math.hypot(pts[i + 1][0] - pts[i][0], pts[i + 1][1] - pts[i][1]) for i in range(len(pts) - 1))


def resample(pts, step):
    """Polyline -> points every `step` metres (keeping the corners)."""
    out = [tuple(pts[0])]
    for i in range(len(pts) - 1):
        a, b = np.asarray(pts[i], float), np.asarray(pts[i + 1], float)
        d = float(np.linalg.norm(b - a))
        n = max(1, int(math.ceil(d / step)))
        for k in range(1, n + 1):
            p = a + (b - a) * (k / n)
            out.append((float(p[0]), float(p[1])))
    return out


def trim(pts, d0, d1):
    """Cut d0 metres off the start and d1 off the end of a polyline."""
    def cut_start(p, d):
        p = [np.asarray(x, float) for x in p]
        while len(p) >= 2 and d > 0:
            seg = float(np.linalg.norm(p[1] - p[0]))
            if seg > d + 1e-6:
                p[0] = p[0] + (p[1] - p[0]) * (d / seg)
                return p
            d -= seg
            p.pop(0)
        return p
    p = cut_start(pts, d0)
    p = cut_start(p[::-1], d1)[::-1]
    return [(float(x[0]), float(x[1])) for x in p]


def offset_line(pts, off):
    """Offset a polyline sideways: positive = to the LEFT of the travel direction (Unity space: left of +Z is -X)."""
    out = []
    n = len(pts)
    for i in range(n):
        p = np.asarray(pts[i], float)
        if i == 0:
            d = norm(np.asarray(pts[1], float) - p)
        elif i == n - 1:
            d = norm(p - np.asarray(pts[i - 1], float))
        else:
            d1 = norm(p - np.asarray(pts[i - 1], float))
            d2 = norm(np.asarray(pts[i + 1], float) - p)
            d = norm(d1 + d2)
            # mitre: keep the offset distance constant on bends
            cosh = max(0.5, float(np.dot(d, d2)))
            left = np.array([-d[1], d[0]])
            out.append(tuple(p + left * off / cosh))
            continue
        left = np.array([-d[1], d[0]])
        out.append(tuple(p + left * off))
    return out


class Roads:
    def __init__(self, graph, grid):
        self.g = graph
        self.grid = grid                  # occupancy / height raster helper (see build.py Grid)
        self.chains = []                  # dict(pts, cls, a, b, road)
        self.lanes = []                   # dict(pts [[x,y,z]], next [], speed, cls)
        self.walks = []                   # dict(pts [[x,y,z]])
        self.walk_links = []
        self.bridges = []                 # dict(p0, p1, y, width)
        self.colliders = []               # oriented boxes
        self.junction_r = {}
        self.dead_ends = []

    # ------------------------------------------------------------------------------------------- chains
    def make_chains(self):
        g = self.g
        used = set()
        for e in g.edges:
            if e["id"] in used:
                continue
            # walk backwards to the chain start
            chain = [e]
            used.add(e["id"])
            for forward in (True, False):
                cur = chain[-1] if forward else chain[0]
                node = cur["b"] if forward else cur["a"]
                # orient: we keep a list of (edge, reversed?) later; here just collect
                while g.degree(node) == 2:
                    nxt = [x for x in g.adj[node] if x["id"] not in used]
                    if not nxt or nxt[0]["cls"] != e["cls"]:
                        break
                    x = nxt[0]
                    used.add(x["id"])
                    if forward:
                        chain.append(x)
                    else:
                        chain.insert(0, x)
                    node = x["b"] if x["a"] == node else x["a"]
            # turn the edge list into an ordered node list
            if len(chain) == 1:
                nodes = [chain[0]["a"], chain[0]["b"]]
            else:
                first, second = chain[0], chain[1]
                start = first["a"] if first["a"] not in (second["a"], second["b"]) else first["b"]
                nodes = [start]
                for x in chain:
                    nodes.append(x["b"] if x["a"] == nodes[-1] else x["a"])
            pts = [g.nodes[i] for i in nodes]
            self.chains.append({"pts": pts, "cls": e["cls"], "a": nodes[0], "b": nodes[-1], "road": e["road"], "nodes": nodes})
        # junction radius: big enough for the widest road plus its footpaths
        for i in range(len(g.nodes)):
            deg = g.degree(i)
            if deg >= 3:
                wmax = max(LY.ROAD_W[x["cls"]] + 2 * LY.WALK_W[x["cls"]] for x in g.adj[i])
                self.junction_r[i] = wmax / 2.0 + 1.0
            elif deg == 2:
                # two chains of different classes meeting: small junction
                self.junction_r[i] = max(LY.ROAD_W[x["cls"]] for x in g.adj[i]) / 2.0
            else:
                self.junction_r[i] = 0.0
                self.dead_ends.append(i)
        for c in self.chains:
            ra = self.junction_r.get(c["a"], 0.0)
            rb = self.junction_r.get(c["b"], 0.0)
            if _len(c["pts"]) <= ra + rb + 2.0:
                c["trimmed"] = None
            else:
                c["trimmed"] = trim(c["pts"], ra, rb)
        return self

    # ------------------------------------------------------------------------------------------- heights
    def surface(self, pts, step=4.0):
        """Resample a 2D line and give each point its road height (bridges span water and river banks)."""
        rp = resample(pts, step)
        X = np.array([p[0] for p in rp])
        Z = np.array([p[1] for p in rp])
        h = LY.height(X, Z)
        wet = (~np.isnan(LY.water_info(X, Z))) | (h < -0.35)
        y = np.maximum(h, -0.3) + ROAD_LIFT
        spans = []
        i = 0
        n = len(rp)
        while i < n:
            if wet[i]:
                j = i
                while j < n and wet[j]:
                    j += 1
                a = max(0, i - 1)
                b = min(n - 1, j)
                ya, yb = y[a], y[b]
                for k in range(a, b + 1):
                    t = (k - a) / max(1, b - a)
                    y[k] = max(ya + (yb - ya) * t, 0.2 + ROAD_LIFT)
                spans.append((a, b))
                i = j
            else:
                i += 1
        return rp, y, spans

    # ------------------------------------------------------------------------------------------- geometry
    def build(self, M):
        """M: dict of chunked meshes (see build.py) - we add into M.get(x, z, group)."""
        self.make_chains()
        for c in self.chains:
            if c["trimmed"]:
                self._chain_geometry(M, c)
        for i in range(len(self.g.nodes)):
            if self.g.degree(i) >= 2 and self.junction_r[i] > 0:
                self._junction(M, i)
        self._lanes()
        self._walks()
        return self

    def _chain_geometry(self, M, c):
        cls = c["cls"]
        w = LY.ROAD_W[cls]
        ww = LY.WALK_W[cls]
        pts = c["trimmed"]
        rp, y, spans = self.surface(pts, 4.0)
        c["surface"] = (rp, y)
        on_bridge = np.zeros(len(rp), bool)
        for a, b in spans:
            on_bridge[a:b + 1] = True
        raised = cls in ("A", "B")
        # draw in pieces of ~40 m so each piece falls in one chunk
        n = len(rp)
        k0 = 0
        while k0 < n - 1:
            k1 = min(n - 1, k0 + 10)
            seg = rp[k0:k1 + 1]
            ys = y[k0:k1 + 1]
            cx, cz = seg[len(seg) // 2]
            mesh = M.get(cx, cz, "world")
            col = M.get(cx, cz, "coll")
            asphalt = L["asphalt"] if cls != "C" else L["asphalt_old"]
            mesh.strip(seg, w, 0, asphalt, tile=(w, 6.0), heights=ys, ao=0.95)
            col.strip(seg, w + 0.2, 0, 0, tile=(10, 10), heights=ys)
            # footpaths on both sides (raised with kerbs on A/B roads, flush on lanes)
            for side in (1, -1):
                off = side * (w / 2 + ww / 2)
                line = offset_line(seg, off)
                hy = ys + (CURB_H if raised else 0.02)
                mesh.strip(line, ww, 0, L["paving"] if raised else L["curb"], tile=(2.0, 2.0), heights=hy, ao=0.92)
                col.strip(line, ww, 0, 0, tile=(10, 10), heights=hy)
                if raised:
                    kerb = offset_line(seg, side * w / 2)
                    for q in range(len(kerb) - 1):
                        p0, p1 = (kerb[q], kerb[q + 1]) if side > 0 else (kerb[q + 1], kerb[q])
                        y0 = min(ys[q], ys[q + 1])
                        mesh.wall(p0, p1, y0 - 0.02, y0 + CURB_H, L["curb"], tile=(1.0, 0.5), col=(0.95, 0.95, 0.92), ao_bottom=0.7)
                        col.wall(p0, p1, y0 - 0.02, y0 + CURB_H, 0)
                    # outer edge of the footpath down to the ground
                    edge = offset_line(seg, side * (w / 2 + ww))
                    for q in range(len(edge) - 1):
                        p0, p1 = (edge[q + 1], edge[q]) if side > 0 else (edge[q], edge[q + 1])
                        y0 = min(ys[q], ys[q + 1])
                        mesh.wall(p0, p1, y0 - 0.5, y0 + CURB_H, L["curb"], tile=(1.0, 0.5), ao_bottom=0.8)
            self._markings(mesh, seg, ys, cls, w)
            k0 = k1
        # occupancy: road + footpaths + 1 m are never built on
        self.grid.mark_line(rp, w + 2 * ww + 2.0, "road", heights=y)
        # bridges
        for a, b in spans:
            self._bridge(M, rp[a:b + 1], y[a:b + 1], w + 2 * ww)

    def _markings(self, mesh, seg, ys, cls, w):
        lift = 0.012
        if cls == "C":
            return
        white, yellow = (1.0, 1.0, 1.0), (1.0, 0.78, 0.12)
        # edge lines
        for side in (1, -1):
            line = offset_line(seg, side * (w / 2 - 0.35))
            mesh.strip(line, 0.15, 0, L["markings"], tile=(0.15, 3.0), heights=ys + lift, col=white)
        if cls == "A":
            for off in (0.12, -0.12):
                line = offset_line(seg, off)
                mesh.strip(line, 0.12, 0, L["markings"], tile=(0.12, 3.0), heights=ys + lift, col=yellow)
            for side in (1, -1):
                self._dashes(mesh, offset_line(seg, side * w / 4), ys + lift, 3.0, 5.0, 0.13, white)
        else:
            self._dashes(mesh, seg, ys + lift, 3.0, 4.0, 0.13, white)

    def _dashes(self, mesh, line, ys, dash, gap, width, col):
        rp = [np.asarray(p, float) for p in line]
        dist = 0.0
        on = True
        acc = 0.0
        for i in range(len(rp) - 1):
            a, b = rp[i], rp[i + 1]
            L2 = float(np.linalg.norm(b - a))
            t = 0.0
            while t < L2:
                left = (dash if on else gap) - acc
                step = min(left, L2 - t)
                if on:
                    p0 = a + (b - a) * (t / L2)
                    p1 = a + (b - a) * ((t + step) / L2)
                    yy = ys[i] + (ys[i + 1] - ys[i]) * (t / L2)
                    if step > 0.3:
                        mesh.strip([tuple(p0), tuple(p1)], width, 0, L["markings"], tile=(width, dash), heights=[yy, yy], col=col)
                acc += step
                t += step
                if acc >= (dash if on else gap) - 1e-6:
                    acc = 0.0
                    on = not on
            dist += L2

    def _junction(self, M, i):
        g = self.g
        node = np.asarray(g.nodes[i], float)
        corners, outer = [], []
        hj = float(LY.height(np.array([node[0]]), np.array([node[1]]))[0])
        yj = max(hj, -0.3) + ROAD_LIFT
        for c in self.chains:
            if not c.get("trimmed"):
                continue
            for end in ("a", "b"):
                if c[end] != i:
                    continue
                p = np.asarray(c["trimmed"][0] if end == "a" else c["trimmed"][-1], float)
                q = np.asarray(c["trimmed"][1] if end == "a" else c["trimmed"][-2], float)
                d = norm(p - q)                     # pointing into the junction
                left = np.array([-d[1], d[0]])
                w = LY.ROAD_W[c["cls"]]
                ww = LY.WALK_W[c["cls"]]
                corners += [p + left * w / 2, p - left * w / 2]
                outer += [p + left * (w / 2 + ww), p - left * (w / 2 + ww), p + left * (w / 2 + ww) + d * 1.5, p - left * (w / 2 + ww) + d * 1.5]
                # zebra crossing on the main roads
                if c["cls"] in ("A", "B") and g.degree(i) >= 3:
                    mesh = M.get(p[0], p[1], "world")
                    nbar = int(w / 1.0)
                    for k in range(nbar):
                        s = -w / 2 + 0.25 + k * (w - 0.5) / max(1, nbar - 1)
                        a0 = p + left * s - d * 0.6
                        a1 = a0 - d * 2.6
                        mesh.strip([tuple(a0), tuple(a1)], 0.45, 0, L["markings"], tile=(0.45, 2.6), heights=[yj + 0.014, yj + 0.014])
        if len(corners) < 3:
            return
        hull = _convex_hull([tuple(c) for c in corners] + [tuple(node)])
        ohull = _convex_hull([tuple(c) for c in outer] + [tuple(node)])
        mesh = M.get(node[0], node[1], "world")
        col = M.get(node[0], node[1], "coll")
        mesh.polygon(ohull, yj + 0.0, L["paving"], tile=(2.0, 2.0), ao=0.92)
        mesh.polygon(hull, yj + 0.006, L["asphalt"], tile=(10.0, 10.0), ao=0.95)
        col.polygon(ohull, yj, 0)
        self.grid.mark_poly(ohull, "road", y=yj)
        self.junctions = getattr(self, "junctions", [])
        self.junctions.append({"id": i, "p": [float(node[0]), yj, float(node[1])], "r": self.junction_r[i], "deg": g.degree(i)})

    def _bridge(self, M, pts, ys, width):
        if len(pts) < 2:
            return
        p0, p1 = np.asarray(pts[0], float), np.asarray(pts[-1], float)
        L2 = float(np.linalg.norm(p1 - p0))
        if L2 < 4:
            return
        d = norm(p1 - p0)
        left = np.array([-d[1], d[0]])
        mid = (p0 + p1) / 2
        mesh = M.get(mid[0], mid[1], "world")
        col = M.get(mid[0], mid[1], "coll")
        yaw = math.degrees(math.atan2(d[0], d[1]))
        ymin = float(min(ys))
        # deck sides and underside
        for side in (1, -1):
            edge = [tuple(np.asarray(p, float) + left * side * width / 2) for p in pts]
            for q in range(len(edge) - 1):
                a, b = (edge[q], edge[q + 1]) if side < 0 else (edge[q + 1], edge[q])
                yy = min(ys[q], ys[q + 1])
                mesh.wall(a, b, yy - 0.9, yy + 0.05, L["concrete"], tile=(3.0, 1.0), col=(0.85, 0.85, 0.82))
            # parapet
            par = [tuple(np.asarray(p, float) + left * side * (width / 2 - 0.15)) for p in pts]
            for q in range(len(par) - 1):
                yy = max(ys[q], ys[q + 1]) + CURB_H
                a, b = np.asarray(par[q]), np.asarray(par[q + 1])
                c = (a + b) / 2
                seg_l = float(np.linalg.norm(b - a))
                mesh.box(c[0], yy - 0.05, c[1], 0.3, 1.0, seg_l + 0.02, L["concrete"], yaw=yaw, tile=(2.0, 1.0), col=(0.92, 0.92, 0.9))
                self.colliders.append([float(c[0]), yy - 0.05, float(c[1]), 0.3, 1.0, seg_l + 0.02, yaw])
        # piers down to the bed
        n = max(1, int(L2 / 16))
        for k in range(1, n):
            p = p0 + (p1 - p0) * (k / n)
            bed = float(LY.height(np.array([p[0]]), np.array([p[1]]))[0])
            top = float(np.interp(k / n, np.linspace(0, 1, len(ys)), ys)) - 0.9
            if top - bed > 0.5:
                for side in (1, -1):
                    q = p + left * side * width * 0.3
                    mesh.cylinder(q[0], bed - 0.5, q[1], 0.7, top - bed + 0.5, L["concrete"], seg=10, tile=(2.0, 2.0), col=(0.8, 0.8, 0.78))
                    self.colliders.append([float(q[0]), bed - 0.5, float(q[1]), 1.4, top - bed + 0.5, 1.4, yaw])
        # the deck underside (seen from boats)
        P0 = [np.asarray(p, float) + left * width / 2 for p in pts]
        P1 = [np.asarray(p, float) - left * width / 2 for p in pts]
        for q in range(len(pts) - 1):
            a = v3(P0[q][0], ys[q] - 0.9, P0[q][1])
            b = v3(P1[q][0], ys[q] - 0.9, P1[q][1])
            c2 = v3(P1[q + 1][0], ys[q + 1] - 0.9, P1[q + 1][1])
            d2 = v3(P0[q + 1][0], ys[q + 1] - 0.9, P0[q + 1][1])
            mesh.quad(a, b, c2, d2, L["concrete"], tile=(4, 4), ao=(0.6, 0.6, 0.6, 0.6), col=(0.7, 0.7, 0.7))
        self.bridges.append({"p0": [float(p0[0]), float(ys[0]), float(p0[1])], "p1": [float(p1[0]), float(ys[-1]), float(p1[1])],
                             "width": width, "ymin": ymin})

    # ------------------------------------------------------------------------------------------- traffic lanes
    def _lanes(self):
        """Lanes along every chain; India drives on the LEFT, so the lane for A->B lies left of the A->B direction."""
        ends = {}          # junction -> list of (lane id, 'in'/'out', direction at that end)
        for ci, c in enumerate(self.chains):
            if not c.get("surface"):
                continue
            rp, y = c["surface"]
            cls = c["cls"]
            n = LY.LANES[cls]
            w = LY.ROAD_W[cls]
            lw = w / (2 * n)
            speed = {"A": 15.0, "B": 11.0, "C": 7.0}[cls]
            for direction in (1, -1):
                for k in range(n):
                    off = lw * (0.5 + k)
                    line = rp if direction > 0 else rp[::-1]
                    ys = y if direction > 0 else y[::-1]
                    ol = offset_line(line, off)
                    lane = {"pts": [[round(p[0], 2), round(float(h) + 0.0, 2), round(p[1], 2)] for p, h in zip(ol, ys)],
                            "next": [], "speed": speed, "cls": cls, "chain": ci, "dir": direction, "k": k}
                    lid = len(self.lanes)
                    self.lanes.append(lane)
                    a, b = (c["a"], c["b"]) if direction > 0 else (c["b"], c["a"])
                    ends.setdefault(b, []).append((lid, "in"))
                    ends.setdefault(a, []).append((lid, "out"))
        # connectors through each junction
        for j, lst in ends.items():
            ins = [l for l, t in lst if t == "in"]
            outs = [l for l, t in lst if t == "out"]
            for li in ins:
                A = self.lanes[li]
                for lo in outs:
                    B = self.lanes[lo]
                    same_chain = B["chain"] == A["chain"]
                    if same_chain and self.g.degree(j) > 1:
                        continue                          # no U-turns at junctions
                    if B["k"] != A["k"] and not same_chain and (LY.LANES[A["cls"]] > 1 or LY.LANES[B["cls"]] > 1):
                        if not (B["k"] == 0 or A["k"] == 0):
                            continue
                    p0 = np.asarray(A["pts"][-1], float)
                    p3 = np.asarray(B["pts"][0], float)
                    d0 = norm(p0 - np.asarray(A["pts"][-2], float))
                    d3 = norm(np.asarray(B["pts"][1], float) - p3)
                    dist = float(np.linalg.norm(p3 - p0))
                    if dist < 0.5:
                        A["next"].append(lo)
                        continue
                    c1 = p0 + d0 * dist * 0.4
                    c2 = p3 - d3 * dist * 0.4
                    pts = []
                    m = max(3, int(dist / 2.5))
                    for t in np.linspace(0, 1, m):
                        q = (1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * c1 + 3 * (1 - t) * t ** 2 * c2 + t ** 3 * p3
                        pts.append([round(float(q[0]), 2), round(float(q[1]), 2), round(float(q[2]), 2)])
                    cid = len(self.lanes)
                    self.lanes.append({"pts": pts, "next": [lo], "speed": min(A["speed"], B["speed"]) * 0.6, "cls": "J", "chain": -1,
                                       "dir": 0, "k": 0, "junction": j})
                    A["next"].append(cid)

    # ------------------------------------------------------------------------------------------- footpaths
    def _walks(self):
        endpoints = {}
        for c in self.chains:
            if not c.get("surface"):
                continue
            rp, y = c["surface"]
            cls = c["cls"]
            w, ww = LY.ROAD_W[cls], LY.WALK_W[cls]
            for side in (1, -1):
                line = offset_line(rp, side * (w / 2 + ww / 2))
                hy = y + (CURB_H if cls in ("A", "B") else 0.02)
                wid = len(self.walks)
                self.walks.append({"pts": [[round(p[0], 2), round(float(h), 2), round(p[1], 2)] for p, h in zip(line, hy)]})
                endpoints.setdefault(c["a"], []).append((wid, 0))
                endpoints.setdefault(c["b"], []).append((wid, -1))
        # at each junction, link each footpath end with the nearest other ends (zebra crossings)
        for j, lst in endpoints.items():
            P = [np.asarray(self.walks[w]["pts"][e], float) for w, e in lst]
            for a in range(len(lst)):
                d = sorted(((float(np.linalg.norm(P[a] - P[b])), b) for b in range(len(lst)) if b != a))
                for dist, b in d[:2]:
                    if dist < 40:
                        link = sorted([(lst[a][0], lst[a][1]), (lst[b][0], lst[b][1])])
                        if link not in self.walk_links:
                            self.walk_links.append(link)


def _convex_hull(points):
    pts = sorted(set((round(p[0], 3), round(p[1], 3)) for p in points))
    if len(pts) < 3:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]          # counter-clockwise
