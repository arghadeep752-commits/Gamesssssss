import { getApp } from '@react-native-firebase/app';
import { getAuth } from '@react-native-firebase/auth';
import { getFirestore } from '@react-native-firebase/firestore';
import { getFunctions, httpsCallable } from '@react-native-firebase/functions';
import { getStorage } from '@react-native-firebase/storage';
import { FUNCTIONS_REGION, PLACEHOLDER_PROJECT_ID } from '@devdarshan/shared';

export const app = getApp();
export const isBackendConfigured = Boolean(app.options.projectId) && app.options.projectId !== PLACEHOLDER_PROJECT_ID;

export const db = getFirestore(app);
export const auth = getAuth(app);
export const storage = getStorage(app);
export const functions = getFunctions(app, FUNCTIONS_REGION);

/** Typed wrapper for the admin Cloud Functions. */
export async function callFunction<TRequest, TResponse>(name: string, data: TRequest): Promise<TResponse> {
  const callable = httpsCallable<TRequest, TResponse>(functions, name);
  const result = await callable(data);
  return result.data;
}
