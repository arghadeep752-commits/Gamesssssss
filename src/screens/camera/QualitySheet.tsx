import React, { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';

import { Engine, type CameraCapability, type CameraMode, type StabilizationMode, type VideoQuality } from '../../../modules/camero-engine';
import { estimateBitrate, fpsFor, isVideoMode, qualitiesFor } from '../../lib/camera';
import { formatBytes, formatMp, qualityLabel } from '../../lib/format';
import { useSettings, type GridType } from '../../state/settings';
import { palette, space } from '../../theme/tokens';
import { Segmented } from '../../ui/Segmented';
import { Sheet } from '../../ui/Sheet';
import { T } from '../../ui/T';
import { Toggle } from '../../ui/Toggle';

type Props = {
  visible: boolean;
  onClose: () => void;
  mode: CameraMode;
  cam?: CameraCapability;
};

function Label({ title, note }: { title: string; note?: string }) {
  return (
    <View style={styles.label}>
      <T variant="label" color={palette.ash}>
        {title}
      </T>
      {note ? (
        <T variant="caption" color={palette.iron} style={styles.note}>
          {note}
        </T>
      ) : null}
    </View>
  );
}

function SwitchLine({ title, note, value, onChange }: { title: string; note?: string; value: boolean; onChange: (v: boolean) => void }) {
  return (
    <View style={styles.switchLine}>
      <View style={styles.switchText}>
        <T variant="body">{title}</T>
        {note ? (
          <T variant="caption" color={palette.ash} style={styles.note}>
            {note}
          </T>
        ) : null}
      </View>
      <Toggle value={value} onChange={onChange} />
    </View>
  );
}

const STAB_NOTES: Record<StabilizationMode, string> = {
  off: 'No stabilization. The full frame is recorded.',
  standard: 'Uses the optical stabilizer in the lens.',
  enhanced: 'Uses the phone’s electronic stabilization. The frame is cropped slightly.',
  software: 'Camero Plus measures shake from the image and steadies it live. Works on any phone; crops about 10%.',
};

export function QualitySheet({ visible, onClose, mode, cam }: Props) {
  const s = useSettings();
  const [free, setFree] = useState<number | null>(null);

  useEffect(() => {
    if (!visible) return;
    Engine.getStorageInfo()
      .then((i) => setFree(i.freeBytes))
      .catch(() => setFree(null));
  }, [visible]);

  const video = isVideoMode(mode);
  const qualities = qualitiesFor(cam);
  const quality: VideoQuality = qualities.includes(s.video.quality) ? s.video.quality : (qualities.includes('FHD') ? 'FHD' : qualities[0] ?? 'FHD');
  const fpsOptions = fpsFor(cam, quality);
  const fps = fpsOptions.includes(s.video.fps) ? s.video.fps : fpsOptions.includes(30) ? 30 : fpsOptions[0];

  const stabOptions: { value: StabilizationMode; label: string }[] = [{ value: 'off', label: 'Off' }];
  if (cam?.ois) stabOptions.push({ value: 'standard', label: 'Optical' });
  if (cam?.videoStabilization || cam?.previewStabilization) stabOptions.push({ value: 'enhanced', label: 'Electronic' });
  stabOptions.push({ value: 'software', label: 'Software' });
  const stab = stabOptions.some((o) => o.value === s.video.stabilization) ? s.video.stabilization : 'software';

  let storageLine = '';
  if (free != null) {
    if (video && mode === 'video') {
      const seconds = free / (estimateBitrate(quality, fps, s.video.bitrate) / 8);
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      storageLine = `${formatBytes(free)} free. About ${h ? `${h} h ` : ''}${m} min of ${qualityLabel(quality)} at ${fps} fps.`;
    } else if (!video) {
      const mp = cam?.photoMax?.mp ?? 12;
      const per = mp * 0.35 * 1024 * 1024 * (s.photo.format === 'raw+jpeg' ? 4 : 1);
      storageLine = `${formatBytes(free)} free. Room for about ${Math.floor(free / per).toLocaleString()} photos.`;
    } else {
      storageLine = `${formatBytes(free)} free.`;
    }
  }

  return (
    <Sheet visible={visible} onClose={onClose} title={video ? 'Video' : 'Photo'}>
      {!video ? (
        <>
          <Label title="Resolution" note={s.photo.resolution === 'highres' ? 'High-resolution mode can take longer to save.' : undefined} />
          <Segmented
            value={s.photo.resolution}
            onChange={(v) => s.setPhoto({ resolution: v })}
            options={[
              { value: 'max', label: 'Full', hint: cam?.photoMax ? formatMp(cam.photoMax.width, cam.photoMax.height) : undefined },
              { value: 'standard', label: 'Standard', hint: 'about 8 MP' },
              ...(cam?.photoHighRes
                ? [{ value: 'highres' as const, label: 'High-res', hint: formatMp(cam.photoHighRes.width, cam.photoHighRes.height) }]
                : []),
            ]}
          />
          <Label
            title="Format"
            note={
              s.photo.format === 'ultrahdr'
                ? 'Ultra HDR keeps the HDR gain map, so looks are not applied to these photos.'
                : s.photo.format === 'raw+jpeg'
                  ? 'Saves an unprocessed DNG next to the JPEG.'
                  : undefined
            }
          />
          <Segmented
            value={s.photo.format}
            onChange={(v) => s.setPhoto({ format: v })}
            options={[
              { value: 'jpeg', label: 'JPEG' },
              ...(cam?.raw ? [{ value: 'raw+jpeg' as const, label: 'RAW + JPEG' }] : []),
              ...(cam?.ultraHdr ? [{ value: 'ultrahdr' as const, label: 'Ultra HDR' }] : []),
            ]}
          />
          {!cam?.raw ? (
            <T variant="caption" color={palette.iron} style={styles.note}>
              This camera doesn’t provide RAW sensor data.
            </T>
          ) : null}
          <Label title="JPEG quality" />
          <Segmented
            value={s.photo.jpegQuality >= 99 ? 100 : s.photo.jpegQuality >= 90 ? 95 : 85}
            onChange={(v) => s.setPhoto({ jpegQuality: v })}
            options={[
              { value: 85, label: 'Standard' },
              { value: 95, label: 'High' },
              { value: 100, label: 'Maximum' },
            ]}
          />
          {mode === 'photo' && cam?.extensions.some((e) => e !== 'bokeh') ? (
            <>
              <Label title="Processing" note="Uses the phone maker’s HDR or night processing." />
              <Segmented
                value={s.photo.extension}
                onChange={(v) => s.setPhoto({ extension: v })}
                options={[
                  { value: 'none', label: 'Off' },
                  ...(cam.extensions.includes('hdr') ? [{ value: 'hdr' as const, label: 'HDR' }] : []),
                  ...(cam.extensions.includes('night') ? [{ value: 'night' as const, label: 'Night' }] : []),
                  ...(cam.extensions.includes('auto') ? [{ value: 'auto' as const, label: 'Auto' }] : []),
                ]}
              />
            </>
          ) : null}
          <SwitchLine
            title="Keep original"
            note="When a look is applied, also save the untouched photo in an Originals folder."
            value={s.photo.keepOriginal}
            onChange={(v) => s.setPhoto({ keepOriginal: v })}
          />
        </>
      ) : null}

      {mode === 'video' ? (
        <>
          <Label title="Resolution" note={qualities.length === 1 ? 'This camera records one resolution.' : undefined} />
          <Segmented
            value={quality}
            onChange={(v) => s.setVideo({ quality: v })}
            options={qualities.map((q) => ({ value: q, label: qualityLabel(q) }))}
          />
          {!qualities.includes('UHD') ? (
            <T variant="caption" color={palette.iron} style={styles.note}>
              This camera doesn’t record 4K. You can export upscaled 4K from the video editor.
            </T>
          ) : null}
          <Label title="Frame rate" />
          <Segmented value={fps} onChange={(v) => s.setVideo({ fps: v })} options={fpsOptions.map((f) => ({ value: f, label: `${f} fps` }))} />
          {!fpsOptions.includes(60) ? (
            <T variant="caption" color={palette.iron} style={styles.note}>
              60 fps isn’t available at this resolution. Smooth 60 is available when exporting from the editor.
            </T>
          ) : null}
          <Label title="Stabilization" note={STAB_NOTES[stab]} />
          <Segmented value={stab} onChange={(v) => s.setVideo({ stabilization: v })} options={stabOptions} />
          {cam?.hdrVideo && cam.hdrQualities.includes(quality) ? (
            <SwitchLine
              title="HDR video"
              note="10-bit HLG in HEVC. Looks and software stabilization are paused in HDR."
              value={s.video.hdr}
              onChange={(v) => s.setVideo({ hdr: v })}
            />
          ) : null}
          <Label title="Bitrate" />
          <Segmented
            value={s.video.bitrate}
            onChange={(v) => s.setVideo({ bitrate: v })}
            options={[
              { value: 'auto', label: 'Auto' },
              { value: 'high', label: 'High' },
              { value: 'max', label: 'Maximum' },
            ]}
          />
          <SwitchLine title="Record sound" value={s.video.audio} onChange={(v) => s.setVideo({ audio: v })} />
          <SwitchLine
            title="Record without look"
            note="The look stays in the viewfinder but the file is recorded clean, for grading later."
            value={s.video.clean}
            onChange={(v) => s.setVideo({ clean: v })}
          />
        </>
      ) : null}

      {mode === 'slowmo' && cam?.highSpeed ? (
        <>
          <Label title="Frame rate" note="Recorded at high speed and played back slowed down." />
          <Segmented
            value={cam.highSpeed.fps.includes(s.video.slowFps) ? s.video.slowFps : cam.highSpeed.fps[0]}
            onChange={(v) => s.setVideo({ slowFps: v })}
            options={cam.highSpeed.fps.map((f) => ({ value: f, label: `${f} fps` }))}
          />
        </>
      ) : null}

      {mode === 'timelapse' ? (
        <>
          <Label title="Interval" note="One frame is captured each interval and played back at 30 fps." />
          <Segmented
            value={s.timelapseIntervalMs}
            onChange={(v) => s.set({ timelapseIntervalMs: v })}
            options={[
              { value: 500, label: '0.5 s', hint: '15×' },
              { value: 1000, label: '1 s', hint: '30×' },
              { value: 2000, label: '2 s', hint: '60×' },
              { value: 5000, label: '5 s', hint: '150×' },
              { value: 10000, label: '10 s', hint: '300×' },
            ]}
          />
        </>
      ) : null}

      <View style={styles.divider} />
      <Label title="Viewfinder" />
      <Segmented<GridType>
        value={s.grid}
        onChange={(v) => s.set({ grid: v })}
        options={[
          { value: 'off', label: 'No grid' },
          { value: 'thirds', label: 'Thirds' },
          { value: 'golden', label: 'Golden' },
          { value: 'square', label: 'Square' },
        ]}
      />
      <SwitchLine title="Level" value={s.level} onChange={(v) => s.set({ level: v })} />
      <SwitchLine title="Focus peaking" note="Highlights sharp edges in Pro and Macro." value={s.peaking} onChange={(v) => s.set({ peaking: v })} />
      <SwitchLine title="Zebras" note="Stripes over areas that are about to clip." value={s.zebra} onChange={(v) => s.set({ zebra: v })} />
      {storageLine ? (
        <T variant="caption" color={palette.ash} style={styles.storage}>
          {storageLine}
        </T>
      ) : null}
    </Sheet>
  );
}

const styles = StyleSheet.create({
  label: { marginTop: space.lg, marginBottom: space.sm },
  note: { marginTop: 4 },
  switchLine: { flexDirection: 'row', alignItems: 'center', marginTop: space.lg, gap: 12 },
  switchText: { flex: 1 },
  divider: { height: 1, backgroundColor: palette.rule, marginTop: space.xl },
  storage: { marginTop: space.xl },
});
