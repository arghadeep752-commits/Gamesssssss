/**
 * Calc Pro — main screen.
 *
 * Portrait: history card, display, optional scientific keys, basic keys.
 * Landscape: display above scientific + basic keys side by side.
 * Everything floats as frosted glass over pools of colored light.
 *
 * Performance notes (the app has to stay smooth on low-end phones):
 * - a key press re-renders only the display and the keys whose state
 *   changed: metrics, callbacks and derived props are all memoized;
 * - the portrait scientific keys stay mounted while hidden, so showing them
 *   never has to build twenty keys in the middle of an animation;
 * - every animation except the scientific block's height (a layout change)
 *   runs on the native driver.
 */
import React, {
  useCallback,
  useEffect,
  useMemo,
  useReducer,
  useRef,
  useState,
} from 'react';
import {
  Animated,
  Appearance,
  Clipboard,
  Easing,
  StatusBar,
  StyleSheet,
  View,
  useColorScheme,
} from 'react-native';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';
import { Display } from './components/Display';
import { History } from './components/History';
import { BasicPad, SciPad } from './components/Keypad';
import { LiquidBackground } from './components/LiquidBackground';
import { SettingsSheet } from './components/SettingsSheet';
import { Toast, ToastMessage } from './components/Toast';
import { TopBar } from './components/TopBar';
import {
  ERROR_TEXT,
  Notice,
  Token,
  evaluate,
  expressionText,
  formatCanonical,
  hasOperation,
  plainText,
  spokenExpression,
  toCanonical,
  trimForEval,
} from './engine';
import { KEYPAD_PAD, useLayoutMetrics } from './hooks/useLayoutMetrics';
import { useReduceMotion } from './hooks/useReduceMotion';
import { loadAppState, reducer } from './state/calcReducer';
import type { KeyId } from './state/keys';
import { Settings, loadSettings, saveSettings } from './state/settings';
import { KEYS, haptic, windowReady, writeJSON } from './state/storage';
import { ThemeProvider, buildPalette } from './theme/theme';

const NOTICE_TEXT: Record<Notice, string> = {
  'max-digits': 'Numbers can have up to 15 digits',
  'max-length': 'This expression is at its maximum length',
};

const OP_KEY: Record<string, KeyId> = {
  '+': 'add',
  '-': 'sub',
  '*': 'mul',
  '/': 'div',
  '^': 'pow',
};

const NO_INDICATORS: string[] = [];

/** The operator still waiting for its second operand, if any. */
function pendingOperator(tokens: Token[]): KeyId | null {
  let i = tokens.length - 1;
  if (tokens[i]?.t === 'neg') {
    i--;
  }
  const tk = tokens[i];
  return tk?.t === 'op' ? OP_KEY[tk.v] : null;
}

