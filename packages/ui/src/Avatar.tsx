import { Image } from 'expo-image';
import { StyleSheet, View } from 'react-native';
import { AppText } from './AppText';
import { Icon } from './Icon';
import { useTheme } from './theme';

export function Avatar({ uri, name, size = 36 }: { uri?: string | null; name?: string | null; size?: number }) {
  const { colors } = useTheme();
  const initial = (name ?? '').trim().charAt(0).toUpperCase();
  const style = { width: size, height: size, borderRadius: size / 2 };
  if (uri) {
    return (
      <Image
        source={{ uri }}
        style={[style, { backgroundColor: colors.surfaceAlt }]}
        cachePolicy="disk"
        contentFit="cover"
        accessibilityLabel={name ? `${name}'s profile photo` : 'Profile photo'}
        transition={120}
      />
    );
  }
  return (
    <View style={[style, styles.fallback, { backgroundColor: colors.primarySoft }]}>
      {initial ? (
        <AppText variant="subheading" color="onPrimarySoft" style={{ fontSize: size * 0.42, lineHeight: size * 0.6 }}>
          {initial}
        </AppText>
      ) : (
        <Icon name="user" size={size * 0.5} color={colors.onPrimarySoft} />
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  fallback: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});
