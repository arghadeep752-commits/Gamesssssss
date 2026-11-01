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
rm -rf "$STAGE"
mkdir -p "$STAGE/Editor" "$STAGE/Project" "$STAGE/Packages"

echo "$EDITOR_BIN" > "$STAGE/editor-path.txt"
basename "$(dirname "$ED")" > "$STAGE/version.txt"
echo "Unity version: $(cat "$STAGE/version.txt")"

copy() { # copy <src> <dst-dir>
  if [ -e "$1" ]; then cp -a "$1" "$2/"; else echo "missing: $1"; fi
}
mkdir -p "$STAGE/Editor/Data" "$STAGE/Editor/Data/PlaybackEngines/AndroidPlayer" "$STAGE/Editor/Data/Resources/PackageManager"
copy "$ED/Data/NetCoreRuntime" "$STAGE/Editor/Data"
copy "$ED/Data/DotNetSdkRoslyn" "$STAGE/Editor/Data"
copy "$ED/Data/Managed" "$STAGE/Editor/Data"
copy "$ED/Data/NetStandard" "$STAGE/Editor/Data"
for f in "$ED"/Data/PlaybackEngines/AndroidPlayer/*.dll; do [ -e "$f" ] && cp -a "$f" "$STAGE/Editor/Data/PlaybackEngines/AndroidPlayer/"; done
copy "$ED/Data/Resources/PackageManager/Editor" "$STAGE/Editor/Data/Resources/PackageManager"
ls "$ED/Data/Resources/PackageManager/BuiltInPackages" > "$STAGE/builtin-packages.txt" 2>/dev/null || true
find "$ED/Data" -maxdepth 3 > "$STAGE/editor-tree.txt" 2>/dev/null || true

# compiled package assemblies from the probe project
copy "$PROBE/Library/ScriptAssemblies" "$STAGE/Project"
copy "$PROBE/Packages/manifest.json" "$STAGE/Project"
copy "$PROBE/Packages/packages-lock.json" "$STAGE/Project"

# URP / Core / Shader Graph / uGUI package sources (wherever this editor keeps them)
for name in com.unity.render-pipelines.universal com.unity.render-pipelines.core com.unity.render-pipelines.universal-config com.unity.ugui com.unity.shadergraph; do
  src=""
  for cand in "$PROBE"/Library/PackageCache/"$name"@* "$PROBE"/Library/PackageCache/"$name" "$ED/Data/Resources/PackageManager/BuiltInPackages/$name"; do
    if [ -d "$cand" ]; then src="$cand"; break; fi
  done
  if [ -n "$src" ]; then
    echo "package $name <- $src"
    mkdir -p "$STAGE/Packages/$name"
    # sources only: skip large binary samples/textures/tests
    (cd "$src" && find . -type f \( -name "*.cs" -o -name "*.hlsl" -o -name "*.cginc" -o -name "*.shader" -o -name "*.compute" -o -name "*.json" -o -name "*.asmdef" -o -name "*.asset" -o -name "*.md" \) \
       -not -path "./Tests/*" -not -path "./Samples~/*" -not -path "./Documentation~/*" -print0 | \
       tar --null -cf - -T - ) | tar -xf - -C "$STAGE/Packages/$name"
  else
    echo "package $name not found"
  fi
done

for f in "$GITHUB_WORKSPACE"/Logs/*.log "$GITHUB_WORKSPACE"/probe-report.txt; do [ -e "$f" ] && cp "$f" "$STAGE/"; done

du -sh "$STAGE"/* || true
tar -C "$STAGE" -cf - . | xz -T0 -6 > "$RUNNER_TEMP/unity6-kit.tar.xz"
ls -la "$RUNNER_TEMP/unity6-kit.tar.xz"

# replace an older draft with the same tag
for id in $(gh api "repos/$GH_REPO/releases?per_page=100" --jq ".[] | select(.tag_name == \"$TAG\") | .id"); do
  gh api -X DELETE "repos/$GH_REPO/releases/$id" && echo "deleted old kit draft $id"
done
extra=()
for f in "$STAGE/version.txt" "$STAGE/builtin-packages.txt" "$GITHUB_WORKSPACE/probe-report.txt" "$GITHUB_WORKSPACE/Logs/probe-open.log"; do [ -e "$f" ] && extra+=("$f"); done
gh release create "$TAG" --draft \
  --title "Unity 6 compile kit (private draft, safe to delete)" \
  --notes "Private draft used by the Silent Valley workflow to compile-check scripts against Unity $(cat "$STAGE/version.txt") + URP. Safe to delete." \
  "$RUNNER_TEMP/unity6-kit.tar.xz" "${extra[@]}"
echo "Kit published: $TAG"
