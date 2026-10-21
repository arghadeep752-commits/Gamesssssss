import { NativeModule, requireOptionalNativeModule } from 'expo';

export type WallpaperTarget = 'home' | 'lock' | 'both';
export type DestinationResult = 'set' | 'failed' | 'skipped';
export type ShareTarget = 'whatsapp' | 'chooser';

export interface Capabilities {
  wallpaperSupported: boolean;
  setWallpaperAllowed: boolean;
  lockScreenSupported: boolean;
  /** null when the phone doesn't say. */
  lockFollowsHome: boolean | null;
  sdkInt: number;
  manufacturer: string;
  brand: string;
  model: string;
  whatsappPackage: string | null;
  needsStoragePermission: boolean;
}

export interface CachedImage {
  path: string;
  uri: string;
  mimeType: string;
  bytes: number;
  width: number;
  height: number;
  fromCache: boolean;
}

export interface SetWallpaperResult {
  home: DestinationResult;
  lock: DestinationResult;
  homeError: string | null;
  lockError: string | null;
  /** True when only Home was set and the lock screen was mirroring it, so it changed too. */
  lockMirrorsHome: boolean;
  manufacturer: string;
}

export interface SaveResult {
  uri: string;
  alreadyExisted: boolean;
  location: string;
}

export interface ShareResult {
  opened: boolean;
  target: 'whatsapp' | 'whatsappBusiness' | 'chooser';
}

export interface GoogleSignInResult {
  idToken: string;
  email: string | null;
  displayName: string | null;
  photoUrl: string | null;
}

/** A generated, labelled image used by the device self-test in test builds. */
export interface SelfTestImage {
  path: string;
  width: number;
  height: number;
  mimeType: string;
  bytes: number;
}

export interface DownloadProgressEvent {
  key: string;
  bytesWritten: number;
  /** -1 when the server didn't send a length. */
  totalBytes: number;
}

type NativeEvents = {
  onDownloadProgress: (event: DownloadProgressEvent) => void;
};

declare class DevDarshanNativeModule extends NativeModule<NativeEvents> {
  getCapabilities(): Promise<Capabilities>;
  downloadOriginal(key: string, url: string): Promise<CachedImage>;
  getCachedOriginal(key: string): Promise<CachedImage | null>;
  cancelDownload(key: string): void;
  setWallpaper(path: string, target: WallpaperTarget): Promise<SetWallpaperResult>;
  saveToGallery(path: string, displayName: string, mimeType: string): Promise<SaveResult>;
  shareImage(
    path: string,
    mimeType: string,
    target: ShareTarget,
    text: string | null,
    chooserTitle: string | null,
  ): Promise<ShareResult>;
  googleSignIn(webClientId: string): Promise<GoogleSignInResult>;
  googleSignOut(): Promise<void>;
  createSelfTestImage(): Promise<SelfTestImage>;
  getCacheSize(): Promise<number>;
  clearCache(): Promise<number>;
}

const native = requireOptionalNativeModule<DevDarshanNativeModule>('DevDarshanNative');

/** False on platforms without the Kotlin module (iOS/web for now). */
export const isNativeAvailable = native != null;

export class NativeFeatureError extends Error {
  readonly code: string;
  constructor(code: string, message: string) {
    super(message);
    this.code = code;
    this.name = 'NativeFeatureError';
  }
}

function mod(): DevDarshanNativeModule {
  if (!native) throw new NativeFeatureError('E_UNAVAILABLE', 'This feature is only available in the Android app.');
  return native;
}

export const DevDarshanNative = {
  getCapabilities: () => mod().getCapabilities(),
  downloadOriginal: (key: string, url: string) => mod().downloadOriginal(key, url),
  getCachedOriginal: (key: string) => mod().getCachedOriginal(key),
  cancelDownload: (key: string) => {
    if (native) native.cancelDownload(key);
  },
  setWallpaper: (path: string, target: WallpaperTarget) => mod().setWallpaper(path, target),
  saveToGallery: (path: string, displayName: string, mimeType: string) =>
    mod().saveToGallery(path, displayName, mimeType),
  shareImage: (
    path: string,
    mimeType: string,
    target: ShareTarget,
    options: { text?: string | null; chooserTitle?: string | null } = {},
  ) => mod().shareImage(path, mimeType, target, options.text ?? null, options.chooserTitle ?? null),
  googleSignIn: (webClientId: string) => mod().googleSignIn(webClientId),
  googleSignOut: async () => {
    if (native) await native.googleSignOut();
  },
  createSelfTestImage: () => mod().createSelfTestImage(),
  getCacheSize: () => (native ? native.getCacheSize() : Promise.resolve(0)),
  clearCache: () => (native ? native.clearCache() : Promise.resolve(0)),
  addDownloadProgressListener(listener: (event: DownloadProgressEvent) => void): { remove: () => void } {
    if (!native) return { remove: () => undefined };
    return native.addListener('onDownloadProgress', listener);
  },
};

/** The stable error code of a rejection from the native module (e.g. "E_NETWORK"). */
export function nativeErrorCode(error: unknown): string | null {
  if (error && typeof error === 'object' && 'code' in error) {
    const code = (error as { code: unknown }).code;
    return typeof code === 'string' ? code : null;
  }
  return null;
}

export function nativeErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  if (error && typeof error === 'object' && 'message' in error) return String((error as { message: unknown }).message);
  return String(error);
}

/** Phones whose launcher or theme app commonly overrides the lock-screen wallpaper. */
export function lockScreenManagedByVendor(manufacturer: string | null | undefined): string | null {
  const m = (manufacturer ?? '').toLowerCase();
  if (['xiaomi', 'redmi', 'poco'].includes(m)) return 'If the lock screen does not change, turn off Wallpaper Carousel / Glance in Settings → Lock screen.';
  if (['oppo', 'realme', 'oneplus'].includes(m)) return 'If the lock screen does not change, turn off Lock screen magazine in Settings → Wallpapers & style.';
  if (m === 'vivo' || m === 'iqoo') return 'If the lock screen does not change, check the lock screen style in i Theme / Settings → Lock screen.';
  if (m === 'samsung') return 'If the lock screen does not change, turn off Dynamic Lock screen in Settings → Lock screen.';
  return null;
}
