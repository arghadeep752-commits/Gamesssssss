import { EXTENSION_FOR_TYPE, TYPE_FOR_EXTENSION, isAcceptedImageType, type AcceptedImageType, type ImageExtension } from './constants';

/**
 * Cloud Storage layout.
 *
 *   uploads/wallpapers/{id}/source.{jpg|png|webp}   written by admins, read by the processor, then deleted
 *   uploads/categories/{id}/cover.{jpg|png|webp}    same, for category covers
 *   wallpapers/{id}/original.{ext}                  normalised original (downloads + set wallpaper)
 *   wallpapers/{id}/preview.webp                    full-screen preview
 *   wallpapers/{id}/thumb.webp                      grid thumbnail
 *   categories/{id}/cover.webp, cover_thumb.webp    category artwork
 *
 * Only the Cloud Functions write outside uploads/.
 */

export function wallpaperUploadPath(id: string, ext: ImageExtension): string {
  return `uploads/wallpapers/${id}/source.${ext}`;
}

export function categoryCoverUploadPath(id: string, ext: ImageExtension): string {
  return `uploads/categories/${id}/cover.${ext}`;
}

export function wallpaperUploadPrefix(id: string): string {
  return `uploads/wallpapers/${id}/`;
}

export function wallpaperOutputPrefix(id: string): string {
  return `wallpapers/${id}/`;
}

export function wallpaperOutputPaths(id: string, originalExt: ImageExtension) {
  return {
    original: `wallpapers/${id}/original.${originalExt}`,
    preview: `wallpapers/${id}/preview.webp`,
    thumbnail: `wallpapers/${id}/thumb.webp`,
  };
}

export function categoryOutputPaths(id: string) {
  return {
    cover: `categories/${id}/cover.webp`,
    coverThumb: `categories/${id}/cover_thumb.webp`,
  };
}

export type ParsedUploadPath =
  | { kind: 'wallpaper'; id: string; ext: ImageExtension }
  | { kind: 'categoryCover'; id: string; ext: ImageExtension };

const WALLPAPER_UPLOAD = /^uploads\/wallpapers\/([A-Za-z0-9_-]{1,40})\/source\.(jpg|png|webp)$/;
const CATEGORY_UPLOAD = /^uploads\/categories\/([a-z0-9][a-z0-9-]{1,47})\/cover\.(jpg|png|webp)$/;

export function parseUploadPath(path: string | null | undefined): ParsedUploadPath | null {
  if (!path) return null;
  const w = WALLPAPER_UPLOAD.exec(path);
  if (w) return { kind: 'wallpaper', id: w[1] as string, ext: w[2] as ImageExtension };
  const c = CATEGORY_UPLOAD.exec(path);
  if (c) return { kind: 'categoryCover', id: c[1] as string, ext: c[2] as ImageExtension };
  return null;
}

export function extensionForMime(mime: string | null | undefined): ImageExtension | null {
  if (!mime) return null;
  const lower = mime.toLowerCase().split(';')[0]?.trim() ?? '';
  if (lower === 'image/jpg') return 'jpg';
  return isAcceptedImageType(lower) ? EXTENSION_FOR_TYPE[lower as AcceptedImageType] : null;
}

export function mimeForExtension(ext: ImageExtension): AcceptedImageType {
  return TYPE_FOR_EXTENSION[ext];
}

/** Public download URL for an object that carries a Firebase download token. */
export function firebaseDownloadUrl(bucket: string, path: string, token: string): string {
  return `https://firebasestorage.googleapis.com/v0/b/${bucket}/o/${encodeURIComponent(path)}?alt=media&token=${encodeURIComponent(token)}`;
}
