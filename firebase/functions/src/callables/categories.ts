import { HttpsError, onCall } from 'firebase-functions/v2/https';
import { FieldValue } from 'firebase-admin/firestore';
import { CALLABLE_REGION, ENFORCE_APP_CHECK } from '../config';
import { db } from '../firebase';
import { writeAdminLog } from '../lib/audit';
import { parseInput, requireAdmin } from '../lib/callable';
import { recountCategory } from '../lib/counts';
import { deletePrefix } from '../lib/storageFiles';
import { APP_CONFIG_DOC_ID, COLLECTIONS } from '../shared/constants';
import { STARTER_CATEGORIES } from '../shared/starterCategories';
import { deleteCategoryInput } from '../shared/validation';

/**
 * Deletion policy: a category that still has wallpapers (published or not) is never
 * deleted silently. The admin either picks a category to move them to, or hides the
 * category instead. A wallpaper left with no category is moved to the target too.
 */
export const deleteCategory = onCall(
  { region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK, timeoutSeconds: 300 },
  async (request) => {
    const caller = await requireAdmin(request);
    const { categoryId, moveToCategoryId } = parseInput(deleteCategoryInput, request.data);
    const categories = db().collection(COLLECTIONS.categories);
    const category = await categories.doc(categoryId).get();
    if (!category.exists) return { ok: true, alreadyDeleted: true, moved: 0 };

    const wallpapers = db().collection(COLLECTIONS.wallpapers);
    const assigned = (await wallpapers.where('categoryIds', 'array-contains', categoryId).count().get()).data().count;

    if (assigned > 0) {
      if (!moveToCategoryId) {
        throw new HttpsError(
          'failed-precondition',
          `${assigned} wallpaper(s) use this category. Choose a category to move them to, or hide it instead.`,
        );
      }
      if (moveToCategoryId === categoryId) throw new HttpsError('invalid-argument', 'Choose a different category.');
      const target = await categories.doc(moveToCategoryId).get();
      if (!target.exists) throw new HttpsError('not-found', 'The target category does not exist.');
    }

    let moved = 0;
    for (;;) {
      const page = await wallpapers.where('categoryIds', 'array-contains', categoryId).limit(300).get();
      if (page.empty) break;
      const batch = db().batch();
      for (const doc of page.docs) {
        const current: string[] = Array.isArray(doc.get('categoryIds')) ? doc.get('categoryIds') : [];
        const next = [...new Set(current.filter((id) => id !== categoryId).concat(moveToCategoryId ? [moveToCategoryId] : []))];
        batch.update(doc.ref, { categoryIds: next.slice(0, 5) });
      }
      await batch.commit();
      moved += page.size;
    }

    await deletePrefix(`categories/${categoryId}/`);
    await deletePrefix(`uploads/categories/${categoryId}/`);
    await db()
      .collection(COLLECTIONS.appConfig)
      .doc(APP_CONFIG_DOC_ID)
      .set({ featuredCategoryIds: FieldValue.arrayRemove(categoryId) }, { merge: true });
    const config = await db().collection(COLLECTIONS.appConfig).doc(APP_CONFIG_DOC_ID).get();
    if (config.get('festival.categoryId') === categoryId) {
      await config.ref.update({ 'festival.categoryId': null, 'festival.enabled': false });
    }
    await categories.doc(categoryId).delete();
    if (moveToCategoryId) await recountCategory(moveToCategoryId);

    await writeAdminLog({
      action: 'category.deleted',
      targetType: 'category',
      targetId: categoryId,
      targetLabel: String(category.get('name') ?? categoryId),
      actorUid: caller.uid,
      details: moved ? `Moved ${moved} wallpaper(s) to ${moveToCategoryId}` : null,
    });
    return { ok: true, moved };
  },
);

/** Creates the starter categories from the product brief. Existing ones are never overwritten. */
export const seedStarterCategories = onCall({ region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK }, async (request) => {
  const caller = await requireAdmin(request);
  const categories = db().collection(COLLECTIONS.categories);
  const refs = STARTER_CATEGORIES.map((c) => categories.doc(c.id));
  const existing = await db().getAll(...refs);
  const batch = db().batch();
  let created = 0;
  STARTER_CATEGORIES.forEach((starter, index) => {
    if (existing[index]?.exists) return;
    batch.set(categories.doc(starter.id), {
      name: starter.name,
      nameHi: starter.nameHi,
      slug: starter.id,
      description: starter.description,
      sortOrder: starter.sortOrder,
      isActive: true,
      wallpaperCount: 0,
      createdAt: FieldValue.serverTimestamp(),
      updatedAt: FieldValue.serverTimestamp(),
      updatedBy: caller.uid,
    });
    created += 1;
  });
  if (created > 0) await batch.commit();
  await writeAdminLog({
    action: 'categories.seeded',
    targetType: 'category',
    targetId: null,
    targetLabel: 'Starter categories',
    actorUid: caller.uid,
    details: `Created ${created}, kept ${STARTER_CATEGORIES.length - created}`,
  });
  return { ok: true, created, existing: STARTER_CATEGORIES.length - created };
});
