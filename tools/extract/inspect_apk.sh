#!/usr/bin/env bash
# Looks inside the downloaded APK: package, name, version, Unity version, IL2CPP or Mono.
# usage: inspect_apk.sh <work dir>     (reads <work>/input/game.apk, writes <work>/apk_info.json and unpacks to <work>/apk)
set -uo pipefail
W="$1"
APK="$W/input/game.apk"
test -f "$APK" || { echo "::error::$APK not found"; exit 1; }

BT=""
if [ -n "${ANDROID_HOME:-}" ] && [ -d "$ANDROID_HOME/build-tools" ]; then
  BT="$ANDROID_HOME/build-tools/$(ls "$ANDROID_HOME/build-tools" | sort -V | tail -n 1)"
fi
if [ -n "$BT" ] && [ -x "$BT/aapt" ]; then
  "$BT/aapt" dump badging "$APK" > "$W/badging.txt" 2>&1 || true
else
  echo "aapt not available" > "$W/badging.txt"
fi

rm -rf "$W/apk" && mkdir -p "$W/apk"
unzip -oq "$APK" -d "$W/apk" || true
for extra in "$W"/input/*.apk; do
  [ "$extra" = "$APK" ] && continue
  unzip -oq -n "$extra" -d "$W/apk" || true   # split APKs (native libs, assets packs)
done

python3 - "$W" <<'EOF'
import json, mmap, os, re, sys
w = sys.argv[1]
apk = os.path.join(w, "apk")
info = {}
badging = open(os.path.join(w, "badging.txt"), encoding="utf-8", errors="replace").read()
m = re.search(r"package: name='([^']*)' versionCode='([^']*)' versionName='([^']*)'", badging)
if m:
    info.update(package=m.group(1), versionCode=m.group(2), versionName=m.group(3))
for key, pat in (("label", r"application-label:'([^']*)'"), ("minSdk", r"sdkVersion:'([^']*)'"),
                 ("targetSdk", r"targetSdkVersion:'([^']*)'"), ("abis", r"native-code: (.*)"),
                 ("launch_activity", r"launchable-activity: name='([^']*)'")):
    mm = re.search(pat, badging)
    if mm:
        info[key] = mm.group(1).replace("'", "").strip()
libs = {}
for abi in sorted(os.listdir(os.path.join(apk, "lib"))) if os.path.isdir(os.path.join(apk, "lib")) else []:
    libs[abi] = sorted(os.listdir(os.path.join(apk, "lib", abi)))
info["native_libs"] = libs
data = os.path.join(apk, "assets", "bin", "Data")
info["backend"] = ("IL2CPP" if any("libil2cpp.so" in v for v in libs.values())
                   else "Mono" if os.path.exists(os.path.join(data, "Managed", "Assembly-CSharp.dll")) else "unknown")
meta = os.path.join(data, "Managed", "Metadata", "global-metadata.dat")
if os.path.exists(meta):
    with open(meta, "rb") as f:
        head = f.read(8)
    info["il2cpp_metadata"] = {"bytes": os.path.getsize(meta), "magic_ok": head[:4] == b"\xaf\x1b\xb1\xfa",
                               "version": int.from_bytes(head[4:8], "little")}
ver = re.compile(rb"(?<![0-9.])((?:20[12][0-9]|6000)\.[0-9]{1,2}\.[0-9]{1,3}[abfpx][0-9]{1,3}|5\.[0-6]\.[0-9]{1,2}[abfp][0-9]{1,2})")
found = []
cands = [os.path.join(data, n) for n in ("globalgamemanagers", "data.unity3d", "mainData", "level0", "unity default resources")]
cands += [os.path.join(apk, "lib", a, "libunity.so") for a in libs]
for p in cands:
    if not os.path.exists(p) or os.path.getsize(p) == 0:
        continue
    with open(p, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        hit = ver.search(mm[: 1 << 16]) or (ver.search(mm) if p.endswith(".so") else None)
        if hit:
            found.append((os.path.basename(p), hit.group(1).decode()))
info["unity_version_hits"] = found
info["unity_version"] = found[0][1] if found else None
sizes, count = {}, 0
for dp, dn, fn in os.walk(apk):
    for n in fn:
        p = os.path.join(dp, n)
        rel = os.path.relpath(p, apk)
        top = "/".join(rel.split("/")[:3]) if rel.startswith("assets/bin") else rel.split("/")[0]
        sizes[top] = sizes.get(top, 0) + os.path.getsize(p)
        count += 1
info["files"] = count
info["mb_by_folder"] = {k: round(v / 1e6, 2) for k, v in sorted(sizes.items(), key=lambda kv: -kv[1])[:15]}
if os.path.isdir(data):
    info["data_files"] = sorted(os.listdir(data))[:80]
json.dump(info, open(os.path.join(w, "apk_info.json"), "w"), indent=2)
print(json.dumps(info, indent=2))
EOF
