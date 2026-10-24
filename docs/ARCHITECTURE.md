# Architecture

```
          ┌──────────────────────┐            ┌──────────────────────────┐
          │  DevDarshan (user)   │            │   DevDarshan Admin       │
          │  com.devdarshan.     │            │   com.devdarshan.admin   │
          │  wallpapers          │            │                          │
          └─────────┬────────────┘            └────────────┬─────────────┘
   reads published  │  favourites, callables     uploads to │ uploads/…, edits
   content          │                            drafts/meta│ via rules, callables
                    ▼                                        ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Firebase: Auth (Google) · Firestore (asia-south1) · Storage          │
   │           (us-central1)                                              │
   └──────────────┬─────────────────────────────────────┬─────────────────┘
                  │ triggers                            │ callables (asia-south1)
                  ▼                                     ▼
   ┌──────────────────────────────────────────────────────────────────────┐
   │ Cloud Functions v2 (Node 22): image processing (sharp), search       │
   │ keywords, exact counters, featured sync, audit log, admin roles,     │
   │ safe deletes, account deletion, scheduled cleanup                    │
   └──────────────────────────────────────────────────────────────────────┘
```

## Monorepo

npm workspaces: `apps/*` and `packages/*`. `firebase/functions` is a separate npm project, because Cloud Functions deploys it on its own. It receives a copy of `packages/shared/src` at build time (`scripts/sync-shared.mjs`), so the apps and the backend share one definition of constants, limits, search keywords, paths and validation.

Native projects are **generated**, not committed. `expo prebuild` creates `android/` from `app.config.ts` plus config plugins (Continuous Native Generation). Anything native that must be customised lives in a config plugin (`packages/native/app.plugin.js`), so a regenerated project is always identical.

## User app (`apps/user`)

| Layer | Contents |
| --- | --- |
| `src/firebase.ts` | Firebase instances and the `isBackendConfigured` flag (placeholder builds show an "almost ready" screen). |
| `src/data/*` | Firestore queries (paged by cursor), the live `appConfig/public` subscription, auth (Credential Manager, then Firebase), and favourites (live subscription with an optimistic overlay and rollback). |
| `src/features/useWallpaperActions.ts` | Set wallpaper / download / share. It downloads the original once into the native cache (with progress and cancel), then hands the file to the native module. |
| `src/components`, `src/screens` | UI: Home, Categories, Category, Search, Liked, Profile, Preview pager, Legal. |
| `src/state/*` | Small persisted settings (theme, recent searches) and the preview pager session. |

Server data goes through **TanStack Query** with `networkMode: 'offlineFirst'`. Firestore's offline cache answers when there is no connection. NetInfo drives an offline banner and query pausing, and AppState drives refetch on focus.

### Home screen

The admin controls it through `appConfig/public`: section order, *Today's Darshan* (featured wallpapers), home categories, an optional festival collection, maintenance mode, and the minimum supported version (an update gate). The "latest" grid is always last and pages 24 at a time.

### Preview, set, download, share

1. The preview pager shows the WebP preview (with a blur-up placeholder and dominant colour) and prefetches neighbours.
2. **Set wallpaper** → choose Home, Lock or Both → `downloadOriginal` (native, cached by id + image version) → `setWallpaper(path, target)`.
   - Kotlin calls `WallpaperManager.setStream(…, FLAG_SYSTEM)` and `…FLAG_LOCK` **separately** and returns `{home, lock, homeError, lockError}`.
   - The UI reports exactly what happened, including vendor launchers that manage the lock screen themselves.
3. **Download**:
   - Android 10+: MediaStore `Pictures/DevDarshan` with `IS_PENDING`, so no permission is needed.
   - Android 9 and below: `WRITE_EXTERNAL_STORAGE`, capped with `maxSdkVersion=28`.
   - It skips duplicates and records a download count once per session through a callable.
4. **Share**: the file is copied to a cache directory exposed only through a `FileProvider`, then shared straight to WhatsApp if it is installed, or through the system chooser otherwise. The app never reports success, because Android doesn't tell apps whether the user actually sent it.

### Sign-in

