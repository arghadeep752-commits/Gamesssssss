import NetInfo from '@react-native-community/netinfo';
import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { AppText, Icon, useTheme } from '@devdarshan/ui';

export function useIsOnline(): boolean {
  const [online, setOnline] = useState(true);
  useEffect(
    () =>
      NetInfo.addEventListener((state) => {
        setOnline(state.isConnected !== false && state.isInternetReachable !== false);
      }),
    [],
  );
  return online;
}

/** Shown while offline; Firestore and the image cache keep previously seen content available. */
export function OfflineBanner() {
  const online = useIsOnline();
  const { colors, spacing } = useTheme();
  if (online) return null;
  return (
    <View
      accessibilityRole="alert"
      style={[styles.banner, { backgroundColor: colors.warningSoft, paddingHorizontal: spacing.lg }]}
    >
      <Icon name="wifiOff" size={16} color={colors.warning} />
      <AppText variant="caption" color="text" style={{ flex: 1 }}>
        You're offline. Showing wallpapers saved on this phone.
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
});
