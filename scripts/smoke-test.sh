#!/usr/bin/env bash
# CI smoke test on an Android emulator: installs Calc Pro, taps through a few
# calculations and saves screenshots, a short screen recording and the log.
# Usage: bash scripts/smoke-test.sh path/to/app.apk
set -u
APK="${1:-android/app/build/outputs/apk/release/app-release.apk}"
PKG=com.calcpro.app
OUT=smoke
mkdir -p "$OUT"
: > "$OUT/steps.txt"

log() { echo "[smoke] $*"; echo "$*" >> "$OUT/steps.txt"; }

# 0 turns system animations off (the app then also pauses its own), 1 turns them on.
animations() {
  for k in window_animation_scale transition_animation_scale animator_duration_scale; do
    adb shell settings put global "$k" "$1"
  done
}

# Reads every on-screen element with an accessibility label and its centre.
dump_ui() {
  for _ in 1 2 3 4; do
    if adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1 &&
      adb pull /sdcard/ui.xml "$OUT/ui.xml" >/dev/null 2>&1 &&
      python3 scripts/ui_coords.py "$OUT/ui.xml" > "$OUT/coords.txt" &&
      [ -s "$OUT/coords.txt" ]; then
      return 0
    fi
    sleep 2
  done
  log "ui dump failed"
  return 1
}

tap() {
  local xy
  xy=$(awk -F'\t' -v k="$1" '$1 == k { p = $2 " " $3 } END { if (p) print p }' "$OUT/coords.txt" 2>/dev/null)
  if [ -z "$xy" ]; then
    log "key not found: $1"
    return 1
  fi
  # shellcheck disable=SC2086
  adb shell input tap $xy
  sleep "${2:-0.35}"
}

shot() {
  adb exec-out screencap -p > "$OUT/$1.png"
  log "screenshot $1"
}

log "installing $APK"
adb install -r "$APK" || { log "INSTALL FAILED"; exit 1; }
adb logcat -c

animations 0
adb shell am start -W -n "$PKG/.MainActivity"
sleep 12
dump_ui
animations 1
sleep 4
shot 01-start

adb shell screenrecord --time-limit 16 --bit-rate 6000000 /sdcard/demo.mp4 &
REC=$!
sleep 1
for k in 1 2 5 0; do tap "$k"; done
tap Multiply 1.5
shot 02-operator
for k in 1 2; do tap "$k"; done
tap Equals 1.5
shot 03-result
for k in 4 8 7 5 0; do tap "$k" 0.25; done
tap Multiply 0.4
for k in 1 2; do tap "$k" 0.25; done
tap Plus 0.4
for k in 2 5 0 0; do tap "$k" 0.25; done
sleep 1
shot 04-typing
wait "$REC" 2>/dev/null
sleep 1
adb pull /sdcard/demo.mp4 "$OUT/demo.mp4" >/dev/null 2>&1 || log "no screen recording"

tap "Scientific keys" 1.5
animations 0
sleep 1
dump_ui
animations 1
sleep 2
tap Clear 0.4
tap Sine 0.4
tap 3 0.3
tap 0 0.3
tap "Close parenthesis" 0.3
tap Plus 0.3
tap Pi 0.3
tap Equals 1.5
shot 05-scientific

adb shell cmd uimode night yes
sleep 4
shot 06-dark

animations 0
sleep 1
dump_ui
animations 1
sleep 1
tap Settings 2
shot 07-settings

adb logcat -d > "$OUT/logcat.txt"
adb logcat -d -s ReactNativeJS:V ReactNative:V AndroidRuntime:E > "$OUT/logcat-react.txt"

STATUS=0
if grep -q "FATAL EXCEPTION" "$OUT/logcat.txt"; then
  log "CRASH: see logcat.txt"
  grep -A40 "FATAL EXCEPTION" "$OUT/logcat.txt" | head -80
  STATUS=1
fi
if [ -z "$(adb shell pidof "$PKG" | tr -d '\r')" ]; then
  log "app is not running at the end"
  STATUS=1
fi
if [ "$STATUS" -eq 0 ]; then log "PASS"; else log "FAIL"; fi
exit "$STATUS"
