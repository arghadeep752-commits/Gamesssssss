#!/usr/bin/env python3
"""Bring the Hyper3D (Rodin) models listed in tools/rodin/models.json into the build.

The raw .glb files are kept on the `danga-ci` release as rodin_raw.zip, so normally this only downloads that zip.
When models are missing, their temporary download links have to come from the Hyper3D connector, which only the
person's Claude session can call. Those links must not be published, so they are handed over encrypted:

  1. this job makes an RSA key pair and puts the PUBLIC key on the release (rodin_pub_<run id>.pem);
  2. the session encrypts the links with that key and pushes the ciphertext to the `danga-handoff` branch as
     handoff/<run id>.tar;
  3. this job decrypts it with the private key, which never leaves this machine, downloads the models and updates
     rodin_raw.zip  on the release.

    python3 tools/rodin_fetch.py OUT_DIR        (OUT_DIR gets <name>__<gen>.glb)
"""
import base64
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.environ.get("GITHUB_REPOSITORY", "arghadeep752-commits/Gamesssssss")
RUN = os.environ.get("GITHUB_RUN_ID", "local")
TAG = os.environ.get("CI_RELEASE", "danga-ci")
HANDOFF = os.environ.get("HANDOFF_BRANCH", "danga-handoff")
WAIT_MIN = float(os.environ.get("RODIN_WAIT_MIN", "45"))


def sh(*cmd, check=True, capture=False):
    r = subprocess.run(cmd, check=check, capture_output=capture)
    return r.stdout if capture else r.returncode


def log(*a):
    print(*a, flush=True)


def release_assets():
    out = subprocess.run(["gh", "release", "view", TAG, "-R", REPO, "--json", "assets", "-q", ".assets[].name"],
                         capture_output=True, text=True)
    return set(out.stdout.split()) if out.returncode == 0 else set()


def fetch(url, dst):
    for _ in range(3):
        if sh("curl", "-fsSL", "--retry", "2", "-o", dst, url, check=False) == 0 and os.path.getsize(dst) > 1000:
            return True
        time.sleep(3)
    return False


def main():
    out_dir = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "build", "rodin", "raw"))
    os.makedirs(out_dir, exist_ok=True)
    man = json.load(open(os.path.join(ROOT, "tools", "rodin", "models.json")))
    models = man["models"]
    rigged = man.get("rigged", {})
    zpath = os.path.join(tempfile.gettempdir(), "rodin_raw.zip")
    base = "https://github.com/%s/releases/download/%s/" % (REPO, TAG)
    if sh("curl", "-fsSL", "-o", zpath, base + "rodin_raw.zip", check=False) == 0:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(out_dir)
    for name in rigged:
        p = os.path.join(out_dir, name)
        if not os.path.exists(p):
            sh("curl", "-fsSL", "-o", p, base + name, check=False)
            if os.path.exists(p) and os.path.getsize(p) < 1000:
                os.remove(p)
    have = {f[:-4] for f in os.listdir(out_dir) if f.endswith(".glb")}
    want = {"%s__%s" % (k, v["gen"]): v["gen"] for k, v in models.items()}
    missing = {n: g for n, g in want.items() if n not in have}
    rig_missing = {n: v["gen"] for n, v in rigged.items() if not os.path.exists(os.path.join(out_dir, n))}
    log("hyper3d models: %d wanted, %d here, %d missing; rigged missing: %s" % (len(want), len(want) - len(missing), len(missing),
                                                                                 sorted(rig_missing)))
    if not missing and not rig_missing:
        return 0
    if os.environ.get("RODIN_NO_WAIT"):
        log("not waiting for download links (RODIN_NO_WAIT)")
        return 0
    tmp = tempfile.mkdtemp(prefix="rodin_")
    priv, pub = os.path.join(tmp, "priv.pem"), os.path.join(tmp, "rodin_pub_%s.pem" % RUN)
    sh("openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", priv)
    sh("openssl", "pkey", "-in", priv, "-pubout", "-out", pub)
    sh("gh", "release", "upload", TAG, pub, "-R", REPO, "--clobber")
    log("public key published as %s - waiting for the encrypted download links (handoff/%s.tar on %s)" % (os.path.basename(pub), RUN, HANDOFF))
    blob = None
    t0 = time.time()
    while time.time() - t0 < WAIT_MIN * 60:
        r = subprocess.run(["gh", "api", "repos/%s/contents/handoff/%s.tar?ref=%s" % (REPO, RUN, HANDOFF), "-q", ".content"],
                           capture_output=True, text=True)
        if r.returncode == 0 and r.stdout.strip():
            blob = base64.b64decode("".join(r.stdout.split()))
            break
        time.sleep(10)
    sh("gh", "release", "delete-asset", TAG, os.path.basename(pub), "-R", REPO, "-y", check=False)
    if blob is None:
        log("no download links arrived - building with the models already on the release")
        return 0
    bundle = os.path.join(tmp, "bundle.tar")
    open(bundle, "wb").write(blob)
    sh("tar", "-xf", bundle, "-C", tmp)
    sh("openssl", "pkeyutl", "-decrypt", "-inkey", priv, "-pkeyopt", "rsa_padding_mode:oaep", "-pkeyopt", "rsa_oaep_md:sha256",
       "-in", os.path.join(tmp, "k.enc"), "-out", os.path.join(tmp, "k.txt"))
    sh("openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-in", os.path.join(tmp, "urls.enc"),
       "-out", os.path.join(tmp, "urls.json"), "-pass", "file:" + os.path.join(tmp, "k.txt"))
    urls = json.load(open(os.path.join(tmp, "urls.json")))       # {generation id: signed url, "file:<name>": url}
    os.remove(os.path.join(tmp, "urls.json"))
    got = 0
    for name, gen in sorted(missing.items()):
        u = urls.get(gen)
        if not u:
            log("  %-28s no link" % name)
            continue
        dst = os.path.join(out_dir, name + ".glb")
        ok = fetch(u, dst)
        log("  %-28s %s" % (name, ("%.1f MB" % (os.path.getsize(dst) / 1e6)) if ok else "DOWNLOAD FAILED"))
        got += ok
    for name in sorted(rig_missing):
        u = urls.get("file:" + name)
        if not u:
            log("  %-28s no link" % name)
            continue
        dst = os.path.join(out_dir, name)
        ok = fetch(u, dst)
        log("  %-28s %s" % (name, ("%.1f MB" % (os.path.getsize(dst) / 1e6)) if ok else "DOWNLOAD FAILED"))
        if ok:
            sh("gh", "release", "upload", TAG, dst, "-R", REPO, "--clobber")
    if got:
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
            for f in sorted(os.listdir(out_dir)):
                if f.endswith(".glb") and "__" in f:
                    z.write(os.path.join(out_dir, f), f)
        sh("gh", "release", "upload", TAG, zpath, "-R", REPO, "--clobber")
        log("rodin_raw.zip updated (%d models)" % len([f for f in os.listdir(out_dir) if "__" in f]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
