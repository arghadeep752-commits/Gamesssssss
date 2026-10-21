import type { ReactNode } from 'react';
import { ActivityIndicator, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { AppText } from './AppText';
import { Button } from './Button';
import { Icon, type IconName } from './Icon';
import { useTheme } from './theme';

export interface EmptyStateProps {
  icon: IconName;
  title: string;
  message?: string;
  actionLabel?: string;
  onAction?: () => void;
  secondaryLabel?: string;
  onSecondary?: () => void;
  style?: StyleProp<ViewStyle>;
  children?: ReactNode;
}

export function EmptyState({
  icon,
  title,
  message,
  actionLabel,
  onAction,
  secondaryLabel,
  onSecondary,
  style,
  children,
}: EmptyStateProps) {
  const { colors, spacing } = useTheme();
  return (
    <View style={[styles.wrap, { padding: spacing.xxl }, style]}>
      <View style={[styles.iconCircle, { backgroundColor: colors.primarySoft }]}>
        <Icon name={icon} size={28} color={colors.primary} />
      </View>
      <AppText variant="heading" align="center" style={{ marginTop: spacing.lg }}>
        {title}
      </AppText>
      {message ? (
        <AppText variant="body" color="textMuted" align="center" style={{ marginTop: spacing.xs, maxWidth: 320 }}>
          {message}
        </AppText>
      ) : null}
      {children}
      {actionLabel && onAction ? (
        <Button title={actionLabel} onPress={onAction} style={{ marginTop: spacing.xl }} />
      ) : null}
      {secondaryLabel && onSecondary ? (
        <Button title={secondaryLabel} onPress={onSecondary} variant="ghost" style={{ marginTop: spacing.xs }} />
      ) : null}
    </View>
  );
}

export function ErrorState({
  title = 'Something went wrong',
  message = 'Please check your connection and try again.',
  onRetry,
  style,
}: {
  title?: string;
  message?: string;
  onRetry?: () => void;
  style?: StyleProp<ViewStyle>;
}) {
  return (
    <EmptyState
      icon="alert"
      title={title}
      message={message}
      actionLabel={onRetry ? 'Try again' : undefined}
      onAction={onRetry}
      style={style}
    />
  );
}

export function LoadingState({ label, style }: { label?: string; style?: StyleProp<ViewStyle> }) {
  const { colors, spacing } = useTheme();
  return (
    <View style={[styles.wrap, { padding: spacing.xxl }, style]}>
      <ActivityIndicator color={colors.primary} />
      {label ? (
        <AppText variant="caption" color="textMuted" style={{ marginTop: spacing.sm }}>
          {label}
        </AppText>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  iconCircle: {
    width: 64,
    height: 64,
    borderRadius: 32,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
