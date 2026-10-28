import React, { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react';
import { BackHandler, StyleSheet, View } from 'react-native';

/**
 * A deliberately tiny stack navigator. The game has a dozen simple screens, so
 * this avoids shipping a navigation library. Screens below the top stay
 * mounted (hidden) so the game keeps its exact state while Settings is open.
 */
export type LegalDocName = 'privacy' | 'terms' | 'about';

export type Route =
  | { name: 'home' }
  | { name: 'daily' }
  | { name: 'me' }
  | { name: 'levels' }
  | { name: 'game'; mode: 'level'; level: number }
  | { name: 'game'; mode: 'daily'; dateKey: string }
  | { name: 'achievements' }
  | { name: 'settings' }
  | { name: 'help' }
  | { name: 'legal'; doc: LegalDocName }
  | { name: 'privacy' };

export type TabName = 'home' | 'daily' | 'me';

interface Entry {
  readonly key: number;
  readonly route: Route;
}

interface NavValue {
  readonly stack: readonly Entry[];
  push(route: Route): void;
  pop(): void;
  replace(route: Route): void;
  /** Clears the stack down to a single root screen (used by the tab bar and "Home"). */
  resetTo(route: Route): void;
  /** Registers a back-button handler for one screen; only the top screen's handler runs. */
  setBackInterceptor(key: number, handler: (() => boolean) | null): void;
}

const NavContext = createContext<NavValue | null>(null);
const ScreenKeyContext = createContext<{ key: number; isTop: boolean }>({ key: -1, isTop: true });

let nextKey = 1;
const entry = (route: Route): Entry => ({ key: nextKey++, route });

export function NavigationProvider({
  initial,
  render,
}: {
  initial: Route;
  render: (route: Route) => React.ReactNode;
}) {
  const [stack, setStack] = useState<Entry[]>(() => [entry(initial)]);
  const stackRef = useRef(stack);
  stackRef.current = stack;
  const interceptors = useRef(new Map<number, () => boolean>());

  const push = useCallback((route: Route) => setStack((s) => [...s, entry(route)]), []);
  const pop = useCallback(() => setStack((s) => (s.length > 1 ? s.slice(0, -1) : s)), []);
  const replace = useCallback((route: Route) => setStack((s) => [...s.slice(0, -1), entry(route)]), []);
  const resetTo = useCallback((route: Route) => setStack([entry(route)]), []);
  const setBackInterceptor = useCallback((key: number, handler: (() => boolean) | null) => {
    if (handler) interceptors.current.set(key, handler);
    else interceptors.current.delete(key);
  }, []);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      const s = stackRef.current;
      const top = s[s.length - 1];
      const intercept = interceptors.current.get(top.key);
      if (intercept && intercept()) return true;
      if (s.length > 1) {
        setStack(s.slice(0, -1));
        return true;
      }
      if (top.route.name !== 'home') {
        setStack([entry({ name: 'home' })]);
        return true;
      }
      return false; // let Android close the app
    });
    return () => sub.remove();
  }, []);

  const value = useMemo<NavValue>(
    () => ({ stack, push, pop, replace, resetTo, setBackInterceptor }),
    [stack, push, pop, replace, resetTo, setBackInterceptor],
  );

  return (
    <NavContext.Provider value={value}>
      <View style={styles.fill}>
        {stack.map((e, i) => {
          const isTop = i === stack.length - 1;
          return (
            <View key={e.key} style={[styles.fill, !isTop && styles.hidden]} pointerEvents={isTop ? 'auto' : 'none'}>
              <ScreenKeyContext.Provider value={{ key: e.key, isTop }}>{render(e.route)}</ScreenKeyContext.Provider>
            </View>
          );
        })}
      </View>
    </NavContext.Provider>
  );
}

export function useNav(): NavValue {
  const ctx = useContext(NavContext);
  if (!ctx) throw new Error('useNav must be used inside NavigationProvider');
  return ctx;
}

export function useIsTopScreen(): boolean {
  return useContext(ScreenKeyContext).isTop;
}

/** Handle the Android back button on this screen; return true to consume it. */
export function useBackHandler(handler: () => boolean): void {
  const { key } = useContext(ScreenKeyContext);
  const nav = useNav();
  const ref = useRef(handler);
  ref.current = handler;
  useEffect(() => {
    nav.setBackInterceptor(key, () => ref.current());
    return () => nav.setBackInterceptor(key, null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, nav.setBackInterceptor]);
}

const styles = StyleSheet.create({
  fill: { position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 },
  hidden: { display: 'none' },
});
