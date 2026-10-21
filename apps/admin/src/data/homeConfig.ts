import { doc, getDoc, serverTimestamp, setDoc } from '@react-native-firebase/firestore';
import { APP_CONFIG_DOC_ID, COLLECTIONS, toAppConfig, type AppConfig, type HomeSection } from '@devdarshan/shared';
import { db } from '../firebase';

export async function fetchAppConfig(): Promise<AppConfig> {
  const snap = await getDoc(doc(db, COLLECTIONS.appConfig, APP_CONFIG_DOC_ID));
  return toAppConfig(snap.exists() ? snap.data() : null);
}

export interface AppConfigPatch {
  featuredWallpaperIds?: string[];
  featuredCategoryIds?: string[];
  homeSectionOrder?: HomeSection[];
  festival?: AppConfig['festival'];
  maintenanceMode?: boolean;
  maintenanceMessage?: string;
  minimumSupportedVersionCode?: number;
  updateUrl?: string;
  supportEmail?: string;
  shareMessage?: string;
}

/** Changes appear in the user app immediately (it listens to this document). */
export async function saveAppConfig(patch: AppConfigPatch, uid: string): Promise<void> {
  await setDoc(
    doc(db, COLLECTIONS.appConfig, APP_CONFIG_DOC_ID),
    { ...patch, updatedAt: serverTimestamp(), updatedBy: uid },
    { merge: true },
  );
}
