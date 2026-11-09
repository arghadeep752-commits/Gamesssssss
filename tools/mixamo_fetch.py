#!/usr/bin/env python3
"""Fetch Chaya's animation clips from Mixamo automatically, with the developer's own Mixamo login.

    MIXAMO_TOKEN=... GH_TOKEN=... GITHUB_REPOSITORY=owner/repo python3 tools/mixamo_fetch.py <out dir>

Mixamo has no public download API: every export needs a signed-in Adobe account. The developer signs in once on
mixamo.com and copies the session token (localStorage.access_token, valid about a day) into the repository secret
MIXAMO_TOKEN - or hands it over and it is parked in the private draft release `chaya-mixamo` as mixamo_token.txt.
Then this script, in CI, does what the Mixamo website does when you press Download:

  search each clip by name -> read its settings for the chosen character -> ask for an FBX export
  (skin off, 30 fps, 'In Place' for walk/run) -> wait for the job -> download the FBX

The clips are stored in the private draft release `chaya-mixamo` (Mixamo files are not committed to the public repo),
the parked token is deleted, and the game build (chaya.yml) is started - it fits the clips onto Chaya.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

API = "https://www.mixamo.com/api/v1"
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.environ.get("GITHUB_REPOSITORY", "")
GH_TOKEN = os.environ.get("GH_TOKEN", "")
TAG = "chaya-mixamo"
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def log(*a):
    print(*a, flush=True)


# ------------------------------------------------------------------------------------------------ GitHub (private draft release)
def gh(method, url, body=None, data=None, ctype=None, accept="application/vnd.github+json"):
    if not url.startswith("http"):
        url = "https://api.github.com" + url
    h = {"Authorization": "Bearer " + GH_TOKEN, "Accept": accept, "User-Agent": "chaya-ci"}
    if body is not None:
        data = json.dumps(body).encode()
        ctype = "application/json"
    if ctype:
        h["Content-Type"] = ctype
    r = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=120) as resp:
        b = resp.read()
        if accept == "application/octet-stream":
            return b
        return json.loads(b) if b else {}


def draft_release(create=False):
    for rel in gh("GET", "/repos/%s/releases?per_page=100" % REPO):
        if rel.get("tag_name") == TAG:
            return rel
    if not create:
        return None
    return gh("POST", "/repos/%s/releases" % REPO, {"tag_name": TAG, "name": "Chaya Mixamo clips (private draft - do not publish)",
                                                   "draft": True, "body": "The developer's own Mixamo downloads for Chaya. Kept private."})


def release_asset(rel, name):
    for a in gh("GET", "/repos/%s/releases/%d/assets?per_page=100" % (REPO, rel["id"])):
        if a["name"] == name:
            return a
    return None


def put_asset(rel, path, name):
    old = release_asset(rel, name)
    if old:
        gh("DELETE", "/repos/%s/releases/assets/%d" % (REPO, old["id"]))
    url = "https://uploads.github.com/repos/%s/releases/%d/assets?name=%s" % (REPO, rel["id"], urllib.parse.quote(name))
    gh("POST", url, data=open(path, "rb").read(), ctype="application/octet-stream")


# ------------------------------------------------------------------------------------------------ Mixamo
class Mixamo:
    def __init__(self, token):
        self.token = token.strip().strip('"')

    def req(self, method, path, body=None, timeout=60):
        h = {"Accept": "application/json", "Content-Type": "application/json", "X-Api-Key": "mixamo2",
             "X-Requested-With": "XMLHttpRequest", "Authorization": "Bearer " + self.token, "User-Agent": UA,
             "Origin": "https://www.mixamo.com", "Referer": "https://www.mixamo.com/"}
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(API + path, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                b = resp.read()
                return resp.status, (json.loads(b) if b else {})
        except urllib.error.HTTPError as e:
            txt = e.read()[:400].decode("utf-8", "replace")
            if e.code in (401, 403):
                raise SystemExit("Mixamo refused the token (HTTP %d) - it has probably expired: sign in again and copy a new one. %s" % (e.code, txt))
            raise RuntimeError("Mixamo %s %s -> HTTP %d %s" % (method, path, e.code, txt))

    def character(self, wanted=""):
        if wanted:
            return wanted, "configured"
        try:
            _, j = self.req("GET", "/characters/primary")
            cid = j.get("primary_character_id") or j.get("character_id") or j.get("id")
            if cid:
                return cid, j.get("primary_character_name") or j.get("name") or "primary"
            log("characters/primary:", json.dumps(j)[:300])
        except Exception as ex:     # noqa: BLE001
            log("no primary character:", ex)
        try:
            _, j = self.req("GET", "/products?page=1&limit=24&order=&type=Character&query=" + urllib.parse.quote("Y Bot"))
            for r in j.get("results", []):
                if (r.get("name") or r.get("description") or "").strip().lower() in ("y bot", "ybot"):
                    return r["id"], "Y Bot"
            log("character search:", json.dumps(j.get("results", [])[:2])[:300])
        except Exception as ex:     # noqa: BLE001
            log("character search failed:", ex)
        return "ef7eb018-7cf3-4ae1-99ac-bab1c2c5d419", "fallback"

    def find(self, names):
        for name in names:
            _, j = self.req("GET", "/products?page=1&limit=48&order=&type=Motion%2CMotionPack&query=" + urllib.parse.quote(name))
            res = j.get("results", [])
            label = lambda r: (r.get("description") or r.get("name") or "").strip()      # noqa: E731
            singles = [r for r in res if "," not in label(r) and (r.get("type") or "Motion") == "Motion"]
            exact = [r for r in singles if label(r).lower() == name.lower()]
            loose = [r for r in singles if all(w in label(r).lower() for w in name.lower().split())]
            pick = (exact or loose or [None])[0]
            log("search %-16r -> %d results; picked %s" % (name, len(res), label(pick) if pick else "-"))
            if pick:
                return pick, label(pick)
        return None, None

    def export(self, char, prod, name, inplace):
        _, p = self.req("GET", "/products/%s?similar=0&character_id=%s" % (prod["id"], char))
        gms = dict(p["details"]["gms_hash"])
        gms["params"] = ",".join(str(v[1]) for v in gms.get("params", []))
        if inplace:
            gms["inplace"] = True
        body = {"character_id": char, "gms_hash": [gms], "product_name": name, "type": "Motion",
                "preferences": {"format": "fbx7", "skin": "false", "fps": "30", "reducekf": "0"}}
        self.req("POST", "/animations/export", body)
        t0 = time.time()
        while time.time() - t0 < 240:
            time.sleep(3)
            _, m = self.req("GET", "/characters/%s/monitor" % char)
            st = m.get("status")
            if st == "completed":
                return m["job_result"]
            if st == "failed":
                raise RuntimeError("export failed: %s" % json.dumps(m)[:300])
        raise RuntimeError("export timed out")


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else "mixamo_out")
    os.makedirs(out, exist_ok=True)
    cfg = json.load(open(os.path.join(HERE, "mixamo_clips.json")))
    token = os.environ.get("MIXAMO_TOKEN", "").strip()
    rel = None
    parked = None
    if REPO and GH_TOKEN:
        rel = draft_release()
        if rel is not None and not token:
            parked = release_asset(rel, "mixamo_token.txt")
            if parked:
                token = gh("GET", "/repos/%s/releases/assets/%d" % (REPO, parked["id"]), accept="application/octet-stream").decode().strip()
                log("using the token parked in the private draft release")
    if not token:
        log("No Mixamo token yet. Sign in on mixamo.com, copy localStorage.access_token and add it as the repository secret "
            "MIXAMO_TOKEN (or hand it over to be parked in the private draft release). Nothing to do.")
        return 0
    mx = Mixamo(token)
    char, cname = mx.character(cfg.get("character", ""))
    log("exporting with character %s (%s)" % (char, cname))
    got = []
    for c in cfg["clips"]:
        try:
            prod, name = mx.find(c["names"])
            if prod is None:
                log("!! %s: nothing found for %s" % (c["key"], c["names"]))
                continue
            url = mx.export(char, prod, name, c.get("inplace", False))
            path = os.path.join(out, c["key"] + ".fbx")
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=180) as r:
                open(path, "wb").write(r.read())
            log("%-7s <- Mixamo '%s' (%d KB%s)" % (c["key"], name, os.path.getsize(path) // 1024, ", in place" if c.get("inplace") else ""))
            got.append((c["key"], name, path))
        except SystemExit:
            raise
        except Exception as ex:     # noqa: BLE001
            log("!! %s failed: %s" % (c["key"], ex))
    if not got:
        raise SystemExit("no clip could be downloaded")
    json.dump({k: n for k, n, _ in got}, open(os.path.join(out, "clips.json"), "w"), indent=1)
    if REPO and GH_TOKEN:
        rel = rel or draft_release(create=True)
        for key, _, path in got:
            put_asset(rel, path, key + ".fbx")
        put_asset(rel, os.path.join(out, "clips.json"), "clips.json")
        log("stored %d clips in the private draft release %s" % (len(got), TAG))
        if parked:
            gh("DELETE", "/repos/%s/releases/assets/%d" % (REPO, parked["id"]))
            log("deleted the parked token")
        gh("POST", "/repos/%s/actions/workflows/chaya.yml/dispatches" % REPO, {"ref": os.environ.get("GITHUB_REF_NAME", "chaya")})
        log("started the game build")
    return 0


if __name__ == "__main__":
    sys.exit(main())
