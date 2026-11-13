import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View, type LayoutChangeEvent } from 'react-native';

import { CanvasView, Engine, type EditTransform, type MediaProbe } from '../../../modules/camero-engine';
import { formatClock, formatDuration } from '../../lib/format';
import { gradeJson, hasAdjustments, isNeutral, NEUTRAL_GRADE, type UiGrade } from '../../lib/grade';
import { cropForRatio, IDENTITY, isIdentity, mirror, outputSize, rotateClockwise, transformJson, type Rect } from '../../lib/transform';
import type { Nav, RootStackParamList } from '../../navigation/types';
import { useApp } from '../../state/app';
import { useLibrary } from '../../state/library';
import { useSettings } from '../../state/settings';
import { useAccent } from '../../theme/accent';
import { palette, space } from '../../theme/tokens';
import { ConfirmSheet } from '../../ui/ConfirmSheet';
import { Icon } from '../../ui/Icon';
import { Ruler } from '../../ui/Ruler';
import { Segmented } from '../../ui/Segmented';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { Toggle } from '../../ui/Toggle';
import { AdjustPanel } from '../shared/AdjustPanel';
import { LookStrip } from '../shared/LookStrip';
import { CropOverlay } from './CropOverlay';
import { CropTools, ratioFor, type AspectKey } from './CropTools';
import { BeforeTag, CompareButton, EditorHeader, ToolTabs, type ToolTab } from './EditorChrome';
import { ExportSheet } from './ExportSheet';
import { PanelActions } from './PanelActions';
import { Timeline } from './Timeline';
import { useGuard } from './useGuard';
import { useHistory } from './useHistory';

export type VideoEdit = {
  grade: UiGrade;
  transform: EditTransform;
  trimStartMs: number;
  trimEndMs: number;
  speed: number;
  mute: boolean;
  stabilize: number | null;
};

type Tab = 'looks' | 'adjust' | 'crop' | 'speed' | 'sound' | 'steady';

const SPEEDS = [0.25, 0.5, 1, 1.5, 2, 4];
const CROP_INSET = 28;
const FRAME_COUNT = 10;

function fit(viewW: number, viewH: number, w: number, h: number, inset: number) {
  const aw = viewW - inset * 2;
  const ah = viewH - inset * 2;
  if (aw <= 0 || ah <= 0 || w <= 0 || h <= 0) return null;
  const s = Math.min(aw / w, ah / h);
  return { x: (viewW - w * s) / 2, y: (viewH - h * s) / 2, width: w * s, height: h * s };
}

function SwitchRow({ title, note, value, onChange, disabled }: { title: string; note?: string; value: boolean; onChange: (v: boolean) => void; disabled?: boolean }) {
  return (
    <View style={styles.switchRow}>
      <View style={styles.flex}>
        <T variant="body" color={disabled ? palette.iron : palette.ink}>
          {title}
        </T>
        {note ? (
          <T variant="caption" color={palette.ash} style={styles.note}>
            {note}
          </T>
        ) : null}
      </View>
      <Toggle value={value} onChange={onChange} disabled={disabled} />
    </View>
  );
}

