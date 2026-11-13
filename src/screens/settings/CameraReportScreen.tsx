import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import type { CameraCapability, Capabilities } from '../../../modules/camero-engine';
import { backCameras, macroCamera, mainBack } from '../../lib/camera';
import { formatMp, formatShutterNs, qualityLabel } from '../../lib/format';
import { useApp } from '../../state/app';
import { hairline, palette, radius, space } from '../../theme/tokens';
import { Header } from '../../ui/Header';
import { Icon } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { toast } from '../../ui/Toast';

const LENS_NAMES: Record<CameraCapability['lens'], string> = {
  wide: 'Main',
  ultrawide: 'Ultra-wide',
  tele: 'Telephoto',
  macro: 'Macro',
  front: 'Front',
};

type Line = { label: string; value: string };

function yes(v: boolean) {
  return v ? 'Yes' : 'No';
}

function cameraLines(c: CameraCapability): Line[] {
  const lines: Line[] = [];
  const lens: string[] = [];
  if (c.eqFocalLength) lens.push(`${Math.round(c.eqFocalLength)} mm equivalent`);
  if (c.aperture) lens.push(`f/${c.aperture.toFixed(1)}`);
  if (lens.length) lines.push({ label: 'Lens', value: lens.join(', ') });
  lines.push({ label: 'Focus', value: c.fixedFocus ? 'Fixed focus' : c.minFocusCm ? `Down to about ${Math.round(c.minFocusCm)} cm` : 'Autofocus' });
  const stops = c.opticalStops.length > 1 ? `, lenses at ${c.opticalStops.map((z) => `${Number(z.toFixed(1))}×`).join(', ')}` : '';
  lines.push({ label: 'Zoom', value: `${Number(c.zoomMin.toFixed(1))}× to ${Number(c.zoomMax.toFixed(1))}×${stops}` });
  if (c.photoMax) lines.push({ label: 'Photo', value: formatMp(c.photoMax.width, c.photoMax.height) + (c.photoHighRes ? `, high-res ${formatMp(c.photoHighRes.width, c.photoHighRes.height)}` : '') });
  lines.push({ label: 'RAW (DNG)', value: yes(c.raw) });
  lines.push({ label: 'Ultra HDR', value: yes(c.ultraHdr) });
  if (c.video.length) {
    lines.push({
      label: 'Video',
      value: c.video.map((m) => `${qualityLabel(m.quality)} at ${m.fps.join(', ')} fps`).join('\n'),
    });
  }
  lines.push({
    label: 'Slow motion',
    value: c.highSpeed?.fps.length ? `${c.highSpeed.fps.join(', ')} fps (${c.highSpeed.qualities.map(qualityLabel).join(', ')})` : 'Not offered',
  });
  lines.push({ label: 'HDR video', value: c.hdrVideo ? `Yes, ${c.hdrQualities.map(qualityLabel).join(', ')}` : 'No' });
  lines.push({ label: 'Optical stabilization', value: yes(c.ois) });
  lines.push({ label: 'Electronic stabilization', value: yes(c.videoStabilization || c.previewStabilization) });
  if (c.manualSensor && c.isoMin && c.isoMax) {
    lines.push({ label: 'ISO', value: `${c.isoMin} to ${c.isoMax}` });
    lines.push({ label: 'Shutter', value: `${formatShutterNs(c.shutterMinNs)} to ${formatShutterNs(c.shutterMaxNs)}` });
  } else {
    lines.push({ label: 'Manual exposure', value: 'Not offered' });
  }
  lines.push({ label: 'Manual focus', value: yes(c.manualFocus) });
  if (c.extensions.length) lines.push({ label: 'Phone processing', value: c.extensions.map((e) => (e === 'bokeh' ? 'Portrait' : e === 'hdr' ? 'HDR' : e === 'night' ? 'Night' : 'Auto')).join(', ') });
  lines.push({ label: 'Camera2 level', value: c.hardwareLevel });
  return lines;
}

function softwareNotes(caps: Capabilities): string[] {
  const back = backCameras(caps);
  const main = mainBack(caps);
  const notes: string[] = [];
  if (!back.some((c) => c.ois || c.videoStabilization || c.previewStabilization)) {
    notes.push('No optical or electronic stabilization was found. Camero Plus steadies video in software, live and in the editor, with a small crop.');
  } else if (!back.some((c) => c.ois)) {
    notes.push('There’s no optical stabilizer. Electronic or software stabilization is used instead.');
  }
  if (!macroCamera(caps)) notes.push('There’s no macro lens. Macro mode uses the main camera at its closest focus with a 2× crop, peaking and manual focus.');
  if (main && !main.video.some((m) => m.quality === 'UHD')) notes.push('The camera doesn’t record 4K. The video editor can export upscaled 4K, labelled as upscaled.');
  if (main && !main.video.some((m) => m.fps.includes(60))) notes.push('The camera doesn’t record 60 fps. The video editor can export Smooth 60 with interpolated frames.');
  if (!back.some((c) => c.raw)) notes.push('No camera offers RAW sensor data, so RAW capture isn’t shown.');
  return notes;
}

