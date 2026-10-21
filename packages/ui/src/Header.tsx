import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { AppText } from './AppText';
import { IconButton } from './Button';
import { useTheme } from './theme';

export interface ScreenHeaderProps {
  title?: string;
  subtitle?: string;
  onBack?: () => void;
  right?: ReactNode;
  left?: ReactNode;
  /** Adds the status-bar inset (true for screens without a native header). */
  withTopInset?: boolean;
  bordered?: boolean;
}

/** Compact 56dp header used by every screen (the native stack header is disabled). */
export function ScreenHeader({ title, subtitle, onBack, right, left, withTopInset = true, bordered = false }: ScreenHeaderProps) {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  return (
    <View
      style={[
        styles.wrap,
        {
          paddingTop: withTopInset ? insets.top : 0,
          backgroundColor: colors.background,
          borderBottomColor: bordered ? colors.border : 'transparent',
          paddingHorizontal: spacing.sm,
        },
      ]}
    >
      <View style={styles.row}>
        {onBack ? <IconButton name="arrowLeft" onPress={onBack} accessibilityLabel="Go back" /> : null}
        {left}
        <View style={[styles.titles, { paddingHorizontal: onBack || left ? spacing.xs : spacing.sm }]}>
          {title ? (
            <AppText variant="heading" numberOfLines={1} accessibilityRole="header">
              {title}
            </AppText>
          ) : null}
          {subtitle ? (
            <AppText variant="caption" color="textMuted" numberOfLines={1}>
              {subtitle}
            </AppText>
          ) : null}
        </View>
        <View style={styles.right}>{right}</View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    borderBottomWidth: StyleSheet.hairlineWidth,
  },
  row: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
  },
  titles: {
    flex: 1,
    justifyContent: 'center',
  },
  right: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 2,
  },
});
