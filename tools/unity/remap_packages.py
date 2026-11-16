#!/usr/bin/env python3
"""Points the exported game at the real Unity 6 packages.

    python3 remap_packages.py <Unity project> <dll_classes.json> <package folder> [<package folder> ...]

AssetRipper (free edition) writes stand-in DLLs for the Unity packages a game uses (UGUI, TextMeshPro, URP,
AI Navigation, Timeline) and dummy copies of their shaders. Every reference to them is pointed at the real package:
  m_Script {fileID: <class hash>, guid: <stand-in DLL>, type: 3} -> {fileID: 11500000, guid: <package .cs>, type: 3}
  m_Shader {fileID: ..., guid: <dummy shader>, type: 3}         -> {fileID: 4800000, guid: <package .shader>, type: 3}
TextMeshPro's shaders come from "TMP Essential Resources" inside com.unity.ugui. The stand-ins are then deleted.
The class behind a <class hash> comes from original/dll_classes.json (rea's type list, hashed the way Unity does).
"""
import collections
import glob
import io
import json
import os
import re
import sys
import tarfile

REF = re.compile(r"\{fileID: (-?\d+), guid: ([0-9a-f]{32}), type: 3\}")
YAML_EXT = (".unity", ".prefab", ".asset", ".mat", ".playable", ".controller", ".overrideController", ".anim",
            ".signal", ".lighting", ".mask", ".preset", ".mixer", ".spriteatlas", ".fontsettings")
NS = re.compile(r"^\s*namespace\s+([A-Za-z_][\w.]*)", re.M)
SHADER_NAME = re.compile(r'^\s*Shader\s+"([^"]+)"', re.M)


def log(*a):
    print("[remap]", *a, flush=True)


