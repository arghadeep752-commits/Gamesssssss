import { memo } from 'react';
import { Pressable, StyleSheet, Text, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNav, type TabName } from '../app/navigation';
import { COLORS, SPACE } from '../config/theme';
import { playSfx } from '../services/audio';
import { Icon, type IconName } from './Icon';

const TABS: readonly { name: TabName; label: string; icon: IconName }[] = [
  { name: 'home', label: 'Main', icon: 'home' },
  { name: 'daily', label: 'Daily', icon: 'calendar' },
  { name: 'me', label: 'Me', icon: 'user' },
];

export const TabBar = memo(function TabBar({ current, badge }: { current: TabName; badge?: TabName | null }) {
  const nav = useNav();
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.bar, { paddingBottom: Math.max(insets.bottom, SPACE.sm) }]} accessibilityRole="tablist">
      {TABS.map((t) => {
        const active = t.name === current;
        return (
          <Pressable
            key={t.name}
            style={styles.tab}
            accessibilityRole="tab"
            accessibilityLabel={t.label}
            accessibilityState={{ selected: active }}
            onPress={() => {
              if (active) return;
              playSfx('tap');
              nav.resetTo({ name: t.name });
            }}
          >
            <View>
              <Icon name={t.icon} size={24} color={active ? COLORS.ink : COLORS.muted} />
              {badge === t.name ? <View style={styles.dot} /> : null}
            </View>
            <Text style={[styles.label, active && styles.labelActive]}>{t.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
});

const styles = StyleSheet.create({
  bar: {
    flexDirection: 'row',
    backgroundColor: COLORS.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: COLORS.border,
    paddingTop: SPACE.sm,
  },
  tab: { flex: 1, alignItems: 'center', justifyContent: 'center', minHeight: 48, gap: 2 },
  label: { fontSize: 12, fontWeight: '600', color: COLORS.muted },
  labelActive: { color: COLORS.ink },
  dot: {
    position: 'absolute',
    top: -1,
    right: -4,
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: COLORS.error,
  },
});
