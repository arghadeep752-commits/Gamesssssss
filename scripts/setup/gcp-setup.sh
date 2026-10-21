#!/usr/bin/env bash
# DevDarshan one-time Google Cloud setup. Run it in Google Cloud Shell
# (https://shell.cloud.google.com, signed in with the Firebase project owner):
#
#   bash gcp-setup.sh <firebase-project-id>
#
# (Optional extra arguments: <github-owner/repo> <github-repository-id>; they default
# to this repository, arghadeep752-commits/Gamesssssss, id 1418506005.)
#
# What it does (safe to run again; every step is skipped when already done):
#   1. enables the Google APIs the backend and the build pipeline use;
#   2. creates the Firestore database in Mumbai (asia-south1) if it doesn't exist;
#   3. creates a deploy service account for GitHub Actions;
#   4. connects GitHub Actions to Google Cloud with Workload Identity Federation,
#      restricted to the main branch of your repository (matched by its numeric id,
#      so a renamed or re-created repo can't take over). No keys or passwords are
#      created or copied;
#   5. grants the Cloud Functions build/runtime accounts what they need.
#
# It prints the two values to send back: project id and project number.
set -euo pipefail

PROJECT_ID="${1:?Usage: bash gcp-setup.sh <firebase-project-id>}"
REPO="${2:-arghadeep752-commits/Gamesssssss}"
REPO_ID="${3:-1418506005}"
FIRESTORE_LOCATION="${FIRESTORE_LOCATION:-asia-south1}"
POOL="github"
PROVIDER="devdarshan"
SA_NAME="devdarshan-ci"

say() { printf '\n\033[1;33m▸ %s\033[0m\n' "$*"; }
ok() { printf '  \033[0;32m✓\033[0m %s\n' "$*"; }
warn() { printf '  \033[0;31m!\033[0m %s\n' "$*"; }

gcloud config set project "$PROJECT_ID" >/dev/null
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
ok "Project $PROJECT_ID (number $PROJECT_NUMBER)"

BILLING="$(gcloud billing projects describe "$PROJECT_ID" --format='value(billingEnabled)' 2>/dev/null || echo unknown)"
if [ "$BILLING" != "True" ]; then
  warn "Billing does not look enabled. Upgrade the Firebase project to the Blaze plan first, then run this again."
fi

say "1/5 Enabling APIs (takes a minute)"
gcloud services enable \
  firebase.googleapis.com firestore.googleapis.com firebaserules.googleapis.com \
  firebasestorage.googleapis.com storage.googleapis.com identitytoolkit.googleapis.com \
  cloudfunctions.googleapis.com run.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com eventarc.googleapis.com pubsub.googleapis.com \
  cloudscheduler.googleapis.com secretmanager.googleapis.com compute.googleapis.com \
  iam.googleapis.com iamcredentials.googleapis.com sts.googleapis.com \
  cloudresourcemanager.googleapis.com serviceusage.googleapis.com \
  firebaseappcheck.googleapis.com playintegrity.googleapis.com \
  --project "$PROJECT_ID"
ok "APIs enabled"

say "2/5 Firestore database"
if gcloud firestore databases describe --database='(default)' --project "$PROJECT_ID" >/dev/null 2>&1; then
  ok "Already exists ($(gcloud firestore databases describe --database='(default)' --project "$PROJECT_ID" --format='value(locationId)'))"
else
  gcloud firestore databases create --database='(default)' --location="$FIRESTORE_LOCATION" \
    --type=firestore-native --project "$PROJECT_ID" >/dev/null
  ok "Created in $FIRESTORE_LOCATION"
fi

say "3/5 Deploy service account"
SA="$SA_NAME@$PROJECT_ID.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe "$SA" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam service-accounts create "$SA_NAME" --display-name="DevDarshan GitHub deploy" --project "$PROJECT_ID" >/dev/null
  sleep 5
fi
for ROLE in \
  roles/firebase.admin roles/firebaserules.admin roles/datastore.indexAdmin roles/storage.admin \
  roles/cloudfunctions.admin roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.admin \
  roles/eventarc.admin roles/pubsub.admin roles/cloudscheduler.admin roles/secretmanager.admin \
  roles/iam.serviceAccountUser roles/serviceusage.serviceUsageAdmin roles/resourcemanager.projectIamAdmin; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$SA" --role="$ROLE" \
    --condition=None --quiet >/dev/null
done
ok "$SA has deploy roles"

