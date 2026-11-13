import { create } from 'zustand';

import type { AwbMode, CameraMode, FlashMode, ReadyEvent } from '../../modules/camero-engine';
import { NEUTRAL_GRADE, type UiGrade } from '../lib/grade';

export type ManualUi = {
  iso: number | null;
  shutterS: number | null;
  focus: number | null;
  awb: AwbMode;
};

export type RecordingUi = {
  state: 'idle' | 'starting' | 'recording' | 'paused' | 'saving';
  durationMs: number;
  bytes: number;
  frames: number;
  clipMs: number;
  muted: boolean;
};

export type LastCapture = { uri: string; thumbnail?: string; kind: 'photo' | 'video'; at: number };

type CameraState = {
  mode: CameraMode;
  cameraId: string | undefined;
  flash: FlashMode;
  torch: boolean;
  timer: 0 | 3 | 10;
  zoom: number;
  grade: UiGrade;
  manual: ManualUi;
  ready: ReadyEvent | null;
  orientation: number;
  recording: RecordingUi;
  last: LastCapture | null;
  compare: boolean;
  set: (patch: Partial<Omit<CameraState, 'set' | 'setGrade' | 'setManual' | 'setRecording'>>) => void;
  setGrade: (patch: Partial<UiGrade>) => void;
  setManual: (patch: Partial<ManualUi>) => void;
  setRecording: (patch: Partial<RecordingUi>) => void;
};

export const IDLE_RECORDING: RecordingUi = { state: 'idle', durationMs: 0, bytes: 0, frames: 0, clipMs: 0, muted: false };

export const useCamera = create<CameraState>((set) => ({
  mode: 'photo',
  cameraId: undefined,
  flash: 'off',
  torch: false,
  timer: 0,
  zoom: 1,
  grade: NEUTRAL_GRADE,
  manual: { iso: null, shutterS: null, focus: null, awb: 'auto' },
  ready: null,
  orientation: 0,
  recording: IDLE_RECORDING,
  last: null,
  compare: false,
  set: (patch) => set(patch),
  setGrade: (patch) => set((s) => ({ grade: { ...s.grade, ...patch } })),
  setManual: (patch) => set((s) => ({ manual: { ...s.manual, ...patch } })),
  setRecording: (patch) => set((s) => ({ recording: { ...s.recording, ...patch } })),
}));
