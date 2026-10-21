import sharp from 'sharp';
import { describe, expect, it } from 'vitest';
import { ImageRejectedError, processCoverImage, processWallpaperImage } from '../src/lib/imageProcessing';

function gradient(width: number, height: number) {
  return sharp({
    create: { width, height, channels: 3, background: { r: 200, g: 110, b: 40 } },
  });
}

async function expectRejected(promise: Promise<unknown>, fragment: string) {
  let error: unknown = null;
  try {
    await promise;
  } catch (e) {
    error = e;
  }
  expect(error instanceof ImageRejectedError).toBe(true);
  expect(String((error as Error).message)).toContain(fragment);
}

describe('processWallpaperImage', () => {
  it('keeps a clean JPEG byte-for-byte and renders WebP derivatives', async () => {
    const input = await gradient(1080, 2340).jpeg({ quality: 90 }).toBuffer();
    const out = await processWallpaperImage(input);
    expect(out.original.reencoded).toBe(false);
    expect(out.original.buffer.equals(input)).toBe(true);
    expect(out.original.ext).toBe('jpg');
    expect(out.original.width).toBe(1080);
    expect(out.preview.width).toBeLessThanOrEqual(1440);
    expect(out.preview.height).toBeLessThanOrEqual(2560);
    expect(out.thumbnail.width).toBe(540);
    expect((await sharp(out.preview.buffer).metadata()).format).toBe('webp');
    expect((await sharp(out.thumbnail.buffer).metadata()).format).toBe('webp');
    expect(out.placeholder.startsWith('data:image/webp;base64,')).toBe(true);
    expect(out.placeholder.length).toBeLessThan(2000);
    expect(out.dominantColor).toMatch(/^#[0-9a-f]{6}$/);
  });

  it('strips EXIF (e.g. GPS) and applies orientation', async () => {
    const input = await gradient(2000, 1000)
      .jpeg()
      .withMetadata({ orientation: 6, exif: { IFD0: { Copyright: 'test' } } })
      .toBuffer();
    const out = await processWallpaperImage(input);
    expect(out.original.reencoded).toBe(true);
    const meta = await sharp(out.original.buffer).metadata();
    expect(meta.exif).toBeUndefined();
    expect(meta.width).toBe(1000);
    expect(meta.height).toBe(2000);
  });

  it('caps very large originals at 4096px', async () => {
    const input = await gradient(3000, 6000).png().toBuffer();
    const out = await processWallpaperImage(input);
    expect(out.original.reencoded).toBe(true);
    expect(out.original.ext).toBe('png');
    expect(Math.max(out.original.width, out.original.height)).toBe(4096);
  });

  it('rejects small, unsupported and corrupt files', async () => {
    await expectRejected(processWallpaperImage(await gradient(400, 800).jpeg().toBuffer()), 'too small');
    await expectRejected(processWallpaperImage(await gradient(1000, 2000).gif().toBuffer()), 'Unsupported format');
    await expectRejected(processWallpaperImage(Buffer.from('definitely not an image')), 'not a readable image');
  });
});

describe('processCoverImage', () => {
  it('renders a cover and thumbnail', async () => {
    const input = await gradient(1600, 900).jpeg().toBuffer();
    const out = await processCoverImage(input);
    expect(out.cover.width).toBe(1080);
    expect(out.thumbnail.width).toBe(420);
    expect(out.placeholder.startsWith('data:image/webp')).toBe(true);
  });
});
