import { collection, getDocs, orderBy, query } from '@react-native-firebase/firestore';
import { CALLABLES, COLLECTIONS, toAdminRole, type AdminRole } from '@devdarshan/shared';
import { callFunction, db } from '../firebase';

export async function fetchAdmins(): Promise<AdminRole[]> {
  const snap = await getDocs(query(collection(db, COLLECTIONS.adminRoles), orderBy('createdAt', 'asc')));
  return snap.docs.map((d) => toAdminRole(d.id, d.data()));
}

export function setAdminRole(email: string, grant: boolean) {
  return callFunction<{ email: string; grant: boolean }, { ok: boolean; uid?: string }>(CALLABLES.setAdminRole, {
    email,
    grant,
  });
}
