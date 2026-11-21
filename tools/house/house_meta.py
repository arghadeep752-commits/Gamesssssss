"""house_meta.json: everything the game needs to know about the house besides its meshes (numpy only).
Written in Unity space: Unity (x, y, z) = Blender (x, z, y)."""
import math

import layout as LY
import navigation
import props

U = navigation.U


def _fz(fl):
    return LY.floor_z(fl)


def _front(yaw):
    a = math.radians(yaw)
    return [round(math.sin(a), 4), 0.0, round(-math.cos(a), 4)]


def make(L, coll, extra, dyn_meta, hyper_info, heights, lightmaps, base_colors, emit, moon_dir, lm_scale=4.0):
    G = navigation.grid(L, coll)

    def furn(kind):
        return [f for f in L["furniture"] if f["kind"] == kind]

    def at(kind, dx=0.0, dy=0.0, dz=0.0):
        f = furn(kind)[0]
        return U(f["x"] + dx, f["y"] + dy, f["z"] + dz)

    hides = []
    for f in L["furniture"]:
        if f["kind"] in LY.HIDE_KINDS:
            fp = props.FOOTPRINT[f["kind"]]
            hides.append({"pos": U(f["x"], f["y"], f["z"]), "front": _front(f["yaw"]), "depth": fp[1], "kind": f["kind"], "room": f["room"]})
    mon = furn("monitors")[0]
    safe = furn("safe")[0]
    a = math.radians(safe["yaw"])
    safe_front = (safe["x"] + math.sin(a) * 0.25, safe["y"] - math.cos(a) * 0.25)
    dr = furn("drawers")[0]
    a2 = math.radians(dr["yaw"])
    drawer_front = (dr["x"] + math.sin(a2) * 0.3, dr["y"] - math.cos(a2) * 0.3)
    fb = furn("fusebox")[0]
    a3 = math.radians(fb["yaw"])
    fuse_front = (fb["x"] + math.sin(a3) * 0.08, fb["y"] - math.cos(a3) * 0.08)
    return {
        "lm_scale": lm_scale, "lightmaps": lightmaps, "base_colors": base_colors, "emit": emit, "h1": LY.H1, "ceil": list(LY.CEIL),
        "hyper3d": hyper_info,
        "colliders": navigation.arch_colliders(coll) + navigation.furniture_colliders(L, heights),
        "grid": navigation.export(G),
        "rooms": [{"name": r["name"], "floor": r["floor"], "rect": r["rect"], "y": _fz(r["floor"]), "label": r["label"]} for r in L["rooms"]],
        "doors": [dict(name=d["name"], floor=d["floor"], pos=U(d["x"], d["y"], _fz(d["floor"])), w=d["w"], h=d["h"], axis=d["axis"],
                       kind=d["kind"], room=d["room"], into=[d["into"][0], 0, d["into"][1]], lock=d["lock"], label=d["label"])
                  for d in L["doors"]],
        "dynamic": dyn_meta,
        "items": {k: {"label": v["label"], "object": "item_" + k,
                      "spots": [dict(on=s["on"], pos=U(s["x"], s["y"], s["z"])) for s in v["spots"]]} for k, v in L["items"].items()},
        "plants": [{"pos": U(f["x"], f["y"], f["z"]), "room": f["room"]} for f in furn("plant")],
        "hides": hides,
        "props": {
            "trophy": at("trophy", dz=0.25),
            "pc": U(mon["x"], mon["y"] - 0.05, mon["z"] + 0.45),
            "pc_tower": at("gaming_pc", dz=0.3),
            "safe": U(safe_front[0], safe_front[1], safe["z"] + 0.4),
            "drawer": U(drawer_front[0], drawer_front[1], dr["z"] + 0.55),
            "fusebox": U(fuse_front[0], fuse_front[1], fb["z"] + 0.3),
            "keypad": U(*extra["keypad"]),
            "main_door": U(7.0, 0.3, 1.2),
        },
        "lights": [dict(kind=lt["kind"], room=lt["room"], color=lt["color"], energy=lt["energy"], pos=U(lt["x"], lt["y"], lt["z"]))
                   for lt in L["lights"]],
        "trading_lights": [dict(kind=lt["kind"], room=lt["room"], color=lt["color"], energy=lt["energy"], pos=U(lt["x"], lt["y"], lt["z"]))
                           for lt in L["trading_lights"]],
        "patrol": [U(x, y, _fz(fl)) for (x, y, fl) in LY.PATROL],
        "trader_start": U(LY.TRADER_START[0], LY.TRADER_START[1], _fz(LY.TRADER_START[2])),
        "spawn": {"pos": U(LY.SPAWN["x"], LY.SPAWN["y"], _fz(LY.SPAWN["floor"])), "yaw": LY.SPAWN["yaw"]},
        "stair": {"x0": LY.STAIR["x0"], "x1": LY.STAIR["x1"], "z0": LY.STAIR["y0"], "z1": LY.STAIR["y1"], "h": LY.H1},
        "moon_dir": list(moon_dir),
        "furniture": [dict(kind=f["kind"], room=f["room"], yaw=f["yaw"], pos=U(f["x"], f["y"], f["z"])) for f in L["furniture"]],
    }, G
