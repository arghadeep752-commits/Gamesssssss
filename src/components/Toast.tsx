import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import { Animated, StyleSheet, Text } from 'react-native';
import { fonts, usePalette } from '../theme/theme';

export interface ToastMessage {
  text: string;
  seq: number;
}

/** Short confirmation bubble ("Copied 1,234") that springs in and fades. */
export const Toast = memo(function Toast({
  message,
  bottom,
}: {
  message: ToastMessage | null;
  bottom: number;
}) {
  const p = usePalette();
  const show = useRef(new Animated.Value(0)).current;
  const [text, setText] = useState('');

  useEffect(() => {
    if (!message) {
      return;
    }
    setText(message.text);
    show.stopAnimation();
    const anim = Animated.sequence([
      Animated.spring(show, {
        toValue: 1,
        stiffness: 320,
        damping: 22,
        mass: 1,
        useNativeDriver: true,
      }),
      Animated.delay(1400),
      Animated.timing(show, {
        toValue: 0,
        duration: 220,
        useNativeDriver: true,
      }),
    ]);
    anim.start();
    return () => anim.stop();
  }, [message, show]);

  const motion = useMemo(
    () => ({
      opacity: show.interpolate({
        inputRange: [0, 0.6, 1],
        outputRange: [0, 1, 1],
      }),
      transform: [
        {
          translateY: show.interpolate({
            inputRange: [0, 1],
            outputRange: [14, 0],
          }),
        },
        {
          scale: show.interpolate({
            inputRange: [0, 1],
            outputRange: [0.9, 1],
          }),
        },
      ],
    }),
    [show],
  );

  return (
    <Animated.View
      pointerEvents="none"
      accessibilityLiveRegion="polite"
      style={[
        styles.toast,
        motion,
        { bottom, backgroundColor: p.toast, borderColor: p.glassBorder },
      ]}
    >
      <Text
        style={[styles.text, { color: p.toastText }]}
        numberOfLines={1}
        maxFontSizeMultiplier={1.2}
      >
        {text}
      </Text>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    alignSelf: 'center',
    maxWidth: '86%',
    paddingHorizontal: 18,
    paddingVertical: 10,
    borderRadius: 20,
    borderWidth: 1,
  },
  text: {
    fontFamily: fonts.medium,
    fontSize: 14,
  },
});
