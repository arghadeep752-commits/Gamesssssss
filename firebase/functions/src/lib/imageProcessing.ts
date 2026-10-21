import sharp from 'sharp';
import { LIMITS, type ImageExtension } from '../shared/constants';

/** A problem with the uploaded file itself; retrying will not help, the admin must pick another image. */
export class ImageRejectedError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ImageRejectedError';
  }
}

export interface RenderedImage {
  buffer: Buffer;
  width: number;
  height: number;
}

export interface ProcessedWallpaper {
  original: RenderedImage & { ext: ImageExtension; contentType: string; reencoded: boolean };
  preview: RenderedImage;
  thumbnail: RenderedImage;
  /** Tiny blurred WebP as a data URI, shown instantly while the real image loads. */
  placeholder: string;
  /** #rrggbb */
  dominantColor: string;
}

export interface ProcessedCover {
  cover: RenderedImage;
  thumbnail: RenderedImage;
  placeholder: string;
}

const SUPPORTED: Record<string, { ext: ImageExtension; contentType: string }> = {
  jpeg: { ext: 'jpg', contentType: 'image/jpeg' },
  png: { ext: 'png', contentType: 'image/png' },
  webp: { ext: 'webp', contentType: 'image/webp' },
};

function open(input: Buffer) {
  return sharp(input, { limitInputPixels: LIMITS.maxInputPixels, failOn: 'error' });
}

interface Inspection {
  format: keyof typeof SUPPORTED;
  width: number;
  height: number;
  needsReencode: boolean;
}

async function inspect(input: Buffer, minShortEdge: number): Promise<Inspection> {
  let meta: sharp.Metadata;
  try {
    meta = await open(input).metadata();
  } catch {
    throw new ImageRejectedError('This file is not a readable image.');
  }
  const format = meta.format ?? 'unknown';
  if (!(format in SUPPORTED)) {
    throw new ImageRejectedError(`Unsupported format (${format}). Please use JPEG, PNG or WebP.`);
  }
  if (!meta.width || !meta.height) throw new ImageRejectedError('Could not read the image dimensions.');
  if ((meta.pages ?? 1) > 1) throw new ImageRejectedError('Animated images are not supported.');
  if (meta.width * meta.height > LIMITS.maxInputPixels) {
    throw new ImageRejectedError('The image is too large (over 100 megapixels).');
  }
  const orientation = meta.orientation ?? 1;
  const swapped = orientation >= 5;
  const width = swapped ? meta.height : meta.width;
  const height = swapped ? meta.width : meta.height;
  if (Math.min(width, height) < minShortEdge) {
    throw new ImageRejectedError(
      `The image is too small (${width}×${height}). Use at least ${minShortEdge}px on the shorter side.`,
    );
  }
  const needsReencode =
    orientation !== 1 ||
    Boolean(meta.exif) ||
    Boolean(meta.xmp) ||
    Boolean(meta.iptc) ||
    Math.max(width, height) > LIMITS.originalMaxEdgePx;
  return { format: format as keyof typeof SUPPORTED, width, height, needsReencode };
}

async function render(pipeline: sharp.Sharp): Promise<RenderedImage> {
  const { data, info } = await pipeline.toBuffer({ resolveWithObject: true });
  return { buffer: data, width: info.width, height: info.height };
}

async function placeholderFor(source: Buffer): Promise<string> {
  const tiny = await open(source).rotate().resize({ width: 16, height: 32, fit: 'inside' }).webp({ quality: 40 }).toBuffer();
  return `data:image/webp;base64,${tiny.toString('base64')}`;
}

function toHex(value: number): string {
  return Math.max(0, Math.min(255, Math.round(value))).toString(16).padStart(2, '0');
}

/**
 * Turns an uploaded wallpaper into:
 *  - original: kept byte-for-byte when it is already clean; otherwise auto-rotated,
 *    stripped of EXIF/GPS metadata and capped at 4096px, in its original format;
 *  - preview (≤1440×2560 WebP) for the full-screen view;
 *  - thumbnail (≤540×1200 WebP) for grids;
 *  - a ~300-byte placeholder and the dominant colour.
 */
export async function processWallpaperImage(input: Buffer): Promise<ProcessedWallpaper> {
  const info = await inspect(input, LIMITS.minShortEdgePx);
  const format = SUPPORTED[info.format] as { ext: ImageExtension; contentType: string };

  let original: RenderedImage = { buffer: input, width: info.width, height: info.height };
  if (info.needsReencode) {
    let pipeline = open(input)
      .rotate()
      .resize({
        width: LIMITS.originalMaxEdgePx,
        height: LIMITS.originalMaxEdgePx,
        fit: 'inside',
        withoutEnlargement: true,
      });
    if (info.format === 'jpeg') pipeline = pipeline.jpeg({ quality: 92, mozjpeg: true, chromaSubsampling: '4:4:4' });
    else if (info.format === 'png') pipeline = pipeline.png({ compressionLevel: 9, adaptiveFiltering: true });
    else pipeline = pipeline.webp({ quality: 92, effort: 4 });
    original = await render(pipeline);
  }

  const source = original.buffer;
  const preview = await render(
    open(source)
      .rotate()
      .resize({ width: LIMITS.previewMaxWidth, height: LIMITS.previewMaxHeight, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 82, effort: 4 }),
  );
  const thumbnail = await render(
    open(source)
      .rotate()
      .resize({ width: LIMITS.thumbMaxWidth, height: LIMITS.thumbMaxHeight, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 72, effort: 4 }),
  );
  const placeholder = await placeholderFor(source);
  const stats = await open(thumbnail.buffer).stats();
  const dominantColor = `#${toHex(stats.dominant.r)}${toHex(stats.dominant.g)}${toHex(stats.dominant.b)}`;

  return {
    original: { ...original, ext: format.ext, contentType: format.contentType, reencoded: info.needsReencode },
    preview,
    thumbnail,
    placeholder,
    dominantColor,
  };
}

/** Category cover: a 1080px-wide WebP plus a small thumbnail for chips and cards. */
export async function processCoverImage(input: Buffer): Promise<ProcessedCover> {
  await inspect(input, 300);
  const cover = await render(
    open(input)
      .rotate()
      .resize({ width: LIMITS.coverMaxWidth, height: LIMITS.coverMaxWidth * 2, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 80, effort: 4 }),
  );
  const thumbnail = await render(
    open(input)
      .rotate()
      .resize({ width: LIMITS.coverThumbMaxWidth, height: LIMITS.coverThumbMaxWidth * 2, fit: 'inside', withoutEnlargement: true })
      .webp({ quality: 72, effort: 4 }),
  );
  return { cover, thumbnail, placeholder: await placeholderFor(input) };
}
