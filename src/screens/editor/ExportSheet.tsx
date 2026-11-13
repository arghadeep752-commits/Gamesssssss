import React, { useEffect, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Engine, type MediaProbe, type VideoExportOptions } from '../../../modules/camero-engine';
import { formatBytes } from '../../lib/format';
import { gradeJson, isNeutral } from '../../lib/grade';
import { haptic } from '../../lib/haptics';
import { idFromUri } from '../../lib/media';
import { isIdentity, transformJson } from '../../lib/transform';
import { useApp } from '../../state/app';
import { useLibrary } from '../../state/library';
import { hairline, palette, space } from '../../theme/tokens';
import { Button } from '../../ui/Button';
import { Segmented, type SegmentOption } from '../../ui/Segmented';
import { Sheet } from '../../ui/Sheet';
import { T } from '../../ui/T';
import { toast } from '../../ui/Toast';
import type { VideoEdit } from './VideoEditorScreen';

type Resolution = VideoExportOptions['resolution'];
type FpsChoice = 'original' | 'smooth' | '30' | '24';

const TARGETS: { value: Exclude<Resolution, 'original'>; short: number; label: string }[] = [
  { value: '2160', short: 2160, label: '4K' },
  { value: '1440', short: 1440, label: '1440p' },
  { value: '1080', short: 1080, label: '1080p' },
  { value: '720', short: 720, label: '720p' },
];

function nameFor(short: number): string {
  if (short >= 2100) return '4K';
  if (short >= 1400) return '1440p';
  if (short >= 1060) return '1080p';
  if (short >= 700) return '720p';
  return `${short}p`;
}

/** "3840x2160" -> short and long side the encoder accepts. */
function encoderLimit(max?: string): { short: number; long: number } | null {
  const m = max?.match(/(\d+)x(\d+)/);
  if (!m) return null;
  const a = Number(m[1]);
  const b = Number(m[2]);
  return { short: Math.min(a, b), long: Math.max(a, b) };
}

/** Mirrors the engine's automatic bitrate so the size estimate matches what gets written. */
function autoBitrate(w: number, h: number, fps: number, hevc: boolean): number {
  const bpp = hevc ? 0.07 : 0.11;
  return Math.min(100e6, Math.max(2e6, w * h * Math.max(fps, 24) * bpp));
}

type Props = {
  visible: boolean;
  onClose: () => void;
  sourceId: string;
  uri: string;
  edit: VideoEdit;
  probe: MediaProbe | null;
  outputSize: { width: number; height: number } | null;
  outputMs: number;
  accent: string;
  onDone: (id: string | null, uri: string) => void;
};

