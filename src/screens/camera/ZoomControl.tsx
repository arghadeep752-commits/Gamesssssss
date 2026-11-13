import React, { useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn, FadeOut } from 'react-native-reanimated';

import { formatZoom } from '../../lib/format';
import type { LensStop } from '../../lib/camera';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Props = {
  stops: LensStop[];
  cameraId?: string;
  zoom: number;
  zoomMin: number;
  zoomMax: number;
  kind: 'optical' | 'digital';
  rotation: number;
  onStop: (stop: LensStop) => void;
  onZoom: (zoom: number) => void;
};

function pillLabel(z: number): string {
  if (z < 1) return z.toFixed(1).replace(/^0/, '');
  return Number.isInteger(z) ? String(z) : z.toFixed(1);
}

/** Lens pills plus an engraved zoom ruler on long press. Optical vs digital is always labelled. */
export function ZoomControl({ stops, cameraId, zoom, zoomMin, zoomMax, kind, rotation, onStop, onZoom }: Props) {
  const accent = useAccent();
  const [ruler, setRuler] = useState(false);
  const hideTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const values = useMemo(() => {
    const out: number[] = [];
    const lo = Math.max(0.1, zoomMin);
    const hi = Math.max(lo * 1.01, zoomMax);
    const n = Math.max(8, Math.ceil(Math.log(hi / lo) / Math.log(1.04)));
    for (let i = 0; i <= n; i++) out.push(Math.round(lo * Math.pow(hi / lo, i / n) * 100) / 100);
    return out;
  }, [zoomMin, zoomMax]);

  useEffect(() => () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
  }, []);

  const scheduleHide = () => {
    if (hideTimer.current) clearTimeout(hideTimer.current);
    hideTimer.current = setTimeout(() => setRuler(false), 2200);
  };

  const sameCamera = stops.filter((s) => s.cameraId === cameraId);
  const active =
    stops.find((s) => s.cameraId === cameraId && s.key.startsWith('cam')) ??
    [...sameCamera].reverse().find((s) => zoom >= s.zoom - 0.02) ??
    sameCamera[0];

  if (ruler) {
    return (
      <Animated.View entering={FadeIn.duration(140)} exiting={FadeOut.duration(140)} style={styles.rulerWrap}>
        <Ruler
          values={values}
          value={zoom}
          onChange={(z) => {
            onZoom(z);
            scheduleHide();
          }}
          onEnd={scheduleHide}
          format={formatZoom}
          majorEvery={10}
          spacing={7}
          caption={kind === 'optical' ? 'Optical' : 'Digital'}
        />
      </Animated.View>
    );
  }

  if (stops.length <= 1 && zoomMax <= 1.01) return <View style={styles.row} />;

  return (
    <View style={styles.row}>
      {stops.map((s) => {
        const isActive = active?.key === s.key;
        return (
          <Tap
            key={s.key}
            haptic="selection"
            onPress={() => onStop(s)}
            onLongPress={() => {
              setRuler(true);
              scheduleHide();
            }}
            delayLongPress={280}
            style={[styles.pill, isActive && styles.pillActive]}
          >
            <View style={{ transform: [{ rotate: `${rotation}deg` }] }}>
              <T variant="readout" color={isActive ? accent : palette.ink}>
                {isActive ? formatZoom(zoom) : pillLabel(s.zoom)}
              </T>
            </View>
          </Tap>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  row: { height: 48, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10 },
  pill: { width: 36, height: 36, borderRadius: 18, alignItems: 'center', justifyContent: 'center', backgroundColor: palette.scrim },
  pillActive: { width: 44, height: 44, borderRadius: 22, backgroundColor: palette.scrimStrong },
  rulerWrap: { height: 64, justifyContent: 'center', paddingHorizontal: 12 },
});
