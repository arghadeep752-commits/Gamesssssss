#!/usr/bin/env bash
# Emulator smoke test for one installed APK. Fails if the app crashes or dies.
#
#   smoke-test.sh <apk> <package> <user|admin> <out-dir>
#
# User app: launches, visits every tab, and — when the backend has published
# wallpapers — opens one and really sets it as Home + Lock wallpaper, then checks
# with `dumpsys wallpaper` that the system wallpaper changed.
# Admin app: launches and checks the sign-in gate renders.
set -uo pipefail

APK="${1:?apk}"
PKG="${2:?package}"
APP="${3:?app}"
OUT="${4:?out dir}"
HERE="$(cd "$(dirname "$0")" && pwd)"
UI="python3 $HERE/ui.py"
mkdir -p "$OUT"
RESULTS="$OUT/results.md"
: > "$RESULTS"
step=0

note() { echo "- $*" | tee -a "$RESULTS"; }
shot() {
  step=$((step + 1))
  local file
  file="$(printf '%02d' "$step")-$1.png"
  adb exec-out screencap -p > "$OUT/$file" 2>/dev/null || true
  echo "  screenshot: $file" >> "$RESULTS"
}
alive() { adb shell pidof "$PKG" >/dev/null 2>&1; }
# Ids of the current system and lock wallpapers; they change whenever one is set.
wallpaper_state() { adb shell dumpsys wallpaper 2>/dev/null | grep -E 'mWallpaperId|id=' | head -n 6 | tr -d '\r'; }
crashed() { adb logcat -d -b crash 2>/dev/null | grep -q "$PKG"; }
fail() {
  note "FAILED: $*"
  echo "::error title=Smoke test ($APP)::$*"
  shot failure
  adb logcat -d > "$OUT/logcat.txt" 2>/dev/null || true
  exit 1
}

adb wait-for-device
adb shell 'while [ "$(getprop sys.boot_completed)" != "1" ]; do sleep 1; done'
adb shell input keyevent 82 >/dev/null 2>&1 || true
adb shell settings put global window_animation_scale 0 >/dev/null 2>&1 || true
adb shell settings put global transition_animation_scale 0 >/dev/null 2>&1 || true
adb shell settings put global animator_duration_scale 0 >/dev/null 2>&1 || true
# Let the launcher finish starting (slow software-rendered emulators otherwise raise
# "isn't responding" dialogs over the app), then clear any system dialogs.
sleep 20
adb shell am broadcast -a android.intent.action.CLOSE_SYSTEM_DIALOGS >/dev/null 2>&1 || true

note "Device: $(adb shell getprop ro.product.model | tr -d '\r') · Android $(adb shell getprop ro.build.version.release | tr -d '\r') (API $(adb shell getprop ro.build.version.sdk | tr -d '\r'))"
adb install -r -g "$APK" > "$OUT/install.txt" 2>&1 || fail "install: $(cat "$OUT/install.txt")"
note "Installed $(basename "$APK")"
adb logcat -c || true

START=$(date +%s%3N)
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || fail "launch"
for _ in $(seq 1 30); do alive && break; sleep 0.5; done
sleep 12
alive || fail "process died after launch"
crashed && fail "crash during startup"
note "Launched and still running after 12 s (process started in $(( $(date +%s%3N) - START )) ms incl. install wait)"
shot launch

if [ "$APP" = "user" ]; then
  if $UI has-text "Almost ready" || $UI has-text "Device self-test"; then
    note "Build is not connected to Firebase yet: the 'Almost ready' gate is shown (expected for test builds)"

    # Device self-test: the app sets a generated image on Home + Lock, saves it to the
    # gallery and opens the share sheet; each result is then checked from outside the app.
    before="$(wallpaper_state)"
    found=""
    for _ in 1 2 3; do
      if $UI tap-id self-test-run; then found=yes; break; fi
      adb shell input swipe 540 1800 540 700 300; sleep 1
    done
    [ -n "$found" ] || fail "device self-test button not found"
    result=""
    for _ in $(seq 1 45); do
      sleep 1
      if $UI has-text "Self-test passed"; then result=passed; break; fi
      if $UI has-text "Self-test failed"; then result=failed; break; fi
    done
    $UI dump "$OUT/self-test.xml" >/dev/null 2>&1 || true
    checks="$(python3 - "$OUT/self-test.xml" <<'PY' 2>/dev/null || true
import sys, xml.etree.ElementTree as ET
try:
    root = ET.parse(sys.argv[1]).getroot()
