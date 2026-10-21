import { HttpsError, type CallableRequest } from 'firebase-functions/v2/https';
import type { z } from 'zod';
import { db } from '../firebase';
import { COLLECTIONS } from '../shared/constants';
import { firstIssue } from '../shared/validation';

export interface Caller {
  uid: string;
  email: string | null;
}

export function requireAuth(request: CallableRequest<unknown>): Caller {
  if (!request.auth) throw new HttpsError('unauthenticated', 'Please sign in first.');
  const email = typeof request.auth.token.email === 'string' ? request.auth.token.email : null;
  return { uid: request.auth.uid, email };
}

/** Admin = custom claim AND role document, the same test the security rules use. */
export async function requireAdmin(request: CallableRequest<unknown>): Promise<Caller> {
  const caller = requireAuth(request);
  if (request.auth?.token.admin !== true) {
    throw new HttpsError('permission-denied', 'This action is only available to DevDarshan admins.');
  }
  const role = await db().collection(COLLECTIONS.adminRoles).doc(caller.uid).get();
  if (!role.exists) throw new HttpsError('permission-denied', 'Your admin access has been removed.');
  return caller;
}

export function parseInput<T>(schema: z.ZodType<T>, data: unknown): T {
  const result = schema.safeParse(data);
  if (!result.success) throw new HttpsError('invalid-argument', firstIssue(result.error));
  return result.data;
}
