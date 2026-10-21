import { StyleSheet, View } from 'react-native';
import { formatCount } from '@devdarshan/shared';
import { AppText, Card, Icon, Touchable, useTheme, type IconName } from '@devdarshan/ui';

export function StatCard({
  icon,
  label,
  value,
  hint,
  tone = 'default',
  onPress,
}: {
  icon: IconName;
  label: string;
  value: number;
  hint?: string;
  tone?: 'default' | 'warning';
  onPress?: () => void;
}) {
  const { colors, spacing } = useTheme();
  const accent = tone === 'warning' && value > 0 ? colors.warning : colors.primary;
  const body = (
    <Card style={[styles.card, { padding: spacing.md }]}>
      <View style={styles.top}>
        <Icon name={icon} size={18} color={accent} />
        <AppText variant="caption" color="textMuted" numberOfLines={1} style={{ flex: 1 }}>
          {label}
        </AppText>
      </View>
      <AppText variant="display" style={{ marginTop: spacing.xs, color: tone === 'warning' && value > 0 ? colors.warning : colors.text }}>
        {formatCount(value)}
      </AppText>
      {hint ? (
        <AppText variant="caption" color="textSubtle" numberOfLines={1}>
          {hint}
        </AppText>
      ) : null}
    </Card>
  );
  if (!onPress) return <View style={styles.wrap}>{body}</View>;
  return (
    <Touchable onPress={onPress} accessibilityRole="button" accessibilityLabel={label} style={[styles.wrap, { borderRadius: 12, overflow: 'hidden' }]}>
      {body}
    </Touchable>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flexBasis: '47%',
    flexGrow: 1,
  },
  card: {
    minHeight: 96,
  },
  top: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
});
