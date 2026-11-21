#!/usr/bin/env python3
"""Small GitHub Releases helper for the trailer workflows (stdlib only).

Usage:
  ghrel.py upload  <tag> <dir_or_file>... [--public] [--title T] [--notes N]
  ghrel.py download <tag> <dest_dir> [prefix1,prefix2,...]
  ghrel.py publish <tag> --title T --notes-file F
Env: GITHUB_TOKEN, GITHUB_REPOSITORY
"""
import json, os, sys, time, mimetypes, urllib.request, urllib.error, urllib.parse

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "arghadeep752-commits/gamesssssss")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
BRANCH = "mahabharata-trailer"


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_noredir = urllib.request.build_opener(_NoRedirect)


def _req(method, url, data=None, headers=None, raw=False, auth=True, timeout=900):
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if auth and TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    if headers:
        h.update(headers)
    if data is not None and not isinstance(data, (bytes, bytearray)):
        data = json.dumps(data).encode()
        h["Content-Type"] = "application/json"
    last = None
    for attempt in range(6):
        r = urllib.request.Request(url, data=data, method=method, headers=h)
        try:
            with urllib.request.urlopen(r, timeout=timeout) as resp:
                b = resp.read()
                if raw:
                    return b
                return json.loads(b) if b else None
        except urllib.error.HTTPError as e:
            body = e.read()[:400]
            last = f"{method} {url.split('?')[0]} -> {e.code} {body!r}"
            if e.code in (429, 500, 502, 503, 504) and attempt < 5:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(last)
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last = f"{method} {url.split('?')[0]} -> {e}"
            if attempt < 5:
                time.sleep(5 * (attempt + 1))
                continue
            raise RuntimeError(last)
    raise RuntimeError(last)


def releases():
    out, page = [], 1
    while True:
        rs = _req("GET", f"{API}/repos/{REPO}/releases?per_page=100&page={page}")
        out += rs
        if len(rs) < 100:
            return out
        page += 1


def find(tag):
    for r in releases():
        if r["tag_name"] == tag:
            return r
    return None


def ensure(tag, title=None, notes="", draft=True):
    r = find(tag)
    if r:
        return r
    return _req("POST", f"{API}/repos/{REPO}/releases", {
        "tag_name": tag, "name": title or tag, "body": notes, "draft": draft,
        "prerelease": False, "target_commitish": BRANCH})


def assets(rel):
    out, page = [], 1
    while True:
        a = _req("GET", f"{API}/repos/{REPO}/releases/{rel['id']}/assets?per_page=100&page={page}")
        out += a
        if len(a) < 100:
            return out
        page += 1


def upload_file(rel, path, existing):
    name = os.path.basename(path)
    for a in existing:
        if a["name"] == name:
            _req("DELETE", f"{API}/repos/{REPO}/releases/assets/{a['id']}")
    ctype = mimetypes.guess_type(name)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        data = f.read()
    url = f"https://uploads.github.com/repos/{REPO}/releases/{rel['id']}/assets?name={urllib.parse.quote(name)}"
    res = _req("POST", url, data, {"Content-Type": ctype})
    print(f"uploaded {name} ({len(data)/1e6:.1f} MB)", flush=True)
    return res


def download_asset(a, dest):
    url = f"{API}/repos/{REPO}/releases/assets/{a['id']}"
    h = {"Accept": "application/octet-stream", "X-GitHub-Api-Version": "2022-11-28"}
    if TOKEN:
        h["Authorization"] = f"Bearer {TOKEN}"
    loc = None
    for attempt in range(6):
        try:
            try:
                with _noredir.open(urllib.request.Request(url, headers=h), timeout=120) as resp:
                    data = resp.read()
                    open(dest, "wb").write(data)
                    return
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    loc = e.headers["Location"]
                else:
                    raise
            tmp = dest + ".part"
            with urllib.request.urlopen(urllib.request.Request(loc), timeout=900) as resp, open(tmp, "wb") as f:
                while True:
                    chunk = resp.read(1 << 22)
                    if not chunk:
                        break
                    f.write(chunk)
            os.replace(tmp, dest)
            return
        except Exception as e:  # noqa
            if attempt == 5:
                raise
            print(f"retry {a['name']}: {e}", flush=True)
            time.sleep(5 * (attempt + 1))


def main():
    cmd = sys.argv[1]
    if cmd == "upload":
        args = sys.argv[2:]
        tag = args.pop(0)
        public = "--public" in args
        title = notes = None
        if "--title" in args:
            i = args.index("--title"); title = args[i + 1]; del args[i:i + 2]
        if "--notes" in args:
            i = args.index("--notes"); notes = args[i + 1]; del args[i:i + 2]
        args = [a for a in args if a != "--public"]
        rel = ensure(tag, title or tag, notes or "", draft=not public)
        if title or notes:
            patch = {}
            if title:
                patch["name"] = title
            if notes:
                patch["body"] = notes
            rel = _req("PATCH", f"{API}/repos/{REPO}/releases/{rel['id']}", patch)
        existing = assets(rel)
        files = []
        for p in args:
            if os.path.isdir(p):
                files += [os.path.join(p, f) for f in sorted(os.listdir(p)) if os.path.isfile(os.path.join(p, f))]
            else:
                files.append(p)
        for f in files:
            upload_file(rel, f, existing)
        if public and rel.get("draft"):
            _req("PATCH", f"{API}/repos/{REPO}/releases/{rel['id']}", {"draft": False})
    elif cmd == "download":
        tag, dest = sys.argv[2], sys.argv[3]
        prefixes = sys.argv[4].split(",") if len(sys.argv) > 4 and sys.argv[4] else None
        os.makedirs(dest, exist_ok=True)
        rel = find(tag)
        if not rel:
            raise SystemExit(f"release {tag} not found")
        for a in assets(rel):
            if prefixes and not any(a["name"].startswith(p) for p in prefixes):
                continue
            out = os.path.join(dest, a["name"])
            if os.path.exists(out) and os.path.getsize(out) == a["size"]:
                continue
            download_asset(a, out)
            print(f"downloaded {a['name']} ({a['size']/1e6:.1f} MB)", flush=True)
    elif cmd == "publish":
        args = sys.argv[2:]
        tag = args.pop(0)
        i = args.index("--title"); title = args[i + 1]
        j = args.index("--notes-file"); notes = open(args[j + 1]).read()
        rel = ensure(tag, title, notes, draft=False)
        _req("PATCH", f"{API}/repos/{REPO}/releases/{rel['id']}", {"name": title, "body": notes, "draft": False})
    else:
        raise SystemExit("unknown command")


if __name__ == "__main__":
    main()
