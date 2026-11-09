"""Trailer timeline shared by the Blender scene, the soundtrack and the edit (plain Python, no bpy)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def load():
    t = json.load(open(os.path.join(HERE, "timeline.json")))
    fps = t["fps"]
    shots = {s["id"]: s for s in t["shots"]}
    at = 0.0
    segs = []
    for e in t["edit"]:
        e = dict(e)
        if e["type"] == "shot":
            s = shots[e["seg"]]
            e["f0"], e["f1"] = s["f0"], s["f1"]
            e["dur"] = (s["f1"] - s["f0"] + 1) / float(fps)
        e["start"] = at
        e["end"] = at + e["dur"]
        at = e["end"]
        segs.append(e)
    t["segs"] = segs
    t["total"] = at
    t["by_id"] = {e["seg"]: e for e in segs}
    t["frames"] = max(s["f1"] for s in t["shots"])
    return t


def when(t, seg, offset=0.0):
    """absolute edit time (s) of `offset` seconds into segment `seg`"""
    return t["by_id"][seg]["start"] + offset


def shot_time(t, seg, frame):
    """absolute edit time (s) of a scene frame inside shot `seg`"""
    e = t["by_id"][seg]
    return e["start"] + (frame - e["f0"]) / float(t["fps"])


if __name__ == "__main__":
    t = load()
    for e in t["segs"]:
        print("%-7s %-5s %6.2f - %6.2f  (%4.2fs)" % (e["seg"], e["type"], e["start"], e["end"], e["dur"]))
    print("total %.2fs, %d frames to render" % (t["total"], t["frames"]))
