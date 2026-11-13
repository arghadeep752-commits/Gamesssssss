import React, { useMemo, useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import type { CameraCapability, MetadataEvent, ReadyEvent } from '../../../modules/camero-engine';
import { AWB_LABELS, AWB_ORDER, ISO_STOPS, SHUTTER_STOPS } from '../../lib/camera';
import { formatFocus, formatShutterNs, formatShutterSeconds, signed } from '../../lib/format';
import type { ManualUi } from '../../state/camera';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Dial = 'iso' | 'shutter' | 'wb' | 'focus' | 'ev';

type Props = {
  mode: 'pro' | 'macro';
  cam?: CameraCapability;
  ready: ReadyEvent | null;
  manual: ManualUi;
  meta: MetadataEvent;
  evIndex: number;
  onManual: (patch: Partial<ManualUi>) => void;
  onEv: (index: number) => void;
};

/** Pro controls: tap a readout, then set it on the ruler. "Auto" hands control back to the camera. */
export function ProDials({ mode, cam, ready, manual, meta, evIndex, onManual, onEv }: Props) {
  const accent = useAccent();
  const [dial, setDial] = useState<Dial | null>(mode === 'macro' ? 'focus' : null);
  const manualSensor = !!cam?.manualSensor;
  const manualFocus = !!cam?.manualFocus;

  const isoStops = useMemo(() => {
    const lo = cam?.isoMin ?? 100;
    const hi = cam?.isoMax ?? 3200;
    const list = ISO_STOPS.filter((v) => v >= lo && v <= hi);
    return list.length ? list : [lo, hi];
  }, [cam]);

  const shutterStops = useMemo(() => {
    const lo = (cam?.shutterMinNs ?? 125000) / 1e9;
    const hi = Math.min(1, (cam?.shutterMaxNs ?? 1e9) / 1e9);
    const list = SHUTTER_STOPS.filter((v) => v >= lo * 0.98 && v <= hi * 1.02);
    return list.length ? list : [1 / 125];
  }, [cam]);

  const focusStops = useMemo(() => {
    const max = cam?.minFocusDiopters ?? 0;
    if (max <= 0) return [0];
    const n = 48;
    return Array.from({ length: n + 1 }, (_, i) => Math.round(max * Math.pow(i / n, 1.6) * 1000) / 1000);
  }, [cam]);

  const awbModes = AWB_ORDER.filter((m) => m === 'auto' || cam?.awbModes.includes(m as never));
  const evStep = ready?.exposureStep ?? 1 / 3;
  const evMin = ready?.exposureMin ?? 0;
  const evMax = ready?.exposureMax ?? 0;
  const manualExposure = manual.iso != null || manual.shutterS != null;

  const isoLabel = manual.iso != null ? `ISO ${manual.iso}` : meta.iso ? `ISO ${meta.iso}` : 'ISO';
  const shutterLabel = manual.shutterS != null ? formatShutterSeconds(manual.shutterS) : formatShutterNs(meta.exposureNs);
  const wb = AWB_LABELS[manual.awb] ?? AWB_LABELS.auto;
  const wbLabel = wb.kelvin ? `${wb.kelvin}K` : 'AWB';
  const focusLabel = manual.focus != null ? formatFocus(manual.focus) : 'AF';
  const evLabel = `EV ${signed(evIndex * evStep)}`;

  const dials: { key: Dial; label: string; manual: boolean; enabled: boolean }[] =
    mode === 'macro'
      ? [
          { key: 'focus', label: focusLabel, manual: manual.focus != null, enabled: manualFocus },
          { key: 'ev', label: evLabel, manual: evIndex !== 0, enabled: !!ready?.exposureSupported },
        ]
      : [
          { key: 'iso', label: isoLabel, manual: manual.iso != null, enabled: manualSensor },
          { key: 'shutter', label: shutterLabel, manual: manual.shutterS != null, enabled: manualSensor },
          { key: 'wb', label: wbLabel, manual: manual.awb !== 'auto', enabled: awbModes.length > 1 },
          { key: 'focus', label: focusLabel, manual: manual.focus != null, enabled: manualFocus },
          { key: 'ev', label: evLabel, manual: evIndex !== 0, enabled: !!ready?.exposureSupported && !manualExposure },
        ];

  const autoFor: Record<Dial, () => void> = {
    iso: () => onManual({ iso: null }),
    shutter: () => onManual({ shutterS: null }),
    wb: () => onManual({ awb: 'auto' }),
    focus: () => onManual({ focus: null }),
    ev: () => onEv(0),
  };

  const isAuto = (d: Dial) =>
    d === 'iso' ? manual.iso == null : d === 'shutter' ? manual.shutterS == null : d === 'wb' ? manual.awb === 'auto' : d === 'focus' ? manual.focus == null : evIndex === 0;

  let note: string | null = null;
  if (dial === 'iso' || dial === 'shutter') {
    if (!manualSensor) note = 'This camera doesn’t allow manual ISO or shutter. The live values are shown.';
  }
  if (dial === 'focus' && !manualFocus) {
    note = cam?.fixedFocus ? 'This lens has fixed focus.' : 'This camera doesn’t allow manual focus.';
  }

  return (
    <View style={styles.root}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
        {dials.map((d) => {
          const selected = dial === d.key;
          return (
            <Tap key={d.key} haptic="selection" pressedOpacity={0.7} onPress={() => setDial(selected ? null : d.key)} style={styles.dial}>
              <T variant="readout" color={selected ? accent : d.manual ? palette.ink : palette.ash}>
                {d.label}
              </T>
              <View style={[styles.mark, { backgroundColor: selected ? accent : d.manual ? palette.ink : 'transparent' }]} />
            </Tap>
          );
        })}
      </ScrollView>
      {dial ? (
        <View style={styles.panel}>
          {note ? (
            <T variant="caption" color={palette.ash} align="center" style={styles.note}>
              {note}
            </T>
          ) : (
            <View style={styles.rulerRow}>
              <Tap onPress={autoFor[dial]} haptic="selection" style={[styles.auto, isAuto(dial) && { borderColor: accent }]}>
                <T variant="label" color={isAuto(dial) ? accent : palette.ash}>
                  Auto
                </T>
              </Tap>
              <View style={styles.ruler}>
                {dial === 'iso' ? (
                  <Ruler
                    values={isoStops}
                    value={manual.iso ?? meta.iso ?? isoStops[Math.floor(isoStops.length / 3)]}
                    onChange={(v) => onManual({ iso: v })}
                    format={(v) => `ISO ${v}`}
                    majorEvery={3}
                    spacing={14}
                  />
                ) : null}
                {dial === 'shutter' ? (
                  <Ruler
                    values={shutterStops}
                    value={manual.shutterS ?? (meta.exposureNs ? meta.exposureNs / 1e9 : 1 / 60)}
                    onChange={(v) => onManual({ shutterS: v })}
                    format={formatShutterSeconds}
                    majorEvery={3}
                    spacing={14}
                  />
                ) : null}
                {dial === 'wb' ? (
                  <Ruler
                    values={awbModes.map((_, i) => i)}
                    value={Math.max(0, awbModes.indexOf(manual.awb))}
                    onChange={(i) => onManual({ awb: awbModes[i] as ManualUi['awb'] })}
                    format={(i) => {
                      const info = AWB_LABELS[awbModes[i]] ?? AWB_LABELS.auto;
                      return info.kelvin ? `${info.label}  ${info.kelvin}K` : info.label;
                    }}
                    majorEvery={1}
                    spacing={34}
                  />
                ) : null}
                {dial === 'focus' ? (
                  <Ruler
                    values={focusStops}
                    value={manual.focus ?? meta.focusDiopters ?? 0}
                    onChange={(v) => onManual({ focus: v })}
                    format={formatFocus}
                    majorEvery={8}
                    spacing={7}
                    caption={cam?.minFocusCm ? `closest ${Math.round(cam.minFocusCm)} cm` : undefined}
                  />
                ) : null}
                {dial === 'ev' ? (
                  <Ruler
                    min={evMin}
                    max={evMax}
                    step={1}
                    value={evIndex}
                    reference={0}
                    onChange={onEv}
                    format={(i) => signed(i * evStep)}
                    majorEvery={Math.max(1, Math.round(1 / evStep))}
                    spacing={10}
                  />
                ) : null}
              </View>
            </View>
          )}
        </View>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  root: { paddingTop: 2 },
  row: { paddingHorizontal: 10, gap: 2, alignItems: 'center' },
  dial: { paddingHorizontal: 10, paddingVertical: 6, alignItems: 'center' },
  mark: { width: 4, height: 4, borderRadius: 2, marginTop: 5 },
  panel: { paddingTop: 4, paddingBottom: 2 },
  note: { paddingHorizontal: 24, paddingVertical: 14 },
  rulerRow: { flexDirection: 'row', alignItems: 'center', paddingLeft: 10 },
  auto: { paddingHorizontal: 10, paddingVertical: 7, borderRadius: 8, borderWidth: 1.2, borderColor: palette.rule, marginTop: 18 },
  ruler: { flex: 1 },
});
