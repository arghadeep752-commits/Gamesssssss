import React, { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withDelay, withSequence, withTiming } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { create } from 'zustand';

import { hairline, palette, radius } from '../theme/tokens';
import { T } from './T';

type ToastState = { message: string | null; key: number; show: (message: string) => void };

export const useToast = create<ToastState>((set) => ({
  message: null,
  key: 0,
  show: (message) => set((s) => ({ message, key: s.key + 1 })),
}));

export const toast = (message: string) => useToast.getState().show(message);

/** One-line message near the top of the screen. */
export function ToastHost() {
  const { message, key } = useToast();
  const insets = useSafeAreaInsets();
  const o = useSharedValue(0);
  useEffect(() => {
    if (!message) return;
    o.value = 0;
    o.value = withSequence(withTiming(1, { duration: 160 }), withDelay(2600, withTiming(0, { duration: 260 })));
  }, [key, message, o]);
  const style = useAnimatedStyle(() => ({ opacity: o.value, transform: [{ translateY: (1 - o.value) * -8 }] }));
  if (!message) return null;
  return (
    <View pointerEvents="none" style={[styles.host, { top: insets.top + 56 }]}>
      <Animated.View style={[styles.toast, style]}>
        <T variant="label" align="center">
          {message}
        </T>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  host: { position: 'absolute', left: 0, right: 0, alignItems: 'center', zIndex: 100 },
  toast: {
    maxWidth: '86%',
    paddingHorizontal: 14,
    paddingVertical: 9,
    borderRadius: radius.md,
    backgroundColor: palette.scrimStrong,
    borderWidth: hairline,
    borderColor: palette.rule,
  },
});
