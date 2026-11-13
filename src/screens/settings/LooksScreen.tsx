import { Image } from 'expo-image';
import * as MediaLibrary from 'expo-media-library';
import React, { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View, useWindowDimensions } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Engine, type LookInfo } from '../../../modules/camero-engine';
import { mediaPermission } from '../../lib/media';
import { lookName, useApp } from '../../state/app';
import { useLibrary, type Preset } from '../../state/library';
import { useSettings } from '../../state/settings';
import { useAccent } from '../../theme/accent';
import { hairline, palette, radius, space } from '../../theme/tokens';
import { ConfirmSheet } from '../../ui/ConfirmSheet';
import { Header } from '../../ui/Header';
import { Icon } from '../../ui/Icon';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { Swatch } from '../shared/LookStrip';

const COLLECTIONS: { name: string; about: string }[] = [
  { name: 'Natural', about: 'True-to-life colour with a gentle tone curve.' },
  { name: 'Everyday', about: 'Bright, crisp colour for daily shots.' },
  { name: 'Cinematic', about: 'Graded for mood, like a still from a film.' },
  { name: 'Photography', about: 'Editorial, portrait and street styles.' },
  { name: 'Film', about: 'Colour and grain modelled on film stocks.' },
];

async function samplePhoto(): Promise<string | null> {
  const perm = await mediaPermission(false);
  if (perm !== 'granted' && perm !== 'limited') return null;
  try {
    const albums = (await MediaLibrary.getAlbumsAsync()).filter((a) => a.title === 'Camero Plus');
    for (const album of albums) {
      const res = await MediaLibrary.getAssetsAsync({
        album,
        first: 1,
        mediaType: [MediaLibrary.MediaType.photo],
        sortBy: [[MediaLibrary.SortBy.creationTime, false]],
      });
      if (res.assets[0]) return res.assets[0].uri;
    }
  } catch {
    // Fall back to swatches.
  }
  return null;
}

function PresetRow({ preset, looks, onDelete }: { preset: Preset; looks: LookInfo[]; onDelete: () => void }) {
  const rename = useLibrary((s) => s.renamePreset);
  const [name, setName] = useState(preset.name);
  const accent = useAccent();
  const changes = Object.values(preset.grade.adj).filter((v) => !!v).length;
  const look = preset.grade.look !== 'none' ? `${lookName(looks, preset.grade.look)} ${preset.grade.intensity}%` : 'No look';
  return (
    <View style={styles.presetRow}>
      <View style={styles.flex}>
        <TextInput
          value={name}
          onChangeText={setName}
          onEndEditing={() => {
            const n = name.trim();
            if (n && n !== preset.name) rename(preset.id, n);
            else setName(preset.name);
          }}
          style={styles.presetInput}
          selectionColor={accent}
          maxLength={32}
          returnKeyType="done"
          accessibilityLabel="Preset name"
        />
        <T variant="caption" color={palette.ash}>
          {changes ? `${look}, ${changes} adjustment${changes === 1 ? '' : 's'}` : look}
        </T>
      </View>
      <Tap onPress={onDelete} haptic="selection" style={styles.iconBtn} accessibilityLabel={`Delete ${preset.name}`}>
        <Icon name="trash" size={20} color={palette.ash} />
      </Tap>
    </View>
  );
}

