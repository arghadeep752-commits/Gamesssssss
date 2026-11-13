import * as Haptics from 'expo-haptics';
import React, { useCallback } from 'react';
import { Pressable, type PressableProps, type StyleProp, type ViewStyle } from 'react-native';

import { useSettings } from '../state/settings';

type Props = Omit<PressableProps, 'style'> & {
  style?: StyleProp<ViewStyle>;
  haptic?: 'selection' | 'light' | 'medium' | 'none';
  pressedOpacity?: number;
};

/** Pressable with a quiet pressed state and optional haptic tick. */
export function Tap({ haptic = 'none', pressedOpacity = 0.55, onPress, style, hitSlop = 8, ...rest }: Props) {
  const haptics = useSettings((s) => s.haptics);
  const handlePress = useCallback<NonNullable<PressableProps['onPress']>>(
    (e) => {
      if (haptics && haptic !== 'none') {
        if (haptic === 'selection') Haptics.selectionAsync().catch(() => {});
        else Haptics.impactAsync(haptic === 'medium' ? Haptics.ImpactFeedbackStyle.Medium : Haptics.ImpactFeedbackStyle.Light).catch(() => {});
      }
      onPress?.(e);
    },
    [haptic, haptics, onPress]
  );
  return (
    <Pressable
      {...rest}
      hitSlop={hitSlop}
      onPress={handlePress}
      style={({ pressed }) => [style, pressed && { opacity: pressedOpacity }, rest.disabled && { opacity: 0.35 }]}
    />
  );
}
