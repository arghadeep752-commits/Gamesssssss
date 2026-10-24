import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { Image } from 'expo-image';
import { StatusBar } from 'expo-status-bar';
import { memo, useCallback, useEffect, useMemo, useState } from 'react';
import {
  FlatList,
  StyleSheet,
  View,
  useWindowDimensions,
  type LayoutChangeEvent,
  type NativeScrollEvent,
  type NativeSyntheticEvent,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { DevDarshanNative } from '@devdarshan/native';
import { categoryLabel, formatBytes, formatCount, type Wallpaper } from '@devdarshan/shared';
import {
  AppText,
  Badge,
  Button,
  EmptyState,
  Icon,
  IconButton,
  LoadingState,
  Sheet,
  Touchable,
  useTheme,
  useToast,
  type IconName,
} from '@devdarshan/ui';
import { ActionProgressCard } from '../components/ActionProgressCard';
import { SetWallpaperSheet } from '../components/SetWallpaperSheet';
import { useSignInPrompt } from '../components/SignInSheet';
import { useFavorites } from '../data/favorites';
import { useCategories, useWallpaper } from '../data/queries';
import { describeError } from '../errors';
import { useWallpaperActions } from '../features/useWallpaperActions';
import type { RootNavigation, RootStackParamList } from '../navigation/types';
import { usePreviewSessions } from '../state/previewSession';

const PreviewPage = memo(function PreviewPage({ wallpaper, width, height }: { wallpaper: Wallpaper; width: number; height: number }) {
  return (
    <View style={{ width, height }}>
      <Image
        source={wallpaper.previewUrl ? { uri: wallpaper.previewUrl } : undefined}
        placeholder={
          wallpaper.thumbnailUrl ? { uri: wallpaper.thumbnailUrl } : wallpaper.placeholder ? { uri: wallpaper.placeholder } : undefined
        }
        placeholderContentFit="contain"
        contentFit="contain"
        transition={200}
        priority="high"
        cachePolicy="memory-disk"
        recyclingKey={wallpaper.id}
        accessibilityLabel={wallpaper.title}
        style={{ width, height }}
      />
    </View>
  );
});

function ActionButton({
  icon,
  label,
  onPress,
  active = false,
  disabled = false,
  testID,
}: {
  icon: IconName;
  label: string;
  onPress: () => void;
  active?: boolean;
  disabled?: boolean;
  testID?: string;
}) {
  const { colors } = useTheme();
  const tint = active ? colors.heart : colors.previewText;
  return (
    <Touchable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ selected: active, disabled }}
      rippleColor="rgba(255,255,255,0.14)"
      style={[styles.action, { opacity: disabled ? 0.45 : 1 }]}
    >
      <Icon name={icon} size={22} color={tint} fill={active ? tint : 'none'} />
      <AppText variant="caption" color={colors.previewText} style={{ marginTop: 4, opacity: 0.85 }}>
        {label}
      </AppText>
    </Touchable>
  );
}

function InfoSheet({ wallpaper, visible, onClose }: { wallpaper: Wallpaper; visible: boolean; onClose: () => void }) {
  const { spacing } = useTheme();
  const categories = useCategories();
  const names = wallpaper.categoryIds
    .map((id) => categories.data?.find((c) => c.id === id))
    .filter((c): c is NonNullable<typeof c> => Boolean(c))
    .map((c) => categoryLabel(c));
  const rows: [string, string][] = [
    ['Resolution', wallpaper.width && wallpaper.height ? `${wallpaper.width} × ${wallpaper.height}` : '—'],
    ['File size', wallpaper.fileSizeBytes ? formatBytes(wallpaper.fileSizeBytes) : '—'],
    ['Liked by', formatCount(wallpaper.favoriteCount)],
  ];
  return (
    <Sheet visible={visible} onClose={onClose} title={wallpaper.title}>
      <View style={{ paddingHorizontal: spacing.xl, gap: spacing.md }}>
        {wallpaper.description ? (
          <AppText variant="body" color="textMuted">
            {wallpaper.description}
          </AppText>
        ) : null}
        {names.length > 0 ? (
          <View style={styles.badges}>
            {names.map((n) => (
              <Badge key={n} label={n} tone="primary" />
            ))}
            {wallpaper.tags.slice(0, 6).map((t) => (
              <Badge key={`t-${t}`} label={`#${t}`} />
            ))}
          </View>
        ) : null}
        {rows.map(([label, value]) => (
          <View key={label} style={styles.infoRow}>
            <AppText variant="label" color="textMuted">
              {label}
            </AppText>
            <AppText variant="label">{value}</AppText>
          </View>
        ))}
      </View>
    </Sheet>
  );
}