export function LooksScreen() {
  const insets = useSafeAreaInsets();
  const { width } = useWindowDimensions();
  const accent = useAccent();
  const looks = useApp((s) => s.looks);
  const loadLooks = useApp((s) => s.loadLooks);
  const presets = useLibrary((s) => s.presets);
  const removePreset = useLibrary((s) => s.removePreset);
  const lookId = useSettings((s) => s.lookId);
  const defaultIntensity = useSettings((s) => s.defaultIntensity);
  const set = useSettings((s) => s.set);
  const [sample, setSample] = useState<string | null>(null);
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [deleting, setDeleting] = useState<Preset | null>(null);

  const columns = 3;
  const gap = space.sm;
  const tile = Math.floor((width - space.lg * 2 - gap * (columns - 1)) / columns);

  useEffect(() => {
    loadLooks();
    samplePhoto().then(setSample);
  }, [loadLooks]);

  useEffect(() => {
    if (!sample || !looks.length) return;
    let alive = true;
    Engine.renderLookPreviews(sample, 320, ['none', ...looks.map((l) => l.id)])
      .then((p) => alive && setPreviews(p))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [sample, looks]);

  const groups = useMemo(() => {
    const g: Record<string, LookInfo[]> = {};
    for (const l of looks) (g[l.collection] ??= []).push(l);
    return g;
  }, [looks]);

  const renderTile = (id: string, name: string, swatch: string[]) => {
    const selected = lookId === id;
    return (
      <Tap
        key={id}
        haptic="selection"
        pressedOpacity={0.75}
        onPress={() => set({ lookId: id })}
        style={{ width: tile }}
        accessibilityState={{ selected }}
        accessibilityLabel={`${name}${selected ? ', camera look' : ''}`}
      >
        <View style={[styles.tile, { width: tile, height: tile, borderColor: selected ? accent : 'transparent' }]}>
          {previews[id] ? (
            <Image source={{ uri: previews[id] }} style={styles.tileImage} contentFit="cover" transition={150} />
          ) : (
            <View style={styles.tileSwatch}>
              <Swatch colors={swatch} active={false} accent={accent} />
            </View>
          )}
        </View>
        <View style={styles.tileFoot}>
          <T variant="caption" color={selected ? palette.ink : palette.ash} numberOfLines={1} style={styles.flex}>
            {name}
          </T>
          {selected ? <Icon name="check" size={14} color={accent} /> : null}
        </View>
      </Tap>
    );
  };

  return (
    <View style={styles.root}>
      <Header title="Looks" large />
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        <T variant="body" color={palette.ash} style={styles.intro}>
          The look you pick here is on when the camera opens. You can change it any time from the camera.
          {sample ? ' Previews use your latest photo.' : ''}
        </T>

        <View style={styles.strength}>
          <Ruler
            min={10}
            max={100}
            step={5}
            value={defaultIntensity}
            majorEvery={2}
            spacing={14}
            reference={100}
            format={(v) => `${Math.round(v)}%`}
            caption="Starting strength"
            onChange={(v) => set({ defaultIntensity: v })}
          />
        </View>

        <View style={styles.grid}>{renderTile('none', 'Original', ['#2B2B2B', '#757575', '#C9C9C9'])}</View>

        {COLLECTIONS.filter((c) => groups[c.name]?.length).map((c) => (
          <View key={c.name} style={styles.group}>
            <T variant="heading" style={styles.groupTitle}>
              {c.name}
            </T>
            <T variant="caption" color={palette.ash} style={styles.about}>
              {c.about}
            </T>
            <View style={styles.grid}>{groups[c.name].map((l) => renderTile(l.id, l.name, l.swatch))}</View>
          </View>
        ))}

        <View style={styles.group}>
          <T variant="heading" style={styles.groupTitle}>
            Your presets
          </T>
          <T variant="caption" color={palette.ash} style={styles.about}>
            {presets.length
              ? 'Tap a name to rename it. Presets appear first in the look strip.'
              : 'Save a look with your own adjustments from the camera or the editor and it shows up here.'}
          </T>
          {presets.length ? (
            <View style={styles.presets}>
              {presets.map((p) => (
                <PresetRow key={p.id} preset={p} looks={looks} onDelete={() => setDeleting(p)} />
              ))}
            </View>
          ) : null}
        </View>
      </ScrollView>

      <ConfirmSheet
        visible={!!deleting}
        title={`Delete ${deleting?.name ?? 'preset'}?`}
        message="Photos and videos you made with it stay as they are."
        confirmLabel="Delete"
        danger
        onConfirm={() => {
          if (deleting) removePreset(deleting.id);
          setDeleting(null);
        }}
        onClose={() => setDeleting(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  flex: { flex: 1 },
  intro: { paddingHorizontal: space.lg, marginBottom: space.md },
  strength: { paddingHorizontal: space.lg, marginBottom: space.lg },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm, paddingHorizontal: space.lg },
  group: { marginTop: space.xl },
  groupTitle: { paddingHorizontal: space.lg },
  about: { marginTop: 2, marginBottom: space.md, paddingHorizontal: space.lg },
  tile: { borderRadius: radius.md, borderWidth: 1.5, padding: 2, backgroundColor: palette.graphite },
  tileImage: { flex: 1, borderRadius: radius.md - 3 },
  tileSwatch: { flex: 1, alignItems: 'center', justifyContent: 'center' },
  tileFoot: { flexDirection: 'row', alignItems: 'center', marginTop: 6, marginBottom: 4, gap: 4 },
  presets: { marginHorizontal: space.lg, backgroundColor: palette.graphite, borderRadius: radius.md },
  presetRow: { flexDirection: 'row', alignItems: 'center', paddingLeft: space.lg, paddingVertical: space.sm, borderBottomWidth: hairline, borderBottomColor: palette.rule },
  presetInput: { color: palette.ink, fontFamily: 'Inter-Medium', fontSize: 15, padding: 0, marginBottom: 2 },
  iconBtn: { width: 48, height: 44, alignItems: 'center', justifyContent: 'center' },
});