The native module asks Credential Manager for a Google ID token (`GetSignInWithGoogleOption` with the project's web client id). The app exchanges it with `signInWithCredential`. No OAuth secrets are in the app. Signing out also clears the Credential Manager state. Guests can browse, download, share and set wallpapers; favourites need sign-in.

## Admin app (`apps/admin`)

A separate APK with a green theme. `SessionProvider` decides what is shown:

`loading → signed-out → checking → not-admin | admin`

**Admin** means the ID token carries the `admin` custom claim **and** `adminRoles/{uid}` exists. This is the same test the security rules apply, and only Cloud Functions can create either. Until then only the gate screen renders, and query caches are cleared whenever access is lost.

| Screen | Purpose |
| --- | --- |
| Dashboard | Exact counts (aggregation queries), total downloads and likes (`stats/global`), uploads succeeded/failed, recent uploads, recent activity. |
| Wallpapers | Filter by status, category, search; paged. |
| Wallpaper editor | Upload with byte progress, live processing status, metadata, publish toggle, featured toggle, replace image, retry processing, delete. |
| Categories / Category editor | Create (slug id), rename, Hindi name, cover image, reorder, hide, delete (wallpapers must be moved first). |
| Home content | Today's Darshan order, home categories, festival collection, section order, maintenance mode, minimum version, update URL, support email, share text. |
| Admins | Add and remove admins by email (server-side; the last admin can't be removed). |
| Activity | The audit log written by Cloud Functions. |

## Upload pipeline

```
Admin app                    Storage                       Cloud Functions                 Firestore
─────────                    ───────                       ───────────────                 ─────────
create draft doc ───────────────────────────────────────────────────────────────────────▶ wallpapers/{id}
                                                                                            status=draft
                                                                                            processing=uploading
putFile uploads/wallpapers/{id}/source.jpg ─▶ object finalised ─▶ processUpload
                                                                  · validate type/size/dims
                                                                  · auto-orient, cap 4096 px,
                                                                    strip metadata
                                                                  · original + preview.webp
                                                                    + thumb.webp + placeholder
                                                                    + dominant colour
                                                                  · transaction: URLs, size,
                                                                    imageVersion+1, ready,   ──▶ processing=ready
                                                                    publish if requested         (status=published)
                                                                  · delete staging object
```

Failures set `processing=failed` with a readable message, and the editor offers **Retry** (the `retryWallpaperProcessing` callable). A scheduled job runs every 6 hours:

- It deletes drafts whose upload never finished within a day.
- It restores published wallpapers whose *replacement* upload stalled, so they keep their current image.
- It removes orphaned staging files.

Every output object gets a **fresh download token** on each write. Replacing an image therefore changes every URL, which defeats stale caches, and `imageVersion` keys the device cache.

## Derived data, written only by functions

| Data | Maintained by |
| --- | --- |
| `searchKeywords`, `titleLower`, `publishedAt` | `onWallpaperWritten` |
| `categories/{id}.wallpaperCount` | `onWallpaperWritten`, using an exact `count()` aggregation of published wallpapers |
| `wallpapers/{id}.favoriteCount`, `stats/global.totalFavorites` | `onFavoriteWritten` (exact counts) |
| `wallpapers/{id}.featured` | `onAppConfigWritten`, from `featuredWallpaperIds` |
| `downloadCount`, `stats/global.totalDownloads` | the `recordDownload` callable (guests too; the app calls it once per wallpaper per session; best-effort analytics, see SECURITY.md) |
| `adminLog/*` | every trigger and callable that changes content or roles |

## Performance

- Thumbnails (≤ 540 × 1200 WebP) in grids, previews (≤ 1440 × 2560 WebP) full screen. The original is downloaded only to set, save or share.
- FlashList v2 with recycling and `expo-image` with `recyclingKey`, memory + disk cache and blur-up placeholders.
- Paged queries (24 per page) with cursor pagination. No unbounded reads, and indexes are declared for every query.
- Release builds use R8 and resource shrinking, Hermes, and per-ABI APK splits.
- **Small downloads**:
  - native libraries and the Hermes bundle are stored compressed in the APK;
  - only English and Hindi resources are kept from libraries;
  - permissions and SDKs the app doesn't use (App Check, biometrics, push, install referrer) are left out.

## Search

Firestore has no full-text search, so the backend stores up to 250 **prefix keywords** per wallpaper. They are built from the title, tags, category names (English and Hindi), with folded spellings (`aa`→`a`, `ee`/`ii`→`i`, `oo`/`uu`→`u`, `w`→`v`, `ph`→`f`, so *shree* finds *shri*) and light stemming (`rama` → `ram`).

A query uses `array-contains` on its longest term, and the device filters on the remaining terms. The same `buildSearchKeywords` and `parseSearchQuery` code runs on both sides (`packages/shared/src/search.ts`).
