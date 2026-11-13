import type { StyleProp, ViewStyle } from 'react-native';

export type CameraMode = 'photo' | 'video' | 'portrait' | 'macro' | 'pro' | 'slowmo' | 'timelapse';
export type AspectRatio = '4:3' | '16:9' | '1:1';
export type FlashMode = 'off' | 'on' | 'auto';
export type VideoQuality = 'UHD' | 'FHD' | 'HD' | 'SD';
export type StabilizationMode = 'off' | 'standard' | 'enhanced' | 'software';
export type LensKind = 'wide' | 'ultrawide' | 'tele' | 'macro' | 'front';
export type AwbMode =
  | 'auto'
  | 'incandescent'
  | 'fluorescent'
  | 'warm-fluorescent'
  | 'daylight'
  | 'cloudy'
  | 'twilight'
  | 'shade';

export type Adjustments = {
  exposure: number;
  brightness: number;
  contrast: number;
  saturation: number;
  vibrance: number;
  temperature: number;
  tint: number;
  highlights: number;
  shadows: number;
  whites: number;
  blacks: number;
  sharpness: number;
  clarity: number;
  fade: number;
  vignette: number;
  grain: number;
  dehaze: number;
};

/** A grade in native units: exposure in stops, fade/grain/sharpness 0..1, the rest -1..1. */
export type Grade = {
  look: string;
  intensity: number;
  adj: Partial<Adjustments>;
};

export type PhotoConfig = {
  resolution: 'max' | 'standard' | 'highres';
  jpegQuality: number;
  format: 'jpeg' | 'raw+jpeg' | 'ultrahdr';
  extension: 'none' | 'hdr' | 'night' | 'auto';
  keepOriginal: boolean;
  shutterSound: boolean;
  mirrorFront: boolean;
};

export type VideoConfig = {
  quality: VideoQuality;
  fps: number;
  hdr: boolean;
  stabilization: StabilizationMode;
  bitrate: 'auto' | 'high' | 'max';
  audio: boolean;
  clean: boolean;
  slowFps: number;
};

export type OverlayConfig = {
  peaking: boolean;
  zebra: boolean;
  bypass: boolean;
  peakColor: string;
};

export type ManualConfig = {
  iso: number | null;
  shutterNs: number | null;
  focus: number | null;
  awb: AwbMode;
  aeLock: boolean;
  awbLock: boolean;
};

export type EditTransform = {
  rotation: 0 | 90 | 180 | 270;
  flipH: boolean;
  flipV: boolean;
  crop: { x: number; y: number; w: number; h: number };
};

export type VideoMode = { quality: VideoQuality; width: number; height: number; fps: number[] };

export type CameraCapability = {
  id: string;
  facing: 'front' | 'back' | 'external';
  lens: LensKind;
  eqFocalLength?: number;
  focalLength?: number;
  aperture?: number;
  minFocusCm?: number;
  fixedFocus: boolean;
  intrinsicZoom: number;
  sensorOrientation: number;
  hasFlash: boolean;
  hardwareLevel: string;
  zoomMin: number;
  zoomMax: number;
  logicalMultiCamera: boolean;
  opticalStops: number[];
  exposureSupported: boolean;
  exposureMin: number;
  exposureMax: number;
  exposureStep: number;
  manualSensor: boolean;
  manualFocus: boolean;
  minFocusDiopters: number;
  isoMin?: number;
  isoMax?: number;
  shutterMinNs?: number;
  shutterMaxNs?: number;
  awbModes: AwbMode[];
  awbLock: boolean;
  aeLock: boolean;
  ois: boolean;
  eis: boolean;
  previewStabilization: boolean;
  videoStabilization: boolean;
  raw: boolean;
  ultraHdr: boolean;
  photoMax?: { width: number; height: number; mp: number };
  photoHighRes?: { width: number; height: number; mp: number } | null;
  video: VideoMode[];
  hdrVideo: boolean;
  hdrQualities: VideoQuality[];
  highSpeed?: { qualities: VideoQuality[]; fps: number[] } | null;
  extensions: Array<'bokeh' | 'hdr' | 'night' | 'auto'>;
};

export type DeviceInfo = {
  manufacturer: string;
  model: string;
  sdk: number;
  release: string;
  totalRamMb: number;
  lowRam: boolean;
  tier: 'low' | 'mid' | 'high';
  gpu?: string;
  maxTextureSize: number;
  gyroscope: boolean;
  accelerometer: boolean;
};

export type Capabilities = {
  cameras: CameraCapability[];
  device: DeviceInfo;
  codecs: { h264: boolean; h264Max?: string; hevc: boolean; hevcMax?: string };
};

export type LookInfo = { id: string; name: string; collection: string; swatch: string[] };