function Calculator() {
  const insets = useSafeAreaInsets();
  const systemScheme = useColorScheme();
  const reduceMotion = useReduceMotion();
  const [settings, setSettings] = useState<Settings>(loadSettings);
  const [app, dispatch] = useReducer(reducer, undefined, loadAppState);
  const [second, setSecond] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [toast, setToast] = useState<ToastMessage | null>(null);

  const settingsRef = useRef(settings);
  settingsRef.current = settings;

  const scheme =
    settings.theme === 'system'
      ? systemScheme === 'dark'
        ? 'dark'
        : 'light'
      : settings.theme;
  const palette = useMemo(
    () => buildPalette(settings.palette, scheme),
    [settings.palette, scheme],
  );
  const m = useLayoutMetrics(settings.sci);
  // The portrait scientific keys always use their open-state size, so they
  // never re-render when they are shown or hidden.
  const mOpen = useLayoutMetrics(true);
  const sciMetrics = m.landscape ? m : mOpen;
  const sciVisible = m.landscape || settings.sci;

  // Showing the scientific keys grows their block (JS driver, since it is a
  // layout change the history and display follow) while the keys themselves
  // fade and rise on the native driver.
  const [sciHeight] = useState(() => new Animated.Value(settings.sci ? 1 : 0));
  const [sciFade] = useState(() => new Animated.Value(settings.sci ? 1 : 0));
  const sciBlockStyle = useMemo(
    () => ({
      height: sciHeight.interpolate({
        inputRange: [0, 1],
        outputRange: [0, mOpen.sciBlock],
      }),
    }),
    [sciHeight, mOpen.sciBlock],
  );
  const sciKeysStyle = useMemo(
    () => ({
      paddingBottom: mOpen.blockGap,
      opacity: sciFade,
      transform: [
        {
          translateY: sciFade.interpolate({
            inputRange: [0, 1],
            outputRange: [18, 0],
          }),
        },
        {
          scale: sciFade.interpolate({
            inputRange: [0, 1],
            outputRange: [0.96, 1],
          }),
        },
      ],
    }),
    [sciFade, mOpen.blockGap],
  );

  // Persistence
  useEffect(() => saveSettings(settings), [settings]);
  useEffect(() => writeJSON(KEYS.tape, app.tape), [app.tape]);
  useEffect(() => {
    const t = setTimeout(
      () =>
        writeJSON(KEYS.session, {
          tokens: app.calc.tokens,
          justEvaluated: app.calc.justEvaluated,
        }),
      300,
    );
    return () => clearTimeout(t);
  }, [app.calc]);

  // Once the first frames are on screen the app paints its own background,
  // so the window's copy underneath (a full-screen fill on every frame) can
  // go.
  useEffect(() => {
    const t = setTimeout(windowReady, 700);
    return () => clearTimeout(t);
  }, []);

  // The in-app theme also switches the Android window theme (system bars).
  useEffect(() => {
    try {
      Appearance.setColorScheme(
        settings.theme === 'system' ? 'auto' : settings.theme,
      );
    } catch {
      // Not available on every platform.
    }
  }, [settings.theme]);

  const showToast = useCallback((text: string) => {
    setToast(prev => ({ text, seq: (prev?.seq ?? 0) + 1 }));
  }, []);

  useEffect(() => {
    if (app.notice) {
      showToast(NOTICE_TEXT[app.notice.kind]);
    }
  }, [app.notice, showToast]);

  const onKey = useCallback((id: KeyId) => {
    const s = settingsRef.current;
    if (s.haptics) {
      haptic(id === 'eq' ? 'confirm' : 'tap');
    }
    if (id === 'second') {
      setSecond(v => !v);
      return;
    }
    if (id === 'angle') {
      setSettings(prev => ({
        ...prev,
        angle: prev.angle === 'deg' ? 'rad' : 'deg',
      }));
      return;
    }
    dispatch({ type: 'key', key: id, angle: s.angle });
  }, []);

  const onLongKey = useCallback((id: KeyId) => {
    if (id !== 'back') {
      return;
    }
    if (settingsRef.current.haptics) {
      haptic('long');
    }
    dispatch({ type: 'key', key: 'ac', angle: settingsRef.current.angle });
  }, []);

  const onSwipeDelete = useCallback(() => {
    if (settingsRef.current.haptics) {
      haptic('tap');
    }
    dispatch({ type: 'key', key: 'back', angle: settingsRef.current.angle });
  }, []);

  const toggleSci = useCallback(() => {
    const open = !settingsRef.current.sci;
    if (settingsRef.current.haptics) {
      haptic('tap');
    }
    setSettings(prev => ({ ...prev, sci: open }));
    const fast = reduceMotion;
    Animated.parallel([
      Animated.timing(sciHeight, {
        toValue: open ? 1 : 0,
        duration: fast ? 0 : 300,
        easing: Easing.bezier(0.2, 0.9, 0.25, 1),
        useNativeDriver: false,
      }),
      Animated.timing(sciFade, {
        toValue: open ? 1 : 0,
        duration: fast ? 0 : open ? 320 : 150,
        delay: open && !fast ? 60 : 0,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();
  }, [reduceMotion, sciHeight, sciFade]);

  const openSettings = useCallback(() => setSettingsOpen(true), []);
  const closeSettings = useCallback(() => setSettingsOpen(false), []);

  const changeSettings = useCallback((patch: Partial<Settings>) => {
    setSettings(prev => ({ ...prev, ...patch }));
  }, []);

  const copyCanonical = useCallback(
    (canonical: string) => {
      Clipboard.setString(plainText(canonical));
      if (settingsRef.current.haptics) {
        haptic('long');
      }
      showToast(
        `Copied ${formatCanonical(canonical, settingsRef.current.grouping)}`,
      );
    },
    [showToast],
  );

  const reuseValue = useCallback((canonical: string) => {
    if (settingsRef.current.haptics) {
      haptic('tap');
    }
    dispatch({ type: 'insert', value: canonical });
  }, []);

  const clearHistory = useCallback(() => {
    dispatch({ type: 'clearTape' });
    showToast('History cleared');
  }, [showToast]);

  // Derived display state
  const { calc } = app;
  const expr = useMemo(
    () => expressionText(calc.tokens, settings.grouping),
    [calc.tokens, settings.grouping],
  );
  const previewValue = useMemo(() => {
    if (
      calc.justEvaluated ||
      calc.error ||
      !hasOperation(trimForEval(calc.tokens))
    ) {
      return null;
    }
    try {
      return evaluate(calc.tokens, settings.angle);
    } catch {
      return null;
    }
  }, [calc, settings.angle]);
  const preview =
    previewValue === null
      ? null
      : formatCanonical(toCanonical(previewValue), settings.grouping);
  const activeKey = calc.justEvaluated ? null : pendingOperator(calc.tokens);

  const copyCurrent = useCallback(() => {
    try {
      if (calc.tokens.length > 0) {
        copyCanonical(toCanonical(evaluate(calc.tokens, settings.angle)));
      }
    } catch {
      // Nothing to copy for an incomplete expression.
    }
  }, [calc.tokens, settings.angle, copyCanonical]);

  const errorText = calc.error ? ERROR_TEXT[calc.error] : null;
  const spoken = errorText
    ? `${spokenExpression(calc.tokens, settings.grouping)}. ${errorText}`
    : `${spokenExpression(calc.tokens, settings.grouping) || '0'}${
        preview ? `, equals ${preview}` : ''
      }`;
  const indicators = useMemo(
    () =>
      sciVisible
        ? [settings.angle === 'deg' ? 'DEG' : 'RAD', ...(second ? ['2nd'] : [])]
        : NO_INDICATORS,
    [sciVisible, settings.angle, second],
  );

  const display = (
    <Display
      text={expr.text}
      ghost={expr.ghost}
      preview={preview}
      error={errorText}
      indicators={indicators}
      maxFont={m.displayFont}
      minFont={m.landscape ? 22 : 30}
      previewFont={m.landscape ? 22 : 28}
      resultSeq={app.resultSeq}
      spoken={spoken}
      still={reduceMotion}
      onCopy={copyCurrent}
      onSwipe={onSwipeDelete}
    />
  );

  const sciPad = (
    <SciPad
      m={sciMetrics}
      second={second}
      angle={settings.angle}
      activeKey={activeKey}
      still={reduceMotion}
      onKey={onKey}
    />
  );

  return (
    <ThemeProvider palette={palette}>
      <StatusBar
        barStyle={scheme === 'dark' ? 'light-content' : 'dark-content'}
      />
      <View
        style={[
          styles.root,
          {
            paddingTop: insets.top,
            paddingBottom: insets.bottom,
            paddingLeft: insets.left,
            paddingRight: insets.right,
          },
        ]}
      >
        <LiquidBackground width={m.width} height={m.height} />
        <View style={[styles.content, { width: m.contentWidth }]}>
          <TopBar
            height={m.topBar}
            showTitle={!m.landscape}
            showSciToggle={!m.landscape}
            sciOpen={settings.sci}
            still={reduceMotion}
            onToggleSci={toggleSci}
            onOpenSettings={openSettings}
          />
          {m.landscape ? (
            <View style={styles.landscapeDisplay}>{display}</View>
          ) : (
            <>
              {m.showHistory ? (
                <History
                  entries={app.tape}
                  grouping={settings.grouping}
                  still={reduceMotion}
                  onUse={reuseValue}
                  onCopy={copyCanonical}
                />
              ) : (
                <View style={styles.spacer} />
              )}
              {display}
            </>
          )}
          <View
            style={[
              { paddingHorizontal: m.pad, paddingBottom: KEYPAD_PAD },
              m.landscape ? styles.keysLandscape : null,
            ]}
          >
            {m.landscape ? (
              <View style={{ marginRight: m.blockGap }}>{sciPad}</View>
            ) : (
              <Animated.View
                style={[styles.sciClip, sciBlockStyle]}
                importantForAccessibility={
                  settings.sci ? 'auto' : 'no-hide-descendants'
                }
                accessibilityElementsHidden={!settings.sci}
              >
                <Animated.View style={sciKeysStyle}>{sciPad}</Animated.View>
              </Animated.View>
            )}
            <BasicPad
              m={m}
              activeKey={activeKey}
              still={reduceMotion}
              onKey={onKey}
              onLongKey={onLongKey}
            />
          </View>
        </View>
        <Toast message={toast} bottom={insets.bottom + m.keypadHeight + 12} />
        <SettingsSheet
          visible={settingsOpen}
          settings={settings}
          historyCount={app.tape.length}
          still={reduceMotion}
          onChange={changeSettings}
          onClearHistory={clearHistory}
          onClose={closeSettings}
        />
      </View>
    </ThemeProvider>
  );
}

export default function App() {
  return (
    <SafeAreaProvider>
      <Calculator />
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    alignItems: 'center',
  },
  content: {
    flex: 1,
  },
  landscapeDisplay: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  keysLandscape: {
    flexDirection: 'row',
    justifyContent: 'center',
  },
  sciClip: {
    overflow: 'hidden',
    justifyContent: 'flex-end',
  },
  spacer: {
    flex: 1,
  },
});
