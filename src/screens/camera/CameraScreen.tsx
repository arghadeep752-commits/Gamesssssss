import { useIsFocused, useNavigation } from '@react-navigation/native';
import { Image } from 'expo-image';
import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { StyleSheet, View, useWindowDimensions } from 'react-native';
import { Directions, Gesture, GestureDetector } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import {
  Camera,
  CameraView,
  Engine,
  type CameraMode,
  type MetadataEvent,
  type ReadyEvent,
  type RecordingEvent,
  type StabilizationMode,
  type VideoConfig,
} from '../../../modules/camero-engine';
import {
  availableModes,
  cameraById,
  fpsFor,
  isVideoMode,
  lensStops,
  macroCamera,
  mainBack,
  mainFront,
  qualitiesFor,
  zoomKind,
  type LensStop,
} from '../../lib/camera';
import { formatMp, qualityLabel, signed } from '../../lib/format';
import { gradeJson, isNeutral } from '../../lib/grade';
import { haptic } from '../../lib/haptics';
import { idFromUri, latestAsset } from '../../lib/media';
import type { Nav } from '../../navigation/types';
import { useApp } from '../../state/app';
import { IDLE_RECORDING, useCamera } from '../../state/camera';
import { useSettings } from '../../state/settings';
import { useAccent } from '../../theme/accent';
import { palette, radius } from '../../theme/tokens';
import { Icon } from '../../ui/Icon';
import { Tap } from '../../ui/Tap';
import { toast } from '../../ui/Toast';
import { LookDrawer } from './LookDrawer';
import { ModeStrip } from './ModeStrip';
import { CaptureFlash, Countdown, FocusReticle, GridOverlay, LevelIndicator } from './Overlays';
import { ProDials } from './ProDials';
import { QualitySheet } from './QualitySheet';
import { Shutter } from './Shutter';
import { TopBar } from './TopBar';
import { ZoomControl } from './ZoomControl';

const LOOK_NOTES: Record<string, string> = {
  slowmo: 'Looks aren’t applied in slow motion.',
  extension: 'With the phone’s own processing active, the look is applied after capture.',
  hdr: 'Looks are paused while recording HDR video.',
  gpu: 'The GPU pipeline isn’t running, so the look is applied after capture.',
};

