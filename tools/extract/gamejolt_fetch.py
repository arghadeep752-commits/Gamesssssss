#!/usr/bin/env python3
"""Downloads a game's Android build from Game Jolt the same way the Game Jolt website does.

    python3 gamejolt_fetch.py <game id> <work dir>

Writes:
  <work>/input/*.apk (+ any .obb)  the game, unpacked from a .zip / .xapk / .apks if it came in one
  <work>/gamejolt.json             title, developer, version and file name, so the original creator is credited
"""
import json
import os
import shutil
import sys
import time
import urllib.error
import urllib.request
import zipfile

API = "https://gamejolt.com/site-api"
UA = ("Mozilla/5.0 (Linux; Android 13; SM-A215F) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Mobile Safari/537.36")
APK_EXT = (".apk", ".xapk", ".apks", ".apkm")


def log(*a):
    print("[gamejolt]", *a, flush=True)


def call(path, data=None, tries=4):
    url = API + path
    last = None
    for k in range(tries):
        try:
            headers = {"User-Agent": UA, "Accept": "application/json, text/plain, */*",
                       "Referer": "https://gamejolt.com/", "Origin": "https://gamejolt.com"}
            body = None
            if data is not None:
                body = json.dumps(data).encode()
                headers["Content-Type"] = "application/json"
            req = urllib.request.Request(url, data=body, headers=headers,
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=60) as r:
                doc = json.loads(r.read().decode("utf-8", "replace"))
                return doc.get("payload", doc) if isinstance(doc, dict) else doc
        except urllib.error.HTTPError as e:
            last = "HTTP %s %s" % (e.code, e.read()[:300])
        except Exception as e:  # noqa: BLE001
            last = repr(e)
        time.sleep(3 * (k + 1))
    raise RuntimeError("Game Jolt request failed: %s -> %s" % (url, last))


def download(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Referer": "https://gamejolt.com/"})
    with urllib.request.urlopen(req, timeout=120) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got, step = 0, 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if got >= step:
                log("  %.1f / %.1f MB" % (got / 1e6, total / 1e6))
                step += 20 << 20
    return os.path.getsize(dest)


def fname(build):
    return ((build.get("primary_file") or {}).get("filename") or "").strip()


def pick_build(payload):
    builds = payload.get("builds") or []
    packages = {p.get("id"): p for p in payload.get("packages") or []}
    releases = {r.get("id"): r for r in payload.get("releases") or []}
    for b in builds:
        pf = b.get("primary_file") or {}
        pkg = packages.get(b.get("game_package_id"), {})
        rel = releases.get(b.get("game_release_id"), {})
        log("build %s | %s | %s bytes | type=%s other=%s | package=%r | release=%r" % (
            b.get("id"), fname(b), pf.get("filesize"), b.get("type"), b.get("os_other"),
            pkg.get("title"), rel.get("version_number")))

    def is_android(b):
        n = fname(b).lower()
        text = json.dumps(packages.get(b.get("game_package_id"), {})).lower()
        return n.endswith(APK_EXT) or ("android" in n) or ("android" in text and n.endswith(".zip"))

    cands = [b for b in builds if is_android(b)]
    if not cands:
        cands = [b for b in builds if b.get("os_other")]
    if not cands:
        raise SystemExit("No Android build found on the Game Jolt page. Upload the APK to the release "
                         "'granny-dimnight-input' as game.apk and run again.")

    def order(b):
        rel = releases.get(b.get("game_release_id"), {})
        return (fname(b).lower().endswith(".apk"), rel.get("published_on") or rel.get("added_on") or 0,
                b.get("id") or 0)

    cands.sort(key=order, reverse=True)
    return cands[0], packages, releases


def unpack(path, inp):
    """Leaves the APK (and split APKs / OBB files) in <inp>."""
    os.makedirs(inp, exist_ok=True)
    if not zipfile.is_zipfile(path):
        raise SystemExit("The download is not an APK or zip: %s" % path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        if "AndroidManifest.xml" in names:
            dest = os.path.join(inp, "game.apk")
            shutil.move(path, dest)
            return [dest]
        out = []
        for n in names:
            low = n.lower()
            if low.endswith((".apk", ".obb")) and not n.endswith("/"):
                dest = os.path.join(inp, os.path.basename(n))
                with z.open(n) as src, open(dest, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                out.append(dest)
        if not out:
            raise SystemExit("No APK inside the downloaded archive: %s" % names[:40])
        # name the biggest / base APK game.apk so the other steps find it
        apks = [p for p in out if p.lower().endswith(".apk")]
        base = next((p for p in apks if os.path.basename(p).lower() in ("base.apk", "game.apk")), None)
        base = base or max(apks, key=os.path.getsize)
        final = os.path.join(inp, "game.apk")
        if base != final:
            os.replace(base, final)
            out[out.index(base)] = final
        os.remove(path)
        return out


def main():
    gid, work = sys.argv[1], sys.argv[2]
    os.makedirs(work, exist_ok=True)
    info = {"game_id": gid, "url": "https://gamejolt.com/games/_/%s" % gid}
    try:
        g = call("/web/discover/games/%s" % gid)
        game = g.get("game", g) if isinstance(g, dict) else {}
        dev = game.get("developer") or {}
        info.update({
            "title": game.get("title"), "slug": game.get("slug"),
            "developer": dev.get("display_name") or dev.get("name"), "developer_username": dev.get("username"),
            "developer_url": ("https://gamejolt.com/@" + dev["username"]) if dev.get("username") else None,
            "published_on": game.get("published_on"), "modified_on": game.get("modified_on"),
            "engine_tags": [t for t in (game.get("tags") or []) if isinstance(t, str)][:20],
        })
        if game.get("slug"):
            info["url"] = "https://gamejolt.com/games/%s/%s" % (game["slug"], gid)
        log("game: %r by %r (@%s)" % (info.get("title"), info.get("developer"), info.get("developer_username")))
    except Exception as e:  # noqa: BLE001
        log("game info not available:", e)

    payload = call("/web/discover/games/packages/%s" % gid)
    build, packages, releases = pick_build(payload)
    rel = releases.get(build.get("game_release_id"), {})
    pkg = packages.get(build.get("game_package_id"), {})
    info["build"] = {"id": build.get("id"), "file": fname(build),
                     "size": (build.get("primary_file") or {}).get("filesize"),
                     "package": pkg.get("title"), "version": rel.get("version_number")}
    log("chosen build:", info["build"])

    link = call("/web/discover/games/builds/get-download-url/%s" % build["id"], {})
    url = link.get("url") if isinstance(link, dict) else None
    if not url:
        raise SystemExit("Game Jolt gave no download link: %r" % (link,))
    raw = os.path.join(work, "download.bin")
    size = download(url, raw)
    log("downloaded %.1f MB" % (size / 1e6))
    files = unpack(raw, os.path.join(work, "input"))
    info["files"] = [{"name": os.path.basename(p), "bytes": os.path.getsize(p)} for p in files]
    with open(os.path.join(work, "gamejolt.json"), "w", encoding="utf-8") as f:
        json.dump(info, f, indent=2)
    log("ready:", ", ".join("%s (%.1f MB)" % (x["name"], x["bytes"] / 1e6) for x in info["files"]))


if __name__ == "__main__":
    main()
