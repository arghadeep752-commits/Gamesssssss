import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useEffect, useState } from 'react';
import { ActivityIndicator, FlatList, RefreshControl, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { categoryLabel } from '@devdarshan/shared';
import { AppText, Chip, Divider, EmptyState, ErrorState, Icon, IconButton, LoadingState, ScreenHeader, useTheme } from '@devdarshan/ui';
import { WallpaperRow } from '../components/WallpaperRow';
import { useAdminWallpapers, useAllCategories, useCategoryNames } from '../data/queries';
import type { StatusFilter } from '../data/wallpapers';
import type { AdminNavigation } from '../navigation/types';

const STATUS_OPTIONS: { value: StatusFilter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'published', label: 'Published' },
  { value: 'draft', label: 'Drafts' },
  { value: 'attention', label: 'Needs attention' },
];

export function WallpapersScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const { colors, radii, spacing, type } = useTheme();
  const [status, setStatus] = useState<StatusFilter>('all');
  const [categoryId, setCategoryId] = useState<string | null>(null);
  const [text, setText] = useState('');
  const [search, setSearch] = useState('');
  const categories = useAllCategories();
  const categoryNames = useCategoryNames();
  const list = useAdminWallpapers({ status, categoryId, search });
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setSearch(text.trim()), 400);
    return () => clearTimeout(timer);
  }, [text]);

  const refetchList = list.refetch;
  useFocusEffect(
    useCallback(() => {
      void refetchList();
    }, [refetchList]),
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader
        title="Wallpapers"
        right={<IconButton name="upload" accessibilityLabel="Upload wallpaper" onPress={() => navigation.navigate('WallpaperEditor', {})} />}
      />
      <View style={{ paddingHorizontal: spacing.lg, gap: spacing.sm, paddingBottom: spacing.sm }}>
        <View style={[styles.search, { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.pill }]}>
          <Icon name="search" size={18} color={colors.textSubtle} />
          <TextInput
            value={text}
            onChangeText={setText}
            placeholder="Search by title or tag"
            placeholderTextColor={colors.textSubtle}
            selectionColor={colors.primary}
            autoCorrect={false}
            style={[styles.searchInput, { color: colors.text, fontSize: type.body.fontSize }]}
          />
          {text ? <IconButton name="x" size={18} accessibilityLabel="Clear search" onPress={() => setText('')} /> : null}
        </View>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: spacing.sm }}>
          {STATUS_OPTIONS.map((o) => (
            <Chip key={o.value} label={o.label} selected={status === o.value} onPress={() => setStatus(o.value)} />
          ))}
        </ScrollView>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: spacing.sm }}>
          <Chip label="All categories" selected={categoryId === null} onPress={() => setCategoryId(null)} icon="grid" />
          {(categories.data ?? []).map((c) => (
            <Chip key={c.id} label={categoryLabel(c)} selected={categoryId === c.id} onPress={() => setCategoryId(c.id)} />
          ))}
        </ScrollView>
      </View>
      <Divider />
      {list.isPending ? (
        <LoadingState />
      ) : list.error ? (
        <ErrorState onRetry={() => void list.refetch()} />
      ) : (
        <FlatList
          data={list.items}
          keyExtractor={(w) => w.id}
          renderItem={({ item }) => (
            <WallpaperRow
              wallpaper={item}
              categoryNames={categoryNames(item.categoryIds)}
              onPress={() => navigation.navigate('WallpaperEditor', { wallpaperId: item.id })}
            />
          )}
          ItemSeparatorComponent={() => <Divider inset={80} />}
          onEndReached={() => {
            if (list.hasNextPage && !list.isFetchingNextPage) void list.fetchNextPage();
          }}
          onEndReachedThreshold={0.5}
          ListFooterComponent={
            list.isFetchingNextPage ? (
              <ActivityIndicator color={colors.primary} style={{ margin: spacing.lg }} />
            ) : list.items.length > 0 ? (
              <AppText variant="caption" color="textSubtle" align="center" style={{ margin: spacing.lg }}>
                {list.hasNextPage ? 'Scroll for more' : `${list.items.length} shown`}
              </AppText>
            ) : null
          }
          ListEmptyComponent={
            <EmptyState
              icon="image"
              title={search || status !== 'all' || categoryId ? 'No matches' : 'No wallpapers yet'}
              message={search || status !== 'all' || categoryId ? 'Try another filter.' : 'Upload the first wallpaper.'}
              actionLabel={search || status !== 'all' || categoryId ? undefined : 'Upload wallpaper'}
              onAction={() => navigation.navigate('WallpaperEditor', {})}
            />
          }
          refreshControl={
            <RefreshControl
              refreshing={refreshing}
              onRefresh={async () => {
                setRefreshing(true);
                try {
                  await list.refetch();
                } finally {
                  setRefreshing(false);
                }
              }}
              colors={[colors.primary]}
              progressBackgroundColor={colors.surface}
            />
          }
        />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  search: {
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 14,
    borderWidth: StyleSheet.hairlineWidth * 2,
  },
  searchInput: {
    flex: 1,
    height: 44,
    paddingHorizontal: 8,
  },
});
