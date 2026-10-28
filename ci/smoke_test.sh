#!/usr/bin/env bash
# Installs the APK in the emulator, plays a few seconds with simulated touches and
# saves screenshots + a filtered logcat to the output folder.
set -uo pipefail
OUT="${1:-smoke}"
mkdir -p "$OUT"
PKG="com.zombiestrike.fps"
APK=$(ls "$OUT"/*.apk | head -1)

shot() { adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null; echo "screenshot $1"; }
alive() { adb shell pidof "$PKG" >/dev/null 2>&1; }

adb logcat -c || true
echo "Installing $APK"
adb install -r -g "$APK" 2>&1 | tail -2
adb shell settings put system accelerometer_rotation 0 || true
adb shell monkey -p "$PKG" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1

# Wait until the game has drawn its first frames (it logs "ZS-LAYOUT" on frame 3).
READY=0
for i in $(seq 1 120); do
  if adb logcat -d -s Unity:V 2>/dev/null | grep -q "ZS-LAYOUT"; then READY=1; break; fi
  sleep 2
done
echo "ready=$READY after ~$((i*2))s"
sleep 4
shot 01-menu

LAYOUT=$(adb logcat -d -s Unity:V 2>/dev/null | grep -o "ZS-LAYOUT.*" | tail -1)
echo "layout: $LAYOUT"
# ZS-LAYOUT w=.. h=.. play=x,y fire=x,y joy=x,y reload=x,y  (Unity coords, origin bottom-left)
val() { echo "$LAYOUT" | grep -o "$1=[0-9.,-]*" | head -1 | cut -d= -f2; }
W=$(val w); H=$(val h)
pt() { local v; v=$(val "$1"); local x=${v%,*}; local y=${v#*,}; echo "${x%.*} $(( H - ${y%.*} ))"; }

if [ -n "$W" ] && [ -n "$H" ]; then
  read PX PY < <(pt play)
  read FX FY < <(pt fire)
  read JX JY < <(pt joy)
  echo "tap PLAY at $PX,$PY"
  adb shell input tap "$PX" "$PY"
  sleep 4
  shot 02-playing
  # look around (swipe on the right half)
  adb shell input swipe $((W*3/4)) $((H/2)) $((W*3/4 - W/6)) $((H/2)) 700
  sleep 1
  shot 03-look-left
  # walk forward with the joystick while firing
  adb shell input swipe "$JX" "$JY" "$JX" $((JY - H/6)) 3500 &
  sleep 1
  adb shell input swipe "$FX" "$FY" "$FX" "$FY" 1800 &
  sleep 0.6
  shot 04-move-fire
  wait
  sleep 8
  shot 05-zombies-coming
  # look around in quarter turns to find the zombies
  Q=$((H / 2))
  for k in 1 2 3; do
    adb shell input swipe $((W*3/4)) $((H/2)) $((W*3/4 - Q)) $((H/2)) 600
    sleep 1.5
    shot "06-look-$k"
  done
  adb shell input swipe "$FX" "$FY" "$FX" "$FY" 3000 &
  sleep 1.2
  shot 07-shooting
  wait
  sleep 10
  shot 08-later
else
  echo "No layout reported by the game"
fi

if alive; then echo "alive=yes" > "$OUT/result.txt"; else echo "alive=no" > "$OUT/result.txt"; fi
adb logcat -d 2>/dev/null | grep -E "Unity|ZS-|AndroidRuntime|FATAL|CRASH|libc|DEBUG" | tail -400 > "$OUT/logcat.txt" || true
cat "$OUT/result.txt"
exit 0
