import { logger } from 'firebase-functions/v2';
import { onObjectFinalized } from 'firebase-functions/v2/storage';
import { STORAGE_REGION } from '../config';
import { processCategoryCoverUpload, processWallpaperUpload } from '../lib/wallpaperProcessing';
import { parseUploadPath } from '../shared/paths';

/**
 * Fires for every object written to the default bucket. Only staging uploads are
 * processed; the function's own outputs (wallpapers/, categories/) are ignored.
 * One image per instance keeps memory predictable on large uploads.
 */
export const processUpload = onObjectFinalized(
  {
    region: STORAGE_REGION,
    memory: '1GiB',
    cpu: 1,
    concurrency: 1,
    timeoutSeconds: 300,
    maxInstances: 5,
  },
  async (event) => {
    const path = event.data.name;
    const parsed = parseUploadPath(path);
    if (!parsed) return;
    const outcome =
      parsed.kind === 'wallpaper'
        ? await processWallpaperUpload(parsed.id, path)
        : await processCategoryCoverUpload(parsed.id, path);
    logger.info('Upload processed', { path, outcome });
  },
);
