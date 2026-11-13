import { useCallback, useRef, useState } from 'react';

const LIMIT = 60;

/**
 * Undo/redo for editor state. `update(next)` changes the live value (for example while a ruler
 * is being dragged); `update(next, true)` also records it as a step.
 */
export function useHistory<T>(initial: T) {
  const [state, setState] = useState<T>(initial);
  const steps = useRef<T[]>([initial]);
  const [cursor, setCursor] = useState(0);
  const cursorRef = useRef(0);
  const latest = useRef(initial);

  const update = useCallback((next: T | ((prev: T) => T), commit = false) => {
    const value = typeof next === 'function' ? (next as (prev: T) => T)(latest.current) : next;
    latest.current = value;
    setState(value);
    if (commit) {
      if (JSON.stringify(value) === JSON.stringify(steps.current[cursorRef.current])) return;
      const kept = steps.current.slice(0, cursorRef.current + 1);
      kept.push(value);
      while (kept.length > LIMIT) kept.shift();
      steps.current = kept;
      cursorRef.current = kept.length - 1;
      setCursor(cursorRef.current);
    }
  }, []);

  /** Records the current live value as a step (after a drag ends). */
  const commit = useCallback(() => update(latest.current, true), [update]);

  const go = useCallback((delta: number) => {
    const i = cursorRef.current + delta;
    if (i < 0 || i >= steps.current.length) return;
    cursorRef.current = i;
    setCursor(i);
    latest.current = steps.current[i];
    setState(steps.current[i]);
  }, []);

  return {
    state,
    update,
    commit,
    undo: useCallback(() => go(-1), [go]),
    redo: useCallback(() => go(1), [go]),
    canUndo: cursor > 0,
    canRedo: cursor < steps.current.length - 1,
    dirty: cursor > 0,
  };
}
