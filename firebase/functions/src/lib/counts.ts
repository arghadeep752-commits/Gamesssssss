import { FieldValue } from 'firebase-admin/firestore';
import { db, isNotFound } from '../firebase';
import { COLLECTIONS, STATS_DOC_ID } from '../shared/constants';

/** Exact published-wallpaper count for one category (an aggregation query, ~1 read per 1000 entries). */
export async function recountCategory(categoryId: string): Promise<void> {
  const aggregate = await db()
    .collection(COLLECTIONS.wallpapers)
    .where('status', '==', 'published')
    .where('categoryIds', 'array-contains', categoryId)
    .count()
    .get();
  try {
    await db().collection(COLLECTIONS.categories).doc(categoryId).update({ wallpaperCount: aggregate.data().count });
  } catch (error) {
    if (!isNotFound(error)) throw error;
  }
}

/** Exact favourite count for one wallpaper, derived from the favourite documents themselves. */
export async function recountFavorites(wallpaperId: string): Promise<void> {
  const aggregate = await db()
    .collectionGroup(COLLECTIONS.favorites)
    .where('wallpaperId', '==', wallpaperId)
    .count()
    .get();
  try {
    await db().collection(COLLECTIONS.wallpapers).doc(wallpaperId).update({ favoriteCount: aggregate.data().count });
  } catch (error) {
    if (!isNotFound(error)) throw error;
  }
}

/**
 * Exact total of likes across all users, kept in stats/global so the admin
 * dashboard can show it without any access to individual users' favourites.
 */
export async function recountTotalFavorites(): Promise<void> {
  const aggregate = await db().collectionGroup(COLLECTIONS.favorites).count().get();
  await db()
    .collection(COLLECTIONS.stats)
    .doc(STATS_DOC_ID)
    .set({ totalFavorites: aggregate.data().count, updatedAt: FieldValue.serverTimestamp() }, { merge: true });
}

/** Categories whose published count may have changed between two versions of a wallpaper. */
export function categoriesToRecount(
  before: { status?: unknown; categoryIds?: unknown } | undefined,
  after: { status?: unknown; categoryIds?: unknown } | undefined,
): string[] {
  const published = (doc: typeof before) =>
    doc && doc.status === 'published' && Array.isArray(doc.categoryIds)
      ? new Set(doc.categoryIds.filter((c): c is string => typeof c === 'string'))
      : new Set<string>();
  const a = published(before);
  const b = published(after);
  const changed = new Set<string>();
  for (const id of a) if (!b.has(id)) changed.add(id);
  for (const id of b) if (!a.has(id)) changed.add(id);
  return [...changed];
}
