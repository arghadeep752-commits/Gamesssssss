#!/usr/bin/env python3
"""Write trailer/release/source.json from public download links (name=url pairs)."""
import json
import os
import sys

files = []
for arg in sys.argv[1:]:
    name, url = arg.split("=", 1)
    assert url.startswith("https://") and "X-Amz" not in url and "Signature" not in url, "use public read links only"
    files.append({"name": name, "url": url})
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "source.json")
json.dump({"files": files}, open(out, "w"), indent=1)
print("wrote", out, len(files), "files")
