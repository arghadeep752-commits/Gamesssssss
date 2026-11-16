#!/usr/bin/env python3
"""Sets each package in Packages/manifest.json to the newest version on Unity's registry that this editor can use
(same major.minor as written, editor requirement <= the editor). Bundled packages are pinned afterwards by
match_packages.py, which wins.

usage: latest_packages.py <manifest.json> <editor version, e.g. 6000.0.85f1>
"""
import json
import re
import sys
import urllib.request


def vkey(v):
    return tuple(int(x) for x in re.findall(r"\d+", v.split("-")[0])[:3])


def ukey(unity, release):
    m = re.match(r"(\d+)\.(\d+)", unity or "0.0")
    r = re.match(r"(\d+)([abfp])(\d+)", release or "0f0")
    stage = {"a": 0, "b": 1, "f": 2, "p": 3}[r.group(2)] if r else 2
    return (int(m.group(1)), int(m.group(2)), int(r.group(1)) if r else 0, stage, int(r.group(3)) if r else 0)


def main():
    path, editor = sys.argv[1], sys.argv[2]
    m = re.match(r"(\d+)\.(\d+)\.(\d+)([abfp])(\d+)", editor)
    ed = (int(m.group(1)), int(m.group(2)), int(m.group(3)), {"a": 0, "b": 1, "f": 2, "p": 3}[m.group(4)], int(m.group(5)))
    manifest = json.load(open(path))
    deps = manifest["dependencies"]
    for name, want in list(deps.items()):
        if name.startswith("com.unity.modules."):
            continue
        try:
            req = urllib.request.Request("https://packages.unity.com/" + name, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=60) as r:
                info = json.load(r)
        except Exception as e:  # noqa: BLE001
            print("  %s: registry not reachable (%s), keeping %s" % (name, e, want))
            continue
        prefix = vkey(want)[:2]
        best = None
        for v, meta in (info.get("versions") or {}).items():
            if "-" in v or vkey(v)[:2] != prefix:
                continue
            if ukey(meta.get("unity"), meta.get("unityRelease")) > ed:
                continue
            if best is None or vkey(v) > vkey(best):
                best = v
        if best and best != want:
            print("  %s: %s -> %s" % (name, want, best))
            deps[name] = best
        else:
            print("  %s: %s" % (name, want))
    json.dump(manifest, open(path, "w"), indent=2)


if __name__ == "__main__":
    main()
