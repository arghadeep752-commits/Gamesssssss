import React from 'react';
import { Text, type TextProps, type TextStyle } from 'react-native';

import { palette, type as typeScale } from '../theme/tokens';

type Variant = keyof typeof typeScale;

type Props = TextProps & { variant?: Variant; color?: string; align?: TextStyle['textAlign'] };

/** Text with the Camero Plus type scale. Defaults to body text in ink. */
export function T({ variant = 'body', color = palette.ink, align, style, ...rest }: Props) {
  return <Text allowFontScaling={false} {...rest} style={[typeScale[variant], { color, textAlign: align }, style]} />;
}
