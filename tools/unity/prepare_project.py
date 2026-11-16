#!/usr/bin/env python3
"""Fills the Unity 6 project of Granny Dimnight with Granny 4 EndGame's exported house, models, menus and sounds.

    python3 prepare_project.py <AssetRipper export folder> <Unity project dir>

1. copies the exported Assets and ProjectSettings into the Unity project (the committed parts, Assets/Dimnight and
   Packages/, are kept)
2. drops the URP debug-menu prefabs and the TextMeshPro example scripts nothing uses
3. puts the rewritten game scripts (Unity/Overrides/Assembly-CSharp/*.cs) in place of AssetRipper's empty stubs,
   keeping each stub's .meta file, so every scene and prefab stays connected to the same script
The stand-in package DLLs and dummy shaders are handled afterwards by remap_packages.py.
"""
import glob
import os
import shutil
import sys


def log(*a):
    print("[prepare]", *a, flush=True)


def find_export(path):
    for cand in [path, os.path.join(path, "ExportedProject")]:
        if os.path.isdir(os.path.join(cand, "Assets")) and os.path.isdir(os.path.join(cand, "ProjectSettings")):
            return cand
    raise SystemExit("no exported Unity project in " + path)


def copy_tree(src, dst):
    n = 0
    for dp, _dn, fn in os.walk(src):
        rel = os.path.relpath(dp, src)
        out = os.path.join(dst, rel) if rel != "." else dst
        os.makedirs(out, exist_ok=True)
        for f in fn:
            shutil.copy2(os.path.join(dp, f), os.path.join(out, f))
            n += 1
    return n


def remove(path):
    for p in (path, path + ".meta"):
        if os.path.isdir(p):
            shutil.rmtree(p)
        elif os.path.exists(p):
            os.remove(p)


def main():
    export = find_export(sys.argv[1])
    proj = os.path.abspath(sys.argv[2])
    here = os.path.dirname(os.path.abspath(__file__))
    overrides = os.path.join(os.path.dirname(os.path.dirname(here)), "Unity", "Overrides")

    n = copy_tree(os.path.join(export, "Assets"), os.path.join(proj, "Assets"))
    log("copied %d asset files" % n)
    settings = os.path.join(proj, "ProjectSettings")
    os.makedirs(settings, exist_ok=True)
    for f in glob.glob(os.path.join(export, "ProjectSettings", "*")):
        name = os.path.basename(f)
        if name in ("ProjectVersion.txt", "PackageManagerSettings.asset", "boot.config"):
            continue
        shutil.copy2(f, os.path.join(settings, name))
    log("copied project settings")

    assets = os.path.join(proj, "Assets")
    for p in glob.glob(os.path.join(assets, "GameObject", "DebugUI*.prefab")):
        remove(p)
    examples = os.path.join(assets, "Scripts", "Assembly-CSharp", "TMPro")
    if os.path.isdir(examples):
        remove(examples)
        log("removed the TextMeshPro example scripts")

    stubs = {}
    for p in glob.glob(os.path.join(assets, "Scripts", "**", "*.cs"), recursive=True):
        stubs.setdefault(os.path.basename(p), p)
    placed, added = 0, 0
    extra = os.path.join(assets, "Dimnight", "Scripts")
    for src in sorted(glob.glob(os.path.join(overrides, "**", "*.cs"), recursive=True)):
        name = os.path.basename(src)
        if name in stubs:
            shutil.copy2(src, stubs[name])          # the stub's .meta (its guid) stays next to it
            placed += 1
        else:
            os.makedirs(extra, exist_ok=True)
            shutil.copy2(src, os.path.join(extra, name))
            added += 1
    log("game scripts: %d rewritten in place of stubs, %d new helper scripts, %d stubs left as they are"
        % (placed, added, len(stubs) - placed))


if __name__ == "__main__":
    main()