export type ReadyEvent = {
  cameraId: string;
  mode: CameraMode;
  lens: LensKind;
  zoom: number;
  zoomMin: number;
  zoomMax: number;
  exposureSupported: boolean;
  exposureMin: number;
  exposureMax: number;
  exposureStep: number;
  exposureIndex: number;
  hasFlash: boolean;
  liveLook: boolean;
  lookInRecording: boolean;
  lookNote?: 'slowmo' | 'extension' | 'hdr' | 'gpu';
  extension: string;
  photoWidth?: number;
  photoHeight?: number;
  videoWidth?: number;
  videoHeight?: number;
  videoQuality?: VideoQuality;
  fps: number;
  hdr: boolean;
  raw: boolean;
  ultraHdr: boolean;
  ois: boolean;
  eis: boolean;
  softwareStabilization: boolean;
  stabilizationCrop: number;
  notes: string[];
  macroFocusMode: boolean;
};

export type RecordingEvent = {
  state: 'recording' | 'paused' | 'saving' | 'saved' | 'error';
  durationMs?: number;
  bytes?: number;
  frames?: number;
  clipMs?: number;
  uri?: string;
  thumbnail?: string;
  warning?: string;
  message?: string;
};

export type PhotoResult = {
  uri: string;
  thumbnail?: string;
  width?: number;
  height?: number;
  originalUri?: string;
  rawUri?: string;
  warning?: string;
};

export type MetadataEvent = { iso?: number; exposureNs?: number; focusDiopters?: number; afState?: number };

export type CameroCameraViewProps = {
  style?: StyleProp<ViewStyle>;
  active: boolean;
  cameraId?: string;
  mode: CameraMode;
  aspect: AspectRatio;
  photo: string;
  video: string;
  grade: string;
  overlay: string;
  flash: FlashMode;
  torch: boolean;
  manual: string;
  timelapseIntervalMs: number;
  onReady?: (e: { nativeEvent: ReadyEvent }) => void;
  onZoomChanged?: (e: { nativeEvent: { ratio: number } }) => void;
  onFocusResult?: (e: { nativeEvent: { success: boolean; locked: boolean } }) => void;
  onRecordingEvent?: (e: { nativeEvent: RecordingEvent }) => void;
  onPhotoEvent?: (e: { nativeEvent: { state: 'captured' | 'saved'; uri?: string; thumbnail?: string } }) => void;
  onCameraMetadata?: (e: { nativeEvent: MetadataEvent }) => void;
  onOrientationChanged?: (e: { nativeEvent: { degrees: number } }) => void;
  onPreviewState?: (e: { nativeEvent: { streaming: boolean } }) => void;
  onCameraError?: (e: { nativeEvent: { code: string; message: string } }) => void;
};

export type CanvasLayout = {
  x: number;
  y: number;
  width: number;
  height: number;
  sourceWidth: number;
  sourceHeight: number;
};

export type CameroCanvasViewProps = {
  style?: StyleProp<ViewStyle>;
  source: string | null;
  kind: 'image' | 'video';
  grade: string;
  transform: string;
  compare: boolean;
  cropMode: boolean;
  inset: number;
  playing?: boolean;
  muted?: boolean;
  speed?: number;
  trimStartMs?: number;
  trimEndMs?: number;
  seekMs?: number;
  onCanvasLayout?: (e: { nativeEvent: CanvasLayout }) => void;
  onVideoInfo?: (e: { nativeEvent: { durationMs: number; width: number; height: number } }) => void;
  onVideoProgress?: (e: { nativeEvent: { positionMs: number; durationMs: number; playing: boolean } }) => void;
  onCanvasError?: (e: { nativeEvent: { message: string } }) => void;
};

export type MediaProbe = {
  kind: 'photo' | 'video';
  mime?: string;
  bytes: number;
  width?: number;
  height?: number;
  orientation?: number;
  rotation?: number;
  durationMs?: number;
  bitrate?: number;
  fps?: number;
  captureFps?: number;
  hasAudio?: boolean;
  videoCodec?: string;
  audioCodec?: string;
  hdr?: boolean;
  make?: string;
  model?: string;
  dateTime?: string;
  iso?: number;
  exposureTime?: number;
  fNumber?: number;
  focalLength?: number;
  focalLength35?: number;
  software?: string;
  flash?: boolean;
};

export type VideoExportOptions = {
  trimStartMs: number;
  trimEndMs: number;
  speed: number;
  mute: boolean;
  resolution: 'original' | '2160' | '1440' | '1080' | '720';
  fps: number;
  smooth: boolean;
  codec: 'h264' | 'hevc';
  bitrate: number;
  stabilize: number | null;
};

export type VideoExportResult = {
  uri: string;
  thumbnail?: string;
  width: number;
  height: number;
  durationMs?: number;
  bytes?: number;
  upscaled: boolean;
  interpolated: boolean;
  stabilized: boolean;
  codec: 'h264' | 'hevc';
  warning?: string;
};
