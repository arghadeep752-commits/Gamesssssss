import { NavigationBar } from 'expo-navigation-bar';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { Component, useCallback, useEffect, useState, type ReactNode } from 'react';
import { AppState, BackHandler, StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import { DailyScreen } from '../screens/DailyScreen';
import { GameScreen, type GameRoute } from '../screens/GameScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { SettingsSheet } from '../screens/SettingsSheet';
import { TrophiesScreen } from '../screens/TrophiesScreen';
import { preloadSfx, releaseAudio, setAudioAppActive } from '../services/audio';
import { StoreProvider, useStore } from '../state/store';
import { Icon, type IconName } from '../ui/Icon';
import { Pressy } from '../ui/kit';
import { DARK, LIGHT, ThemeContext, useTheme } from '../ui/theme';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

type Tab = 'home' | 'daily' | 'trophies';
type Route = { name: 'tabs' } | { name: 'game'; game: GameRoute };

const TABS: { key: Tab; icon: IconName; label: string }[] = [
  { key: 'home', icon: 'home', label: 'Home' },
  { key: 'daily', icon: 'calendar', label: 'Daily' },
  { key: 'trophies', icon: 'trophy', label: 'Trophies' },
];

function TabBar({ tab, onTab }: { tab: Tab; onTab: (t: Tab) => void }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.tabBar, { backgroundColor: t.surface, borderTopColor: t.border, paddingBottom: insets.bottom + 6 }]}>
      {TABS.map((it) => {
        const on = it.key === tab;
        const color = on ? t.accent : t.faint;
        return (
          <Pressy key={it.key} onPress={() => onTab(it.key)} label={it.label} style={styles.tabItem} containerStyle={styles.fill}>
            <Icon name={it.icon} size={24} color={color} filled={on && it.key === 'trophies'} />
            <Text style={[styles.tabLabel, { color }]}>{it.label}</Text>
          </Pressy>
        );
      })}
    </View>
  );
}

function Root() {
  const { ready, save } = useStore();
  const palette = save.settings.dark ? DARK : LIGHT;
  const [tab, setTab] = useState<Tab>('home');
  const [route, setRoute] = useState<Route>({ name: 'tabs' });
  const [sheet, setSheet] = useState<false | 'settings'>(false);

  useEffect(() => {
    if (!ready) return;
    SplashScreen.hideAsync().catch(() => undefined);
    preloadSfx();
  }, [ready]);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (s) => setAudioAppActive(s === 'active'));
    return () => {
      sub.remove();
      releaseAudio();
    };
  }, []);

  useEffect(() => {
    const sub = BackHandler.addEventListener('hardwareBackPress', () => {
      if (sheet) {
        setSheet(false);
        return true;
      }
      if (route.name === 'game') {
        setRoute({ name: 'tabs' });
        return true;
      }
      if (tab !== 'home') {
        setTab('home');
        return true;
      }
      return false;
    });
    return () => sub.remove();
  }, [sheet, route, tab]);

  const openSettings = useCallback(() => setSheet('settings'), []);
  const closeSheet = useCallback(() => setSheet(false), []);
  const exitGame = useCallback(() => setRoute({ name: 'tabs' }), []);
  const playLevel = useCallback(() => setRoute({ name: 'game', game: { mode: 'level' } }), []);
  const playDaily = useCallback((dateKey: string) => setRoute({ name: 'game', game: { mode: 'daily', dateKey } }), []);

  return (
    <ThemeContext.Provider value={palette}>
      <StatusBar style={palette.dark ? 'light' : 'dark'} />
      <NavigationBar style={palette.dark ? 'light' : 'dark'} />
      <View style={[styles.fill, { backgroundColor: palette.bg }]}>
        {!ready ? null : route.name === 'game' ? (
          <GameScreen route={route.game} onExit={exitGame} onOpenSettings={openSettings} />
        ) : (
          <>
            <View style={styles.fill}>
              {tab === 'home' ? (
                <HomeScreen onPlay={playLevel} onDaily={() => setTab('daily')} onSettings={openSettings} />
              ) : tab === 'daily' ? (
                <DailyScreen onPlay={playDaily} />
              ) : (
                <TrophiesScreen />
              )}
            </View>
            <TabBar tab={tab} onTab={setTab} />
          </>
        )}
        {sheet ? <SettingsSheet onClose={closeSheet} /> : null}
      </View>
    </ThemeContext.Provider>
  );
}

/** Last line of defence: show a recoverable screen instead of crashing to the launcher. */
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null; attempt: number }> {
  state = { error: null as Error | null, attempt: 0 };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return (
        <View style={styles.error}>
          <Text style={styles.errorTitle}>Something went wrong</Text>
          <Text style={styles.errorText}>Your progress is saved. Tap below to go back to the game.</Text>
          <Text style={styles.errorBtn} onPress={() => this.setState((s) => ({ error: null, attempt: s.attempt + 1 }))}>
            Back to the game
          </Text>
        </View>
      );
    }
    return (
      <View key={this.state.attempt} style={styles.fill}>
        {this.props.children}
      </View>
    );
  }
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ErrorBoundary>
        <StoreProvider>
          <Root />
        </StoreProvider>
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  tabBar: { flexDirection: 'row', borderTopWidth: 1, paddingTop: 8 },
  tabItem: { alignItems: 'center', gap: 2, paddingVertical: 2 },
  tabLabel: { fontSize: 12, fontWeight: '700' },
  error: { flex: 1, backgroundColor: LIGHT.bg, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 14 },
  errorTitle: { fontSize: 22, fontWeight: '800', color: LIGHT.text },
  errorText: { fontSize: 16, color: LIGHT.sub, textAlign: 'center' },
  errorBtn: { fontSize: 17, fontWeight: '800', color: LIGHT.accent, padding: 12 },
});
