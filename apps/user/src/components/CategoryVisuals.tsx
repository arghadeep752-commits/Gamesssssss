import { Image } from 'expo-image';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { categoryLabel, formatCount, type Category } from '@devdarshan/shared';
import { AppText, Touchable, useTheme } from '@devdarshan/ui';

function hash(value: string): number {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) h = (h * 31 + value.charCodeAt(i)) | 0;
  return Math.abs(h);
}

/** The deity's name in Devanagari (last word, e.g. "राम" from "श्री राम") as artwork. */
function monogramText(category: Category): string {
  const hi = category.nameHi.trim();
  if (hi) {
    const words = hi.split(/\s+/);
    return words[words.length - 1] ?? hi;
  }
  return category.name.trim().charAt(0).toUpperCase() || 'ॐ';
}

export function CategoryArtwork({ category, size, radius }: { category: Category; size: { width: number; height: number }; radius: number }) {
  const { colors } = useTheme();
  const tones: [string, string][] = [
    [colors.primarySoft, colors.onPrimarySoft],
    [colors.secondarySoft, colors.onSecondarySoft],
    [colors.goldSoft, colors.gold],
  ];
  const [bg, fg] = tones[hash(category.id) % tones.length] ?? tones[0]!;
  const uri = category.coverThumbUrl ?? category.coverUrl;
  return (
    <View style={[styles.art, { width: size.width, height: size.height, borderRadius: radius, backgroundColor: bg }]}>
      {uri ? (
        <Image
          source={{ uri }}
          placeholder={category.coverPlaceholder ? { uri: category.coverPlaceholder } : undefined}
          contentFit="cover"
          transition={140}
          recyclingKey={category.id}
          style={StyleSheet.absoluteFill}
        />
      ) : (
        <AppText
          variant="title"
          color={fg}
          numberOfLines={1}
          adjustsFontSizeToFit
          style={{ fontSize: Math.min(28, size.height * 0.34), lineHeight: Math.min(40, size.height * 0.5), paddingHorizontal: 6 }}
        >
          {monogramText(category)}
        </AppText>
      )}
    </View>
  );
}

/** Compact round-rect card for the Home screen's horizontal category strip. */
export const CategoryBubble = memo(function CategoryBubble({ category, onPress }: { category: Category; onPress: () => void }) {
  const { radii } = useTheme();
  return (
    <Touchable onPress={onPress} accessibilityRole="button" accessibilityLabel={category.name} style={styles.bubble}>
      <CategoryArtwork category={category} size={{ width: 68, height: 68 }} radius={radii.lg} />
      <AppText variant="caption" numberOfLines={1} align="center" style={styles.bubbleLabel}>
        {categoryLabel(category)}
      </AppText>
    </Touchable>
  );
});

/** Grid card for the Categories screen. */
export const CategoryCard = memo(function CategoryCard({
  category,
  width,
  onPress,
}: {
  category: Category;
  width: number;
  onPress: () => void;
}) {
  const { radii } = useTheme();
  const height = Math.round(width * 0.78);
  return (
    <Touchable onPress={onPress} accessibilityRole="button" accessibilityLabel={category.name} style={{ width, borderRadius: radii.md, overflow: 'hidden' }}>
      <CategoryArtwork category={category} size={{ width, height }} radius={radii.md} />
      <View style={styles.cardText}>
        <AppText variant="subheading" numberOfLines={1}>
          {category.name}
        </AppText>
        <View style={styles.cardMeta}>
          {category.nameHi && category.nameHi !== category.name ? (
            <AppText variant="caption" color="textMuted" numberOfLines={1} style={{ flexShrink: 1 }}>
              {category.nameHi}
            </AppText>
          ) : null}
          {category.wallpaperCount > 0 ? (
            <AppText variant="caption" color="textSubtle">
              {category.nameHi ? ' · ' : ''}
              {formatCount(category.wallpaperCount)}
            </AppText>
          ) : null}
        </View>
      </View>
    </Touchable>
  );
});

const styles = StyleSheet.create({
  art: {
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bubble: {
    width: 80,
    alignItems: 'center',
    borderRadius: 12,
    overflow: 'hidden',
    paddingVertical: 4,
  },
  bubbleLabel: {
    marginTop: 6,
    width: 78,
  },
  cardText: {
    paddingTop: 8,
    paddingBottom: 4,
    paddingHorizontal: 2,
  },
  cardMeta: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
