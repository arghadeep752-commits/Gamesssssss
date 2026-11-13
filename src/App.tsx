import { DarkTheme, NavigationContainer, type Theme } from '@react-navigation/native';
import * as NavigationBar from 'expo-navigation-bar';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import React, { useEffect, useState } from 'react';
import { PermissionsAndroid, Platform, StyleSheet } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { mediaPermission } from './lib/media';
import { RootNavigator } from './navigation/RootNavigator';
import type { RootStackParamList } from './navigation/types';
import { useApp } from './state/app';
import { useLibrary } from './state/library';
import { useSettings } from './state/settings';
import { accents, palette } from './theme/tokens';
import { ToastHost } from './ui/Toast';

SplashScreen.preventAutoHideAsync().catch(() => {});
SplashScreen.setOptions({ duration: 180, fade: true });

function hydrated(store: { persist: { hasHydrated: () => boolean; onFinishHydration: (fn: () => void) => () => void } }) {
  if (store.persist.hasHydrated()) return Promise.resolve();
  return new Promise<void>((resolve) => {
    const unsub = store.persist.onFinishHydration(() => {
      unsub();
      resolve();
    });
  });
}

const delay = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

/** Decides the first screen: the camera if it can be used, otherwise the permission screen. */
async function boot(): Promise<keyof RootStackParamList> {
  await Promise.race([Promise.all([hydrated(useSettings), hydrated(useLibrary)]), delay(1500)]);
  const app = useApp.getState();
  app.loadLooks();
  const caps = app.loadCapabilities();
  const camera = await PermissionsAndroid.check(PermissionsAndroid.PERMISSIONS.CAMERA).catch(() => false);
  let ready = camera;
  if (ready && Platform.OS === 'android' && Number(Platform.Version) < 29) {
    // Android 8 and 9 need storage access to save into DCIM.
    const media = await mediaPermission(false);
    ready = media === 'granted' || media === 'limited';
  }
  // Camera details usually arrive in well under a second; don't hold the splash longer than this.
  await Promise.race([caps, delay(2500)]);
  return ready ? 'Camera' : 'Permissions';
}

export default function App() {
  const [initial, setInitial] = useState<keyof RootStackParamList | null>(null);
  const accent = useSettings((s) => accents[s.accent]?.color ?? accents.tungsten.color);

  useEffect(() => {
    boot()
      .then(setInitial)
      .catch(() => setInitial('Permissions'));
    NavigationBar.setButtonStyleAsync('light').catch(() => {});
  }, []);

  if (!initial) return null;

  const theme: Theme = {
    ...DarkTheme,
    colors: {
      ...DarkTheme.colors,
      primary: accent,
      background: palette.black,
      card: palette.black,
      text: palette.ink,
      border: palette.rule,
      notification: palette.tally,
    },
  };

  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <NavigationContainer theme={theme} onReady={() => SplashScreen.hideAsync().catch(() => {})}>
          <RootNavigator initialRouteName={initial} />
        </NavigationContainer>
        <ToastHost />
        <StatusBar style="light" />
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: palette.black } });
