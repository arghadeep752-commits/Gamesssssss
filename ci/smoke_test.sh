#!/usr/bin/env bash
# Runs the emulator build of the game, waits for its built-in check (menus, the house, the trader, the PC, a chase,
# being caught, the pause menu) and collects the screenshots and the Unity log into <dir>/out.
set -u
DIR="${1:-smoke}"
PKG="com.anomynousdevs.tradersmadness"
OUT="$DIR/out"
mkdir -p "$OUT"

APK="$(ls "$DIR"/*.apk 2>/dev/null | head -n 1)"
if [ -z "$APK" ]; then
  echo "No APK found in $DIR" | tee "$OUT/test-result.txt"
  exit 1
fi

adb wait-for-device
adb shell input keyevent 82 >/dev/null 2>&1 || true
echo "Installing $APK"
adb install -r -g "$APK" 2>&1 | tee "$OUT/install.txt"
adb logcat -c || true
# record the first seconds after launch (the Unity splash plays there)
adb shell screenrecord --time-limit 25 --size 1110x540 --bit-rate 4000000 /sdcard/start.mp4 >/dev/null 2>&1 &
rec=$!
sleep 1
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
for t in 3 6 9 12; do
  sleep 3
  adb exec-out screencap -p > "$OUT/00-start-${t}s.png" 2>/dev/null || true
done
wait $rec 2>/dev/null || true
sleep 2
adb pull /sdcard/start.mp4 "$OUT/00-start.mp4" >/dev/null 2>&1 && ls -la "$OUT/00-start.mp4" || echo "no start recording"

result="TIMEOUT"
captured=" "
for _ in $(seq 1 600); do
  sleep 1
  ulog="$(adb logcat -d -s Unity 2>/dev/null)"
  # the game holds the picture for 3 s after each "SNAP <name>" line: take the screenshot now
  for name in $(echo "$ulog" | grep -o "\[TM-TEST\] SNAP [A-Za-z0-9_-]*" | awk '{print $3}'); do
    case "$captured" in
      *" $name "*) ;;
      *) adb exec-out screencap -p > "$OUT/$name.png" 2>/dev/null; captured="$captured$name "; echo "captured $name";;
    esac
  done
  if echo "$ulog" | grep -q "\[TM-TEST\] DONE"; then result="DONE"; break; fi
  if adb logcat -d 2>/dev/null | grep -qE "Fatal signal|Process $PKG .*has died|ANR in $PKG"; then result="CRASH"; break; fi
done
sleep 2

# the game saves its own exact screenshots (shot_<name>.png): they replace the screen grabs, which can lag behind
mkdir -p "$OUT/game"
dir="$(adb logcat -d -s Unity 2>/dev/null | grep -o 'files go to [^ ]*' | tail -n 1 | awk '{print $4}' | tr -d '\r')"
[ -z "$dir" ] && dir="/sdcard/Android/data/$PKG/files"
echo "game files in: $dir"
adb shell ls -la "$dir" 2>&1 | head -n 40
adb pull "$dir/." "$OUT/game/" 2>&1 | tail -n 3 || true
if ! ls "$OUT"/game/shot_*.png >/dev/null 2>&1; then
  # the app's private folder: copy out through a shell the app can read
  for f in $(adb shell ls "$dir" 2>/dev/null | tr -d '\r' | grep '^shot_'); do
    adb exec-out cat "$dir/$f" > "$OUT/game/$f" 2>/dev/null || true
  done
fi
n=0
for f in $(find "$OUT/game" -name 'shot_*.png'); do mv -f "$f" "$OUT/$(basename "$f" | sed 's/^shot_//')"; n=$((n+1)); done
echo "game screenshots: $n"
rm -rf "$OUT/game"
adb logcat -d > "$OUT/logcat-full.log" 2>/dev/null || true
grep -E "Unity|TM|AndroidRuntime|DEBUG|libc|$PKG" "$OUT/logcat-full.log" | tail -n 4000 > "$OUT/logcat-unity.txt" || true
grep "TM-TEST" "$OUT/logcat-full.log" > "$OUT/test-result.txt" || true
echo "RESULT: $result" >> "$OUT/test-result.txt"
adb exec-out screencap -p > "$OUT/zz-emulator-screen.png" 2>/dev/null || true

cat "$OUT/test-result.txt"
ls -la "$OUT" 2>/dev/null || true
[ "$result" = "DONE" ]
