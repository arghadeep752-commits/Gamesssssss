#!/usr/bin/env bash
# Installs Unity Hub from Unity's official apt repository (the editor itself is installed by unity-setup)
# and makes sure it can be found at /opt/unityhub/unityhub, where tools expect it.
set -uo pipefail

if ! dpkg -s unityhub >/dev/null 2>&1; then
  sudo install -d -m 0755 /usr/share/keyrings
  wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /usr/share/keyrings/Unity_Technologies_ApS.gpg >/dev/null
  echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" \
    | sudo tee /etc/apt/sources.list.d/unityhub.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq unityhub || exit 1
fi

echo "Unity Hub package files (executables):"
dpkg -L unityhub | while read -r f; do
  if [ -f "$f" ] && [ -x "$f" ]; then echo "  $f"; fi
done | head -n 40

hub=""
resolved="$(readlink -f "$(command -v unityhub 2>/dev/null)" 2>/dev/null || true)"
for c in "$resolved" /opt/unityhub/unityhub /opt/unityhub/unityhub-bin; do
  if [ -n "$c" ] && [ -f "$c" ] && [ -x "$c" ]; then hub="$c"; break; fi
done
if [ -z "$hub" ]; then
  hub="$(dpkg -L unityhub | grep -E '/unityhub(-bin)?$' | while read -r f; do
    if [ -f "$f" ] && [ -x "$f" ]; then echo "$f"; break; fi
  done)"
fi

if [ -z "$hub" ]; then
  echo "::warning::Unity Hub is installed but its executable was not found; unity-setup will try on its own"
  exit 0
fi

echo "Unity Hub executable: $hub ($(file -b "$hub" 2>/dev/null | cut -c1-60))"
if head -c 2 "$hub" 2>/dev/null | grep -q '#!'; then head -n 20 "$hub"; fi
# Hub 3.22+ installs to /usr/lib/unityhub; tools still look in /opt/unityhub (executable + resources/app.asar)
real_dir="$(dirname "$hub")"
if [ ! -e /opt/unityhub/resources ]; then
  sudo rm -rf /opt/unityhub
  sudo ln -sfn "$real_dir" /opt/unityhub
  echo "linked /opt/unityhub -> $real_dir"
fi
echo "UNITY_HUB_PATH=$hub" >> "${GITHUB_ENV:-/dev/null}"
ls -la /opt/unityhub/ | head -n 20
