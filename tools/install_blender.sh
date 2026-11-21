#!/usr/bin/env bash
set -e
if [ ! -x ~/blender/blender ]; then
  mkdir -p ~/blender && cd ~/blender
  V=$BLENDER_VERSION; S=${V%.*}
  for u in https://download.blender.org/release/Blender$S/blender-$V-linux-x64.tar.xz \
           https://mirrors.ocf.berkeley.edu/blender/release/Blender$S/blender-$V-linux-x64.tar.xz; do
    curl -fsSL --retry 3 --max-time 900 "$u" -o b.tar.xz && break || rm -f b.tar.xz
  done
  tar -xJf b.tar.xz --strip-components=1 && rm -f b.tar.xz
fi
if ! ~/blender/blender -b --version >/dev/null 2>&1; then
  sudo apt-get update -qq || true
  sudo apt-get install -y -qq --no-install-recommends libxi6 libxxf86vm1 libxfixes3 libxrender1 libxkbcommon0 libgl1 libsm6 libegl1
fi
~/blender/blender -b --version | head -2
