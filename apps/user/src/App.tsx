import NetInfo from '@react-native-community/netinfo';
import { DarkTheme, DefaultTheme, NavigationContainer, type Theme as NavigationTheme } from '@react-navigation/native';
import { QueryClient, QueryClientProvider, focusManager, onlineManager } from '@tanstack/react-query';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo } from 'react';
import { AppState, type AppStateStatus } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, ToastProvider, useTheme } from '@devdarshan/ui';
import { AppGate } from './components/AppGate';
import { SignInSheet } from './components/SignInSheet';
import { AppConfigProvider } from './data/appConfig';
import { AuthProvider } from './data/auth';
import { FavoritesProvider } from './data/favorites';
import { RootNavigator } from './navigation/RootNavigator';
import { useSettings } from './state/settings';

void SplashScreen.preventAutoHideAsync().catch(() => undefined);

// Firestore serves cached results offline, so queries must still run without a
// connection ("offlineFirst") instead of pausing.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      networkMode: 'offlineFirst',
      staleTime: 5 * 60 * 1000,
      gcTime: 30 * 60 * 1000,
      retry: 2,
      refetchOnWindowFocus: true,
    },
  },
});

onlineManager.setEventListener((setOnline) =>
  NetInfo.addEventListener((state) => setOnline(state.isConnected !== false)),
);

function useAppFocus() {
  useEffect(() => {
    const sub = AppState.addEventListener('change', (status: AppStateStatus) => focusManager.setFocused(status === 'active'));
    return () => sub.remove();
  }, []);
}

function ThemedApp() {
  const theme = useTheme();

  // The first frame (skeletons or a gate screen) is ready: reveal it immediately.
  useEffect(() => {
    void SplashScreen.hideAsync().catch(() => undefined);
  }, []);

  const navigationTheme = useMemo<NavigationTheme>(() => {
    const base = theme.scheme === 'dark' ? DarkTheme : DefaultTheme;
    return {
      ...base,
      colors: {
        ...base.colors,
        primary: theme.colors.primary,
        background: theme.colors.background,
        card: theme.colors.surface,
        text: theme.colors.text,
        border: theme.colors.border,
        notification: theme.colors.primary,
      },
    };
  }, [theme]);

  return (
    <ToastProvider>
      <NavigationContainer theme={navigationTheme} onReady={() => void SplashScreen.hideAsync().catch(() => undefined)}>
        <StatusBar style={theme.scheme === 'dark' ? 'light' : 'dark'} />
        <AppGate>
          <RootNavigator />
          <SignInSheet />
        </AppGate>
      </NavigationContainer>
    </ToastProvider>
  );
}

export default function App() {
  const themePreference = useSettings((s) => s.themePreference);
  useAppFocus();

  // Never keep the splash screen up if something goes wrong before navigation is ready.
  useEffect(() => {
    const timer = setTimeout(() => void SplashScreen.hideAsync().catch(() => undefined), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <SafeAreaProvider>
      <ThemeProvider accent="user" preference={themePreference}>
        <QueryClientProvider client={queryClient}>
          <AppConfigProvider>
            <AuthProvider>
              <FavoritesProvider>
                <ThemedApp />
              </FavoritesProvider>
            </AuthProvider>
          </AppConfigProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
