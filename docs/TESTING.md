# Testing

Every push runs these. Results appear under GitHub → Actions, and in each release's notes.

## Automated

| Suite | Where | What it proves |
| --- | --- | --- |
| **TypeScript** | `npm run typecheck` (Checks) | Both apps and all packages compile under `strict`. |
| **Shared unit tests** | `packages/shared/test` (Vitest) | Search keyword generation and query parsing (spelling folds, stemming, prefixes, caps), slugs, validation schemas, mappers (defaults, timestamps), storage-path parsing, tag parsing. |
| **Image pipeline tests** | `firebase/functions/test` (Vitest, real `sharp`) | Clean JPEGs are kept byte-for-byte; EXIF-rotated images are re-encoded upright; oversized images are capped at 4096 px; previews and thumbnails respect their bounds; placeholders and colours are generated; tiny, corrupt and unsupported files are rejected with readable reasons. |
| **Security rules tests** | `firebase/rules-tests` (emulators) | Allow/deny for guests, users and admins (see below). |
| **APK verification** | `scripts/ci/collect-apks.sh` | Each APK's package id, version code, SDK levels, ABIs and permissions (`aapt2`); v2/v3 signature and signer certificate (`apksigner`); size and SHA-256. |
| **Emulator smoke test** | `scripts/ci/smoke-test.sh` (Android 14, x86_64) | Install, launch and stay alive; no crash-buffer entries; the scenarios below. Screenshots, the UI dump and logcat are kept as artifacts. |

### Security rules coverage

- Guests read only published wallpapers, active categories and `appConfig/public`. They can't write anything.
- Signed-in users can't write content, can't touch `adminRoles`, `adminLog` or `stats`, and can't give themselves a claim or role.
- A user with only a forged-looking claim but **no role document** is refused, and so is a role document without the claim.
- Favourites: owners only, exact shape, published wallpapers only. Other users and admins can't read them.
- Admins:
  - can create drafts only with the exact field list;
  - can't write URLs, counters or keywords;
  - can't publish before processing is `ready`;
  - can't delete directly.
- Storage: admins only, `uploads/` only, image types and sizes only. Processed files are read-only, and unpublished files aren't readable by the public.

### Emulator scenarios

**Test builds** (no Firebase yet). The app shows *Almost ready* and a **Device self-test**. The smoke test taps it, and the app generates a labelled image and then:

1. sets it on **Home and Lock** through `WallpaperManager` (each destination reported separately). The test then confirms from outside the app that `dumpsys wallpaper` changed;
2. saves it with MediaStore. The test confirms the file exists in `Pictures/DevDarshan` and is indexed by MediaStore;
3. opens the share sheet through the `FileProvider`. The test confirms the system chooser is the resumed activity, then closes it.

**Release builds**:

- *User app*: visits every tab. When published wallpapers exist, it opens one, taps **Set wallpaper → Both screens**, waits for the app's confirmation and confirms the `dumpsys wallpaper` change.
- *Admin app*: the sign-in gate renders.

> The full set-wallpaper path in a release build needs at least one published wallpaper. After you upload the first one, re-run **Android APKs** to get that evidence too.

## Manual checklist (on a real phone)

Use this after installing a release:

- [ ] **Sign in** with Google, then sign out. Sign in on a second phone and see the same likes.
- [ ] **Like** a wallpaper while offline. It shows liked immediately, then syncs once you're back online.
- [ ] **Set wallpaper** to Home, then Lock, then Both. The message matches what actually changed. On Xiaomi, OPPO, vivo and Samsung, the app's hint helps if a theme app overrides the lock screen.
- [ ] **Download**: the image appears in the Gallery under *DevDarshan*. Downloading again says it's already saved.
- [ ] **Share to WhatsApp**: WhatsApp opens directly with the image. Without WhatsApp, the system chooser opens.
- [ ] **Airplane mode**: previously seen screens still load from cache, and the offline banner shows.
- [ ] **Admin**: upload, wait for *Ready*, publish, feature, replace the image (it updates in the user app), unpublish, delete. Add a category with a cover, reorder, hide. Add a second admin, remove them, and confirm their app loses access.
- [ ] **Home content**: change *Today's Darshan*, the section order and the festival collection. The user app follows after a refresh.
- [ ] **Maintenance mode** on, then off. **Minimum version** above the current build shows the update screen.
- [ ] **Delete account** removes likes and signs out.

## Running locally (optional)

With Node 22 and Java 21:

```bash
npm install
npm run typecheck
npm test --workspace @devdarshan/shared
(cd firebase/functions && npm install && npm test)
(cd firebase/rules-tests && npm install && npm test)   # starts the Firestore + Storage emulators
```
