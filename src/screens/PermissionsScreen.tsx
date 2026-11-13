import { useNavigation } from '@react-navigation/native';
import React, { useCallback, useEffect, useState } from 'react';
import { AppState, Linking, PermissionsAndroid, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { mediaPermission } from '../lib/media';
import type { Nav } from '../navigation/types';
import { useSettings } from '../state/settings';
import { useAccent } from '../theme/accent';
import { hairline, palette, radius, space } from '../theme/tokens';
import { Button } from '../ui/Button';
import { Icon, type IconName } from '../ui/Icon';
import { T } from '../ui/T';
import { Tap } from '../ui/Tap';

type State = 'granted' | 'denied' | 'blocked' | 'unknown';
type Perms = { camera: State; mic: State; media: State };

const legacyStorage = Platform.OS === 'android' && Number(Platform.Version) < 29;

async function check(): Promise<Perms> {
  const [camera, mic, media] = await Promise.all([
    PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.CAMERA),
    PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.RECORD_AUDIO),
    mediaPermission(false),
  ]);
  return {
    camera: camera ? 'granted' : 'unknown',
    mic: mic ? 'granted' : 'unknown',
    media: media === 'granted' || media === 'limited' ? 'granted' : media === 'denied' ? 'blocked' : 'unknown',
  };
}

function PermissionRow({ icon, title, detail, state, onAllow, last }: {
  icon: IconName;
  title: string;
  detail: string;
  state: State;
  onAllow: () => void;
  last?: boolean;
}) {
  const accent = useAccent();
  return (
    <View style={[styles.row, !last && styles.rule]}>
      <Icon name={icon} size={24} color={state === 'granted' ? accent : palette.ash} />
      <View style={styles.rowText}>
        <T variant="bodyStrong">{title}</T>
        <T variant="caption" color={palette.ash} style={styles.detail}>
          {detail}
        </T>
      </View>
      {state === 'granted' ? (
        <View style={styles.allowed}>
          <Icon name="check" size={16} color={accent} />
          <T variant="label" color={accent}>
            Allowed
          </T>
        </View>
      ) : (
        <Tap haptic="light" onPress={onAllow} style={[styles.allow, { borderColor: accent }]}>
          <T variant="label" color={accent}>
            {state === 'blocked' ? 'Settings' : 'Allow'}
          </T>
        </Tap>
      )}
    </View>
  );
}

export function PermissionsScreen() {
  const nav = useNavigation<Nav>();
  const insets = useSafeAreaInsets();
  const setSettings = useSettings((s) => s.set);
  const [perms, setPerms] = useState<Perms>({ camera: 'unknown', mic: 'unknown', media: 'unknown' });

  const refresh = useCallback(async () => {
    const p = await check();
    setPerms((prev) => ({
      // Keep "blocked" from an earlier answer; check() can't tell blocked from not asked yet.
      camera: p.camera === 'granted' ? 'granted' : prev.camera === 'blocked' ? 'blocked' : p.camera,
      mic: p.mic === 'granted' ? 'granted' : prev.mic === 'blocked' ? 'blocked' : p.mic,
      media: p.media,
    }));
  }, []);

  useEffect(() => {
    refresh();
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') refresh();
    });
    return () => sub.remove();
  }, [refresh]);

  const request = async (which: 'camera' | 'mic' | 'media') => {
    if (perms[which] === 'blocked') {
      Linking.openSettings();
      return;
    }
    if (which === 'media') {
      const r = await mediaPermission(true);
      setPerms((p) => ({ ...p, media: r === 'granted' || r === 'limited' ? 'granted' : 'blocked' }));
      return;
    }
    const permission = which === 'camera' ? PermissionsAndroid.PERMISSIONS.CAMERA : PermissionsAndroid.PERMISSIONS.RECORD_AUDIO;
    const r = await PermissionsAndroid.request(permission);
    const state: State = r === 'granted' ? 'granted' : r === 'never_ask_again' ? 'blocked' : 'denied';
    setPerms((p) => ({ ...p, [which]: state }));
  };

  const allowAll = async () => {
    const r = await PermissionsAndroid.requestMultiple([PermissionsAndroid.PERMISSIONS.CAMERA, PermissionsAndroid.PERMISSIONS.RECORD_AUDIO]);
    const toState = (v?: string): State => (v === 'granted' ? 'granted' : v === 'never_ask_again' ? 'blocked' : 'denied');
    const media = await mediaPermission(true);
    setPerms({
      camera: toState(r[PermissionsAndroid.PERMISSIONS.CAMERA]),
      mic: toState(r[PermissionsAndroid.PERMISSIONS.RECORD_AUDIO]),
      media: media === 'granted' || media === 'limited' ? 'granted' : 'blocked',
    });
  };

  const ready = perms.camera === 'granted' && (!legacyStorage || perms.media === 'granted');
  const nothingAsked = perms.camera !== 'granted' && perms.mic !== 'granted' && perms.media !== 'granted';

  return (
    <View style={[styles.root, { paddingTop: insets.top + space.xxl, paddingBottom: insets.bottom + space.lg }]}>
      <ScrollView contentContainerStyle={styles.content}>
        <T variant="title">Before the first shot</T>
        <T variant="body" color={palette.ash} style={styles.lead}>
          Camero Plus asks for three permissions. Each one is used only for what it says, and nothing leaves your phone.
        </T>
        <View style={styles.card}>
          <PermissionRow
            icon="photo"
            title="Camera"
            detail="Needed to take photos and videos."
            state={perms.camera}
            onAllow={() => request('camera')}
          />
          <PermissionRow
            icon="volume"
            title="Microphone"
            detail="For sound in your videos. You can leave this off."
            state={perms.mic}
            onAllow={() => request('mic')}
          />
          <PermissionRow
            icon="gallery"
            title="Photos and videos"
            detail={legacyStorage ? 'Needed to save and show your photos on this version of Android.' : 'To show and edit what you shoot in the library.'}
            state={perms.media}
            onAllow={() => request('media')}
            last
          />
        </View>
        {perms.camera === 'blocked' ? (
          <T variant="caption" color={palette.ash} style={styles.blocked}>
            Camera access was turned off. Open Settings, choose Permissions, then allow Camera.
          </T>
        ) : null}
      </ScrollView>
      {ready ? (
        <Button
          label="Open the camera"
          onPress={() => {
            setSettings({ onboarded: true });
            nav.reset({ index: 0, routes: [{ name: 'Camera' }] });
          }}
          style={styles.cta}
        />
      ) : nothingAsked ? (
        <Button label="Allow all" onPress={allowAll} style={styles.cta} />
      ) : (
        <Button label={perms.camera === 'blocked' ? 'Open Android settings' : 'Allow camera'} onPress={() => request('camera')} style={styles.cta} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  content: { paddingHorizontal: space.xl },
  lead: { marginTop: space.md, marginBottom: space.xl, maxWidth: 420 },
  card: { backgroundColor: palette.graphite, borderRadius: radius.lg, paddingHorizontal: space.lg },
  row: { flexDirection: 'row', alignItems: 'center', paddingVertical: space.lg, gap: space.md },
  rule: { borderBottomWidth: hairline, borderBottomColor: palette.rule },
  rowText: { flex: 1 },
  detail: { marginTop: 2 },
  allowed: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  allow: { borderWidth: 1.2, borderRadius: radius.md, paddingHorizontal: 14, paddingVertical: 7 },
  blocked: { marginTop: space.md },
  cta: { marginHorizontal: space.xl },
});
