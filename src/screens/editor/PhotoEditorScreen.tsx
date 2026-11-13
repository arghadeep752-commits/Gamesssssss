import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, StyleSheet, View, type LayoutChangeEvent } from 'react-native';

import { CanvasView, Engine, type EditTransform } from '../../../modules/camero-engine';
import { haptic } from '../../lib/haptics';
import { gradeJson, hasAdjustments, isNeutral, NEUTRAL_GRADE, type UiGrade } from '../../lib/grade';
import { idFromUri } from '../../lib/media';
import { cropForRatio, IDENTITY, isIdentity, mirror, outputSize, rotateClockwise, transformJson, type Rect } from '../../lib/transform';
import type { Nav, RootStackParamList } from '../../navigation/types';
import { useApp } from '../../state/app';
import { useLibrary } from '../../state/library';
import { useSettings } from '../../state/settings';
import { palette, space } from '../../theme/tokens';
import { ConfirmSheet } from '../../ui/ConfirmSheet';
import { Ruler } from '../../ui/Ruler';
import { T } from '../../ui/T';
import { toast } from '../../ui/Toast';
import { AdjustPanel } from '../shared/AdjustPanel';
import { LookStrip } from '../shared/LookStrip';
import { CropTools, ratioFor, type AspectKey } from './CropTools';
import { CropOverlay } from './CropOverlay';
import { BeforeTag, CompareButton, EditorHeader, ToolTabs, type ToolTab } from './EditorChrome';
import { PanelActions } from './PanelActions';
import { useGuard } from './useGuard';
import { useHistory } from './useHistory';

type PhotoEdit = { grade: UiGrade; transform: EditTransform };
type Tab = 'looks' | 'adjust' | 'crop';

const CROP_INSET = 28;

/** Fits a w x h box into the view, the way the canvas does. */
function fit(viewW: number, viewH: number, w: number, h: number, inset: number) {
  const aw = viewW - inset * 2;
  const ah = viewH - inset * 2;
  if (aw <= 0 || ah <= 0 || w <= 0 || h <= 0) return null;
  const s = Math.min(aw / w, ah / h);
  const width = w * s;
  const height = h * s;
  return { x: (viewW - width) / 2, y: (viewH - height) / 2, width, height };
}

