import { NavigationBar } from 'expo-navigation-bar';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { Component, useCallback, useEffect, useRef, useState, type ReactNode } from 'react';
import { AppState, BackHandler, Linking, StyleSheet, Text, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider, useSafeAreaInsets } from 'react-native-safe-area-context';
import type { LegalId } from '../legal/docs';
import { CollectionScreen } from '../screens/CollectionScreen';
import { DailyScreen } from '../screens/DailyScreen';
import { GameScreen, type GameRoute } from '../screens/GameScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { LegalScreen } from '../screens/LegalScreen';
import { RewardSheet } from '../screens/RewardSheet';
import { SettingsSheet } from '../screens/SettingsSheet';
import { ShopSheet } from '../screens/ShopSheet';
import { TrophiesScreen } from '../screens/TrophiesScreen';
import { preloadSfx, releaseAudio, setAudioAppActive } from '../services/audio';
import { todayKey } from '../state/dates';
import { loginReward } from '../state/economy';
import { StoreProvider, useStore } from '../state/store';
import { Icon, type IconName } from '../ui/Icon';
import { Pressy } from '../ui/kit';
import { DARK, LIGHT, ThemeContext, useTheme } from '../ui/theme';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

type Tab = 'home' | 'daily' | 'collection' | 'trophies';
type Route = { name: 'tabs' } | { name: 'game'; game: GameRoute } | { name: 'legal'; doc: LegalId; back: 'tabs' | 'game' };
type SheetName = 'settings' | 'shop' | 'reward' | null;

const TABS: { key: Tab; icon: IconName; label: string }[] = [
  { key: 'home', icon: 'home', label: 'Home' },
  { key: 'daily', icon: 'calendar', label: 'Daily' },
  { key: 'collection', icon: 'shapes', label: 'Collection' },
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
  const [sheet, setSheet] = useState<SheetName>(null);
  const lastGame = useRef<GameRoute | null>(null);
  const rewardShown = useRef(false);

  useEffect(() => {
    if (!ready) return;
    SplashScreen.hideAsync().catch(() => undefined);
    preloadSfx();
    // Offer the daily login reward once per launch.
    if (!rewardShown.current && loginReward(save.login.last, save.login.day, todayKey()).available) {
      rewardShown.current = true;
      setTimeout(() => setSheet((s) => s ?? 'reward'), 700);
    }
  }, [ready, save.login.last, save.login.day]);

  // QA builds only (EXPO_PUBLIC_QA=1 at build time): arrowflow://qa?level=N opens level N,
  // so automated tests can check big boards. Store builds ignore these links.
  useEffect(() => {
    if (process.env.EXPO_PUBLIC_QA !== '1' || !ready) return;
    const open = (url: string | null) => {
      const m = url ? /level=(\d+)/.exec(url) : null;
      if (m) {
        setSheet(null);
        setRoute({ name: 'game', game: { mode: 'level', start: Math.max(1, Number(m[1])) } });
      }
    };
    Linking.getInitialURL().then(open).catch(() => undefined);
    const sub = Linking.addEventListener('url', (e) => open(e.url));
    return () => sub.remove();
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
        setSheet(null);
        return true;
      }
      if (route.name === 'legal') {
        setRoute(route.back === 'game' && lastGame.current ? { name: 'game', game: lastGame.current } : { name: 'tabs' });
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
  const openShop = useCallback(() => setSheet('shop'), []);
  const closeSheet = useCallback(() => setSheet(null), []);
  const exitGame = useCallback(() => setRoute({ name: 'tabs' }), []);
  const playLevel = useCallback(() => {
    const g: GameRoute = { mode: 'level' };
    lastGame.current = g;
    setRoute({ name: 'game', game: g });
  }, []);
  const playDaily = useCallback((dateKey: string) => {
    const g: GameRoute = { mode: 'daily', dateKey };
    lastGame.current = g;
    setRoute({ name: 'game', game: g });
  }, []);
  const openLegal = useCallback(
    (doc: LegalId) => {
      setSheet(null);
      setRoute({ name: 'legal', doc, back: route.name === 'game' ? 'game' : 'tabs' });
    },
    [route.name],
  );
  const closeLegal = useCallback(() => {
    setRoute((r) => (r.name === 'legal' && r.back === 'game' && lastGame.current ? { name: 'game', game: lastGame.current } : { name: 'tabs' }));
  }, []);

  return (
    <ThemeContext.Provider value={palette}>
      <StatusBar style={palette.dark ? 'light' : 'dark'} />
      <NavigationBar style={palette.dark ? 'light' : 'dark'} />
      <View style={[styles.fill, { backgroundColor: palette.bg }]}>
        {!ready ? null : route.name === 'game' ? (
          <GameScreen route={route.game} onExit={exitGame} onOpenSettings={openSettings} />
        ) : route.name === 'legal' ? (
          <LegalScreen doc={route.doc} onBack={closeLegal} />
        ) : (
          <>
            <View style={styles.fill}>
              {tab === 'home' ? (
                <HomeScreen onPlay={playLevel} onDaily={() => setTab('daily')} onSettings={openSettings} onShop={openShop} />
              ) : tab === 'daily' ? (
                <DailyScreen onPlay={playDaily} />
              ) : tab === 'collection' ? (
                <CollectionScreen />
              ) : (
                <TrophiesScreen />
              )}
            </View>
            <TabBar tab={tab} onTab={setTab} />
          </>
        )}
        {sheet === 'settings' ? <SettingsSheet onClose={closeSheet} onLegal={openLegal} /> : null}
        {sheet === 'shop' ? <ShopSheet onClose={closeSheet} /> : null}
        {sheet === 'reward' ? <RewardSheet onClose={closeSheet} /> : null}
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
    <GestureHandlerRootView style={styles.fill}>
      <SafeAreaProvider>
        <ErrorBoundary>
          <StoreProvider>
            <Root />
          </StoreProvider>
        </ErrorBoundary>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  tabBar: { flexDirection: 'row', borderTopWidth: 1, paddingTop: 8 },
  tabItem: { alignItems: 'center', gap: 2, paddingVertical: 2 },
  tabLabel: { fontSize: 11, fontWeight: '700' },
  error: { flex: 1, backgroundColor: LIGHT.bg, alignItems: 'center', justifyContent: 'center', padding: 32, gap: 14 },
  errorTitle: { fontSize: 22, fontWeight: '800', color: LIGHT.text },
  errorText: { fontSize: 16, color: LIGHT.sub, textAlign: 'center' },
  errorBtn: { fontSize: 17, fontWeight: '800', color: LIGHT.accent, padding: 12 },
});
