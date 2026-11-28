import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AppState } from 'react-native';
import { configureAudio } from '../services/audio';
import { configureHaptics } from '../services/haptics';
import { monthKeyOf, todayKey } from './dates';

export interface Settings {
  sound: boolean;
  music: boolean;
  haptics: boolean;
  dark: boolean;
}

export interface Save {
  v: 1;
  /** Next level to play (levels below it are cleared). */
  level: number;
  hints: number;
  /** Completed daily challenges, by date key. */
  daily: Record<string, number>;
  stats: { levels: number; perfect: number; daily: number };
  settings: Settings;
  /** Month of first launch; the trophy room starts here. */
  since: string;
  /** Has finished the first-run tutorial. */
  tutorial: boolean;
}

const KEY = 'arrowflow.save.v2';
export const START_HINTS = 3;

export function defaultSave(): Save {
  return {
    v: 1,
    level: 1,
    hints: START_HINTS,
    daily: {},
    stats: { levels: 0, perfect: 0, daily: 0 },
    settings: { sound: true, music: false, haptics: true, dark: false },
    since: monthKeyOf(todayKey()),
    tutorial: false,
  };
}

const num = (v: unknown, d: number, min = 0) => (typeof v === 'number' && Number.isFinite(v) && v >= min ? Math.floor(v) : d);
const bool = (v: unknown, d: boolean) => (typeof v === 'boolean' ? v : d);

/** Accepts anything and returns a valid save, keeping every field that makes sense. */
export function parseSave(text: string | null): Save {
  const base = defaultSave();
  if (!text) return base;
  try {
    const raw = JSON.parse(text) as Partial<Save> & Record<string, unknown>;
    const st = (raw.stats ?? {}) as Partial<Save['stats']>;
    const se = (raw.settings ?? {}) as Partial<Settings>;
    const daily: Record<string, number> = {};
    if (raw.daily && typeof raw.daily === 'object') {
      for (const [k, v] of Object.entries(raw.daily)) if (/^\d{4}-\d{2}-\d{2}$/.test(k) && v) daily[k] = 1;
    }
    return {
      v: 1,
      level: num(raw.level, 1, 1),
      hints: Math.min(999, num(raw.hints, START_HINTS)),
      daily,
      stats: { levels: num(st.levels, 0), perfect: num(st.perfect, 0), daily: num(st.daily, 0) },
      settings: {
        sound: bool(se.sound, true),
        music: bool(se.music, false),
        haptics: bool(se.haptics, true),
        dark: bool(se.dark, false),
      },
      since: typeof raw.since === 'string' && /^\d{4}-\d{2}$/.test(raw.since) ? raw.since : base.since,
      tutorial: bool(raw.tutorial, false),
    };
  } catch {
    return base;
  }
}

interface StoreValue {
  ready: boolean;
  save: Save;
  update: (fn: (s: Save) => Save) => void;
  reset: () => void;
}

const StoreContext = createContext<StoreValue | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [save, setSave] = useState<Save>(defaultSave);
  const [ready, setReady] = useState(false);
  const latest = useRef(save);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const flush = useCallback(() => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    AsyncStorage.setItem(KEY, JSON.stringify(latest.current)).catch(() => undefined);
  }, []);

  useEffect(() => {
    let alive = true;
    AsyncStorage.getItem(KEY)
      .catch(() => null)
      .then((text) => {
        if (!alive) return;
        const s = parseSave(text);
        latest.current = s;
        setSave(s);
        setReady(true);
      });
    const sub = AppState.addEventListener('change', (st) => {
      if (st !== 'active') flush();
    });
    return () => {
      alive = false;
      sub.remove();
    };
  }, [flush]);

  useEffect(() => {
    configureAudio({ sfx: save.settings.sound, music: save.settings.music });
    configureHaptics(save.settings.haptics);
  }, [save.settings.sound, save.settings.music, save.settings.haptics]);

  const update = useCallback(
    (fn: (s: Save) => Save) => {
      const next = fn(latest.current);
      latest.current = next;
      setSave(next);
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(flush, 400);
    },
    [flush],
  );

  const reset = useCallback(() => {
    const keep = latest.current.settings;
    update(() => ({ ...defaultSave(), settings: keep, tutorial: true }));
  }, [update]);

  const value = useMemo(() => ({ ready, save, update, reset }), [ready, save, update, reset]);
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const v = useContext(StoreContext);
  if (!v) throw new Error('useStore outside StoreProvider');
  return v;
}
