#!/usr/bin/env python3
"""Downloads the human-made interface art for DANGA, so nothing on screen is a generated picture:

  - game-icons.net icons by Lorc, Delapouite, Skoll and other artists (CC BY 3.0), from the Iconify package of the
    whole collection (npm / jsDelivr / unpkg), with the game-icons GitHub archive as a fallback
  - Kenney's "Onscreen Controls", "UI Pack" and "Game Icons" (CC0) from kenney.nl

    fetch_ui.py OUT_DIR

  OUT_DIR/game-icons.json       every game-icons.net icon (name -> SVG body)
  OUT_DIR/kenney/<pack>/...     the Kenney packs, unzipped
  OUT_DIR/ui_listing.txt        every PNG in the Kenney packs (path, size)
  OUT_DIR/ui_candidates.jpg     candidate icons for each button, with their names (to check the choice)
  OUT_DIR/CREDITS_UI.md         sources and licences
"""
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request
import zipfile

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
KENNEY = ["onscreen-controls", "ui-pack", "game-icons", "mobile-controls"]

# for the candidates sheet: words to look for in icon names, per button
SLOTS = {
    "fist": ["fist", "punch"], "bat": ["baseball-bat", "spiked-bat", "bat-blade"], "knife": ["knife", "switchblade", "dagger"],
    "revolver": ["revolver"], "pistol": ["pistol", "colt", "glock", "luger", "beretta"], "smg": ["uzi", "mp5", "thompson", "submachine", "machine-gun"],
    "shotgun": ["shotgun", "pump"], "jump": ["jump", "upgrade", "up-card"], "sprint": ["sprint", "run", "running"],
    "car": ["car", "sedan"], "exit": ["exit", "door"], "phone": ["smartphone", "phone"], "map": ["map", "position-marker"],
    "horn": ["megaphone", "horn", "bugle"], "camera": ["camera"], "pause": ["pause"], "arrow": ["arrow"], "gas": ["pedal", "gas"],
    "brake": ["brake", "stop"], "star": ["star"], "house": ["house", "home"], "shirt": ["shirt", "t-shirt", "hoodie", "jacket"],
    "cross": ["hospital", "health", "first-aid", "medical"], "badge": ["police", "badge", "sheriff"], "heart": ["heart"],
    "shield": ["shield", "kevlar", "vest"], "boat": ["boat", "speedboat"], "heli": ["helicopter"], "settings": ["cog", "gear", "settings"],
    "radio": ["radio", "boombox"], "wallet": ["wallet", "cash", "money"], "notes": ["notebook", "notes", "scroll", "paper"],
    "dial": ["rotary-phone", "phone", "dial"], "save": ["save", "floppy"], "sleep": ["sleep", "bed", "moon"], "target": ["crosshair", "target", "reticule"],
    "reload": ["reload", "rotation", "cycle"], "steering": ["steering"],
}


def get(url, tries=3, timeout=90):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + 3 * i)
    raise RuntimeError("%s: %s" % (url, last))


def game_icons(out):
    path = os.path.join(out, "game-icons.json")
    if os.path.exists(path) and os.path.getsize(path) > 500000:
        print("game-icons: kept from an earlier build")
        return json.load(open(path))
    data = None
    for url in ("https://cdn.jsdelivr.net/npm/@iconify-json/game-icons/icons.json",
                "https://unpkg.com/@iconify-json/game-icons/icons.json"):
        try:
            data = json.loads(get(url))
            print("game-icons: %s (%d icons)" % (url, len(data.get("icons", {}))))
            break
        except Exception as e:  # noqa: BLE001
            print("game-icons:", e)
    if data is None:
        try:
            meta = json.loads(get("https://registry.npmjs.org/@iconify-json/game-icons"))
            ver = meta["dist-tags"]["latest"]
            tgz = get(meta["versions"][ver]["dist"]["tarball"])
            with tarfile.open(fileobj=io.BytesIO(tgz), mode="r:gz") as t:
                data = json.load(t.extractfile("package/icons.json"))
            print("game-icons: npm %s (%d icons)" % (ver, len(data.get("icons", {}))))
        except Exception as e:  # noqa: BLE001
            print("game-icons npm:", e)
    if data is None:
        # the artists' own repository: one SVG per icon (black square background + white shape)
        z = zipfile.ZipFile(io.BytesIO(get("https://github.com/game-icons/icons/archive/refs/heads/master.zip", timeout=300)))
        icons = {}
        for n in z.namelist():
            if n.endswith(".svg"):
                svg = z.read(n).decode("utf-8", "replace")
                body = re.sub(r'<path d="M0 0h512v512H0z"\s*/>', "", svg)
                body = re.sub(r"^.*?<svg[^>]*>|</svg>\s*$", "", body, flags=re.S)
                body = body.replace('fill="#fff"', 'fill="currentColor"')
                name = os.path.splitext(os.path.basename(n))[0]
                icons.setdefault(name, {"body": body, "author": n.split("/")[-2]})
        data = {"prefix": "game-icons", "icons": icons, "width": 512, "height": 512}
        print("game-icons: GitHub archive (%d icons)" % len(icons))
    json.dump(data, open(path, "w"))
    return data


