"""Renders every view in house.json with the WebGL viewer in headless Chromium (local check only).
usage: python3 preview.py <out_dir> [mode=fake|baked] [views...]"""
import os
import sys
import shutil
import threading
import http.server
import functools
from playwright.sync_api import sync_playwright

out = os.path.abspath(sys.argv[1])
mode = sys.argv[2] if len(sys.argv) > 2 else "fake"
only = sys.argv[3:]
shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), "viewer.html"), os.path.join(out, "viewer.html"))
handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=out)
handler.log_message = lambda *a, **k: None
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()
shots = os.path.join(out, "preview")
os.makedirs(shots, exist_ok=True)
with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--ignore-gpu-blocklist"])
    page = b.new_page(viewport={"width": 1280, "height": 720})
    page.on("console", lambda m: print("console:", m.text))
    page.on("pageerror", lambda e: print("pageerror:", e))
    page.goto("http://127.0.0.1:%d/viewer.html?mode=%s" % (port, mode))
    names = page.evaluate("viewNames()")
    for n in names:
        if only and n not in only:
            continue
        page.evaluate("v => renderView(v)", n)
        page.locator("canvas").screenshot(path=os.path.join(shots, n + ".png"))
        print("rendered", n)
    b.close()
srv.shutdown()
