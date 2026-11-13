import type * as MediaLibrary from 'expo-media-library';
import React, { useEffect, useState } from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';

import { Engine, type MediaProbe } from '../../../modules/camero-engine';
import {
  formatBytes,
  formatDate,
  formatDuration,
  formatMp,
  formatShutterSeconds,
} from '../../lib/format';
import { ADJUSTMENT_MAP, formatAdjustment, type AdjustmentKey } from '../../lib/grade';
import { lookName, useApp } from '../../state/app';
import type { EditRecord } from '../../state/library';
import { hairline, palette, space } from '../../theme/tokens';
import { Sheet } from '../../ui/Sheet';
import { T } from '../../ui/T';

const VIDEO_CODECS: Record<string, string> = {
  'video/avc': 'H.264',
  'video/hevc': 'HEVC (H.265)',
  'video/x-vnd.on2.vp9': 'VP9',
  'video/av01': 'AV1',
  'video/dolby-vision': 'Dolby Vision',
};
const AUDIO_CODECS: Record<string, string> = {
  'audio/mp4a-latm': 'AAC',
  'audio/opus': 'Opus',
  'audio/3gpp': 'AMR',
  'audio/flac': 'FLAC',
};
const IMAGE_TYPES: Record<string, string> = {
  'image/jpeg': 'JPEG',
  'image/png': 'PNG',
  'image/heic': 'HEIF',
  'image/heif': 'HEIF',
  'image/webp': 'WebP',
  'image/x-adobe-dng': 'DNG (RAW)',
};

function resolutionName(w?: number, h?: number): string {
  if (!w || !h) return '';
  const short = Math.min(w, h);
  if (short >= 2100) return '4K';
  if (short >= 1400) return '1440p';
  if (short >= 1060) return '1080p';
  if (short >= 700) return '720p';
  return `${short}p`;
}

