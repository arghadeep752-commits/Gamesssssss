/**
 * Small glass button (pill or circle) with the same spring press and
 * highlight as the keys. When `active`, it fills with liquid.
 */
import React from 'react';
import {
  AccessibilityRole,
  AccessibilityState,
  Animated,
  StyleSheet,
  View,
} from 'react-native';
import { usePalette } from '../theme/theme';
import { AnimatedPressable, usePressMotion } from './Key';
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
  const motion = usePressMotion();
  const radius = Math.min(width, height) / 2;
  const fillable = activeChildren !== undefined;
  return (
    <AnimatedPressable
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
        fillable && styles.clip,
        {
          width,
          height,
          borderRadius: radius,
          opacity: disabled ? 0.45 : 1,
          backgroundImage: tone === 'danger' ? undefined : p.glassFn,
          borderColor: tone === 'danger' ? p.danger : p.glassBorder,
          transform: [{ scale: motion.scale }],
        },
      ]}
    >
      <View style={styles.content}>{children}</View>
      {fillable ? (
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
      <Animated.View
        pointerEvents="none"
        style={[
          StyleSheet.absoluteFill,
          {
            borderRadius: radius - 1,
            backgroundColor: p.pressGlow,
            opacity: motion.glow,
          },
        ]}
      />
    </AnimatedPressable>
  );
}

const styles = StyleSheet.create({
  glass: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  clip: {
    overflow: 'hidden',
  },
  content: {
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  },
});
