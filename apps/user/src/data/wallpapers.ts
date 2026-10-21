import {
  collection,
  doc,
  documentId,
  getDoc,
  getDocs,
  limit,
  orderBy,
  query,
  startAfter,
  where,
  type DocumentData,
  type QueryDocumentSnapshot,
} from '@react-native-firebase/firestore';
import {
  COLLECTIONS,
  LIMITS,
  isDisplayable,
  matchesAllTerms,
  parseSearchQuery,
  toCategory,
  toWallpaper,
  type Category,
  type Wallpaper,
} from '@devdarshan/shared';
import { db } from '../firebase';

/**
 * All user-facing reads go through here. Every wallpaper query is constrained to
 * status == "published" (the security rules reject anything else), paginated
 * with cursors, and served from Firestore's on-device cache when offline.
 */

export type Cursor = QueryDocumentSnapshot<DocumentData> | null;

export interface WallpaperPage {
  items: Wallpaper[];
  cursor: Cursor;
}

const wallpapers = () => collection(db, COLLECTIONS.wallpapers);

function toPage(docs: QueryDocumentSnapshot<DocumentData>[], pageSize: number): WallpaperPage {
  return {
    items: docs.map((d) => toWallpaper(d.id, d.data())).filter(isDisplayable),
    cursor: docs.length === pageSize ? (docs[docs.length - 1] ?? null) : null,
  };
}

export async function fetchLatestPage(cursor: Cursor, pageSize: number = LIMITS.pageSize): Promise<WallpaperPage> {
  const base = query(wallpapers(), where('status', '==', 'published'), orderBy('publishedAt', 'desc'));
  const snap = await getDocs(cursor ? query(base, startAfter(cursor), limit(pageSize)) : query(base, limit(pageSize)));
  return toPage(snap.docs, pageSize);
}

export async function fetchCategoryPage(
  categoryId: string,
  cursor: Cursor,
  pageSize: number = LIMITS.pageSize,
): Promise<WallpaperPage> {
  const base = query(
    wallpapers(),
    where('status', '==', 'published'),
    where('categoryIds', 'array-contains', categoryId),
    orderBy('publishedAt', 'desc'),
  );
  const snap = await getDocs(cursor ? query(base, startAfter(cursor), limit(pageSize)) : query(base, limit(pageSize)));
  return toPage(snap.docs, pageSize);
}

/** One indexed term goes to Firestore; every other term is matched on the device. */
export async function searchWallpapers(input: string): Promise<Wallpaper[]> {
  const parsed = parseSearchQuery(input);
  if (!parsed.term) return [];
  const snap = await getDocs(
    query(
      wallpapers(),
      where('status', '==', 'published'),
      where('searchKeywords', 'array-contains', parsed.term),
      orderBy('publishedAt', 'desc'),
      limit(60),
    ),
  );
  return snap.docs
    .map((d) => toWallpaper(d.id, d.data()))
    .filter((w) => isDisplayable(w) && matchesAllTerms(w.searchKeywords, parsed.terms));
}

/** Fetches published wallpapers by id (30 per query, Firestore's `in` limit), keeping the given order. */
export async function fetchWallpapersByIds(ids: readonly string[]): Promise<{ items: Wallpaper[]; missing: string[] }> {
  const unique = [...new Set(ids)].filter(Boolean);
  const found = new Map<string, Wallpaper>();
  for (let i = 0; i < unique.length; i += 30) {
    const chunk = unique.slice(i, i + 30);
    const snap = await getDocs(query(wallpapers(), where(documentId(), 'in', chunk), where('status', '==', 'published')));
    snap.docs.forEach((d) => {
      const w = toWallpaper(d.id, d.data());
      if (isDisplayable(w)) found.set(w.id, w);
    });
  }
  const items: Wallpaper[] = [];
  const missing: string[] = [];
  for (const id of unique) {
    const w = found.get(id);
    if (w) items.push(w);
    else missing.push(id);
  }
  return { items, missing };
}

export async function fetchWallpaper(id: string): Promise<Wallpaper | null> {
  try {
    const snap = await getDoc(doc(db, COLLECTIONS.wallpapers, id));
    if (!snap.exists()) return null;
    const w = toWallpaper(snap.id, snap.data());
    return isDisplayable(w) ? w : null;
  } catch {
    // Unpublished wallpapers are unreadable by design (permission-denied): treat as unavailable.
    return null;
  }
}

export async function fetchCategories(): Promise<Category[]> {
  const snap = await getDocs(
    query(collection(db, COLLECTIONS.categories), where('isActive', '==', true), orderBy('sortOrder', 'asc'), limit(200)),
  );
  return snap.docs.map((d) => toCategory(d.id, d.data()));
}
