#!/usr/bin/env bash
# Collects, renames and verifies the release APKs of one app, and writes a
# Markdown verification report (package id, version, SDK levels, ABIs,
# permissions, signer certificate, size, SHA-256).
#
#   collect-apks.sh <user|admin> <version-name> <version-code> <channel>
set -euo pipefail

APP="${1:?app}"
VERSION="${2:?version}"
CODE="${3:?versionCode}"
CHANNEL="${4:-release}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/apps/$APP/android/app/build/outputs/apk/release"
OUT="$ROOT/build-output/$APP"
mkdir -p "$OUT"

BT="$(ls -1 "$ANDROID_HOME/build-tools" | sort -V | tail -n1)"
APKSIGNER="$ANDROID_HOME/build-tools/$BT/apksigner"
AAPT2="$ANDROID_HOME/build-tools/$BT/aapt2"

case "$APP" in
  user) LABEL="DevDarshan"; EXPECTED_PACKAGE="com.devdarshan.wallpapers" ;;
  admin) LABEL="DevDarshan-Admin"; EXPECTED_PACKAGE="com.devdarshan.admin" ;;
  *) echo "unknown app $APP" >&2; exit 1 ;;
esac
SUFFIX=""
[ "$CHANNEL" = "release" ] || SUFFIX="-TEST"

REPORT="$OUT/report.md"
{
  echo "## $LABEL $VERSION ($CODE)${SUFFIX:+ — test build, not connected to Firebase}"
  echo
} > "$REPORT"

shopt -s nullglob
found=0
for apk in "$SRC"/*.apk; do
  found=1
  base="$(basename "$apk" .apk)"            # app-arm64-v8a-release | app-universal-release | app-release
  abi="${base#app-}"
  abi="${abi%-release}"
  if [ "$abi" = "release" ] || [ "$abi" = "universal" ]; then abi="universal"; fi
  name="$LABEL-$VERSION-$abi$SUFFIX.apk"
  cp "$apk" "$OUT/$name"

  badging="$("$AAPT2" dump badging "$OUT/$name")"
  package="$(echo "$badging" | sed -n "s/^package: name='\([^']*\)'.*/\1/p")"
  vcode="$(echo "$badging" | sed -n "s/.*versionCode='\([^']*\)'.*/\1/p" | head -n1)"
  vname="$(echo "$badging" | sed -n "s/.*versionName='\([^']*\)'.*/\1/p" | head -n1)"
  minsdk="$(echo "$badging" | sed -n "s/^minSdkVersion:'\([^']*\)'.*/\1/p")"
  target="$(echo "$badging" | sed -n "s/^targetSdkVersion:'\([^']*\)'.*/\1/p")"
  abis="$(echo "$badging" | sed -n "s/^native-code: //p" | tr -d "'")"
  appname="$(echo "$badging" | sed -n "s/^application-label:'\([^']*\)'.*/\1/p")"
  perms="$("$AAPT2" dump permissions "$OUT/$name" | sed -n "s/^uses-permission: name='\([^']*\)'.*/\1/p" | sort -u)"
  certs="$("$APKSIGNER" verify --verbose --print-certs "$OUT/$name")"
  schemes="$(echo "$certs" | grep -E '^Verified using v[0-9].*: true' | sed 's/Verified using //; s/ scheme.*//' | paste -sd ', ' -)"
  signer256="$(echo "$certs" | sed -n 's/^Signer #1 certificate SHA-256 digest: //p')"
  signer1="$(echo "$certs" | sed -n 's/^Signer #1 certificate SHA-1 digest: //p')"
  size="$(du -k "$OUT/$name" | cut -f1)"
  sha="$(sha256sum "$OUT/$name" | cut -d' ' -f1)"

  if [ "$package" != "$EXPECTED_PACKAGE" ]; then
    echo "::error::$name has package $package, expected $EXPECTED_PACKAGE"
    exit 1
  fi
  if [ "$vcode" != "$CODE" ]; then
    echo "::error::$name has versionCode $vcode, expected $CODE"
    exit 1
  fi

  {
    echo "### \`$name\`"
    echo
    echo "| Check | Result |"
    echo "|---|---|"
    echo "| App name | $appname |"
    echo "| Package | \`$package\` |"
    echo "| Version | $vname ($vcode) |"
    echo "| Min / target SDK | $minsdk / $target |"
    echo "| Native ABIs | ${abis:-none} |"
    echo "| Signature | verified ($schemes) |"
    echo "| Signer SHA-1 | \`$signer1\` |"
    echo "| Signer SHA-256 | \`$signer256\` |"
    echo "| Size | $((size / 1024)).$(( (size % 1024) * 10 / 1024 )) MB |"
    echo "| SHA-256 | \`$sha\` |"
    echo
    echo "<details><summary>Permissions ($(echo "$perms" | grep -c . || true))</summary>"
    echo
    echo "$perms" | sed 's/^/- /'
    echo
    echo "</details>"
    echo
  } >> "$REPORT"
  echo "$sha  $name" >> "$OUT/SHA256SUMS.txt"
done

if [ "$found" -eq 0 ]; then
  echo "::error::No APKs found in $SRC"
  exit 1
fi

cat "$REPORT" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"
ls -la "$OUT"
