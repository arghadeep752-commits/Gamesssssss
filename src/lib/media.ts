import * as MediaLibrary from 'expo-media-library';

import { Engine } from '../../modules/camero-engine';

export type Filter = 'all' | 'photos' | 'videos' | 'favorites' | 'edited' | 'recent';

export const ALBUM = 'Camero Plus';

export async function mediaPermission(request: boolean): Promise<'granted' | 'limited' | 'denied' | 'undetermined'> {
  try {
    const current = await MediaLibrary.getPermissionsAsync(false, ['photo', 'video']);
    if (current.granted) return current.accessPrivileges === 'limited' ? 'limited' : 'granted';
    if (!request) return current.canAskAgain ? 'undetermined' : 'denied';
    const res = await MediaLibrary.requestPermissionsAsync(false, ['photo', 'video']);
    if (res.granted) return res.accessPrivileges === 'limited' ? 'limited' : 'granted';
    return 'denied';
  } catch {
    return 'denied';
  }
}

async function appAlbums(): Promise<MediaLibrary.Album[]> {
  const albums = await MediaLibrary.getAlbumsAsync();
  return albums.filter((a) => a.title === ALBUM);
}

export type Page = { assets: MediaLibrary.Asset[]; done: boolean; cursors: Record<string, string | undefined> };

const PAGE = 60;

/** Loads the next page of Camero Plus media, newest first, merged across its folders. */
export async function loadPage(filter: Filter, cursors: Record<string, string | undefined> | null): Promise<Page> {
  const albums = await appAlbums();
  if (!albums.length) return { assets: [], done: true, cursors: {} };
  const mediaType =
    filter === 'photos'
      ? [MediaLibrary.MediaType.photo]
      : filter === 'videos'
        ? [MediaLibrary.MediaType.video]
        : [MediaLibrary.MediaType.photo, MediaLibrary.MediaType.video];
  const createdAfter = filter === 'recent' ? Date.now() - 7 * 24 * 3600 * 1000 : undefined;
  const nextCursors: Record<string, string | undefined> = {};
  const all: MediaLibrary.Asset[] = [];
  let done = true;
  for (const album of albums) {
    const key = album.id;
    if (cursors && cursors[key] === 'END') {
      nextCursors[key] = 'END';
      continue;
    }
    const res = await MediaLibrary.getAssetsAsync({
      album,
      first: PAGE,
      after: cursors?.[key],
      mediaType,
      sortBy: [[MediaLibrary.SortBy.creationTime, false]],
      createdAfter,
    });
    all.push(...res.assets);
    nextCursors[key] = res.hasNextPage ? res.endCursor : 'END';
    if (res.hasNextPage) done = false;
  }
  all.sort((a, b) => b.creationTime - a.creationTime);
  return { assets: all, done, cursors: nextCursors };
}

/** Assets by id (favourites and edits), skipping ones that were deleted elsewhere. */
export async function loadByIds(ids: string[]): Promise<{ assets: MediaLibrary.Asset[]; missing: string[] }> {
  const assets: MediaLibrary.Asset[] = [];
  const missing: string[] = [];
  for (const id of ids) {
    try {
      const info = await MediaLibrary.getAssetInfoAsync(id);
      if (info) assets.push(info);
      else missing.push(id);
    } catch {
      missing.push(id);
    }
  }
  assets.sort((a, b) => b.creationTime - a.creationTime);
  return { assets, missing };
}

/** MediaStore content URIs end with the row id, which is also the media library asset id. */
export function idFromUri(uri: string): string | null {
  const m = uri.match(/\/(\d+)$/);
  return m ? m[1] : null;
}

export async function assetFromUri(uri: string): Promise<MediaLibrary.Asset | null> {
  const id = idFromUri(uri);
  if (!id) return null;
  try {
    return await MediaLibrary.getAssetInfoAsync(id);
  } catch {
    return null;
  }
}

export async function latestAsset(): Promise<MediaLibrary.Asset | null> {
  try {
    const page = await loadPage('all', null);
    return page.assets[0] ?? null;
  } catch {
    return null;
  }
}

export async function deleteAsset(asset: MediaLibrary.Asset): Promise<boolean> {
  try {
    return await MediaLibrary.deleteAssetsAsync([asset]);
  } catch {
    return false;
  }
}

/**
 * The media library hands out file paths; other apps need a MediaStore content URI with a read
 * grant. Asset ids are MediaStore row ids, shared by the images and video tables.
 */
export function contentUri(asset: Pick<MediaLibrary.Asset, 'id' | 'mediaType'>): string {
  return `content://media/external/${asset.mediaType === 'video' ? 'video' : 'images'}/media/${asset.id}`;
}

export async function shareAssets(assets: MediaLibrary.Asset[]): Promise<boolean> {
  if (!assets.length) return false;
  const videos = assets.filter((a) => a.mediaType === 'video').length;
  const mime = videos === assets.length ? 'video/*' : videos === 0 ? 'image/*' : '*/*';
  try {
    return await Engine.share(assets.map(contentUri), mime);
  } catch {
    return false;
  }
}
