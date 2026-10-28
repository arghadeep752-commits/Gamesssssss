import { NavigationBar } from 'expo-navigation-bar';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { Component, useEffect, type ReactNode } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { Button } from '../components/Button';
import { COLORS, SPACE, TYPE } from '../config/theme';
import { AchievementsScreen } from '../screens/AchievementsScreen';
import { DailyScreen } from '../screens/DailyScreen';
import { GameScreen } from '../screens/GameScreen';
import { HelpScreen } from '../screens/HelpScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { LegalScreen } from '../screens/LegalScreen';
import { LevelSelectScreen } from '../screens/LevelSelectScreen';
import { PrivacyScreen } from '../screens/PrivacyScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { preloadSfx, releaseAudio } from '../services/audio';
import { GameStoreProvider, useStore } from '../state/store';
import { NavigationProvider, type Route } from './navigation';

SplashScreen.preventAutoHideAsync().catch(() => undefined);

function renderRoute(route: Route): ReactNode {
  switch (route.name) {
    case 'home':
      return <HomeScreen />;
    case 'daily':
      return <DailyScreen />;
    case 'me':
      return <ProfileScreen />;
    case 'levels':
      return <LevelSelectScreen />;
    case 'game':
      return <GameScreen route={route.mode === 'level' ? { mode: 'level', level: route.level } : { mode: 'daily', dateKey: route.dateKey }} />;
    case 'achievements':
      return <AchievementsScreen />;
    case 'settings':
      return <SettingsScreen />;
    case 'help':
      return <HelpScreen />;
    case 'legal':
      return <LegalScreen doc={route.doc} />;
    case 'privacy':
      return <PrivacyScreen />;
  }
}

function Root() {
  const { ready } = useStore();
  useEffect(() => {
    if (!ready) return;
    SplashScreen.hideAsync().catch(() => undefined);
    preloadSfx();
  }, [ready]);
  useEffect(() => releaseAudio, []);

  if (!ready) return <View style={styles.blank} />;
  return (
    <>
      <StatusBar style="dark" />
      <NavigationBar style="dark" />
      <NavigationProvider initial={{ name: 'home' }} render={renderRoute} />
    </>
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
          <Text style={TYPE.title}>Something went wrong</Text>
          <Text style={styles.errorText}>Your saved progress is safe. Tap below to return to the game.</Text>
          <Button label="Back to the game" onPress={() => this.setState((s) => ({ error: null, attempt: s.attempt + 1 }))} />
        </View>
      );
    }
    return <View key={this.state.attempt} style={styles.fill}>{this.props.children}</View>;
  }
}

export default function App() {
  return (
    <SafeAreaProvider>
      <ErrorBoundary>
        <GameStoreProvider>
          <Root />
        </GameStoreProvider>
      </ErrorBoundary>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  blank: { flex: 1, backgroundColor: COLORS.background },
  error: { flex: 1, backgroundColor: COLORS.background, alignItems: 'center', justifyContent: 'center', padding: SPACE.xl, gap: SPACE.lg },
  errorText: { ...TYPE.body, color: COLORS.inkSoft, textAlign: 'center' },
});
