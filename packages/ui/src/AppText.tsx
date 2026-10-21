import { Text, type TextProps, type TextStyle } from 'react-native';
import type { Palette, TypeVariant } from '@devdarshan/shared/theme';
import { useTheme } from './theme';

export interface AppTextProps extends TextProps {
  variant?: TypeVariant;
  /** A palette key ("textMuted", "primary") or any colour string. */
  color?: keyof Palette | (string & {});
  align?: TextStyle['textAlign'];
  weight?: TextStyle['fontWeight'];
}

export function AppText({ variant = 'body', color = 'text', align, weight, style, ...rest }: AppTextProps) {
  const theme = useTheme();
  const base = theme.type[variant];
  const resolved = color in theme.colors ? theme.colors[color as keyof Palette] : color;
  return (
    <Text
      maxFontSizeMultiplier={1.35}
      {...rest}
      style={[
        {
          color: resolved,
          fontSize: base.fontSize,
          lineHeight: base.lineHeight,
          fontWeight: weight ?? base.fontWeight,
          letterSpacing: 'letterSpacing' in base ? base.letterSpacing : undefined,
          fontFamily: 'fontFamily' in base ? base.fontFamily : undefined,
          textAlign: align,
        },
        style,
      ]}
    />
  );
}
