/**
 * Glass history card. Newest calculation at the bottom, next to the display;
 * tap a line to reuse its result, long-press to copy it. Only the most recent
 * rows are rendered, so the card stays light however long the history gets.
 */
import React, { memo, useEffect, useMemo, useRef } from 'react';
import {
  Animated,
  LayoutChangeEvent,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Grouping, closedExpressionText, formatCanonical } from '../engine';
import type { TapeEntry } from '../state/calcReducer';
import { fonts, usePalette } from '../theme/theme';

/** Rows kept on screen; older calculations stay saved but are not drawn. */
const VISIBLE_ROWS = 40;

interface Props {
  entries: TapeEntry[];
  grouping: Grouping;
  still: boolean;
  onUse: (value: string) => void;
  onCopy: (value: string) => void;
}

const Row = memo(function Row({
  entry,
  grouping,
  animateIn,
  onUse,
  onCopy,
}: {
  entry: TapeEntry;
  grouping: Grouping;
  animateIn: boolean;
  onUse: (v: string) => void;
  onCopy: (v: string) => void;
}) {
  const p = usePalette();
  // Rows that were already there never animate, so they skip the animated
  // wrapper altogether (the choice is fixed when the row mounts).
  const animated = useRef(animateIn).current;
  const enter = useRef(new Animated.Value(animateIn ? 0 : 1)).current;
  const enterStyle = useMemo(
    () => ({
      opacity: enter,
      transform: [
        {
          translateY: enter.interpolate({
            inputRange: [0, 1],
            outputRange: [18, 0],
          }),
        },
      ],
    }),
    [enter],
  );

  useEffect(() => {
    if (!animated) {
      return;
    }
    Animated.spring(enter, {
      toValue: 1,
      stiffness: 220,
      damping: 22,
      mass: 1,
      useNativeDriver: true,
    }).start();
  }, [animated, enter]);

  const expression = closedExpressionText(entry.tokens, grouping);
  const result = formatCanonical(entry.result, grouping);
  const row = (
    <Pressable
      onPress={() => onUse(entry.result)}
      onLongPress={() => onCopy(entry.result)}
      accessibilityRole="button"
      accessibilityLabel={`${expression} equals ${result}`}
      accessibilityHint="Tap to use this result. Long press to copy it."
      style={({ pressed }) => [
        styles.row,
        pressed && { backgroundColor: p.segment },
      ]}
    >
      <Text
        style={[styles.expr, { color: p.inkMuted }]}
        maxFontSizeMultiplier={1.3}
      >
        {expression}
      </Text>
      <Text
        style={[styles.result, { color: p.ink }]}
        maxFontSizeMultiplier={1.3}
      >
        {result}
      </Text>
    </Pressable>
  );
  return animated ? (
    <Animated.View style={enterStyle}>{row}</Animated.View>
  ) : (
    row
  );
});

export const History = memo(function History({
  entries,
  grouping,
  still,
  onUse,
  onCopy,
}: Props) {
  const p = usePalette();
  const scroll = useRef<ScrollView>(null);
  const viewport = useRef(0);
  // Rows present on first render appear without animation.
  const initial = useRef<Set<string> | null>(null);
  if (initial.current === null) {
    initial.current = new Set(entries.map(e => e.id));
  }
  const visible =
    entries.length > VISIBLE_ROWS ? entries.slice(-VISIBLE_ROWS) : entries;

  // The newest calculation sits at the bottom, next to the display. A scroll
  // view keeps its offset from the top when it gets shorter (the scientific
  // keys opening), which would push the newest rows out of view, so it is
  // pinned back to the end whenever its height changes.
  const onViewport = (e: LayoutChangeEvent) => {
    const h = e.nativeEvent.layout.height;
    if (h !== viewport.current) {
      viewport.current = h;
      scroll.current?.scrollToEnd({ animated: false });
    }
  };

  return (
    <View
      style={[
        styles.card,
        { backgroundImage: p.card, borderColor: p.cardBorder },
      ]}
    >
      {visible.length === 0 ? (
        <View style={styles.empty}>
          <Text
            style={[styles.emptyTitle, { color: p.inkMuted }]}
            maxFontSizeMultiplier={1.3}
          >
            No calculations yet
          </Text>
          <Text
            style={[styles.emptyText, { color: p.inkFaint }]}
            maxFontSizeMultiplier={1.3}
          >
            Results appear here. Tap one to reuse it.
          </Text>
        </View>
      ) : (
        <ScrollView
          ref={scroll}
          onLayout={onViewport}
          onContentSizeChange={() =>
            scroll.current?.scrollToEnd({ animated: !still })
          }
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        >
          {visible.map(entry => (
            <Row
              key={entry.id}
              entry={entry}
              grouping={grouping}
              animateIn={!still && !initial.current!.has(entry.id)}
              onUse={onUse}
              onCopy={onCopy}
            />
          ))}
        </ScrollView>
      )}
    </View>
  );
});

const styles = StyleSheet.create({
  card: {
    flex: 1,
    minHeight: 64,
    marginHorizontal: 18,
    borderRadius: 28,
    borderWidth: 1,
    overflow: 'hidden',
  },
  list: {
    flexGrow: 1,
    justifyContent: 'flex-end',
    paddingVertical: 10,
  },
  row: {
    paddingHorizontal: 20,
    paddingVertical: 7,
    alignItems: 'flex-end',
  },
  expr: {
    fontFamily: fonts.regular,
    fontSize: 14,
    lineHeight: 19,
    textAlign: 'right',
    fontVariant: ['tabular-nums'],
  },
  result: {
    fontFamily: fonts.medium,
    fontSize: 19,
    lineHeight: 25,
    textAlign: 'right',
    fontVariant: ['tabular-nums'],
  },
  empty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    gap: 4,
  },
  emptyTitle: {
    fontFamily: fonts.medium,
    fontSize: 15,
    textAlign: 'center',
  },
  emptyText: {
    fontFamily: fonts.regular,
    fontSize: 13,
    textAlign: 'center',
  },
});