export function CameraScreen() {
  const nav = useNavigation<Nav>();
  const focused = useIsFocused();
  const { width: W, height: H } = useWindowDimensions();
  const insets = useSafeAreaInsets();
  const accent = useAccent();
  const caps = useApp((s) => s.caps);
  const settings = useSettings();
  const cam = useCamera();

  const [evIndex, setEvIndex] = useState(0);
  const [meta, setMeta] = useState<MetadataEvent>({});
  const [focus, setFocus] = useState({ x: 0, y: 0, visible: 0, locked: false });
  const [countdown, setCountdown] = useState(0);
  const [flashKey, setFlashKey] = useState(0);
  const [drawer, setDrawer] = useState(false);
  const [quality, setQuality] = useState(false);
  const [busy, setBusy] = useState(false);
  const countdownTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const zoomRef = useRef(cam.zoom);
  const lastZoomSent = useRef(0);
  const fade = useSharedValue(0);

  // ---- camera selection ----
  const current = cameraById(caps, cam.cameraId) ?? (settings.defaultCamera === 'front' ? mainFront(caps) : mainBack(caps));
  const facing: 'front' | 'back' = current?.facing === 'front' ? 'front' : 'back';
  useEffect(() => {
    if (current && cam.cameraId !== current.id) cam.set({ cameraId: current.id });
  }, [current, cam]);
  useEffect(() => {
    if (cam.mode !== settings.lastMode) cam.set({ mode: settings.lastMode });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const modes = useMemo(() => availableModes(caps, facing), [caps, facing]);
  const mode: CameraMode = modes.some((m) => m.mode === cam.mode) ? cam.mode : 'photo';
  const video = isVideoMode(mode);
  const aspect = video ? '16:9' : settings.aspect;
  const stops = useMemo(() => lensStops(caps, current), [caps, current]);
  const ready = cam.ready;
  const recording = cam.recording.state === 'recording' || cam.recording.state === 'paused' || cam.recording.state === 'starting';

  // ---- geometry ----
  const ratio = aspect === '16:9' ? 16 / 9 : aspect === '1:1' ? 1 : 4 / 3;
  const pw = W;
  const ph = Math.round(W * ratio);
  const topBarH = insets.top + 52;
  const top =
    aspect === '16:9' ? Math.max(insets.top, Math.round((H - ph) / 2)) : aspect === '1:1' ? topBarH + Math.round((W * 4) / 3 - W) / 2 : topBarH;
  const controlsH = 210 + insets.bottom;
  const overlapBottom = top + ph > H - controlsH;
  const overlapTop = top < topBarH;

  // ---- native props ----
  const videoConfig: VideoConfig = useMemo(() => {
    const v = settings.video;
    const qs = qualitiesFor(current);
    const q = qs.includes(v.quality) ? v.quality : qs.includes('FHD') ? 'FHD' : qs[0] ?? 'FHD';
    const fl = fpsFor(current, q);
    const fps = fl.includes(v.fps) ? v.fps : fl.includes(30) ? 30 : fl[0];
    let stab: StabilizationMode = v.stabilization;
    if (stab === 'standard' && !current?.ois) stab = 'software';
    if (stab === 'enhanced' && !(current?.videoStabilization || current?.previewStabilization)) stab = 'software';
    const hdr = v.hdr && !!current?.hdrVideo && !!current?.hdrQualities.includes(q);
    const slow = current?.highSpeed?.fps ?? [120];
    return { ...v, quality: q, fps, stabilization: stab, hdr, slowFps: slow.includes(v.slowFps) ? v.slowFps : slow[0] };
  }, [settings.video, current]);

  const photoJson = useMemo(() => {
    const resolution =
      mode === 'macro' && settings.photo.resolution === 'max' && current?.photoHighRes ? 'highres' : settings.photo.resolution;
    const format = settings.photo.format === 'raw+jpeg' && !current?.raw ? 'jpeg' : settings.photo.format === 'ultrahdr' && !current?.ultraHdr ? 'jpeg' : settings.photo.format;
    return JSON.stringify({ ...settings.photo, resolution, format, extension: mode === 'photo' ? settings.photo.extension : 'none' });
  }, [settings.photo, mode, current]);
  const videoJson = useMemo(() => JSON.stringify(videoConfig), [videoConfig]);
  const gradeStr = useMemo(() => gradeJson(cam.grade), [cam.grade]);
  const overlayJson = useMemo(
    () =>
      JSON.stringify({
        peaking: settings.peaking && (mode === 'pro' || mode === 'macro'),
        zebra: settings.zebra,
        bypass: cam.compare,
        peakColor: accent,
      }),
    [settings.peaking, settings.zebra, mode, cam.compare, accent]
  );
  const manualOn = mode === 'pro' || mode === 'macro';
  const manualJson = useMemo(
    () =>
      JSON.stringify({
        iso: manualOn ? cam.manual.iso : null,
        shutterNs: manualOn && cam.manual.shutterS ? Math.round(cam.manual.shutterS * 1e9) : null,
        focus: manualOn ? cam.manual.focus : null,
        awb: manualOn ? cam.manual.awb : 'auto',
        aeLock: false,
        awbLock: false,
      }),
    [cam.manual, manualOn]
  );

  // ---- last capture thumbnail ----
  useEffect(() => {
    if (cam.last) return;
    let cancelled = false;
    latestAsset().then(async (a) => {
      if (!a || cancelled) return;
      const thumb = a.mediaType === 'video' ? await Engine.getThumbnail(a.uri, 200).catch(() => null) : a.uri;
      if (!cancelled) cam.set({ last: { uri: a.uri, thumbnail: thumb ?? undefined, kind: a.mediaType === 'video' ? 'video' : 'photo', at: a.creationTime } });
    });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    Engine.setSaveLocation(settings.saveLocation).catch(() => {});
  }, [settings.saveLocation]);

  // ---- events ----
  const onReady = useCallback(
    (e: { nativeEvent: ReadyEvent }) => {
      const r = e.nativeEvent;
      cam.set({ ready: r, zoom: r.zoom });
      zoomRef.current = r.zoom;
      setEvIndex(r.exposureIndex ?? 0);
      fade.value = withTiming(1, { duration: 220 });
      if (r.notes?.includes('fps') && r.mode === 'video') toast('That frame rate isn’t supported with these settings, so 30 fps is used.');
    },
    [cam, fade]
  );

  const onRecordingEvent = useCallback(
    (e: { nativeEvent: RecordingEvent }) => {
      const r = e.nativeEvent;
      switch (r.state) {
        case 'recording':
        case 'paused':
          cam.setRecording({ state: r.state, durationMs: r.durationMs ?? 0, bytes: r.bytes ?? 0, frames: r.frames ?? 0, clipMs: r.clipMs ?? 0 });
          break;
        case 'saving':
          cam.setRecording({ state: 'saving' });
          break;
        case 'saved':
          cam.set({ recording: IDLE_RECORDING, last: r.uri ? { uri: r.uri, thumbnail: r.thumbnail, kind: 'video', at: Date.now() } : cam.last });
          haptic.success();
          toast(r.warning ?? 'Video saved');
          break;
        case 'error':
          cam.set({ recording: IDLE_RECORDING });
          haptic.warning();
          toast(r.message ?? 'Recording failed');
          break;
      }
    },
    [cam]
  );

  const onOrientation = useCallback((e: { nativeEvent: { degrees: number } }) => cam.set({ orientation: e.nativeEvent.degrees }), [cam]);
  const onZoomChanged = useCallback(
    (e: { nativeEvent: { ratio: number } }) => {
      zoomRef.current = e.nativeEvent.ratio;
      cam.set({ zoom: e.nativeEvent.ratio });
    },
    [cam]
  );

  // ---- actions ----
  const sendZoom = useCallback((z: number) => {
    const now = Date.now();
    zoomRef.current = z;
    if (now - lastZoomSent.current > 24) {
      lastZoomSent.current = now;
      Camera.setZoom(z).catch(() => {});
    }
  }, []);

  const selectStop = useCallback(
    (s: LensStop) => {
      if (s.cameraId !== cam.cameraId) {
        fade.value = withTiming(0, { duration: 120 });
        cam.set({ cameraId: s.cameraId, zoom: 1 });
        if (s.key.startsWith('cam')) return;
      }
      Camera.setZoom(s.key.startsWith('cam') ? 1 : s.zoom).catch(() => {});
    },
    [cam, fade]
  );

  const changeMode = useCallback(
    (m: CameraMode) => {
      if (m === mode || recording) return;
      fade.value = withTiming(0, { duration: 120 });
      const patch: Partial<ReturnType<typeof useCamera.getState>> = { mode: m };
      if (m === 'macro') {
        const macro = macroCamera(caps);
        const main = mainBack(caps);
        if (macro) {
          patch.cameraId = macro.id;
        } else if (main) {
          patch.cameraId = main.id;
          setTimeout(() => Camera.setZoom(Math.min(2, main.zoomMax)).catch(() => {}), 700);
          toast('Macro uses the main camera at its closest focus with a 2× crop.');
        }
      } else if (mode === 'macro') {
        const main = mainBack(caps);
        if (main) patch.cameraId = main.id;
      }
      if (m === 'portrait' && current && !current.extensions.includes('bokeh')) {
        const alt = caps?.cameras.find((c) => c.facing === current.facing && c.extensions.includes('bokeh'));
        if (alt) patch.cameraId = alt.id;
      }
      if (m !== 'pro' && m !== 'macro') patch.manual = { iso: null, shutterS: null, focus: null, awb: 'auto' };
      cam.set(patch);
      settings.set({ lastMode: m });
      setDrawer(false);
    },
    [mode, recording, caps, current, cam, settings, fade]
  );

  const flip = useCallback(() => {
    if (recording) return;
    const next = facing === 'back' ? mainFront(caps) : mainBack(caps);
    if (!next) return;
    fade.value = withTiming(0, { duration: 120 });
    const nextModes = availableModes(caps, next.facing === 'front' ? 'front' : 'back');
    cam.set({ cameraId: next.id, zoom: 1, mode: nextModes.some((m) => m.mode === mode) ? mode : 'photo' });
  }, [recording, facing, caps, cam, mode, fade]);

  const takePhoto = useCallback(async () => {
    setFlashKey((k) => k + 1);
    haptic.light();
    try {
      setBusy(true);
      const res = await Camera.takePhoto();
      cam.set({ last: { uri: res.uri, thumbnail: res.thumbnail, kind: 'photo', at: Date.now() } });
      if (res.warning) toast(res.warning);
      if (settings.reviewAfterCapture) {
        const id = idFromUri(res.uri);
        if (id) nav.navigate('Viewer', { id, uri: res.uri });
      }
    } catch (e) {
      toast(e instanceof Error ? e.message : 'The photo couldn’t be taken.');
    } finally {
      setBusy(false);
    }
  }, [cam, nav, settings.reviewAfterCapture]);

  const toggleRecording = useCallback(async () => {
    if (cam.recording.state === 'saving') return;
    if (recording) {
      Camera.stopRecording().catch(() => {});
      return;
    }
    cam.setRecording({ ...IDLE_RECORDING, state: 'starting' });
    haptic.medium();
    try {
      await Camera.startRecording();
    } catch (e) {
      cam.set({ recording: IDLE_RECORDING });
      toast(e instanceof Error ? e.message : 'Recording couldn’t start.');
    }
  }, [cam, recording]);

  const shutter = useCallback(() => {
    if (video) {
      toggleRecording();
      return;
    }
    if (countdownTimer.current) {
      clearInterval(countdownTimer.current);
      countdownTimer.current = null;
      setCountdown(0);
      return;
    }
    if (cam.timer > 0) {
      let left = cam.timer;
      setCountdown(left);
      countdownTimer.current = setInterval(() => {
        left -= 1;
        if (left <= 0) {
          if (countdownTimer.current) clearInterval(countdownTimer.current);
          countdownTimer.current = null;
          setCountdown(0);
          takePhoto();
        } else {
          setCountdown(left);
          haptic.tick();
        }
      }, 1000);
      return;
    }
    takePhoto();
  }, [video, toggleRecording, cam.timer, takePhoto]);

  useEffect(() => () => {
    if (countdownTimer.current) clearInterval(countdownTimer.current);
  }, []);

  // ---- gestures on the preview ----
  const zoomMin = ready?.zoomMin ?? current?.zoomMin ?? 1;
  const zoomMax = ready?.zoomMax ?? current?.zoomMax ?? 1;
  const pinchStart = useRef(1);
  const evStart = useRef(0);
  const manualExposure = manualOn && (cam.manual.iso != null || cam.manual.shutterS != null);

  const doFocus = useCallback(
    (x: number, y: number, lock: boolean) => {
      setFocus((f) => ({ x, y, visible: f.visible + 1, locked: lock }));
      Camera.focusAt(x, y, lock).catch(() => {});
      if (lock) haptic.medium();
    },
    []
  );

  const setExposure = useCallback((i: number) => {
    setEvIndex(i);
    Camera.setExposureIndex(i).catch(() => {});
  }, []);

  const pinch = Gesture.Pinch()
    .runOnJS(true)
    .onStart(() => {
      pinchStart.current = zoomRef.current;
    })
    .onUpdate((e) => {
      const z = Math.min(zoomMax, Math.max(zoomMin, pinchStart.current * e.scale));
      sendZoom(z);
      cam.set({ zoom: z });
    })
    .onEnd(() => Camera.setZoom(zoomRef.current).catch(() => {}));

  const tap = Gesture.Tap()
    .runOnJS(true)
    .maxDuration(250)
    .onEnd((e, ok) => {
      if (ok) doFocus(e.x, e.y, false);
    });

  const longPress = Gesture.LongPress()
    .runOnJS(true)
    .minDuration(550)
    .onStart((e) => doFocus(e.x, e.y, true));

  const exposurePan = Gesture.Pan()
    .runOnJS(true)
    .enabled(focus.visible > 0 && !manualExposure && !!ready?.exposureSupported)
    .activeOffsetY([-12, 12])
    .failOffsetX([-24, 24])
    .onStart(() => {
      evStart.current = evIndex;
    })
    .onUpdate((e) => {
      const lo = ready?.exposureMin ?? 0;
      const hi = ready?.exposureMax ?? 0;
      const next = Math.min(hi, Math.max(lo, Math.round(evStart.current - e.translationY / 9)));
      if (next !== evIndex) setExposure(next);
    });

  const nextMode = (dir: 1 | -1) => {
    const i = modes.findIndex((m) => m.mode === mode);
    const n = modes[i + dir];
    if (n) changeMode(n.mode);
  };
  const flingLeft = Gesture.Fling().runOnJS(true).direction(Directions.LEFT).onEnd(() => nextMode(1));
  const flingRight = Gesture.Fling().runOnJS(true).direction(Directions.RIGHT).onEnd(() => nextMode(-1));

  const gestures = Gesture.Simultaneous(pinch, Gesture.Race(exposurePan, flingLeft, flingRight, Gesture.Exclusive(longPress, tap)));

  const previewStyle = useAnimatedStyle(() => ({ opacity: fade.value }));

  // ---- labels ----
  let primary = 'Photo';
  let secondary: string | undefined;
  if (!video) {
    primary = ready?.photoWidth ? formatMp(ready.photoWidth, ready.photoHeight) : current?.photoMax ? formatMp(current.photoMax.width, current.photoMax.height) : 'Photo';
    secondary = ready?.raw ? 'RAW' : ready?.ultraHdr ? 'Ultra HDR' : ready && ready.extension !== 'none' ? ({ hdr: 'HDR', night: 'Night', auto: 'Auto', bokeh: 'Portrait' } as Record<string, string>)[ready.extension] : undefined;
  } else if (mode === 'video') {
    primary = qualityLabel(ready?.videoQuality ?? videoConfig.quality);
    secondary = `${ready?.fps ?? videoConfig.fps} fps${ready?.hdr ? ' HDR' : ''}`;
  } else if (mode === 'slowmo') {
    primary = qualityLabel(ready?.videoQuality ?? 'HD');
    secondary = `${videoConfig.slowFps} fps`;
  } else {
    primary = `${settings.timelapseIntervalMs / 1000} s`;
    secondary = `${Math.round((settings.timelapseIntervalMs / 1000) * 30)}×`;
  }
  const stabilization =
    mode === 'video'
      ? ready?.softwareStabilization
        ? 'SW'
        : ready?.eis
          ? 'EIS'
          : ready?.ois
            ? 'OIS'
            : 'Off'
      : undefined;
  const lookNote = ready && !ready.liveLook && !isNeutral(cam.grade) ? LOOK_NOTES[ready.lookNote ?? 'gpu'] : video && settings.video.clean ? 'Recording without look. The look only shows in the viewfinder.' : null;
  const rotation = cam.orientation;
  const zoomK = zoomKind(stops, cam.cameraId, cam.zoom);

  return (
    <View style={styles.root}>
      <StatusBar hidden style="light" />
      <Animated.View style={[styles.previewBox, { top, width: pw, height: ph }, previewStyle]}>
        <CameraView
          style={StyleSheet.absoluteFill}
          active={focused}
          cameraId={current?.id}
          mode={mode}
          aspect={aspect}
          photo={photoJson}
          video={videoJson}
          grade={gradeStr}
          overlay={overlayJson}
          flash={video ? 'off' : cam.flash}
          torch={video && cam.torch}
          manual={manualJson}
          timelapseIntervalMs={settings.timelapseIntervalMs}
          onReady={onReady}
          onZoomChanged={onZoomChanged}
          onRecordingEvent={onRecordingEvent}
          onCameraMetadata={(e) => setMeta(e.nativeEvent)}
          onOrientationChanged={onOrientation}
          onPreviewState={(e) => {
            if (e.nativeEvent.streaming) fade.value = withTiming(1, { duration: 200 });
          }}
          onCameraError={(e) => toast(e.nativeEvent.message)}
          onFocusResult={() => {}}
        />
      </Animated.View>

      <GestureDetector gesture={gestures}>
        <View style={[styles.previewBox, { top, width: pw, height: ph }]} collapsable={false}>
          <GridOverlay type={settings.grid} width={pw} height={ph} />
          {settings.level ? <LevelIndicator /> : null}
          <FocusReticle
            x={focus.x}
            y={focus.y}
            visible={focus.visible}
            locked={focus.locked}
            ev={evIndex !== 0 && ready ? signed(evIndex * ready.exposureStep) : undefined}
          />
          <Countdown value={countdown} />
          <CaptureFlash trigger={flashKey} />
        </View>
      </GestureDetector>

      <TopBar
        mode={mode}
        flash={cam.flash}
        torch={cam.torch}
        hasFlash={!!(ready?.hasFlash ?? current?.hasFlash)}
        timer={cam.timer}
        aspect={settings.aspect}
        primary={primary}
        secondary={secondary}
        stabilization={stabilization}
        lookActive={!isNeutral(cam.grade)}
        recording={{
          active: recording || cam.recording.state === 'saving',
          paused: cam.recording.state === 'paused',
          durationMs: cam.recording.durationMs,
          clipMs: mode === 'timelapse' ? cam.recording.clipMs : undefined,
        }}
        rotation={rotation}
        overlay={overlapTop}
        onFlash={() => cam.set({ flash: cam.flash === 'off' ? 'auto' : cam.flash === 'auto' ? 'on' : 'off' })}
        onTorch={() => cam.set({ torch: !cam.torch })}
        onTimer={() => cam.set({ timer: cam.timer === 0 ? 3 : cam.timer === 3 ? 10 : 0 })}
        onAspect={() => {
          fade.value = withTiming(0, { duration: 100 });
          settings.set({ aspect: settings.aspect === '4:3' ? '16:9' : settings.aspect === '16:9' ? '1:1' : '4:3' });
        }}
        onReadout={() => setQuality(true)}
        onLook={() => setDrawer((d) => !d)}
        onLookHold={(on) => cam.set({ compare: on })}
        onSettings={() => nav.navigate('Settings')}
      />

      <View style={[styles.controls, { paddingBottom: insets.bottom + 10, backgroundColor: overlapBottom && !drawer ? palette.scrim : 'transparent' }]}>
        {drawer ? <LookDrawer grade={cam.grade} onChange={cam.setGrade} note={lookNote} /> : null}
        {!drawer && (mode === 'pro' || mode === 'macro') ? (
          <ProDials
            mode={mode}
            cam={current}
            ready={ready}
            manual={cam.manual}
            meta={meta}
            evIndex={evIndex}
            onManual={cam.setManual}
            onEv={setExposure}
          />
        ) : null}
        {!drawer ? (
          <ZoomControl
            stops={stops}
            cameraId={cam.cameraId}
            zoom={cam.zoom}
            zoomMin={zoomMin}
            zoomMax={zoomMax}
            kind={zoomK}
            rotation={rotation}
            onStop={selectStop}
            onZoom={(z) => {
              sendZoom(z);
              cam.set({ zoom: z });
            }}
          />
        ) : null}
        <ModeStrip modes={modes} mode={mode} onChange={changeMode} disabled={recording} />
        <View style={styles.shutterRow}>
          <View style={styles.side}>
            {recording && mode === 'video' ? (
              <Tap
                haptic="selection"
                style={styles.round}
                onPress={() => (cam.recording.state === 'paused' ? Camera.resumeRecording() : Camera.pauseRecording()).catch(() => {})}
              >
                <Icon name={cam.recording.state === 'paused' ? 'play' : 'pause'} size={20} />
              </Tap>
            ) : (
              <Tap
                haptic="selection"
                disabled={recording}
                onPress={() => {
                  const id = cam.last ? idFromUri(cam.last.uri) : null;
                  if (cam.last && id) nav.navigate('Viewer', { id, uri: cam.last.uri });
                  else nav.navigate('Gallery');
                }}
                onLongPress={() => nav.navigate('Gallery')}
                style={styles.thumb}
              >
                {cam.last?.thumbnail ? (
                  <Image source={{ uri: cam.last.thumbnail }} style={styles.thumbImage} contentFit="cover" transition={160} recyclingKey={cam.last.thumbnail} />
                ) : (
                  <Icon name="gallery" size={20} color={palette.ash} />
                )}
              </Tap>
            )}
          </View>
          <Shutter mode={mode} recording={recording} busy={busy || cam.recording.state === 'saving'} onPress={shutter} />
          <View style={styles.side}>
            {recording && mode === 'video' && settings.video.audio ? (
              <Tap
                haptic="selection"
                style={styles.round}
                onPress={() => {
                  const muted = !cam.recording.muted;
                  cam.setRecording({ muted });
                  Camera.setRecordingMuted(muted).catch(() => {});
                }}
              >
                <Icon name={cam.recording.muted ? 'mute' : 'volume'} size={20} />
              </Tap>
            ) : (
              <Tap haptic="selection" onPress={flip} disabled={recording || !mainFront(caps)} style={styles.round}>
                <View style={{ transform: [{ rotate: `${rotation}deg` }] }}>
                  <Icon name="flip" size={22} />
                </View>
              </Tap>
            )}
          </View>
        </View>
      </View>

      <QualitySheet visible={quality} onClose={() => setQuality(false)} mode={mode} cam={current} />
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  previewBox: { position: 'absolute', left: 0 },
  controls: { position: 'absolute', left: 0, right: 0, bottom: 0 },
  shutterRow: { height: 96, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: 32 },
  side: { width: 56, alignItems: 'center' },
  thumb: {
    width: 48,
    height: 48,
    borderRadius: radius.sm,
    overflow: 'hidden',
    backgroundColor: palette.panel,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  thumbImage: { width: '100%', height: '100%' },
  round: { width: 48, height: 48, borderRadius: 24, backgroundColor: palette.smoke, alignItems: 'center', justifyContent: 'center' },
});
