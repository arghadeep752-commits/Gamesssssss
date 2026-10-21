import { DEFAULT_HOME_SECTION_ORDER, DEFAULT_UPDATE_URL, HOME_SECTIONS, type HomeSection } from './constants';
import type {
  AdminLogEntry,
  AdminRole,
  AppConfig,
  Category,
  GlobalStats,
  ProcessingState,
  RequestedStatus,
  Wallpaper,
  WallpaperStatus,
} from './types';

type RawData = Record<string, unknown> | null | undefined;

/**
 * Converts any Firestore timestamp representation (RNFB Timestamp, firebase-admin
 * Timestamp, {seconds, nanoseconds}, Date or millis) into epoch milliseconds.
 */
export function millisOf(value: unknown): number | null {
  if (value == null) return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (value instanceof Date) return value.getTime();
  if (typeof value === 'object') {
    const v = value as { toMillis?: () => number; seconds?: number; nanoseconds?: number; _seconds?: number };
    if (typeof v.toMillis === 'function') {
      try {
        return v.toMillis();
      } catch {
        return null;
      }
    }
    const seconds = typeof v.seconds === 'number' ? v.seconds : typeof v._seconds === 'number' ? v._seconds : null;
    if (seconds !== null) return seconds * 1000 + Math.floor((v.nanoseconds ?? 0) / 1e6);
  }
  return null;
}