except Exception:
    sys.exit(0)
print("; ".join(n.get("text") for n in root.iter("node") if n.get("text", "").startswith(("\u2713", "\u2717"))))
PY
)"
    shot self-test
    [ "$result" = "passed" ] || fail "device self-test ${result:-gave no result}: $checks"
    note "In-app self-test passed: $checks"

    after="$(wallpaper_state)"
    if [ -n "$after" ] && [ "$before" != "$after" ]; then
      note "WallpaperManager state changed (dumpsys wallpaper ids before: $(echo $before) → after: $(echo $after))"
    else
      fail "dumpsys wallpaper shows no change after the self-test (before: $(echo $before); after: $(echo $after))"
    fi

    saved="$(adb shell ls /sdcard/Pictures/DevDarshan/ 2>/dev/null | tr -d '\r' | grep 'DevDarshan-selftest-' | head -n1)"
    [ -n "$saved" ] || fail "the saved image is not in Pictures/DevDarshan"
    note "Gallery: Pictures/DevDarshan/$saved exists"
    indexed="$(adb shell "content query --uri content://media/external/images/media --projection _display_name:relative_path --where \"_display_name='$saved'\"" 2>/dev/null | tr -d '\r' | head -n1)"
    [ -n "$indexed" ] && note "MediaStore: $indexed"

    $UI tap-id self-test-share || fail "share button not found"
    top=""
    for _ in $(seq 1 10); do
      sleep 1
      top="$(adb shell dumpsys activity activities 2>/dev/null | grep -E 'topResumedActivity|mResumedActivity' | head -n1 | tr -d '\r')"
      echo "$top" | grep -qiE 'chooser|resolver' && break
    done
    shot share-sheet
    echo "$top" | grep -qiE 'chooser|resolver' || fail "the share sheet did not open (top activity: $top)"
    note "Share sheet opened: $(echo "$top" | sed 's/^ *//')"
    adb shell input keyevent 4; sleep 2
    alive || fail "app died after closing the share sheet"

    adb shell input keyevent 3; sleep 2; shot home-screen-wallpaper
    adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; sleep 3
  else
    for tab in Categories Liked Profile Home; do
      if $UI tap-text "$tab"; then
        sleep 4
        alive || fail "crashed after opening $tab"
        note "Opened tab: $tab"
        shot "tab-$tab"
      else
        fail "tab '$tab' not found"
      fi
    done

    if title="$($UI tap-first-image)"; then
      sleep 5
      alive || fail "crashed opening a wallpaper"
      note "Opened wallpaper preview: $title"
      shot preview
      before="$(wallpaper_state)"
      if $UI tap-id preview-set-wallpaper; then
        sleep 2
        shot set-sheet
        $UI tap-id set-both || fail "'Both Screens' option not found"
        confirmed=""
        for _ in $(seq 1 60); do
          sleep 1
          if $UI has-text "Set on" --contains || $UI has-text "wallpaper set" --contains; then confirmed=yes; break; fi
        done
        shot after-set
        after="$(wallpaper_state)"
        alive || fail "crashed while setting the wallpaper"
        [ -n "$confirmed" ] && note "App confirmed: $($UI has-text 'Set on' --contains >/dev/null && echo 'Set on Home and Lock screen' || echo 'wallpaper set')"
        if [ -n "$after" ] && [ "$before" != "$after" ]; then
          note "WallpaperManager state changed (dumpsys wallpaper ids before: $(echo $before | tr '\n' ' ') → after: $(echo $after | tr '\n' ' '))"
        elif [ -z "$after" ]; then
          [ -n "$confirmed" ] || fail "no confirmation and wallpaper state unreadable"
          note "dumpsys wallpaper not readable on this image; relying on the in-app confirmation"
        else
          fail "wallpaper state did not change after 'Set on Both Screens'"
        fi
        adb shell input keyevent 3; sleep 2; shot home-screen-wallpaper
        adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1; sleep 3
      fi
    else
      note "No published wallpapers yet: skipped the set-wallpaper check"
    fi
  fi
else
  if $UI has-text "Sign in with Google" --contains || $UI has-text "Almost ready"; then
    note "Admin sign-in gate rendered"
  else
    fail "admin sign-in screen not found"
  fi
fi

sleep 2
alive || fail "process died at the end of the run"
crashed && fail "crash recorded in the crash buffer"
adb logcat -d > "$OUT/logcat.txt" 2>/dev/null || true
note "PASSED: no crashes"
echo "::notice title=Smoke test ($APP)::passed"
exit 0
