# Build and release

All builds run in GitHub Actions. Nothing has to be installed locally.

## Workflows

| Workflow | Trigger | Does |
| --- | --- | --- |
| `checks.yml`, **Checks** | Every push and PR | `npm install`, an Expo SDK version check, a TypeScript check of all workspaces, shared unit tests, and Cloud Functions typecheck + unit tests (real sharp) + build. Firestore and Storage rules are tested in the emulators. |
| `backend.yml`, **Firebase backend** | Changes under `firebase/`, `packages/shared/src/`, `config/firebase-project.json` | Matches function regions to the Firestore and bucket locations, then deploys rules, indexes and functions with `firebase-tools` (WIF auth, 3 attempts). |
| `android.yml`, **Android APKs** | Changes to apps, packages, CI scripts, config; or *Run workflow* | Prepares Firebase, then builds, verifies, emulator-tests and publishes both apps. |

## Android pipeline in detail

1. **Prepare** (once per run):
   - reads `config/firebase-project.json`;
   - sets the version code to `run_number + 100`;
   - when configured, authenticates with Workload Identity Federation and runs `scripts/ci/firebase-prepare.sh`, which:
     - creates the upload key in Secret Manager the first time;
     - registers `com.devdarshan.wallpapers` and `com.devdarshan.admin` in Firebase if needed;
     - adds the key's SHA-1/SHA-256 to both;
     - checks that Google sign-in is enabled;
   - opens a draft release `v1.0.0-build.N`.
2. **Build** (user and admin in parallel):
   - `npm install`;
   - `scripts/ci/android-inputs.sh` writes `google-services.json` (the real one from Firebase, or a placeholder) and the signing key;
   - `expo prebuild` generates `android/`;
   - `./gradlew assembleRelease` with Hermes, R8 + resource shrinking and per-ABI splits (`armeabi-v7a`, `arm64-v8a`, `x86_64` + `universal`);
   - native libraries and the JS bundle are compressed, and only `en`/`hi` resources are kept (`packages/native/app.plugin.js`), so each phone downloads as little as possible.
3. **Verify** (`scripts/ci/collect-apks.sh`), for every APK:
   - `aapt2` confirms the package id, version, SDK levels, ABIs and permissions;
   - `apksigner verify` confirms the v2/v3 signature and signer certificate;
   - a size and SHA-256 are recorded.
   The results become `report.md` and `SHA256SUMS.txt`.
4. **Smoke test** (`scripts/ci/smoke-test.sh`, Android 14 emulator, x86_64 APK). It fails the build on any crash. See [TESTING.md](TESTING.md).
5. **Publish**: when both builds pass, the release notes are assembled from the reports and the release is published as *latest*. If anything fails, the draft is deleted. Nothing half-built is ever published.

The `x86_64` APK is used for the emulator only and isn't attached to releases. Every build's full output, including screenshots and logcat, is kept for 30 days as a workflow artifact.

## Test builds vs release builds

| | Test build | Release build |
| --- | --- | --- |
| When | `config/firebase-project.json` is empty | The project is configured |
| Firebase config | Placeholder (`devdarshan-not-configured`) | Real `google-services.json` from the project |
| Signing key | Throwaway key generated for that run | Upload key from Secret Manager (stable) |
| File names | `…-TEST.apk` | `DevDarshan-1.0.0-arm64-v8a.apk` etc. |
| Published | Rolling `test-build` pre-release (replaced each build) | GitHub Release |
| App behaviour | Shows "Almost ready, not connected" | Full app |

## APK sizes

Measured on the latest build:

| APK | DevDarshan | DevDarshan Admin |
| --- | --- | --- |
| arm64-v8a (most phones) | 14.0 MB | 14.3 MB |
| armeabi-v7a (older phones) | 13.2 MB | 13.5 MB |
| universal (all phones) | 32.2 MB | 32.5 MB |

Before the size work, the arm64 APK was 28.8 MB. The savings come from compressed native libraries and JS bundle, English/Hindi-only resources, and removing unused SDKs.

## Downloading

The repository is public, so <https://github.com/arghadeep752-commits/Gamesssssss/releases/latest> works on any phone without a GitHub account. A good **Update URL** for the admin app's minimum-version setting is the same link.

## Versioning

- `versionName` is `1.0.0`, set by `VERSION_NAME` in `android.yml` and `version` in each `app.config.ts`.
- `versionCode` is `run_number + 100`, so it always increases and installs upgrade in place.
- To force users to update, raise **Settings → Home content → Minimum supported version** in the admin app. Builds below it show an update screen that links to the *Update URL*.

## Signing key

The upload key never leaves Google Cloud except into a CI runner's temporary directory. **Losing it means existing installs can't be upgraded**, so the copy in Secret Manager is the one to protect. Don't delete the `devdarshan-android-upload-*` secrets.

If you publish on Google Play, enrol in Play App Signing and use this key as the *upload* key. Play then holds the app-signing key.

## Google Play (optional, later)

Play needs an Android App Bundle. Add `./gradlew bundleRelease` next to `assembleRelease` in `android.yml` and upload `app-release.aab`.

Also on Play:

- Add App Check and turn on enforcement (see [SECURITY.md](SECURITY.md)).
- Host [PRIVACY-POLICY.md](PRIVACY-POLICY.md) at a public URL; Play requires one.
- Data safety form answers: email, name and user ID for account management; app interactions (likes); no sharing; deletion available in the app.

## Re-running

GitHub → Actions → *Android APKs* → **Run workflow** lets you choose `both` / `user` / `admin` and whether to run the emulator test. *Firebase backend* can be re-run the same way.
