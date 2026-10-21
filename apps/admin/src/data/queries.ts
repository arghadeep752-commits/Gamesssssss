import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { useMemo } from 'react';
import { categoryLabel, type Category, type Wallpaper } from '@devdarshan/shared';
import { fetchAdmins } from './admins';
import { fetchAllCategories } from './categories';
import { fetchActivity, fetchDashboard } from './dashboard';
import { fetchAppConfig } from './homeConfig';
import { fetchAdminPage, type AdminFilter, type Cursor } from './wallpapers';

export const adminKeys = {
  dashboard: ['dashboard'] as const,
  wallpapers: (filter: AdminFilter) => ['admin-wallpapers', filter.status, filter.categoryId ?? '', filter.search] as const,
  wallpapersRoot: ['admin-wallpapers'] as const,
  categories: ['admin-categories'] as const,
  config: ['admin-config'] as const,
  admins: ['admins'] as const,
  activity: ['activity'] as const,
};

export function useDashboard() {
  return useQuery({ queryKey: adminKeys.dashboard, queryFn: fetchDashboard, staleTime: 30 * 1000 });
}

export function useAdminWallpapers(filter: AdminFilter) {
  const result = useInfiniteQuery({
    queryKey: adminKeys.wallpapers(filter),
    queryFn: ({ pageParam }) => fetchAdminPage(filter, pageParam),
    initialPageParam: null as Cursor,
    getNextPageParam: (last) => last.cursor ?? undefined,
  });
  const items = useMemo<Wallpaper[]>(() => {
    const seen = new Set<string>();
    return (result.data?.pages ?? []).flatMap((p) => p.items).filter((w) => (seen.has(w.id) ? false : (seen.add(w.id), true)));
  }, [result.data]);
  return { ...result, items };
}

export function useAllCategories() {
  return useQuery<Category[]>({ queryKey: adminKeys.categories, queryFn: fetchAllCategories, staleTime: 60 * 1000 });
}

/** "Shri Ram, Ram Darbar" for a wallpaper's category ids. */
export function useCategoryNames() {
  const categories = useAllCategories();
  return useMemo(() => {
    const byId = new Map((categories.data ?? []).map((c) => [c.id, c]));
    return (ids: string[]) =>
      ids
        .map((id) => byId.get(id))
        .filter((c): c is Category => Boolean(c))
        .map((c) => categoryLabel(c))
        .join(', ');
  }, [categories.data]);
}

export function useAppConfigQuery() {
  return useQuery({ queryKey: adminKeys.config, queryFn: fetchAppConfig });
}

export function useAdmins() {
  return useQuery({ queryKey: adminKeys.admins, queryFn: fetchAdmins });
}

export function useActivity() {
  return useQuery({ queryKey: adminKeys.activity, queryFn: () => fetchActivity(80) });
}