export function PhotoEditorScreen() {
  const nav = useNavigation<Nav>();
  const route = useRoute<RouteProp<RootStackParamList, 'PhotoEditor'>>();
  const { id, uri } = route.params;
  const looks = useApp((s) => s.looks);
  const loadLooks = useApp((s) => s.loadLooks);
  const presets = useLibrary((s) => s.presets);
  const addPreset = useLibrary((s) => s.addPreset);
  const addEdit = useLibrary((s) => s.addEdit);
  const defaultIntensity = useSettings((s) => s.defaultIntensity);

  const h = useHistory<PhotoEdit>({ grade: NEUTRAL_GRADE, transform: IDENTITY });
  const { grade, transform } = h.state;
  const [tab, setTab] = useState<Tab>('looks');
  const [presetId, setPresetId] = useState<string | null>(null);
  const [compare, setCompare] = useState(false);
  const [view, setView] = useState({ w: 0, h: 0 });
  const [source, setSource] = useState<{ w: number; h: number } | null>(null);
  const [aspect, setAspect] = useState<AspectKey>('free');
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  const [failed, setFailed] = useState<string | null>(null);
  const cropMode = tab === 'crop';
  const changed = !isNeutral(grade) || !isIdentity(transform);
  const guard = useGuard(h.dirty && changed);

  useEffect(() => {
    loadLooks();
  }, [loadLooks]);

  useEffect(() => {
    if (!looks.length) return;
    let alive = true;
    Engine.renderLookPreviews(uri, 160, ['none', ...looks.map((l) => l.id)])
      .then((p) => alive && setPreviews(p))
      .catch(() => {});
    return () => {
      alive = false;
    };
  }, [uri, looks]);

  const turned = transform.rotation === 90 || transform.rotation === 270;
  const frameW = source ? (turned ? source.h : source.w) : 0;
  const frameH = source ? (turned ? source.w : source.h) : 0;
  const frame = useMemo(() => fit(view.w, view.h, frameW, frameH, CROP_INSET), [view, frameW, frameH]);
  const frameAspect = frameW > 0 && frameH > 0 ? frameW / frameH : 1;
  const lockRatio = ratioFor(aspect, frameAspect, source ? source.w / source.h : 1);
  const out = source ? outputSize(source.w, source.h, transform) : null;

  const setGrade = (patch: Partial<UiGrade>, commit: boolean) => h.update((s) => ({ ...s, grade: { ...s.grade, ...patch } }), commit);
  const setTransform = (next: EditTransform) => h.update((s) => ({ ...s, transform: next }), true);

  const onAspect = (key: AspectKey) => {
    setAspect(key);
    const r = ratioFor(key, frameAspect, source ? source.w / source.h : 1);
    if (r) setTransform({ ...transform, crop: cropForRatio(r) });
  };

  const save = async () => {
    setSaving(true);
    try {
      const res = await Engine.exportPhoto(
        uri,
        isNeutral(grade) ? null : gradeJson(grade),
        isIdentity(transform) ? null : transformJson(transform),
        'jpeg',
        95
      );
      const newId = idFromUri(res.uri);
      if (newId) addEdit(newId, { sourceId: id, sourceUri: uri, kind: 'photo', grade, transform, createdAt: Date.now() });
      haptic.success();
      toast('Saved as a new photo. The original is unchanged.');
      guard.release();
      if (newId) nav.replace('Viewer', { id: newId, uri: res.uri, filter: 'all' });
      else nav.goBack();
    } catch (e) {
      toast(e instanceof Error && e.message ? e.message : 'The photo couldn’t be saved.');
    } finally {
      setSaving(false);
    }
  };

  const tabs: ToolTab<Tab>[] = [
    { key: 'looks', label: 'Looks', icon: 'look', marked: grade.look !== 'none' },
    { key: 'adjust', label: 'Adjust', icon: 'adjust', marked: hasAdjustments(grade.adj) },
    { key: 'crop', label: 'Crop', icon: 'crop', marked: !isIdentity(transform) },
  ];

  return (
    <View style={styles.root}>
      <EditorHeader
        onClose={() => nav.goBack()}
        onUndo={h.undo}
        onRedo={h.redo}
        canUndo={h.canUndo}
        canRedo={h.canRedo}
        onSave={save}
        saveLabel="Save copy"
        saveDisabled={!changed || saving}
      />

      <View style={styles.canvasBox} onLayout={(e: LayoutChangeEvent) => setView({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
        <CanvasView
          style={StyleSheet.absoluteFill}
          source={uri}
          kind="image"
          grade={gradeJson(grade)}
          transform={transformJson(transform)}
          compare={compare && !cropMode}
          cropMode={cropMode}
          inset={cropMode ? CROP_INSET : 0}
          onCanvasLayout={(e) => {
            const { sourceWidth, sourceHeight } = e.nativeEvent;
            if (!source || source.w !== sourceWidth || source.h !== sourceHeight) setSource({ w: sourceWidth, h: sourceHeight });
          }}
          onCanvasError={(e) => setFailed(e.nativeEvent.message)}
        />
        {!source && !failed ? <ActivityIndicator color={palette.ash} style={styles.loading} /> : null}
        {failed ? (
          <View style={styles.failed}>
            <T variant="bodyStrong">This photo can’t be opened for editing.</T>
            <T variant="caption" color={palette.ash}>
              {failed}
            </T>
          </View>
        ) : null}
        {cropMode && frame ? (
          <CropOverlay frame={frame} crop={transform.crop} ratio={lockRatio} onChange={(crop: Rect) => setTransform({ ...transform, crop })} />
        ) : null}
        {!cropMode && source ? <CompareButton active={compare} onChange={setCompare} /> : null}
        {compare && !cropMode ? <BeforeTag /> : null}
      </View>

      <View style={styles.panel}>
        {tab === 'looks' ? (
          <View>
            <LookStrip
              looks={looks}
              presets={presets}
              selected={grade.look}
              selectedPreset={presetId}
              previews={previews}
              onSelect={(look) => {
                setPresetId(null);
                const keep = grade.look !== 'none' && look !== 'none';
                setGrade({ look, intensity: keep ? grade.intensity : defaultIntensity }, true);
              }}
              onPreset={(p) => {
                setPresetId(p.id);
                h.update((s) => ({ ...s, grade: p.grade }), true);
              }}
            />
            <View style={styles.rulerBox}>
              {grade.look !== 'none' ? (
                <Ruler
                  min={0}
                  max={100}
                  step={1}
                  value={grade.intensity}
                  reference={100}
                  format={(v) => `${Math.round(v)}%`}
                  caption="Strength"
                  onChange={(v) => setGrade({ intensity: v }, false)}
                  onEnd={h.commit}
                />
              ) : (
                <T variant="caption" color={palette.iron} align="center" style={styles.hint}>
                  Pick a look. The preview is the same render that gets saved, at full resolution.
                </T>
              )}
            </View>
          </View>
        ) : null}

        {tab === 'adjust' ? (
          <View>
            <AdjustPanel
              adj={grade.adj}
              onChange={(k, v) => h.update((s) => ({ ...s, grade: { ...s.grade, adj: { ...s.grade.adj, [k]: v } } }))}
              onCommit={h.commit}
            />
            <PanelActions
              actions={[
                {
                  label: 'Reset',
                  disabled: !hasAdjustments(grade.adj),
                  onPress: () => setGrade({ adj: {} }, true),
                },
                {
                  label: 'Save as preset',
                  disabled: isNeutral(grade),
                  onPress: () => {
                    const p = addPreset(`Preset ${presets.length + 1}`, grade);
                    setPresetId(p.id);
                    toast(`Saved as ${p.name}. Rename it in Looks.`);
                  },
                },
              ]}
            />
          </View>
        ) : null}

        {tab === 'crop' ? (
          <CropTools
            aspect={aspect}
            onAspect={onAspect}
            onRotate={() => {
              setTransform(rotateClockwise(transform));
              if (aspect !== 'free' && aspect !== 'square') setAspect('free');
            }}
            onMirror={() => setTransform(mirror(transform))}
            onReset={() => {
              setAspect('free');
              setTransform(IDENTITY);
            }}
            resetDisabled={isIdentity(transform)}
            outputLabel={out ? `${out.width} × ${out.height}` : undefined}
          />
        ) : null}
      </View>

      <ToolTabs tabs={tabs} value={tab} onChange={setTab} />

      {saving ? (
        <View style={styles.saving}>
          <ActivityIndicator color={palette.ink} />
          <T variant="label" style={styles.savingText}>
            Saving a copy at full resolution
          </T>
        </View>
      ) : null}

      <ConfirmSheet
        visible={guard.asking}
        title="Discard your edits?"
        message="The photo stays as it was. Your changes to it will be lost."
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
  canvasBox: { flex: 1, backgroundColor: palette.black },
  loading: { ...StyleSheet.absoluteFillObject },
  failed: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center', gap: space.xs, paddingHorizontal: space.xl },
  panel: { minHeight: 168, justifyContent: 'center', paddingTop: space.sm, backgroundColor: palette.black },
  rulerBox: { minHeight: 70, justifyContent: 'center', marginTop: space.xs },
  hint: { paddingHorizontal: space.xl },
  saving: { ...StyleSheet.absoluteFillObject, backgroundColor: 'rgba(0,0,0,0.7)', alignItems: 'center', justifyContent: 'center' },
  savingText: { marginTop: space.md },
});
