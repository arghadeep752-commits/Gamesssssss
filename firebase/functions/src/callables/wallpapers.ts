import { HttpsError, onCall } from 'firebase-functions/v2/https';
import { FieldValue } from 'firebase-admin/firestore';
import { CALLABLE_REGION, ENFORCE_APP_CHECK } from '../config';
import { db } from '../firebase';
import { writeAdminLog } from '../lib/audit';
import { parseInput, requireAdmin } from '../lib/callable';
import { deletePrefix, findFirstObject } from '../lib/storageFiles';
import { processWallpaperUpload } from '../lib/wallpaperProcessing';
import { APP_CONFIG_DOC_ID, COLLECTIONS, STATS_DOC_ID } from '../shared/constants';
import { wallpaperOutputPrefix, wallpaperUploadPrefix } from '../shared/paths';
import { deleteWallpaperInput, recordDownloadInput, retryProcessingInput } from '../shared/validation';

/**
 * Deletes a wallpaper everywhere, in an order that is safe to retry:
 *  1. mark it "deleting" (immediately hidden from users),
 *  2. delete its files, 3. drop it from the featured list,
 *  4. delete every user's favourite of it, 5. delete the document.
 * If any step fails the document stays "deleting" and the admin can run it again.
 */
export const deleteWallpaper = onCall(
  { region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK, timeoutSeconds: 300 },
  async (request) => {
    const caller = await requireAdmin(request);
    const { wallpaperId } = parseInput(deleteWallpaperInput, request.data);
    const ref = db().collection(COLLECTIONS.wallpapers).doc(wallpaperId);
    const snapshot = await ref.get();
    if (!snapshot.exists) return { ok: true, alreadyDeleted: true };
    const title = String(snapshot.get('title') ?? wallpaperId);

    await ref.update({ status: 'deleting', deletingAt: FieldValue.serverTimestamp() });
    await deletePrefix(wallpaperOutputPrefix(wallpaperId));
    await deletePrefix(wallpaperUploadPrefix(wallpaperId));
    await db()
      .collection(COLLECTIONS.appConfig)
      .doc(APP_CONFIG_DOC_ID)
      .set({ featuredWallpaperIds: FieldValue.arrayRemove(wallpaperId) }, { merge: true });

    let removedFavorites = 0;
    for (;;) {
      const favorites = await db()
        .collectionGroup(COLLECTIONS.favorites)
        .where('wallpaperId', '==', wallpaperId)
        .limit(400)
        .get();
      if (favorites.empty) break;
      const batch = db().batch();
      favorites.docs.forEach((doc) => batch.delete(doc.ref));
      await batch.commit();
      removedFavorites += favorites.size;
    }

    await ref.delete();
    await writeAdminLog({
      action: 'wallpaper.deleted',
      targetType: 'wallpaper',
      targetId: wallpaperId,
      targetLabel: title,
      actorUid: caller.uid,
      details: removedFavorites ? `Removed from ${removedFavorites} favourites` : null,
    });
    return { ok: true, removedFavorites };
  },
);

/** Re-runs processing on the staged upload after a transient failure. */
export const retryWallpaperProcessing = onCall(
  { region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK, memory: '1GiB', timeoutSeconds: 300 },
  async (request) => {
    await requireAdmin(request);
    const { wallpaperId } = parseInput(retryProcessingInput, request.data);
    const staged = await findFirstObject(wallpaperUploadPrefix(wallpaperId));
    if (!staged) {
      throw new HttpsError('failed-precondition', 'The uploaded file is no longer available. Use "Replace image" to upload it again.');
    }
    const outcome = await processWallpaperUpload(wallpaperId, staged);
    return { ok: outcome !== 'failed', outcome };
  },
);

/**
 * Counts a download. Callable by anyone (signed in or not); the count is a single
 * number per wallpaper and is never linked to a person.
 */
export const recordDownload = onCall({ region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK }, async (request) => {
  const { wallpaperId } = parseInput(recordDownloadInput, request.data);
  const ref = db().collection(COLLECTIONS.wallpapers).doc(wallpaperId);
  const snapshot = await ref.get();
  if (!snapshot.exists || snapshot.get('status') !== 'published') {
    throw new HttpsError('not-found', 'This wallpaper is no longer available.');
  }
  await Promise.all([
    ref.update({ downloadCount: FieldValue.increment(1) }),
    db()
      .collection(COLLECTIONS.stats)
      .doc(STATS_DOC_ID)
      .set({ totalDownloads: FieldValue.increment(1), updatedAt: FieldValue.serverTimestamp() }, { merge: true }),
  ]);
  return { ok: true };
});
