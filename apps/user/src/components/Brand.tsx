import { StyleSheet, View } from 'react-native';
import { APP_NAME, APP_NAME_HI } from '@devdarshan/shared';
import { AppText, Logo, useTheme } from '@devdarshan/ui';

/** Compact DevDarshan lockup: the diya-in-doorway mark with the English and Hindi names. */
export function BrandMark({ size = 30, showHindi = true }: { size?: number; showHindi?: boolean }) {
  const { colors } = useTheme();
  return (
    <View style={styles.row} accessible accessibilityRole="header" accessibilityLabel={APP_NAME}>
      <Logo size={size} archColor={colors.primary} flameColor={colors.gold} flameCoreColor={colors.surface} />
      <View style={styles.texts}>
        <AppText variant="brand" color="text" style={styles.brand}>
          {APP_NAME}
        </AppText>
        {showHindi ? (
          <AppText variant="caption" color="textMuted" style={styles.hindi}>
            {APP_NAME_HI}
          </AppText>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  texts: {
    justifyContent: 'center',
  },
  brand: {
    lineHeight: 24,
  },
  hindi: {
    marginTop: -2,
    lineHeight: 16,
  },
});
