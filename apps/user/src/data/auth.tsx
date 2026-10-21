import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithCredential,
  signOut as firebaseSignOut,
} from '@react-native-firebase/auth';
import { httpsCallable } from '@react-native-firebase/functions';
import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { DevDarshanNative } from '@devdarshan/native';
import { CALLABLES } from '@devdarshan/shared';
import { buildInfo } from '../config';
import { AppError } from '../errors';
import { auth, functions, isBackendConfigured } from '../firebase';

/** The signed-in Firebase user (derived from the SDK so it follows its type names across versions). */
export type AppUser = NonNullable<typeof auth.currentUser>;

interface AuthState {
  user: AppUser | null;
  initializing: boolean;
  signingIn: boolean;
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
  deleteAccount: () => Promise<{ ok: boolean; message?: string }>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Google sign-in: Credential Manager (native) returns a Google ID token, which is
 * exchanged for a Firebase session. Firebase persists the session across restarts.
 * Browsing never requires an account; only likes do.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AppUser | null>(null);
  const [initializing, setInitializing] = useState(isBackendConfigured);
  const [signingIn, setSigningIn] = useState(false);

  useEffect(() => {
    if (!isBackendConfigured) return undefined;
    return onAuthStateChanged(auth, (next) => {
      setUser(next);
      setInitializing(false);
    });
  }, []);

  const signIn = useCallback(async () => {
    if (!isBackendConfigured || !buildInfo.googleWebClientId) {
      throw new AppError('SIGNIN_NOT_CONFIGURED', 'Google sign-in is not configured for this build.');
    }
    setSigningIn(true);
    try {
      const { idToken } = await DevDarshanNative.googleSignIn(buildInfo.googleWebClientId);
      await signInWithCredential(auth, GoogleAuthProvider.credential(idToken));
    } finally {
      setSigningIn(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    await firebaseSignOut(auth);
    await DevDarshanNative.googleSignOut().catch(() => undefined);
  }, []);

  const deleteAccount = useCallback(async () => {
    const call = httpsCallable<Record<string, never>, { ok: boolean; message?: string }>(functions, CALLABLES.deleteMyAccount);
    const result = await call({});
    if (result.data.ok) {
      await firebaseSignOut(auth).catch(() => undefined);
      await DevDarshanNative.googleSignOut().catch(() => undefined);
    }
    return result.data;
  }, []);

  const value = useMemo<AuthState>(
    () => ({ user, initializing, signingIn, signIn, signOut, deleteAccount }),
    [user, initializing, signingIn, signIn, signOut, deleteAccount],
  );
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const value = useContext(AuthContext);
  if (!value) throw new Error('useAuth must be used inside AuthProvider');
  return value;
}
