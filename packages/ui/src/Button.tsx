import { ActivityIndicator, StyleSheet, View, type StyleProp, type ViewStyle } from 'react-native';
import { AppText } from './AppText';
import { Icon, type IconName } from './Icon';
import { useTheme } from './theme';
import { Touchable } from './Touchable';

export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'danger';

export interface ButtonProps {
  title: string;
  onPress?: () => void;
  variant?: ButtonVariant;
  size?: 'sm' | 'md';
  icon?: IconName;
  loading?: boolean;
  disabled?: boolean;
  fullWidth?: boolean;
  style?: StyleProp<ViewStyle>;
  accessibilityLabel?: string;
  testID?: string;
}

export function Button({
  title,
  onPress,
  variant = 'primary',
  size = 'md',
  icon,
  loading = false,
  disabled = false,
  fullWidth = false,
  style,
  accessibilityLabel,
  testID,
}: ButtonProps) {
  const { colors, radii } = useTheme();
  const tones: Record<ButtonVariant, { bg: string; fg: string; border?: string }> = {
    primary: { bg: colors.primary, fg: colors.onPrimary },
    secondary: { bg: colors.primarySoft, fg: colors.onPrimarySoft },
    outline: { bg: 'transparent', fg: colors.text, border: colors.borderStrong },
    ghost: { bg: 'transparent', fg: colors.primary },
    danger: { bg: colors.dangerSoft, fg: colors.danger },
  };
  const tone = tones[variant];
  const inactive = disabled || loading;
  const height = size === 'sm' ? 36 : 46;

  return (
    <Touchable
      testID={testID}
      onPress={onPress}
      disabled={inactive}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel ?? title}
      accessibilityState={{ disabled: inactive, busy: loading }}
      style={[
        styles.base,
        {
          height,
          paddingHorizontal: size === 'sm' ? 14 : 18,
          borderRadius: radii.md,
          backgroundColor: tone.bg,
          borderWidth: tone.border ? StyleSheet.hairlineWidth * 2 : 0,
          borderColor: tone.border ?? 'transparent',
          opacity: disabled ? 0.45 : 1,
          alignSelf: fullWidth ? 'stretch' : 'auto',
        },
        style,
      ]}
    >
      <View style={styles.row}>
        {loading ? (
          <ActivityIndicator size="small" color={tone.fg} />
        ) : icon ? (
          <Icon name={icon} size={size === 'sm' ? 16 : 18} color={tone.fg} />
        ) : null}
        <AppText variant="label" color={tone.fg} weight="600" style={{ fontSize: size === 'sm' ? 13 : 15 }} numberOfLines={1}>
          {title}
        </AppText>
      </View>
    </Touchable>
  );
}

export interface IconButtonProps {
  name: IconName;
  onPress?: () => void;
  accessibilityLabel: string;
  tone?: 'plain' | 'tonal' | 'overlay';
  color?: string;
  fill?: string;
  size?: number;
  disabled?: boolean;
  testID?: string;
  style?: StyleProp<ViewStyle>;
}

export function IconButton({
  name,
  onPress,
  accessibilityLabel,
  tone = 'plain',
  color,
  fill,
  size = 22,
  disabled,
  testID,
  style,
}: IconButtonProps) {
  const { colors } = useTheme();
  const bg = tone === 'tonal' ? colors.surfaceAlt : tone === 'overlay' ? 'rgba(12,10,8,0.42)' : 'transparent';
  const fg = color ?? (tone === 'overlay' ? colors.previewText : colors.text);
  return (
    <Touchable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel}
      hitSlop={6}
      style={[styles.iconButton, { backgroundColor: bg, opacity: disabled ? 0.4 : 1 }, style]}
    >
      <Icon name={name} size={size} color={fg} fill={fill} />
    </Touchable>
  );
}

const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
    justifyContent: 'center',
    alignItems: 'center',
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
  },
  iconButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
