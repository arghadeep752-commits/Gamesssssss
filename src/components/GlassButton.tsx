/**
 * Small glass button (pill or circle) with the same spring press and touch
 * light as the keys. When `active`, it fills with liquid.
 */
import React from 'react';
import {
  AccessibilityRole,
  AccessibilityState,
  Animated,
  Pressable,
  StyleSheet,
  View,
} from 'react-native';
import { usePalette } from '../theme/theme';
import { usePressMotion } from './Key';
import { LiquidFill } from './LiquidFill';

interface Props {
  width: number;
  height: number;
  onPress: () => void;
  accessibilityLabel: string;
  accessibilityRole?: AccessibilityRole;
  accessibilityState?: AccessibilityState;
  active?: boolean;
  still?: boolean;
  /** Content on glass. */
  children: React.ReactNode;
  /** Content on the liquid (same as children in the "on" color). */
  activeChildren?: React.ReactNode;
  tone?: 'glass' | 'danger';
  disabled?: boolean;
}

export function GlassButton({
  width,
  height,
  onPress,
  accessibilityLabel,
  accessibilityRole = 'button',
  accessibilityState,
  active = false,
  still = false,
  children,
  activeChildren,
  tone = 'glass',
  disabled = false,
}: Props) {
  const p = usePalette();
  const motion = usePressMotion(width, height);
  const radius = Math.min(width, height) / 2;
  return (
    <Animated.View
      style={{
        width,
        height,
        borderRadius: radius,
        boxShadow: disabled ? undefined : p.keyShadow,
        opacity: disabled ? 0.45 : 1,
        transform: [{ scale: motion.scale }],
      }}
    >
      <Pressable
        onPressIn={disabled ? undefined : motion.pressIn}
        onPressOut={disabled ? undefined : motion.pressOut}
        onPress={onPress}
        disabled={disabled}
        hitSlop={6}
        accessibilityRole={accessibilityRole}
        accessibilityLabel={accessibilityLabel}
        accessibilityState={accessibilityState}
        style={[
          styles.glass,
          {
            width,
            height,
            borderRadius: radius,
            backgroundColor: tone === 'danger' ? 'transparent' : p.glassFn,
            backgroundImage: tone === 'danger' ? undefined : p.sheen,
            borderColor: tone === 'danger' ? p.danger : p.glassBorder,
          },
        ]}
      >
        <View pointerEvents="none" style={styles.content}>
          {children}
        </View>
        {activeChildren !== undefined ? (
          <LiquidFill
            active={active}
            width={width}
            height={height}
            color={p.accent}
            gradient={p.liquidColumn}
            still={still}
          >
            {activeChildren}
          </LiquidFill>
        ) : null}
        {motion.light}
      </Pressable>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  glass: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 1,
  },
  content: {
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
});
