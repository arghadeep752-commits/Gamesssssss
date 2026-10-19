/**
 * A frosted-glass key: translucent fill, top-light sheen, rim highlight and a
 * soft shadow. Pressing it squeezes the key on a spring and lights the glass
 * from the touch point; an active key (pending operator, 2nd) fills with
 * liquid. Every animation here runs on the native driver.
 */
import React, { memo, useRef } from 'react';
import {
  Animated,
  Easing,
  GestureResponderEvent,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import type { KeyId, KeyKind, KeyLabel, KeySpec } from '../state/keys';
import { Palette, fonts, usePalette } from '../theme/theme';
import { LiquidFill } from './LiquidFill';

const backspaceIcon = require('../../assets/icons/backspace.png');
const pool = require('../../assets/liquid/pool.png');

interface Look {
  fill: string;
  gradient: string;
  text: string;
  shadow: string;
  border: string;
}

function lookFor(kind: KeyKind, p: Palette): Look {
  const glass = (fill: string, text: string): Look => ({
    fill,
    gradient: p.sheen,
    text,
    shadow: p.keyShadow,
    border: p.glassBorder,
  });
  switch (kind) {
    case 'digit':
      return glass(p.glassDigit, p.ink);
    case 'fn':
      return glass(p.glassFn, p.ink);
    case 'op':
      return glass(p.glassOp, p.accentText);
    case 'sci':
      return glass(p.glassSci, p.ink);
    case 'eq':
      return {
        fill: p.accent,
        gradient: `${p.sheen}, ${p.liquidGradient}`,
        text: p.accentInk,
        shadow: p.eqShadow,
        border: 'rgba(255, 255, 255, 0.3)',
      };
  }
}

interface LabelProps {
  label: KeyLabel;
  color: string;
  fontSize: number;
  kind: KeyKind;
}

export function KeyLabelView({ label, color, fontSize, kind }: LabelProps) {
  if (label.icon === 'backspace') {
    const size = Math.round(fontSize * 1.15);
    return (
      <Image
        source={backspaceIcon}
        fadeDuration={0}
        style={{ width: size, height: size, tintColor: color }}
      />
    );
  }
  const family =
    kind === 'op' || kind === 'eq'
      ? fonts.light
      : kind === 'fn'
        ? fonts.medium
        : fonts.regular;
  const base = (
    <Text
      allowFontScaling={false}
      style={[styles.label, { fontFamily: family, fontSize, color }]}
    >
      {label.text}
    </Text>
  );
  if (!label.sup && !label.pre) {
    return base;
  }
  const supSize = Math.round(fontSize * 0.62);
  const sup = [
    styles.label,
    { fontFamily: fonts.medium, fontSize: supSize, color },
  ];
  return (
    <View style={styles.row}>
      {label.pre ? (
        <Text
          allowFontScaling={false}
          style={[
            sup,
            { marginRight: -fontSize * 0.12, marginTop: -fontSize * 0.04 },
          ]}
        >
          {label.pre}
        </Text>
      ) : null}
      {base}
      {label.sup ? (
        <Text
          allowFontScaling={false}
          style={[sup, { marginLeft: 1, marginTop: -fontSize * 0.12 }]}
        >
          {label.sup}
        </Text>
      ) : null}
    </View>
  );
}

/** Spring "squeeze" plus a light that blooms from the touch point. */
export function usePressMotion(width: number, height: number) {
  const scale = useRef(new Animated.Value(1)).current;
  const glow = useRef(new Animated.Value(0)).current;
  const bloom = useRef(new Animated.Value(0)).current;
  const x = useRef(new Animated.Value(width / 2)).current;
  const y = useRef(new Animated.Value(height / 2)).current;

  const pressIn = (e: GestureResponderEvent) => {
    const { locationX, locationY } = e.nativeEvent;
    x.setValue(Number.isFinite(locationX) ? locationX : width / 2);
    y.setValue(Number.isFinite(locationY) ? locationY : height / 2);
    bloom.setValue(0);
    Animated.parallel([
      Animated.spring(scale, {
        toValue: 0.92,
        stiffness: 520,
        damping: 28,
        mass: 1,
        useNativeDriver: true,
      }),
      Animated.timing(glow, {
        toValue: 1,
        duration: 90,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
      Animated.timing(bloom, {
        toValue: 1,
        duration: 520,
        easing: Easing.out(Easing.cubic),
        useNativeDriver: true,
      }),
    ]).start();
  };

  const pressOut = () => {
    Animated.parallel([
      Animated.spring(scale, {
        toValue: 1,
        stiffness: 280,
        damping: 13,
        mass: 1,
        useNativeDriver: true,
      }),
      Animated.timing(glow, {
        toValue: 0,
        duration: 420,
        easing: Easing.out(Easing.quad),
        useNativeDriver: true,
      }),
    ]).start();
  };

  const lightSize = Math.max(width, height) * 2.4;
  const light = (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      <Animated.Image
        source={pool}
        fadeDuration={0}
        style={{
          position: 'absolute',
          width: lightSize,
          height: lightSize,
          left: -lightSize / 2,
          top: -lightSize / 2,
          tintColor: '#FFFFFF',
          opacity: glow.interpolate({
            inputRange: [0, 1],
            outputRange: [0, 0.34],
          }),
          transform: [
            { translateX: x },
            { translateY: y },
            {
              scale: bloom.interpolate({
                inputRange: [0, 1],
                outputRange: [0.3, 1],
              }),
            },
          ],
        }}
      />
    </View>
  );

  return { scale, pressIn, pressOut, light };
}

interface Props {
  spec: KeySpec;
  width: number;
  height: number;
  fontSize: number;
  /** Fills the key with liquid (pending operator, 2nd). */
  active?: boolean;
  still?: boolean;
  onPress: (id: KeyId) => void;
  onLongPress?: (id: KeyId) => void;
}

export const Key = memo(function Key({
  spec,
  width,
  height,
  fontSize,
  active = false,
  still = false,
  onPress,
  onLongPress,
}: Props) {
  const p = usePalette();
  const look = lookFor(spec.kind, p);
  const radius = Math.round(Math.min(width, height) / 2);
  const motion = usePressMotion(width, height);
  const fillable = spec.kind === 'op' || spec.kind === 'sci';

  return (
    <Animated.View
      style={{
        width,
        height,
        borderRadius: radius,
        boxShadow: look.shadow,
        transform: [{ scale: motion.scale }],
      }}
    >
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={spec.a11y}
        accessibilityState={active ? { selected: true } : undefined}
        onPressIn={e => {
          motion.pressIn(e);
          onPress(spec.id);
        }}
        onPressOut={motion.pressOut}
        onLongPress={onLongPress ? () => onLongPress(spec.id) : undefined}
        delayLongPress={450}
        style={[
          styles.glass,
          {
            width,
            height,
            borderRadius: radius,
            backgroundColor: look.fill,
            backgroundImage: look.gradient,
            borderColor: look.border,
          },
        ]}
      >
        {/* Children ignore touches so the touch point is relative to the key. */}
        <View pointerEvents="none">
          <KeyLabelView
            label={spec.label}
            color={look.text}
            fontSize={fontSize}
            kind={spec.kind}
          />
        </View>
        {fillable ? (
          <LiquidFill
            active={active}
            width={width}
            height={height}
            color={p.accent}
            gradient={p.liquidColumn}
            still={still}
          >
            <KeyLabelView
              label={spec.label}
              color={p.accentInk}
              fontSize={fontSize}
              kind={spec.kind}
            />
          </LiquidFill>
        ) : null}
        {motion.light}
      </Pressable>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  glass: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
    borderWidth: 1,
  },
  label: {
    includeFontPadding: false,
    textAlignVertical: 'center',
    fontVariant: ['tabular-nums'],
  },
  row: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
});
