import type { HomeSection } from './constants';

export type WallpaperStatus = 'draft' | 'published' | 'deleting';
export type RequestedStatus = 'draft' | 'published';
export type ProcessingState = 'uploading' | 'processing' | 'ready' | 'failed';

/** A wallpaper as the apps use it: timestamps are epoch milliseconds, missing fields have safe defaults. */
export interface Wallpaper {
  id: string;
  title: string;
  description: string;
  categoryIds: string[];
  tags: string[];
  status: WallpaperStatus;
  requestedStatus: RequestedStatus;
  processing: ProcessingState;
  processingError: string | null;
  featured: boolean;
  originalUrl: string | null;
  previewUrl: string | null;
  thumbnailUrl: string | null;
  originalStoragePath: string | null;
  previewStoragePath: string | null;
  thumbnailStoragePath: string | null;
  width: number;
  height: number;
  aspectRatio: number;
  fileSizeBytes: number;
  mimeType: string | null;
  /** Tiny base64 WebP data URI shown while the real image loads. */
  placeholder: string | null;
  dominantColor: string | null;
  /** Increments every time the image is replaced; used to key on-device caches. */
  imageVersion: number;
  favoriteCount: number;
  downloadCount: number;
  searchKeywords: string[];
  createdAt: number | null;
  updatedAt: number | null;
  publishedAt: number | null;
  processedAt: number | null;
  createdBy: string | null;
  updatedBy: string | null;
}

export interface Category {
  id: string;
  name: string;
  nameHi: string;
  slug: string;
  description: string;
  sortOrder: number;
  isActive: boolean;
  wallpaperCount: number;
  coverUrl: string | null;
  coverThumbUrl: string | null;
  coverImagePath: string | null;
  coverThumbnailPath: string | null;
  coverPlaceholder: string | null;
  createdAt: number | null;
  updatedAt: number | null;
}

export interface FestivalConfig {
  enabled: boolean;
  title: string;
  titleHi: string;
  categoryId: string | null;
}

export interface AppConfig {
  featuredWallpaperIds: string[];
  featuredCategoryIds: string[];
  homeSectionOrder: HomeSection[];
  festival: FestivalConfig;
  maintenanceMode: boolean;
  maintenanceMessage: string;
  minimumSupportedVersionCode: number;
  updateUrl: string;
  supportEmail: string;
  shareMessage: string;
  updatedAt: number | null;
}

export interface FavoriteRecord {
  wallpaperId: string;
  createdAt: number | null;
}

export interface AdminRole {
  uid: string;
  email: string;
  displayName: string | null;
  grantedBy: string;
  createdAt: number | null;
}

export type AdminAction =
  | 'wallpaper.created'
  | 'wallpaper.updated'
  | 'wallpaper.published'
  | 'wallpaper.unpublished'
  | 'wallpaper.imageReplaced'
  | 'wallpaper.processed'
  | 'wallpaper.processingFailed'
  | 'wallpaper.deleted'
  | 'category.created'
  | 'category.updated'
  | 'category.deleted'
  | 'categories.seeded'
  | 'config.updated'
  | 'admin.bootstrapped'
  | 'admin.granted'
  | 'admin.revoked';

export interface AdminLogEntry {
  id: string;
  action: AdminAction;
  targetType: 'wallpaper' | 'category' | 'config' | 'admin';
  targetId: string | null;
  targetLabel: string;
  actorUid: string;
  actorEmail: string | null;
  details: string | null;
  createdAt: number | null;
}

export interface GlobalStats {
  totalDownloads: number;
  totalFavorites: number;
  uploadsSucceeded: number;
  uploadsFailed: number;
}
