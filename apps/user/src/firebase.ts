import { getApp } from '@react-native-firebase/app';
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
