import { HttpsError, onCall } from 'firebase-functions/v2/https';
import { FieldValue } from 'firebase-admin/firestore';
import { CALLABLE_REGION, ENFORCE_APP_CHECK, hasBootstrapAdmin, isBootstrapAdminEmail } from '../config';
import { adminAuth, db } from '../firebase';
import { writeAdminLog } from '../lib/audit';
import { parseInput, requireAdmin, requireAuth } from '../lib/callable';
import { COLLECTIONS } from '../shared/constants';
import { setAdminRoleInput } from '../shared/validation';

async function setAdminClaim(uid: string, admin: boolean): Promise<void> {
  const user = await adminAuth().getUser(uid);
  const claims = { ...(user.customClaims ?? {}) } as Record<string, unknown>;
  if (admin) claims.admin = true;
  else delete claims.admin;
  await adminAuth().setCustomUserClaims(uid, claims);
}

/**
 * One-time setup: the Google account configured in functions/.env (normally as the
 * SHA-256 of its email) may become the first admin, only with a Google-verified
 * email, and only while no other admin exists. After that, admins are added with
 * setAdminRole.
 */
export const bootstrapAdmin = onCall(
  { region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK },
  async (request) => {
    const caller = requireAuth(request);
    if (!hasBootstrapAdmin()) {
      throw new HttpsError('failed-precondition', 'No bootstrap admin is configured on the server.');
    }
    const email = (caller.email ?? '').trim().toLowerCase();
    if (request.auth?.token.email_verified !== true || !isBootstrapAdminEmail(email)) {
      throw new HttpsError('permission-denied', 'This Google account is not the configured first admin.');
    }
    const roles = db().collection(COLLECTIONS.adminRoles);
    const existing = await roles.limit(2).get();
    const others = existing.docs.filter((d) => d.id !== caller.uid);
    if (others.length > 0) {
      throw new HttpsError('failed-precondition', 'An admin already exists. Ask them to add you from the Admins screen.');
    }
    await setAdminClaim(caller.uid, true);
    await roles.doc(caller.uid).set({
      email,
      displayName: typeof request.auth?.token.name === 'string' ? request.auth.token.name : null,
      grantedBy: 'bootstrap',
      createdAt: FieldValue.serverTimestamp(),
    });
    await writeAdminLog({
      action: 'admin.bootstrapped',
      targetType: 'admin',
      targetId: caller.uid,
      targetLabel: email,
      actorUid: caller.uid,
    });
    return { ok: true };
  },
);

/** Grants or revokes admin access by email. The person must have signed in once. */
export const setAdminRole = onCall({ region: CALLABLE_REGION, enforceAppCheck: ENFORCE_APP_CHECK }, async (request) => {
  const caller = await requireAdmin(request);
  const { email, grant } = parseInput(setAdminRoleInput, request.data);

  let user;
  try {
    user = await adminAuth().getUserByEmail(email);
  } catch {
    throw new HttpsError('not-found', 'No account with that email. Ask them to sign in to DevDarshan Admin once, then try again.');
  }

  const roles = db().collection(COLLECTIONS.adminRoles);
  if (grant) {
    await setAdminClaim(user.uid, true);
    await roles.doc(user.uid).set({
      email: (user.email ?? email).toLowerCase(),
      displayName: user.displayName ?? null,
      grantedBy: caller.uid,
      createdAt: FieldValue.serverTimestamp(),
    });
    await writeAdminLog({
      action: 'admin.granted',
      targetType: 'admin',
      targetId: user.uid,
      targetLabel: email,
      actorUid: caller.uid,
    });
    return { ok: true, uid: user.uid };
  }

  const count = (await roles.count().get()).data().count;
  if (count <= 1) throw new HttpsError('failed-precondition', 'You cannot remove the last admin.');
  await roles.doc(user.uid).delete();
  await setAdminClaim(user.uid, false);
  // Ends their current sessions; the role document check in the rules already blocks them.
  await adminAuth().revokeRefreshTokens(user.uid);
  await writeAdminLog({
    action: 'admin.revoked',
    targetType: 'admin',
    targetId: user.uid,
    targetLabel: email,
    actorUid: caller.uid,
  });
  return { ok: true, uid: user.uid };
});
