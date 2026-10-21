#!/usr/bin/env python3
"""Tiny UI Automator helper for the emulator smoke test.

    ui.py dump <out.xml>                     dump the current screen
    ui.py tap-text <text> [--contains]       tap the first node whose text/content-desc matches
    ui.py tap-id <resource-id-suffix>        tap a node by testID (exposed as resource-id)
    ui.py has-text <text>                    exit 0 if the text is on screen
    ui.py tap-first-image                    tap the first node that looks like a wallpaper tile

React Native exposes `testID` as the Android resource-id and `accessibilityLabel`
as content-desc, so the app's own labels are used as selectors.
"""
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET


def adb(*args, check=True):
    return subprocess.run(["adb", *args], check=check, capture_output=True, text=True).stdout


def dump():
    for _ in range(3):
        adb("shell", "uiautomator", "dump", "/sdcard/ui.xml", check=False)
        xml = adb("shell", "cat", "/sdcard/ui.xml", check=False)
        if "<hierarchy" in xml:
            return ET.fromstring(xml[xml.index("<hierarchy"):])
        time.sleep(1.5)
    raise SystemExit("could not dump UI hierarchy")


def centre(node):
    nums = [int(n) for n in re.findall(r"\d+", node.get("bounds", ""))]
    if len(nums) != 4:
        return None
    x1, y1, x2, y2 = nums
    return (x1 + x2) // 2, (y1 + y2) // 2


def find(root, predicate):
    for node in root.iter("node"):
        if predicate(node):
            return node
    return None


def matcher(text, contains):
    def check(node):
        for attr in ("text", "content-desc"):
            value = node.get(attr, "")
            if (contains and text.lower() in value.lower()) or value == text:
                return True
        return False
    return check


def tap(node):
    point = centre(node)
    if not point:
        raise SystemExit("node has no bounds")
    adb("shell", "input", "tap", str(point[0]), str(point[1]))


def main():
    if len(sys.argv) < 2:
        raise SystemExit(__doc__)
    cmd = sys.argv[1]
    if cmd == "dump":
        root = dump()
        ET.ElementTree(root).write(sys.argv[2], encoding="utf-8")
        return
    root = dump()
    if cmd in ("tap-text", "has-text"):
        node = find(root, matcher(sys.argv[2], "--contains" in sys.argv))
        if node is None:
            raise SystemExit(1)
        if cmd == "tap-text":
            tap(node)
        return
    if cmd == "tap-id":
        node = find(root, lambda n: n.get("resource-id", "").endswith(sys.argv[2]))
        if node is None:
            raise SystemExit(1)
        tap(node)
        return
    if cmd == "tap-first-image":
        # Wallpaper tiles are image buttons whose content-desc is the wallpaper title.
        candidates = [
            n for n in root.iter("node")
            if n.get("clickable") == "true"
            and n.get("content-desc")
            and n.get("class", "").endswith(("ImageView", "Button", "ViewGroup", "View"))
            and centre(n) is not None
        ]
        tiles = [n for n in candidates if (lambda b: (b[2] - b[0]) > 200 and (b[3] - b[1]) > 300)(
            [int(v) for v in re.findall(r"\d+", n.get("bounds"))])]
        if not tiles:
            raise SystemExit(1)
        tap(tiles[0])
        print(tiles[0].get("content-desc"))
        return
    raise SystemExit(f"unknown command {cmd}")


if __name__ == "__main__":
    main()
