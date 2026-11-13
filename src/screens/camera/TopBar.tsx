import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { AspectRatio, CameraMode, FlashMode } from '../../../modules/camero-engine';
import { formatClock } from '../../lib/format';
import { isVideoMode } from '../../lib/camera';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { Icon, type IconName } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Props = {
  mode: CameraMode;
  flash: FlashMode;
  torch: boolean;
  hasFlash: boolean;
  timer: 0 | 3 | 10;
  aspect: AspectRatio;
  primary: string;
  secondary?: string;
  stabilization?: string;
  lookActive: boolean;
  recording: { active: boolean; paused: boolean; durationMs: number; clipMs?: number };
  rotation: number;
  overlay: boolean;
  onFlash: () => void;
  onTorch: () => void;
  onTimer: () => void;
  onAspect: () => void;
  onReadout: () => void;
  onLook: () => void;
  onLookHold: (on: boolean) => void;
  onSettings: () => void;
};

function Btn({ icon, onPress, active, rotation, disabled, label, accent }: {
  icon: IconName;
  onPress: () => void;
  active?: boolean;
  rotation: number;
  disabled?: boolean;
  label?: string;
  accent: string;
}) {
  return (
    <Tap onPress={onPress} disabled={disabled} haptic="selection" style={styles.btn}>
      <View style={{ transform: [{ rotate: `${rotation}deg` }], alignItems: 'center' }}>
        <Icon name={icon} size={22} color={active ? accent : palette.ink} />
        {label ? (
          <T variant="caption" color={active ? accent : palette.ink} style={styles.btnLabel}>
            {label}
          </T>
        ) : null}
      </View>
    </Tap>
  );
}

export function TopBar(p: Props) {
  const accent = useAccent();
  const insets = useSafeAreaInsets();
  const video = isVideoMode(p.mode);
  const rec = p.recording.active;
  const flashIcon: IconName = p.flash === 'on' ? 'flash' : p.flash === 'auto' ? 'flash-auto' : 'flash-off';
  return (
    <View style={[styles.root, { paddingTop: insets.top, backgroundColor: p.overlay ? palette.scrim : palette.black }]}>
      <View style={styles.bar}>
        <View style={styles.side}>
          {video ? (
            <Btn icon="torch" onPress={p.onTorch} active={p.torch} rotation={p.rotation} disabled={!p.hasFlash} accent={accent} />
          ) : (
            <Btn icon={flashIcon} onPress={p.onFlash} active={p.flash !== 'off'} rotation={p.rotation} disabled={!p.hasFlash || rec} accent={accent} />
          )}
          {video ? (
            p.stabilization ? (
              <Btn
                icon="stabilize"
                onPress={p.onReadout}
                active={p.stabilization !== 'Off'}
                label={p.stabilization === 'Off' ? undefined : p.stabilization}
                rotation={p.rotation}
                disabled={rec}
                accent={accent}
              />
            ) : null
          ) : (
            <>
              <Btn icon="timer" onPress={p.onTimer} active={p.timer > 0} label={p.timer ? `${p.timer}s` : undefined} rotation={p.rotation} accent={accent} />
              <Tap onPress={p.onAspect} haptic="selection" style={styles.textBtn}>
                <View style={{ transform: [{ rotate: `${p.rotation}deg` }] }}>
                  <T variant="readout" color={palette.ink}>
                    {p.aspect}
                  </T>
                </View>
              </Tap>
            </>
          )}
        </View>

        <View style={styles.center}>
          {rec ? (
            <View style={styles.recBadge}>
              <View style={[styles.recDot, p.recording.paused && styles.recDotPaused]} />
              <T variant="readoutLarge" color={palette.ink}>
                {formatClock(p.recording.durationMs)}
              </T>
              {p.recording.clipMs !== undefined ? (
                <T variant="readout" color={palette.ash}>
                  {formatClock(p.recording.clipMs)}
                </T>
              ) : null}
            </View>
          ) : (
            <Tap onPress={p.onReadout} haptic="selection" style={styles.readout}>
              <T variant="readout" color={palette.ink}>
                {p.primary}
              </T>
              {p.secondary ? (
                <T variant="readout" color={palette.ash}>
                  {p.secondary}
                </T>
              ) : null}
            </Tap>
          )}
        </View>

        <View style={[styles.side, styles.right]}>
          <Tap
            onPress={p.onLook}
            onLongPress={() => p.onLookHold(true)}
            onPressOut={() => p.onLookHold(false)}
            delayLongPress={220}
            haptic="selection"
            style={styles.btn}
          >
            <View style={{ transform: [{ rotate: `${p.rotation}deg` }] }}>
              <Icon name="look" size={22} color={p.lookActive ? accent : palette.ink} />
            </View>
          </Tap>
          <Btn icon="settings" onPress={p.onSettings} rotation={p.rotation} disabled={rec} accent={accent} />
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { position: 'absolute', top: 0, left: 0, right: 0, zIndex: 10 },
  bar: { height: 52, flexDirection: 'row', alignItems: 'center', paddingHorizontal: 6 },
  side: { flexDirection: 'row', alignItems: 'center', minWidth: 112 },
  right: { justifyContent: 'flex-end' },
  center: { flex: 1, alignItems: 'center' },
  btn: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  btnLabel: { position: 'absolute', top: 17, left: 15, fontSize: 9, lineHeight: 11 },
  textBtn: { height: 44, minWidth: 40, paddingHorizontal: 6, alignItems: 'center', justifyContent: 'center' },
  readout: { flexDirection: 'row', alignItems: 'center', gap: 6, paddingHorizontal: 10, height: 44 },
  recBadge: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  recDot: { width: 8, height: 8, borderRadius: 4, backgroundColor: palette.tally },
  recDotPaused: { backgroundColor: palette.ash },
});
