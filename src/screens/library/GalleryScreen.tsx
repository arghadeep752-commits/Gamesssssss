import { useFocusEffect, useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import type * as MediaLibrary from 'expo-media-library';
import { Image } from 'expo-image';
import React, { memo, useCallback, useEffect, useRef, useState } from 'react';
import { ActivityIndicator, FlatList, Linking, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Engine } from '../../../modules/camero-engine';
import { formatDuration } from '../../lib/format';
import { loadByIds, loadPage, mediaPermission, type Filter } from '../../lib/media';
import type { Nav, RootStackParamList } from '../../navigation/types';
import { useLibrary } from '../../state/library';
import { useSettings } from '../../state/settings';
import { useAccent } from '../../theme/accent';
import { palette, space } from '../../theme/tokens';
import { Button } from '../../ui/Button';
import { Icon } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

const FILTERS: { value: Filter; label: string }[] = [
  { value: 'all', label: 'All' },
  { value: 'photos', label: 'Photos' },
  { value: 'videos', label: 'Videos' },
  { value: 'favorites', label: 'Favourites' },
  { value: 'edited', label: 'Edited' },
  { value: 'recent', label: 'Recent' },
];

const videoThumbs = new Map<string, string>();

export const Thumb = memo(function Thumb({ asset, size }: { asset: MediaLibrary.Asset; size: number }) {
  const isVideo = asset.mediaType === 'video';
  const [uri, setUri] = useState<string | null>(isVideo ? videoThumbs.get(asset.uri) ?? null : asset.uri);
  const favorite = useLibrary((s) => !!s.favorites[asset.id]);
  const edited = useLibrary((s) => !!s.edits[asset.id]);
  useEffect(() => {
    if (!isVideo || uri) return;
    let alive = true;
    Engine.getThumbnail(asset.uri, 256)
      .then((t) => {
        if (t) videoThumbs.set(asset.uri, t);
        if (alive && t) setUri(t);
      })
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [asset.uri, isVideo, uri]);
  return (
    <View style={{ width: size, height: size, backgroundColor: palette.panel }}>
      {uri ? <Image source={{ uri }} style={StyleSheet.absoluteFill} contentFit="cover" recyclingKey={asset.id} transition={120} /> : null}
      {isVideo ? (
        <T variant="caption" style={styles.duration}>
          {formatDuration(asset.duration * 1000)}
        </T>
      ) : null}
      {favorite ? (
        <View style={styles.fav}>
          <Icon name="heart-fill" size={13} color={palette.ink} />
        </View>
      ) : null}
      {edited ? <View style={styles.editedMark} /> : null}
    </View>
  );
});

export function GalleryScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<RouteProp<RootStackParamList, 'Gallery'>>();
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const accent = useAccent();
  const columns = useSettings((s) => s.galleryColumns);
  const favorites = useLibrary((s) => s.favorites);
  const edits = useLibrary((s) => s.edits);
  const forget = useLibrary((s) => s.forget);
  const [filter, setFilter] = useState<Filter>(route.params?.filter ?? 'all');
  const [assets, setAssets] = useState<MediaLibrary.Asset[]>([]);
  const [permission, setPermission] = useState<'granted' | 'limited' | 'denied' | 'undetermined' | null>(null);
  const [loading, setLoading] = useState(false);
  const cursors = useRef<Record<string, string | undefined> | null>(null);
  const done = useRef(false);
  const busy = useRef(false);
  const gap = 2;
  const size = Math.floor((width - gap * (columns - 1)) / columns);

  const load = useCallback(
    async (reset: boolean) => {
      if (busy.current && !reset) return;
      if (!reset && done.current) return;
      busy.current = true;
      setLoading(true);
      try {
        if (filter === 'favorites' || filter === 'edited') {
          const ids = Object.keys(filter === 'favorites' ? favorites : edits);
          const res = await loadByIds(ids);
          res.missing.forEach(forget);
          setAssets(res.assets);
          done.current = true;
        } else {
          if (reset) {
            cursors.current = null;
            done.current = false;
          }
          const page = await loadPage(filter, cursors.current);
          cursors.current = page.cursors;
          done.current = page.done;
          setAssets((prev) => (reset ? page.assets : [...prev, ...page.assets]));
        }
      } finally {
        busy.current = false;
        setLoading(false);
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [filter, favorites, edits]
  );

  useFocusEffect(
    useCallback(() => {
      let alive = true;
      mediaPermission(true).then((p) => {
        if (!alive) return;
        setPermission(p);
        if (p === 'granted' || p === 'limited') load(true);
      });
      return () => {
        alive = false;
      };
    }, [load])
  );

  const header = (
    <View style={{ paddingTop: insets.top }}>
      <View style={styles.bar}>
        <Tap onPress={() => nav.goBack()} haptic="selection" style={styles.back}>
          <Icon name="back" />
        </Tap>
        <View style={styles.flex} />
        <Tap onPress={() => nav.navigate('Looks')} haptic="selection" style={styles.back}>
          <Icon name="look" />
        </Tap>
      </View>
      <T variant="title" style={styles.title}>
        Library
      </T>
      <FlatList
        horizontal
        data={FILTERS}
        keyExtractor={(f) => f.value}
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.filters}
        renderItem={({ item }) => {
          const selected = item.value === filter;
          return (
            <Tap haptic="selection" onPress={() => setFilter(item.value)} style={styles.filter}>
              <T variant="label" color={selected ? palette.ink : palette.ash}>
                {item.label}
              </T>
              <View style={[styles.filterMark, { backgroundColor: selected ? accent : 'transparent' }]} />
            </Tap>
          );
        }}
      />
    </View>
  );

  if (permission === 'denied') {
    return (
      <View style={styles.root}>
        {header}
        <View style={styles.empty}>
          <T variant="heading">Allow access to your photos</T>
          <T variant="body" color={palette.ash} style={styles.emptyText}>
            The library shows the photos and videos you take with Camero Plus. Turn on Photos and videos access in Settings.
          </T>
          <Button label="Open settings" onPress={() => Linking.openSettings()} />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root}>
      <FlatList
        data={assets}
        key={columns}
        numColumns={columns}
        keyExtractor={(a) => a.id}
        ListHeaderComponent={header}
        columnWrapperStyle={columns > 1 ? { gap } : undefined}
        ItemSeparatorComponent={() => <View style={{ height: gap }} />}
        contentContainerStyle={{ paddingBottom: insets.bottom + 24 }}
        renderItem={({ item }) => (
          <Tap pressedOpacity={0.75} onPress={() => nav.navigate('Viewer', { id: item.id, uri: item.uri, filter })}>
            <Thumb asset={item} size={size} />
          </Tap>
        )}
        getItemLayout={undefined}
        onEndReached={() => load(false)}
        onEndReachedThreshold={0.6}
        removeClippedSubviews
        initialNumToRender={24}
        maxToRenderPerBatch={24}
        windowSize={9}
        ListEmptyComponent={
          loading ? (
            <ActivityIndicator color={palette.ash} style={styles.loading} />
          ) : (
            <View style={styles.empty}>
              <T variant="heading">{filter === 'favorites' ? 'No favourites yet' : filter === 'edited' ? 'No edits yet' : 'Nothing here yet'}</T>
              <T variant="body" color={palette.ash} style={styles.emptyText}>
                {filter === 'favorites'
                  ? 'Tap the heart on a photo or video to keep it here.'
                  : filter === 'edited'
                    ? 'Copies you save from the editor show up here.'
                    : 'Photos and videos you take with Camero Plus show up here.'}
              </T>
              {filter === 'all' || filter === 'recent' ? <Button label="Open camera" kind="secondary" onPress={() => nav.goBack()} /> : null}
            </View>
          )
        }
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  bar: { height: 52, flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.sm },
  back: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  flex: { flex: 1 },
  title: { paddingHorizontal: space.lg },
  filters: { paddingHorizontal: space.sm, paddingVertical: space.sm },
  filter: { paddingHorizontal: 10, paddingVertical: 8, alignItems: 'center' },
  filterMark: { width: 14, height: 2, borderRadius: 1, marginTop: 5 },
  duration: { position: 'absolute', right: 6, bottom: 4, fontVariant: ['tabular-nums'], textShadowColor: 'rgba(0,0,0,0.6)', textShadowRadius: 3 },
  fav: { position: 'absolute', left: 6, bottom: 6 },
  editedMark: { position: 'absolute', top: 6, right: 6, width: 6, height: 6, borderRadius: 3, backgroundColor: palette.ink },
  empty: { paddingHorizontal: space.xl, paddingTop: 80, alignItems: 'flex-start', gap: space.md },
  emptyText: { marginBottom: space.sm },
  loading: { marginTop: 80 },
});
