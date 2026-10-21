import AsyncStorage from '@react-native-async-storage/async-storage';
import { create } from 'zustand';
import { createJSONStorage, persist } from 'zustand/middleware';
import type { ThemePreference } from '@devdarshan/ui';

interface SettingsState {
  themePreference: ThemePreference;
  recentSearches: string[];
  setThemePreference: (value: ThemePreference) => void;
  addRecentSearch: (value: string) => void;
  clearRecentSearches: () => void;
}

export const useSettings = create<SettingsState>()(
  persist(
    (set) => ({
      themePreference: 'system',
      recentSearches: [],
      setThemePreference: (themePreference) => set({ themePreference }),
      addRecentSearch: (value) =>
        set((state) => {
          const term = value.trim();
          if (term.length < 2) return state;
          const rest = state.recentSearches.filter((s) => s.toLowerCase() !== term.toLowerCase());
          return { recentSearches: [term, ...rest].slice(0, 6) };
        }),
      clearRecentSearches: () => set({ recentSearches: [] }),
    }),
    {
      name: 'devdarshan-settings',
      version: 1,
      storage: createJSONStorage(() => AsyncStorage),
      partialize: (state) => ({ themePreference: state.themePreference, recentSearches: state.recentSearches }),
    },
  ),
);
