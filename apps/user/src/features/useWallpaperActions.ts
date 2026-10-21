import { httpsCallable } from '@react-native-firebase/functions';
import { useCallback, useEffect, useRef, useState } from 'react';
import { PermissionsAndroid, Platform } from 'react-native';
import {
  DevDarshanNative,
  lockScreenManagedByVendor,
  type CachedImage,
  type Capabilities,
  type SetWallpaperResult,
  type ShareTarget,
  type WallpaperTarget,
} from '@devdarshan/native';
import { CALLABLES, wallpaperFileName, type Wallpaper } from '@devdarshan/shared';
import { useToast } from '@devdarshan/ui';
import { useAppConfig } from '../data/appConfig';
import { AppError, describeError } from '../errors';
import { functions } from '../firebase';

export type ActionKind = 'set' | 'download' | 'share';

export interface ActionProgress {
  kind: ActionKind;
  phase: 'downloading' | 'applying' | 'saving' | 'opening';
  /** 0..1, or null when the size is unknown. */
  fraction: number | null;
  key: string;
}

let capabilitiesCache: Promise<Capabilities | null> | null = null;
function getCapabilities(): Promise<Capabilities | null> {
  if (!capabilitiesCache) capabilitiesCache = DevDarshanNative.getCapabilities().catch(() => null);
  return capabilitiesCache;
}

const recordedDownloads = new Set<string>();
function recordDownload(wallpaperId: string): void {
  if (recordedDownloads.has(wallpaperId)) return;
  recordedDownloads.add(wallpaperId);
  httpsCallable(functions, CALLABLES.recordDownload)({ wallpaperId }).catch(() => recordedDownloads.delete(wallpaperId));
}

const cacheKey = (w: Wallpaper) => `${w.id}_v${w.imageVersion}`;

const EXTENSIONS: Record<string, string> = { 'image/png': 'png', 'image/webp': 'webp' };

function summarize(target: WallpaperTarget, result: SetWallpaperResult): { tone: 'success' | 'warning'; message: string; detail?: string } {
  const vendorHint = lockScreenManagedByVendor(result.manufacturer) ?? undefined;
  if (target === 'both') {
    if (result.home === 'set' && result.lock === 'set') {
      return { tone: 'success', message: 'Set on Home and Lock screen', detail: vendorHint };
    }
    if (result.home === 'set') {
      return {
        tone: 'warning',
        message: 'Set on Home screen only',
        detail: `Your phone did not accept the Lock screen change${result.lockError ? ` (${result.lockError})` : ''}.${vendorHint ? ` ${vendorHint}` : ''}`,
      };
    }
    return {
      tone: 'warning',
      message: 'Set on Lock screen only',
      detail: `The Home screen could not be changed${result.homeError ? ` (${result.homeError})` : ''}.`,
    };
  }
  if (target === 'home') {
    return {
      tone: 'success',
      message: 'Home screen wallpaper set',
      detail: result.lockMirrorsHome ? 'Your lock screen was using the same wallpaper, so it changed too.' : undefined,
    };
  }
  return { tone: 'success', message: 'Lock screen wallpaper set', detail: vendorHint };
}

/**
 * Set as wallpaper, download and share. All three use the full-resolution original,
 * downloaded once into the app cache with real progress (and reused afterwards).
 * Only one action runs at a time; a second tap is ignored while busy.
 */
