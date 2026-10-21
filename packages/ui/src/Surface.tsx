import { StyleSheet, View, type StyleProp, type ViewProps, type ViewStyle } from 'react-native';
import { AppText } from './AppText';
import { Icon, type IconName } from './Icon';
import { useTheme } from './theme';
import { Touchable } from './Touchable';

export function Card({ style, children, ...rest }: ViewProps) {
  const { colors, radii } = useTheme();
  return (
    <View
      {...rest}
      style={[
        {
          backgroundColor: colors.surface,
          borderRadius: radii.md,
          borderWidth: StyleSheet.hairlineWidth,
          borderColor: colors.border,
        },
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function Divider({ style, inset = 0 }: { style?: StyleProp<ViewStyle>; inset?: number }) {
  const { colors } = useTheme();
  return <View style={[{ height: StyleSheet.hairlineWidth, backgroundColor: colors.border, marginLeft: inset }, style]} />;
}

export type BadgeTone = 'neutral' | 'primary' | 'success' | 'warning' | 'danger' | 'secondary';

export function Badge({ label, tone = 'neutral', icon }: { label: string; tone?: BadgeTone; icon?: IconName }) {
  const { colors, radii } = useTheme();
  const map: Record<BadgeTone, [string, string]> = {
    neutral: [colors.surfaceAlt, colors.textMuted],
    primary: [colors.primarySoft, colors.onPrimarySoft],
    secondary: [colors.secondarySoft, colors.onSecondarySoft],
    success: [colors.successSoft, colors.success],
    warning: [colors.warningSoft, colors.warning],
    danger: [colors.dangerSoft, colors.danger],
  };
  const [bg, fg] = map[tone];
  return (
    <View style={[styles.badge, { backgroundColor: bg, borderRadius: radii.pill }]}>
      {icon ? <Icon name={icon} size={12} color={fg} strokeWidth={2.2} /> : null}
      <AppText variant="overline" color={fg} style={{ letterSpacing: 0.4 }}>
        {label}
      </AppText>
    </View>
  );
}

export interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  icon?: IconName;
  testID?: string;
}

export function Chip({ label, selected = false, onPress, icon, testID }: ChipProps) {
  const { colors, radii } = useTheme();
  const bg = selected ? colors.primary : colors.surface;
  const fg = selected ? colors.onPrimary : colors.text;
  return (
    <Touchable
      testID={testID}
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[
        styles.chip,
        {
          backgroundColor: bg,
          borderRadius: radii.pill,
          borderColor: selected ? colors.primary : colors.border,
        },
      ]}
    >
      {icon ? <Icon name={icon} size={14} color={fg} /> : null}
      <AppText variant="label" color={fg} numberOfLines={1}>
        {label}
      </AppText>
    </Touchable>
  );
}

const styles = StyleSheet.create({
  badge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    alignSelf: 'flex-start',
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    height: 34,
    paddingHorizontal: 14,
    borderWidth: StyleSheet.hairlineWidth * 2,
    overflow: 'hidden',
  },
});
