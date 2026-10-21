import { getApp } from '@react-native-firebase/app';
import { ReactNativeFirebaseAppCheckProvider, initializeAppCheck } from '@react-native-firebase/app-check';
import { getAuth } from '@react-native-firebase/auth';
import { getFirestore } from '@react-native-firebase/firestore';
import { getFunctions } from '@react-native-firebase/functions';
import { FUNCTIONS_REGION, PLACEHOLDER_PROJECT_ID } from '@devdarshan/shared';

export const app = getApp();

/** False for builds made before Firebase was connected (they carry a placeholder config). */
export const isBackendConfigured = Boolean(app.options.projectId) && app.options.projectId !== PLACEHOLDER_PROJECT_ID;

export const db = getFirestore(app);
export const auth = getAuth(app);
export const functions = getFunctions(app, FUNCTIONS_REGION);

let appCheckStarted = false;

/**
 * App Check with Play Integrity. Tokens are only issued to installs from Google
 * Play, so the backend does not enforce App Check until the app is published
 * there (see docs/SECURITY.md); starting it here is harmless for sideloaded builds.
 */
export function startAppCheck(): void {
  if (appCheckStarted || !isBackendConfigured) return;
  appCheckStarted = true;
  try {
    const provider = new ReactNativeFirebaseAppCheckProvider();
    provider.configure({ android: { provider: __DEV__ ? 'debug' : 'playIntegrity' } });
    void Promise.resolve(initializeAppCheck(app, { provider, isTokenAutoRefreshEnabled: true })).catch(() => undefined);
  } catch {
    // App Check is defence in depth; the app works without it.
  }
}
