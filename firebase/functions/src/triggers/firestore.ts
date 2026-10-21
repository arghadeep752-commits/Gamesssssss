import { logger } from 'firebase-functions/v2';
import { onDocumentWritten } from 'firebase-functions/v2/firestore';
import { FieldValue, type DocumentData } from 'firebase-admin/firestore';
import { FIRESTORE_REGION } from '../config';
import { db } from '../firebase';
import { writeAdminLog } from '../lib/audit';
import { categoriesToRecount, recountCategory, recountFavorites, recountTotalFavorites } from '../lib/counts';
import { APP_CONFIG_DOC_ID, COLLECTIONS } from '../shared/constants';
import { buildSearchKeywords, normalizeText } from '../shared/search';

function sameList(a: unknown, b: readonly string[]): boolean {
  return Array.isArray(a) && a.length === b.length && a.every((v, i) => v === b[i]);
}

function millis(value: unknown): number | null {
  return value && typeof value === 'object' && 'toMillis' in value
    ? (value as { toMillis: () => number }).toMillis()
    : null;
}

function stringList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];
}

async function categoryNames(categoryIds: string[]): Promise<string[]> {
  if (categoryIds.length === 0) return [];
  const refs = categoryIds.slice(0, 5).map((id) => db().collection(COLLECTIONS.categories).doc(id));
  const snaps = await db().getAll(...refs);
  return snaps.flatMap((s) => (s.exists ? [String(s.get('name') ?? ''), String(s.get('nameHi') ?? '')] : []));
}

/**
 * Keeps server-owned wallpaper fields correct after any write:
 *  - searchKeywords / titleLower (from title, tags and category names),
 *  - publishedAt on first publish,
 *  - exact per-category published counts,
 *  - an audit entry for admin edits (detected by a changed updatedAt).
 * Writes made here do not touch updatedAt, so they never trigger a second audit or a loop.
 */
export const onWallpaperWritten = onDocumentWritten(
  { document: 'wallpapers/{wallpaperId}', region: FIRESTORE_REGION },
  async (event) => {
    const wallpaperId = event.params.wallpaperId;
    const beforeSnap = event.data?.before;
    const afterSnap = event.data?.after;
    const before: DocumentData | undefined = beforeSnap?.exists ? beforeSnap.data() : undefined;
    const after: DocumentData | undefined = afterSnap?.exists ? afterSnap.data() : undefined;

    // 1. Derived fields.
    if (after && afterSnap && after.status !== 'deleting') {
      const searchableChanged =
        !before ||
        before.title !== after.title ||
        JSON.stringify(before.tags) !== JSON.stringify(after.tags) ||
        JSON.stringify(before.categoryIds) !== JSON.stringify(after.categoryIds) ||
        !Array.isArray(after.searchKeywords);
      const patch: Record<string, unknown> = {};
      if (searchableChanged) {
        const keywords = buildSearchKeywords({
          title: String(after.title ?? ''),
          tags: stringList(after.tags),
          extra: await categoryNames(stringList(after.categoryIds)),
        });
        if (!sameList(after.searchKeywords, keywords)) patch.searchKeywords = keywords;
        const titleLower = normalizeText(String(after.title ?? ''));
        if (after.titleLower !== titleLower) patch.titleLower = titleLower;
      }
      if (after.status === 'published' && !after.publishedAt) patch.publishedAt = FieldValue.serverTimestamp();
      if (Object.keys(patch).length > 0) await afterSnap.ref.update(patch);
    }

    // 2. Category counts.
    const recount = categoriesToRecount(before, after);
    await Promise.all(recount.map((id) => recountCategory(id)));

    // 3. Audit trail for admin edits (server-side processing and deletes log themselves).
    if (after && millis(after.updatedAt) !== millis(before?.updatedAt)) {
      const actorUid = typeof after.updatedBy === 'string' ? after.updatedBy : 'unknown';
      let action:
        | 'wallpaper.created'
        | 'wallpaper.published'
        | 'wallpaper.unpublished'
        | 'wallpaper.imageReplaced'
        | 'wallpaper.updated' = 'wallpaper.updated';
      if (!before) action = 'wallpaper.created';
      else if (before.status !== 'published' && after.status === 'published') action = 'wallpaper.published';
      else if (before.status === 'published' && after.status === 'draft') action = 'wallpaper.unpublished';
      else if (before.processing !== 'uploading' && after.processing === 'uploading') action = 'wallpaper.imageReplaced';
      await writeAdminLog({
        action,
        targetType: 'wallpaper',
        targetId: wallpaperId,
        targetLabel: String(after.title ?? wallpaperId),
        actorUid,
        details: action === 'wallpaper.imageReplaced' ? 'New image uploading' : null,
      });
    }
  },
);