export function PreviewScreen() {
  const navigation = useNavigation<RootNavigation>();
  const { params } = useRoute<RouteProp<RootStackParamList, 'Preview'>>();
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const toast = useToast();
  const session = usePreviewSessions((s) => (params.sessionKey ? s.sessions[params.sessionKey] : undefined));
  const single = useWallpaper(params.wallpaperId, !session);
  const favorites = useFavorites();
  const openSignIn = useSignInPrompt((s) => s.open);
  const actions = useWallpaperActions();

  const list = useMemo<Wallpaper[]>(() => session ?? (single.data ? [single.data] : []), [session, single.data]);
  const initialIndex = Math.max(0, list.findIndex((w) => w.id === params.wallpaperId));
  const [index, setIndex] = useState(initialIndex);
  const [pagerHeight, setPagerHeight] = useState(0);
  const [sheet, setSheet] = useState<'set' | 'info' | null>(null);
  const [manufacturer, setManufacturer] = useState<string | null>(null);
  const current = list[Math.min(index, list.length - 1)];

  useEffect(() => {
    DevDarshanNative.getCapabilities()
      .then((c) => setManufacturer(c.manufacturer))
      .catch(() => setManufacturer(null));
  }, []);

  // Warm the cache for the neighbours so swiping feels instant.
  useEffect(() => {
    const neighbours = [list[index + 1], list[index - 1]]
      .map((w) => w?.previewUrl)
      .filter((u): u is string => Boolean(u));
    if (neighbours.length > 0) void Image.prefetch(neighbours, 'memory-disk').catch(() => false);
  }, [index, list]);

  const onLayout = useCallback((e: LayoutChangeEvent) => setPagerHeight(Math.round(e.nativeEvent.layout.height)), []);
  const onMomentumEnd = useCallback(
    (e: NativeSyntheticEvent<NativeScrollEvent>) => setIndex(Math.round(e.nativeEvent.contentOffset.x / Math.max(1, width))),
    [width],
  );

  const toggleLike = async () => {
    if (!current) return;
    try {
      const result = await favorites.toggle(current.id);
      if (result === 'needs-sign-in') openSignIn('Sign in with Google to like wallpapers and keep them on all your phones.');
    } catch (error) {
      const friendly = describeError(error);
      toast.show({ tone: 'error', message: 'Could not update your like', detail: friendly.message });
    }
  };

  const topBar = (
    <View style={[styles.topBar, { paddingTop: insets.top, paddingHorizontal: spacing.sm }]}>
      <IconButton name="arrowLeft" tone="overlay" accessibilityLabel="Close preview" onPress={() => navigation.goBack()} />
      <View style={styles.titles}>
        {current ? (
          <>
            <AppText variant="subheading" color={colors.previewText} numberOfLines={1}>
              {current.title}
            </AppText>
            {list.length > 1 ? (
              <AppText variant="caption" color={colors.previewText} style={{ opacity: 0.7 }}>
                {index + 1} / {list.length}
              </AppText>
            ) : null}
          </>
        ) : null}
      </View>
      {current ? <IconButton name="info" tone="overlay" accessibilityLabel="Wallpaper details" onPress={() => setSheet('info')} /> : null}
    </View>
  );

  if (!current) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <StatusBar style="auto" />
        <View style={{ paddingTop: insets.top }}>
          <IconButton name="arrowLeft" accessibilityLabel="Go back" onPress={() => navigation.goBack()} />
        </View>
        {single.isPending ? (
          <LoadingState label="Loading wallpaper" />
        ) : (
          <EmptyState icon="image" title="Not available" message="This wallpaper has been removed or is no longer published." />
        )}
      </View>
    );
  }

  const liked = favorites.isFavorite(current.id);

  return (
    <View style={[styles.root, { backgroundColor: colors.previewBackground }]}>
      <StatusBar style="light" />
      {topBar}
      <View style={styles.pager} onLayout={onLayout}>
        {pagerHeight > 0 ? (
          <FlatList
            data={list}
            horizontal
            pagingEnabled
            keyExtractor={(w) => w.id}
            initialScrollIndex={initialIndex}
            getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
            renderItem={({ item }) => <PreviewPage wallpaper={item} width={width} height={pagerHeight} />}
            onMomentumScrollEnd={onMomentumEnd}
            showsHorizontalScrollIndicator={false}
            initialNumToRender={1}
            maxToRenderPerBatch={2}
            windowSize={3}
            removeClippedSubviews
            scrollEnabled={!actions.busy}
          />
        ) : null}
      </View>

      {actions.progress ? (
        <View style={[styles.progress, { bottom: insets.bottom + 150, paddingHorizontal: spacing.lg }]}>
          <ActionProgressCard progress={actions.progress} onCancel={actions.cancel} />
        </View>
      ) : null}

      <View style={[styles.bottomBar, { paddingBottom: insets.bottom + spacing.md, paddingHorizontal: spacing.lg }]}>
        <View style={styles.actionRow}>
          <ActionButton icon="heart" label={liked ? 'Liked' : 'Like'} active={liked} onPress={toggleLike} testID="preview-like" />
          <ActionButton icon="download" label="Download" onPress={() => void actions.download(current)} disabled={actions.busy} testID="preview-download" />
          <ActionButton icon="share" label="Share" onPress={() => void actions.share(current, 'chooser')} disabled={actions.busy} testID="preview-share" />
          <ActionButton icon="message" label="WhatsApp" onPress={() => void actions.share(current, 'whatsapp')} disabled={actions.busy} testID="preview-whatsapp" />
        </View>
        <Button
          title="Set Wallpaper"
          icon="image"
          onPress={() => setSheet('set')}
          disabled={actions.busy}
          fullWidth
          testID="preview-set-wallpaper"
        />
      </View>

      <SetWallpaperSheet
        visible={sheet === 'set'}
        manufacturer={manufacturer}
        onClose={() => setSheet(null)}
        onSelect={(target) => {
          setSheet(null);
          void actions.setWallpaper(current, target);
        }}
      />
      <InfoSheet wallpaper={current} visible={sheet === 'info'} onClose={() => setSheet(null)} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    minHeight: 56,
    gap: 8,
  },
  titles: {
    flex: 1,
  },
  pager: {
    flex: 1,
  },
  progress: {
    position: 'absolute',
    left: 0,
    right: 0,
  },
  bottomBar: {
    paddingTop: 12,
    gap: 12,
  },
  actionRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
  },
  action: {
    minWidth: 72,
    alignItems: 'center',
    paddingVertical: 6,
    borderRadius: 12,
    overflow: 'hidden',
  },
  badges: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  infoRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
});
