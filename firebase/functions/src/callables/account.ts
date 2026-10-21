import { logger } from 'firebase-functions/v2';
import { onCall } from 'firebase-functions/v2/https';
import { CALLABLE_REGION, ENFORCE_APP_CHECK } from '../config';
import { adminAuth, db } from '../firebase';
import { requireAuth } from '../lib/callable';
import { COLLECTIONS } from '../shared/constants';

/**
 * In-app account deletion (required by Google Play for apps with sign-in):
 * removes the user's favourites and their Firebase Auth account. Admin accounts
 * must be removed by another admin first, so the project can't lose its last admin.
 */
export const deleteMyAccount = onCall({ region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK }, async (request) => {
  const { uid } = requireAuth(request);
  const role = await db().collection(COLLECTIONS.adminRoles).doc(uid).get();
  if (role.exists) {
    return { ok: false, reason: 'admin', message: 'Admin accounts must be removed by another admin first.' };
  }
  const userDoc = db().collection(COLLECTIONS.users).doc(uid);
  for (;;) {
    const page = await userDoc.collection(COLLECTIONS.favorites).limit(400).get();
    if (page.empty) break;
    const batch = db().batch();
    page.docs.forEach((doc) => batch.delete(doc.ref));
    await batch.commit();
  }
  await userDoc.delete();
  await adminAuth().deleteUser(uid);
  logger.info('Account deleted on request', { uid });
  return { ok: true };
});
