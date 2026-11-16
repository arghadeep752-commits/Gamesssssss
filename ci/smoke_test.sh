#!/usr/bin/env bash
# Runs the emulator build of the game, waits for its built-in check (the menu, then a camera walk through every room of the house)
# and collects the screenshots and the Unity log into <dir>/out.
set -u
DIR="${1:-smoke}"
PKG="com.anomynousdevs.grannydimnight"
OUT="$DIR/out"
mkdir -p "$OUT"

APK="$(ls "$DIR"/*.apk 2>/dev/null | head -n 1)"
if [ -z "$APK" ]; then
  echo "No APK found in $DIR" | tee "$OUT/test-result.txt"
  exit 1
fi

# every adb call gets a time limit: a stuck emulator must not stall the whole check
A() { timeout "${T:-25}" adb "$@"; }
echo "RESULT: RUNNING" > "$OUT/test-result.txt"
START=$(date +%s)
adb wait-for-device
A shell input keyevent 82 >/dev/null 2>&1 || true
echo "Installing $APK"
T=300 A install -r -g "$APK" 2>&1 | tee "$OUT/install.txt"
A logcat -c || true
# the whole Unity log streams to a file from here on, so it survives even if the emulator freezes later
timeout 1800 adb logcat -v time > "$OUT/logcat-stream.txt" 2>&1 &
logpid=$!
# record the first seconds after launch (the Unity splash plays there)
T=40 A shell screenrecord --time-limit 25 --size 1110x540 --bit-rate 4000000 /sdcard/start.mp4 >/dev/null 2>&1 &
rec=$!
sleep 1
A shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
for t in 3 6 9 12; do
  sleep 3
  A exec-out screencap -p > "$OUT/00-start-${t}s.png" 2>/dev/null || true
done
wait $rec 2>/dev/null || true
sleep 2
T=60 A pull /sdcard/start.mp4 "$OUT/00-start.mp4" >/dev/null 2>&1 && ls -la "$OUT/00-start.mp4" || echo "no start recording"

result="TIMEOUT"
captured=" "
while [ $(( $(date +%s) - START )) -lt 1200 ]; do
  sleep 1
  ulog="$(grep -a "DIMNIGHT-TEST" "$OUT/logcat-stream.txt" 2>/dev/null)"
  # the game holds the picture for 3 s after each "SNAP <name>" line: take the screenshot now
  for name in $(echo "$ulog" | grep -o "\[DIMNIGHT-TEST\] SNAP [A-Za-z0-9_-]*" | awk '{print $3}'); do
    case "$captured" in
      *" $name "*) ;;
      *) A exec-out screencap -p > "$OUT/$name.png" 2>/dev/null; captured="$captured$name "; echo "captured $name $(date +%T)";;
    esac
  done
  na=$(echo "$ulog" | grep -c "alive:")
  if [ "$na" != "${pa:-0}" ]; then echo "$ulog" | grep "alive:" | tail -n 1; pa=$na; fi
  if echo "$ulog" | grep -q "\[DIMNIGHT-TEST\] DONE"; then result="DONE"; break; fi
  if grep -aqE "Fatal signal|Process $PKG .*has died|ANR in $PKG" "$OUT/logcat-stream.txt" 2>/dev/null; then result="CRASH"; break; fi
done
sleep 2

# the game saves its own exact screenshots (shot_<name>.png): they replace the screen grabs, which can lag behind
mkdir -p "$OUT/game"
dir="$(grep -ao 'files go to [^ ]*' "$OUT/logcat-stream.txt" 2>/dev/null | tail -n 1 | awk '{print $4}' | tr -d '\r')"
[ -z "$dir" ] && dir="/sdcard/Android/data/$PKG/files"
echo "game files in: $dir"
A shell ls -la "$dir" 2>&1 | head -n 40
T=120 A pull "$dir/." "$OUT/game/" 2>&1 | tail -n 3 || true
if ! ls "$OUT"/game/shot_*.png >/dev/null 2>&1; then
  # the app's private folder: copy out through a shell the app can read
  for f in $(A shell ls "$dir" 2>/dev/null | tr -d '\r' | grep '^shot_'); do
    A exec-out cat "$dir/$f" > "$OUT/game/$f" 2>/dev/null || true
  done
fi
n=0
for f in $(find "$OUT/game" -name 'shot_*.png'); do mv -f "$f" "$OUT/$(basename "$f" | sed 's/^shot_//')"; n=$((n+1)); done
echo "game screenshots: $n"
rm -rf "$OUT/game"
kill $logpid 2>/dev/null || true
cp "$OUT/logcat-stream.txt" "$OUT/logcat-full.log" 2>/dev/null || true
grep -aE "Unity|DIMNIGHT|AndroidRuntime|DEBUG|libc|lowmemory|lmkd|ActivityManager|$PKG" "$OUT/logcat-full.log" | tail -n 6000 > "$OUT/logcat-unity.txt" || true
grep -a "DIMNIGHT-TEST" "$OUT/logcat-full.log" > "$OUT/test-result.txt" || true
echo "RESULT: $result" >> "$OUT/test-result.txt"
A exec-out screencap -p > "$OUT/zz-emulator-screen.png" 2>/dev/null || true

cat "$OUT/test-result.txt"
ls -la "$OUT" 2>/dev/null || true
[ "$result" = "DONE" ]
