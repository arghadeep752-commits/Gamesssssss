import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { AppState, type AppStateStatus } from 'react-native';
import { configureAudio, setAudioAppActive } from '../services/audio';
import { configureHaptics } from '../services/haptics';
import { deleteSave, loadSave, writeSave } from '../storage/saveStorage';
import { defaultSave, type SaveData } from './saveSchema';

/**
 * Holds the one SaveData object for the whole app.
 *
 * - update():      commits a change, re-renders consumers and schedules a write.
 * - updateQuiet(): commits a change without re-rendering (used for the
 *                  in-progress puzzle snapshot after every move, which nothing
 *                  else on screen needs to react to).
 * Writes are debounced, serialised so they land in order, and flushed
 * immediately when the app goes to the background.
 */
interface StoreValue {
  readonly ready: boolean;
  readonly save: SaveData;
  getSave(): SaveData;
  update(fn: (s: SaveData) => SaveData): SaveData;
  updateQuiet(fn: (s: SaveData) => SaveData): void;
  /** Publishes quiet changes to React (call when leaving a screen that used updateQuiet). */
  sync(): void;
  flush(): Promise<void>;
  resetAll(): Promise<boolean>;
}

const StoreContext = createContext<StoreValue | null>(null);
const WRITE_DELAY_MS = 400;

function applySettings(save: SaveData) {
  configureAudio({ sfx: save.settings.sfx, music: save.settings.music });
  configureHaptics(save.settings.vibration);
}

export function GameStoreProvider({ children }: { children: React.ReactNode }) {
  const saveRef = useRef<SaveData>(defaultSave(Date.now()));
  const [save, setSave] = useState<SaveData>(saveRef.current);
  const [ready, setReady] = useState(false);
  const dirty = useRef(false);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const chain = useRef<Promise<unknown>>(Promise.resolve());
  const loaded = useRef(false);

  const flush = useCallback(async () => {
    if (timer.current) {
      clearTimeout(timer.current);
      timer.current = null;
    }
    if (!dirty.current || !loaded.current) return;
    dirty.current = false;
    const snapshot = saveRef.current;
    const job = chain.current.then(() => writeSave(snapshot));
    chain.current = job.catch(() => undefined);
    const ok = await job.catch(() => false);
    if (!ok) dirty.current = true; // retry on the next change or background event
  }, []);

  const schedule = useCallback(() => {
    dirty.current = true;
    if (timer.current) clearTimeout(timer.current);
    timer.current = setTimeout(() => {
      timer.current = null;
      void flush();
    }, WRITE_DELAY_MS);
  }, [flush]);

  useEffect(() => {
    let alive = true;
    loadSave().then(({ save: loadedSave }) => {
      if (!alive) return;
      saveRef.current = loadedSave;
      loaded.current = true;
      applySettings(loadedSave);
      setSave(loadedSave);
      setReady(true);
    });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    const onChange = (state: AppStateStatus) => {
      const active = state === 'active';
      setAudioAppActive(active);
      if (!active) void flush();
    };
    const sub = AppState.addEventListener('change', onChange);
    return () => {
      sub.remove();
      void flush();
    };
  }, [flush]);

  const update = useCallback(
    (fn: (s: SaveData) => SaveData) => {
      const prev = saveRef.current;
      const next = fn(prev);
      if (next === prev) return prev;
      saveRef.current = next;
      if (next.settings !== prev.settings) applySettings(next);
      setSave(next);
      schedule();
      return next;
    },
    [schedule],
  );

  const updateQuiet = useCallback(
    (fn: (s: SaveData) => SaveData) => {
      const prev = saveRef.current;
      const next = fn(prev);
      if (next === prev) return;
      saveRef.current = next;
      schedule();
    },
    [schedule],
  );

  const sync = useCallback(() => setSave(saveRef.current), []);
  const getSave = useCallback(() => saveRef.current, []);

  const resetAll = useCallback(async () => {
    if (timer.current) clearTimeout(timer.current);
    timer.current = null;
    dirty.current = false;
    await chain.current;
    const ok = await deleteSave();
    const fresh = defaultSave(Date.now());
    saveRef.current = fresh;
    applySettings(fresh);
    setSave(fresh);
    return ok;
  }, []);

  const value = useMemo<StoreValue>(
    () => ({ ready, save, getSave, update, updateQuiet, sync, flush, resetAll }),
    [ready, save, getSave, update, updateQuiet, sync, flush, resetAll],
  );
  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>;
}

export function useStore(): StoreValue {
  const ctx = useContext(StoreContext);
  if (!ctx) throw new Error('useStore must be used inside GameStoreProvider');
  return ctx;
}
