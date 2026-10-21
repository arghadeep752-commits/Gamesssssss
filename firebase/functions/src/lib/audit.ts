import { logger } from 'firebase-functions/v2';
import { FieldValue } from 'firebase-admin/firestore';
import { db } from '../firebase';
import { COLLECTIONS } from '../shared/constants';
import type { AdminAction, AdminLogEntry } from '../shared/types';

const emailCache = new Map<string, string | null>();

async function emailFor(uid: string): Promise<string | null> {
  if (uid === 'system') return null;
  if (emailCache.has(uid)) return emailCache.get(uid) ?? null;
  try {
    const snap = await db().collection(COLLECTIONS.adminRoles).doc(uid).get();
    const email = snap.exists ? ((snap.get('email') as string | undefined) ?? null) : null;
    emailCache.set(uid, email);
    return email;
  } catch {
    return null;
  }
}

export interface AuditInput {
  action: AdminAction;
  targetType: AdminLogEntry['targetType'];
  targetId: string | null;
  targetLabel: string;
  actorUid: string;
  details?: string | null;
}

/** Appends to the admin activity log. Never throws: auditing must not break the operation. */
export async function writeAdminLog(input: AuditInput): Promise<void> {
  try {
    await db()
      .collection(COLLECTIONS.adminLog)
      .add({
        action: input.action,
        targetType: input.targetType,
        targetId: input.targetId,
        targetLabel: input.targetLabel.slice(0, 120),
        actorUid: input.actorUid,
        actorEmail: await emailFor(input.actorUid),
        details: input.details ? input.details.slice(0, 300) : null,
        createdAt: FieldValue.serverTimestamp(),
      });
  } catch (error) {
    logger.warn('Could not write admin log entry', { action: input.action, error: String(error) });
  }
}
