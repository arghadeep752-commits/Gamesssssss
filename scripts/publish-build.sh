#!/usr/bin/env bash
# Publishes the built APK (and the smoke test results, when there are any) to
# the "calcpro-builds" branch, so it can be downloaded straight from a phone.
# Runs in GitHub Actions; needs GH_TOKEN, GITHUB_REPOSITORY, GITHUB_SHA and
# RUN_NUMBER in the environment. Safe to run more than once per build.
set -eu

out="${RUNNER_TEMP:-/tmp}/calcpro-builds"
rm -rf "$out" && mkdir -p "$out"
cp dist/CalcPro.apk "$out/"
if [ -d smoke ]; then
  cp -r smoke "$out/"
  note="The smoke folder has emulator screenshots, a screen recording, frame statistics and the log."
else
  note="Emulator test results are added here when that test finishes."
fi

{
  echo "# Calc Pro build ${RUN_NUMBER}"
  echo
  echo "Download **CalcPro.apk** from this branch and open it on your Android phone to install."
  echo
  echo "Built from commit ${GITHUB_SHA::7}. ${note}"
} > "$out/README.md"

cd "$out"
git init -q -b calcpro-builds
git config user.name "github-actions[bot]"
git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
git add -A
git commit -q -m "Calc Pro build ${RUN_NUMBER} (${GITHUB_SHA::7})"
git push -q -f "https://x-access-token:${GH_TOKEN}@github.com/${GITHUB_REPOSITORY}.git" calcpro-builds
echo "Published build ${RUN_NUMBER} to calcpro-builds."
