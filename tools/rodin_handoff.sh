#!/usr/bin/env bash
# Session side of the Hyper3D handoff (see tools/rodin_fetch.py): encrypt the temporary download links with the
# public key a running build published, so only that build can read them.
#   tools/rodin_handoff.sh PUBLIC_KEY.pem URLS.json OUT.tar
set -euo pipefail
PUB="$1"; URLS="$2"; OUT="$3"
T="$(mktemp -d)"
openssl rand -hex 32 > "$T/k.txt"
openssl pkeyutl -encrypt -pubin -inkey "$PUB" -pkeyopt rsa_padding_mode:oaep -pkeyopt rsa_oaep_md:sha256 \
  -in "$T/k.txt" -out "$T/k.enc"
openssl enc -aes-256-cbc -pbkdf2 -iter 100000 -salt -in "$URLS" -out "$T/urls.enc" -pass "file:$T/k.txt"
tar -cf "$OUT" -C "$T" k.enc urls.enc
rm -rf "$T"
echo "wrote $OUT"
