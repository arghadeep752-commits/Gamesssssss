import { Image } from 'expo-image';
import { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import type { Wallpaper } from '@devdarshan/shared';
import { Icon, Touchable, useTheme } from '@devdarshan/ui';

export interface WallpaperTileProps {
  wallpaper: Wallpaper;
  width: number;
  height: number;
  liked?: boolean;
  onPress: () => void;
}

/** Grid cell: server-generated thumbnail over its blurred placeholder and dominant colour. */
export const WallpaperTile = memo(function WallpaperTile({ wallpaper, width, height, liked = false, onPress }: WallpaperTileProps) {
  const { colors, radii } = useTheme();
  return (
    <Touchable
      onPress={onPress}
      accessibilityRole="imagebutton"
      accessibilityLabel={wallpaper.title}
      style={[
        styles.tile,
        { width, height, borderRadius: radii.md, backgroundColor: wallpaper.dominantColor ?? colors.imageBackdrop },
      ]}
    >
      <Image
        source={wallpaper.thumbnailUrl ? { uri: wallpaper.thumbnailUrl } : undefined}
        placeholder={wallpaper.placeholder ? { uri: wallpaper.placeholder } : undefined}
        placeholderContentFit="cover"
        contentFit="cover"
        transition={160}
        recyclingKey={wallpaper.id}
        cachePolicy="memory-disk"
        style={StyleSheet.absoluteFill}
      />
      {liked ? (
        <View style={styles.liked} pointerEvents="none">
          <Icon name="heart" size={13} color="#FFFFFF" fill="#FFFFFF" strokeWidth={2} />
        </View>
      ) : null}
    </Touchable>
  );
});

const styles = StyleSheet.create({
  tile: {
    overflow: 'hidden',
  },
  liked: {
    position: 'absolute',
    top: 8,
    right: 8,
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: 'rgba(12,10,8,0.45)',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
