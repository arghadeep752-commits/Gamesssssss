#!/usr/bin/env bash
# Installs Unity Hub from Unity's apt repository and makes sure it is reachable at
# /opt/unityhub/unityhub, where the unity-setup / activate-unity-license actions look for it.
set -uo pipefail

LOG="$RUNNER_TEMP/hub-install.log"
note() { echo "::notice title=Unity Hub::$1"; }
fail() {
  echo "::error title=Unity Hub install failed::$1%0A$(tail -n 40 "$LOG" | sed 's/%/%25/g' | sed ':a;N;$!ba;s/\n/%0A/g')"
  exit 1
}

{
  set -x
  sudo sh -c 'dbus-uuidgen > /etc/machine-id && mkdir -p /var/lib/dbus/ && ln -sf /etc/machine-id /var/lib/dbus/machine-id'
  wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /usr/share/keyrings/Unity_Technologies_ApS.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" | sudo tee /etc/apt/sources.list.d/unityhub.list
  # Older editors (and the Android NDK r21 toolchain) need a few libraries that only Ubuntu 22.04 ships.
  echo "deb https://archive.ubuntu.com/ubuntu jammy main universe" | sudo tee /etc/apt/sources.list.d/jammy.list
  sudo apt-get update -q
  apt-cache policy unityhub
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends unityhub xvfb libgtk2.0-0 libglu1-mesa libgconf-2-4 libncurses5
  set +x
} >"$LOG" 2>&1 || fail "apt could not install unityhub"

dpkg -L unityhub > "$RUNNER_TEMP/hub-files.txt" 2>/dev/null || true
BIN=$(command -v unityhub || true)
REAL=""
[ -n "$BIN" ] && REAL=$(readlink -f "$BIN")
ASAR=$(grep -m1 "/resources/app.asar$" "$RUNNER_TEMP/hub-files.txt" || true)
ROOT=""
[ -n "$ASAR" ] && ROOT=$(dirname "$(dirname "$ASAR")")
ULC=$(grep -m1 "/Unity.Licensing.Client$" "$RUNNER_TEMP/hub-files.txt" || true)
VER=$(dpkg-query -W -f='${Version}' unityhub 2>/dev/null || echo "?")
note "version=$VER bin=$BIN real=$REAL root=$ROOT licensing=$ULC"

if [ -z "$ROOT" ]; then
  fail "Could not find the Hub's resources/app.asar (bin=$BIN real=$REAL). Files: $(head -c 1500 "$RUNNER_TEMP/hub-files.txt" | tr '\n' ' ')"
fi

EXE="$ROOT/unityhub"
if [ ! -x "$EXE" ]; then
  # Pick the main executable inside the Hub folder
  EXE=$(find "$ROOT" -maxdepth 1 -type f -perm -u+x \( -name "unityhub*" -o -name "Unity*Hub*" \) | grep -v -E "\.so|chrome|crash" | head -1)
fi
[ -z "$EXE" ] && fail "No Hub executable in $ROOT"

if [ "$ROOT" != "/opt/unityhub" ] && [ ! -e /opt/unityhub ]; then
  sudo ln -s "$ROOT" /opt/unityhub
fi
if [ ! -x /opt/unityhub/unityhub ]; then
  sudo ln -sf "$EXE" /opt/unityhub/unityhub
fi
sudo chmod -R a+rwX "$ROOT" || true
ls -la /opt/unityhub/unityhub || fail "/opt/unityhub/unityhub still missing"

# Headless wrapper the actions call on Linux (same as unity-setup's own installer creates).
sudo sed -i 's/^\(.*DISPLAY=:.*XAUTHORITY=.*\)\( "\$@" \)2>&1$/\1\2/' /usr/bin/xvfb-run || true
printf '#!/bin/bash\nxvfb-run --auto-servernum /opt/unityhub/unityhub "$@" 2>/dev/null' | sudo tee /usr/bin/unity-hub >/dev/null
sudo chmod 777 /usr/bin/unity-hub
note "Hub ready at /opt/unityhub (real root $ROOT, exe $EXE)"
