"""Prints the centre "x y" of the first UI node whose accessibility label or text matches.

Usage: find.py ui.xml "Label"   (exact)   "Label*" (starts with)   "*label" (ends with)
"""
import re
import sys
import xml.etree.ElementTree as ET

path, q = sys.argv[1], sys.argv[2]
try:
    root = ET.parse(path).getroot()
except Exception:
    sys.exit(0)


def match(v: str) -> bool:
    if not v:
        return False
    if q.endswith('*') and not q.startswith('*'):
        return v.startswith(q[:-1])
    if q.startswith('*') and not q.endswith('*'):
        return v.endswith(q[1:])
    return v == q


for n in root.iter('node'):
    if match(n.get('content-desc', '')) or match(n.get('text', '')):
        m = re.findall(r'\d+', n.get('bounds', ''))
        if len(m) == 4:
            x1, y1, x2, y2 = map(int, m)
            print((x1 + x2) // 2, (y1 + y2) // 2)
            break