function Block({ title, lines, note }: { title: string; lines: Line[]; note?: string }) {
  return (
    <View style={styles.block}>
      <T variant="heading" style={styles.blockTitle}>
        {title}
      </T>
      {note ? (
        <T variant="caption" color={palette.iron} style={styles.blockNote}>
          {note}
        </T>
      ) : null}
      <View style={styles.card}>
        {lines.map((l, i) => (
          <View key={l.label} style={[styles.line, i < lines.length - 1 && styles.rule]}>
            <T variant="label" color={palette.ash} style={styles.label}>
              {l.label}
            </T>
            <T variant="body" style={styles.value} selectable>
              {l.value}
            </T>
          </View>
        ))}
      </View>
    </View>
  );
}

export function CameraReportScreen() {
  const insets = useSafeAreaInsets();
  const caps = useApp((s) => s.caps);
  const loadCapabilities = useApp((s) => s.loadCapabilities);
  const [busy, setBusy] = useState(false);

  const refresh = async () => {
    setBusy(true);
    await loadCapabilities(true);
    setBusy(false);
    toast('Cameras checked again');
  };

  const d = caps?.device;
  return (
    <View style={styles.root}>
      <Header
        title="Camera report"
        large
        right={
          <Tap onPress={refresh} disabled={busy} haptic="selection" style={styles.refresh} accessibilityLabel="Check the cameras again">
            <Icon name="rotate" size={22} />
          </Tap>
        }
      />
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        <T variant="body" color={palette.ash} style={styles.intro}>
          Read from the phone when Camero Plus started. Controls only appear in the app when a camera supports them.
        </T>
        {caps && d ? (
          <>
            <Block
              title={`${d.manufacturer.charAt(0).toUpperCase()}${d.manufacturer.slice(1)} ${d.model}`}
              lines={[
                { label: 'Android', value: `${d.release} (API ${d.sdk})` },
                { label: 'Memory', value: `${(d.totalRamMb / 1024).toFixed(1)} GB` },
                ...(d.gpu ? [{ label: 'GPU', value: d.gpu }] : []),
                { label: 'Gyroscope', value: yes(d.gyroscope) },
                { label: 'H.264 encoder', value: caps.codecs.h264Max ? `Up to ${caps.codecs.h264Max.replace('x', ' × ')}` : 'Not found' },
                { label: 'HEVC encoder', value: caps.codecs.hevcMax ? `Up to ${caps.codecs.hevcMax.replace('x', ' × ')}` : 'Not found' },
              ]}
            />
            {softwareNotes(caps).length ? (
              <View style={styles.block}>
                <T variant="heading" style={styles.blockTitle}>
                  Done in software here
                </T>
                <View style={[styles.card, styles.notes]}>
                  {softwareNotes(caps).map((n) => (
                    <T key={n} variant="body" color={palette.ink}>
                      {n}
                    </T>
                  ))}
                </View>
              </View>
            ) : null}
            {caps.cameras.map((c) => (
              <Block
                key={c.id}
                title={`${c.facing === 'front' ? 'Front' : LENS_NAMES[c.lens]} camera`}
                note={`Camera ${c.id}${c.logicalMultiCamera ? ', combines several lenses' : ''}`}
                lines={cameraLines(c)}
              />
            ))}
          </>
        ) : (
          <T variant="body" color={palette.ash} style={styles.intro}>
            The cameras haven’t been read yet. Tap the refresh button above.
          </T>
        )}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  refresh: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  intro: { paddingHorizontal: space.lg, marginBottom: space.md },
  block: { marginTop: space.xl, paddingHorizontal: space.lg },
  blockTitle: { marginBottom: 2 },
  blockNote: { marginBottom: space.sm },
  card: { marginTop: space.sm, backgroundColor: palette.graphite, borderRadius: radius.md, paddingHorizontal: space.md },
  notes: { paddingVertical: space.md, gap: space.md },
  line: { flexDirection: 'row', paddingVertical: 10, gap: space.md },
  rule: { borderBottomWidth: hairline, borderBottomColor: palette.rule },
  label: { width: 128, paddingTop: 2 },
  value: { flex: 1 },
});
