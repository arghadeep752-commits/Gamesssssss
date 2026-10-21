import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { ThemePreference } from '@devdarshan/ui';

interface AdminSettings {
  themePreference: ThemePreference;
  setThemePreference: (value: ThemePreference) => void;
}

export const useSettings = create<AdminSettings>()(
  persist(
    (set) => ({
      themePreference: 'system',
      setThemePreference: (themePreference) => set({ themePreference }),
    }),
    {
      name: 'devdarshan-admin-settings',
      version: 1,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ themePreference: state.themePreference }),
    },
  ),
);
