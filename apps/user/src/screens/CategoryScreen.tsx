import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText, EmptyState, IconButton, ScreenHeader, useTheme } from '@devdarshan/ui';
import { OfflineBanner } from '../components/OfflineBanner';
import { WallpaperGrid } from '../components/WallpaperGrid';
import { useCategories, useCategoryWallpapers } from '../data/queries';
import type { RootNavigation, RootStackParamList } from '../navigation/types';
import { useOpenPreview } from '../navigation/useOpenPreview';

export function CategoryScreen() {
  const navigation = useNavigation<RootNavigation>();
  const { params } = useRoute<RouteProp<RootStackParamList, 'Category'>>();
  const { colors, spacing } = useTheme();
  const categories = useCategories();
  const category = categories.data?.find((c) => c.id === params.categoryId);
  const wallpapers = useCategoryWallpapers(params.categoryId);
  const openPreview = useOpenPreview();
  const [refreshing, setRefreshing] = useState(false);

  const title = category?.name ?? params.title ?? 'Wallpapers';
  const subtitle = category?.nameHi && category.nameHi !== category.name ? category.nameHi : undefined;

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await wallpapers.refetch();
    } finally {
      setRefreshing(false);
    }
  };

  const header = category?.description ? (
    <AppText variant="body" color="textMuted" style={{ paddingHorizontal: spacing.sm, paddingBottom: spacing.md }}>
      {category.description}
    </AppText>
  ) : null;

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader
        title={title}
        subtitle={subtitle}
        onBack={() => navigation.goBack()}
        right={<IconButton name="search" accessibilityLabel="Search" onPress={() => navigation.navigate('Search')} />}
      />
      <OfflineBanner />
      <WallpaperGrid
        data={wallpapers.items}
        header={header}
        loading={wallpapers.isPending}
        error={wallpapers.error}
        onRetry={() => void wallpapers.refetch()}
        hasMore={wallpapers.hasNextPage}
        loadingMore={wallpapers.isFetchingNextPage}
        onLoadMore={() => void wallpapers.fetchNextPage()}
        refreshing={refreshing}
        onRefresh={onRefresh}
        onOpen={(w) => openPreview(wallpapers.items, w)}
        empty={
          <EmptyState
            icon="image"
            title="Nothing here yet"
            message={`New ${title} wallpapers will appear here soon.`}
            actionLabel="Browse all"
            onAction={() => navigation.navigate('Tabs', { screen: 'Home' })}
          />
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
});
