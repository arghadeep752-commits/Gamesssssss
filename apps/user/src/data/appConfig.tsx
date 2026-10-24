import { doc, onSnapshot } from '@react-native-firebase/firestore';
import { createContext, useContext, useEffect, useState, type ReactNode } from 'react';
import { APP_CONFIG_DOC_ID, COLLECTIONS, DEFAULT_APP_CONFIG, toAppConfig, type AppConfig } from '@devdarshan/shared';
import { buildInfo } from '../config';
import { DEMO_CONFIG } from '../demo/catalog';
import { db, isBackendConfigured } from '../firebase';

interface AppConfigState {
  config: AppConfig;
  /** True once the first snapshot (from cache or server) arrived. */
  loaded: boolean;
}

const AppConfigContext = createContext<AppConfigState>({ config: DEFAULT_APP_CONFIG, loaded: false });

/** Live public config: featured lists, home layout, maintenance mode, minimum version. */
export function AppConfigProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AppConfigState>(
    buildInfo.demo ? { config: DEMO_CONFIG, loaded: true } : { config: DEFAULT_APP_CONFIG, loaded: !isBackendConfigured },
  );

  useEffect(() => {
    if (!isBackendConfigured) return undefined;
    return onSnapshot(
      doc(db, COLLECTIONS.appConfig, APP_CONFIG_DOC_ID),
      (snap) => setState({ config: toAppConfig(snap.exists() ? snap.data() : null), loaded: true }),
      () => setState((s) => ({ ...s, loaded: true })),
    );
  }, []);

  return <AppConfigContext.Provider value={state}>{children}</AppConfigContext.Provider>;
}

export function useAppConfig(): AppConfigState {
  return useContext(AppConfigContext);
}
