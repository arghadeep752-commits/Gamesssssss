#!/usr/bin/env python3
"""Writes a Packages/manifest.json that matches the installed Unity 6 editor.

Unity 6 ships the graphics packages (URP, SRP Core, Shader Graph) and uGUI as
"core" packages whose versions are locked to the editor. This script reads the
versions from the editor installation, so the project always asks for exactly the
versions the editor has, and prints what it found (useful when debugging CI).

usage: unity6_manifest.py <path-to-Unity-binary> <out manifest.json> [--report <file>]
"""
import glob
import json
import os
import re
import sys

WANTED = [
    "com.unity.render-pipelines.universal",
    "com.unity.render-pipelines.core",
    "com.unity.shadergraph",
    "com.unity.ugui",
]

MODULES = [
    "com.unity.modules.androidjni",
    "com.unity.modules.animation",
    "com.unity.modules.audio",
    "com.unity.modules.imageconversion",
    "com.unity.modules.imgui",
    "com.unity.modules.jsonserialize",
    "com.unity.modules.particlesystem",
    "com.unity.modules.physics",
    "com.unity.modules.terrain",
    "com.unity.modules.terrainphysics",
    "com.unity.modules.ui",
    "com.unity.modules.uielements",
    "com.unity.modules.unitywebrequest",
]


def log(msg, out):
    print(msg)
    out.append(msg)


def main():
    editor_bin, out_path = sys.argv[1], sys.argv[2]
    report_path = None
    if "--report" in sys.argv:
        report_path = sys.argv[sys.argv.index("--report") + 1]
    lines = []
    editor_dir = os.path.dirname(editor_bin)
    data = os.path.join(editor_dir, "Data")
    pm = os.path.join(data, "Resources", "PackageManager")
    log(f"editor: {editor_bin}", lines)
    m = re.search(r"/(\d{4,}\.\d+\.\d+[abfp]\d+)/", editor_bin)
    log(f"editor version: {m.group(1) if m else '?'}", lines)

    found = {}
    # 1) built-in (bundled) packages: BuiltInPackages/<name>/package.json
    for pj in glob.glob(os.path.join(pm, "BuiltInPackages", "*", "package.json")):
        try:
            info = json.load(open(pj, encoding="utf-8"))
        except Exception:
            continue
        name, ver = info.get("name"), info.get("version")
        if name and ver and not name.startswith("com.unity.modules."):
            log(f"built-in package: {name} {ver}", lines)
        if name in WANTED and ver:
            found.setdefault(name, ver)

    # 2) any json manifest in the PackageManager folder that mentions the packages
    for path in glob.glob(os.path.join(pm, "**", "*.json"), recursive=True):
        if "BuiltInPackages" in path:
            continue
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        if "render-pipelines.universal" not in text and "com.unity.ugui" not in text:
            continue
        log(f"manifest file: {path} ({len(text)} bytes)", lines)
        try:
            doc = json.loads(text)
        except Exception:
            doc = None

        def walk(node):
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in WANTED:
                        ver = v if isinstance(v, str) else (v.get("version") or v.get("defaultVersion") if isinstance(v, dict) else None)
                        if isinstance(ver, str) and re.match(r"^\d+\.\d+\.\d+", ver):
                            log(f"  {k}: {ver}", lines)
                            found.setdefault(k, ver)
                    walk(v)
            elif isinstance(node, list):
                for v in node:
                    walk(v)
        if doc is not None:
            walk(doc)

    # 3) project templates bundled with the editor
    for tgz in glob.glob(os.path.join(pm, "ProjectTemplates", "*")):
        log(f"template: {os.path.basename(tgz)}", lines)

    deps = {}
    for name in WANTED:
        if name in found:
            deps[name] = found[name]
    if "com.unity.render-pipelines.universal" not in deps:
        log("ERROR: could not find the URP version in the editor installation", lines)
        if report_path:
            open(report_path, "w").write("\n".join(lines) + "\n")
        sys.exit(2)
    # only list URP + uGUI explicitly; URP pulls in the matching Core and Shader Graph
    manifest = {"dependencies": {}}
    manifest["dependencies"]["com.unity.render-pipelines.universal"] = deps["com.unity.render-pipelines.universal"]
    manifest["dependencies"]["com.unity.ugui"] = deps.get("com.unity.ugui", "2.0.0")
    for mod in MODULES:
        manifest["dependencies"][mod] = "1.0.0"
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")
    log(f"wrote {out_path}: URP {manifest['dependencies']['com.unity.render-pipelines.universal']}, uGUI {manifest['dependencies']['com.unity.ugui']}", lines)
    if report_path:
        open(report_path, "w").write("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
