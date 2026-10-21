import { describe, expect, it } from 'vitest';
import { STARTER_CATEGORIES } from '../src/starterCategories';
import { isValidSlug, slugForName, slugify } from '../src/slug';
import { categoryOutputPaths, extensionForMime, firebaseDownloadUrl, parseUploadPath, wallpaperOutputPaths, wallpaperUploadPath } from '../src/paths';
import { formatBytes, formatCount, relativeTime, wallpaperFileName } from '../src/format';
import { millisOf, toAppConfig, toCategory, toWallpaper } from '../src/mappers';
import { categoryFormSchema, deleteCategoryInput, parseTags, setAdminRoleInput, wallpaperFormSchema } from '../src/validation';
import { palettes } from '../src/theme';

describe('starter categories', () => {
  it('has 20 unique, valid slugs in order', () => {
    expect(STARTER_CATEGORIES).toHaveLength(20);
    const ids = STARTER_CATEGORIES.map((c) => c.id);
    expect(new Set(ids).size).toBe(20);
    expect(ids.every(isValidSlug)).toBe(true);
    expect(STARTER_CATEGORIES[0]?.sortOrder).toBe(10);
    expect(STARTER_CATEGORIES[19]?.sortOrder).toBe(200);
  });

  it('has Hindi names for every category', () => {
    expect(STARTER_CATEGORIES.every((c) => /[ऀ-ॿ]/.test(c.nameHi))).toBe(true);
  });
});

describe('slugs', () => {
  it('slugifies English names', () => {
    expect(slugify('Shri Ram Darbar!')).toBe('shri-ram-darbar');
    expect(slugify('  Maa  Durgā ')).toBe('maa-durga');
  });

  it('falls back to a random slug for Hindi-only names', () => {
    const slug = slugForName('माँ काली', () => 0.5);
    expect(isValidSlug(slug)).toBe(true);
    expect(slug.startsWith('category-')).toBe(true);
  });
});

describe('storage paths', () => {
  it('round-trips upload paths', () => {
    expect(parseUploadPath(wallpaperUploadPath('abc123', 'jpg'))).toEqual({ kind: 'wallpaper', id: 'abc123', ext: 'jpg' });
    expect(parseUploadPath('uploads/categories/shri-ram/cover.webp')).toEqual({ kind: 'categoryCover', id: 'shri-ram', ext: 'webp' });
  });

  it('ignores outputs and unexpected paths', () => {
    expect(parseUploadPath(wallpaperOutputPaths('abc', 'jpg').preview)).toBeNull();
    expect(parseUploadPath(categoryOutputPaths('shri-ram').cover)).toBeNull();
    expect(parseUploadPath('uploads/wallpapers/abc/source.gif')).toBeNull();
    expect(parseUploadPath('uploads/wallpapers/../x/source.jpg')).toBeNull();
  });

  it('maps mime types', () => {
    expect(extensionForMime('image/jpeg')).toBe('jpg');
    expect(extensionForMime('IMAGE/PNG')).toBe('png');
    expect(extensionForMime('image/heic')).toBeNull();
  });

  it('builds encoded download URLs', () => {
    expect(firebaseDownloadUrl('b.firebasestorage.app', 'wallpapers/a/thumb.webp', 't-1')).toBe(
      'https://firebasestorage.googleapis.com/v0/b/b.firebasestorage.app/o/wallpapers%2Fa%2Fthumb.webp?alt=media&token=t-1',
    );
  });
});

describe('formatting', () => {
  it('formats counts and bytes', () => {
    expect(formatCount(950)).toBe('950');
    expect(formatCount(1240)).toBe('1.2K');
    expect(formatCount(3_400_000)).toBe('3.4M');
    expect(formatBytes(1536)).toBe('1.5 KB');
    expect(formatBytes(5 * 1024 * 1024)).toBe('5.0 MB');
  });

  it('formats relative times', () => {
    const now = Date.UTC(2026, 9, 21, 12);
    expect(relativeTime(now - 30_000, now)).toBe('just now');
    expect(relativeTime(now - 5 * 60_000, now)).toBe('5 min ago');
    expect(relativeTime(now - 3 * 3_600_000, now)).toBe('3 h ago');
  });

  it('builds safe file names', () => {
    expect(wallpaperFileName('Shri Rām Darbar ✨', 'AbC123xyz', 'jpg')).toBe('DevDarshan_Shri-Ram-Darbar_AbC123xy.jpg');
    expect(wallpaperFileName('श्री राम', 'id1', 'png')).toBe('DevDarshan_Wallpaper_id1.png');
  });
});

describe('mappers', () => {
  it('reads timestamps in every shape', () => {
    expect(millisOf({ toMillis: () => 42 })).toBe(42);
    expect(millisOf({ seconds: 2, nanoseconds: 5_000_000 })).toBe(2005);
    expect(millisOf(new Date(7))).toBe(7);
    expect(millisOf('nope')).toBeNull();
  });

  it('defaults missing wallpaper fields safely', () => {
    const w = toWallpaper('x', { title: 'T', status: 'published', width: 1080, height: 2340, favoriteCount: -3 });
    expect(w.status).toBe('published');
    expect(w.aspectRatio).toBeCloseTo(1080 / 2340, 5);
    expect(w.favoriteCount).toBe(0);
    expect(w.categoryIds).toEqual([]);
    expect(toWallpaper('y', { status: 'hacked' }).status).toBe('draft');
  });

  it('fills app config defaults and appends missing sections', () => {
    const c = toAppConfig({ homeSectionOrder: ['latest', 'bogus', 'featured'] });
    expect(c.homeSectionOrder).toEqual(['latest', 'featured', 'categories', 'festival']);
    expect(toAppConfig(null).maintenanceMode).toBe(false);
  });

  it('maps categories', () => {
    expect(toCategory('shri-ram', { name: 'Shri Ram', isActive: false }).isActive).toBe(false);
  });
});

describe('validation', () => {
  it('parses tags', () => {
    expect(parseTags('ram, Sita ,  #ayodhya\nRAM')).toEqual(['ram', 'Sita', 'ayodhya']);
  });

  it('validates wallpaper forms', () => {
    const ok = wallpaperFormSchema.safeParse({
      title: 'Shri Ram',
      description: '',
      categoryIds: ['shri-ram'],
      tagsText: 'ram',
      featured: false,
      requestedStatus: 'published',
    });
    expect(ok.success).toBe(true);
    const bad = wallpaperFormSchema.safeParse({
      title: 'x',
      description: '',
      categoryIds: [],
      tagsText: '',
      featured: false,
      requestedStatus: 'published',
    });
    expect(bad.success).toBe(false);
  });

  it('requires a category name in either language', () => {
    expect(categoryFormSchema.safeParse({ name: '', nameHi: 'श्री राम', description: '', isActive: true }).success).toBe(true);
    expect(categoryFormSchema.safeParse({ name: '', nameHi: '', description: '', isActive: true }).success).toBe(false);
  });

  it('validates callable inputs', () => {
    expect(setAdminRoleInput.parse({ email: ' Admin@Example.com ', grant: true }).email).toBe('admin@example.com');
    expect(deleteCategoryInput.safeParse({ categoryId: 'Bad Slug' }).success).toBe(false);
  });
});

describe('theme', () => {
  it('defines the same tokens for every accent and scheme', () => {
    const keys = Object.keys(palettes.user.light).sort();
    for (const accent of ['user', 'admin'] as const) {
      for (const scheme of ['light', 'dark'] as const) {
        expect(Object.keys(palettes[accent][scheme]).sort()).toEqual(keys);
      }
    }
  });
});
