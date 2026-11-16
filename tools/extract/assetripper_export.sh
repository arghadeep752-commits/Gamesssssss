#!/usr/bin/env bash
# Exports the game with AssetRipper (github.com/AssetRipper/AssetRipper, free edition) without a screen:
# starts its local web app with --headless and drives it with the same form posts its buttons send.
#   1. a Unity project (scenes, meshes, materials, textures, sounds, scripts)  -> <out>/unity
#   2. "primary content": every scene and model as .glb, textures as .png     -> <out>/primary
# usage: assetripper_export.sh <apk file or folder of apks> <out dir>
set -euo pipefail
IN="$(realpath "$1")"
OUT="$(realpath -m "$2")"
mkdir -p "$OUT" ~/assetripper
cd ~/assetripper
if [ ! -x ./bin/AssetRipper.GUI.Free ]; then
  rm -rf dl bin && mkdir -p dl bin
  gh release download -R AssetRipper/AssetRipper --pattern '*linux_x64*' --dir dl
  f="$(ls dl | head -n 1)"
  echo "AssetRipper package: $f ($(gh release view -R AssetRipper/AssetRipper --json tagName --jq .tagName))"
  case "$f" in
    *.zip) unzip -oq "dl/$f" -d bin ;;
    *.tar.xz) tar -xJf "dl/$f" -C bin ;;
    *.tar.gz|*.tgz) tar -xzf "dl/$f" -C bin ;;
    *) echo "::error::unknown AssetRipper package $f"; exit 1 ;;
  esac
  exe="$(find bin -type f -name AssetRipper.GUI.Free | head -n 1)"
  if [ "$exe" != "bin/AssetRipper.GUI.Free" ]; then
    d="$(dirname "$exe")"; mv "$d"/* bin/ 2>/dev/null || true
  fi
  chmod +x bin/AssetRipper.GUI.Free
fi

PORT=8899
./bin/AssetRipper.GUI.Free --headless --port $PORT > "$OUT/assetripper_console.log" 2>&1 &
PID=$!
trap 'kill $PID 2>/dev/null || true' EXIT
for i in $(seq 1 120); do
  if curl -fs -o /dev/null "http://127.0.0.1:$PORT/"; then break; fi
  if ! kill -0 $PID 2>/dev/null; then echo "::error::AssetRipper stopped"; tail -n 40 "$OUT/assetripper_console.log"; exit 1; fi
  sleep 2
done
echo "AssetRipper is running on port $PORT"

post() {  # post <endpoint> <path>
  local t0=$SECONDS code
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 5400 --data-urlencode "Path=$2" "http://127.0.0.1:$PORT$1")
  echo "$1 -> HTTP $code in $((SECONDS - t0)) s"
  case "$code" in 2*|3*) ;; *) tail -n 60 "$OUT/assetripper_console.log"; exit 1 ;; esac
}

if [ -d "$IN" ]; then post /LoadFolder "$IN"; else post /LoadFile "$IN"; fi
post /Export/UnityProject "$OUT/unity"
post /Export/PrimaryContent "$OUT/primary"

echo "---- AssetRipper log (warnings and errors) ----"
grep -E "Warning|Error|Exception" "$OUT/assetripper_console.log" | sort | uniq -c | sort -rn | head -n 40 || true
echo "---- exported ----"
du -sh "$OUT/unity" "$OUT/primary" 2>/dev/null || true
find "$OUT/unity" -maxdepth 3 -type d | head -n 40