export function VideoEditorScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<RouteProp<RootStackParamList, 'VideoEditor'>>();
  const { id, uri } = route.params;
  const accent = useAccent();
  const looks = useApp((s) => s.looks);
  const loadLooks = useApp((s) => s.loadLooks);
  const presets = useLibrary((s) => s.presets);
  const addPreset = useLibrary((s) => s.addPreset);
  const defaultIntensity = useSettings((s) => s.defaultIntensity);

  const h = useHistory<VideoEdit>({
    grade: NEUTRAL_GRADE,
    transform: IDENTITY,
    trimStartMs: 0,
    trimEndMs: -1,
    speed: 1,
    mute: false,
    stabilize: null,
  });
  const e = h.state;
  const [tab, setTab] = useState<Tab>('looks');
  const [presetId, setPresetId] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [probe, setProbe] = useState<MediaProbe | null>(null);
  const [durationMs, setDurationMs] = useState(0);
  const [source, setSource] = useState<{ w: number; h: number } | null>(null);
  const [view, setView] = useState({ w: 0, h: 0 });
  const [frames, setFrames] = useState<string[]>([]);
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [playing, setPlaying] = useState(true);
  const [positionMs, setPositionMs] = useState(0);
  const [seek, setSeek] = useState<{ ms: number; n: number }>({ ms: -1, n: 0 });
  const [aspect, setAspect] = useState<AspectKey>('free');
  const [exporting, setExporting] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const wasPlaying = useRef(true);
  const lastSeekAt = useRef(0);
  const cropMode = tab === 'crop';
  const trimEnd = e.trimEndMs > 0 ? e.trimEndMs : durationMs;
  const trimmed = e.trimStartMs > 0 || (e.trimEndMs > 0 && e.trimEndMs < durationMs - 30);
  const changed = !isNeutral(e.grade) || !isIdentity(e.transform) || trimmed || e.speed !== 1 || e.mute || e.stabilize != null;
  const guard = useGuard(h.dirty && changed);

  useEffect(() => {
    loadLooks();
  }, [loadLooks]);

  useEffect(() => {
    let alive = true;
    Engine.probeMedia(uri)
      .then((p) => alive && setProbe(p))
      .catch(() => {});
    Engine.getVideoFrames(uri, FRAME_COUNT, 96)
      .then((f) => alive && setFrames(f))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [uri]);

  // Look previews come from a frame in the middle of the clip.
  useEffect(() => {
    if (!looks.length || frames.length === 0) return;
    let alive = true;
    const frame = frames[Math.floor(frames.length / 2)];
    Engine.renderLookPreviews(frame, 160, ['none', ...looks.map((l) => l.id)])
      .then((p) => alive && setPreviews(p))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [frames, looks]);

  const doSeek = (ms: number, force: boolean) => {
    const now = Date.now();
    if (!force && now - lastSeekAt.current < 70) return;
    lastSeekAt.current = now;
    // Alternate by a millisecond so seeking to the same spot twice still registers.
    setSeek((s) => ({ ms: Math.round(ms) + (s.n % 2), n: s.n + 1 }));
    setPositionMs(ms);
  };

  const turned = e.transform.rotation === 90 || e.transform.rotation === 270;
  const frameW = source ? (turned ? source.h : source.w) : 0;
  const frameH = source ? (turned ? source.w : source.h) : 0;
  const frame = useMemo(() => fit(view.w, view.h, frameW, frameH, CROP_INSET), [view, frameW, frameH]);
  const frameAspect = frameW > 0 && frameH > 0 ? frameW / frameH : 1;
  const lockRatio = ratioFor(aspect, frameAspect, source ? source.w / source.h : 1);
  const out = source ? outputSize(source.w, source.h, e.transform) : null;
  const clipMs = Math.max(0, trimEnd - e.trimStartMs);
  const outMs = clipMs / e.speed;

  const setGrade = (patch: Partial<UiGrade>, commit: boolean) => h.update((s) => ({ ...s, grade: { ...s.grade, ...patch } }), commit);
  const set = (patch: Partial<VideoEdit>, commit = true) => h.update((s) => ({ ...s, ...patch }), commit);

  const tabs: ToolTab<Tab>[] = [
    { key: 'looks', label: 'Looks', icon: 'look', marked: e.grade.look !== 'none' },
    { key: 'adjust', label: 'Adjust', icon: 'adjust', marked: hasAdjustments(e.grade.adj) },
    { key: 'crop', label: 'Crop', icon: 'crop', marked: !isIdentity(e.transform) },
    { key: 'speed', label: 'Speed', icon: 'speed', marked: e.speed !== 1 },
    { key: 'sound', label: 'Sound', icon: e.mute ? 'mute' : 'volume', marked: e.mute },
    { key: 'steady', label: 'Steady', icon: 'stabilize', marked: e.stabilize != null },
  ];

  return (
    <View style={styles.root}>
      <EditorHeader
        onClose={() => nav.goBack()}
        onUndo={h.undo}
        onRedo={h.redo}
        canUndo={h.canUndo}
        canRedo={h.canRedo}
        onSave={() => {
          wasPlaying.current = playing;
          setPlaying(false);
          setExporting(true);
        }}
        saveLabel="Export"
        saveDisabled={!source || !!failed}
      />

      <View style={styles.canvasBox} onLayout={(ev: LayoutChangeEvent) => setView({ w: ev.nativeEvent.layout.width, h: ev.nativeEvent.layout.height })}>
        <CanvasView
          style={StyleSheet.absoluteFill}
          source={uri}
          kind="video"
          grade={gradeJson(e.grade)}
          transform={transformJson(e.transform)}
          compare={compare && !cropMode}
          cropMode={cropMode}
          inset={cropMode ? CROP_INSET : 0}
          playing={playing && !exporting}
          muted={e.mute}
          speed={e.speed}
          trimStartMs={e.trimStartMs}
          trimEndMs={e.trimEndMs > 0 ? e.trimEndMs : -1}
          seekMs={seek.ms}
          onCanvasLayout={(ev) => {
            const { sourceWidth, sourceHeight } = ev.nativeEvent;
            if (!source || source.w !== sourceWidth || source.h !== sourceHeight) setSource({ w: sourceWidth, h: sourceHeight });
          }}
          onVideoInfo={(ev) => setDurationMs(ev.nativeEvent.durationMs)}
          onVideoProgress={(ev) => {
            setPositionMs(ev.nativeEvent.positionMs);
            if (!durationMs && ev.nativeEvent.durationMs > 0) setDurationMs(ev.nativeEvent.durationMs);
          }}
          onCanvasError={(ev) => setFailed(ev.nativeEvent.message)}
        />
        {!source && !failed ? <ActivityIndicator color={palette.ash} style={StyleSheet.absoluteFill} /> : null}
        {failed ? (
          <View style={styles.failed}>
            <T variant="bodyStrong">This video can’t be opened for editing.</T>
            <T variant="caption" color={palette.ash}>
              {failed}
            </T>
          </View>
        ) : null}
        {cropMode && frame ? (
          <CropOverlay frame={frame} crop={e.transform.crop} ratio={lockRatio} onChange={(crop: Rect) => set({ transform: { ...e.transform, crop } })} />
        ) : null}
        {!cropMode && source ? <CompareButton active={compare} onChange={setCompare} /> : null}
        {compare && !cropMode ? <BeforeTag /> : null}
      </View>

      <View style={styles.transport}>
        <Tap haptic="selection" onPress={() => setPlaying((p) => !p)} style={styles.play} accessibilityLabel={playing ? 'Pause' : 'Play'}>
          <Icon name={playing ? 'pause' : 'play'} size={22} />
        </Tap>
        <T variant="readout">{formatClock(positionMs)}</T>
        <View style={styles.flex} />
        <T variant="readout" color={palette.ash}>
          {e.speed !== 1 ? `${formatDuration(clipMs)} at ${e.speed}×  →  ${formatDuration(outMs)}` : `Length ${formatDuration(clipMs)}`}
        </T>
      </View>
      <View style={styles.timeline}>
        <Timeline
          frames={frames}
          durationMs={durationMs}
          startMs={e.trimStartMs}
          endMs={trimEnd}
          positionMs={positionMs}
          onTrim={(start, end, commit) => {
            const moved = Math.abs(start - e.trimStartMs) > 1 ? start : end;
            set({ trimStartMs: Math.round(start), trimEndMs: Math.round(end) >= durationMs - 30 ? -1 : Math.round(end) }, commit);
            if (!commit) {
              if (playing) {
                wasPlaying.current = true;
                setPlaying(false);
              }
              doSeek(moved, false);
            } else {
              doSeek(start, true);
            }
          }}
          onSeek={(ms, done) => {
            if (!done && playing) {
              wasPlaying.current = true;
              setPlaying(false);
            }
            doSeek(ms, done);
          }}
        />
      </View>

      <View style={styles.panel}>
        {tab === 'looks' ? (
          <View>
            <LookStrip
              looks={looks}
              presets={presets}
              selected={e.grade.look}
              selectedPreset={presetId}
              previews={previews}
              onSelect={(look) => {
                setPresetId(null);
                const keep = e.grade.look !== 'none' && look !== 'none';
                setGrade({ look, intensity: keep ? e.grade.intensity : defaultIntensity }, true);
              }}
              onPreset={(p) => {
                setPresetId(p.id);
                set({ grade: p.grade });
              }}
            />
            {e.grade.look !== 'none' ? (
              <Ruler
                min={0}
                max={100}
                step={1}
                value={e.grade.intensity}
                reference={100}
                format={(v) => `${Math.round(v)}%`}
                caption="Strength"
                onChange={(v) => setGrade({ intensity: v }, false)}
                onEnd={h.commit}
              />
            ) : null}
          </View>
        ) : null}

        {tab === 'adjust' ? (
          <View>
            <AdjustPanel
              adj={e.grade.adj}
              onChange={(k, v) => h.update((s) => ({ ...s, grade: { ...s.grade, adj: { ...s.grade.adj, [k]: v } } }))}
              onCommit={h.commit}
            />
            <PanelActions
              actions={[
                { label: 'Reset', disabled: !hasAdjustments(e.grade.adj), onPress: () => setGrade({ adj: {} }, true) },
                {
                  label: 'Save as preset',
                  disabled: isNeutral(e.grade),
                  onPress: () => {
                    const p = addPreset(`Preset ${presets.length + 1}`, e.grade);
                    setPresetId(p.id);
                  },
                },
              ]}
            />
          </View>
        ) : null}

        {tab === 'crop' ? (
          <CropTools
            aspect={aspect}
            onAspect={(key) => {
              setAspect(key);
              const r = ratioFor(key, frameAspect, source ? source.w / source.h : 1);
              if (r) set({ transform: { ...e.transform, crop: cropForRatio(r) } });
            }}
            onRotate={() => {
              set({ transform: rotateClockwise(e.transform) });
              if (aspect !== 'free' && aspect !== 'square') setAspect('free');
            }}
            onMirror={() => set({ transform: mirror(e.transform) })}
            onReset={() => {
              setAspect('free');
              set({ transform: IDENTITY });
            }}
            resetDisabled={isIdentity(e.transform)}
            outputLabel={out ? `${out.width} × ${out.height}` : undefined}
          />
        ) : null}

        {tab === 'speed' ? (
          <View style={styles.padded}>
            <Segmented
              options={SPEEDS.map((s) => ({ value: s, label: `${s}×` }))}
              value={e.speed}
              onChange={(s) => set({ speed: s })}
            />
            <T variant="caption" color={palette.ash} style={styles.note}>
              {e.speed < 1
                ? 'Each recorded frame is shown for longer, and the sound drops in pitch. For smooth slow motion, record in Slow-mo.'
                : e.speed > 1
                  ? 'Frames are skipped evenly and the sound rises in pitch. Turn sound off in Sound for a silent clip.'
                  : 'Plays at the speed it was recorded.'}
            </T>
          </View>
        ) : null}

        {tab === 'sound' ? (
          <View style={styles.padded}>
            <SwitchRow
              title="Keep sound"
              note={probe && !probe.hasAudio ? 'This video has no sound track.' : 'Turn off to export a silent video.'}
              value={!e.mute && !!probe?.hasAudio}
              disabled={!probe?.hasAudio}
              onChange={(v) => set({ mute: !v })}
            />
          </View>
        ) : null}

        {tab === 'steady' ? (
          <View style={styles.padded}>
            <SwitchRow
              title="Software stabilization"
              note="Measures camera shake frame by frame and smooths the path. Crops the edges a little. The result shows after export."
              value={e.stabilize != null}
              onChange={(v) => set({ stabilize: v ? 0.6 : null })}
            />
            {e.stabilize != null ? (
              <Ruler
                min={10}
                max={100}
                step={5}
                value={Math.round(e.stabilize * 100)}
                majorEvery={2}
                spacing={14}
                format={(v) => `${Math.round(v)}%`}
                caption="Smoothing"
                onChange={(v) => set({ stabilize: v / 100 }, false)}
                onEnd={h.commit}
              />
            ) : null}
          </View>
        ) : null}
      </View>

      <ToolTabs tabs={tabs} value={tab} onChange={setTab} />

      <ExportSheet
        visible={exporting}
        onClose={() => {
          setExporting(false);
          if (wasPlaying.current) setPlaying(true);
        }}
        sourceId={id}
        uri={uri}
        edit={e}
        probe={probe}
        outputSize={out}
        outputMs={outMs}
        accent={accent}
        onDone={(newId, newUri) => {
          guard.release();
          setExporting(false);
          if (newId) nav.replace('Viewer', { id: newId, uri: newUri, filter: 'all' });
          else nav.goBack();
        }}
      />

      <ConfirmSheet
        visible={guard.asking}
        title="Discard your edits?"
        message="The video stays as it was. Your changes to it will be lost."
        confirmLabel="Discard"
        cancelLabel="Keep editing"
        danger
        onConfirm={guard.leave}
        onClose={guard.stay}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  flex: { flex: 1 },
  canvasBox: { flex: 1, backgroundColor: palette.black },
  failed: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center', gap: space.xs, paddingHorizontal: space.xl },
  transport: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.sm, paddingTop: space.xs, gap: space.xs },
  play: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  timeline: { paddingHorizontal: space.md },
  panel: { minHeight: 150, justifyContent: 'center', paddingTop: space.sm },
  padded: { paddingHorizontal: space.lg, gap: space.sm },
  switchRow: { flexDirection: 'row', alignItems: 'center', gap: space.md, paddingVertical: space.xs },
  note: { marginTop: space.xs },
});