def meta_guid(path):
    try:
        with open(path + ".meta", encoding="utf-8", errors="replace") as f:
            for line in f:
                if line.startswith("guid:"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        return None
    return None


def scan_packages(folders):
    scripts, shaders, unitypackages = {}, {}, []
    for root in folders:
        for dp, dn, fn in os.walk(root):
            dn[:] = [d for d in dn if d not in ("Tests", "Samples~", "Documentation~")]
            for f in fn:
                p = os.path.join(dp, f)
                if f.endswith(".cs"):
                    stem = f[:-3]
                    try:
                        text = open(p, encoding="utf-8", errors="replace").read()
                    except OSError:
                        continue
                    if not re.search(r"\b(class|struct)\s+%s\b" % re.escape(stem), text):
                        continue
                    m = NS.search(text)
                    key = (m.group(1) + "." + stem) if m else stem
                    g = meta_guid(p)
                    if g and key not in scripts:
                        scripts[key] = g
                elif f.endswith(".shader"):
                    try:
                        m = SHADER_NAME.search(open(p, encoding="utf-8", errors="replace").read(4000))
                    except OSError:
                        continue
                    g = meta_guid(p)
                    if m and g and m.group(1) not in shaders:
                        shaders[m.group(1)] = g
                elif f == "TMP Essential Resources.unitypackage":
                    unitypackages.append(p)
    return scripts, shaders, unitypackages


def extract_tmp_shaders(unitypackage, proj):
    """Unpacks only the shaders (and their include files) of TMP Essential Resources, keeping their guids."""
    found = {}
    with tarfile.open(unitypackage, "r:gz") as tar:
        entries = collections.defaultdict(dict)
        for m in tar.getmembers():
            parts = m.name.split("/")
            if len(parts) >= 2 and m.isfile():
                entries[parts[-2] if parts[-1] in ("asset", "asset.meta", "pathname") else parts[0]][parts[-1]] = m
        for guid, files in entries.items():
            if "pathname" not in files or "asset" not in files:
                continue
            path = tar.extractfile(files["pathname"]).read().decode("utf-8", "replace").splitlines()[0].strip()
            if "/Shaders/" not in path:
                continue
            dest = os.path.join(proj, path)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = tar.extractfile(files["asset"]).read()
            with open(dest, "wb") as f:
                f.write(data)
            if "asset.meta" in files:
                with open(dest + ".meta", "wb") as f:
                    f.write(tar.extractfile(files["asset.meta"]).read())
            if path.endswith(".shader"):
                m = SHADER_NAME.search(data.decode("utf-8", "replace")[:4000])
                if m:
                    found[m.group(1)] = guid
    return found


def main():
    proj = os.path.abspath(sys.argv[1])
    with open(sys.argv[2], encoding="utf-8") as f:
        dll_classes = {k: {int(i): c for i, c in v.items()} for k, v in json.load(f).items()}
    folders = [p for p in sys.argv[3:] if os.path.isdir(p)]
    scripts, shaders, ups = scan_packages(folders)
    log("package scripts: %d, package shaders: %d (from %d folders)" % (len(scripts), len(shaders), len(folders)))
    for up in ups[:1]:
        tmp = extract_tmp_shaders(up, proj)
        log("TextMeshPro shaders unpacked:", ", ".join(sorted(tmp)))
        for k, v in tmp.items():
            shaders.setdefault(k, v)

    assets = os.path.join(proj, "Assets")
    dlls = {}
    for p in glob.glob(os.path.join(assets, "**", "*.dll"), recursive=True):
        g = meta_guid(p)
        if g:
            dlls[g] = p
    dummies = {}
    for p in glob.glob(os.path.join(assets, "**", "*.shader"), recursive=True):
        if "TextMesh Pro" in p:
            continue
        text = open(p, encoding="utf-8", errors="replace").read(6000)
        m = SHADER_NAME.search(text)
        g = meta_guid(p)
        if m and g and "DummyShaderTextExporter" in text:
            dummies[g] = (m.group(1), p)
    log("stand-in DLLs: %s" % ", ".join(sorted(os.path.basename(p) for p in dlls.values())))
    log("dummy shaders: %d" % len(dummies))

    hits, misses = collections.Counter(), collections.Counter()
    shader_hits, shader_misses = collections.Counter(), collections.Counter()

    def fix(m):
        fid, guid = int(m.group(1)), m.group(2)
        if guid in dlls:
            dll = os.path.basename(dlls[guid])
            cls = dll_classes.get(dll, {}).get(fid)
            target = scripts.get(cls) if cls else None
            if target:
                hits[cls] += 1
                return "{fileID: 11500000, guid: %s, type: 3}" % target
            misses["%s#%s (%s)" % (dll, fid, cls)] += 1
            return m.group(0)
        if guid in dummies:
            name = dummies[guid][0]
            target = shaders.get(name)
            if target:
                shader_hits[name] += 1
                return "{fileID: 4800000, guid: %s, type: 3}" % target
            shader_misses[name] += 1
        return m.group(0)

    changed = 0
    files = [p for p in glob.glob(os.path.join(assets, "**", "*"), recursive=True) if p.endswith(YAML_EXT)]
    files += glob.glob(os.path.join(proj, "ProjectSettings", "*.asset"))
    for p in files:
        try:
            text = open(p, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        if "type: 3}" not in text:
            continue
        new = REF.sub(fix, text)
        if new != text:
            with open(p, "w", encoding="utf-8") as f:
                f.write(new)
            changed += 1
    log("files changed: %d" % changed)
    log("scripts pointed at packages: %d references, %d classes" % (sum(hits.values()), len(hits)))
    for k, n in hits.most_common(60):
        log("   %5d  %s" % (n, k))
    if misses:
        log("NOT FOUND in the packages (left as missing scripts):")
        for k, n in misses.most_common(40):
            log("   %5d  %s" % (n, k))
    log("shaders pointed at packages: %s" % dict(shader_hits))
    if shader_misses:
        log("shaders with no package version (fixed in the editor step): %s" % dict(shader_misses))

    for p in dlls.values():
        for q in (p, p + ".meta"):
            if os.path.exists(q):
                os.remove(q)
    removed = 0
    for g, (name, p) in dummies.items():
        if name in shaders:
            for q in (p, p + ".meta"):
                if os.path.exists(q):
                    os.remove(q)
            removed += 1
    log("deleted %d stand-in DLLs and %d dummy shaders" % (len(dlls), removed))


if __name__ == "__main__":
    main()
