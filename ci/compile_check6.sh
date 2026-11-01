#!/usr/bin/env bash
# Fast compile check (no Unity license needed): compiles the project's scripts with
# Unity 6's own Roslyn compiler against the engine, URP and uGUI assemblies from the
# private "unity6-kit" draft release. Errors become GitHub annotations.
# Usage: ci/compile_check6.sh <kit_dir> [project_dir]
set -uo pipefail
KIT_DIR="${1:?kit dir}"
PROJ="${2:-$PWD}"
OUT="${RUNNER_TEMP:-/tmp}/rf_compile_out6"
mkdir -p "$OUT"
DATA="$KIT_DIR/Editor/Data"
ASM="$KIT_DIR/Project/ScriptAssemblies"
export DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=1
export DOTNET_CLI_TELEMETRY_OPTOUT=1
DOTNET="$DATA/NetCoreRuntime/dotnet"
CSC="$DATA/DotNetSdkRoslyn/csc.dll"

COMMON="-nologo -nostdlib+ -noconfig -langversion:9.0 -target:library -debug- -nowarn:1701,1702,0169,0414,0649,0618"
REFS="-r:$DATA/NetStandard/ref/2.1.0/netstandard.dll"
for f in "$DATA"/NetStandard/compat/2.1.0/shims/netfx/*.dll "$DATA"/NetStandard/compat/2.1.0/shims/netstandard/*.dll; do [ -e "$f" ] && REFS="$REFS -r:$f"; done
for f in "$DATA"/Managed/UnityEngine/UnityEngine*.dll; do REFS="$REFS -r:$f"; done
if ! ls "$ASM"/*.dll >/dev/null 2>&1; then
  echo "::warning title=Compile check skipped::The compile kit has no compiled package assemblies; the full build will check the code instead."
  exit 0
fi
RUNTIME_PKGS=""
EDITOR_PKGS=""
for f in "$ASM"/*.dll; do
  n=$(basename "$f")
  case "$n" in
    Assembly-CSharp*) ;;
    *Editor*|*editor*|UnityEditor.*) EDITOR_PKGS="$EDITOR_PKGS -r:$f" ;;
    *Tests*|*nunit*|*NUnit*) ;;
    *) RUNTIME_PKGS="$RUNTIME_PKGS -r:$f" ;;
  esac
done

report() {
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
        if errors <= 80:
            print(f"::error file={rel},line={ln},col={col},title={code}::{msg}")
    elif code not in ('CS0618',):
        print(f"{rel}({ln},{col}): {kind} {code}: {msg}")
print(f"{asm}: {errors} error(s)")
sys.exit(1 if errors else 0)
PY
}

STATUS=0
DEFINES="UNITY_6000_0_OR_NEWER;UNITY_2023_3_OR_NEWER;UNITY_2022_3_OR_NEWER;UNITY_2021_3_OR_NEWER;UNITY_ANDROID;ENABLE_IL2CPP;UNITY_5_3_OR_NEWER;UNITY_2017_1_OR_NEWER;UNITY_2019_1_OR_NEWER;UNITY_2020_1_OR_NEWER;UNITY_2021_1_OR_NEWER;UNITY_2022_1_OR_NEWER;UNITY_2023_1_OR_NEWER"
find "$PROJ/Assets" -name "*.cs" -not -path "*/Editor/*" > "$OUT/runtime.txt"
"$DOTNET" "$CSC" $COMMON $REFS $RUNTIME_PKGS -define:"$DEFINES" \
  -out:"$OUT/Assembly-CSharp.dll" @"$OUT/runtime.txt" > "$OUT/runtime.log" 2>&1
report "$OUT/runtime.log" "Assembly-CSharp" || STATUS=1

if [ $STATUS -eq 0 ] && [ -n "$(find "$PROJ/Assets" -path "*/Editor/*" -name "*.cs" | head -1)" ]; then
  EDREFS=""
  for f in "$DATA"/PlaybackEngines/AndroidPlayer/*.dll; do [ -e "$f" ] && EDREFS="$EDREFS -r:$f"; done
  for f in "$DATA"/Managed/UnityEngine/UnityEditor*.dll; do EDREFS="$EDREFS -r:$f"; done
  for f in "$DATA"/Managed/Unity.*.dll; do [ -e "$f" ] && EDREFS="$EDREFS -r:$f"; done
  find "$PROJ/Assets" -path "*/Editor/*" -name "*.cs" > "$OUT/editor.txt"
  "$DOTNET" "$CSC" $COMMON $REFS $RUNTIME_PKGS $EDITOR_PKGS $EDREFS -r:"$OUT/Assembly-CSharp.dll" \
    -define:"UNITY_EDITOR;$DEFINES" -out:"$OUT/Assembly-CSharp-Editor.dll" @"$OUT/editor.txt" > "$OUT/editor.log" 2>&1
  report "$OUT/editor.log" "Assembly-CSharp-Editor" || STATUS=1
fi
exit $STATUS
