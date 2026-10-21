import { Image } from 'expo-image';
import { memo, type ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { relativeTime, type Wallpaper } from '@devdarshan/shared';
import { AppText, Icon, Touchable, useTheme } from '@devdarshan/ui';
import { StatusBadge } from './StatusBadge';

export const WallpaperRow = memo(function WallpaperRow({
  wallpaper,
  categoryNames,
  onPress,
  right,
}: {
  wallpaper: Wallpaper;
  categoryNames?: string;
  onPress?: () => void;
  right?: ReactNode;
}) {
  const { colors, radii, spacing } = useTheme();
  return (
    <Touchable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityLabel={wallpaper.title}
      style={[styles.row, { paddingHorizontal: spacing.lg }]}
    >
      <View style={[styles.thumb, { borderRadius: radii.sm, backgroundColor: wallpaper.dominantColor ?? colors.imageBackdrop }]}>
        {wallpaper.thumbnailUrl ? (
          <Image
            source={{ uri: wallpaper.thumbnailUrl }}
            placeholder={wallpaper.placeholder ? { uri: wallpaper.placeholder } : undefined}
            contentFit="cover"
            recyclingKey={wallpaper.id}
            style={StyleSheet.absoluteFill}
          />
        ) : (
          <Icon name="image" size={20} color={colors.textSubtle} />
        )}
      </View>
      <View style={styles.texts}>
        <AppText variant="bodyStrong" numberOfLines={1}>
          {wallpaper.title || 'Untitled'}
        </AppText>
        {categoryNames ? (
          <AppText variant="caption" color="textMuted" numberOfLines={1}>
            {categoryNames}
          </AppText>
        ) : null}
        <View style={styles.meta}>
          <StatusBadge wallpaper={wallpaper} />
          {wallpaper.featured ? <Icon name="star" size={14} color={colors.gold} fill={colors.gold} /> : null}
          <AppText variant="caption" color="textSubtle">
            {relativeTime(wallpaper.createdAt)}
          </AppText>
        </View>
      </View>
      {right ?? (onPress ? <Icon name="chevronRight" size={18} color={colors.textSubtle} /> : null)}
    </Touchable>
  );
});

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingVertical: 10,
  },
  thumb: {
    width: 52,
    height: 88,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  texts: {
    flex: 1,
    gap: 3,
  },
  meta: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
});
