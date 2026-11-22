#!/usr/bin/env bash
# Runs the emulator build of the Godot version, waits for its built-in check (menus, the city, driving, the boat,
# the helicopter, night, the police) and collects the screenshots and the log into <dir>/out.
set -u
DIR="${1:-smoke}"
PKG="com.mxyangames.dangagodot"
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
adb shell screenrecord --time-limit 30 --size 1110x540 --bit-rate 4000000 /sdcard/start.mp4 >/dev/null 2>&1 &
rec=$!
sleep 1
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
( for t in 4 8 12 16 20; do sleep 4; adb exec-out screencap -p > "$OUT/00-start-${t}s.png" 2>/dev/null || true; done ) &
starts=$!

result="TIMEOUT"
captured=" "
for _ in $(seq 1 1200); do
  sleep 0.5
  glog="$(adb logcat -d -s godot 2>/dev/null)"
  # the game holds the picture for a few seconds after each "SNAP <name>" line: take the screenshot now
  for name in $(echo "$glog" | grep -o "\[DG-TEST\] SNAP [A-Za-z0-9_-]*" | awk '{print $3}'); do
    case "$captured" in
      *" $name "*) ;;
      *) adb exec-out screencap -p > "$OUT/$name.png" 2>/dev/null; captured="$captured$name "; echo "captured $name";;
    esac
  done
  if echo "$glog" | grep -q "\[DG-TEST\] DONE"; then result="DONE"; break; fi
  if adb logcat -d 2>/dev/null | grep -qE "Fatal signal|Process $PKG .*has died|ANR in $PKG"; then result="CRASH"; break; fi
done
sleep 2
wait $starts 2>/dev/null || true
wait $rec 2>/dev/null || true
adb pull /sdcard/start.mp4 "$OUT/00-start.mp4" >/dev/null 2>&1 && ls -la "$OUT/00-start.mp4" || echo "no start recording"

adb logcat -d > "$OUT/logcat-full.log" 2>/dev/null || true
grep -E "godot|DG-TEST|AndroidRuntime|DEBUG|libc|$PKG" "$OUT/logcat-full.log" | tail -n 4000 > "$OUT/logcat-godot.txt" || true
grep "DG-TEST" "$OUT/logcat-full.log" > "$OUT/test-result.txt" || true
grep -E "SCRIPT ERROR|ERROR:" "$OUT/logcat-full.log" | sort | uniq -c | sort -rn | head -n 40 >> "$OUT/test-result.txt" || true
echo "RESULT: $result" >> "$OUT/test-result.txt"
adb exec-out screencap -p > "$OUT/zz-emulator-screen.png" 2>/dev/null || true

cat "$OUT/test-result.txt"
ls -la "$OUT" 2>/dev/null || true
[ "$result" = "DONE" ]