/** "/storage/emulated/0/DCIM/Camero Plus/IMG.jpg" -> "DCIM/Camero Plus" */
function folderOf(uri: string): string | null {
  const path = decodeURIComponent(uri.replace(/^file:\/\//, ''));
  const m = path.match(/^\/storage\/[^/]+\/(?:\d+\/)?(.+)\/[^/]+$/);
  return m ? m[1] : null;
}

type Line = { label: string; value: string };

function lines(asset: MediaLibrary.Asset, probe: MediaProbe | null, edit: EditRecord | undefined, looks: ReturnType<typeof useApp.getState>['looks']): Line[][] {
  const file: Line[] = [{ label: 'Name', value: asset.filename }];
  const folder = folderOf(asset.uri);
  if (folder) file.push({ label: 'Folder', value: folder });
  file.push({ label: 'Taken', value: formatDate(asset.creationTime) });
  if (probe) file.push({ label: 'Size', value: formatBytes(probe.bytes) });

  const w = probe?.width ?? asset.width;
  const h = probe?.height ?? asset.height;
  const media: Line[] = [];
  if (asset.mediaType === 'video') {
    media.push({ label: 'Resolution', value: `${w} × ${h}  ${resolutionName(w, h)}`.trim() });
    if (probe?.fps) media.push({ label: 'Frame rate', value: `${Math.round(probe.fps)} fps` });
    if (probe?.captureFps && probe.fps && probe.captureFps > probe.fps * 1.5) {
      media.push({ label: 'Captured at', value: `${Math.round(probe.captureFps)} fps (slow motion)` });
    }
    media.push({ label: 'Length', value: formatDuration((probe?.durationMs ?? asset.duration * 1000) || 0) });
    if (probe?.videoCodec) media.push({ label: 'Video', value: VIDEO_CODECS[probe.videoCodec] ?? probe.videoCodec });
    if (probe?.bitrate) media.push({ label: 'Bitrate', value: `${(probe.bitrate / 1e6).toFixed(1)} Mbps` });
    media.push({ label: 'Audio', value: probe?.hasAudio ? AUDIO_CODECS[probe.audioCodec ?? ''] ?? probe.audioCodec ?? 'Yes' : 'None' });
    if (probe?.hdr) media.push({ label: 'Dynamic range', value: 'HDR' });
  } else {
    media.push({ label: 'Dimensions', value: `${w} × ${h}  ${formatMp(w, h)}`.trim() });
    if (probe?.mime) media.push({ label: 'Format', value: IMAGE_TYPES[probe.mime] ?? probe.mime });
  }

  const camera: Line[] = [];
  if (probe?.make || probe?.model) {
    const make = probe.make ?? '';
    const model = probe.model ?? '';
    camera.push({ label: 'Camera', value: model.toLowerCase().startsWith(make.toLowerCase()) ? model : `${make} ${model}`.trim() });
  }
  if (probe?.iso) camera.push({ label: 'ISO', value: String(probe.iso) });
  if (probe?.exposureTime) camera.push({ label: 'Shutter', value: formatShutterSeconds(probe.exposureTime) });
  if (probe?.fNumber) camera.push({ label: 'Aperture', value: `f/${probe.fNumber.toFixed(1)}` });
  if (probe?.focalLength) {
    const eq = probe.focalLength35 ? `  (${Math.round(probe.focalLength35)} mm equivalent)` : '';
    camera.push({ label: 'Focal length', value: `${probe.focalLength.toFixed(1)} mm${eq}` });
  }
  if (probe?.flash != null && asset.mediaType === 'photo') camera.push({ label: 'Flash', value: probe.flash ? 'Fired' : 'Off' });

  const edited: Line[] = [];
  if (edit) {
    edited.push({ label: 'Edited', value: formatDate(edit.createdAt) });
    if (edit.grade.look !== 'none') edited.push({ label: 'Look', value: `${lookName(looks, edit.grade.look)}  ${edit.grade.intensity}%` });
    const adj = Object.entries(edit.grade.adj).filter(([, v]) => !!v) as [AdjustmentKey, number][];
    if (adj.length) {
      edited.push({
        label: 'Adjustments',
        value: adj.map(([k, v]) => `${ADJUSTMENT_MAP[k].label} ${formatAdjustment(ADJUSTMENT_MAP[k], v)}`).join('\n'),
      });
    }
    for (const note of edit.notes ?? []) edited.push({ label: 'Note', value: note });
    edited.push({ label: 'Original', value: 'Kept unchanged' });
  }
  return [file, media, camera, edited].filter((g) => g.length);
}

type Props = { asset: MediaLibrary.Asset | null; edit?: EditRecord; visible: boolean; onClose: () => void };

export function DetailsSheet({ asset, edit, visible, onClose }: Props) {
  const looks = useApp((s) => s.looks);
  const [probe, setProbe] = useState<MediaProbe | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!visible || !asset) return;
    let alive = true;
    setLoading(true);
    setProbe(null);
    Engine.probeMedia(asset.uri)
      .then((p) => alive && setProbe(p))
      .catch(() => {})
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [asset, visible]);

  return (
    <Sheet visible={visible} onClose={onClose} title="Details" maxHeightRatio={0.78}>
      {asset ? (
        <View>
          {lines(asset, probe, edit, looks).map((group, gi) => (
            <View key={gi} style={[styles.group, gi > 0 && styles.groupRule]}>
              {group.map((l) => (
                <View key={l.label + l.value} style={styles.line}>
                  <T variant="label" color={palette.ash} style={styles.label}>
                    {l.label}
                  </T>
                  <T variant="body" style={styles.value} selectable>
                    {l.value}
                  </T>
                </View>
              ))}
            </View>
          ))}
          {loading ? <ActivityIndicator color={palette.ash} style={styles.loading} /> : null}
        </View>
      ) : null}
    </Sheet>
  );
}

const styles = StyleSheet.create({
  group: { paddingVertical: space.sm },
  groupRule: { borderTopWidth: hairline, borderTopColor: palette.rule },
  line: { flexDirection: 'row', paddingVertical: 6, gap: space.md },
  label: { width: 104, paddingTop: 2 },
  value: { flex: 1 },
  loading: { marginVertical: space.md },
});
