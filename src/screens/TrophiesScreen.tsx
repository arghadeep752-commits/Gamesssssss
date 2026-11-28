import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { addMonths, MONTHS_SHORT, monthKeyOf, monthProgress, todayKey } from '../state/dates';
import { useStore } from '../state/store';
import { Icon, type IconName } from '../ui/Icon';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

export function TrophiesScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save } = useStore();
  const current = monthKeyOf(todayKey());
  const months: string[] = [];
  for (let m = current; m >= save.since && months.length < 60; m = addMonths(m, -1)) months.push(m);
  if (!months.length) months.push(current);
  const earned = months.filter((m) => {
    const p = monthProgress(m, save.daily);
    return p.done === p.total;
  }).length;

  const stats: { icon: IconName; value: number; label: string }[] = [
    { icon: 'flame', value: save.stats.levels, label: 'Levels' },
    { icon: 'star', value: save.stats.stars, label: 'Stars' },
    { icon: 'sparkle', value: save.stats.perfect, label: 'Perfect' },
    { icon: 'calendar', value: save.stats.daily, label: 'Dailies' },
    { icon: 'arrowUR', value: save.stats.bestStreak, label: 'Best streak' },
    { icon: 'trophy', value: earned, label: 'Trophies' },
  ];

  return (
    <Animated.View collapsable={false} entering={FadeIn.duration(200)} style={styles.fill}>
      <ScrollView contentContainerStyle={[styles.root, { paddingTop: insets.top + 8 }]} showsVerticalScrollIndicator={false}>
        <Text style={[styles.h1, { color: t.text }]}>Trophies</Text>
        <View style={styles.stats}>
          {stats.map((s) => (
            <View key={s.label} style={styles.statWrap}>
            <View style={[styles.stat, { width: '100%', backgroundColor: t.surface, borderColor: t.border }]}>
              <Icon name={s.icon} size={20} color={s.icon === 'trophy' || s.icon === 'star' ? t.gold : t.accent} filled={s.icon !== 'arrowUR' && s.icon !== 'calendar'} />
              <Text style={[styles.statValue, { color: t.text }]}>{s.value}</Text>
              <Text style={[styles.statLabel, { color: t.sub }]}>{s.label}</Text>
            </View>
            </View>
          ))}
        </View>
        <Text style={[styles.h2, { color: t.sub }]}>Solve every daily challenge in a month to win its trophy.</Text>
        <View style={styles.grid}>
          {months.map((m) => {
            const p = monthProgress(m, save.daily);
            const won = p.done === p.total;
            const [y, mm] = m.split('-').map(Number);
            return (
              <View key={m} style={styles.cellWrap}>
                <View style={[styles.cell, { backgroundColor: won ? t.goldSoft : t.surface, borderColor: won ? t.gold : t.border }]}>
                  <Icon name="trophy" size={40} color={won ? t.gold : p.done ? t.sub : t.faint} filled={won} strokeWidth={1.6} />
                  <Text style={[styles.month, { color: t.text }]}>
                    {MONTHS_SHORT[mm - 1]} {y}
                  </Text>
                  <Text style={[styles.count, { color: won ? t.gold : t.sub }]}>
                    {p.done}/{p.total}
                  </Text>
                </View>
              </View>
            );
          })}
        </View>
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  root: { paddingHorizontal: SPACE.xl, gap: SPACE.lg, paddingBottom: SPACE.xl },
  h1: { fontSize: 28, fontWeight: '900', marginTop: 4 },
  h2: { fontSize: 14, fontWeight: '600' },
  stats: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -4 },
  stat: { width: '33.333%', alignItems: 'center', borderWidth: 1, borderRadius: RADIUS.md, paddingVertical: SPACE.md, gap: 2, borderColor: 'transparent' },
  statWrap: { width: '33.333%', padding: 4 },
  statValue: { fontSize: 20, fontWeight: '900' },
  statLabel: { fontSize: 12, fontWeight: '600' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -5 },
  cellWrap: { width: '33.333%', padding: 5 },
  cell: { alignItems: 'center', borderWidth: 1.5, borderRadius: RADIUS.md, paddingVertical: SPACE.lg, gap: 4 },
  month: { fontSize: 14, fontWeight: '800', marginTop: 4 },
  count: { fontSize: 13, fontWeight: '700' },
});
