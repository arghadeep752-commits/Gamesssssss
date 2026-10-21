import { randomUUID } from 'node:crypto';
import { bucket } from '../firebase';
import { firebaseDownloadUrl } from '../shared/paths';

/**
 * Writes an object with a fresh Firebase download token and returns its public
 * URL. A new token per write means a replaced image gets a new URL, so phones
 * never show a stale cached copy.
 */
export async function saveWithToken(path: string, data: Buffer, contentType: string): Promise<string> {
  const target = bucket();
  const token = randomUUID();
  await target.file(path).save(data, {
    resumable: false,
    metadata: {
      contentType,
      cacheControl: 'public, max-age=31536000',
      metadata: { firebaseStorageDownloadTokens: token },
    },
  });
  return firebaseDownloadUrl(target.name, path, token);
}

export async function deletePrefix(prefix: string): Promise<void> {
  await bucket().deleteFiles({ prefix, force: true });
}

export async function deleteObject(path: string): Promise<void> {
  await bucket().file(path).delete({ ignoreNotFound: true });
}

export async function findFirstObject(prefix: string): Promise<string | null> {
  const [files] = await bucket().getFiles({ prefix, maxResults: 5 });
  return files[0]?.name ?? null;
}
