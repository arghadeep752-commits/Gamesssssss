import { useNavigation, type NavigationAction } from '@react-navigation/native';
import { useCallback, useEffect, useRef, useState } from 'react';

type Action = NavigationAction;

/**
 * Asks before leaving a screen with unsaved work. Covers the back button, the back gesture and
 * the close button alike, since they all remove the screen.
 */
export function useGuard(active: boolean) {
  const nav = useNavigation();
  const [asking, setAsking] = useState(false);
  const pending = useRef<Action | null>(null);
  const released = useRef(false);

  useEffect(
    () =>
      nav.addListener('beforeRemove', (e) => {
        if (released.current || !active) return;
        e.preventDefault();
        pending.current = e.data.action;
        setAsking(true);
      }),
    [nav, active]
  );

  /** Lets the next navigation through without asking (after saving). */
  const release = useCallback(() => {
    released.current = true;
  }, []);

  const leave = useCallback(() => {
    released.current = true;
    setAsking(false);
    if (pending.current) nav.dispatch(pending.current);
  }, [nav]);

  const stay = useCallback(() => {
    pending.current = null;
    setAsking(false);
  }, []);

  return { asking, release, leave, stay };
}
