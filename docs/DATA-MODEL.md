# Data model

Cloud Firestore (database `(default)`, normally `asia-south1`) and Cloud Storage (the Firebase default bucket, normally `us-central1`).

The TypeScript shapes live in `packages/shared/src/types.ts` and the mappers in `packages/shared/src/mappers.ts`. The mappers turn Firestore timestamps into epoch milliseconds and give every missing field a safe default.

Key: **C** = written by clients (admins, through security rules) · **F** = written only by Cloud Functions · **U** = written by the signed-in user.

## `wallpapers/{wallpaperId}`

The id is auto-generated (≤ 40 characters).

| Field | Type | Who | Notes |
| --- | --- | --- | --- |
| `title` | string 2–80 | C | |
| `description` | string ≤ 500 | C | Excluded from indexing. |
| `categoryIds` | string[] 1–5 | C | Category ids (slugs). |
| `tags` | string[] ≤ 15 | C | Lower-case, each ≤ 32 characters. |
| `status` | `draft` \| `published` \| `deleting` | C / F | Clients may publish only when `processing == ready`. `deleting` is set by `deleteWallpaper`. |
| `requestedStatus` | `draft` \| `published` | C | "Publish when ready": the processor publishes automatically on success. |
| `processing` | `uploading` \| `processing` \| `ready` \| `failed` | C / F | Clients may only move `ready/failed → uploading` (replacement) or `uploading → failed` (their own failed upload). |
| `processingError` | string \| null | C / F | Readable reason shown in the admin app. |
| `originalUrl`, `previewUrl`, `thumbnailUrl` | string | F | Firebase download-token URLs. Every write gets a new token. |
| `originalStoragePath`, `previewStoragePath`, `thumbnailStoragePath` | string | F | |
| `width`, `height`, `aspectRatio`, `fileSizeBytes`, `mimeType` | | F | From the processed original. |
| `placeholder` | string | F | ~16 px WebP data URI for blur-up loading. Excluded from indexing. |
| `dominantColor` | `#rrggbb` | F | Background while loading. |
| `imageVersion` | number | F | +1 on every successful (re)processing. It keys device caches. |
| `featured` | bool | F | Mirrors `appConfig/public.featuredWallpaperIds`. |
| `favoriteCount`, `downloadCount` | number | F | Exact favourite count (aggregation), download counter. |
| `searchKeywords` | string[] ≤ 250 | F | Prefix keywords from the title, tags and category names (see ARCHITECTURE.md → Search). |
| `titleLower` | string | F | |
| `createdAt`, `updatedAt` | timestamp | C | Must equal the request time (rules). |
| `createdBy`, `updatedBy` | uid | C | Must equal the caller (rules). |
| `publishedAt` | timestamp | F | Set the first time it becomes published. It orders the user feeds. |
| `processedAt` | timestamp | F | |

**Readable by:** everyone when `status == published`, plus admins. **Deleted by:** the `deleteWallpaper` function only, which also removes its files, featured entry and every favourite.

## `categories/{slug}`

The id is the slug: `^[a-z0-9][a-z0-9-]{1,47}$`, for example `shri-ram`.

| Field | Type | Who | Notes |
| --- | --- | --- | --- |
| `name`, `nameHi` | string ≤ 60 | C | English and Hindi names. |
| `slug` | string | C | Equals the document id. |
| `description` | string ≤ 300 | C | |
| `sortOrder` | number | C | Ascending. Starter categories use 10, 20, … 200. |
| `isActive` | bool | C | Hidden categories keep their wallpapers. |
| `wallpaperCount` | number | F | Exact count of *published* wallpapers (aggregation). |
| `coverUrl`, `coverThumbUrl`, `coverImagePath`, `coverThumbnailPath`, `coverPlaceholder` | | F | From an uploaded cover (optional). Without one, the app draws a Devanagari monogram. |
| `createdAt`, `updatedAt`, `updatedBy` | | C | |

**Readable by:** everyone when `isActive`, plus admins. **Deleted by:** `deleteCategory` only. If wallpapers still use the category, it requires a target category and moves them there.

## `appConfig/public`

One document that drives the user app's home screen and gates.

| Field | Notes |
| --- | --- |
| `featuredWallpaperIds` | ≤ 30, in display order (*Today's Darshan*). |
| `featuredCategoryIds` | ≤ 30, the home category row. |
| `homeSectionOrder` | Any order of `featured`, `categories`, `festival`; `latest` is always last. |
| `festival` | `{enabled, title, titleHi, categoryId}`, an optional festival collection. |
| `maintenanceMode`, `maintenanceMessage` | Shows a maintenance screen instead of the app. |
| `minimumSupportedVersionCode`, `updateUrl` | Builds below this version code show an update screen. |
| `supportEmail`, `shareMessage` | Feedback address, and the text attached when sharing. |
| `updatedAt`, `updatedBy` | |

**Readable by:** everyone (`get` only). **Writable by:** admins, with every field validated.

## `users/{uid}/favorites/{wallpaperId}`

| Field | Notes |
| --- | --- |
| `wallpaperId` | Equals the document id. |
| `createdAt` | Request time. |

Only the owner can read, create or delete these, and only for published wallpapers. No other data about users is stored. Profile name and photo come from the Google account through Firebase Auth and are not copied into Firestore. `deleteMyAccount` removes the favourites and the Auth account.

## Server-only collections

| Path | Contents | Read |
| --- | --- | --- |
| `adminRoles/{uid}` | `{uid, email, displayName, grantedBy, createdAt}` | The user themself, and admins. |
| `adminLog/{auto}` | `{action, targetType, targetId, targetLabel, actorUid, actorEmail, details, createdAt}` | Admins. |
| `stats/global` | `{totalDownloads, totalFavorites, uploadsSucceeded, uploadsFailed, updatedAt}` | Admins. |

## Indexes

`firebase/firestore.indexes.json` declares every composite index the apps use.

**User feeds**
- `status + publishedAt↓`
- `status + categoryIds[] + publishedAt↓`
- `status + searchKeywords[] + publishedAt↓`

**Admin lists**
- `status + createdAt↓`
- `processing + createdAt↓`
- `categoryIds[] + createdAt↓`
- `categoryIds[] + status + createdAt↓`
- `searchKeywords[] + createdAt↓`
- `searchKeywords[] + status + createdAt↓`

**Categories**
- `isActive + sortOrder`

**Field overrides**
- A collection-group index on `favorites.wallpaperId`, used for exact counts and deletes.
- `placeholder`, `description` and `coverPlaceholder` are excluded from indexing.

## Storage layout

| Path | Written by | Read by |
| --- | --- | --- |
| `uploads/wallpapers/{id}/source.{jpg,png,webp}` | Admins (≤ 30 MB, image types only) | Functions. Deleted after processing. |
| `uploads/categories/{slug}/cover.{jpg,png,webp}` | Admins (≤ 15 MB) | Functions. Deleted after processing. |
| `wallpapers/{id}/original.{ext}`, `preview.webp`, `thumb.webp` | Functions | Everyone if the wallpaper is published, plus admins. In practice apps use the token URLs. |
| `categories/{slug}/cover.webp`, `cover_thumb.webp` | Functions | Everyone. |

Image limits (`LIMITS` in `packages/shared/src/constants.ts`):

- Short edge ≥ 600 px.
- Originals are capped at 4096 px and stored byte-for-byte when they are already clean JPEGs. Otherwise they are re-encoded with orientation applied and metadata removed.
- Previews ≤ 1440 × 2560.
- Thumbnails ≤ 540 × 1200.
- Inputs are capped at 100 megapixels.
