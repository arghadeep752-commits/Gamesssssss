import { create } from 'zustand';

import { Engine, type Capabilities, type LookInfo } from '../../modules/camero-engine';

type AppState = {
  caps: Capabilities | null;
  looks: LookInfo[];
  capsError: string | null;
  loadCapabilities: (refresh?: boolean) => Promise<Capabilities | null>;
  loadLooks: () => Promise<void>;
};

export const useApp = create<AppState>((set, get) => ({
  caps: null,
  looks: [],
  capsError: null,
  loadCapabilities: async (refresh = false) => {
    try {
      const caps = await Engine.getCapabilities(refresh);
      set({ caps, capsError: null });
      return caps;
    } catch (e) {
      set({ capsError: e instanceof Error ? e.message : String(e) });
      return get().caps;
    }
  },
  loadLooks: async () => {
    if (get().looks.length) return;
    try {
      const looks = await Engine.getLooks();
      set({ looks });
    } catch {
      set({ looks: [] });
    }
  },
}));

export function lookName(looks: LookInfo[], id: string): string {
  if (id === 'none') return 'Original';
  return looks.find((l) => l.id === id)?.name ?? 'Original';
}
