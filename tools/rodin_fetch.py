#!/usr/bin/env python3
"""Bring the Hyper3D (Rodin) models listed in tools/school/rodin_models.json into the build.

The raw .glb files are kept on the `ragini-ci` release as rodin_raw.zip, so normally this only downloads that zip.
When models are missing, their temporary download links have to come from the Hyper3D connector, which only the
person's Claude session can call. Those links must not be published, so they are handed over encrypted:

  1. this job makes an RSA key pair and puts the PUBLIC key on the release (rodin_pub_<run id>.pem);
  2. the session encrypts the links with that key and pushes the ciphertext to the `rodin-handoff` branch
     as handoff/<run id>.tar (pushes of handoff/ files do not start builds);
  3. this job decrypts it with the private key, which never leaves this machine, downloads the models,
     and updates rodin_raw.zip.
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
REPO = os.environ.get("GITHUB_REPOSITORY", "arghadeep752-commits/gamesssssss")
RUN = os.environ.get("GITHUB_RUN_ID", "local")
OUT = os.path.join(ROOT, "build", "rodin", "raw")
WAIT_MIN = float(os.environ.get("RODIN_WAIT_MIN", "40"))


def sh(*cmd, check=True, capture=False, inp=None):
    r = subprocess.run(cmd, check=check, capture_output=capture, input=inp)
    return r.stdout if capture else r.returncode


def log(*a):
    print(*a, flush=True)


def main():
    manifest = json.load(open(os.path.join(ROOT, "tools", "school", "rodin_models.json")))["models"]
    os.makedirs(OUT, exist_ok=True)
    zpath = os.path.join(ROOT, "build", "rodin_raw.zip")
    if sh("curl", "-fsSL", "-o", zpath, "https://github.com/%s/releases/download/ragini-ci/rodin_raw.zip" % REPO, check=False) == 0:
        with zipfile.ZipFile(zpath) as z:
            z.extractall(OUT)
    have = {f[:-4] for f in os.listdir(OUT) if f.endswith(".glb")}
    want = {"%s__%s" % (k, v["gen"]): (k, v["gen"]) for k, v in manifest.items()}
    missing = {n: kg for n, kg in want.items() if n not in have}
    log("hyper3d models: %d wanted, %d already on the release, %d missing" % (len(want), len(want) - len(missing), len(missing)))
    if not missing:
        return 0

    tmp = tempfile.mkdtemp(prefix="rodin_")
    priv, pub = os.path.join(tmp, "priv.pem"), os.path.join(tmp, "rodin_pub_%s.pem" % RUN)
    sh("openssl", "genpkey", "-algorithm", "RSA", "-pkeyopt", "rsa_keygen_bits:3072", "-out", priv)
    sh("openssl", "pkey", "-in", priv, "-pubout", "-out", pub)
    sh("gh", "release", "upload", "ragini-ci", pub, "-R", REPO, "--clobber")
    log("public key published as %s - waiting for the encrypted download links" % os.path.basename(pub))

    blob = None
    t0 = time.time()
    while time.time() - t0 < WAIT_MIN * 60:
        out = subprocess.run(["gh", "api", "repos/%s/contents/handoff/%s.tar?ref=rodin-handoff" % (REPO, RUN), "-q", ".content"],
                             capture_output=True, text=True)
        if out.returncode == 0 and out.stdout.strip():
            blob = base64.b64decode("".join(out.stdout.split()))
            break
        time.sleep(10)
    sh("gh", "release", "delete-asset", "ragini-ci", os.path.basename(pub), "-R", REPO, "-y", check=False)
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
    urls = json.load(open(os.path.join(tmp, "urls.json")))      # {generation id: signed url}
    os.remove(os.path.join(tmp, "urls.json"))
    got = 0
    for name, (kind, gen) in sorted(missing.items()):
        u = urls.get(gen)
        if not u:
            log("  %-15s no link (not finished yet?)" % kind)
            continue
        dst = os.path.join(OUT, name + ".glb")
        ok = False
        for k in range(3):
            if sh("curl", "-fsSL", "--retry", "2", "-o", dst, u, check=False) == 0 and os.path.getsize(dst) > 1000:
                ok = True
                break
            time.sleep(3)
        log("  %-15s %s" % (kind, ("%.1f MB" % (os.path.getsize(dst) / 1e6)) if ok else "DOWNLOAD FAILED"))
        got += ok
    if got:
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
            for f in sorted(os.listdir(OUT)):
                if f.endswith(".glb"):
                    z.write(os.path.join(OUT, f), f)
        sh("gh", "release", "upload", "ragini-ci", zpath, "-R", REPO, "--clobber")
        log("rodin_raw.zip updated (%d models)" % len([f for f in os.listdir(OUT) if f.endswith(".glb")]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
