"""Prints "label<TAB>x<TAB>y" for every labelled element in a uiautomator dump.

Later elements win, so keypad keys take precedence over the display, which
can carry the same text (for example "0").
"""
import re
import sys
import xml.etree.ElementTree as ET

BOUNDS = re.compile(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]")


def main(path: str) -> None:
    coords = {}
    for node in ET.parse(path).iter("node"):
        label = node.get("content-desc") or ""
        match = BOUNDS.match(node.get("bounds") or "")
        if not label or not match:
            continue
        x1, y1, x2, y2 = map(int, match.groups())
        if x2 > x1 and y2 > y1:
            coords[label] = ((x1 + x2) // 2, (y1 + y2) // 2)
    for label, (x, y) in coords.items():
        print(f"{label}\t{x}\t{y}")


if __name__ == "__main__":
    main(sys.argv[1])
