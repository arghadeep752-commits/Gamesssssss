import { FlashList, type ListRenderItemInfo } from '@shopify/flash-list';
import { useCallback, useMemo, type ReactElement } from 'react';
import { ActivityIndicator, RefreshControl, StyleSheet, View, useWindowDimensions } from 'react-native';
import type { Wallpaper } from '@devdarshan/shared';
import { AppText, ErrorState, Skeleton, useTheme } from '@devdarshan/ui';
import { useFavorites } from '../data/favorites';
import { WallpaperTile } from './WallpaperTile';

const SIDE = 16;
const GAP = 10;
const TILE_RATIO = 0.58;

export function useGridMetrics() {
  const { width } = useWindowDimensions();
  const columns = width >= 900 ? 4 : width >= 600 ? 3 : 2;
  const tileWidth = Math.floor((width - SIDE * 2 - GAP * (columns - 1)) / columns);
  return { columns, tileWidth, tileHeight: Math.round(tileWidth / TILE_RATIO) };
}

export function GridSkeleton({ count = 6 }: { count?: number }) {
  const { columns, tileWidth, tileHeight } = useGridMetrics();
  return (
    <View style={styles.skeletonWrap}>
      {Array.from({ length: count }, (_, i) => (
        <Skeleton
          key={i}
          style={{
            width: tileWidth,
            height: tileHeight,
            marginRight: (i + 1) % columns === 0 ? 0 : GAP,
            marginBottom: GAP,
          }}
        />
      ))}
    </View>
  );
}

export interface WallpaperGridProps {
  data: Wallpaper[];
  onOpen: (wallpaper: Wallpaper, index: number) => void;
  header?: ReactElement | null;
  loading?: boolean;
  error?: unknown;
  onRetry?: () => void;
  empty?: ReactElement | null;
  hasMore?: boolean;
  loadingMore?: boolean;
  onLoadMore?: () => void;
  refreshing?: boolean;
  onRefresh?: () => void;
  bottomInset?: number;
}

/**
 * Virtualised, recycled two-column grid (FlashList). Only thumbnails are loaded
 * here; previews and originals are fetched on demand.
 */
export function WallpaperGrid({
  data,
  onOpen,
  header,
  loading = false,
  error,
  onRetry,
  empty,
  hasMore = false,
  loadingMore = false,
  onLoadMore,
  refreshing = false,
  onRefresh,
  bottomInset = 24,
}: WallpaperGridProps) {
  const { colors } = useTheme();
  const { columns, tileWidth, tileHeight } = useGridMetrics();
  const { isFavorite } = useFavorites();

  const renderItem = useCallback(
    ({ item, index }: ListRenderItemInfo<Wallpaper>) => (
      <View style={styles.cell}>
        <WallpaperTile
          wallpaper={item}
          width={tileWidth}
          height={tileHeight}
          liked={isFavorite(item.id)}
          onPress={() => onOpen(item, index)}
        />
      </View>
    ),
    [isFavorite, onOpen, tileHeight, tileWidth],
  );

  const footer = useMemo(() => {
    if (loadingMore) {
      return (
        <View style={styles.footer}>
          <ActivityIndicator color={colors.primary} />
        </View>
      );
    }
    if (!hasMore && data.length > 12) {
      return (
        <View style={styles.footer}>
          <AppText variant="caption" color="textSubtle">
            ॐ · You have seen them all
          </AppText>
        </View>
      );
    }
    return null;
  }, [colors.primary, data.length, hasMore, loadingMore]);

  const emptyComponent = loading ? (
    <GridSkeleton />
  ) : error ? (
    <ErrorState onRetry={onRetry} style={styles.state} />
  ) : (
    (empty ?? null)
  );

  return (
    <FlashList
      data={data}
      numColumns={columns}
      keyExtractor={(item) => item.id}
      renderItem={renderItem}
      ListHeaderComponent={header ?? null}
      ListEmptyComponent={emptyComponent}
      ListFooterComponent={footer}
      onEndReached={hasMore && !loadingMore ? onLoadMore : undefined}
      onEndReachedThreshold={0.6}
      contentContainerStyle={{ paddingHorizontal: SIDE - GAP / 2, paddingBottom: bottomInset }}
      showsVerticalScrollIndicator={false}
      refreshControl={
        onRefresh ? (
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[colors.primary]}
            tintColor={colors.primary}
            progressBackgroundColor={colors.surface}
          />
        ) : undefined
      }
    />
  );
}

const styles = StyleSheet.create({
  cell: {
    paddingHorizontal: GAP / 2,
    paddingBottom: GAP,
  },
  skeletonWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    paddingHorizontal: GAP / 2,
  },
  footer: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  state: {
    paddingTop: 48,
  },
});
