import { useNavigation } from '@react-navigation/native';
import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText, Button, EmptyState, LoadingState, ScreenHeader, useTheme, useToast } from '@devdarshan/ui';
import { OfflineBanner } from '../components/OfflineBanner';
import { useSignInPrompt } from '../components/SignInSheet';
import { WallpaperGrid } from '../components/WallpaperGrid';
import { useAuth } from '../data/auth';
import { useFavorites } from '../data/favorites';
import { useWallpapersByIds } from '../data/queries';
import type { RootNavigation } from '../navigation/types';
import { useOpenPreview } from '../navigation/useOpenPreview';

export function FavoritesScreen() {
  const navigation = useNavigation<RootNavigation>();
  const { colors, spacing, radii } = useTheme();
  const toast = useToast();
  const { user, initializing } = useAuth();
  const favorites = useFavorites();
  const wallpapers = useWallpapersByIds(favorites.ids, favorites.ready && !!user);
  const openPreview = useOpenPreview();
  const openSignIn = useSignInPrompt((s) => s.open);
  const [cleaning, setCleaning] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const items = wallpapers.data?.items ?? [];
  const missing = wallpapers.data?.missing ?? [];

  const subtitle = user && favorites.ids.length > 0 ? `${favorites.ids.length} liked` : undefined;

  if (initializing) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Liked" />
        <LoadingState />
      </View>
    );
  }

  if (!user) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Liked" />
        <EmptyState
          icon="heart"
          title="Keep your favourite darshan"
          message="Sign in with Google to like wallpapers and find them here on all your phones."
          actionLabel="Sign in with Google"
          onAction={() => openSignIn()}
          secondaryLabel="Browse wallpapers"
          onSecondary={() => navigation.navigate('Tabs', { screen: 'Home' })}
        />
      </View>
    );
  }

  const removeMissing = async () => {
    setCleaning(true);
    try {
      await favorites.remove(missing);
      toast.show({ tone: 'success', message: 'Removed unavailable wallpapers' });
    } catch {
      toast.show({ tone: 'error', message: 'Could not update your likes', detail: 'Please try again.' });
    } finally {
      setCleaning(false);
    }
  };

  const header =
    missing.length > 0 && !wallpapers.isFetching ? (
      <View style={[styles.notice, { backgroundColor: colors.surfaceAlt, borderRadius: radii.md, marginHorizontal: spacing.xs }]}>
        <AppText variant="caption" color="textMuted" style={{ flex: 1 }}>
          {missing.length === 1
            ? '1 liked wallpaper is no longer available.'
            : `${missing.length} liked wallpapers are no longer available.`}
        </AppText>
        <Button title="Remove" size="sm" variant="secondary" onPress={removeMissing} loading={cleaning} />
      </View>
    ) : null;

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader title="Liked" subtitle={subtitle} />
      <OfflineBanner />
      <WallpaperGrid
        data={items}
        header={header}
        loading={!favorites.ready || (favorites.ids.length > 0 && wallpapers.isPending)}
        error={wallpapers.error}
        onRetry={() => void wallpapers.refetch()}
        refreshing={refreshing}
        onRefresh={async () => {
          setRefreshing(true);
          try {
            await wallpapers.refetch();
          } finally {
            setRefreshing(false);
          }
        }}
        onOpen={(w) => openPreview(items, w)}
        empty={
          <EmptyState
            icon="heart"
            title="No liked wallpapers yet"
            message="Tap the heart on any wallpaper to keep it here."
            actionLabel="Explore wallpapers"
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
  notice: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 10,
    marginBottom: 12,
  },
});