say "4/5 GitHub → Google Cloud trust (Workload Identity Federation)"
if ! gcloud iam workload-identity-pools describe "$POOL" --location=global --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools create "$POOL" --location=global --display-name="GitHub Actions" --project "$PROJECT_ID" >/dev/null
fi
MAPPING="google.subject=assertion.sub,attribute.repository=assertion.repository,attribute.repository_id=assertion.repository_id,attribute.ref=assertion.ref"
CONDITION="assertion.repository_id == '$REPO_ID' && assertion.ref == 'refs/heads/main'"
if gcloud iam workload-identity-pools providers describe "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" --project "$PROJECT_ID" >/dev/null 2>&1; then
  gcloud iam workload-identity-pools providers update-oidc "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" --attribute-mapping="$MAPPING" --attribute-condition="$CONDITION" \
    --project "$PROJECT_ID" >/dev/null
else
  gcloud iam workload-identity-pools providers create-oidc "$PROVIDER" --location=global \
    --workload-identity-pool="$POOL" --display-name="DevDarshan repository" \
    --issuer-uri="https://token.actions.githubusercontent.com" \
    --attribute-mapping="$MAPPING" --attribute-condition="$CONDITION" \
    --project "$PROJECT_ID" >/dev/null
fi
gcloud iam service-accounts add-iam-policy-binding "$SA" --project "$PROJECT_ID" \
  --role=roles/iam.workloadIdentityUser \
  --member="principalSet://iam.googleapis.com/projects/$PROJECT_NUMBER/locations/global/workloadIdentityPools/$POOL/attribute.repository_id/$REPO_ID" \
  --quiet >/dev/null
ok "Only GitHub Actions on the main branch of $REPO can act as $SA_NAME"

say "5/5 Cloud Functions build and runtime permissions"
COMPUTE_SA="$PROJECT_NUMBER-compute@developer.gserviceaccount.com"
for i in 1 2 3 4 5 6; do
  gcloud iam service-accounts describe "$COMPUTE_SA" --project "$PROJECT_ID" >/dev/null 2>&1 && break
  sleep 10
done
for ROLE in roles/cloudbuild.builds.builder roles/artifactregistry.writer roles/logging.logWriter \
  roles/storage.objectAdmin roles/datastore.user roles/firebaseauth.admin roles/eventarc.eventReceiver \
  roles/run.invoker; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$COMPUTE_SA" --role="$ROLE" \
    --condition=None --quiet >/dev/null || warn "could not grant $ROLE to $COMPUTE_SA"
done
GCS_AGENT="$(gcloud storage service-agent --project "$PROJECT_ID" 2>/dev/null || true)"
if [ -n "$GCS_AGENT" ]; then
  gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="serviceAccount:$GCS_AGENT" \
    --role=roles/pubsub.publisher --condition=None --quiet >/dev/null || warn "could not grant pubsub.publisher to $GCS_AGENT"
fi
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-pubsub.iam.gserviceaccount.com" \
  --role=roles/iam.serviceAccountTokenCreator --condition=None --quiet >/dev/null 2>&1 || true
ok "Functions can build, run, read Storage and Firestore, and set admin claims"

BUCKET_OK=no
for B in "$PROJECT_ID.firebasestorage.app" "$PROJECT_ID.appspot.com"; do
  if gcloud storage buckets describe "gs://$B" --project "$PROJECT_ID" >/dev/null 2>&1; then
    BUCKET_OK="$B ($(gcloud storage buckets describe "gs://$B" --format='value(location)'))"
    break
  fi
done
if [ "$BUCKET_OK" = "no" ]; then
  warn "No Firebase Storage bucket yet: open Firebase console → Storage → Get started (choose US-CENTRAL1), then run this script again."
else
  ok "Storage bucket: $BUCKET_OK"
  # The Storage rules check admin roles in Firestore (cross-service rules), which needs this role.
  if gcloud projects add-iam-policy-binding "$PROJECT_ID" \
      --member="serviceAccount:service-$PROJECT_NUMBER@gcp-sa-firebasestorage.iam.gserviceaccount.com" \
      --role=roles/firebaserules.firestoreServiceAgent --condition=None --quiet >/dev/null 2>&1; then
    ok "Storage rules can read admin roles from Firestore"
  else
    warn "Could not let Storage rules read Firestore yet; the backend deploy will try again"
  fi
fi

printf '\n\033[1;32mAll set.\033[0m Send these two lines back:\n\n'
printf '  project id: %s\n  project number: %s\n\n' "$PROJECT_ID" "$PROJECT_NUMBER"
