/**
 * A frosted-glass key: translucent fill with a top-light sheen and a rim.
 * Pressing it squeezes the key and brightens the glass; an active key
 * (pending operator, 2nd) fills with liquid.
 *
 * Built to stay smooth on low-end phones:
 * - the fill and its sheen are one gradient layer, so each key paints once;
 * - no blurred shadows (only "=" has a glow), and clipping only on keys that
 *   can fill with liquid;
 * - one animated value drives both the squeeze and the highlight, on the
 *   native driver, so a tap costs the JS thread almost nothing.
 */
import React, { memo, useMemo, useRef } from 'react';
import {
  Animated,
  Easing,
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

export const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

/** Shared so the props of a key stay identical between renders. */
const SELECTED = { selected: true } as const;

interface Look {
  image: string;
  text: string;
  border: string;
  glow: string;
}

function lookFor(kind: KeyKind, p: Palette): Look {
  const glass = (image: string, text: string): Look => ({
    image,
    text,
    border: p.glassBorder,
    glow: p.pressGlow,
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
        image: `${p.sheen}, ${p.liquidGradient}`,
        text: p.accentInk,
        border: 'rgba(255, 255, 255, 0.3)',
        glow: 'rgba(255, 255, 255, 0.24)',
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

const PRESS_IN = Easing.out(Easing.quad);
// Eases back past rest for a small rebound, like a drop of liquid settling.
const RELEASE = Easing.out(Easing.back(1.7));

/**
 * Press feedback: `press` runs 0 → 1 while the finger lands and back to 0 on
 * release. The squeeze and the highlight are both derived from it, so each
 * tap is one native animation per phase.
 */
export function usePressMotion(squeeze = 0.93) {
  const press = useRef(new Animated.Value(0)).current;
  return useMemo(() => {
    const scale = press.interpolate({
      inputRange: [0, 1],
      outputRange: [1, squeeze],
    });
    const glow = press.interpolate({
      inputRange: [0, 1],
      outputRange: [0, 1],
      extrapolate: 'clamp',
    });
    const pressIn = () => {
      Animated.timing(press, {
        toValue: 1,
        duration: 90,
        easing: PRESS_IN,
        useNativeDriver: true,
      }).start();
    };
    const pressOut = () => {
      Animated.timing(press, {
        toValue: 0,
        duration: 320,
        easing: RELEASE,
        useNativeDriver: true,
      }).start();
    };
    return { scale, glow, pressIn, pressOut };
  }, [press, squeeze]);
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

/** Only these keys can be "active", so only they carry the liquid layer. */
function canFill(spec: KeySpec): boolean {
  return spec.kind === 'op' || spec.id === 'second' || spec.id === 'pow';
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
  const motion = usePressMotion();
  const fillable = canFill(spec);

  const onPressIn = () => {
    // Start the animation first: its native batch is flushed before the
    // render that the key press triggers.
    motion.pressIn();
    onPress(spec.id);
  };

  return (
    <AnimatedPressable
      accessibilityRole="button"
      accessibilityLabel={spec.a11y}
      accessibilityState={active ? SELECTED : undefined}
      onPressIn={onPressIn}
      onPressOut={motion.pressOut}
      onLongPress={onLongPress ? () => onLongPress(spec.id) : undefined}
      delayLongPress={450}
      style={[
        styles.glass,
        fillable && styles.clip,
        {
          width,
          height,
          borderRadius: radius,
          backgroundImage: look.image,
          borderColor: look.border,
          boxShadow: spec.kind === 'eq' ? p.eqShadow : undefined,
          transform: [{ scale: motion.scale }],
        },
      ]}
    >
      <KeyLabelView
        label={spec.label}
        color={look.text}
        fontSize={fontSize}
        kind={spec.kind}
      />
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
      <Animated.View
        pointerEvents="none"
        style={[
          StyleSheet.absoluteFill,
          {
            borderRadius: radius - 1,
            backgroundColor: look.glow,
            opacity: motion.glow,
          },
        ]}
      />
    </AnimatedPressable>
  );
});

const styles = StyleSheet.create({
  glass: {
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
  },
  clip: {
    overflow: 'hidden',
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
