#!/usr/bin/env bash
# Installs the APK in the emulator, starts it with the automated screenshot tour
# (intent extra rf_tour) and saves a screenshot each time the game reports a view
# ("[RF] TOUR shot <n> <name>"), then a short touch-control test and a filtered logcat.
set -uo pipefail
OUT="${1:-smoke}"
mkdir -p "$OUT"
PKG="com.silentvalley.fps"
APK=$(ls "$OUT"/*.apk | head -1)

alive() { timeout 20 adb shell pidof "$PKG" >/dev/null 2>&1; }
shot() { timeout 60 adb exec-out screencap -p > "$OUT/$1.png" 2>/dev/null; echo "screenshot $1 ($(date +%T))"; }

adb logcat -c || true
echo "Installing $APK"
adb install -r -g "$APK" 2>&1 | tail -2
adb shell settings put system accelerometer_rotation 0 || true
adb shell am start -n "$PKG/com.unity3d.player.UnityPlayerActivity" -e rf_tour 1 >/dev/null 2>&1

dump() { timeout 60 adb logcat -d 2>/dev/null | grep -E "Unity|RF|AndroidRuntime|FATAL|CRASH|libc|DEBUG|ActivityManager" | tail -800 > "$OUT/logcat.txt" || true; }

taken=""
start=$(date +%s)
lastdump=$start
periodic=0
while true; do
  now=$(date +%s)
  if [ $((now - start)) -gt 1260 ]; then echo "tour timeout"; shot "zz-timeout"; break; fi
  if [ $((now - lastdump)) -ge 120 ]; then
    lastdump=$now; periodic=$((periodic + 1)); dump
    # a periodic screenshot only while no tour shot has arrived yet in this window
    shot "p$(printf '%02d' $periodic)-periodic"
  fi
  log=$(timeout 30 adb logcat -d -s Unity:V 2>/dev/null)
  while read -r line; do
    n=$(echo "$line" | sed -n 's/.*TOUR shot \([0-9]*\) \([A-Za-z_]*\).*/\1/p')
    name=$(echo "$line" | sed -n 's/.*TOUR shot \([0-9]*\) \([A-Za-z_]*\).*/\2/p')
    [ -z "$n" ] && continue
    case " $taken " in *" $n "*) continue ;; esac
    taken="$taken $n"
    shot "$(printf '%02d' "$n")-$name"
    echo "$line" | grep -o "TOUR shot.*" >> "$OUT/tour.txt"
  done < <(echo "$log" | grep "TOUR shot")
  if echo "$log" | grep -q "TOUR done"; then echo "tour finished"; break; fi
  if [ $(( (now - start) % 60 )) -lt 3 ]; then echo "waiting... $((now - start))s, shots:$taken"; echo "$log" | grep -E "\[RF\]|Exception|Error" | tail -3; fi
  if ! alive; then echo "app died"; break; fi
  sleep 2
done

if alive; then echo "alive=yes" > "$OUT/result.txt"; else echo "alive=no" > "$OUT/result.txt"; fi
dump
cat "$OUT/result.txt"
exit 0
