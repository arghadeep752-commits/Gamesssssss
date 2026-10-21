# Security

## Secrets: what is, and isn't, in the apps

| Item | Where it lives |
| --- | --- |
| Service-account keys | **None exist.** GitHub Actions authenticates to Google Cloud with Workload Identity Federation. Trust is limited to this repository's numeric id **and** its `main` branch (`assertion.repository_id == '1418506005' && assertion.ref == 'refs/heads/main'`). |
| Android upload (signing) key | Generated in CI on the first configured run and stored only in **Google Secret Manager** (`devdarshan-android-upload-keystore`, with a random password in `devdarshan-android-upload-password`). It is never committed, printed or stored in GitHub, and it is deleted from the runner after use. |
| `google-services.json` | Fetched at build time and never committed. It holds *public* identifiers (API key, app id, web OAuth client id). They are not secrets: access is controlled by the security rules, and (once enforced) App Check. |
| OAuth client secret | **Not used.** Android sign-in uses Credential Manager with the public web client id. |
| Admin bootstrap email | `firebase/functions/.env`, stored as a **SHA-256 hash** so the address isn't published. It is not a credential: a Google-verified sign-in with the matching email is still required, and it only works while no admin exists. |

## Public repository

The code is public on purpose: it contains no secrets, and every protection is enforced by the backend.

- **Forks and pull requests can't deploy or sign builds.** The deploy and build workflows run only on pushes to `main` or manual runs by maintainers, and Google Cloud only trusts tokens from `main` of this repository.
- **The admin APK is public too, and that is fine.** Installing it grants nothing: admin rights live in a server-set claim and role document.

## Admin authorization

An account is an admin **only if both** of these are true:

1. its ID token has the custom claim `admin: true`, which can only be set by Cloud Functions with the Admin SDK; and
2. `adminRoles/{uid}` exists. The rules deny every client write to that collection.

Firestore rules, Storage rules and every admin callable (`requireAdmin`) all check both. The admin app's screens are only a convenience. Hiding or showing UI grants nothing.

| Path to admin | Safeguards |
| --- | --- |
| `bootstrapAdmin` | Requires a signed-in account whose **Google-verified** email matches the configured hash (`DEVDARSHAN_ADMIN_BOOTSTRAP_EMAIL_SHA256`). Refuses once any other admin exists. Writes an audit entry. |
| `setAdminRole` | Admins only. Grants or revokes by email. The last admin can't be removed. Revoking deletes the role document first (instantly blocks rules and functions), then clears the claim and **revokes refresh tokens**. |

Normal users can't create claims or role documents, so there is no way to grant oneself access.

## Firestore rules (`firebase/firestore.rules`)

- **Default deny.** Anything not matched is refused.
- **Wallpapers.**
  - Anyone can read published wallpapers.
  - Admins may create *drafts* with an exact field list and validated values. They may then update only editorial fields (title, description, categories, tags, status, requested status) and the narrow upload-state transitions.
  - Image URLs, storage paths, sizes, counters, search keywords, `featured` and `publishedAt` are server-only.
  - Publishing requires `processing == ready`.
  - Direct deletes are denied: `deleteWallpaper` removes the files, featured entry and favourites safely.
- **Categories.** Slug ids. Validated, admin-only writes. Deletes go through `deleteCategory`, which never leaves wallpapers without a category.
- **`appConfig/public`.** Readable by anyone. Admin writes are validated per field, with list sizes capped.
- **Favourites.** Owner-only, limited to `{wallpaperId, createdAt}`, and only for published wallpapers. No one, including admins, can list other users' favourites. Totals are computed server-side.
- **`adminRoles`, `adminLog`, `stats`.** No client writes.

The rules are covered by emulator tests (`firebase/rules-tests`), which run in CI on every push.

## Storage rules (`firebase/storage.rules`)

- Uploads are allowed only for admins, only into `uploads/…` with a fixed file name, image content types (`image/jpeg|png|webp`), and size limits (30 MB wallpapers, 15 MB covers).
- Processed files can be written only by Cloud Functions.
- Wallpaper files are readable only when the wallpaper is published, or by admins.

Cross-service rules (the Storage rules read `adminRoles` from Firestore) need the `firebaserules.firestoreServiceAgent` role. The setup script and the backend workflow grant it.

## Untrusted input

- **Callables** validate their input with zod schemas (`packages/shared/src/validation.ts`).
- **Images** are decoded with sharp before anything else:
  - format sniffing, so the declared type can't lie;
  - a 100 MP input cap against decompression bombs;
  - a minimum resolution;
  - auto-orientation. Any file carrying EXIF (including GPS), XMP or IPTC metadata is re-encoded without it, so stored originals never keep it.
  Rejected files fail with a readable reason and the staged upload is deleted.
- **Counters** are never trusted from clients: favourite counts and category counts use exact server-side aggregation.

## Android permissions

| App | Permissions |
| --- | --- |
| DevDarshan | `INTERNET`, `ACCESS_NETWORK_STATE` (from libraries), `SET_WALLPAPER`, and `WRITE_EXTERNAL_STORAGE` **capped at Android 9** (`maxSdkVersion=28`, used only for saving on old devices). It asks for no media, camera, audio, location, contacts or ad-ID permissions; those are explicitly blocked. |
| DevDarshan Admin | Network only. Images are chosen through the **system photo picker**, which needs no storage permission. Storage, media, camera and wallpaper permissions are blocked. |

Sharing uses a `FileProvider` scoped to one cache sub-directory (`devdarshan-share/`). No `file://` URIs are exposed.

## App Check

The apps initialise App Check with Play Integrity. Functions can enforce it (`DEVDARSHAN_ENFORCE_APP_CHECK=true` in `firebase/functions/.env`), and Firestore and Storage enforcement can be switched on in the Firebase console.

**Keep it off while distributing APKs outside Google Play.** Play Integrity can't vouch for sideloaded installs, so enforcement would lock those users out. When the app is published on Google Play:

1. Register both apps under App Check → Play Integrity.
2. Watch the metrics for a few days.
3. Then enforce.

## Known limitations

- **Download counts are best-effort.** `recordDownload` accepts guest calls (downloads don't need sign-in), so a determined person could inflate the counter. It only feeds statistics. App Check enforcement (via Google Play) closes this.
- **Unpublishing doesn't revoke file URLs** someone already has. Deleting a wallpaper removes its files, and replacing the image issues new URLs.
- **Accounts.** The admin app relies on Google accounts, so protect the admin Google accounts with 2-Step Verification.

## Privacy

DevDarshan stores only what the features need: favourites (wallpaper id + time) for signed-in users. Display name and photo come from Firebase Auth and aren't copied. There is no analytics, advertising or tracking SDK. Users can delete their account and favourites from **Profile → Delete account**. See [PRIVACY-POLICY.md](PRIVACY-POLICY.md).

## Reporting a vulnerability

Email the support address shown in the app (Profile → Send feedback) with details. Please don't disclose it publicly until it's fixed.
