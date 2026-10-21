import type { ConfigContext, ExpoConfig } from 'expo/config';
import * as fs from 'fs';
import * as path from 'path';

/**
 * DevDarshan Admin: a separate Android app (own application id, icon, entry point
 * and APK) for managing wallpapers, categories and home content.
 */

const PACKAGE = 'com.devdarshan.admin';
const VERSION = '1.0.0';
const IVORY = '#FAF6EF';
const GREEN = '#2E5B43';
const CHARCOAL = '#141210';

const versionCode = Math.max(1, Number.parseInt(process.env.DEVDARSHAN_VERSION_CODE ?? '1', 10) || 1);
const googleServicesFile = process.env.DEVDARSHAN_GOOGLE_SERVICES_FILE ?? './google-services.json';

function readFirebaseInfo(file: string, packageName: string): { projectId: string | null; webClientId: string | null } {
  try {
    const json = JSON.parse(fs.readFileSync(path.resolve(__dirname, file), 'utf8'));
    const clients: any[] = Array.isArray(json.client) ? json.client : [];
    const client = clients.find((c) => c?.client_info?.android_client_info?.package_name === packageName) ?? clients[0];
    const oauth: any[] = [
      ...(client?.oauth_client ?? []),
      ...(client?.services?.appinvite_service?.other_platform_oauth_client ?? []),
    ];
    const web = oauth.find((o) => o?.client_type === 3);
    return { projectId: json?.project_info?.project_id ?? null, webClientId: web?.client_id ?? null };
  } catch {
    return { projectId: null, webClientId: null };
  }
}

const firebase = readFirebaseInfo(googleServicesFile, PACKAGE);

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: 'DevDarshan Admin',
  slug: 'devdarshan-admin',
  version: VERSION,
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'automatic',
  backgroundColor: IVORY,
  platforms: ['android'],
  android: {
    package: PACKAGE,
    versionCode,
    googleServicesFile,
    adaptiveIcon: {
      foregroundImage: './assets/adaptive-icon.png',
      monochromeImage: './assets/adaptive-icon-monochrome.png',
      backgroundColor: GREEN,
    },
    // The admin app picks images with the Android photo picker, which needs no permission.
    permissions: [],
    blockedPermissions: [
      'android.permission.CAMERA',
      'android.permission.RECORD_AUDIO',
      'android.permission.READ_EXTERNAL_STORAGE',
      'android.permission.WRITE_EXTERNAL_STORAGE',
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.READ_MEDIA_VIDEO',
      'android.permission.READ_MEDIA_AUDIO',
      'android.permission.READ_MEDIA_VISUAL_USER_SELECTED',
      'android.permission.SET_WALLPAPER',
      'android.permission.SYSTEM_ALERT_WINDOW',
      'android.permission.VIBRATE',
      'com.google.android.gms.permission.AD_ID',
      'android.permission.ACCESS_ADSERVICES_AD_ID',
      'android.permission.ACCESS_ADSERVICES_ATTRIBUTION',
      // Pulled in by Credential Manager / Play services / Firebase libraries but not used by
      // DevDarshan (no biometrics, push messaging or install-referrer tracking).
      'android.permission.USE_BIOMETRIC',
      'android.permission.USE_FINGERPRINT',
      'com.google.android.c2dm.permission.RECEIVE',
      'com.google.android.finsky.permission.BIND_GET_INSTALL_REFERRER_SERVICE',
    ],
  },
  plugins: [
    '@react-native-firebase/app',
    '@react-native-firebase/auth',
    ['@devdarshan/native', { legacyStorage: false }],
    ['expo-image-picker', { photosPermission: false, cameraPermission: false, microphonePermission: false }],
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 168,
        resizeMode: 'contain',
        backgroundColor: GREEN,
        dark: { image: './assets/splash-icon-dark.png', backgroundColor: CHARCOAL },
      },
    ],
  ],
  extra: {
    variant: 'admin',
    versionCode,
    firebaseProjectId: firebase.projectId,
    googleWebClientId: firebase.webClientId,
    buildChannel: process.env.DEVDARSHAN_BUILD_CHANNEL ?? 'local',
    gitSha: (process.env.GITHUB_SHA ?? '').slice(0, 7) || null,
  },
});
