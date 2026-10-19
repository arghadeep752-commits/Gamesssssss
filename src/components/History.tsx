/**
 * Glass history card. Newest calculation at the bottom, next to the display;
 * tap a line to reuse its result, long-press to copy it.
 */
import React, { memo, useEffect, useRef } from 'react';
import {
  Animated,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { Grouping, closedExpressionText, formatCanonical } from '../engine';
import type { TapeEntry } from '../state/calcReducer';
import { fonts, usePalette } from '../theme/theme';

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
  const enter = useRef(new Animated.Value(animateIn ? 0 : 1)).current;

  useEffect(() => {
    if (!animateIn) {
      return;
    }
    Animated.spring(enter, {
      toValue: 1,
      stiffness: 200,
      damping: 20,
      mass: 1,
      useNativeDriver: true,
    }).start();
  }, [animateIn, enter]);

  const expression = closedExpressionText(entry.tokens, grouping);
  const result = formatCanonical(entry.result, grouping);
  return (
    <Animated.View
      style={{
        opacity: enter,
        transform: [
          {
            translateY: enter.interpolate({
              inputRange: [0, 1],
              outputRange: [18, 0],
            }),
          },
        ],
      }}
    >
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
    </Animated.View>
  );
});

export function History({ entries, grouping, still, onUse, onCopy }: Props) {
  const p = usePalette();
  const scroll = useRef<ScrollView>(null);
  // Rows present on first render appear without animation.
  const initial = useRef<Set<string> | null>(null);
  if (initial.current === null) {
    initial.current = new Set(entries.map(e => e.id));
  }

  return (
    <View
      style={[
        styles.card,
        {
          backgroundColor: p.card,
          borderColor: p.cardBorder,
          backgroundImage: p.sheen,
        },
      ]}
    >
      {entries.length === 0 ? (
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
          onContentSizeChange={() =>
            scroll.current?.scrollToEnd({ animated: !still })
          }
          contentContainerStyle={styles.list}
          showsVerticalScrollIndicator={false}
        >
          {entries.map(entry => (
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
}

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
