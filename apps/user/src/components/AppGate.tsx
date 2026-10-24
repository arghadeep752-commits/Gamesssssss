import type { ReactNode } from 'react';
import { Linking, ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText, Button, EmptyState, useTheme } from '@devdarshan/ui';
import { buildInfo, versionLabel } from '../config';
import { useAppConfig } from '../data/appConfig';
import { isBackendConfigured } from '../firebase';
import { BrandMark } from './Brand';
import { SelfTestPanel } from './SelfTestPanel';

function GateScreen({ children }: { children: ReactNode }) {
  const { colors } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.gate, { backgroundColor: colors.background, paddingTop: insets.top + 24, paddingBottom: insets.bottom + 24 }]}>
      <BrandMark size={34} />
      <View style={styles.body}>{children}</View>
      <AppText variant="caption" color="textSubtle">
        Version {versionLabel()}
      </AppText>
    </View>
  );
}

/**
 * Screens that replace the app entirely: a build without a backend, maintenance
 * mode, or a version older than the admin's minimum. All driven by live config.
 */
export function AppGate({ children }: { children: ReactNode }) {
  const { config } = useAppConfig();

  if (!isBackendConfigured && !buildInfo.demo) {
    return (
      <GateScreen>
        <ScrollView contentContainerStyle={styles.scroll}>
          <EmptyState
            icon="info"
            title="Almost ready"
            message="This test build is not connected to the DevDarshan server yet. Install the release build from your build page to see wallpapers."
          />
          {buildInfo.channel !== 'release' ? <SelfTestPanel /> : null}
        </ScrollView>
      </GateScreen>
    );
  }

  if (config.maintenanceMode) {
    return (
      <GateScreen>
        <EmptyState
          icon="clock"
          title="Pausing for a short while"
          message={config.maintenanceMessage || 'DevDarshan is being updated. Please come back in a little while.'}
        />
      </GateScreen>
    );
  }

  if (config.minimumSupportedVersionCode > buildInfo.versionCode) {
    return (
      <GateScreen>
        <EmptyState icon="download" title="Update needed" message="This version of DevDarshan is no longer supported. Please install the latest version.">
          {config.updateUrl ? (
            <Button title="Get the update" onPress={() => Linking.openURL(config.updateUrl)} style={{ marginTop: 20 }} />
          ) : null}
        </EmptyState>
      </GateScreen>
    );
  }

  return <>{children}</>;
}

const styles = StyleSheet.create({
  gate: {
    flex: 1,
    alignItems: 'center',
    paddingHorizontal: 24,
  },
  body: {
    flex: 1,
    alignSelf: 'stretch',
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    paddingVertical: 24,
  },
});
