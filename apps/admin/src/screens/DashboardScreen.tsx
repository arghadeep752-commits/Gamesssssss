import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { useCallback, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { formatCount, relativeTime, type AdminLogEntry } from '@devdarshan/shared';
import { AppText, Badge, Button, Card, Divider, EmptyState, ErrorState, Icon, Logo, SectionTitle, Skeleton, useTheme, useToast } from '@devdarshan/ui';
import { StatCard } from '../components/StatCard';
import { WallpaperRow } from '../components/WallpaperRow';
import { seedStarterCategories } from '../data/categories';
import { useCategoryNames, useDashboard } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import type { AdminNavigation } from '../navigation/types';

const ACTION_LABELS: Record<string, string> = {
  'wallpaper.created': 'created',
  'wallpaper.updated': 'edited',
  'wallpaper.published': 'published',
  'wallpaper.unpublished': 'unpublished',
  'wallpaper.imageReplaced': 'replaced the image of',
  'wallpaper.processed': 'processed',
  'wallpaper.processingFailed': 'failed to process',
  'wallpaper.deleted': 'deleted',
  'category.created': 'created category',
  'category.updated': 'edited category',
  'category.deleted': 'deleted category',
  'categories.seeded': 'added',
  'config.updated': 'updated',
  'admin.bootstrapped': 'became the first admin:',
  'admin.granted': 'made admin:',
  'admin.revoked': 'removed admin:',
};

export function ActivityRow({ entry }: { entry: AdminLogEntry }) {
  const { colors, spacing } = useTheme();
  const actor = entry.actorUid === 'system' ? 'System' : (entry.actorEmail?.split('@')[0] ?? 'An admin');
  const failed = entry.action === 'wallpaper.processingFailed';
  return (
    <View style={[styles.activity, { paddingHorizontal: spacing.lg }]}>
      <Icon name={failed ? 'alert' : entry.targetType === 'category' ? 'grid' : entry.targetType === 'admin' ? 'users' : entry.targetType === 'config' ? 'sliders' : 'image'} size={16} color={failed ? colors.danger : colors.textMuted} />
      <View style={{ flex: 1 }}>
        <AppText variant="caption" numberOfLines={2}>
          <AppText variant="caption" weight="600">
            {actor}
          </AppText>{' '}
          {ACTION_LABELS[entry.action] ?? entry.action} {entry.targetLabel}
        </AppText>
        {entry.details ? (
          <AppText variant="caption" color="textSubtle" numberOfLines={1}>
            {entry.details}
          </AppText>
        ) : null}
      </View>
      <AppText variant="caption" color="textSubtle">
        {relativeTime(entry.createdAt)}
      </AppText>
    </View>
  );
}

export function DashboardScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const insets = useSafeAreaInsets();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const { user } = useSession();
  const dashboard = useDashboard();
  const categoryNames = useCategoryNames();
  const [seeding, setSeeding] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const data = dashboard.data;

  const refetchDashboard = dashboard.refetch;
  useFocusEffect(
    useCallback(() => {
      void refetchDashboard();
    }, [refetchDashboard]),
  );

  const seed = async () => {
    setSeeding(true);
    try {
      const result = await seedStarterCategories();
      toast.show({ tone: 'success', message: `Added ${result.created} starter categories` });
      await dashboard.refetch();
    } catch (error) {
      const friendly = describeError(error);
      toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
    } finally {
      setSeeding(false);
    }
  };

  const firstName = (user?.displayName ?? '').split(' ')[0];

  return (
    <ScrollView
      style={{ backgroundColor: colors.background }}
      contentContainerStyle={{ paddingTop: insets.top + spacing.md, paddingBottom: spacing.xxxl }}
      refreshControl={
        <RefreshControl
          refreshing={refreshing}
          onRefresh={async () => {
            setRefreshing(true);
            try {
              await dashboard.refetch();
            } finally {
              setRefreshing(false);
            }
          }}
          colors={[colors.primary]}
          progressBackgroundColor={colors.surface}
        />
      }
    >
      <View style={[styles.header, { paddingHorizontal: spacing.lg }]}>
        <Logo size={34} archColor={colors.primary} flameColor={colors.secondary} flameCoreColor={colors.surface} />
        <View style={{ flex: 1 }}>
          <AppText variant="title">{firstName ? `Namaste, ${firstName}` : 'Namaste'}</AppText>
          <AppText variant="caption" color="textMuted">
            DevDarshan content dashboard
          </AppText>
        </View>
        <Badge label="ADMIN" tone="primary" />
      </View>

      <View style={{ paddingHorizontal: spacing.lg, marginTop: spacing.lg }}>
        <Button title="Upload wallpaper" icon="upload" onPress={() => navigation.navigate('WallpaperEditor', {})} fullWidth testID="dashboard-upload" />
      </View>

      {dashboard.isPending ? (
        <View style={[styles.grid, { padding: spacing.lg }]}>
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} style={{ flexBasis: '47%', flexGrow: 1, height: 96 }} />
          ))}
        </View>
      ) : dashboard.error || !data ? (
        <ErrorState onRetry={() => void dashboard.refetch()} />
      ) : (
        <>
          <View style={[styles.grid, { padding: spacing.lg, gap: spacing.md }]}>
            <StatCard icon="checkCircle" label="Published" value={data.published} hint={`${formatCount(data.total)} total`} onPress={() => navigation.navigate('Tabs', { screen: 'Wallpapers' })} />
            <StatCard icon="edit" label="Drafts" value={data.drafts} />
            <StatCard icon="alert" label="Needs attention" value={data.needsAttention} tone="warning" hint="Uploading or failed" />
            <StatCard icon="grid" label="Categories" value={data.categories} hint={`${data.activeCategories} visible`} onPress={() => navigation.navigate('Tabs', { screen: 'Categories' })} />
            <StatCard icon="upload" label="Uploads this week" value={data.uploadsThisWeek} hint={`${formatCount(data.stats.uploadsSucceeded)} ok · ${formatCount(data.stats.uploadsFailed)} failed overall`} />
            <StatCard icon="heart" label="Likes" value={data.stats.totalFavorites} hint={`${formatCount(data.stats.totalDownloads)} downloads`} />
          </View>

          {data.categories === 0 ? (
            <Card style={{ marginHorizontal: spacing.lg, padding: spacing.lg, gap: spacing.sm }}>
              <AppText variant="subheading">Start with the 20 starter categories?</AppText>
              <AppText variant="caption" color="textMuted">
                Shri Ram, Shri Krishna, Mahadev, Maa Durga and more, each with an English and Hindi name. You can edit, hide,
                reorder or delete any of them later.
              </AppText>
              <Button title="Create starter categories" variant="secondary" onPress={seed} loading={seeding} />
            </Card>
          ) : null}

          <SectionTitle title="Recent uploads" action="All" onAction={() => navigation.navigate('Tabs', { screen: 'Wallpapers' })} />
          <Card style={{ marginHorizontal: spacing.lg, overflow: 'hidden' }}>
            {data.recent.length === 0 ? (
              <EmptyState icon="image" title="No wallpapers yet" message="Upload the first darshan wallpaper." style={{ paddingVertical: 24 }} />
            ) : (
              data.recent.map((w, i) => (
                <View key={w.id}>
                  {i > 0 ? <Divider inset={80} /> : null}
                  <WallpaperRow
                    wallpaper={w}
                    categoryNames={categoryNames(w.categoryIds)}
                    onPress={() => navigation.navigate('WallpaperEditor', { wallpaperId: w.id })}
                  />
                </View>
              ))
            )}
          </Card>

          <SectionTitle title="Recent activity" action="Log" onAction={() => navigation.navigate('Activity')} />
          <Card style={{ marginHorizontal: spacing.lg, paddingVertical: spacing.xs }}>
            {data.activity.length === 0 ? (
              <AppText variant="caption" color="textMuted" style={{ padding: spacing.lg }}>
                Admin actions will be listed here.
              </AppText>
            ) : (
              data.activity.map((entry) => <ActivityRow key={entry.id} entry={entry} />)
            )}
          </Card>
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
  },
  activity: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    paddingVertical: 8,
  },
});
