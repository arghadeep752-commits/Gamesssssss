import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { AspectRatio, CameraMode, PhotoConfig, VideoConfig } from '../../modules/camero-engine';
import type { AccentKey } from '../theme/tokens';

export type GridType = 'off' | 'thirds' | 'golden' | 'square';

export type SettingsState = {
  photo: PhotoConfig;
  video: VideoConfig;
  aspect: AspectRatio;
  lastMode: CameraMode;
  defaultCamera: 'back' | 'front';
  grid: GridType;
  level: boolean;
  zebra: boolean;
  peaking: boolean;
  peakColor: string;
  defaultIntensity: number;
  lookId: string;
  saveLocation: 'dcim' | 'pictures';
  galleryColumns: 3 | 4;
  reviewAfterCapture: boolean;
  timelapseIntervalMs: number;
  accent: AccentKey;
  haptics: boolean;
  performance: 'auto' | 'quality' | 'efficiency';
  onboarded: boolean;
  set: (patch: Partial<Omit<SettingsState, 'set' | 'setPhoto' | 'setVideo'>>) => void;
  setPhoto: (patch: Partial<PhotoConfig>) => void;
  setVideo: (patch: Partial<VideoConfig>) => void;
};

export const DEFAULT_PHOTO: PhotoConfig = {
  resolution: 'max',
  jpegQuality: 95,
  format: 'jpeg',
  extension: 'none',
  keepOriginal: true,
  shutterSound: false,
  mirrorFront: true,
};

export const DEFAULT_VIDEO: VideoConfig = {
  quality: 'FHD',
  fps: 30,
  hdr: false,
  stabilization: 'standard',
  bitrate: 'auto',
  audio: true,
  clean: false,
  slowFps: 120,
};

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      photo: DEFAULT_PHOTO,
      video: DEFAULT_VIDEO,
      aspect: '4:3',
      lastMode: 'photo',
      defaultCamera: 'back',
      grid: 'off',
      level: true,
      zebra: false,
      peaking: true,
      peakColor: '#FFB46B',
      defaultIntensity: 80,
      lookId: 'none',
      saveLocation: 'dcim',
      galleryColumns: 3,
      reviewAfterCapture: false,
      timelapseIntervalMs: 1000,
      accent: 'tungsten',
      haptics: true,
      performance: 'auto',
      onboarded: false,
      set: (patch) => set(patch),
      setPhoto: (patch) => set((s) => ({ photo: { ...s.photo, ...patch } })),
      setVideo: (patch) => set((s) => ({ video: { ...s.video, ...patch } })),
    }),
    {
      name: 'camero.settings',
      version: 1,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: ({ set: _s, setPhoto: _p, setVideo: _v, ...rest }) => rest,
    }
  )
);
