import { memo, useEffect } from 'react';
import { StyleSheet, Text } from 'react-native';
import Animated, { useAnimatedStyle, useSharedValue, withDelay, withSequence, withTiming } from 'react-native-reanimated';
import { COLORS, RADIUS, SPACE } from '../config/theme';
import { Icon, type IconName } from './Icon';

export interface ToastMessage {
  readonly seq: number;
  readonly text: string;
  readonly icon?: IconName;
}

/** Small transient banner (achievements, rewards). Ignores touches. */
export const Toast = memo(function Toast({ message, top }: { message: ToastMessage | null; top: number }) {
  const t = useSharedValue(0);
  useEffect(() => {
    if (!message) return;
    t.value = 0;
    t.value = withSequence(withTiming(1, { duration: 180 }), withDelay(2200, withTiming(0, { duration: 220 })));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [message?.seq]);
  const style = useAnimatedStyle(() => ({ opacity: t.value, transform: [{ translateY: (1 - t.value) * -12 }] }));
  if (!message) return null;
  return (
    <Animated.View pointerEvents="none" style={[styles.toast, { top }, style]}>
      {message.icon ? <Icon name={message.icon} size={18} color={COLORS.star} filled={message.icon === 'star'} /> : null}
      <Text style={styles.text} numberOfLines={2}>
        {message.text}
      </Text>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  toast: {
    position: 'absolute',
    alignSelf: 'center',
    maxWidth: '90%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACE.sm,
    backgroundColor: COLORS.ink,
    paddingHorizontal: SPACE.lg,
    paddingVertical: SPACE.sm + 2,
    borderRadius: RADIUS.pill,
  },
  text: { color: COLORS.white, fontSize: 14, fontWeight: '600', flexShrink: 1 },
});
