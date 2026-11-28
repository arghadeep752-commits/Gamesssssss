import AsyncStorage from '@react-native-async-storage/async-storage';
import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AppState } from 'react-native';
import { configureAudio } from '../services/audio';
import { configureHaptics } from '../services/haptics';
import { monthKeyOf, todayKey } from './dates';
import { START_COINS, START_HINTS } from './economy';

export interface Settings {
  sound: boolean;
  haptics: boolean;
  dark: boolean;
  /** Thinner arrow lines (easier to read on very dense boards). */
  thin: boolean;
  /** Show cell grid lines on the board. */
  grid: boolean;
}

export interface Save {
  v: 3;
  /** Next level to play (levels below it are cleared). */
  level: number;
  hints: number;
  coins: number;
  /** Completed daily challenges, by date key. */
  daily: Record<string, number>;
  stats: { levels: number; perfect: number; daily: number; stars: number; arrows: number; bestStreak: number };
  /** Collection: how many times each outline has been cleared. */
  shapes: Record<string, number>;
  skin: string;
  skins: string[];
  settings: Settings;
  /** Month of first launch; the trophy room starts here. */
  since: string;
  /** Has finished the first-run tutorial. */
  tutorial: boolean;
  /** Daily login reward: last claim date and streak day (1..7). */
  login: { last: string; day: number };
  /** Level clears toward the next reward chest. */
  chest: number;
}

const KEY = 'arrowflow.save.v3';

export function defaultSave(): Save {
  return {
    v: 3,
    level: 1,
    hints: START_HINTS,
    coins: START_COINS,
    daily: {},
    stats: { levels: 0, perfect: 0, daily: 0, stars: 0, arrows: 0, bestStreak: 0 },
    shapes: {},
    skin: 'classic',
    skins: ['classic'],
    settings: { sound: true, haptics: true, dark: false, thin: false, grid: false },
    since: monthKeyOf(todayKey()),
    tutorial: false,
    login: { last: '', day: 0 },
    chest: 0,
  };
}

const num = (v: unknown, d: number, min = 0, max = 1e9) =>
  typeof v === 'number' && Number.isFinite(v) && v >= min ? Math.min(max, Math.floor(v)) : d;
const bool = (v: unknown, d: boolean) => (typeof v === 'boolean' ? v : d);
const str = (v: unknown, d: string) => (typeof v === 'string' ? v : d);

/** Accepts anything and returns a valid save, keeping every field that makes sense. */
export function parseSave(text: string | null): Save {
  const base = defaultSave();
  if (!text) return base;
  try {
    const raw = JSON.parse(text) as Record<string, unknown>;
    const st = (raw.stats ?? {}) as Record<string, unknown>;
    const se = (raw.settings ?? {}) as Record<string, unknown>;
    const lg = (raw.login ?? {}) as Record<string, unknown>;
    const daily: Record<string, number> = {};
    if (raw.daily && typeof raw.daily === 'object') {
      for (const [k, v] of Object.entries(raw.daily as Record<string, unknown>)) if (/^\d{4}-\d{2}-\d{2}$/.test(k) && v) daily[k] = 1;
    }
    const shapes: Record<string, number> = {};
    if (raw.shapes && typeof raw.shapes === 'object') {
      for (const [k, v] of Object.entries(raw.shapes as Record<string, unknown>)) {
        const n = num(v, 0);
        if (n > 0 && k.length < 40) shapes[k] = n;
      }
    }
    const skins = Array.isArray(raw.skins) ? (raw.skins as unknown[]).filter((s): s is string => typeof s === 'string') : [];
    if (!skins.includes('classic')) skins.unshift('classic');
    const skin = str(raw.skin, 'classic');
    return {
      v: 3,
      level: num(raw.level, 1, 1),
      hints: num(raw.hints, START_HINTS, 0, 999),
      coins: num(raw.coins, START_COINS, 0, 9_999_999),
      daily,
      stats: {
        levels: num(st.levels, 0),
        perfect: num(st.perfect, 0),
        daily: num(st.daily, 0),
        stars: num(st.stars, 0),
        arrows: num(st.arrows, 0),
        bestStreak: num(st.bestStreak, 0),
      },
      shapes,
      skin: skins.includes(skin) ? skin : 'classic',
      skins,
      settings: {
        sound: bool(se.sound, true),
        haptics: bool(se.haptics, true),
        dark: bool(se.dark, false),
        thin: bool(se.thin, false),
        grid: bool(se.grid, false),
      },
      since: typeof raw.since === 'string' && /^\d{4}-\d{2}$/.test(raw.since) ? raw.since : base.since,
      tutorial: bool(raw.tutorial, false),
      login: { last: str(lg.last, ''), day: num(lg.day, 0, 0, 7) },
      chest: num(raw.chest, 0, 0, 100),
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
    configureAudio({ sfx: save.settings.sound });
    configureHaptics(save.settings.haptics);
  }, [save.settings.sound, save.settings.haptics]);

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
