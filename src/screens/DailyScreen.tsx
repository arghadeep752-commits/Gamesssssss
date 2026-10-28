import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useNav } from '../app/navigation';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { Stars } from '../components/Stars';
import { StaticBoard } from '../components/StaticBoard';
import { TabBar } from '../components/TabBar';
import { Card, Screen, StatTile, TierBadge } from '../components/ui';
import { DAILY_REWARD } from '../config/gameConfig';
import { COLORS, SPACE, TYPE } from '../config/theme';
import type { LevelDef } from '../game/types';
import { useTodayKey } from '../hooks/useTodayKey';
import { dailyLevel } from '../levels/daily';
import { currentStreak } from '../state/progress';
import { useStore } from '../state/store';
import { formatLongDate, plural } from '../utils/format';

export function DailyScreen() {
  const nav = useNav();
  const { save } = useStore();
  const today = useTodayKey();
  const { width } = useWindowDimensions();
  const [level, setLevel] = useState<LevelDef | null>(null);

  // The puzzle is generated from the date, after the screen has appeared.
  useEffect(() => {
    setLevel(null);
    // Let the screen paint first; generation then takes a few milliseconds.
    const t = setTimeout(() => setLevel(dailyLevel(today)), 32);
    return () => clearTimeout(t);
  }, [today]);

  const record = save.daily.records[today];
  const inProgress = save.session?.dailyKey === today;
  const streak = currentStreak(save, today);
  const status = record?.completed ? 'Completed' : inProgress || record?.played ? 'In progress' : 'Not played yet';
  const previewCell = level ? Math.floor(Math.min((width - 96) / level.width, 220 / level.height)) : 0;

  return (
    <Screen bottomInset={false}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <Text style={[TYPE.title, styles.heading]} accessibilityRole="header">
          Daily Challenge
        </Text>
        <Text style={styles.date}>{formatLongDate(today)}</Text>

        <Card style={styles.card}>
          {level ? (
            <>
              <View style={styles.row}>
                <TierBadge tier={level.tier} />
                <Text style={styles.reward}>
                  {record?.rewardClaimed ? 'Reward claimed' : `Reward +${plural(DAILY_REWARD[level.tier], 'hint')}`}
                </Text>
              </View>
              <View style={styles.preview}>
                <StaticBoard level={level} cell={previewCell} />
              </View>
              <View style={styles.row}>
                <Text style={styles.status}>{status}</Text>
                {record?.best ? <Stars count={record.best.stars} size={18} /> : null}
              </View>
              <Button
                label={record?.completed ? 'Play again' : inProgress ? 'Continue' : 'Play'}
                icon="play"
                onPress={() => nav.push({ name: 'game', mode: 'daily', dateKey: today })}
              />
            </>
          ) : (
            <View style={styles.loading}>
              <ActivityIndicator color={COLORS.ink} />
              <Text style={styles.status}>Preparing today's puzzle</Text>
            </View>
          )}
        </Card>

        <View style={styles.stats}>
          <StatTile label="Current streak" value={streak} />
          <StatTile label="Best streak" value={save.daily.bestStreak} />
          <StatTile label="Completed" value={save.daily.completedCount} />
        </View>

        <View style={styles.note}>
          <Icon name="info" size={18} color={COLORS.muted} />
          <Text style={styles.noteText}>
            A new puzzle arrives every day at midnight. It works offline, and finishing it on consecutive days builds
            your streak.
          </Text>
        </View>
      </ScrollView>
      <TabBar current="daily" badge={record?.completed ? null : 'daily'} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: SPACE.lg, gap: SPACE.lg, paddingBottom: SPACE.xxl },
  heading: { marginTop: SPACE.lg },
  date: { fontSize: 15, color: COLORS.inkSoft, marginTop: -SPACE.md },
  card: { padding: SPACE.lg, gap: SPACE.md },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  reward: { fontSize: 13, fontWeight: '700', color: COLORS.hint },
  preview: { alignItems: 'center', paddingVertical: SPACE.sm },
  status: { fontSize: 14, fontWeight: '600', color: COLORS.inkSoft },
  loading: { alignItems: 'center', gap: SPACE.sm, paddingVertical: SPACE.xxl },
  stats: { flexDirection: 'row', gap: SPACE.sm },
  note: { flexDirection: 'row', gap: SPACE.sm, paddingHorizontal: SPACE.xs },
  noteText: { flex: 1, fontSize: 13, lineHeight: 19, color: COLORS.muted },
});
