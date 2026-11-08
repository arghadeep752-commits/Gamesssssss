#!/usr/bin/env bash
# Runs the emulator build of the game, waits for its built-in auto test (walk around, open the door,
# open the pause menu) and collects the screenshots and the Unity log into <dir>/out.
set -u
DIR="${1:-smoke}"
PKG="com.gridprototype.fps"
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
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1

result="TIMEOUT"
captured=" "
for _ in $(seq 1 220); do
  sleep 1
  ulog="$(adb logcat -d -s Unity 2>/dev/null)"
  # the game freezes for 3 s after each "SNAP <name>" line: take the screenshot now
  for name in $(echo "$ulog" | grep -o "\[PROTO-TEST\] SNAP [A-Za-z0-9_-]*" | awk '{print $3}'); do
    case "$captured" in
      *" $name "*) ;;
      *) adb exec-out screencap -p > "$OUT/$name.png" 2>/dev/null; captured="$captured$name "; echo "captured $name";;
    esac
  done
  if echo "$ulog" | grep -q "\[PROTO-TEST\] DONE"; then result="DONE"; break; fi
  if adb logcat -d 2>/dev/null | grep -qE "Fatal signal|Process $PKG .*has died|ANR in $PKG"; then result="CRASH"; break; fi
done
sleep 2

adb logcat -d > "$OUT/logcat-full.log" 2>/dev/null || true
grep -E "Unity|PROTO|GridProto|AndroidRuntime|DEBUG|libc|$PKG" "$OUT/logcat-full.log" | tail -n 4000 > "$OUT/logcat-unity.txt" || true
grep "PROTO-TEST" "$OUT/logcat-full.log" > "$OUT/test-result.txt" || true
echo "RESULT: $result" >> "$OUT/test-result.txt"

adb exec-out screencap -p > "$OUT/zz-emulator-screen.png" 2>/dev/null || true

cat "$OUT/test-result.txt"
ls -la "$OUT" "$OUT/autotest" 2>/dev/null || true
[ "$result" = "DONE" ]
