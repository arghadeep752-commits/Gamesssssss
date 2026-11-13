import { useFocusEffect, useNavigation } from '@react-navigation/native';
import * as Application from 'expo-application';
import React, { useCallback, useState } from 'react';
import { Linking, PermissionsAndroid, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { Engine } from '../../../modules/camero-engine';
import { mainBack, qualitiesFor } from '../../lib/camera';
import { formatBytes, formatMp, qualityLabel } from '../../lib/format';
import { mediaPermission } from '../../lib/media';
import type { Nav } from '../../navigation/types';
import { lookName, useApp } from '../../state/app';
import { useSettings, type GridType } from '../../state/settings';
import { accents, palette, space, type AccentKey } from '../../theme/tokens';
import { ChoiceSheet, type Choice } from '../../ui/ChoiceSheet';
import { Header } from '../../ui/Header';
import { Row, Section } from '../../ui/Row';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { toast } from '../../ui/Toast';
import { QualitySheet } from '../camera/QualitySheet';

type Picker = 'grid' | 'interval' | 'location' | 'columns' | 'camera' | 'peak' | null;

const GRID: Choice<GridType>[] = [
  { value: 'off', label: 'No grid' },
  { value: 'thirds', label: 'Rule of thirds' },
  { value: 'golden', label: 'Golden ratio' },
  { value: 'square', label: 'Square guide' },
];
const INTERVALS: Choice<number>[] = [
  { value: 500, label: 'Every 0.5 seconds', detail: '15 times faster' },
  { value: 1000, label: 'Every second', detail: '30 times faster' },
  { value: 2000, label: 'Every 2 seconds', detail: '60 times faster' },
  { value: 5000, label: 'Every 5 seconds', detail: '150 times faster' },
  { value: 10000, label: 'Every 10 seconds', detail: '300 times faster' },
];
const PEAK_COLORS: Choice<string>[] = [
  { value: '#FFB46B', label: 'Amber' },
  { value: '#FF4D4D', label: 'Red' },
  { value: '#5CFF9D', label: 'Green' },
  { value: '#FFFFFF', label: 'White' },
];

type Perms = { camera: boolean; mic: boolean; media: string };

export function SettingsScreen() {
  const nav = useNavigation<Nav>();
  const insets = useSafeAreaInsets();
  const s = useSettings();
  const caps = useApp((st) => st.caps);
  const looks = useApp((st) => st.looks);
  const back = mainBack(caps);
  const [picker, setPicker] = useState<Picker>(null);
  const [quality, setQuality] = useState<'photo' | 'video' | null>(null);
  const [storage, setStorage] = useState<{ freeBytes: number; totalBytes: number } | null>(null);
  const [perms, setPerms] = useState<Perms | null>(null);

  useFocusEffect(
    useCallback(() => {
      let alive = true;
      Engine.getStorageInfo()
        .then((i) => alive && setStorage(i))
        .catch(() => {});
      Promise.all([
        PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.CAMERA),
        PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO),
        mediaPermission(false),
      ])
        .then(([camera, mic, media]) => alive && setPerms({ camera, mic, media }))
        .catch(() => {});
      return () => {
        alive = false;
      };
    }, [])
  );

  const photoValue = (() => {
    const mp = s.photo.resolution === 'standard' ? 'About 8 MP' : back?.photoMax ? formatMp(back.photoMax.width, back.photoMax.height) : 'Full';
    const fmt = s.photo.format === 'raw+jpeg' && back?.raw ? 'RAW + JPEG' : s.photo.format === 'ultrahdr' && back?.ultraHdr ? 'Ultra HDR' : 'JPEG';
    return `${mp}, ${fmt}`;
  })();
  const videoValue = (() => {
    const qs = qualitiesFor(back);
    const q = qs.includes(s.video.quality) ? s.video.quality : 'FHD';
    return `${qualityLabel(q)}, ${s.video.fps} fps`;
  })();

  const permText = (ok: boolean | undefined) => (ok == null ? '' : ok ? 'Allowed' : 'Not allowed');

  return (
    <View style={styles.root}>
      <Header title="Settings" large />
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        <Section title="Capture">
          <Row label="Photo" value={photoValue} onPress={() => setQuality('photo')} />
          <Row label="Video" value={videoValue} onPress={() => setQuality('video')} />
          <Row
            label="Open with"
            value={s.defaultCamera === 'front' ? 'Front camera' : 'Back camera'}
            onPress={() => setPicker('camera')}
          />
          <Row
            label="Time-lapse interval"
            value={INTERVALS.find((i) => i.value === s.timelapseIntervalMs)?.label.replace('Every ', '') ?? '1 second'}
            onPress={() => setPicker('interval')}
          />
          <Row
            label="Review after capture"
            detail="Opens each photo right after you take it."
            toggle={{ value: s.reviewAfterCapture, onChange: (v) => s.set({ reviewAfterCapture: v }) }}
          />
          <Row
            label="Shutter sound"
            detail="Some countries require it. Your phone may play it anyway."
            toggle={{ value: s.photo.shutterSound, onChange: (v) => s.setPhoto({ shutterSound: v }) }}
          />
          <Row
            label="Mirror front photos"
            detail="Saves selfies the way they look in the viewfinder."
            toggle={{ value: s.photo.mirrorFront, onChange: (v) => s.setPhoto({ mirrorFront: v }) }}
          />
          <Row
            label="Keep an untouched copy"
            detail="When a look is on, the photo without it is also saved, in an Originals folder."
            toggle={{ value: s.photo.keepOriginal, onChange: (v) => s.setPhoto({ keepOriginal: v }) }}
            last
          />
        </Section>

        <Section title="Viewfinder">
          <Row label="Grid" value={GRID.find((g) => g.value === s.grid)?.label} onPress={() => setPicker('grid')} />
          <Row label="Level" detail="A line that turns solid when the phone is straight." toggle={{ value: s.level, onChange: (v) => s.set({ level: v }) }} />
          <Row
            label="Focus peaking"
            detail="Outlines what’s in focus in Pro and Macro."
            toggle={{ value: s.peaking, onChange: (v) => s.set({ peaking: v }) }}
          />
          <Row
            label="Peaking colour"
            value={PEAK_COLORS.find((c) => c.value.toLowerCase() === s.peakColor.toLowerCase())?.label ?? 'Amber'}
            onPress={() => setPicker('peak')}
            disabled={!s.peaking}
          />
          <Row
            label="Zebras"
            detail="Stripes over bright areas that are about to lose detail."
            toggle={{ value: s.zebra, onChange: (v) => s.set({ zebra: v }) }}
            last
          />
        </Section>

        <Section title="Looks">
          <Row label="Camera look and presets" value={lookName(looks, s.lookId)} onPress={() => nav.navigate('Looks')} last />
        </Section>

        <Section
          title="Storage"
          note={storage ? `${formatBytes(storage.freeBytes)} free of ${formatBytes(storage.totalBytes)}.` : undefined}
        >
          <Row
            label="Save to"
            value={s.saveLocation === 'pictures' ? 'Pictures and Movies' : 'DCIM'}
            onPress={() => setPicker('location')}
          />
          <Row
            label="Clear temporary files"
            detail="Thumbnails, previews and unfinished exports. Your photos and videos aren’t touched."
            onPress={() => {
              Engine.clearCache()
                .then(() => toast('Temporary files cleared'))
                .catch(() => toast('They couldn’t be cleared right now.'));
            }}
            last
          />
        </Section>

        <Section title="Appearance">
          <View style={styles.accentRow}>
            <T variant="body" style={styles.flex}>
              Accent
            </T>
            {(Object.keys(accents) as AccentKey[]).map((k) => {
              const selected = s.accent === k;
              return (
                <Tap
                  key={k}
                  haptic="selection"
                  onPress={() => s.set({ accent: k })}
                  style={[styles.accentDot, { borderColor: selected ? accents[k].color : 'transparent' }]}
                  accessibilityLabel={`${accents[k].label} accent`}
                  accessibilityState={{ selected }}
                >
                  <View style={[styles.accentFill, { backgroundColor: accents[k].color }]} />
                </Tap>
              );
            })}
          </View>
          <Row label="Haptics" detail="Small ticks on dials, the shutter and switches." toggle={{ value: s.haptics, onChange: (v) => s.set({ haptics: v }) }} />
          <Row label="Library grid" value={`${s.galleryColumns} across`} onPress={() => setPicker('columns')} last />
        </Section>

        <Section title="Permissions" note="Change these in Android settings.">
          <Row label="Camera" value={permText(perms?.camera)} onPress={() => Linking.openSettings()} />
          <Row label="Microphone" detail="Needed for sound in videos." value={permText(perms?.mic)} onPress={() => Linking.openSettings()} />
          <Row
            label="Photos and videos"
            detail="Needed for the library and editor."
            value={perms ? (perms.media === 'granted' ? 'Allowed' : perms.media === 'limited' ? 'Some items' : 'Not allowed') : ''}
            onPress={() => Linking.openSettings()}
            last
          />
        </Section>

        <Section title="About">
          <Row label="What this phone’s cameras can do" onPress={() => nav.navigate('CameraReport')} />
          <Row label="Privacy" onPress={() => nav.navigate('Privacy')} />
          <Row label="Open-source licences" onPress={() => nav.navigate('Licenses')} />
          <Row label="Version" value={`${Application.nativeApplicationVersion ?? '1.0.0'} (${Application.nativeBuildVersion ?? '1'})`} last />
        </Section>
      </ScrollView>

      <QualitySheet visible={quality === 'photo'} onClose={() => setQuality(null)} mode="photo" cam={back} />
      <QualitySheet visible={quality === 'video'} onClose={() => setQuality(null)} mode="video" cam={back} />

      <ChoiceSheet visible={picker === 'grid'} title="Grid" choices={GRID} value={s.grid} onChange={(v) => s.set({ grid: v })} onClose={() => setPicker(null)} />
      <ChoiceSheet
        visible={picker === 'interval'}
        title="Time-lapse interval"
        note="One frame is taken each interval. Playback runs at 30 fps."
        choices={INTERVALS}
        value={s.timelapseIntervalMs}
        onChange={(v) => s.set({ timelapseIntervalMs: v })}
        onClose={() => setPicker(null)}
      />
      <ChoiceSheet
        visible={picker === 'location'}
        title="Save to"
        choices={[
          { value: 'dcim', label: 'DCIM', detail: 'DCIM/Camero Plus, next to your other camera photos.' },
          { value: 'pictures', label: 'Pictures and Movies', detail: 'Photos in Pictures/Camero Plus, videos in Movies/Camero Plus.' },
        ]}
        value={s.saveLocation}
        onChange={(v) => s.set({ saveLocation: v })}
        onClose={() => setPicker(null)}
      />
      <ChoiceSheet
        visible={picker === 'columns'}
        title="Library grid"
        choices={[
          { value: 3, label: '3 across', detail: 'Bigger thumbnails' },
          { value: 4, label: '4 across', detail: 'More at a glance' },
        ]}
        value={s.galleryColumns}
        onChange={(v) => s.set({ galleryColumns: v === 4 ? 4 : 3 })}
        onClose={() => setPicker(null)}
      />
      <ChoiceSheet
        visible={picker === 'camera'}
        title="Open with"
        choices={[
          { value: 'back', label: 'Back camera' },
          { value: 'front', label: 'Front camera' },
        ]}
        value={s.defaultCamera}
        onChange={(v) => s.set({ defaultCamera: v })}
        onClose={() => setPicker(null)}
      />
      <ChoiceSheet
        visible={picker === 'peak'}
        title="Peaking colour"
        choices={PEAK_COLORS}
        value={PEAK_COLORS.find((c) => c.value.toLowerCase() === s.peakColor.toLowerCase())?.value ?? '#FFB46B'}
        onChange={(v) => s.set({ peakColor: v })}
        onClose={() => setPicker(null)}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  flex: { flex: 1 },
  accentRow: { minHeight: 54, flexDirection: 'row', alignItems: 'center', paddingRight: space.md, gap: space.xs, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: palette.rule },
  accentDot: { width: 36, height: 36, borderRadius: 18, borderWidth: 2, padding: 4 },
  accentFill: { flex: 1, borderRadius: 14 },
});
