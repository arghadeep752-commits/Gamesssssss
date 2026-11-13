import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import * as MediaLibrary from 'expo-media-library';
import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, StyleSheet, View, useWindowDimensions, type ViewToken } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { formatDay, formatTime } from '../../lib/format';
import { haptic } from '../../lib/haptics';
import { deleteAsset, idFromUri, loadByIds, loadPage, mediaPermission, shareAssets, type Filter } from '../../lib/media';
import type { Nav, RootStackParamList } from '../../navigation/types';
import { useLibrary } from '../../state/library';
import { useAccent } from '../../theme/accent';
import { palette, space } from '../../theme/tokens';
import { Button } from '../../ui/Button';
import { ConfirmSheet } from '../../ui/ConfirmSheet';
import { Icon, type IconName } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { toast } from '../../ui/Toast';
import { DetailsSheet } from './DetailsSheet';
import { VideoPage } from './VideoPage';
import { ZoomableImage } from './ZoomableImage';

const BAR_H = 64;
const MAX_PAGES_TO_FIND = 20;

function Action({ icon, label, onPress, color, a11y }: { icon: IconName; label: string; onPress: () => void; color?: string; a11y?: string }) {
  return (
    <Tap haptic="selection" onPress={onPress} style={styles.action} accessibilityLabel={a11y ?? label}>
      <Icon name={icon} size={22} color={color ?? palette.ink} />
      <T variant="caption" color={palette.ash} style={styles.actionLabel}>
        {label}
      </T>
    </Tap>
  );
}