export function ExportSheet({ visible, onClose, sourceId, uri, edit, probe, outputSize, outputMs, accent, onDone }: Props) {
  const caps = useApp((s) => s.caps);
  const addEdit = useLibrary((s) => s.addEdit);
  const [resolution, setResolution] = useState<Resolution>('original');
  const [fps, setFps] = useState<FpsChoice>('original');
  const [codec, setCodec] = useState<'h264' | 'hevc'>('h264');
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<{ stage: 'analyzing' | 'rendering'; progress: number }>({ stage: 'rendering', progress: 0 });
  const [error, setError] = useState<string | null>(null);

  const w = outputSize?.width ?? probe?.width ?? 0;
  const h = outputSize?.height ?? probe?.height ?? 0;
  const short = Math.min(w, h);
  const long = Math.max(w, h);
  const srcFps = Math.round(probe?.fps ?? 30);
  const hevcAvailable = !!caps?.codecs.hevc;
  const limit = encoderLimit(codec === 'hevc' ? caps?.codecs.hevcMax : caps?.codecs.h264Max);

  const resolutionOptions = useMemo(() => {
    const opts: SegmentOption<Resolution>[] = [{ value: 'original', label: short ? nameFor(short) : 'Original', hint: 'Original' }];
    for (const t of TARGETS) {
      if (!short || Math.abs(t.short - short) <= 8) continue;
      if (t.short < short) {
        opts.push({ value: t.value, label: t.label });
      } else {
        const longOut = Math.round((long * t.short) / short);
        const fits = !limit || (t.short <= limit.short && longOut <= limit.long);
        if (fits) opts.push({ value: t.value, label: t.label, hint: 'Upscaled' });
      }
    }
    return opts;
  }, [short, long, limit]);

  const fpsOptions = useMemo(() => {
    const opts: SegmentOption<FpsChoice>[] = [{ value: 'original', label: `${srcFps} fps`, hint: 'Original' }];
    if (srcFps <= 31) opts.push({ value: 'smooth', label: `${srcFps * 2} fps`, hint: 'Interpolated' });
    if (srcFps > 31) opts.push({ value: '30', label: '30 fps' });
    if (srcFps > 26) opts.push({ value: '24', label: '24 fps' });
    return opts;
  }, [srcFps]);

  // Drop choices that stop applying after an edit (for example a crop that changes the size).
  useEffect(() => {
    if (!resolutionOptions.some((o) => o.value === resolution)) setResolution('original');
  }, [resolutionOptions, resolution]);
  useEffect(() => {
    if (!fpsOptions.some((o) => o.value === fps)) setFps('original');
  }, [fpsOptions, fps]);
  useEffect(() => {
    if (codec === 'hevc' && !hevcAvailable) setCodec('h264');
  }, [codec, hevcAvailable]);
  useEffect(() => {
    if (visible) setError(null);
  }, [visible]);

  const target = TARGETS.find((t) => t.value === resolution);
  const scale = target && short ? target.short / short : 1;
  const outW = Math.round((w * scale) / 2) * 2;
  const outH = Math.round((h * scale) / 2) * 2;
  const outFps = fps === 'smooth' ? srcFps * 2 : fps === 'original' ? srcFps : Math.min(srcFps, Number(fps));
  const keepsAudio = !edit.mute && !!probe?.hasAudio;
  const bitrate = autoBitrate(outW, outH, outFps, codec === 'hevc') + (keepsAudio ? 128e3 : 0);
  const bytes = (bitrate / 8) * (outputMs / 1000);
  const upscaled = scale > 1.01;

  const notes: string[] = [];
  if (upscaled) notes.push('Upscaled frames are resized and sharpened. They look cleaner on big screens but don’t gain real detail.');
  if (fps === 'smooth') notes.push('The extra frames are generated from motion between real ones. Very fast movement can show soft edges.');
  if (edit.stabilize != null) notes.push('Stabilization analyzes the clip first, so the export takes longer.');
  if (probe?.hdr) notes.push('This video is HDR. The export is converted to standard dynamic range.');

  const run = async () => {
    setRunning(true);
    setError(null);
    setProgress({ stage: edit.stabilize != null ? 'analyzing' : 'rendering', progress: 0 });
    const sub = Engine.addListener('onExportProgress', (p) => setProgress(p));
    const options: VideoExportOptions = {
      trimStartMs: edit.trimStartMs,
      trimEndMs: edit.trimEndMs > 0 ? edit.trimEndMs : -1,
      speed: edit.speed,
      mute: edit.mute,
      resolution,
      fps: fps === '30' ? 30 : fps === '24' ? 24 : 0,
      smooth: fps === 'smooth',
      codec,
      bitrate: 0,
      stabilize: edit.stabilize,
    };
    try {
      const res = await Engine.exportVideo(
        uri,
        isNeutral(edit.grade) ? null : gradeJson(edit.grade),
        isIdentity(edit.transform) ? null : transformJson(edit.transform),
        JSON.stringify(options)
      );
      const id = idFromUri(res.uri);
      const recordNotes: string[] = [];
      if (res.upscaled) recordNotes.push(`Upscaled to ${nameFor(Math.min(res.width, res.height))}`);
      if (res.interpolated) recordNotes.push(`${outFps} fps with interpolated frames`);
      if (res.stabilized) recordNotes.push('Software stabilized');
      if (edit.speed !== 1) recordNotes.push(`Speed ${edit.speed}×`);
      if (id) {
        addEdit(id, {
          sourceId,
          sourceUri: uri,
          kind: 'video',
          grade: edit.grade,
          transform: edit.transform,
          createdAt: Date.now(),
          notes: recordNotes,
        });
      }
      haptic.success();
      toast(res.warning ?? 'Saved as a new video. The original is unchanged.');
      onDone(id, res.uri);
    } catch (e) {
      const message = e instanceof Error ? e.message : String(e);
      if (/cancel/i.test(message)) toast('Export cancelled');
      else setError(message || 'The export failed.');
    } finally {
      sub.remove();
      setRunning(false);
    }
  };

  const pct = Math.round(progress.progress * 100);

  return (
    <Sheet visible={visible} onClose={running ? () => {} : onClose} title={running ? undefined : 'Export video'} maxHeightRatio={0.86}>
      {running ? (
        <View style={styles.running}>
          <T variant="heading">{progress.stage === 'analyzing' ? 'Measuring camera shake' : 'Rendering'}</T>
          <View style={styles.barTrack}>
            <View style={[styles.barFill, { width: `${pct}%`, backgroundColor: accent }]} />
          </View>
          <T variant="readout" color={palette.ash}>
            {pct}%
          </T>
          <T variant="caption" color={palette.iron} style={styles.keepOpen}>
            Keep Camero Plus open until the export finishes.
          </T>
          <Button label="Cancel export" kind="secondary" onPress={() => Engine.cancelExport().catch(() => {})} />
        </View>
      ) : (
        <View style={styles.body}>
          <T variant="label" color={palette.ash} style={styles.label}>
            Resolution
          </T>
          <Segmented options={resolutionOptions} value={resolution} onChange={setResolution} />

          <T variant="label" color={palette.ash} style={styles.label}>
            Frame rate
          </T>
          <Segmented options={fpsOptions} value={fps} onChange={setFps} />

          <T variant="label" color={palette.ash} style={styles.label}>
            Format
          </T>
          <Segmented
            options={[
              { value: 'h264' as const, label: 'H.264', hint: 'Plays anywhere' },
              { value: 'hevc' as const, label: 'HEVC', hint: 'Smaller file', disabled: !hevcAvailable },
            ]}
            value={codec}
            onChange={setCodec}
          />

          <View style={styles.summary}>
            <T variant="bodyStrong">
              {outW && outH ? `${outW} × ${outH}, ${outFps} fps` : 'Reading the video'}
            </T>
            <T variant="caption" color={palette.ash}>
              {outW ? `About ${formatBytes(bytes)}${keepsAudio ? '' : ', no sound'}` : ''}
            </T>
            {notes.map((n) => (
              <T key={n} variant="caption" color={palette.iron} style={styles.notesLine}>
                {n}
              </T>
            ))}
          </View>

          {error ? (
            <T variant="caption" color={palette.tally} style={styles.error}>
              {error}
            </T>
          ) : null}
          <Button label={error ? 'Try again' : 'Export'} onPress={run} disabled={!outW} />
        </View>
      )}
    </Sheet>
  );
}

const styles = StyleSheet.create({
  body: { paddingBottom: space.sm },
  label: { marginTop: space.md, marginBottom: space.sm },
  summary: { marginTop: space.lg, marginBottom: space.md, paddingTop: space.md, borderTopWidth: hairline, borderTopColor: palette.rule, gap: 2 },
  notesLine: { marginTop: space.xs },
  error: { marginBottom: space.sm },
  running: { paddingVertical: space.xl, gap: space.md },
  barTrack: { height: 4, borderRadius: 2, backgroundColor: palette.smoke, overflow: 'hidden' },
  barFill: { height: 4, borderRadius: 2 },
  keepOpen: { marginBottom: space.sm },
});