export function useWallpaperActions() {
  const toast = useToast();
  const { config } = useAppConfig();
  const [progress, setProgress] = useState<ActionProgress | null>(null);
  const busy = useRef(false);
  const mounted = useRef(true);

  useEffect(
    () => () => {
      mounted.current = false;
    },
    [],
  );

  const update = useCallback((next: ActionProgress | null) => {
    if (mounted.current) setProgress(next);
  }, []);

  const ensureOriginal = useCallback(
    async (wallpaper: Wallpaper, kind: ActionKind): Promise<CachedImage> => {
      if (!wallpaper.originalUrl) throw new AppError('E_UNAVAILABLE', 'This wallpaper is not available right now.');
      const key = cacheKey(wallpaper);
      const cached = await DevDarshanNative.getCachedOriginal(key);
      if (cached) return cached;
      update({ kind, phase: 'downloading', fraction: 0, key });
      const subscription = DevDarshanNative.addDownloadProgressListener((event) => {
        if (event.key !== key) return;
        update({ kind, phase: 'downloading', fraction: event.totalBytes > 0 ? event.bytesWritten / event.totalBytes : null, key });
      });
      try {
        return await DevDarshanNative.downloadOriginal(key, wallpaper.originalUrl);
      } finally {
        subscription.remove();
      }
    },
    [update],
  );

  const run = useCallback(
    async (job: () => Promise<void>) => {
      if (busy.current) return;
      busy.current = true;
      try {
        await job();
      } catch (error) {
        const friendly = describeError(error);
        if (!friendly.silent) toast.show({ tone: 'error', message: friendly.title, detail: friendly.message || undefined });
      } finally {
        busy.current = false;
        update(null);
      }
    },
    [toast, update],
  );

  const setWallpaper = useCallback(
    (wallpaper: Wallpaper, target: WallpaperTarget) =>
      run(async () => {
        const image = await ensureOriginal(wallpaper, 'set');
        update({ kind: 'set', phase: 'applying', fraction: null, key: cacheKey(wallpaper) });
        const result = await DevDarshanNative.setWallpaper(image.path, target);
        const summary = summarize(target, result);
        toast.show({ tone: summary.tone, message: summary.message, detail: summary.detail });
      }),
    [ensureOriginal, run, toast, update],
  );

  const download = useCallback(
    (wallpaper: Wallpaper) =>
      run(async () => {
        const capabilities = await getCapabilities();
        if (Platform.OS === 'android' && capabilities?.needsStoragePermission) {
          const granted = await PermissionsAndroid.request(PermissionsAndroid.PERMISSIONS.WRITE_EXTERNAL_STORAGE);
          if (granted !== PermissionsAndroid.RESULTS.GRANTED) {
            throw new AppError('E_PERMISSION_REQUIRED', 'Storage permission was not granted.');
          }
          capabilitiesCache = null;
        }
        const image = await ensureOriginal(wallpaper, 'download');
        update({ kind: 'download', phase: 'saving', fraction: null, key: cacheKey(wallpaper) });
        const ext = EXTENSIONS[image.mimeType] ?? 'jpg';
        const saved = await DevDarshanNative.saveToGallery(image.path, wallpaperFileName(wallpaper.title, wallpaper.id, ext), image.mimeType);
        toast.show({
          tone: 'success',
          message: saved.alreadyExisted ? 'Already in your gallery' : 'Saved to your gallery',
          detail: `Gallery › ${saved.location}`,
        });
        recordDownload(wallpaper.id);
      }),
    [ensureOriginal, run, toast, update],
  );

  const share = useCallback(
    (wallpaper: Wallpaper, target: ShareTarget) =>
      run(async () => {
        const image = await ensureOriginal(wallpaper, 'share');
        update({ kind: 'share', phase: 'opening', fraction: null, key: cacheKey(wallpaper) });
        const text = config.shareMessage?.trim() || `${wallpaper.title} · shared from DevDarshan`;
        const result = await DevDarshanNative.shareImage(image.path, image.mimeType, target, {
          text,
          chooserTitle: 'Share wallpaper',
        });
        // Android never tells an app whether the share was completed, so nothing claims success here.
        if (target === 'whatsapp' && result.target === 'chooser') {
          toast.show({ tone: 'default', message: 'WhatsApp is not installed', detail: 'Pick another app to share with.' });
        }
      }),
    [config.shareMessage, ensureOriginal, run, toast, update],
  );

  const cancel = useCallback(() => {
    if (progress?.phase === 'downloading') DevDarshanNative.cancelDownload(progress.key);
  }, [progress]);

  return { progress, busy: progress !== null, setWallpaper, download, share, cancel };
}
