#!/usr/bin/env bash
# Unity 2021.3's bundled .NET 5 (used to compile scripts) needs OpenSSL 1.1, which Ubuntu 24.04 lacks.
set -euo pipefail
if ldconfig -p | grep -q "libssl.so.1.1"; then
  echo "OpenSSL 1.1 already installed"
  exit 0
fi
URL="https://archive.ubuntu.com/ubuntu/pool/main/o/openssl/libssl1.1_1.1.0g-2ubuntu4_amd64.deb"
wget -q -O "$RUNNER_TEMP/libssl1.1.deb" "$URL"
sudo dpkg -i "$RUNNER_TEMP/libssl1.1.deb"
ldconfig -p | grep "libssl.so.1.1"
