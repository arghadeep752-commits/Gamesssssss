/**
 * Segmented control whose selection slides between options on a spring.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  LayoutChangeEvent,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { fonts, usePalette } from '../theme/theme';

interface Option<T extends string> {
  value: T;
  label: string;
  a11y?: string;
}

interface Props<T extends string> {
  value: T;
  options: Option<T>[];
  onChange: (value: T) => void;
  accessibilityLabel: string;
  still?: boolean;
}

const PAD = 4;

export function Segmented<T extends string>({
  value,
  options,
  onChange,
  accessibilityLabel,
  still = false,
}: Props<T>) {
  const p = usePalette();
  const [width, setWidth] = useState(0);
  const index = Math.max(
    0,
    options.findIndex(o => o.value === value),
  );
  const pos = useRef(new Animated.Value(index)).current;

  useEffect(() => {
    if (still) {
      pos.setValue(index);
      return;
    }
    Animated.spring(pos, {
      toValue: index,
      stiffness: 320,
      damping: 28,
      mass: 1,
      useNativeDriver: true,
    }).start();
  }, [index, still, pos]);

  const segW = width > 0 ? (width - PAD * 2) / options.length : 0;
  const last = options.length - 1;
  const slide = useMemo(
    () =>
      last > 0
        ? pos.interpolate({
            inputRange: [0, last],
            outputRange: [0, last * segW],
          })
        : 0,
    [pos, last, segW],
  );
  const onLayout = (e: LayoutChangeEvent) =>
    setWidth(e.nativeEvent.layout.width);

  return (
    <View
      onLayout={onLayout}
      accessibilityRole="radiogroup"
      accessibilityLabel={accessibilityLabel}
      style={[
        styles.track,
        { backgroundColor: p.segment, borderColor: p.glassBorder },
      ]}
    >
      {segW > 0 ? (
        <Animated.View
          pointerEvents="none"
          style={[
            styles.indicator,
            {
              width: segW,
              backgroundColor: p.segmentOn,
              backgroundImage: p.sheen,
              borderColor: p.glassBorder,
              transform: [{ translateX: slide }],
            },
          ]}
        />
      ) : null}
      {options.map(opt => {
        const on = opt.value === value;
        return (
          <Pressable
            key={opt.value}
            onPress={() => onChange(opt.value)}
            accessibilityRole="radio"
            accessibilityState={{ checked: on }}
            accessibilityLabel={opt.a11y ?? opt.label}
            style={styles.option}
          >
            <Text
              maxFontSizeMultiplier={1.2}
              numberOfLines={1}
              style={[
                styles.label,
                {
                  color: on ? p.ink : p.inkMuted,
                  fontFamily: on ? fonts.medium : fonts.regular,
                },
              ]}
            >
              {opt.label}
            </Text>
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    flexDirection: 'row',
    borderRadius: 22,
    borderWidth: 1,
    padding: PAD - 1,
  },
  indicator: {
    borderWidth: 1,
    position: 'absolute',
    left: PAD - 1,
    top: PAD - 1,
    bottom: PAD - 1,
    borderRadius: 18,
  },
  option: {
    flex: 1,
    minHeight: 40,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
  label: {
    fontSize: 14,
    includeFontPadding: false,
    fontVariant: ['tabular-nums'],
  },
});