function str(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function strOrNull(value: unknown): string | null {
  return typeof value === 'string' && value.length > 0 ? value : null;
}

function num(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

function bool(value: unknown, fallback = false): boolean {
  return typeof value === 'boolean' ? value : fallback;
}

function strList(value: unknown): string[] {
  return Array.isArray(value) ? value.filter((v): v is string => typeof v === 'string') : [];
}

function oneOf<T extends string>(value: unknown, allowed: readonly T[], fallback: T): T {
  return typeof value === 'string' && (allowed as readonly string[]).includes(value) ? (value as T) : fallback;
}

const STATUSES: readonly WallpaperStatus[] = ['draft', 'published', 'deleting'];
const REQUESTED: readonly RequestedStatus[] = ['draft', 'published'];
const PROCESSING: readonly ProcessingState[] = ['uploading', 'processing', 'ready', 'failed'];

export function toWallpaper(id: string, data: RawData): Wallpaper {
  const d = data ?? {};
  const width = num(d.width);
  const height = num(d.height);
  return {
    id,
    title: str(d.title),
    description: str(d.description),
    categoryIds: strList(d.categoryIds),
    tags: strList(d.tags),
    status: oneOf(d.status, STATUSES, 'draft'),
    requestedStatus: oneOf(d.requestedStatus, REQUESTED, 'draft'),
    processing: oneOf(d.processing, PROCESSING, 'uploading'),
    processingError: strOrNull(d.processingError),
    featured: bool(d.featured),
    originalUrl: strOrNull(d.originalUrl),
    previewUrl: strOrNull(d.previewUrl),
    thumbnailUrl: strOrNull(d.thumbnailUrl),
    originalStoragePath: strOrNull(d.originalStoragePath),
    previewStoragePath: strOrNull(d.previewStoragePath),
    thumbnailStoragePath: strOrNull(d.thumbnailStoragePath),
    width,
    height,
    aspectRatio: num(d.aspectRatio, width > 0 && height > 0 ? width / height : 9 / 19.5),
    fileSizeBytes: num(d.fileSizeBytes),
    mimeType: strOrNull(d.mimeType),
    placeholder: strOrNull(d.placeholder),
    dominantColor: strOrNull(d.dominantColor),
    imageVersion: num(d.imageVersion),
    favoriteCount: Math.max(0, num(d.favoriteCount)),
    downloadCount: Math.max(0, num(d.downloadCount)),
    searchKeywords: strList(d.searchKeywords),
    createdAt: millisOf(d.createdAt),
    updatedAt: millisOf(d.updatedAt),
    publishedAt: millisOf(d.publishedAt),
    processedAt: millisOf(d.processedAt),
    createdBy: strOrNull(d.createdBy),
    updatedBy: strOrNull(d.updatedBy),
  };
}

/** True when a wallpaper has everything the user app needs to show and use it. */
export function isDisplayable(w: Wallpaper): boolean {
  return w.status === 'published' && !!w.thumbnailUrl && !!w.previewUrl && !!w.originalUrl;
}

export function toCategory(id: string, data: RawData): Category {
  const d = data ?? {};
  return {
    id,
    name: str(d.name, id),
    nameHi: str(d.nameHi),
    slug: str(d.slug, id),
    description: str(d.description),
    sortOrder: num(d.sortOrder),
    isActive: bool(d.isActive, true),
    wallpaperCount: Math.max(0, num(d.wallpaperCount)),
    coverUrl: strOrNull(d.coverUrl),
    coverThumbUrl: strOrNull(d.coverThumbUrl),
    coverImagePath: strOrNull(d.coverImagePath),
    coverThumbnailPath: strOrNull(d.coverThumbnailPath),
    coverPlaceholder: strOrNull(d.coverPlaceholder),
    createdAt: millisOf(d.createdAt),
    updatedAt: millisOf(d.updatedAt),
  };
}

export const DEFAULT_APP_CONFIG: AppConfig = {
  featuredWallpaperIds: [],
  featuredCategoryIds: [],
  homeSectionOrder: [...DEFAULT_HOME_SECTION_ORDER],
  festival: { enabled: false, title: '', titleHi: '', categoryId: null },
  maintenanceMode: false,
  maintenanceMessage: '',
  minimumSupportedVersionCode: 0,
  updateUrl: DEFAULT_UPDATE_URL,
  supportEmail: '',
  shareMessage: '',
  updatedAt: null,
};

export function toAppConfig(data: RawData): AppConfig {
  if (!data) return { ...DEFAULT_APP_CONFIG, homeSectionOrder: [...DEFAULT_HOME_SECTION_ORDER] };
  const festivalRaw = (data.festival && typeof data.festival === 'object' ? data.festival : {}) as Record<string, unknown>;
  const order = strList(data.homeSectionOrder).filter((s): s is HomeSection =>
    (HOME_SECTIONS as readonly string[]).includes(s),
  );
  // Any section the admin hasn't ordered yet is appended so new sections never disappear.
  const fullOrder: HomeSection[] = [...new Set<HomeSection>([...order, ...DEFAULT_HOME_SECTION_ORDER])];
  return {
    featuredWallpaperIds: strList(data.featuredWallpaperIds),
    featuredCategoryIds: strList(data.featuredCategoryIds),
    homeSectionOrder: fullOrder,
    festival: {
      enabled: bool(festivalRaw.enabled),
      title: str(festivalRaw.title),
      titleHi: str(festivalRaw.titleHi),
      categoryId: strOrNull(festivalRaw.categoryId),
    },
    maintenanceMode: bool(data.maintenanceMode),
    maintenanceMessage: str(data.maintenanceMessage),
    minimumSupportedVersionCode: Math.max(0, Math.floor(num(data.minimumSupportedVersionCode))),
    updateUrl: str(data.updateUrl) || DEFAULT_UPDATE_URL,
    supportEmail: str(data.supportEmail),
    shareMessage: str(data.shareMessage),
    updatedAt: millisOf(data.updatedAt),
  };
}

export function toAdminRole(uid: string, data: RawData): AdminRole {
  const d = data ?? {};
  return {
    uid,
    email: str(d.email),
    displayName: strOrNull(d.displayName),
    grantedBy: str(d.grantedBy, 'unknown'),
    createdAt: millisOf(d.createdAt),
  };
}

export function toAdminLogEntry(id: string, data: RawData): AdminLogEntry {
  const d = data ?? {};
  return {
    id,
    action: str(d.action, 'wallpaper.updated') as AdminLogEntry['action'],
    targetType: oneOf(d.targetType, ['wallpaper', 'category', 'config', 'admin'] as const, 'wallpaper'),
    targetId: strOrNull(d.targetId),
    targetLabel: str(d.targetLabel),
    actorUid: str(d.actorUid, 'system'),
    actorEmail: strOrNull(d.actorEmail),
    details: strOrNull(d.details),
    createdAt: millisOf(d.createdAt),
  };
}

export function toGlobalStats(data: RawData): GlobalStats {
  const d = data ?? {};
  return {
    totalDownloads: Math.max(0, num(d.totalDownloads)),
    totalFavorites: Math.max(0, num(d.totalFavorites)),
    uploadsSucceeded: Math.max(0, num(d.uploadsSucceeded)),
    uploadsFailed: Math.max(0, num(d.uploadsFailed)),
  };
}

/** Category label for display: Hindi and English together when both exist. */
export function categoryLabel(c: Pick<Category, 'name' | 'nameHi'>, prefer: 'en' | 'hi' = 'en'): string {
  if (!c.nameHi) return c.name;
  if (!c.name || c.name === c.nameHi) return c.nameHi;
  return prefer === 'hi' ? c.nameHi : c.name;
}
