/**
 * The expression and its live result. A new result springs into place, a
 * horizontal swipe deletes the last character and a long press copies the
 * value. When the space above the keys changes (scientific keys shown or
 * hidden) the text glides to its new size instead of jumping.
 */
import React, { memo, useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  LayoutChangeEvent,
  PanResponder,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { fitFontSize, textWidthEm } from '../theme/measure';
import { fonts, usePalette } from '../theme/theme';

interface Props {
  text: string;
  ghost: string;
  preview: string | null;
  error: string | null;
  indicators: string[];
  maxFont: number;
  minFont: number;
  previewFont: number;
  resultSeq: number;
  spoken: string;
  still: boolean;
  onCopy: () => void;
  onSwipe: () => void;
}

export const Display = memo(function Display({
  text,
  ghost,
  preview,
  error,
  indicators,
  maxFont,
  minFont,
  previewFont,
  resultSeq,
  spoken,
  still,
  onCopy,
  onSwipe,
}: Props) {
  const p = usePalette();
  const [width, setWidth] = useState(0);
  const scroll = useRef<ScrollView>(null);
  const rise = useRef(new Animated.Value(0)).current;
  // Native from the start, so setting it never re-renders anything. Created
  // lazily: a native value allocates a node on the UI side when constructed.
  const [zoom] = useState(
    () => new Animated.Value(1, { useNativeDriver: true }),
  );

  const shown = text === '' ? '0' : text;
  const full = shown + ghost;
  const fontSize = fitFontSize(full, width, maxFont, minFont);
  const previewSize = preview
    ? fitFontSize(preview, width, previewFont, 16)
    : previewFont;

  // Created once: new interpolation nodes on every render would rebuild the
  // native animation graph on each key press.
  const textMotion = useMemo(
    () => ({
      opacity: rise.interpolate({
        inputRange: [0, 1],
        outputRange: [1, 0.2],
      }),
      transform: [
        {
          translateY: rise.interpolate({
            inputRange: [0, 1],
            outputRange: [0, 26],
          }),
        },
        {
          scale: Animated.multiply(
            zoom,
            rise.interpolate({
              inputRange: [0, 1],
              outputRange: [1, 0.94],
            }),
          ),
        },
      ],
    }),
    [rise, zoom],
  );

  // When the room for the text changes (scientific keys shown or hidden),
  // the text starts at its old size and glides to the new one. The starting
  // scale is set while rendering, so it is committed together with the new
  // font size and the text never flashes at the wrong size.
  const sizing = useRef({ font: fontSize, max: maxFont, glide: false });
  if (sizing.current.max !== maxFont) {
    const before = sizing.current.font;
    sizing.current.max = maxFont;
    if (!still && width > 0 && before !== fontSize) {
      zoom.setValue(before / fontSize);
      sizing.current.glide = true;
    }
  }
  sizing.current.font = fontSize;

  useEffect(() => {
    if (!sizing.current.glide) {
      return;
    }
    sizing.current.glide = false;
    Animated.spring(zoom, {
      toValue: 1,
      stiffness: 240,
      damping: 30,
      mass: 1,
      useNativeDriver: true,
    }).start();
  }, [maxFont, zoom]);

  // Swipes are only for deleting while the expression fits; once it needs
  // scrolling, horizontal drags scroll it instead.
  const swipeable = useRef(true);
  swipeable.current = width > 0 && textWidthEm(full) * minFont <= width;
  const onSwipeRef = useRef(onSwipe);
  onSwipeRef.current = onSwipe;
  const pan = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponderCapture: (_, g) =>
        swipeable.current &&
        Math.abs(g.dx) > 14 &&
        Math.abs(g.dx) > Math.abs(g.dy) * 1.6,
      onPanResponderRelease: (_, g) => {
        if (Math.abs(g.dx) > 44) {
          onSwipeRef.current();
        }
      },
      onPanResponderTerminationRequest: () => false,
    }),
  ).current;

  useEffect(() => {
    if (resultSeq === 0 || still) {
      return;
    }
    rise.setValue(1);
    Animated.spring(rise, {
      toValue: 0,
      stiffness: 240,
      damping: 22,
      mass: 1,
      useNativeDriver: true,
    }).start();
  }, [resultSeq, still, rise]);

  const onLayout = (e: LayoutChangeEvent) =>
    setWidth(e.nativeEvent.layout.width);

  return (
    <View style={styles.wrap} {...pan.panHandlers}>
      <Pressable
        onLongPress={onCopy}
        delayLongPress={500}
        accessible
        accessibilityRole="text"
        accessibilityLabel={spoken}
        accessibilityHint="Long press to copy the result. Swipe sideways to delete."
      >
        <View style={styles.indicators}>
          {indicators.map(label => (
            <View
              key={label}
              style={[
                styles.chip,
                { borderColor: p.glassBorder, backgroundColor: p.segment },
              ]}
            >
              <Text
                allowFontScaling={false}
                style={[styles.chipText, { color: p.inkMuted }]}
              >
                {label}
              </Text>
            </View>
          ))}
        </View>
        <View onLayout={onLayout}>
          <Animated.View style={[styles.textBox, textMotion]}>
            <ScrollView
              ref={scroll}
              horizontal
              showsHorizontalScrollIndicator={false}
              onContentSizeChange={() =>
                scroll.current?.scrollToEnd({ animated: false })
              }
              contentContainerStyle={styles.scrollContent}
            >
              <Text
                testID="expression"
                allowFontScaling={false}
                style={[
                  styles.expression,
                  {
                    fontSize,
                    lineHeight: Math.round(fontSize * 1.18),
                    letterSpacing: fontSize > 40 ? -1 : -0.4,
                    color: p.ink,
                  },
                ]}
              >
                {shown}
                {ghost ? (
                  <Text style={{ color: p.inkFaint }}>{ghost}</Text>
                ) : null}
              </Text>
            </ScrollView>
          </Animated.View>
          <Text
            testID="preview"
            allowFontScaling={false}
            numberOfLines={1}
            accessibilityLiveRegion="polite"
            style={[
              styles.preview,
              {
                fontSize: error ? Math.min(previewFont, 20) : previewSize,
                lineHeight: Math.round(previewFont * 1.3),
                color: error ? p.danger : p.inkMuted,
                fontFamily: error ? fonts.regular : fonts.light,
              },
            ]}
          >
            {error ?? preview ?? ' '}
          </Text>
        </View>
      </Pressable>
    </View>
  );
});

const styles = StyleSheet.create({
  textBox: {
    // Text is right-aligned and sits on the result line, so size changes
    // grow from the bottom-right corner.
    transformOrigin: 'right bottom',
  },
  wrap: {
    paddingHorizontal: 26,
    paddingTop: 4,
    paddingBottom: 14,
  },
  indicators: {
    flexDirection: 'row',
    gap: 6,
    minHeight: 22,
  },
  chip: {
    borderWidth: 1,
    borderRadius: 11,
    height: 22,
    paddingHorizontal: 9,
    justifyContent: 'center',
  },
  chipText: {
    fontFamily: fonts.medium,
    fontSize: 11,
    letterSpacing: 0.6,
    includeFontPadding: false,
  },
  scrollContent: {
    flexGrow: 1,
    justifyContent: 'flex-end',
    alignItems: 'flex-end',
  },
  expression: {
    fontFamily: fonts.light,
    includeFontPadding: false,
    textAlign: 'right',
    fontVariant: ['tabular-nums'],
  },
  preview: {
    includeFontPadding: false,
    textAlign: 'right',
    marginTop: 4,
    fontVariant: ['tabular-nums'],
  },
});
