/**
 * Calc Pro — main screen.
 *
 * Portrait: history card, display, optional scientific keys, basic keys.
 * Landscape: display above scientific + basic keys side by side.
 * Everything floats as frosted glass over the drifting liquid background.
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
import { useLayoutMetrics } from './hooks/useLayoutMetrics';
import { useReduceMotion } from './hooks/useReduceMotion';
import { loadAppState, reducer } from './state/calcReducer';
import type { KeyId } from './state/keys';
import { Settings, loadSettings, saveSettings } from './state/settings';
import { KEYS, haptic, writeJSON } from './state/storage';
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

  // Scientific keys (portrait): the block's height follows the JS driver,
  // its keys fade and rise on the native driver.
  const [sciMounted, setSciMounted] = useState(settings.sci);
  const sciHeight = useRef(new Animated.Value(settings.sci ? 1 : 0)).current;
  const sciFade = useRef(new Animated.Value(settings.sci ? 1 : 0)).current;
  const sciVisible = m.landscape || sciMounted;

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
    if (open) {
      setSciMounted(true);
    }
    const fast = reduceMotion;
    Animated.parallel([
      Animated.timing(sciHeight, {
        toValue: open ? 1 : 0,
        duration: fast ? 0 : 320,
        easing: Easing.bezier(0.2, 0.9, 0.25, 1),
        useNativeDriver: false,
      }),
      Animated.timing(sciFade, {
        toValue: open ? 1 : 0,
        duration: fast ? 0 : open ? 340 : 160,
        delay: open && !fast ? 70 : 0,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start(({ finished }) => {
      if (finished && !open) {
        setSciMounted(false);
      }
    });
  }, [reduceMotion, sciHeight, sciFade]);

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
  const indicators = sciVisible
    ? [settings.angle === 'deg' ? 'DEG' : 'RAD', ...(second ? ['2nd'] : [])]
    : [];

  const keypadHeight =
    m.keyH * 5 +
    m.gap * 4 +
    14 +
    (!m.landscape && settings.sci ? m.sciBlock : 0);

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
      m={m}
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
            backgroundColor: palette.base,
            paddingTop: insets.top,
            paddingBottom: insets.bottom,
            paddingLeft: insets.left,
            paddingRight: insets.right,
          },
        ]}
      >
        <LiquidBackground
          width={m.width}
          height={m.height}
          still={reduceMotion}
        />
        <View style={[styles.content, { width: m.contentWidth }]}>
          <TopBar
            height={m.topBar}
            showTitle={!m.landscape}
            showSciToggle={!m.landscape}
            sciOpen={settings.sci}
            still={reduceMotion}
            onToggleSci={toggleSci}
            onOpenSettings={() => setSettingsOpen(true)}
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
              { paddingHorizontal: m.pad, paddingBottom: 14 },
              m.landscape ? styles.keysLandscape : null,
            ]}
          >
            {m.landscape ? (
              <View style={{ marginRight: m.blockGap }}>{sciPad}</View>
            ) : sciMounted ? (
              <Animated.View
                style={[
                  styles.sciClip,
                  {
                    height: sciHeight.interpolate({
                      inputRange: [0, 1],
                      outputRange: [0, m.sciBlock],
                    }),
                  },
                ]}
              >
                <Animated.View
                  style={{
                    paddingBottom: m.blockGap,
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
                  }}
                >
                  {sciPad}
                </Animated.View>
              </Animated.View>
            ) : null}
            <BasicPad
              m={m}
              activeKey={activeKey}
              still={reduceMotion}
              onKey={onKey}
              onLongKey={onLongKey}
            />
          </View>
        </View>
        <Toast message={toast} bottom={insets.bottom + keypadHeight + 12} />
        <SettingsSheet
          visible={settingsOpen}
          settings={settings}
          historyCount={app.tape.length}
          still={reduceMotion}
          onChange={changeSettings}
          onClearHistory={clearHistory}
          onClose={() => setSettingsOpen(false)}
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