/** Keeps each wallpaper's `featured` flag in step with the curated list in appConfig/public. */
export const onAppConfigWritten = onDocumentWritten(
  { document: 'appConfig/{docId}', region: FIRESTORE_REGION },
  async (event) => {
    if (event.params.docId !== APP_CONFIG_DOC_ID) return;
    const before = event.data?.before?.exists ? event.data.before.data() : undefined;
    const after = event.data?.after?.exists ? event.data.after.data() : undefined;
    const oldIds = new Set(stringList(before?.featuredWallpaperIds));
    const newIds = new Set(stringList(after?.featuredWallpaperIds));
    const changes: Array<[string, boolean]> = [
      ...[...newIds].filter((id) => !oldIds.has(id)).map((id): [string, boolean] => [id, true]),
      ...[...oldIds].filter((id) => !newIds.has(id)).map((id): [string, boolean] => [id, false]),
    ];
    if (changes.length > 0) {
      const refs = changes.map(([id]) => db().collection(COLLECTIONS.wallpapers).doc(id));
      const snaps = await db().getAll(...refs);
      const batch = db().batch();
      snaps.forEach((snap, index) => {
        const change = changes[index];
        if (snap.exists && change) batch.update(snap.ref, { featured: change[1] });
      });
      await batch.commit();
    }

    if (after && millis(after.updatedAt) !== millis(before?.updatedAt)) {
      const changedKeys = Object.keys(after).filter(
        (key) => !['updatedAt', 'updatedBy'].includes(key) && JSON.stringify(after[key]) !== JSON.stringify(before?.[key]),
      );
      await writeAdminLog({
        action: 'config.updated',
        targetType: 'config',
        targetId: APP_CONFIG_DOC_ID,
        targetLabel: 'Home & app settings',
        actorUid: typeof after.updatedBy === 'string' ? after.updatedBy : 'unknown',
        details: changedKeys.length ? `Changed: ${changedKeys.join(', ')}` : null,
      });
    }
  },
);

/** Per-wallpaper favourite counts are recomputed from the favourite documents (exact, idempotent). */
export const onFavoriteWritten = onDocumentWritten(
  { document: 'users/{uid}/favorites/{wallpaperId}', region: FIRESTORE_REGION },
  async (event) => {
    const existedBefore = event.data?.before?.exists ?? false;
    const existsAfter = event.data?.after?.exists ?? false;
    if (existedBefore === existsAfter) return;
    try {
      await Promise.all([recountFavorites(event.params.wallpaperId), recountTotalFavorites()]);
    } catch (error) {
      logger.error('Favourite recount failed', { wallpaperId: event.params.wallpaperId, error: String(error) });
      throw error;
    }
  },
);

/** Re-indexes wallpapers of a renamed category so searches by its new name work. */
async function refreshKeywordsForCategory(categoryId: string): Promise<number> {
  const snaps = await db()
    .collection(COLLECTIONS.wallpapers)
    .where('categoryIds', 'array-contains', categoryId)
    .limit(2000)
    .get();
  const nameCache = new Map<string, string[]>();
  const namesFor = async (ids: string[]) => {
    const missing = ids.filter((id) => !nameCache.has(id));
    if (missing.length > 0) {
      const fetched = await db().getAll(...missing.map((id) => db().collection(COLLECTIONS.categories).doc(id)));
      fetched.forEach((s, i) => {
        const id = missing[i];
        if (id) nameCache.set(id, s.exists ? [String(s.get('name') ?? ''), String(s.get('nameHi') ?? '')] : []);
      });
    }
    return ids.flatMap((id) => nameCache.get(id) ?? []);
  };
  let updated = 0;
  let batch = db().batch();
  let pending = 0;
  for (const doc of snaps.docs) {
    const data = doc.data();
    const keywords = buildSearchKeywords({
      title: String(data.title ?? ''),
      tags: stringList(data.tags),
      extra: await namesFor(stringList(data.categoryIds).slice(0, 5)),
    });
    if (sameList(data.searchKeywords, keywords)) continue;
    batch.update(doc.ref, { searchKeywords: keywords });
    pending += 1;
    updated += 1;
    if (pending === 400) {
      await batch.commit();
      batch = db().batch();
      pending = 0;
    }
  }
  if (pending > 0) await batch.commit();
  return updated;
}

/** Logs category edits made from the admin app and re-indexes wallpapers after a rename. */
export const onCategoryWritten = onDocumentWritten(
  { document: 'categories/{categoryId}', region: FIRESTORE_REGION, timeoutSeconds: 300 },
  async (event) => {
    const before = event.data?.before?.exists ? event.data.before.data() : undefined;
    const after = event.data?.after?.exists ? event.data.after.data() : undefined;
    if (before && after && (before.name !== after.name || before.nameHi !== after.nameHi)) {
      const updated = await refreshKeywordsForCategory(event.params.categoryId);
      logger.info('Re-indexed wallpapers after category rename', { categoryId: event.params.categoryId, updated });
    }
    if (!after || millis(after.updatedAt) === millis(before?.updatedAt)) return;
    await writeAdminLog({
      action: before ? 'category.updated' : 'category.created',
      targetType: 'category',
      targetId: event.params.categoryId,
      targetLabel: String(after.name ?? event.params.categoryId),
      actorUid: typeof after.updatedBy === 'string' ? after.updatedBy : 'unknown',
      details: before && before.isActive !== after.isActive ? (after.isActive ? 'Shown' : 'Hidden') : null,
    });
  },
);
