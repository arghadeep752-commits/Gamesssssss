#!/usr/bin/env python3
"""Pin Packages/manifest.json to the package versions bundled with the installed Unity editor.

usage: match_packages.py <path to the Unity editor executable> <path to manifest.json>
"""
import json
import os
import sys


def bundled_packages(editor):
    root = os.path.join(os.path.dirname(os.path.realpath(editor)), "Data", "Resources", "PackageManager")
    found = {}
    for dirpath, _dirs, files in os.walk(root):
        if "package.json" not in files:
            continue
        try:
            with open(os.path.join(dirpath, "package.json"), encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue
        name, version = data.get("name"), data.get("version")
        if isinstance(name, str) and isinstance(version, str) and name.startswith("com.unity.") and name not in found:
            found[name] = version
    return found


def main():
    editor, manifest_path = sys.argv[1], sys.argv[2]
    bundled = bundled_packages(editor)
    modules = [n for n in bundled if n.startswith("com.unity.modules.")]
    print(f"{len(bundled)} Unity packages bundled with the editor ({len(modules)} modules)")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)
    deps = manifest.setdefault("dependencies", {})
    for name in list(deps):
        if name in bundled:
            if deps[name] != bundled[name]:
                print(f"  {name}: {deps[name]} -> {bundled[name]}")
                deps[name] = bundled[name]
            else:
                print(f"  {name}: {deps[name]}")
        elif name.startswith("com.unity.modules.") and len(modules) >= 10:
            print(f"  {name}: not part of this editor, removed")
            del deps[name]
        else:
            print(f"  {name}: {deps[name]} (unchanged)")

    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)
        f.write("\n")


if __name__ == "__main__":
    main()
