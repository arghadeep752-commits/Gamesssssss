import { NativeModule, requireNativeModule } from 'expo';

import type {
  Capabilities,
  LookInfo,
  MediaProbe,
  PhotoResult,
  VideoExportResult,
} from './types';

type EngineEvents = {
  onExportProgress: (event: { stage: 'analyzing' | 'rendering'; progress: number }) => void;
};

declare class CameroEngineModule extends NativeModule<EngineEvents> {
  getCapabilities(refresh: boolean): Promise<Capabilities>;
  getLooks(): Promise<LookInfo[]>;
  renderLookPreviews(uri: string, size: number, ids: string[]): Promise<Record<string, string>>;
  exportPhoto(
    uri: string,
    grade: string | null,
    transform: string | null,
    format: 'jpeg' | 'png',
    quality: number
  ): Promise<{ uri: string; width: number; height: number; bytes: number; thumbnail?: string }>;
  exportVideo(uri: string, grade: string | null, transform: string | null, options: string): Promise<VideoExportResult>;
  cancelExport(): Promise<void>;
  probeMedia(uri: string): Promise<MediaProbe>;
  getThumbnail(uri: string, size: number): Promise<string | null>;
  getVideoFrames(uri: string, count: number, height: number): Promise<string[]>;
  getStorageInfo(): Promise<{ freeBytes: number; totalBytes: number }>;
  setSaveLocation(location: 'dcim' | 'pictures'): Promise<void>;
  clearCache(): Promise<void>;
  share(uris: string[], mime: string): Promise<boolean>;
}

declare class CameroCameraModule extends NativeModule<Record<string, never>> {
  takePhoto(): Promise<PhotoResult>;
  startRecording(): Promise<void>;
  stopRecording(): Promise<void>;
  pauseRecording(): Promise<void>;
  resumeRecording(): Promise<void>;
  setRecordingMuted(muted: boolean): Promise<void>;
  setZoom(ratio: number): Promise<void>;
  setExposureIndex(index: number): Promise<void>;
  focusAt(x: number, y: number, lock: boolean): Promise<void>;
  resetFocus(): Promise<void>;
}

export const Engine = requireNativeModule<CameroEngineModule>('CameroEngine');
export const Camera = requireNativeModule<CameroCameraModule>('CameroCamera');
