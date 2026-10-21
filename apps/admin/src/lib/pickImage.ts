import * as ImagePicker from 'expo-image-picker';
import {
  extensionForMime,
  formatBytes,
  mimeForExtension,
  type AcceptedImageType,
  type ImageExtension,
} from '@devdarshan/shared';
import { AppError } from '../errors';

export interface PickedImage {
  uri: string;
  width: number;
  height: number;
  mimeType: AcceptedImageType;
  ext: ImageExtension;
  fileSize: number | null;
  fileName: string | null;
}

function mimeFromName(name: string): string {
  const lower = name.toLowerCase();
  if (lower.endsWith('.png')) return 'image/png';
  if (lower.endsWith('.webp')) return 'image/webp';
  if (lower.endsWith('.jpg') || lower.endsWith('.jpeg')) return 'image/jpeg';
  if (lower.endsWith('.heic') || lower.endsWith('.heif')) return 'image/heic';
  return '';
}

/**
 * Opens the Android system photo picker (no storage permission needed) and
 * validates type, size and resolution before anything is uploaded. The server
 * validates again; these checks just give the admin instant feedback.
 */
export async function pickImage(options: { minShortEdge: number; maxBytes: number }): Promise<PickedImage | null> {
  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ['images'],
    allowsEditing: false,
    allowsMultipleSelection: false,
    quality: 1,
    exif: false,
  });
  if (result.canceled || !result.assets || result.assets.length === 0) return null;
  const asset = result.assets[0];
  if (!asset) return null;

  const mime = (asset.mimeType || mimeFromName(asset.fileName ?? asset.uri)).toLowerCase();
  const ext = extensionForMime(mime);
  if (!ext) {
    throw new AppError(
      'E_FORMAT',
      mime.includes('heic') || mime.includes('heif')
        ? 'HEIC photos are not supported. Export the image as JPEG or PNG and try again.'
        : 'Please choose a JPEG, PNG or WebP image.',
    );
  }
  if (asset.fileSize && asset.fileSize > options.maxBytes) {
    throw new AppError('E_SIZE', `This image is ${formatBytes(asset.fileSize)}. The limit is ${formatBytes(options.maxBytes)}.`);
  }
  if (Math.min(asset.width, asset.height) < options.minShortEdge) {
    throw new AppError(
      'E_SMALL',
      `This image is ${asset.width}×${asset.height}. Use at least ${options.minShortEdge}px on the shorter side.`,
    );
  }
  return {
    uri: asset.uri,
    width: asset.width,
    height: asset.height,
    mimeType: mimeForExtension(ext),
    ext,
    fileSize: asset.fileSize ?? null,
    fileName: asset.fileName ?? null,
  };
}
