/**
 * Constants shared by the user app, the admin app and the Cloud Functions.
 * Changing a value here changes behaviour everywhere, so keep the Firestore and
 * Storage security rules (firebase/*.rules) in sync with LIMITS.
 */

export const APP_NAME = 'DevDarshan';
export const APP_NAME_HI = 'देवदर्शन';
export const ADMIN_APP_NAME = 'DevDarshan Admin';

export const USER_APP_PACKAGE = 'com.devdarshan.wallpapers';
export const ADMIN_APP_PACKAGE = 'com.devdarshan.admin';

/** Region of the callable Cloud Functions (Mumbai, closest to most users). */
export const FUNCTIONS_REGION = 'asia-south1';

/** Where new builds are published (public GitHub releases). Used when the admin hasn't set an update link. */
export const DEFAULT_UPDATE_URL = 'https://github.com/arghadeep752-commits/Gamesssssss/releases/latest';

/** Project id baked into placeholder builds made before Firebase is connected. */
export const PLACEHOLDER_PROJECT_ID = 'devdarshan-not-configured';

export const COLLECTIONS = {
  wallpapers: 'wallpapers',
  categories: 'categories',
  users: 'users',
  favorites: 'favorites',
  adminRoles: 'adminRoles',
  adminLog: 'adminLog',
  appConfig: 'appConfig',
  stats: 'stats',
} as const;

export const APP_CONFIG_DOC_ID = 'public';
export const STATS_DOC_ID = 'global';

export const CALLABLES = {
  bootstrapAdmin: 'bootstrapAdmin',
  setAdminRole: 'setAdminRole',
  deleteWallpaper: 'deleteWallpaper',
  retryWallpaperProcessing: 'retryWallpaperProcessing',
  deleteCategory: 'deleteCategory',
  seedStarterCategories: 'seedStarterCategories',
  recordDownload: 'recordDownload',
  deleteMyAccount: 'deleteMyAccount',
} as const;

export const LIMITS = {
  pageSize: 24,
  adminPageSize: 25,
  featuredMax: 30,
  featuredCategoriesMax: 30,
  homeSectionsMax: 6,
  titleMin: 2,
  titleMax: 80,
  descriptionMax: 500,
  tagsMax: 15,
  tagMaxLength: 32,
  categoriesPerWallpaperMin: 1,
  categoriesPerWallpaperMax: 5,
  categoryNameMax: 60,
  categoryDescriptionMax: 300,
  configTextMax: 300,
  uploadMaxBytes: 30 * 1024 * 1024,
  coverUploadMaxBytes: 15 * 1024 * 1024,
  minShortEdgePx: 600,
  maxInputPixels: 100_000_000,
  originalMaxEdgePx: 4096,
  previewMaxWidth: 1440,
  previewMaxHeight: 2560,
  thumbMaxWidth: 540,
  thumbMaxHeight: 1200,
  coverMaxWidth: 1080,
  coverThumbMaxWidth: 420,
  searchKeywordsMax: 250,
  searchQueryMaxLength: 60,
  searchTokenPrefixMax: 15,
  idMaxLength: 40,
} as const;

export const ACCEPTED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'] as const;
export type AcceptedImageType = (typeof ACCEPTED_IMAGE_TYPES)[number];
export type ImageExtension = 'jpg' | 'png' | 'webp';

export const EXTENSION_FOR_TYPE: Readonly<Record<AcceptedImageType, ImageExtension>> = {
  'image/jpeg': 'jpg',
  'image/png': 'png',
  'image/webp': 'webp',
};

export const TYPE_FOR_EXTENSION: Readonly<Record<ImageExtension, AcceptedImageType>> = {
  jpg: 'image/jpeg',
  png: 'image/png',
  webp: 'image/webp',
};

export const HOME_SECTIONS = ['featured', 'categories', 'festival', 'latest'] as const;
export type HomeSection = (typeof HOME_SECTIONS)[number];
export const DEFAULT_HOME_SECTION_ORDER: readonly HomeSection[] = HOME_SECTIONS;

export function isAcceptedImageType(value: string | null | undefined): value is AcceptedImageType {
  return !!value && (ACCEPTED_IMAGE_TYPES as readonly string[]).includes(value.toLowerCase());
}
