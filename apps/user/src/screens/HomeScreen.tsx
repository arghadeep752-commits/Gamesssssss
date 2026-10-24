import { useNavigation } from '@react-navigation/native';
import { useCallback, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { categoryLabel, type Category, type HomeSection } from '@devdarshan/shared';
import { AppText, Avatar, EmptyState, Icon, IconButton, SectionTitle, Skeleton, Touchable, useTheme } from '@devdarshan/ui';
import { BrandMark } from '../components/Brand';
import { DemoBanner } from '../components/DemoBanner';
import { buildInfo } from '../config';
import { CategoryArtwork, CategoryBubble } from '../components/CategoryVisuals';
import { FeaturedStrip } from '../components/FeaturedStrip';
import { OfflineBanner } from '../components/OfflineBanner';
import { WallpaperGrid } from '../components/WallpaperGrid';
import { useAppConfig } from '../data/appConfig';
import { useAuth } from '../data/auth';
import { useCategories, useLatestWallpapers, useWallpapersByIds } from '../data/queries';
import type { RootNavigation } from '../navigation/types';
import { useOpenPreview } from '../navigation/useOpenPreview';

function FestivalBanner({ title, subtitle, category, onPress }: { title: string; subtitle: string; category: Category; onPress: () => void }) {
  const { colors, radii, spacing } = useTheme();
  return (
    <Touchable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={title}
      style={[styles.festival, { backgroundColor: colors.goldSoft, borderRadius: radii.lg, marginHorizontal: spacing.lg }]}
    >
      <CategoryArtwork category={category} size={{ width: 64, height: 64 }} radius={radii.md} />
      <View style={{ flex: 1 }}>
        <AppText variant="overline" color="gold">
          FESTIVAL COLLECTION
        </AppText>
        <AppText variant="heading" numberOfLines={1}>
          {title}
        </AppText>
        {subtitle ? (
          <AppText variant="caption" color="textMuted" numberOfLines={1}>
            {subtitle}
          </AppText>
        ) : null}
      </View>
      <Icon name="chevronRight" size={20} color={colors.textMuted} />
    </Touchable>
  );
}

export function HomeScreen() {
  const navigation = useNavigation<RootNavigation>();
  const insets = useSafeAreaInsets();
  const { colors, spacing } = useTheme();
  const { config, loaded } = useAppConfig();
  const { user } = useAuth();
  const latest = useLatestWallpapers();
  const categories = useCategories();
  const featured = useWallpapersByIds(config.featuredWallpaperIds, loaded);
  const openPreview = useOpenPreview();
  const [refreshing, setRefreshing] = useState(false);

  const homeCategories = useMemo(() => {
    const all = categories.data ?? [];
    if (config.featuredCategoryIds.length === 0) return all;
    const byId = new Map(all.map((c) => [c.id, c]));
    const picked = config.featuredCategoryIds.map((id) => byId.get(id)).filter((c): c is Category => Boolean(c));
    return picked.length > 0 ? picked : all;
  }, [categories.data, config.featuredCategoryIds]);

  const festivalCategory =
    config.festival.enabled && config.festival.categoryId
      ? (categories.data ?? []).find((c) => c.id === config.festival.categoryId)
      : undefined;

  const featuredItems = featured.data?.items ?? [];

  const onRefresh = useCallback(async () => {
    setRefreshing(true);
    try {
      await Promise.all([latest.refetch(), categories.refetch(), featured.refetch()]);
    } finally {
      setRefreshing(false);
    }
  }, [categories, featured, latest]);

  const openCategory = useCallback(
    (category: Category) => navigation.navigate('Category', { categoryId: category.id, title: category.name }),
    [navigation],
  );

  const renderSection = (section: HomeSection) => {
    switch (section) {
      case 'featured':
        if (config.featuredWallpaperIds.length === 0 || (!featured.isPending && featuredItems.length === 0)) return null;
        return (
          <View key="featured">
            <SectionTitle title="Today's Darshan" />
            <FeaturedStrip
              wallpapers={featuredItems}
              loading={featured.isPending}
              onOpen={(w) => openPreview(featuredItems, w)}
            />
          </View>
        );
      case 'categories':
        if (!categories.isPending && homeCategories.length === 0) return null;
        return (
          <View key="categories">
            <SectionTitle title="Explore by deity" action="See all" onAction={() => navigation.navigate('Tabs', { screen: 'Categories' })} />
            {categories.isPending ? (
              <View style={styles.bubbleRow}>
                {[0, 1, 2, 3].map((i) => (
                  <Skeleton key={i} style={{ width: 68, height: 68, marginRight: 12 }} radius={16} />
                ))}
              </View>
            ) : (
              <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.bubbleRow}>
                {homeCategories.map((c) => (
                  <CategoryBubble key={c.id} category={c} onPress={() => openCategory(c)} />
                ))}
              </ScrollView>
            )}
          </View>
        );
      case 'festival':
        if (!festivalCategory) return null;
        return (
          <View key="festival" style={{ marginTop: spacing.xl }}>
            <FestivalBanner
              title={config.festival.title || festivalCategory.name}
              subtitle={config.festival.titleHi || categoryLabel(festivalCategory, 'hi')}
              category={festivalCategory}
              onPress={() => openCategory(festivalCategory)}
            />
          </View>
        );
      default:
        return null;
    }
  };

  const header = (
    <View>
      <View style={[styles.header, { paddingTop: insets.top + 6, paddingHorizontal: spacing.lg }]}>
        <BrandMark />
        <View style={styles.headerActions}>
          <IconButton name="search" accessibilityLabel="Search wallpapers" onPress={() => navigation.navigate('Search')} testID="home-search" />
          {user ? (
            <Touchable
              onPress={() => navigation.navigate('Tabs', { screen: 'Profile' })}
              accessibilityRole="button"
              accessibilityLabel="Your profile"
              style={styles.avatarButton}
            >
              <Avatar uri={user.photoURL} name={user.displayName} size={32} />
            </Touchable>
          ) : null}
        </View>
      </View>
      <OfflineBanner />
      {buildInfo.demo ? <DemoBanner /> : null}
      {config.homeSectionOrder.filter((s) => s !== 'latest').map(renderSection)}
      <SectionTitle title="Latest wallpapers" />
    </View>
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <WallpaperGrid
        data={latest.items}
        header={header}
        loading={latest.isPending}
        error={latest.error}
        onRetry={() => void latest.refetch()}
        hasMore={latest.hasNextPage}
        loadingMore={latest.isFetchingNextPage}
        onLoadMore={() => void latest.fetchNextPage()}
        refreshing={refreshing}
        onRefresh={onRefresh}
        onOpen={(w) => openPreview(latest.items, w)}
        empty={
          <EmptyState
            icon="image"
            title="Wallpapers are on their way"
            message="New darshan wallpapers will appear here as soon as they are published."
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
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingBottom: 6,
  },
  headerActions: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  avatarButton: {
    borderRadius: 20,
    overflow: 'hidden',
    padding: 4,
  },
  bubbleRow: {
    flexDirection: 'row',
    paddingHorizontal: 12,
    gap: 4,
  },
  festival: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    overflow: 'hidden',
  },
});
