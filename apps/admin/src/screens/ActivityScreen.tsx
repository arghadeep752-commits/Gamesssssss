import { useNavigation } from '@react-navigation/native';
import { FlatList, RefreshControl, View } from 'react-native';
import { EmptyState, ErrorState, LoadingState, ScreenHeader, useTheme } from '@devdarshan/ui';
import { useActivity } from '../data/queries';
import { ActivityRow } from './DashboardScreen';

export function ActivityScreen() {
  const navigation = useNavigation();
  const { colors, spacing } = useTheme();
  const activity = useActivity();
  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScreenHeader title="Activity log" subtitle="Latest 80 admin actions" onBack={() => navigation.goBack()} />
      {activity.isPending ? (
        <LoadingState />
      ) : activity.error ? (
        <ErrorState onRetry={() => void activity.refetch()} />
      ) : (
        <FlatList
          data={activity.data ?? []}
          keyExtractor={(e) => e.id}
          renderItem={({ item }) => <ActivityRow entry={item} />}
          contentContainerStyle={{ paddingVertical: spacing.sm }}
          ListEmptyComponent={<EmptyState icon="clock" title="No activity yet" />}
          refreshControl={
            <RefreshControl refreshing={activity.isRefetching} onRefresh={() => void activity.refetch()} colors={[colors.primary]} progressBackgroundColor={colors.surface} />
          }
        />
      )}
    </View>
  );
}
