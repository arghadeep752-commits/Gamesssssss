#!/usr/bin/env bash
# Fast compile check (no Unity license needed): compiles the project's scripts with
# Unity 2021.3's own Roslyn compiler and engine reference assemblies, taken from the
# private "unity-kit" draft release. Errors become GitHub annotations.
set -uo pipefail
KIT_DIR="${1:?kit dir}"
PROJ="${2:-$PWD}"
OUT="${RUNNER_TEMP:-/tmp}/compile_out"
mkdir -p "$OUT"
KIT="$KIT_DIR/Data"
export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
DOTNET="$KIT/NetCoreRuntime/dotnet"
CSC="$KIT/DotNetSdkRoslyn/csc.dll"

COMMON="-nologo -nostdlib+ -noconfig -langversion:9.0 -target:library -debug- -nowarn:1701,1702,0169,0414,0649"
REFS="-r:$KIT/NetStandard/ref/2.1.0/netstandard.dll"
for f in "$KIT"/NetStandard/compat/2.1.0/shims/netfx/*.dll "$KIT"/NetStandard/compat/2.1.0/shims/netstandard/*.dll; do REFS="$REFS -r:$f"; done
for f in "$KIT"/Managed/UnityEngine/UnityEngine*.dll; do REFS="$REFS -r:$f"; done

report() {
  # $1 = compiler output file, $2 = assembly name
  python3 - "$1" "$2" "$PROJ" <<'PY'
import re, sys
path, asm, proj = sys.argv[1], sys.argv[2], sys.argv[3].rstrip('/') + '/'
rx = re.compile(r'^(.*?)\((\d+),(\d+)\): (error|warning) (CS\d+): (.*)$')
errors = 0
for line in open(path, errors='replace'):
    line = line.rstrip()
    m = rx.match(line)
    if not m:
        if 'error' in line.lower():
            print(f"::error title={asm}::{line}")
            errors += 1
        continue
    f, ln, col, kind, code, msg = m.groups()
    rel = f.replace(proj, '')
    if kind == 'error':
        errors += 1
        if errors <= 40:
            print(f"::error file={rel},line={ln},col={col},title={code}::{msg}")
    print(f"{rel}({ln},{col}): {kind} {code}: {msg}")
print(f"{asm}: {errors} error(s)")
sys.exit(1 if errors else 0)
PY
}

STATUS=0
find "$KIT/Resources/PackageManager/BuiltInPackages/com.unity.ugui/Runtime" -name "*.cs" > "$OUT/ugui.txt"
"$DOTNET" "$CSC" $COMMON $REFS -define:"UNITY_2021_3_OR_NEWER;UNITY_ANDROID;PACKAGE_PHYSICS;PACKAGE_ANIMATION;PACKAGE_UITOOLKIT" \
  -out:"$OUT/UnityEngine.UI.dll" @"$OUT/ugui.txt" > "$OUT/ugui.log" 2>&1
report "$OUT/ugui.log" "UnityEngine.UI" || { echo "UGUI failed to compile"; cat "$OUT/ugui.log" | tail -20; exit 1; }

DEFINES="UNITY_2021_3_OR_NEWER;UNITY_2021_3;UNITY_ANDROID;ENABLE_IL2CPP;UNITY_5_3_OR_NEWER;UNITY_2017_1_OR_NEWER;UNITY_2019_1_OR_NEWER;UNITY_2020_1_OR_NEWER;UNITY_2021_1_OR_NEWER"
find "$PROJ/Assets" -name "*.cs" -not -path "*/Editor/*" > "$OUT/runtime.txt"
"$DOTNET" "$CSC" $COMMON $REFS -r:"$OUT/UnityEngine.UI.dll" -define:"$DEFINES" \
  -out:"$OUT/Assembly-CSharp.dll" @"$OUT/runtime.txt" > "$OUT/runtime.log" 2>&1
report "$OUT/runtime.log" "Assembly-CSharp" || STATUS=1

if [ $STATUS -eq 0 ]; then
  EDREFS=""
  [ -f "$KIT/PlaybackEngines/AndroidPlayer/UnityEditor.Android.Extensions.dll" ] && EDREFS="-r:$KIT/PlaybackEngines/AndroidPlayer/UnityEditor.Android.Extensions.dll"
  for f in "$KIT"/Managed/UnityEngine/UnityEditor*.dll; do EDREFS="$EDREFS -r:$f"; done
  find "$PROJ/Assets" -path "*/Editor/*" -name "*.cs" > "$OUT/editor.txt"
  "$DOTNET" "$CSC" $COMMON $REFS $EDREFS -r:"$OUT/UnityEngine.UI.dll" -r:"$OUT/Assembly-CSharp.dll" \
    -define:"UNITY_EDITOR;$DEFINES" -out:"$OUT/Assembly-CSharp-Editor.dll" @"$OUT/editor.txt" > "$OUT/editor.log" 2>&1
  report "$OUT/editor.log" "Assembly-CSharp-Editor" || STATUS=1
fi
exit $STATUS
