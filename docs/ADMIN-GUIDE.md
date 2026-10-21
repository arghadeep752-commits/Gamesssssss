# DevDarshan Admin: guide

The admin app (green icon, **DevDarshan Admin**) is the only way to add or change what users see. It works with any Google account that has been made an admin.

## Signing in

1. Open the app → **Sign in with Google**.
2. If the account is an admin, the dashboard opens.
3. If not, you'll see *Admin access needed*:
   - the **first** admin taps **Claim admin access** (see [SETUP-FROM-PHONE.md](SETUP-FROM-PHONE.md), step 9);
   - anyone else needs an existing admin to add their email under **Settings → Admins**. They must have signed in once before they can be added.

## Dashboard

Exact counts of wallpapers (total, published, drafts, needing attention) and categories. It also shows total downloads and likes, how many uploads succeeded or failed, the latest uploads and recent admin activity. Pull down to refresh.

## Uploading a wallpaper

**Wallpapers → +**

1. **Choose an image** with the system photo picker.
   - JPEG, PNG or WebP. HEIC isn't accepted: export it as JPEG first.
   - At least **600 px** on the short side, at most **30 MB**.
   - Portrait images (about 9:19.5, for example 1440 × 3120) look best on phones.
2. **Title** (2–80 characters), optional **description**, 1–5 **categories**, and up to 15 **tags**, comma-separated. Tags and categories make search work, for example *ganesh, ganpati, vinayak*.
3. **Publish when ready**: on, the wallpaper goes live as soon as processing finishes; off, it stays a draft.
4. Tap **Upload**. The progress bar shows the real bytes sent.

After the upload, the server:

- checks the file;
- straightens rotated photos;
- removes hidden metadata (such as location);
- makes the preview, the thumbnail and the blurred placeholder.

This usually takes a few seconds and the status updates live: *Uploading → Processing → Ready*. If it shows **Failed**, the reason is shown (for example "too small"), and **Retry** or **Replace image** fixes it.

You can leave the screen during processing. If the app closes mid-upload, the half-finished draft is cleaned up automatically within a day.

## Editing

Open any wallpaper to:

- change its text, categories or tags (search keywords update automatically);
- **Publish / Unpublish**. Unpublished wallpapers disappear from the user app at once, and favourites of them are kept but hidden;
- **Feature in Today's Darshan**;
- **Replace image**. Everyone sees the new image, and phones that cached the old one download the new version;
- **Delete**. This removes the files, the featured entry and every user's like of it, and can't be undone.

## Categories

**Categories** tab:

- **+** creates a category: English and Hindi names, an id (letters, numbers and hyphens, used in links, can't be changed later), and an optional description.
- **Cover image** (optional). Without one, the app shows the Hindi name as artwork.
- **Visible in the app**: hidden categories keep their wallpapers but disappear from browsing.
- **Reorder** with the arrows.
- **Delete**: if wallpapers use the category, choose where to move them first. Wallpapers are never left without a category.

**Settings → Add starter categories** creates any of the 20 starter categories that are missing. It's safe to tap more than once.

## Home screen content

**Settings → Home content**:

| Setting | What it does |
| --- | --- |
| Today's Darshan | Up to 30 featured wallpapers, in your order (published ones only). |
| Home categories | The category row on the home screen. Empty means "all active categories". |
| Festival collection | On or off, a title (English and Hindi) and the category to show, for example *Navratri*. |
| Section order | The order of Today's Darshan, categories and the festival collection. "Latest" is always last. |
| Maintenance mode | Replaces the user app with your message. Use it for big changes. |
| Minimum supported version | Builds older than this version code must update first. The *Update URL* is where the button goes. |
| Support email / share message | Used by "Send feedback" and attached when users share. |

Tap **Save**. Users get changes on their next refresh or app start.

## Admins and activity

- **Settings → Admins**: add by Google email or remove. Removal ends that person's sessions straight away. The last admin can't be removed.
- **Settings → Activity log**: who uploaded, published, edited or deleted what, and when. It is written by the server, so it can't be edited.

## Good practice

- Upload only images you have the right to use. The Terms ask users to report infringements, and **Delete** removes everything.
- Use clear titles in English. Search also matches Hindi category names and common spellings (*shree / shri*, *ganesha / ganesh*).
- Protect admin Google accounts with 2-Step Verification.
