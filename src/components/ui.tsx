import React, { memo } from 'react';
import {
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
  type StyleProp,
  type ViewStyle,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNav } from '../app/navigation';
import { TIER_LABEL } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TIER_COLORS, TYPE } from '../config/theme';
import type { Tier } from '../game/types';
import { playSfx } from '../services/audio';
import { IconButton } from './Button';
import { Icon, type IconName } from './Icon';

/** Full-screen container that respects Android edge-to-edge safe areas. */
export function Screen({
  children,
  bottomInset = true,
  style,
}: {
  children: React.ReactNode;
  bottomInset?: boolean;
  style?: StyleProp<ViewStyle>;
}) {
  const insets = useSafeAreaInsets();
  return (
    <View
      style={[
        styles.screen,
        { paddingTop: insets.top, paddingBottom: bottomInset ? insets.bottom : 0, paddingLeft: insets.left, paddingRight: insets.right },
        style,
      ]}
    >
      {children}
    </View>
  );
}

/** Title bar with a back button, used by secondary screens. */
export function TopBar({ title, right }: { title: string; right?: React.ReactNode }) {
  const nav = useNav();
  return (
    <View style={styles.topBar}>
      <IconButton icon="back" label="Back" onPress={nav.pop} />
      <Text style={[TYPE.heading, styles.topTitle]} numberOfLines={1} accessibilityRole="header">
        {title}
      </Text>
      <View style={styles.topRight}>{right}</View>
    </View>
  );
}

/** Scrollable page body for secondary screens. */
export function Page({ children }: { children: React.ReactNode }) {
  return (
    <ScrollView contentContainerStyle={styles.page} showsVerticalScrollIndicator={false}>
      {children}
    </ScrollView>
  );
}

export const TierBadge = memo(function TierBadge({ tier, small }: { tier: Tier; small?: boolean }) {
  const color = TIER_COLORS[tier];
  return (
    <View style={[styles.badge, small && styles.badgeSmall, { borderColor: color }]}>
      <Text style={[styles.badgeText, small && styles.badgeTextSmall, { color }]}>{TIER_LABEL[tier].toUpperCase()}</Text>
    </View>
  );
});

export function Card({ children, style }: { children: React.ReactNode; style?: StyleProp<ViewStyle> }) {
  return <View style={[styles.card, style]}>{children}</View>;
}

export function SectionTitle({ children }: { children: string }) {
  return <Text style={styles.section}>{children.toUpperCase()}</Text>;
}

export const ListRow = memo(function ListRow({
  icon,
  label,
  value,
  onPress,
  danger,
  last,
}: {
  icon: IconName;
  label: string;
  value?: string;
  onPress: () => void;
  danger?: boolean;
  last?: boolean;
}) {
  const tint = danger ? COLORS.error : COLORS.ink;
  return (
    <Pressable
      onPress={() => {
        playSfx('tap');
        onPress();
      }}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => [styles.row, !last && styles.rowDivider, pressed && styles.rowPressed]}
    >
      <Icon name={icon} size={20} color={tint} />
      <Text style={[styles.rowLabel, { color: tint }]}>{label}</Text>
      {value ? <Text style={styles.rowValue}>{value}</Text> : null}
      <Icon name="chevron" size={18} color={COLORS.muted} />
    </Pressable>
  );
});

export const ToggleRow = memo(function ToggleRow({
  icon,
  label,
  detail,
  value,
  onChange,
  last,
}: {
  icon: IconName;
  label: string;
  detail?: string;
  value: boolean;
  onChange: (v: boolean) => void;
  last?: boolean;
}) {
  return (
    <View style={[styles.row, !last && styles.rowDivider]}>
      <Icon name={icon} size={20} color={COLORS.ink} />
      <View style={styles.toggleText}>
        <Text style={styles.rowLabel}>{label}</Text>
        {detail ? <Text style={styles.detail}>{detail}</Text> : null}
      </View>
      <Switch
        value={value}
        onValueChange={onChange}
        accessibilityLabel={label}
        trackColor={{ false: COLORS.border, true: COLORS.ink }}
        thumbColor={COLORS.white}
      />
    </View>
  );
});

export const ProgressBar = memo(function ProgressBar({ value, color = COLORS.ink }: { value: number; color?: string }) {
  const pct = Math.max(0, Math.min(1, value));
  return (
    <View style={styles.barTrack}>
      <View style={[styles.barFill, { width: `${pct * 100}%`, backgroundColor: color }]} />
    </View>
  );
});

export function StatTile({ label, value }: { label: string; value: string | number }) {
  return (
    <View style={styles.stat}>
      <Text style={styles.statValue}>{value}</Text>
      <Text style={styles.statLabel}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: { flex: 1, backgroundColor: COLORS.background },
  topBar: {
    height: 56,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACE.sm,
  },
  topTitle: { flex: 1, textAlign: 'center' },
  topRight: { width: 44, alignItems: 'center' },
  page: { paddingHorizontal: SPACE.lg, paddingBottom: SPACE.xxl, gap: SPACE.lg },
  badge: {
    borderWidth: 1.5,
    borderRadius: RADIUS.pill,
    paddingHorizontal: 10,
    paddingVertical: 3,
    alignSelf: 'center',
  },
  badgeSmall: { paddingHorizontal: 7, paddingVertical: 1 },
  badgeText: { fontSize: 11, fontWeight: '800', letterSpacing: 0.8 },
  badgeTextSmall: { fontSize: 9 },
  card: {
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: COLORS.border,
    overflow: 'hidden',
  },
  section: { ...TYPE.caption, letterSpacing: 1, marginBottom: -SPACE.sm, marginLeft: SPACE.xs },
  row: {
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: SPACE.lg,
    gap: SPACE.md,
    backgroundColor: COLORS.surface,
  },
  rowDivider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: COLORS.border },
  rowPressed: { backgroundColor: COLORS.surfaceAlt },
  rowLabel: { flex: 1, fontSize: 15, fontWeight: '600', color: COLORS.ink },
  rowValue: { fontSize: 14, color: COLORS.inkSoft, marginRight: SPACE.xs },
  toggleText: { flex: 1, paddingVertical: SPACE.md },
  detail: { ...TYPE.caption, marginTop: 2 },
  barTrack: { height: 8, borderRadius: 4, backgroundColor: COLORS.surfaceAlt, overflow: 'hidden' },
  barFill: { height: '100%', borderRadius: 4 },
  stat: {
    flexGrow: 1,
    flexBasis: '30%',
    paddingVertical: SPACE.md,
    paddingHorizontal: SPACE.sm,
    alignItems: 'center',
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.md,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  statValue: { fontSize: 22, fontWeight: '800', color: COLORS.ink },
  statLabel: { ...TYPE.caption, marginTop: 2, textAlign: 'center' },
});
