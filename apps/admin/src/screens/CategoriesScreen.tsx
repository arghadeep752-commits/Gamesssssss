import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useCallback, useState } from 'react';
import { FlatList, RefreshControl, StyleSheet, Switch, View } from 'react-native';
import { formatCount, type Category } from '@devdarshan/shared';
import {
  AppText,
  Button,
  Divider,
  EmptyState,
  ErrorState,
  IconButton,
  LoadingState,
  ScreenHeader,
  Touchable,
  useTheme,
  useToast,
} from '@devdarshan/ui';
import { seedStarterCategories, setCategoryActive, swapCategoryOrder } from '../data/categories';
import { adminKeys, useAllCategories } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import type { AdminNavigation } from '../navigation/types';

function CategoryThumb({ category }: { category: Category }) {
  const { colors, radii } = useTheme();
  const uri = category.coverThumbUrl ?? category.coverUrl;
  return (
    <View style={[styles.thumb, { borderRadius: radii.sm, backgroundColor: colors.primarySoft }]}>
      {uri ? (
        <Image source={{ uri }} contentFit="cover" style={StyleSheet.absoluteFill} recyclingKey={category.id} />
      ) : (
        <AppText variant="subheading" color="onPrimarySoft" numberOfLines={1} adjustsFontSizeToFit>
          {(category.nameHi || category.name).split(/\s+/).pop()}
        </AppText>
      )}
    </View>
  );
}

export function CategoriesScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const uid = user?.uid ?? '';
  const categories = useAllCategories();
  const [busyId, setBusyId] = useState<string | null>(null);
  const [seeding, setSeeding] = useState(false);
  const list = categories.data ?? [];

  const refetchCategories = categories.refetch;
  useFocusEffect(
    useCallback(() => {
      void refetchCategories();
    }, [refetchCategories]),
  );

  const refresh = () => queryClient.invalidateQueries({ queryKey: adminKeys.categories });

  const fail = (error: unknown) => {
    const friendly = describeError(error);
    toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
  };

  const move = async (index: number, delta: -1 | 1) => {
    const a = list[index];
    const b = list[index + delta];
    if (!a || !b) return;
    setBusyId(a.id);
    try {
      await swapCategoryOrder(a, b, uid);
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusyId(null);
    }
  };

  const toggle = async (category: Category, active: boolean) => {
    setBusyId(category.id);
    try {
      await setCategoryActive(category.id, active, uid);
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusyId(null);
    }
  };

  const seed = async () => {
    setSeeding(true);
    try {
      const result = await seedStarterCategories();
      toast.show({ tone: 'success', message: `Added ${result.created} starter categories` });
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader
        title="Categories"
        subtitle={list.length ? `${list.length} total · ${list.filter((c) => c.isActive).length} visible` : undefined}
        right={<IconButton name="plus" accessibilityLabel="New category" onPress={() => navigation.navigate('CategoryEditor', {})} />}
      />
      {categories.isPending ? (
        <LoadingState />
      ) : categories.error ? (
        <ErrorState onRetry={() => void categories.refetch()} />
      ) : (
        <FlatList
          data={list}
          keyExtractor={(c) => c.id}
          ItemSeparatorComponent={() => <Divider inset={76} />}
          refreshControl={
            <RefreshControl refreshing={false} onRefresh={() => void refresh()} colors={[colors.primary]} progressBackgroundColor={colors.surface} />
          }
          renderItem={({ item, index }) => (
            <Touchable
              onPress={() => navigation.navigate('CategoryEditor', { categoryId: item.id })}
              accessibilityRole="button"
              accessibilityLabel={`Edit ${item.name}`}
              style={[styles.row, { paddingHorizontal: spacing.lg, opacity: busyId === item.id ? 0.5 : 1 }]}
            >
              <CategoryThumb category={item} />
              <View style={{ flex: 1 }}>
                <AppText variant="bodyStrong" numberOfLines={1}>
                  {item.name}
                </AppText>
                <AppText variant="caption" color="textMuted" numberOfLines={1}>
                  {[item.nameHi, `${formatCount(item.wallpaperCount)} published`].filter(Boolean).join(' · ')}
                </AppText>
              </View>
              <View style={styles.order}>
                <IconButton name="chevronUp" size={18} accessibilityLabel="Move up" disabled={index === 0 || busyId !== null} onPress={() => void move(index, -1)} />
                <IconButton
                  name="chevronDown"
                  size={18}
                  accessibilityLabel="Move down"
                  disabled={index === list.length - 1 || busyId !== null}
                  onPress={() => void move(index, 1)}
                />
              </View>
              <Switch
                value={item.isActive}
                onValueChange={(v) => void toggle(item, v)}
                disabled={busyId !== null}
                trackColor={{ false: colors.borderStrong, true: colors.primarySoft }}
                thumbColor={item.isActive ? colors.primary : colors.surface}
                accessibilityLabel={item.isActive ? `Hide ${item.name}` : `Show ${item.name}`}
              />
            </Touchable>
          )}
          ListEmptyComponent={
            <EmptyState
              icon="grid"
              title="No categories yet"
              message="Create the 20 starter categories (Shri Ram, Shri Krishna, Mahadev…) or add your own."
            >
              <Button title="Create starter categories" onPress={seed} loading={seeding} style={{ marginTop: spacing.lg }} />
              <Button title="New category" variant="ghost" onPress={() => navigation.navigate('CategoryEditor', {})} />
            </EmptyState>
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
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    paddingVertical: 8,
  },
  thumb: {
    width: 48,
    height: 48,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 2,
  },
  order: {
    flexDirection: 'row',
  },
});
