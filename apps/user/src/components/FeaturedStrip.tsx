import { Image } from 'expo-image';
import { memo } from 'react';
import { FlatList, StyleSheet, View, useWindowDimensions } from 'react-native';
import type { Wallpaper } from '@devdarshan/shared';
import { AppText, Skeleton, Touchable, useTheme } from '@devdarshan/ui';

const FeaturedCard = memo(function FeaturedCard({
  wallpaper,
  width,
  onPress,
}: {
  wallpaper: Wallpaper;
  width: number;
  onPress: () => void;
}) {
  const { colors, radii } = useTheme();
  const height = Math.round(width / 0.62);
  return (
    <View style={{ width }}>
      <Touchable
        onPress={onPress}
        accessibilityRole="imagebutton"
        accessibilityLabel={wallpaper.title}
        style={{ width, height, borderRadius: radii.lg, overflow: 'hidden', backgroundColor: wallpaper.dominantColor ?? colors.imageBackdrop }}
      >
        <Image
          source={{ uri: wallpaper.previewUrl ?? wallpaper.thumbnailUrl ?? undefined }}
          placeholder={wallpaper.thumbnailUrl ? { uri: wallpaper.thumbnailUrl } : wallpaper.placeholder ? { uri: wallpaper.placeholder } : undefined}
          placeholderContentFit="cover"
          contentFit="cover"
          transition={180}
          recyclingKey={wallpaper.id}
          style={StyleSheet.absoluteFill}
        />
      </Touchable>
      <AppText variant="label" numberOfLines={1} style={{ marginTop: 8 }}>
        {wallpaper.title}
      </AppText>
    </View>
  );
});

/** "Today's Darshan": the admin-curated, ordered featured list. */
export function FeaturedStrip({
  wallpapers,
  loading,
  onOpen,
}: {
  wallpapers: Wallpaper[];
  loading: boolean;
  onOpen: (wallpaper: Wallpaper, index: number) => void;
}) {
  const { width } = useWindowDimensions();
  const cardWidth = Math.min(260, Math.round(width * 0.5));
  if (loading) {
    return (
      <View style={styles.row}>
        {[0, 1].map((i) => (
          <Skeleton key={i} style={{ width: cardWidth, height: Math.round(cardWidth / 0.62), marginRight: 12 }} />
        ))}
      </View>
    );
  }
  return (
    <FlatList
      horizontal
      data={wallpapers}
      keyExtractor={(w) => w.id}
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.list}
      ItemSeparatorComponent={() => <View style={{ width: 12 }} />}
      renderItem={({ item, index }) => <FeaturedCard wallpaper={item} width={cardWidth} onPress={() => onOpen(item, index)} />}
      initialNumToRender={3}
      windowSize={3}
      snapToInterval={cardWidth + 12}
      decelerationRate="fast"
    />
  );
}

const styles = StyleSheet.create({
  list: {
    paddingHorizontal: 16,
  },
  row: {
    flexDirection: 'row',
    paddingHorizontal: 16,
  },
});
