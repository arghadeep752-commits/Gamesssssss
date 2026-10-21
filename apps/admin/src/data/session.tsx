import {
  GoogleAuthProvider,
  getIdTokenResult,
  onAuthStateChanged,
  signInWithCredential,
  signOut as firebaseSignOut,
  type FirebaseAuthTypes,
} from '@react-native-firebase/auth';
import { doc, getDoc } from '@react-native-firebase/firestore';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { DevDarshanNative } from '@devdarshan/native';
import { CALLABLES, COLLECTIONS } from '@devdarshan/shared';
import { buildInfo } from '../config';
import { AppError } from '../errors';
import { auth, callFunction, db, isBackendConfigured } from '../firebase';

export type SessionStatus = 'loading' | 'signed-out' | 'checking' | 'not-admin' | 'admin';

interface Session {
  status: SessionStatus;
  user: FirebaseAuthTypes.User | null;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  /** One-time bootstrap for the configured first admin. */
  claimAdmin: () => Promise<void>;
  recheck: () => Promise<void>;
}

const SessionContext = createContext<Session | null>(null);

/**
 * Admin access is decided by the backend: a custom claim set by Cloud Functions
 * AND a role document only Cloud Functions can write (the same test the security
 * rules apply). The app only reflects that state; it can't grant anything itself.
 */
export function SessionProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null);
  const [status, setStatus] = useState<SessionStatus>(isBackendConfigured ? 'loading' : 'signed-out');
  const checkId = useRef(0);

  const evaluate = useCallback(async (next: FirebaseAuthTypes.User | null, forceRefresh: boolean) => {
    const id = ++checkId.current;
    if (!next) {
      setStatus('signed-out');
      return;
    }
    setStatus('checking');
    try {
      const token = await getIdTokenResult(next, forceRefresh);
      let admin = token.claims.admin === true;
      if (admin) {
        const role = await getDoc(doc(db, COLLECTIONS.adminRoles, next.uid));
        admin = role.exists();
      }
      if (id === checkId.current) setStatus(admin ? 'admin' : 'not-admin');
    } catch {
      if (id === checkId.current) setStatus('not-admin');
    }
  }, []);

  useEffect(() => {
    if (!isBackendConfigured) return undefined;
    return onAuthStateChanged(auth, (next) => {
      setUser(next);
      void evaluate(next, true);
    });
  }, [evaluate]);

  const signIn = useCallback(async () => {
    if (!isBackendConfigured || !buildInfo.googleWebClientId) {
      throw new AppError('SIGNIN_NOT_CONFIGURED', 'Google sign-in is not configured for this build.');
    }
    const { idToken } = await DevDarshanNative.googleSignIn(buildInfo.googleWebClientId);
    await signInWithCredential(auth, GoogleAuthProvider.credential(idToken));
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
    await DevDarshanNative.googleSignOut().catch(() => undefined);
  }, []);

  const recheck = useCallback(async () => {
    await evaluate(auth.currentUser, true);
  }, [evaluate]);

  const claimAdmin = useCallback(async () => {
    await callFunction<Record<string, never>, { ok: boolean }>(CALLABLES.bootstrapAdmin, {});
    await evaluate(auth.currentUser, true);
  }, [evaluate]);

  const value = useMemo<Session>(
    () => ({ status, user, signIn, signOut, claimAdmin, recheck }),
    [status, user, signIn, signOut, claimAdmin, recheck],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const value = useContext(SessionContext);
  if (!value) throw new Error('useSession must be used inside SessionProvider');
  return value;
}
