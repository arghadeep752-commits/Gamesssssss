import NetInfo from '@react-native-community/netinfo';
import { DarkTheme, DefaultTheme, NavigationContainer, type Theme as NavigationTheme } from '@react-navigation/native';
import { QueryClient, QueryClientProvider, focusManager, onlineManager } from '@tanstack/react-query';
import * as SplashScreen from 'expo-splash-screen';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useMemo } from 'react';
import { AppState, type AppStateStatus } from 'react-native';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { ThemeProvider, ToastProvider, useTheme } from '@devdarshan/ui';
import { SessionProvider, useSession } from './data/session';
import { startAppCheck } from './firebase';
import { RootNavigator } from './navigation/RootNavigator';
import { GateScreen } from './screens/GateScreen';
import { useSettings } from './state/settings';

void SplashScreen.preventAutoHideAsync().catch(() => undefined);
startAppCheck();

// Admin data must be fresh: short stale time, and queries pause while offline
// (writes need the server anyway, and the UI shows an error state).
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30 * 1000,
      gcTime: 10 * 60 * 1000,
      retry: 1,
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

function AdminShell() {
  const theme = useTheme();
  const { status } = useSession();

  useEffect(() => {
    void SplashScreen.hideAsync().catch(() => undefined);
  }, []);

  // Never show admin screens (or keep their cached data) for a non-admin session.
  useEffect(() => {
    if (status !== 'admin') queryClient.clear();
  }, [status]);

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
    <>
      <StatusBar style={theme.scheme === 'dark' ? 'light' : 'dark'} />
      {status === 'admin' ? (
        <NavigationContainer theme={navigationTheme}>
          <RootNavigator />
        </NavigationContainer>
      ) : (
        <GateScreen />
      )}
    </>
  );
}

export default function App() {
  const themePreference = useSettings((s) => s.themePreference);
  useAppFocus();

  useEffect(() => {
    const timer = setTimeout(() => void SplashScreen.hideAsync().catch(() => undefined), 4000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <SafeAreaProvider>
      <ThemeProvider accent="admin" preference={themePreference}>
        <QueryClientProvider client={queryClient}>
          <SessionProvider>
            <ToastProvider>
              <AdminShell />
            </ToastProvider>
          </SessionProvider>
        </QueryClientProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
