#!/usr/bin/env bash
# Prepares Unity Hub for RageAgainstThePixel/unity-setup on Ubuntu 24.04.
# Installs the same packages and the same `unity-hub` xvfb wrapper the action would install itself,
# and exposes Hub 3.20+ (which lives in /usr/lib/unityhub) at /opt/unityhub, where the action looks.
set -euo pipefail

sudo sh -c 'dbus-uuidgen > /etc/machine-id && mkdir -p /var/lib/dbus && ln -sf /etc/machine-id /var/lib/dbus/machine-id' || true
sudo install -d -m 0755 /usr/share/keyrings
wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /usr/share/keyrings/Unity_Technologies_ApS.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/unityhub.list >/dev/null
# libgconf-2-4 and libncurses5 only exist in jammy
echo "deb https://archive.ubuntu.com/ubuntu jammy main universe" | sudo tee /etc/apt/sources.list.d/jammy.list >/dev/null
# Unity Hub 4 changed its layout and unity-setup no longer finds it: keep the 3.x Hub that works (3.22.6),
# pinned so that unity-setup's own "apt-get install unityhub" leaves it alone
printf 'Package: unityhub\nPin: version 3.22.*\nPin-Priority: 1001\n' | sudo tee /etc/apt/preferences.d/unityhub >/dev/null
sudo apt-get update -qq
apt-cache madison unityhub | head -n 8 || true
sudo apt-get install -y -qq --no-install-recommends --allow-downgrades \
  unityhub xvfb ffmpeg libgtk2.0-0 libglu1-mesa libgconf-2-4 libncurses5 pulseaudio
if ! dpkg -s unityhub 2>/dev/null | grep -q '^Version: 3\.'; then
  v3="$(apt-cache madison unityhub | awk '{print $3}' | grep '^3\.' | head -n 1)"
  echo "pinned Hub not installed, trying $v3"
  printf 'Package: unityhub\nPin: version %s\nPin-Priority: 1001\n' "$v3" | sudo tee /etc/apt/preferences.d/unityhub >/dev/null
  sudo apt-get install -y -qq --no-install-recommends --allow-downgrades "unityhub=$v3"
fi
dpkg -s unityhub | grep '^Version'
# keep the Hub's error output out of its normal output (the action parses stdout)
sudo sed -i 's/^\(.*DISPLAY=:.*XAUTHORITY=.*\)\( "\$@" \)2>&1$/\1\2/' /usr/bin/xvfb-run

# find the Hub launcher (Hub 3.20+: /usr/lib/unityhub/unityhub, older: /opt/unityhub/unityhub)
hub=""
resolved="$(readlink -f "$(command -v unityhub 2>/dev/null)" 2>/dev/null || true)"
for c in "$resolved" /usr/lib/unityhub/unityhub /opt/unityhub/unityhub; do
  if [ -n "$c" ] && [ -f "$c" ] && [ -x "$c" ]; then hub="$c"; break; fi
done
if [ -z "$hub" ]; then
  echo "::error::Unity Hub was installed but its launcher was not found"
  dpkg -L unityhub | head -n 60
  exit 1
fi
echo "Unity Hub launcher: $hub (version $(cat "$(dirname "$hub")/version" 2>/dev/null || echo unknown))"

real_dir="$(dirname "$hub")"
if [ ! -e /opt/unityhub/resources ]; then
  sudo rm -rf /opt/unityhub
  sudo ln -sfn "$real_dir" /opt/unityhub
  echo "linked /opt/unityhub -> $real_dir"
fi

# the command unity-setup runs on Linux: the Hub on a virtual display
printf '#!/bin/bash\nxvfb-run --auto-servernum /opt/unityhub/unityhub "$@" 2>/dev/null\n' | sudo tee /usr/bin/unity-hub >/dev/null
sudo chmod 755 /usr/bin/unity-hub

echo "UNITY_HUB_PATH=$hub" >> "${GITHUB_ENV:-/dev/null}"
ls -la /opt/unityhub/ | head -n 8
cat /usr/bin/unity-hub
