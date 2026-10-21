# Setting up DevDarshan from a phone

Everything below can be done in a mobile browser. Nothing has to be installed on a computer. Do it once and it takes about 20 minutes, plus build time.

You will create a Firebase project, connect it to this GitHub repository with a short Cloud Shell script, and from then on GitHub Actions deploys the backend and builds the APKs for you.

> **Accounts.** Use the same Google account for steps 2–6 (it becomes the Firebase project owner). The **first admin** of DevDarshan Admin is the Gmail address chosen during setup. It is stored in `firebase/functions/.env` only as a SHA-256 hash (`DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256`), so the address itself isn't published in this public repository.

---

## 1. GitHub repository

The code lives in the existing **public** repository [`arghadeep752-commits/Gamesssssss`](https://github.com/arghadeep752-commits/Gamesssssss) (branch `main`), so there's nothing to create.

Because it's public:

- GitHub Actions minutes are free;
- anyone can download the APKs from **Releases** without a GitHub account.

The repository contains no keys or passwords (see [SECURITY.md](SECURITY.md)).

## 2. Firebase project

1. Open <https://console.firebase.google.com> and choose **Create a project**.
2. Name it `DevDarshan`. Firebase shows the **project ID** underneath (for example `devdarshan-1a2b3`). Write it down.
3. Google Analytics: **turn it off**. DevDarshan doesn't use it.

## 3. Blaze plan and a budget alert

Cloud Functions and Cloud Storage need the pay-as-you-go **Blaze** plan. A small app usually stays within the free monthly quotas, but set an alert so there are no surprises:

1. In the Firebase console, tap the plan name (Spark) → **Upgrade** → choose or create a billing account.
2. Accept the prompt to create a **budget alert**, or go to Google Cloud console → Billing → *Budgets & alerts* → **Create budget**. For example ₹500 per month with email alerts at 50%, 90% and 100%.

## 4. Turn on Google sign-in

Firebase console → **Build → Authentication** → *Get started* → **Sign-in method** → **Google** → Enable → choose your support email → **Save**.

This also creates the OAuth "web client" that Android sign-in needs. The build pipeline checks for it and reports `Google sign-in: enabled` in the release notes.

## 5. Create the Storage bucket

Firebase console → **Build → Storage** → *Get started* → choose location **US-CENTRAL1** → *Production mode* → **Done**.

US-CENTRAL1 qualifies for Cloud Storage's always-free tier. The security rules you see there are replaced automatically on the first deploy.

> You don't need to create the Firestore database. The script in the next step creates it in **asia-south1 (Mumbai)**. If you already created one, that's fine too: the backend deploy adapts to its location.

## 6. Connect GitHub Actions to Google Cloud (Cloud Shell)

1. Get `scripts/setup/gcp-setup.sh` onto your phone. Claude can send it to you, or open the file on github.com in a browser, tap **Raw** and save the page.
2. Open <https://shell.cloud.google.com> with the same Google account. Tap **Authorize** if asked.
3. Upload the script: in the Cloud Shell menu tap **⋮ → Upload**, then pick `gcp-setup.sh`.
4. Run it, replacing the project ID:

   ```bash
   bash gcp-setup.sh YOUR-PROJECT-ID
   ```

The script is safe to re-run. It takes about 3 minutes and:

- turns on the Google APIs the backend and the pipeline use;
- creates the Firestore database (Mumbai) if it is missing;
- creates a deploy service account, `devdarshan-ci`;
- sets up **Workload Identity Federation** so that *only GitHub Actions on the `main` branch of this repository* can deploy. Forks and pull requests can't. No keys or passwords are created or stored anywhere;
- gives Cloud Functions the permissions they need (building, Storage, Firestore, setting admin claims).

It finishes by printing two lines:

```
project id: devdarshan-1a2b3
project number: 123456789012
```

## 7. Tell the repository about the project

Put both values in `config/firebase-project.json`. Claude can do this for you; just send the two lines:

```json
{
  "projectId": "devdarshan-1a2b3",
  "projectNumber": "123456789012",
  "githubRepository": "arghadeep752-commits/Gamesssssss"
}
```

Pushing that change starts two workflows (GitHub → **Actions**):

| Workflow | What it does | Time |
| --- | --- | --- |
| **Firebase backend** | Deploys Firestore rules and indexes, Storage rules and the Cloud Functions. | 5–10 min |
| **Android APKs** | Creates the signing key (first run only, kept in Secret Manager), registers both Android apps in Firebase with their fingerprints, then builds, verifies and emulator-tests both APKs and publishes a **GitHub Release**. | 30–45 min |

## 8. Install the apps

Open <https://github.com/arghadeep752-commits/Gamesssssss/releases/latest> on the phone. No GitHub account is needed. Download and open:

- `DevDarshan-Admin-1.0.0-arm64-v8a.apk`: the admin app;
- `DevDarshan-1.0.0-arm64-v8a.apk`: the user app (`armeabi-v7a` for old 32-bit phones; `universal` if unsure).

Android will ask you to allow installs from your browser or the GitHub app. Allow it for that app only.

## 9. Become the first admin

1. Open **DevDarshan Admin** → **Sign in with Google** with the first-admin Gmail account.
2. You'll see *Admin access needed*. Tap **Claim admin access**.

This works only for that account (its verified email must match the stored hash), and only while there are no admins yet. After that, admins are added from **Settings → Admins**.

## 10. Add content

1. **Settings → Add starter categories** creates the 20 starter categories (Shri Ganesh, Mahadev, Shri Ram, …).
2. **Wallpapers → +** → choose an image (JPEG, PNG or WebP; at least 600 px on the short side; up to 30 MB) → title, categories, tags → **Upload**.
3. Within a few seconds the server checks the image and creates the preview, thumbnail and placeholder. Then it publishes the wallpaper (if you chose *Publish when ready*).
4. **Settings → Home content** chooses *Today's Darshan*, the home categories and the festival collection.

In the user app, pull down on the home screen to refresh and see new wallpapers straight away.

---

### If something goes wrong

| Symptom | Fix |
| --- | --- |
| Release notes say `Google sign-in: missing` | Do step 4, then re-run **Android APKs** (Actions → Android APKs → *Run workflow*). |
| Backend deploy says no Storage bucket | Do step 5, then re-run **Firebase backend**. |
| First backend deploy fails with an Eventarc or "service agent" permission error | Google is still provisioning. The workflow retries automatically; if all three attempts fail, re-run it after 10 minutes. |
| *Claim admin access* says it's not allowed | Make sure you signed in with the bootstrap email, and that no admin exists yet. |
| Admin lists say an index is building | Firestore builds new indexes for a few minutes after the first deploy. Pull to refresh later. |
