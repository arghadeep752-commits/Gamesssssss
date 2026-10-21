import {
  arrayRemove,
  arrayUnion,
  collection,
  doc,
  getDocs,
  limit,
  onSnapshot,
  orderBy,
  query,
  serverTimestamp,
  setDoc,
  startAfter,
  updateDoc,
  where,
  type DocumentData,
  type QueryDocumentSnapshot,
} from '@react-native-firebase/firestore';
import { putFile, ref } from '@react-native-firebase/storage';
import {
  APP_CONFIG_DOC_ID,
  CALLABLES,
  COLLECTIONS,
  LIMITS,
  matchesAllTerms,
  parseSearchQuery,
  toWallpaper,
  wallpaperUploadPath,
  type ImageExtension,
  type Wallpaper,
} from '@devdarshan/shared';
import { callFunction, db, storage } from '../firebase';

export type StatusFilter = 'all' | 'published' | 'draft' | 'attention';

export interface AdminFilter {
  status: StatusFilter;
  categoryId: string | null;
  search: string;
}

export type Cursor = QueryDocumentSnapshot<DocumentData> | null;

export interface AdminPage {
  items: Wallpaper[];
  cursor: Cursor;
}

const wallpapers = () => collection(db, COLLECTIONS.wallpapers);

/**
 * Admin list query. Firestore allows one array-contains filter per query, so the
 * server applies the most selective filter that has an index and the rest are
 * applied on the device.
 */
export async function fetchAdminPage(filter: AdminFilter, cursor: Cursor): Promise<AdminPage> {
  const search = parseSearchQuery(filter.search);
  const filters: ReturnType<typeof where>[] = [];
  let clientCategory: string | null = null;
  let clientAttention = false;

  if (search.term) {
    filters.push(where('searchKeywords', 'array-contains', search.term));
    clientCategory = filter.categoryId;
  } else if (filter.categoryId) {
    filters.push(where('categoryIds', 'array-contains', filter.categoryId));
  }
  if (filter.status === 'published' || filter.status === 'draft') {
    filters.push(where('status', '==', filter.status));
  } else if (filter.status === 'attention') {
    if (search.term || filter.categoryId) {
      clientAttention = true;
      clientCategory = clientCategory ?? null;
    } else {
      filters.push(where('processing', 'in', ['uploading', 'processing', 'failed']));
    }
  }

  const base = query(wallpapers(), ...filters, orderBy('createdAt', 'desc'));
  const pageSize = LIMITS.adminPageSize;
  const snap = await getDocs(cursor ? query(base, startAfter(cursor), limit(pageSize)) : query(base, limit(pageSize)));
  const items = snap.docs
    .map((d) => toWallpaper(d.id, d.data()))
    .filter((w) => matchesAllTerms(w.searchKeywords, search.terms))
    .filter((w) => !clientCategory || w.categoryIds.includes(clientCategory))
    .filter((w) => !clientAttention || w.processing !== 'ready' || w.status === 'deleting');
  return { items, cursor: snap.docs.length === pageSize ? (snap.docs[snap.docs.length - 1] ?? null) : null };
}

export function watchWallpaper(id: string, onChange: (w: Wallpaper | null) => void, onError: (e: unknown) => void) {
  return onSnapshot(
    doc(db, COLLECTIONS.wallpapers, id),
    (snap) => onChange(snap.exists() ? toWallpaper(snap.id, snap.data()) : null),
    onError,
  );
}

export interface WallpaperDraftInput {
  title: string;
  description: string;
  categoryIds: string[];
  tags: string[];
  requestedStatus: 'draft' | 'published';
}

/** Step 1 of an upload: the draft document (hidden from users until processed). */
export async function createWallpaperDraft(input: WallpaperDraftInput, uid: string): Promise<string> {
  const target = doc(wallpapers());
  await setDoc(target, {
    title: input.title,
    description: input.description,
    categoryIds: input.categoryIds,
    tags: input.tags,
    status: 'draft',
    requestedStatus: input.requestedStatus,
    processing: 'uploading',
    processingError: null,
    createdAt: serverTimestamp(),
    updatedAt: serverTimestamp(),
    createdBy: uid,
    updatedBy: uid,
  });
  return target.id;
}

export interface UploadHandle {
  done: Promise<void>;
  cancel: () => void;
}

/** Step 2: upload the source image with real byte progress. Processing starts on the server when it finishes. */
export function uploadWallpaperSource(
  wallpaperId: string,
  localUri: string,
  ext: ImageExtension,
  contentType: string,
  onProgress: (fraction: number) => void,
): UploadHandle {
  const task = putFile(ref(storage, wallpaperUploadPath(wallpaperId, ext)), localUri, {
    contentType,
    customMetadata: { wallpaperId },
  });
  const unsubscribe = task.on('state_changed', (snapshot) => {
    if (snapshot.totalBytes > 0) onProgress(snapshot.bytesTransferred / snapshot.totalBytes);
  });
  const done = Promise.resolve(task).then(
    () => {
      if (typeof unsubscribe === 'function') unsubscribe();
    },
    (error: unknown) => {
      if (typeof unsubscribe === 'function') unsubscribe();
      throw error;
    },
  );
  return { done, cancel: () => void task.cancel() };
}

export async function updateWallpaperMeta(id: string, input: WallpaperDraftInput, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.wallpapers, id), {
    title: input.title,
    description: input.description,
    categoryIds: input.categoryIds,
    tags: input.tags,
    requestedStatus: input.requestedStatus,
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

export async function setPublished(id: string, publish: boolean, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.wallpapers, id), {
    status: publish ? 'published' : 'draft',
    requestedStatus: publish ? 'published' : 'draft',
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

/** Before uploading a replacement image (or retrying a failed upload). */
export async function beginReplacement(id: string, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.wallpapers, id), {
    processing: 'uploading',
    processingError: null,
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

export async function markUploadFailed(id: string, message: string, uid: string): Promise<void> {
  await updateDoc(doc(db, COLLECTIONS.wallpapers, id), {
    processing: 'failed',
    processingError: `Upload failed: ${message}`.slice(0, 280),
    updatedAt: serverTimestamp(),
    updatedBy: uid,
  });
}

export async function setFeatured(id: string, featured: boolean, uid: string): Promise<void> {
  await setDoc(
    doc(db, COLLECTIONS.appConfig, APP_CONFIG_DOC_ID),
    {
      featuredWallpaperIds: featured ? arrayUnion(id) : arrayRemove(id),
      updatedAt: serverTimestamp(),
      updatedBy: uid,
    },
    { merge: true },
  );
}

export function deleteWallpaper(id: string) {
  return callFunction<{ wallpaperId: string }, { ok: boolean; removedFavorites?: number }>(CALLABLES.deleteWallpaper, {
    wallpaperId: id,
  });
}

export function retryProcessing(id: string) {
  return callFunction<{ wallpaperId: string }, { ok: boolean; outcome: string }>(CALLABLES.retryWallpaperProcessing, {
    wallpaperId: id,
  });
}
