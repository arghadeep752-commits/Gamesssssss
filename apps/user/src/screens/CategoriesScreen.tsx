import { useNavigation } from '@react-navigation/native';
import { FlashList } from '@shopify/flash-list';
import { useState } from 'react';
import { RefreshControl, StyleSheet, View, useWindowDimensions } from 'react-native';
import { EmptyState, ErrorState, ScreenHeader, Skeleton, useTheme } from '@devdarshan/ui';
import { CategoryCard } from '../components/CategoryVisuals';
import { OfflineBanner } from '../components/OfflineBanner';
import { useCategories } from '../data/queries';
import type { RootNavigation } from '../navigation/types';

const SIDE = 16;
const GAP = 12;

export function CategoriesScreen() {
  const navigation = useNavigation<RootNavigation>();
  const { colors } = useTheme();
  const { width } = useWindowDimensions();
  const categories = useCategories();
  const [refreshing, setRefreshing] = useState(false);
  const columns = width >= 600 ? 3 : 2;
  const cardWidth = Math.floor((width - SIDE * 2 - GAP * (columns - 1)) / columns);

  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await categories.refetch();
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader title="Categories" subtitle="Choose a deity or collection" />
      <OfflineBanner />
      <FlashList
        data={categories.data ?? []}
        numColumns={columns}
        keyExtractor={(c) => c.id}
        contentContainerStyle={{ paddingHorizontal: SIDE - GAP / 2, paddingBottom: 24, paddingTop: 8 }}
        renderItem={({ item }) => (
          <View style={styles.cell}>
            <CategoryCard
              category={item}
              width={cardWidth}
              onPress={() => navigation.navigate('Category', { categoryId: item.id, title: item.name })}
            />
          </View>
        )}
        ListEmptyComponent={
          categories.isPending ? (
            <View style={styles.skeletons}>
              {Array.from({ length: 6 }, (_, i) => (
                <Skeleton key={i} style={{ width: cardWidth, height: Math.round(cardWidth * 0.78) + 44, margin: GAP / 2 }} />
              ))}
            </View>
          ) : categories.error ? (
            <ErrorState onRetry={() => void categories.refetch()} />
          ) : (
            <EmptyState icon="grid" title="No categories yet" message="Categories will appear here once they are added." />
          )
        }
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={[colors.primary]}
            tintColor={colors.primary}
            progressBackgroundColor={colors.surface}
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
  cell: {
    paddingHorizontal: GAP / 2,
    paddingBottom: GAP + 4,
  },
  skeletons: {
    flexDirection: 'row',
    flexWrap: 'wrap',
  },
});
