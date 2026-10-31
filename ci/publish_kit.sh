#!/usr/bin/env bash
# Packages Unity's own C# compiler and engine reference assemblies into a PRIVATE
# draft release (visible only to people with write access). It lets the game's
# scripts be compile-checked without running the full Unity build.
# Runs once; later runs see the draft and skip.
set -euo pipefail

EDITOR_PATH="${1:-}"
if [ -z "$EDITOR_PATH" ]; then
  echo "No Unity editor path given; skipping kit."
  exit 0
fi

existing=$(gh api "repos/$GH_REPO/releases?per_page=100" --jq "[.[] | select(.tag_name == \"$KIT_TAG\")] | length" || echo 0)
if [ "$existing" != "0" ]; then
  echo "Compile kit already published; skipping."
  exit 0
fi

EDITOR_DIR="$(dirname "$EDITOR_PATH")"
cd "$EDITOR_DIR"
echo "Editor dir: $EDITOR_DIR"
find Data -maxdepth 2 | sort > "$RUNNER_TEMP/kit-tree.txt"
find Data/PlaybackEngines -maxdepth 2 -name "*.dll" >> "$RUNNER_TEMP/kit-tree.txt" 2>/dev/null || true

items=()
for p in Data/NetCoreRuntime Data/DotNetSdkRoslyn Data/Managed Data/NetStandard \
         Data/Resources/PackageManager/BuiltInPackages/com.unity.ugui \
         Data/PlaybackEngines/AndroidPlayer/UnityEditor.Android.Extensions.dll; do
  if [ -e "$p" ]; then items+=("$p"); else echo "missing: $p"; fi
done

tar -cf - "${items[@]}" | xz -T0 -6 > "$RUNNER_TEMP/unity-kit.tar.xz"
ls -la "$RUNNER_TEMP/unity-kit.tar.xz"

gh release create "$KIT_TAG" --draft \
  --title "Unity compile kit (private draft, safe to delete)" \
  --notes "Private draft used by the Unity workflows to compile-check scripts. Safe to delete." \
  "$RUNNER_TEMP/unity-kit.tar.xz" "$RUNNER_TEMP/kit-tree.txt"
echo "Compile kit published as a draft release."
