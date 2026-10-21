import { StyleSheet, View } from 'react-native';
import { lockScreenManagedByVendor, type WallpaperTarget } from '@devdarshan/native';
import { AppText, Icon, Sheet, Touchable, useTheme, type IconName } from '@devdarshan/ui';

const OPTIONS: { target: WallpaperTarget; icon: IconName; title: string; description: string }[] = [
  { target: 'home', icon: 'smartphone', title: 'Home Screen', description: 'Behind your apps' },
  { target: 'lock', icon: 'lock', title: 'Lock Screen', description: 'When your phone is locked' },
  { target: 'both', icon: 'layers', title: 'Both Screens', description: 'Home and Lock screen' },
];

export function SetWallpaperSheet({
  visible,
  onClose,
  onSelect,
  manufacturer,
}: {
  visible: boolean;
  onClose: () => void;
  onSelect: (target: WallpaperTarget) => void;
  manufacturer?: string | null;
}) {
  const { colors, spacing, radii } = useTheme();
  const note = lockScreenManagedByVendor(manufacturer);
  return (
    <Sheet visible={visible} onClose={onClose} title="Set as wallpaper" subtitle="Uses the full-quality image">
      <View style={{ paddingHorizontal: spacing.lg, gap: spacing.sm }}>
        {OPTIONS.map((option) => (
          <Touchable
            key={option.target}
            testID={`set-${option.target}`}
            onPress={() => onSelect(option.target)}
            accessibilityRole="button"
            accessibilityLabel={`Set on ${option.title}`}
            style={[styles.option, { backgroundColor: colors.surfaceAlt, borderRadius: radii.md }]}
          >
            <View style={[styles.iconWrap, { backgroundColor: colors.primarySoft }]}>
              <Icon name={option.icon} size={20} color={colors.primary} />
            </View>
            <View style={{ flex: 1 }}>
              <AppText variant="bodyStrong">{option.title}</AppText>
              <AppText variant="caption" color="textMuted">
                {option.description}
              </AppText>
            </View>
            <Icon name="chevronRight" size={18} color={colors.textSubtle} />
          </Touchable>
        ))}
        {note ? (
          <View style={[styles.note, { backgroundColor: colors.goldSoft, borderRadius: radii.sm }]}>
            <Icon name="info" size={16} color={colors.gold} />
            <AppText variant="caption" color="text" style={{ flex: 1 }}>
              {note}
            </AppText>
          </View>
        ) : null}
      </View>
    </Sheet>
  );
}

const styles = StyleSheet.create({
  option: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    overflow: 'hidden',
  },
  iconWrap: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
  },
  note: {
    flexDirection: 'row',
    gap: 8,
    padding: 10,
    marginTop: 4,
  },
});
