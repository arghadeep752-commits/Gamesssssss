#!/usr/bin/env bash
# Per-app build inputs: google-services.json and the release signing key.
#
#   android-inputs.sh <user|admin> <project-id-or-empty> <firebase-app-id-or-empty>
#
# With a project: downloads the real config and the upload key from Secret Manager.
# Without one: writes the placeholder config and signs with a throwaway key, so the
# build pipeline can still be verified end to end. The user app is then a DEMO build
# (sample catalogue, labelled -DEMO); the admin app is labelled -TEST.
set -euo pipefail

APP="${1:?app}"
PROJECT="${2:-}"
APP_ID="${3:-}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TARGET="$ROOT/apps/$APP/google-services.json"
WORK="${RUNNER_TEMP:-/tmp}/devdarshan-signing"
mkdir -p "$WORK"
env_out="${GITHUB_ENV:-/dev/null}"

if [ -n "$PROJECT" ] && [ -n "$APP_ID" ]; then
  npx --yes firebase-tools@15 apps:sdkconfig ANDROID "$APP_ID" --project "$PROJECT" --out "$TARGET" >/dev/null
  gcloud secrets versions access latest --secret devdarshan-android-upload-keystore --project "$PROJECT" | base64 -d > "$WORK/upload.p12"
  PASSWORD="$(gcloud secrets versions access latest --secret devdarshan-android-upload-password --project "$PROJECT")"
  echo "::add-mask::$PASSWORD"
  CHANNEL=release
else
  node "$ROOT/scripts/ci/placeholder-google-services.mjs" "$TARGET"
  PASSWORD="$(openssl rand -hex 16)"
  echo "::add-mask::$PASSWORD"
  keytool -genkeypair -noprompt -keystore "$WORK/upload.p12" -storetype PKCS12 -alias devdarshan \
    -keyalg RSA -keysize 2048 -validity 30 -storepass "$PASSWORD" -keypass "$PASSWORD" \
    -dname "CN=DevDarshan Test Build, O=DevDarshan, C=IN" >/dev/null
  if [ "$APP" = "user" ]; then
    # Without a backend the user app is built as a DEMO with a sample catalogue.
    CHANNEL=demo
    echo "DEVDARSHAN_DEMO=true" >> "$env_out"
  else
    CHANNEL=test
  fi
fi

{
  echo "DEVDARSHAN_KEYSTORE_PATH=$WORK/upload.p12"
  echo "DEVDARSHAN_KEYSTORE_PASSWORD=$PASSWORD"
  echo "DEVDARSHAN_KEY_ALIAS=devdarshan"
  echo "DEVDARSHAN_BUILD_CHANNEL=$CHANNEL"
} >> "$env_out"
echo "Prepared $APP build inputs (channel: $CHANNEL)"
