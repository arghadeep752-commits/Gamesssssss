#!/usr/bin/env bash
# One-per-run Firebase preparation (runs once, before the parallel app builds):
#   1. creates the Android upload key in Google Secret Manager on the first run
#      (random password, never printed, never stored in GitHub);
#   2. registers both Android apps in the Firebase project if missing;
#   3. registers the key's SHA-1 and SHA-256 with both apps (needed for Google sign-in
#      and App Check);
#   4. reports whether Google sign-in is enabled.
# Requires: gcloud + Application Default Credentials (google-github-actions/auth), keytool, jq, npx.
set -euo pipefail

PROJECT="${1:?usage: firebase-prepare.sh <project-id>}"
KS_SECRET="devdarshan-android-upload-keystore"
PW_SECRET="devdarshan-android-upload-password"
ALIAS="devdarshan"
WORK="${RUNNER_TEMP:-/tmp}/devdarshan-signing"
FIREBASE="npx --yes firebase-tools@15"
mkdir -p "$WORK"

summary() { echo "$*" >> "${GITHUB_STEP_SUMMARY:-/dev/null}"; }

# ---------- 1. Upload key ----------
if ! gcloud secrets describe "$KS_SECRET" --project "$PROJECT" >/dev/null 2>&1; then
  echo "Creating the Android upload key (first run)…"
  PASSWORD="$(openssl rand -base64 48 | tr -dc 'A-Za-z0-9' | cut -c1-32)"
  echo "::add-mask::$PASSWORD"
  keytool -genkeypair -noprompt \
    -keystore "$WORK/upload.p12" -storetype PKCS12 \
    -alias "$ALIAS" -keyalg RSA -keysize 4096 -validity 10000 \
    -storepass "$PASSWORD" -keypass "$PASSWORD" \
    -dname "CN=DevDarshan, OU=Apps, O=DevDarshan, L=India, C=IN" >/dev/null
  printf '%s' "$PASSWORD" | gcloud secrets create "$PW_SECRET" --project "$PROJECT" \
    --replication-policy=automatic --data-file=- >/dev/null
  base64 -w0 "$WORK/upload.p12" | gcloud secrets create "$KS_SECRET" --project "$PROJECT" \
    --replication-policy=automatic --data-file=- >/dev/null
  rm -f "$WORK/upload.p12"
  summary "- Created a new Android upload key in Secret Manager (\`$KS_SECRET\`)."
fi

gcloud secrets versions access latest --secret "$KS_SECRET" --project "$PROJECT" | base64 -d > "$WORK/upload.p12"
PASSWORD="$(gcloud secrets versions access latest --secret "$PW_SECRET" --project "$PROJECT")"
echo "::add-mask::$PASSWORD"
CERT="$(keytool -list -v -keystore "$WORK/upload.p12" -storetype PKCS12 -storepass "$PASSWORD" -alias "$ALIAS")"
SHA1="$(echo "$CERT" | awk '/SHA1:/ {print $2; exit}')"
SHA256="$(echo "$CERT" | awk '/SHA256:/ {print $2; exit}')"
rm -f "$WORK/upload.p12"
echo "Upload key SHA-1:   $SHA1"
echo "Upload key SHA-256: $SHA256"

# ---------- 2 + 3. Android apps and fingerprints ----------
APPS_JSON="$($FIREBASE apps:list ANDROID --project "$PROJECT" --json)"
ensure_app() {
  local package="$1" name="$2" app_id
  app_id="$(echo "$APPS_JSON" | jq -r --arg p "$package" '.result[]? | select(.packageName == $p) | .appId' | head -n1)"
  if [ -z "$app_id" ]; then
    echo "Registering $package in Firebase…" >&2
    app_id="$($FIREBASE apps:create ANDROID "$name" --package-name "$package" --project "$PROJECT" --json | jq -r '.result.appId')"
    summary "- Registered Android app \`$package\` in Firebase."
  fi
  local existing
  existing="$($FIREBASE apps:android:sha:list "$app_id" --project "$PROJECT" --json | jq -r '.result[]?.shaHash' | tr '[:upper:]' '[:lower:]' | tr -d ':')"
  for sha in "$SHA1" "$SHA256"; do
    local plain
    plain="$(echo "$sha" | tr '[:upper:]' '[:lower:]' | tr -d ':')"
    if ! echo "$existing" | grep -qx "$plain"; then
      $FIREBASE apps:android:sha:create "$app_id" "$sha" --project "$PROJECT" >/dev/null
      echo "Added fingerprint ${sha:0:20}… to $package" >&2
    fi
  done
  echo "$app_id"
}

USER_APP_ID="$(ensure_app com.devdarshan.wallpapers 'DevDarshan')"
ADMIN_APP_ID="$(ensure_app com.devdarshan.admin 'DevDarshan Admin')"

# ---------- 4. Google sign-in check ----------
$FIREBASE apps:sdkconfig ANDROID "$USER_APP_ID" --project "$PROJECT" --out "$WORK/check.json" >/dev/null
if jq -e '[.client[]?.oauth_client[]?, .client[]?.services.appinvite_service.other_platform_oauth_client[]?] | map(select(.client_type == 3)) | length > 0' "$WORK/check.json" >/dev/null; then
  GOOGLE_SIGN_IN=enabled
else
  GOOGLE_SIGN_IN=missing
  echo "::warning::Google sign-in is not enabled in Firebase Authentication yet; the apps will build but sign-in will show a setup message."
fi
STORAGE_BUCKET="$(jq -r '.project_info.storage_bucket // empty' "$WORK/check.json")"
rm -f "$WORK/check.json"

{
  echo "user_app_id=$USER_APP_ID"
  echo "admin_app_id=$ADMIN_APP_ID"
  echo "sha1=$SHA1"
  echo "sha256=$SHA256"
  echo "google_sign_in=$GOOGLE_SIGN_IN"
  echo "storage_bucket=$STORAGE_BUCKET"
} >> "${GITHUB_OUTPUT:-/dev/stdout}"

summary "- Upload key SHA-1 \`$SHA1\`"
summary "- Upload key SHA-256 \`$SHA256\`"
summary "- Google sign-in: **$GOOGLE_SIGN_IN**"
