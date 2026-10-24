import { StyleSheet, View } from 'react-native';
import { AppText, Icon, useTheme } from '@devdarshan/ui';

/** Shown on DEMO builds so sample artwork is never mistaken for the real catalogue. */
export function DemoBanner() {
  const { colors, radii, spacing } = useTheme();
  return (
    <View
      testID="demo-banner"
      style={[
        styles.row,
        { backgroundColor: colors.secondarySoft, borderRadius: radii.md, marginHorizontal: spacing.lg, marginTop: spacing.sm, padding: spacing.md },
      ]}
    >
      <Icon name="info" size={18} color={colors.onSecondarySoft} />
      <View style={{ flex: 1 }}>
        <AppText variant="bodyStrong" style={{ color: colors.onSecondarySoft }}>
          Demo build
        </AppText>
        <AppText variant="caption" style={{ color: colors.onSecondarySoft }}>
          Sample artwork for trying the app. Real wallpapers appear once DevDarshan is connected to its server.
        </AppText>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
  },
});
