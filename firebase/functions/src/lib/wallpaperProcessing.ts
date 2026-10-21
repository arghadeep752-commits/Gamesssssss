import { logger } from 'firebase-functions/v2';
import { FieldValue } from 'firebase-admin/firestore';
import { bucket, db } from '../firebase';
import { COLLECTIONS, STATS_DOC_ID } from '../shared/constants';
import { categoryOutputPaths, wallpaperOutputPaths, wallpaperOutputPrefix } from '../shared/paths';
import { writeAdminLog } from './audit';
import { ImageRejectedError, processCoverImage, processWallpaperImage } from './imageProcessing';
import { deleteObject, deletePrefix, saveWithToken } from './storageFiles';

export type ProcessingOutcome = 'ready' | 'published' | 'failed' | 'skipped';

async function bumpStats(field: 'uploadsSucceeded' | 'uploadsFailed'): Promise<void> {
  await db()
    .collection(COLLECTIONS.stats)
    .doc(STATS_DOC_ID)
    .set({ [field]: FieldValue.increment(1), updatedAt: FieldValue.serverTimestamp() }, { merge: true });
}

/**
 * The recoverable upload workflow (Storage and Firestore share no transaction):
 *
 *  1. The admin app creates the wallpaper doc as a draft with processing="uploading".
 *  2. It uploads the source to uploads/wallpapers/{id}/source.{ext}.
 *  3. This function renders the outputs, writes them under wallpapers/{id}/, then
 *     commits URLs + metadata in a Firestore transaction and publishes if requested.
 *  4. The staging file is deleted only after the commit, so a failed run can be retried.
 *
 * Users only ever query status == "published", so a half-finished upload is never visible.
 * Uploads abandoned at step 2 are removed by the scheduled cleanup.
 */
export async function processWallpaperUpload(wallpaperId: string, stagingPath: string): Promise<ProcessingOutcome> {
  const ref = db().collection(COLLECTIONS.wallpapers).doc(wallpaperId);
  const snapshot = await ref.get();
  if (!snapshot.exists || snapshot.get('status') === 'deleting') {
    logger.warn('Upload without an active wallpaper document; removing it', { wallpaperId, stagingPath });
    await deleteObject(stagingPath);
    return 'skipped';
  }
  const title = String(snapshot.get('title') ?? wallpaperId);
  await ref.update({ processing: 'processing', processingError: null });

  let processed;
  try {
    const [buffer] = await bucket().file(stagingPath).download();
    processed = await processWallpaperImage(buffer);
  } catch (error) {
    const rejected = error instanceof ImageRejectedError;
    const message = rejected ? error.message : 'Processing failed. Retry, or replace the image.';
    logger.error('Wallpaper processing failed', { wallpaperId, error: String(error) });
    await ref.update({ processing: 'failed', processingError: message });
    // An unreadable source will never succeed, so it is not kept for retries.
    if (rejected) await deleteObject(stagingPath);
    await bumpStats('uploadsFailed');
    await writeAdminLog({
      action: 'wallpaper.processingFailed',
      targetType: 'wallpaper',
      targetId: wallpaperId,
      targetLabel: title,
      actorUid: 'system',
      details: message,
    });
    return 'failed';
  }

  const paths = wallpaperOutputPaths(wallpaperId, processed.original.ext);
  const [originalUrl, previewUrl, thumbnailUrl] = await Promise.all([
    saveWithToken(paths.original, processed.original.buffer, processed.original.contentType),
    saveWithToken(paths.preview, processed.preview.buffer, 'image/webp'),
    saveWithToken(paths.thumbnail, processed.thumbnail.buffer, 'image/webp'),
  ]);

  // A replacement in a different format leaves the old original behind; remove it.
  const [oldOriginals] = await bucket().getFiles({ prefix: `${wallpaperOutputPrefix(wallpaperId)}original.` });
  await Promise.all(oldOriginals.filter((f) => f.name !== paths.original).map((f) => f.delete({ ignoreNotFound: true })));

  const commit = await db().runTransaction(async (tx) => {
    const current = await tx.get(ref);
    if (!current.exists || current.get('status') === 'deleting') return null;
    const wasPublished = current.get('status') === 'published';
    const publishNow = !wasPublished && current.get('requestedStatus') === 'published';
    const update: Record<string, unknown> = {
      originalStoragePath: paths.original,
      previewStoragePath: paths.preview,
      thumbnailStoragePath: paths.thumbnail,
      originalUrl,
      previewUrl,
      thumbnailUrl,
      width: processed.original.width,
      height: processed.original.height,
      aspectRatio: processed.original.width / processed.original.height,
      fileSizeBytes: processed.original.buffer.length,
      mimeType: processed.original.contentType,
      placeholder: processed.placeholder,
      dominantColor: processed.dominantColor,
      imageVersion: FieldValue.increment(1),
      processing: 'ready',
      processingError: null,
      processedAt: FieldValue.serverTimestamp(),
      favoriteCount: current.get('favoriteCount') ?? 0,
      downloadCount: current.get('downloadCount') ?? 0,
      featured: current.get('featured') ?? false,
    };
    if (publishNow) {
      update.status = 'published';
      if (!current.get('publishedAt')) update.publishedAt = FieldValue.serverTimestamp();
    }
    tx.update(ref, update);
    return { publishNow, replaced: Number(current.get('imageVersion') ?? 0) > 0 };
  });

  if (!commit) {
    // Deleted while we were working: remove everything we just wrote.
    await deletePrefix(wallpaperOutputPrefix(wallpaperId));
    await deleteObject(stagingPath);
    return 'skipped';
  }

  await deleteObject(stagingPath);
  await bumpStats('uploadsSucceeded');
  await writeAdminLog({
    action: commit.replaced ? 'wallpaper.imageReplaced' : 'wallpaper.processed',
    targetType: 'wallpaper',
    targetId: wallpaperId,
    targetLabel: title,
    actorUid: 'system',
    details: `${processed.original.width}×${processed.original.height}${commit.publishNow ? ', published' : ''}`,
  });
  return commit.publishNow ? 'published' : 'ready';
}

export async function processCategoryCoverUpload(categoryId: string, stagingPath: string): Promise<ProcessingOutcome> {
  const ref = db().collection(COLLECTIONS.categories).doc(categoryId);
  const snapshot = await ref.get();
  if (!snapshot.exists) {
    await deleteObject(stagingPath);
    return 'skipped';
  }
  let processed;
  try {
    const [buffer] = await bucket().file(stagingPath).download();
    processed = await processCoverImage(buffer);
  } catch (error) {
    logger.error('Category cover processing failed', { categoryId, error: String(error) });
    await deleteObject(stagingPath);
    return 'failed';
  }
  const paths = categoryOutputPaths(categoryId);
  const [coverUrl, coverThumbUrl] = await Promise.all([
    saveWithToken(paths.cover, processed.cover.buffer, 'image/webp'),
    saveWithToken(paths.coverThumb, processed.thumbnail.buffer, 'image/webp'),
  ]);
  try {
    await ref.update({
      coverImagePath: paths.cover,
      coverThumbnailPath: paths.coverThumb,
      coverUrl,
      coverThumbUrl,
      coverPlaceholder: processed.placeholder,
      coverUpdatedAt: FieldValue.serverTimestamp(),
    });
  } catch (error) {
    logger.warn('Category vanished during cover processing', { categoryId, error: String(error) });
    await deletePrefix(`categories/${categoryId}/`);
  }
  await deleteObject(stagingPath);
  return 'ready';
}
