import { memo, useCallback } from 'react';
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import { COLORS, RADIUS, SPACE, TOUCH } from '../config/theme';
import { playSfx } from '../services/audio';
import { Icon, type IconName } from './Icon';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';

interface ButtonProps {
  label: string;
  onPress: () => void;
  icon?: IconName;
  variant?: Variant;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  /** Plays the button sound (default true). */
  sound?: boolean;
}

const VARIANT: Record<Variant, { bg: string; fg: string; border: string }> = {
  primary: { bg: COLORS.ink, fg: COLORS.white, border: COLORS.ink },
  secondary: { bg: COLORS.surface, fg: COLORS.ink, border: COLORS.border },
  ghost: { bg: 'transparent', fg: COLORS.ink, border: 'transparent' },
  danger: { bg: COLORS.surface, fg: COLORS.error, border: COLORS.errorSoft },
};

export const Button = memo(function Button({
  label,
  onPress,
  icon,
  variant = 'primary',
  disabled,
  style,
  sound = true,
}: ButtonProps) {
  const v = VARIANT[variant];
  const handle = useCallback(() => {
    if (sound) playSfx('tap');
    onPress();
  }, [onPress, sound]);
  return (
    <Pressable
      onPress={handle}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled }}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: v.bg, borderColor: v.border },
        pressed && styles.pressed,
        disabled && styles.disabled,
        style,
      ]}
    >
      {icon ? <Icon name={icon} size={20} color={v.fg} filled={icon === 'play'} /> : null}
      <Text style={[styles.label, { color: v.fg }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressable>
  );
});

interface IconButtonProps {
  icon: IconName;
  onPress: () => void;
  label: string;
  badge?: string | number;
  disabled?: boolean;
  size?: number;
  tint?: string;
  /** Show the label under the icon (toolbar style). */
  showLabel?: boolean;
  active?: boolean;
}

export const IconButton = memo(function IconButton({
  icon,
  onPress,
  label,
  badge,
  disabled,
  size = 24,
  tint = COLORS.ink,
  showLabel,
  active,
}: IconButtonProps) {
  const handle = useCallback(() => {
    playSfx('tap');
    onPress();
  }, [onPress]);
  return (
    <Pressable
      onPress={handle}
      disabled={disabled}
      hitSlop={8}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled: !!disabled, selected: !!active }}
      style={({ pressed }) => [
        showLabel ? styles.toolButton : styles.iconButton,
        active && styles.active,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      <View>
        <Icon name={icon} size={size} color={active ? COLORS.white : tint} />
        {badge !== undefined ? (
          <View style={[styles.badge, active && styles.badgeActive]}>
            <Text style={[styles.badgeText, active && styles.badgeTextActive]}>{badge}</Text>
          </View>
        ) : null}
      </View>
      {showLabel ? (
        <Text style={[styles.toolLabel, active && { color: COLORS.white }]} numberOfLines={1}>
          {label}
        </Text>
      ) : null}
    </Pressable>
  );
});

const styles = StyleSheet.create({
  button: {
    minHeight: 52,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    paddingHorizontal: SPACE.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACE.sm,
  },
  label: { fontSize: 16, fontWeight: '700', letterSpacing: 0.2 },
  pressed: { opacity: 0.75, transform: [{ scale: 0.98 }] },
  disabled: { opacity: 0.4 },
  iconButton: {
    width: TOUCH,
    height: TOUCH,
    borderRadius: RADIUS.pill,
    alignItems: 'center',
    justifyContent: 'center',
  },
  toolButton: {
    minWidth: 72,
    minHeight: 58,
    paddingHorizontal: SPACE.md,
    paddingVertical: SPACE.sm,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 2,
  },
  active: { backgroundColor: COLORS.ink, borderColor: COLORS.ink },
  toolLabel: { fontSize: 12, fontWeight: '600', color: COLORS.inkSoft },
  badge: {
    position: 'absolute',
    top: -6,
    right: -12,
    minWidth: 18,
    height: 18,
    borderRadius: 9,
    paddingHorizontal: 4,
    backgroundColor: COLORS.ink,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeActive: { backgroundColor: COLORS.white },
  badgeText: { color: COLORS.white, fontSize: 11, fontWeight: '700' },
  badgeTextActive: { color: COLORS.ink },
});
