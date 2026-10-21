import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import type { Category, Wallpaper } from '@devdarshan/shared';
import {
  fetchCategories,
  fetchCategoryPage,
  fetchLatestPage,
  fetchWallpaper,
  fetchWallpapersByIds,
  searchWallpapers,
  type Cursor,
  type WallpaperPage,
} from './wallpapers';

export const queryKeys = {
  latest: ['wallpapers', 'latest'] as const,
  category: (id: string) => ['wallpapers', 'category', id] as const,
  search: (term: string) => ['wallpapers', 'search', term] as const,
  byIds: (ids: readonly string[]) => ['wallpapers', 'ids', ids.join(',')] as const,
  wallpaper: (id: string) => ['wallpaper', id] as const,
  categories: ['categories'] as const,
};

function flatten(pages: WallpaperPage[] | undefined): Wallpaper[] {
  if (!pages) return [];
  const seen = new Set<string>();
  const out: Wallpaper[] = [];
  for (const page of pages) {
    for (const item of page.items) {
      if (seen.has(item.id)) continue;
      seen.add(item.id);
      out.push(item);
    }
  }
  return out;
}

export function useLatestWallpapers(enabled = true) {
  const result = useInfiniteQuery({
    queryKey: queryKeys.latest,
    queryFn: ({ pageParam }) => fetchLatestPage(pageParam),
    initialPageParam: null as Cursor,
    getNextPageParam: (last) => last.cursor ?? undefined,
    enabled,
  });
  const items = useMemo(() => flatten(result.data?.pages), [result.data]);
  return { ...result, items };
}

export function useCategoryWallpapers(categoryId: string) {
  const result = useInfiniteQuery({
    queryKey: queryKeys.category(categoryId),
    queryFn: ({ pageParam }) => fetchCategoryPage(categoryId, pageParam),
    initialPageParam: null as Cursor,
    getNextPageParam: (last) => last.cursor ?? undefined,
  });
  const items = useMemo(() => flatten(result.data?.pages), [result.data]);
  return { ...result, items };
}

export function useSearch(term: string) {
  return useQuery({
    queryKey: queryKeys.search(term),
    queryFn: () => searchWallpapers(term),
    enabled: term.trim().length >= 2,
    staleTime: 2 * 60 * 1000,
  });
}

export function useWallpapersByIds(ids: readonly string[], enabled = true) {
  return useQuery({
    queryKey: queryKeys.byIds(ids),
    queryFn: () => fetchWallpapersByIds(ids),
    enabled: enabled && ids.length > 0,
    placeholderData: (previous) => previous,
  });
}

export function useWallpaper(id: string, enabled = true) {
  return useQuery({
    queryKey: queryKeys.wallpaper(id),
    queryFn: () => fetchWallpaper(id),
    enabled,
  });
}

export function useCategories() {
  return useQuery<Category[]>({
    queryKey: queryKeys.categories,
    queryFn: fetchCategories,
    staleTime: 10 * 60 * 1000,
  });
}
