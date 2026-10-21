import type { ConfigContext, ExpoConfig } from 'expo/config';
import * as fs from 'fs';
import * as path from 'path';

/**
 * DevDarshan user app. Native projects are generated from this file
 * (`expo prebuild`); nothing under android/ is edited by hand.
 *
 * Build-time inputs (all optional locally, set by CI):
 *   DEVDARSHAN_VERSION_CODE           monotonically increasing Android versionCode
 *   DEVDARSHAN_GOOGLE_SERVICES_FILE   path to google-services.json (default ./google-services.json)
 *   DEVDARSHAN_BUILD_CHANNEL          e.g. "release", "test"
 */

const PACKAGE = 'com.devdarshan.wallpapers';
const VERSION = '1.0.0';
const IVORY = '#FAF6EF';
const CHARCOAL = '#141210';

const versionCode = Math.max(1, Number.parseInt(process.env.DEVDARSHAN_VERSION_CODE ?? '1', 10) || 1);
const googleServicesFile = process.env.DEVDARSHAN_GOOGLE_SERVICES_FILE ?? './google-services.json';

interface FirebaseInfo {
  projectId: string | null;
  webClientId: string | null;
}

/** Reads the project id and the OAuth "web" client id (needed for Google sign-in) from google-services.json. */
function readFirebaseInfo(file: string, packageName: string): FirebaseInfo {
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
  name: 'DevDarshan',
  slug: 'devdarshan',
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
      backgroundColor: IVORY,
    },
    // Everything else is declared by the libraries that need it (INTERNET, network state)
    // or by @devdarshan/native (WRITE_EXTERNAL_STORAGE capped at Android 9).
    permissions: ['android.permission.SET_WALLPAPER'],
    blockedPermissions: [
      'android.permission.CAMERA',
      'android.permission.RECORD_AUDIO',
      'android.permission.READ_EXTERNAL_STORAGE',
      'android.permission.READ_MEDIA_IMAGES',
      'android.permission.READ_MEDIA_VIDEO',
      'android.permission.READ_MEDIA_AUDIO',
      'android.permission.SYSTEM_ALERT_WINDOW',
      'android.permission.VIBRATE',
      'com.google.android.gms.permission.AD_ID',
      'android.permission.ACCESS_ADSERVICES_AD_ID',
      'android.permission.ACCESS_ADSERVICES_ATTRIBUTION',
    ],
  },
  plugins: [
    '@react-native-firebase/app',
    '@react-native-firebase/auth',
    ['@devdarshan/native', { legacyStorage: true }],
    [
      'expo-splash-screen',
      {
        image: './assets/splash-icon.png',
        imageWidth: 168,
        resizeMode: 'contain',
        backgroundColor: IVORY,
        dark: { image: './assets/splash-icon-dark.png', backgroundColor: CHARCOAL },
      },
    ],
  ],
  extra: {
    variant: 'user',
    versionCode,
    firebaseProjectId: firebase.projectId,
    googleWebClientId: firebase.webClientId,
    buildChannel: process.env.DEVDARSHAN_BUILD_CHANNEL ?? 'local',
    gitSha: (process.env.GITHUB_SHA ?? '').slice(0, 7) || null,
  },
});
