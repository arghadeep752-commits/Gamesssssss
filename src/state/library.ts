import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';

import type { EditTransform } from '../../modules/camero-engine';
import type { UiGrade } from '../lib/grade';

export type EditRecord = {
  sourceId?: string;
  sourceUri: string;
  kind: 'photo' | 'video';
  grade: UiGrade;
  transform?: EditTransform;
  createdAt: number;
  notes?: string[];
};

export type Preset = { id: string; name: string; grade: UiGrade; createdAt: number };

type LibraryState = {
  favorites: Record<string, number>;
  edits: Record<string, EditRecord>;
  presets: Preset[];
  toggleFavorite: (id: string) => boolean;
  addEdit: (id: string, record: EditRecord) => void;
  forget: (id: string) => void;
  addPreset: (name: string, grade: UiGrade) => Preset;
  removePreset: (id: string) => void;
  renamePreset: (id: string, name: string) => void;
};

export const useLibrary = create<LibraryState>()(
  persist(
    (set, get) => ({
      favorites: {},
      edits: {},
      presets: [],
      toggleFavorite: (id) => {
        const next = { ...get().favorites };
        const on = !next[id];
        if (on) next[id] = Date.now();
        else delete next[id];
        set({ favorites: next });
        return on;
      },
      addEdit: (id, record) => set((s) => ({ edits: { ...s.edits, [id]: record } })),
      forget: (id) =>
        set((s) => {
          const favorites = { ...s.favorites };
          const edits = { ...s.edits };
          delete favorites[id];
          delete edits[id];
          return { favorites, edits };
        }),
      addPreset: (name, grade) => {
        const preset: Preset = { id: `p${Date.now().toString(36)}`, name, grade, createdAt: Date.now() };
        set((s) => ({ presets: [preset, ...s.presets] }));
        return preset;
      },
      removePreset: (id) => set((s) => ({ presets: s.presets.filter((p) => p.id !== id) })),
      renamePreset: (id, name) => set((s) => ({ presets: s.presets.map((p) => (p.id === id ? { ...p, name } : p)) })),
    }),
    {
      name: 'camero.library',
      version: 1,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (s) => ({ favorites: s.favorites, edits: s.edits, presets: s.presets }),
    }
  )
);