export function ViewerScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<RouteProp<RootStackParamList, 'Viewer'>>();
  const { width, height } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const accent = useAccent();
  const filter: Filter = route.params.filter ?? 'all';
  const initialId = route.params.id ?? (route.params.uri ? idFromUri(route.params.uri) : null);

  const favorites = useLibrary((s) => s.favorites);
  const edits = useLibrary((s) => s.edits);
  const toggleFavorite = useLibrary((s) => s.toggleFavorite);
  const forget = useLibrary((s) => s.forget);

  const [assets, setAssets] = useState<MediaLibrary.Asset[] | null>(null);
  const [index, setIndex] = useState(0);
  const [status, setStatus] = useState<'loading' | 'ready' | 'denied' | 'missing'>('loading');
  const [chrome, setChrome] = useState(true);
  const [zoomed, setZoomed] = useState(false);
  const [details, setDetails] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const cursors = useRef<Record<string, string | undefined> | null>(null);
  const done = useRef(true);
  const loadingMore = useRef(false);

  useEffect(() => {
    let alive = true;
    (async () => {
      const perm = await mediaPermission(false);
      if (perm !== 'granted' && perm !== 'limited') {
        if (alive) setStatus('denied');
        return;
      }
      let list: MediaLibrary.Asset[] = [];
      if (filter === 'favorites' || filter === 'edited') {
        const ids = Object.keys(filter === 'favorites' ? useLibrary.getState().favorites : useLibrary.getState().edits);
        list = (await loadByIds(ids)).assets;
        done.current = true;
      } else {
        // Page through until the opened item turns up, so swiping stays in gallery order.
        let pages = 0;
        do {
          const page = await loadPage(filter, cursors.current);
          cursors.current = page.cursors;
          done.current = page.done;
          list = [...list, ...page.assets];
          pages++;
        } while (initialId && !done.current && pages < MAX_PAGES_TO_FIND && !list.some((a) => a.id === initialId));
      }
      let i = initialId ? list.findIndex((a) => a.id === initialId) : 0;
      if (i < 0 && initialId) {
        try {
          const info = await MediaLibrary.getAssetInfoAsync(initialId);
          if (info) {
            list = [info];
            done.current = true;
            i = 0;
          }
        } catch {
          // Deleted elsewhere.
        }
      }
      if (!alive) return;
      if (!list.length || i < 0) {
        setStatus('missing');
        return;
      }
      setAssets(list);
      setIndex(i);
      setStatus('ready');
    })();
    return () => {
      alive = false;
    };
    // Load once per opened item.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialId, filter]);

  const loadMore = useCallback(async () => {
    if (done.current || loadingMore.current || filter === 'favorites' || filter === 'edited') return;
    loadingMore.current = true;
    try {
      const page = await loadPage(filter, cursors.current);
      cursors.current = page.cursors;
      done.current = page.done;
      setAssets((prev) => {
        const seen = new Set(prev?.map((a) => a.id));
        return [...(prev ?? []), ...page.assets.filter((a) => !seen.has(a.id))];
      });
    } finally {
      loadingMore.current = false;
    }
  }, [filter]);

  const onViewable = useRef(({ viewableItems }: { viewableItems: ViewToken[] }) => {
    const first = viewableItems.find((v) => v.isViewable);
    if (first?.index != null) setIndex(first.index);
  }).current;

  const asset = assets?.[index] ?? null;
  const favorite = asset ? !!favorites[asset.id] : false;
  const edit = asset ? edits[asset.id] : undefined;
  const isVideo = asset?.mediaType === 'video';

  const onDelete = async () => {
    if (!asset || !assets) return;
    setDeleting(true);
    const ok = await deleteAsset(asset);
    setDeleting(false);
    setConfirmDelete(false);
    if (!ok) {
      toast(isVideo ? 'The video wasn’t deleted.' : 'The photo wasn’t deleted.');
      return;
    }
    haptic.success();
    forget(asset.id);
    const next = assets.filter((a) => a.id !== asset.id);
    if (!next.length) {
      nav.goBack();
      return;
    }
    setAssets(next);
    setIndex((i) => Math.min(i, next.length - 1));
    toast('Deleted');
  };

  const onShare = async () => {
    if (!asset) return;
    const ok = await shareAssets([asset]);
    if (!ok) toast('Sharing isn’t available right now.');
  };

  const onEdit = () => {
    if (!asset) return;
    nav.navigate(isVideo ? 'VideoEditor' : 'PhotoEditor', { id: asset.id, uri: asset.uri });
  };

  const bottomInset = BAR_H + insets.bottom;

  if (status !== 'ready' || !assets) {
    return (
      <View style={styles.root}>
        <View style={[styles.topBar, { paddingTop: insets.top }]}>
          <Tap onPress={() => nav.goBack()} haptic="selection" style={styles.iconBtn} accessibilityLabel="Back">
            <Icon name="back" />
          </Tap>
        </View>
        {status === 'loading' ? (
          <ActivityIndicator color={palette.ash} style={styles.centerFill} />
        ) : (
          <View style={styles.message}>
            <T variant="heading">{status === 'denied' ? 'Allow access to your photos' : 'This item is no longer on your phone'}</T>
            <T variant="body" color={palette.ash}>
              {status === 'denied'
                ? 'Camero Plus needs Photos and videos access to show what you’ve taken.'
                : 'It may have been deleted or moved by another app.'}
            </T>
            <Button label="Back to library" kind="secondary" onPress={() => nav.goBack()} />
          </View>
        )}
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <StatusBar hidden={!chrome} style="light" animated />
      <FlatList
        data={assets}
        horizontal
        pagingEnabled
        scrollEnabled={!zoomed}
        initialScrollIndex={index}
        getItemLayout={(_, i) => ({ length: width, offset: width * i, index: i })}
        keyExtractor={(a) => a.id}
        showsHorizontalScrollIndicator={false}
        onViewableItemsChanged={onViewable}
        viewabilityConfig={{ itemVisiblePercentThreshold: 60 }}
        onEndReached={loadMore}
        onEndReachedThreshold={2}
        windowSize={3}
        initialNumToRender={1}
        maxToRenderPerBatch={2}
        removeClippedSubviews
        renderItem={({ item, index: i }) =>
          item.mediaType === 'video' ? (
            <VideoPage
              uri={item.uri}
              width={width}
              height={height}
              active={i === index}
              chrome={chrome}
              bottomInset={bottomInset}
              onTap={() => setChrome((c) => !c)}
            />
          ) : (
            <ZoomableImage
              uri={item.uri}
              width={width}
              height={height}
              active={i === index}
              onTap={() => setChrome((c) => !c)}
              onZoomChange={setZoomed}
            />
          )
        }
      />

      {chrome && asset ? (
        <Animated.View entering={FadeIn.duration(140)} exiting={FadeOut.duration(140)} style={[styles.topBar, styles.scrim, { paddingTop: insets.top }]}>
          <Tap onPress={() => nav.goBack()} haptic="selection" style={styles.iconBtn} accessibilityLabel="Back">
            <Icon name="back" />
          </Tap>
          <View style={styles.titleBox}>
            <T variant="bodyStrong" numberOfLines={1}>
              {formatDay(asset.creationTime)}
            </T>
            <View style={styles.subtitle}>
              <T variant="caption" color={palette.ash}>
                {formatTime(asset.creationTime)}
              </T>
              {edit ? (
                <View style={[styles.tag, { borderColor: accent }]}>
                  <T variant="caption" color={accent}>
                    Edited
                  </T>
                </View>
              ) : null}
            </View>
          </View>
          <Tap onPress={() => nav.navigate('Gallery', { filter })} haptic="selection" style={styles.iconBtn} accessibilityLabel="All photos and videos">
            <Icon name="gallery" />
          </Tap>
        </Animated.View>
      ) : null}

      {chrome && asset ? (
        <Animated.View
          entering={FadeIn.duration(140)}
          exiting={FadeOut.duration(140)}
          style={[styles.bottomBar, styles.scrim, { paddingBottom: insets.bottom, height: bottomInset }]}
        >
          <Action icon="share" label="Share" onPress={onShare} />
          <Action
            icon={favorite ? 'heart-fill' : 'heart'}
            label="Favourite"
            a11y={favorite ? 'Remove from favourites' : 'Add to favourites'}
            color={favorite ? accent : undefined}
            onPress={() => {
              const on = toggleFavorite(asset.id);
              if (on) haptic.light();
            }}
          />
          <Action icon="adjust" label="Edit" onPress={onEdit} />
          <Action icon="info" label="Details" onPress={() => setDetails(true)} />
          <Action icon="trash" label="Delete" onPress={() => setConfirmDelete(true)} />
        </Animated.View>
      ) : null}

      <DetailsSheet asset={asset} edit={edit} visible={details} onClose={() => setDetails(false)} />
      <ConfirmSheet
        visible={confirmDelete}
        title={isVideo ? 'Delete this video?' : 'Delete this photo?'}
        message="It will be removed from your phone and from other gallery apps."
        confirmLabel="Delete"
        danger
        busy={deleting}
        onConfirm={onDelete}
        onClose={() => setConfirmDelete(false)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  scrim: { backgroundColor: palette.scrim },
  topBar: { position: 'absolute', top: 0, left: 0, right: 0, flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.sm, minHeight: 52 },
  iconBtn: { width: 44, height: 52, alignItems: 'center', justifyContent: 'center' },
  titleBox: { flex: 1, alignItems: 'center', paddingVertical: 6 },
  subtitle: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  tag: { borderWidth: 1, borderRadius: 6, paddingHorizontal: 5, paddingVertical: 0 },
  bottomBar: { position: 'absolute', left: 0, right: 0, bottom: 0, flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-around', paddingTop: 8 },
  action: { minWidth: 60, alignItems: 'center', paddingVertical: 2 },
  actionLabel: { marginTop: 3 },
  centerFill: { flex: 1 },
  message: { flex: 1, justifyContent: 'center', paddingHorizontal: space.xl, gap: space.md },
});
