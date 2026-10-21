import { logger } from 'firebase-functions/v2';
import { onSchedule } from 'firebase-functions/v2/scheduler';
import { Timestamp } from 'firebase-admin/firestore';
import { CALLABLE_REGION } from '../config';
import { bucket, db } from '../firebase';
import { deletePrefix } from '../lib/storageFiles';
import { COLLECTIONS } from '../shared/constants';
import { parseUploadPath, wallpaperOutputPrefix, wallpaperUploadPrefix } from '../shared/paths';

const STALE_AFTER_MS = 24 * 60 * 60 * 1000;

/**
 * Every 6 hours:
 *  - drafts stuck in "uploading" for a day (the admin closed the app mid-upload)
 *    are deleted with their files; published wallpapers whose replacement upload
 *    stalled go back to "ready" and keep their current image;
 *  - staged uploads with no matching document are deleted.
 */
export const cleanupStaleUploads = onSchedule(
  { schedule: 'every 6 hours', region: CALLABLE_REGION, timeZone: 'Asia/Kolkata', timeoutSeconds: 540 },
  async () => {
    const cutoff = Timestamp.fromMillis(Date.now() - STALE_AFTER_MS);
    const stuck = await db()
      .collection(COLLECTIONS.wallpapers)
      .where('processing', '==', 'uploading')
      .where('createdAt', '<', cutoff)
      .orderBy('createdAt', 'desc') // matches the (processing, createdAt desc) index
      .limit(200)
      .get();

    let removedDrafts = 0;
    let restored = 0;
    for (const doc of stuck.docs) {
      const updatedAt = doc.get('updatedAt') as Timestamp | undefined;
      if (updatedAt && updatedAt.toMillis() > cutoff.toMillis()) continue; // recent replacement attempt
      if (doc.get('status') === 'published' || doc.get('originalUrl')) {
        await doc.ref.update({ processing: 'ready', processingError: null });
        await deletePrefix(wallpaperUploadPrefix(doc.id));
        restored += 1;
      } else {
        await deletePrefix(wallpaperUploadPrefix(doc.id));
        await deletePrefix(wallpaperOutputPrefix(doc.id));
        await doc.ref.delete();
        removedDrafts += 1;
      }
    }

    let orphanUploads = 0;
    const [files] = await bucket().getFiles({ prefix: 'uploads/', maxResults: 1000 });
    for (const file of files) {
      const created = Date.parse(String(file.metadata.timeCreated ?? ''));
      if (!Number.isFinite(created) || Date.now() - created < STALE_AFTER_MS) continue;
      const parsed = parseUploadPath(file.name);
      const collection = parsed?.kind === 'categoryCover' ? COLLECTIONS.categories : COLLECTIONS.wallpapers;
      const owner = parsed ? await db().collection(collection).doc(parsed.id).get() : null;
      const stillNeeded = owner?.exists && parsed?.kind === 'wallpaper' && owner.get('processing') === 'failed';
      if (!stillNeeded) {
        await file.delete({ ignoreNotFound: true });
        orphanUploads += 1;
      }
    }

    logger.info('Cleanup finished', { removedDrafts, restored, orphanUploads });
  },
);
