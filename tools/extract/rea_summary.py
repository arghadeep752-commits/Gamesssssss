#!/usr/bin/env python3
"""Turns rea's JSON (IL2CPP metadata or managed members) into short, readable lists.

    python3 rea_summary.py il2cpp|managed <rea json> <out dir>

Writes rea_<mode>_structure.json (the shape of rea's answer), rea_<mode>_types.md (the game's own classes with their
fields and methods) and rea_<mode>_strings.txt (text literals: UI words, tags, scene names...).
"""
import collections
import json
import os
import re
import sys

ENGINE_NS = re.compile(r"^(System|Mono|Unity|UnityEngine|UnityEditor|TMPro|Microsoft|Internal|JetBrains|"
                       r"Newtonsoft|Google|GooglePlayGames|Firebase|Photon|ExitGames|DG\.Tweening|Cinemachine|"
                       r"Il2Cpp|AOT|<)")
ENGINE_IMG = re.compile(r"^(mscorlib|System|Mono|Unity|UnityEngine|netstandard|Newtonsoft|Google|Firebase|"
                        r"Photon|DOTween|Cinemachine|__Generated)", re.I)


def skeleton(x, depth=0):
    if depth > 6:
        return "..."
    if isinstance(x, dict):
        return {k: skeleton(v, depth + 1) for k, v in list(x.items())[:50]}
    if isinstance(x, list):
        if not x:
            return []
        return [skeleton(x[0], depth + 1), "... %d items" % len(x)] if len(x) > 1 else [skeleton(x[0], depth + 1)]
    if isinstance(x, str):
        return x[:100]
    return x


def collect(data, wanted):
    found = collections.defaultdict(list)

    def walk(x):
        if isinstance(x, dict):
            for k, v in x.items():
                if k in wanted and isinstance(v, list) and v and isinstance(v[0], dict):
                    found[k].extend(v)
                walk(v)
        elif isinstance(x, list):
            for v in x:
                walk(v)

    walk(data)
    return found


def text(v):
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        for k in ("display", "rendered", "name", "full_name", "value", "text"):
            if isinstance(v.get(k), str):
                return v[k]
    return None


def main():
    mode, src, outd = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outd, exist_ok=True)
    try:
        with open(src, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:  # noqa: BLE001
        print("rea output not readable:", e)
        return
    with open(os.path.join(outd, "rea_%s_structure.json" % mode), "w", encoding="utf-8") as f:
        json.dump(skeleton(data), f, indent=1)

    nr = data.get("normalized_result") if isinstance(data, dict) else None
    if isinstance(nr, dict) and isinstance(nr.get("types"), list):
        got = {k: v for k, v in nr.items() if isinstance(v, list)}
    else:
        got = collect(data, {"images", "types", "methods", "fields", "properties", "string_literals", "members"})
    print("rea collections:", {k: len(v) for k, v in got.items() if isinstance(v, list)})

    image_rows = [r for r in got.get("images", []) if isinstance(r, dict)]

    def image_of(ti):
        for im in image_rows:
            s0, n = im.get("type_start"), im.get("type_count")
            if isinstance(s0, int) and isinstance(n, int) and s0 <= ti < s0 + n:
                return text(im.get("name")) or ""
        return ""

    types = {}
    for pos, row in enumerate(got.get("types", [])):
        idx = row.get("index", pos)
        types[idx] = {"name": text(row.get("name")) or "?", "ns": text(row.get("namespace")) or "",
                      "image": image_of(idx), "parent": text(row.get("parent")) or "",
                      "declaring": row.get("declaring_type", -1), "fields": [], "methods": [], "props": []}
    for t in types.values():   # nested classes: Outer/Inner
        d = t["declaring"]
        if isinstance(d, int) and d in types and d != -1:
            t["name"] = types[d]["name"] + "/" + t["name"]
            t["ns"] = t["ns"] or types[d]["ns"]

    def owner(row):
        d = row.get("declaring_type")
        if isinstance(d, dict):
            d = d.get("index", text(d))
        if d in types:
            return types[d]
        if isinstance(d, str):
            for t in types.values():
                if t["name"] == d or (t["ns"] + "." + t["name"]) == d:
                    return t
        return None

    for coll, key in (("fields", "fields"), ("methods", "methods"), ("properties", "props")):
        for row in got.get(coll, []):
            t = owner(row)
            n = text(row.get("name"))
            if t is not None and n:
                t[key].append(n)

    for row in got.get("members", []):   # managed members: flat rows with a declaring type name
        tn = text(row.get("declaring_type")) or text(row.get("type_name")) or "?"
        t = types.setdefault(tn, {"name": tn, "ns": "", "image": "Assembly-CSharp", "parent": "",
                                  "fields": [], "methods": [], "props": []})
        kind = (text(row.get("kind")) or "").lower()
        n = text(row.get("name")) or "?"
        (t["methods"] if "method" in kind else t["props"] if "prop" in kind else t["fields"]).append(n)

    game_images = {t["image"] for t in types.values() if t["image"].lower().startswith("assembly-csharp")}
    if game_images:
        game = [t for t in types.values() if t["image"] in game_images and not t["name"].startswith("<")]
    else:
        game = [t for t in types.values()
                if not ENGINE_NS.match(t["ns"] or "") and not ENGINE_IMG.match(t["image"] or "")
                and not t["name"].startswith("<")]
    game.sort(key=lambda t: (t["image"], t["ns"], t["name"]))
    lines = ["# Game classes found by rea (%s)" % mode, "",
             "%d classes in the game's own code (engine and library classes left out)." % len(game), ""]
    for t in game:
        head = "## %s%s" % ((t["ns"] + ".") if t["ns"] else "", t["name"])
        if t["parent"]:
            head += " : " + t["parent"]
        lines.append(head + ("  _(%s)_" % t["image"] if t["image"] else ""))
        if t["fields"]:
            lines.append("- fields: " + ", ".join(t["fields"][:60]))
        if t["props"]:
            lines.append("- properties: " + ", ".join(t["props"][:40]))
        if t["methods"]:
            lines.append("- methods: " + ", ".join(m for m in t["methods"][:80] if not m.startswith("<")))
        lines.append("")
    with open(os.path.join(outd, "rea_%s_types.md" % mode), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    strings = []
    for row in got.get("string_literals", []):
        s = text(row.get("value")) or text(row.get("text")) or text(row.get("literal")) or text(row.get("name"))
        if s and 2 <= len(s) <= 160 and s.isprintable():
            strings.append(s)
    if strings:
        with open(os.path.join(outd, "rea_%s_strings.txt" % mode), "w", encoding="utf-8") as f:
            f.write("\n".join(dict.fromkeys(strings)))
    print("rea summary: %d game classes, %d strings" % (len(game), len(strings)))


if __name__ == "__main__":
    main()
