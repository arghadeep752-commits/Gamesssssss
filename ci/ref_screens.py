#!/usr/bin/env python3
"""Reference only: the store screenshots of the original game, so the in-game controls can be laid out the same way.

They are never put into the game or published as pictures. They are encrypted with the public key in ci/ref_pub.pem
(the matching private key exists only in the Claude session that made it) and attached to the CI release as
ref_screens.tar.

    python3 ci/ref_screens.py ci/ref_pub.pem OUT.tar
"""
import os
import re
import subprocess
import sys
import tempfile
import urllib.request

APP = "com.LackopsGames.DinoTerror"
UA = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return r.read()


def main():
    pub, out = sys.argv[1], sys.argv[2]
    page = get("https://play.google.com/store/apps/details?id=%s&hl=en&gl=US" % APP).decode("utf-8", "replace")
    urls = []
    for m in re.finditer(r"https://play-lh\.googleusercontent\.com/[A-Za-z0-9_\-]{20,}", page):
        u = m.group(0)
        if u not in urls:
            urls.append(u)
    print("store images found:", len(urls))
    tmp = tempfile.mkdtemp(prefix="ref_")
    shots = os.path.join(tmp, "shots")
    os.makedirs(shots)
    n = 0
    for u in urls[:24]:
        try:
            data = get(u + "=w1600-h900")
        except Exception as e:      # noqa: BLE001
            print("  skip", e)
            continue
        if len(data) < 15000:       # icons and badges
            continue
        n += 1
        open(os.path.join(shots, "shot_%02d.jpg" % n), "wb").write(data)
    print("screenshots kept:", n)
    if not n:
        return 1
    subprocess.run(["tar", "-cf", os.path.join(tmp, "shots.tar"), "-C", shots, "."], check=True)
    key = os.path.join(tmp, "k.txt")
    subprocess.run(["openssl", "rand", "-hex", "-out", key, "32"], check=True)
    subprocess.run(["openssl", "pkeyutl", "-encrypt", "-pubin", "-inkey", pub, "-pkeyopt", "rsa_padding_mode:oaep",
                    "-pkeyopt", "rsa_oaep_md:sha256", "-in", key, "-out", os.path.join(tmp, "k.enc")], check=True)
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-salt", "-in", os.path.join(tmp, "shots.tar"),
                    "-out", os.path.join(tmp, "shots.enc"), "-pass", "file:" + key], check=True)
    subprocess.run(["tar", "-cf", os.path.abspath(out), "-C", tmp, "k.enc", "shots.enc"], check=True)
    print("wrote", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
