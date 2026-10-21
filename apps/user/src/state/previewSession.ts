import { create } from 'zustand';
import type { Wallpaper } from '@devdarshan/shared';

/**
 * Lets the full-screen preview swipe through the list it was opened from without
 * serialising wallpapers into navigation params. Only the latest few lists are kept.
 */
interface PreviewSessionState {
  sessions: Record<string, Wallpaper[]>;
  order: string[];
  open: (wallpapers: Wallpaper[]) => string;
}

let counter = 0;

export const usePreviewSessions = create<PreviewSessionState>((set) => ({
  sessions: {},
  order: [],
  open: (wallpapers) => {
    counter += 1;
    const key = `s${Date.now().toString(36)}${counter}`;
    set((state) => {
      const order = [...state.order, key];
      const sessions = { ...state.sessions, [key]: wallpapers.slice(0, 300) };
      while (order.length > 4) {
        const dropped = order.shift();
        if (dropped) delete sessions[dropped];
      }
      return { sessions, order };
    });
    return key;
  },
}));
