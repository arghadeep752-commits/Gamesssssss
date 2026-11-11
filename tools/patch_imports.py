#!/usr/bin/env python3
"""After the first `godot --import`: make every downloaded texture VRAM-compressed with mipmaps (the phone
GPU can't afford 100+ MB of uncompressed textures), then Godot re-imports them."""
import glob
import os
import re
import sys

root = sys.argv[1] if len(sys.argv) > 1 else "assets/downloaded"
base_limit = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
# scanned models seen close up (the ritual vessels, the player's candle) keep more detail
CLOSE_UP = ("brass_vase_03", "brass_pot_01", "brass_pot_02", "wooden_bowl_02", "brass_candleholders", "wooden_candlestick")
count = 0
for path in glob.glob(os.path.join(root, "**", "*.import"), recursive=True):
    src = path[:-len(".import")]
    if not src.lower().endswith((".jpg", ".jpeg", ".png", ".tga", ".webp")):
        continue
    text = open(path).read()
    name = os.path.basename(src).lower()
    is_normal = bool(re.search(r"(^|[_\-.])(nor|normal|nrm)([_\-.]|$)", name))
    limit = base_limit
    if any(k.lower() in name for k in CLOSE_UP):
        limit = max(limit, 1024)
    if "head_color" in name:
        limit = 2048
    sets = {
        "compress/mode": "2",
        "mipmaps/generate": "true",
        "compress/normal_map": "1" if is_normal else "0",
        "process/size_limit": str(limit),
    }
    for k, v in sets.items():
        text, n = re.subn(r"^%s=.*$" % re.escape(k), "%s=%s" % (k, v), text, flags=re.M)
        if n == 0:
            text = text.replace("[params]\n", "[params]\n\n%s=%s\n" % (k, v), 1)
    open(path, "w").write(text)
    count += 1
print("patched %d texture import files" % count)