def kenney(out, slug):
    dest = os.path.join(out, "kenney", slug)
    if os.path.isdir(dest) and any(f.endswith(".png") for _, _, fs in os.walk(dest) for f in fs):
        print("kenney %s: kept from an earlier build" % slug)
        return True
    try:
        html = get("https://kenney.nl/assets/" + slug).decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001
        print("kenney %s page: %s" % (slug, e))
        return False
    links = re.findall(r'href=["\']([^"\']+?\.zip)["\']', html)
    if not links:
        print("kenney %s: no zip link on the page" % slug)
        return False
    url = links[0]
    if url.startswith("/"):
        url = "https://kenney.nl" + url
    try:
        z = zipfile.ZipFile(io.BytesIO(get(url, timeout=300)))
    except Exception as e:  # noqa: BLE001
        print("kenney %s zip: %s" % (slug, e))
        return False
    os.makedirs(dest, exist_ok=True)
    n = 0
    for name in z.namelist():
        low = name.lower()
        if low.endswith((".png", ".txt")) and "/vector" not in low and not os.path.basename(name).startswith("."):
            target = os.path.join(dest, name)
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "wb") as f:
                f.write(z.read(name))
            n += 1
    print("kenney %s: %s -> %d files" % (slug, url, n))
    return n > 0


def svg_png(body, w, h, size, path):
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 %d %d" width="%d" height="%d">%s</svg>' % (w, h, size, size, body.replace("currentColor", "#ffffff"))
    subprocess.run(["rsvg-convert", "-w", str(size), "-h", str(size), "-o", path], input=svg.encode(), check=True)


def candidates_sheet(icons, out):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    W = icons.get("width", 512)
    H = icons.get("height", 512)
    names = sorted(icons["icons"])
    rows = []
    for slot, words in SLOTS.items():
        found = [n for n in names if any(w in n for w in words)]
        found.sort(key=lambda n: (min([n.find(w) if w in n else 99 for w in words]), len(n)))
        rows.append((slot, found[:12]))
    cell, lab = 96, 18
    sheet = Image.new("RGB", (110 + 12 * cell, len(rows) * (cell + lab)), (40, 44, 52))
    d = ImageDraw.Draw(sheet)
    tmp = os.path.join(out, "_tmp.png")
    for r, (slot, found) in enumerate(rows):
        y = r * (cell + lab)
        d.text((6, y + cell // 2), slot, fill=(255, 220, 120))
        for c, n in enumerate(found):
            ic = icons["icons"][n]
            try:
                svg_png(ic["body"], ic.get("width", W), ic.get("height", H), cell - 16, tmp)
                im = Image.open(tmp).convert("RGBA")
                sheet.paste(im, (110 + c * cell + 8, y + 4), im)
            except Exception:  # noqa: BLE001
                pass
            d.text((110 + c * cell + 2, y + cell - 4), n[:16], fill=(200, 200, 200))
    if os.path.exists(tmp):
        os.remove(tmp)
    sheet.save(os.path.join(out, "ui_candidates.jpg"), quality=85)
    with open(os.path.join(out, "ui_candidates.txt"), "w") as f:
        for slot, found in rows:
            f.write("%s: %s\n" % (slot, ", ".join(found)))


def kenney_sheets(out):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return
    root = os.path.join(out, "kenney")
    lines = []
    files = []
    for dp, _, fs in os.walk(root):
        for f in sorted(fs):
            if f.endswith(".png"):
                p = os.path.join(dp, f)
                try:
                    w, h = Image.open(p).size
                except Exception:  # noqa: BLE001
                    continue
                rel = os.path.relpath(p, root)
                lines.append("%s %dx%d" % (rel, w, h))
                files.append((rel, p))
    open(os.path.join(out, "ui_listing.txt"), "w").write("\n".join(lines) + "\n")
    # one sheet per pack and style folder (first 120 pictures each), labelled with the file names
    groups = {}
    for rel, p in files:
        key = "/".join(rel.split("/")[:3])
        groups.setdefault(key, []).append((rel, p))
    picked = sorted(groups.items(), key=lambda kv: kv[0])
    cell, lab, cols = 110, 26, 12
    k = 0
    for key, items in picked:
        items = items[:120]
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * (cell + lab) + 30), (70, 90, 120))
        d = ImageDraw.Draw(sheet)
        d.text((6, 6), key, fill=(255, 255, 0))
        for i, (rel, p) in enumerate(items):
            im = Image.open(p).convert("RGBA")
            im.thumbnail((cell - 10, cell - 10))
            x, y = (i % cols) * cell, 30 + (i // cols) * (cell + lab)
            sheet.paste(im, (x + 5, y + 5), im)
            d.text((x + 2, y + cell), os.path.basename(rel)[:18], fill=(255, 255, 255))
        sheet.save(os.path.join(out, "kenney_sheet_%02d.jpg" % k), quality=80)
        k += 1
        if k >= 24:
            break


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    icons = game_icons(out)
    ok = {s: kenney(out, s) for s in KENNEY}
    candidates_sheet(icons, out)
    kenney_sheets(out)
    info = icons.get("info", {})
    credits = [
        "## Interface art",
        "",
        "- Icons: game-icons.net - by Lorc, Delapouite, Skoll, Sbed, Carl Olsen, Faithtoken, Willdabeast and other artists - "
        "licensed CC BY 3.0 (https://creativecommons.org/licenses/by/3.0/). %s" % (info.get("author", {}).get("url", "https://game-icons.net")),
        "- Buttons, joystick and panels: Kenney (www.kenney.nl) - Onscreen Controls, UI Pack, Game Icons - CC0 1.0.",
        "- Fonts: The Bold Font and Bebas Neue, from dafont.com (see the font licence files).",
        "",
    ]
    open(os.path.join(out, "CREDITS_UI.md"), "w").write("\n".join(credits))
    print("kenney packs:", ok)


if __name__ == "__main__":
    main()
