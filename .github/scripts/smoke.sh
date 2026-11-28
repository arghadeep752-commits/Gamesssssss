#!/usr/bin/env bash
# Installs the QA build on the emulator, walks through the main screens and some
# dense levels, and saves screenshots, frame stats and the device log to smoke-out/.
# Fails if the app crashes or logs a JavaScript error.
set -u
APK="$1"
PKG=com.arghadeepdas.arrowflow
OUT=smoke-out
W=720
H=1600
mkdir -p "$OUT"
log() { echo "[smoke] $*"; }
shot() { adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null; log "shot $1"; }
dump() { adb shell uiautomator dump /sdcard/ui.xml >/dev/null 2>&1; adb pull /sdcard/ui.xml "$OUT/ui.xml" >/dev/null 2>&1; }
tap() { adb shell input tap "$1" "$2"; }
tapq() {
  local xy=""
  for attempt in 1 2 3; do
    dump
    xy=$(python3 .github/scripts/find.py "$OUT/ui.xml" "$1")
    [ -n "$xy" ] && break
    sleep 1
  done
  if [ -n "$xy" ]; then
    # shellcheck disable=SC2086
    tap $xy
    log "tapped '$1' at $xy"
    return 0
  fi
  log "not found: $1"
  return 1
}
grid_taps() { # $1 = pause between taps
  for fy in 30 38 46 54 62 70; do
    for fx in 14 28 42 56 70 84; do
      tap $((W * fx / 100)) $((H * fy / 100))
      sleep "$1"
    done
  done
}

adb wait-for-device
adb shell wm size ${W}x${H}
adb shell wm density 280
adb install -r "$APK" > "$OUT/install.txt" 2>&1 || { log "install failed"; cat "$OUT/install.txt"; exit 1; }
adb logcat -c

adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 15
shot 01-launch
tapq "Claim*" && sleep 2 && shot 02-reward-claimed
tapq "Play level*" || tapq "Play"
sleep 4
shot 03-level1
grid_taps 0.5
shot 04-level1-tapped
sleep 2
shot 05-win
tapq "Next level" && sleep 3 && shot 06-level2
grid_taps 0.4
sleep 2
shot 07-level2-tapped
adb shell input keyevent 4
sleep 2
shot 08-home
tapq "Daily" && sleep 2 && shot 09-daily
tapq "Trophies" && sleep 2 && shot 11-trophies
tapq "Home" && sleep 2
tapq "Settings" && sleep 2 && shot 12-settings
tapq "Privacy Policy" && sleep 2 && shot 13-privacy
adb shell input keyevent 4
sleep 2
tapq "*open shop" && sleep 2 && shot 14-shop
adb shell input keyevent 4
sleep 1

for L in 25 90 300; do
  adb shell am start -W -a android.intent.action.VIEW -d "arrowflow://qa?level=$L" "$PKG" >/dev/null 2>&1
  sleep 7
  shot "20-level$L"
  tapq "Zoom in" && sleep 1 && tapq "Zoom in" && sleep 1 && shot "22-level$L-zoomed"
  tapq "Grid lines" && sleep 1 && shot "23-level$L-grid" && tapq "Grid lines"
  tapq "Zoom out" && sleep 1 && tapq "Zoom out" && sleep 1
  adb shell dumpsys gfxinfo "$PKG" reset >/dev/null 2>&1
  grid_taps 0.25
  sleep 1
  shot "21-level$L-tapped"
  adb shell dumpsys gfxinfo "$PKG" > "$OUT/gfx-level$L.txt" 2>&1
  adb shell input keyevent 4
  sleep 2
done

# Dark mode
tapq "Settings" && sleep 1 && tapq "Dark mode" && sleep 1 && adb shell input keyevent 4 && sleep 1
adb shell am start -W -a android.intent.action.VIEW -d "arrowflow://qa?level=60" "$PKG" >/dev/null 2>&1
sleep 6
shot 30-dark-level60

adb logcat -d > "$OUT/logcat.txt" 2>&1
grep -E "FATAL EXCEPTION|AndroidRuntime: FATAL|ReactNativeJS: .*(Error|Exception)|JavascriptException|SoLoader.*error|ANR in com\.arghadeepdas" "$OUT/logcat.txt" > "$OUT/errors.txt" || true
# Animations updating views that are already gone: a few at mount are harmless, a flood freezes the app.
STALE=$(grep -c "synchronouslyUpdateUIProps failed" "$OUT/logcat.txt" || true)
log "stale view updates: $STALE"
if [ "${STALE:-0}" -gt 200 ]; then
  echo "too many stale view updates: $STALE" >> "$OUT/errors.txt"
fi
if ! adb shell pidof "$PKG" >/dev/null 2>&1; then
  log "app is not running at the end"
  echo "app not running at end" >> "$OUT/errors.txt"
fi
grep -h -E "Total frames rendered|Janky frames" "$OUT"/gfx-*.txt || true
if [ -s "$OUT/errors.txt" ]; then
  log "errors found:"
  head -60 "$OUT/errors.txt"
  exit 1
fi
log "smoke test passed"
