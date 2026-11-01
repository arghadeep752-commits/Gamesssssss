#!/usr/bin/env bash
# Packages a Unity 6 "compile kit" into a PRIVATE draft release (only people with
# write access can see drafts): Unity's C# compiler, the engine/editor reference
# assemblies, the compiled URP/SRP Core/uGUI assemblies from a probe project and the
# URP + SRP Core package sources (shader library). It lets the game's scripts be
# compile-checked, and its shaders be written against the exact URP version, without
# running a full Unity build.
# usage: publish_kit6.sh <Unity binary> <probe project dir> <tag>
set -uo pipefail

EDITOR_BIN="${1:?editor}"
PROBE="${2:?probe project}"
TAG="${3:?tag}"
ED="$(dirname "$EDITOR_BIN")"
STAGE="$RUNNER_TEMP/kit6"
OUTDIR="$RUNNER_TEMP/kit6-out"
rm -rf "$STAGE" "$OUTDIR"
mkdir -p "$STAGE/Editor/Data/PlaybackEngines/AndroidPlayer" "$STAGE/Editor/Data/Resources/PackageManager" "$STAGE/Editor/Data/Managed" "$STAGE/Project" "$STAGE/Packages" "$OUTDIR"

echo "$EDITOR_BIN" > "$STAGE/editor-path.txt"
basename "$(dirname "$ED")" > "$STAGE/version.txt"
echo "Unity version: $(cat "$STAGE/version.txt")"

copy() { # copy <src> <dst-dir>
  if [ -e "$1" ]; then cp -a "$1" "$2/"; else echo "missing: $1" | tee -a "$STAGE/missing.txt"; fi
}
copy "$ED/Data/NetCoreRuntime" "$STAGE/Editor/Data"
copy "$ED/Data/DotNetSdkRoslyn" "$STAGE/Editor/Data"
copy "$ED/Data/NetStandard" "$STAGE/Editor/Data"
copy "$ED/Data/Managed/UnityEngine" "$STAGE/Editor/Data/Managed"
for f in "$ED"/Data/Managed/*.dll; do [ -e "$f" ] && cp -a "$f" "$STAGE/Editor/Data/Managed/"; done
for f in "$ED"/Data/PlaybackEngines/AndroidPlayer/*.dll; do [ -e "$f" ] && cp -a "$f" "$STAGE/Editor/Data/PlaybackEngines/AndroidPlayer/"; done
mkdir -p "$STAGE/Editor/Data/Resources/PackageManager/Editor"
cp "$ED"/Data/Resources/PackageManager/Editor/*.json "$STAGE/Editor/Data/Resources/PackageManager/Editor/" 2>/dev/null || true
ls "$ED/Data/Resources/PackageManager/BuiltInPackages" > "$STAGE/builtin-packages.txt" 2>/dev/null || true
find "$ED/Data" -maxdepth 3 > "$STAGE/editor-tree.txt" 2>/dev/null || true

# compiled package assemblies from the probe project
copy "$PROBE/Library/ScriptAssemblies" "$STAGE/Project"
copy "$PROBE/Packages/manifest.json" "$STAGE/Project"
copy "$PROBE/Packages/packages-lock.json" "$STAGE/Project"
ls -la "$PROBE/Library/ScriptAssemblies" > "$STAGE/script-assemblies.txt" 2>&1 || true

# URP / Core / Shader Graph / uGUI package sources (wherever this editor keeps them)
for name in com.unity.render-pipelines.universal com.unity.render-pipelines.core com.unity.render-pipelines.universal-config com.unity.ugui com.unity.shadergraph; do
  src=""
  for cand in "$PROBE"/Library/PackageCache/"$name"@* "$PROBE"/Library/PackageCache/"$name" "$ED/Data/Resources/PackageManager/BuiltInPackages/$name"; do
    if [ -d "$cand" ]; then src="$cand"; break; fi
  done
  if [ -n "$src" ]; then
    echo "package $name <- $src"
    mkdir -p "$STAGE/Packages/$name"
    (cd "$src" && find . -type f \( -name "*.cs" -o -name "*.hlsl" -o -name "*.cginc" -o -name "*.shader" -o -name "*.compute" -o -name "*.json" -o -name "*.asmdef" -o -name "*.asset" \) \
       -not -path "./Tests/*" -not -path "./Samples~/*" -not -path "./Documentation~/*" -print0 | tar --null -cf - -T - ) | tar -xf - -C "$STAGE/Packages/$name"
  else
    echo "package $name not found" | tee -a "$STAGE/missing.txt"
  fi
done

for f in "$GITHUB_WORKSPACE"/Logs/*.log "$GITHUB_WORKSPACE"/probe-report.txt "$GITHUB_WORKSPACE"/probe-urp.txt; do [ -e "$f" ] && cp "$f" "$STAGE/"; done

{ du -sh "$STAGE"/*; du -sh "$STAGE"/Editor/Data/*; du -sh "$STAGE"/Editor/Data/Managed/*; } > "$STAGE/sizes.txt" 2>&1 || true
cat "$STAGE/sizes.txt"
tar -C "$STAGE" -cf - . | xz -T0 -6 > "$OUTDIR/unity6-kit.tar.xz"
ls -la "$OUTDIR/unity6-kit.tar.xz"
# split into parts that upload reliably
(cd "$OUTDIR" && split -b 90m -d -a 2 unity6-kit.tar.xz unity6-kit.tar.xz.part && rm unity6-kit.tar.xz && ls -la)
cp "$STAGE/version.txt" "$STAGE/sizes.txt" "$STAGE/script-assemblies.txt" "$OUTDIR/" 2>/dev/null || true
for f in "$GITHUB_WORKSPACE"/probe-report.txt "$GITHUB_WORKSPACE"/probe-urp.txt "$GITHUB_WORKSPACE"/Logs/probe-open.log "$GITHUB_WORKSPACE"/Logs/probe-urp.log; do [ -e "$f" ] && cp "$f" "$OUTDIR/"; done

# replace an older draft with the same tag
for id in $(gh api "repos/$GH_REPO/releases?per_page=100" --jq ".[] | select(.tag_name == \"$TAG\") | .id"); do
  gh api -X DELETE "repos/$GH_REPO/releases/$id" && echo "deleted old kit draft $id"
done
REL=$(gh api -X POST "repos/$GH_REPO/releases" -f tag_name="$TAG" -f name="Unity 6 compile kit (private draft, safe to delete)" \
      -f body="Private draft used by the Silent Valley workflow to compile-check scripts against Unity $(cat "$STAGE/version.txt") + URP. Safe to delete." \
      -F draft=true --jq .id)
echo "draft release id: $REL"
status=0
for f in "$OUTDIR"/*; do
  name=$(basename "$f")
  ok=0
  for attempt in 1 2 3 4; do
    if gh api -X POST -H "Content-Type: application/octet-stream" \
         "https://uploads.github.com/repos/$GH_REPO/releases/$REL/assets?name=$name" --input "$f" --jq .name >/dev/null; then
      ok=1; echo "uploaded $name"; break
    fi
    echo "upload of $name failed (attempt $attempt), retrying"; sleep $((attempt * 10))
  done
  [ $ok -eq 1 ] || status=1
done
exit $status
