#!/usr/bin/env bash
# Installs Unity Hub from Unity's official apt repository (the editor itself is installed by unity-setup).
set -euo pipefail

if [ -x /opt/unityhub/unityhub ] || command -v unityhub >/dev/null 2>&1; then
  echo "Unity Hub is already installed"
  exit 0
fi

sudo install -d -m 0755 /usr/share/keyrings
wget -qO - https://hub.unity3d.com/linux/keys/public | gpg --dearmor | sudo tee /usr/share/keyrings/Unity_Technologies_ApS.gpg >/dev/null
echo "deb [signed-by=/usr/share/keyrings/Unity_Technologies_ApS.gpg] https://hub.unity3d.com/linux/repos/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/unityhub.list >/dev/null
sudo apt-get update -qq
sudo apt-get install -y -qq unityhub
ls -la /opt/unityhub/unityhub
