import type { ReactNode } from 'react';
import { Platform, Pressable, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';
import { useTheme } from './theme';

export interface TouchableProps extends Omit<PressableProps, 'style' | 'children'> {
  style?: StyleProp<ViewStyle>;
  children?: ReactNode;
  rippleColor?: string;
  borderlessRipple?: boolean;
}

/** Native ripple on Android, a light fade elsewhere. Round corners need overflow: 'hidden' on `style`. */
export function Touchable({ style, rippleColor, borderlessRipple = false, disabled, children, ...rest }: TouchableProps) {
  const theme = useTheme();
  const ripple = rippleColor ?? (theme.scheme === 'dark' ? 'rgba(255,255,255,0.12)' : 'rgba(42,37,32,0.08)');
  return (
    <Pressable
      disabled={disabled}
      android_ripple={disabled ? undefined : { color: ripple, borderless: borderlessRipple, foreground: true }}
      style={({ pressed }) => [style, Platform.OS !== 'android' && pressed ? { opacity: 0.7 } : null]}
      {...rest}
    >
      {children}
    </Pressable>
  );
}
