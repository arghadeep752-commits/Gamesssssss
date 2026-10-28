import { useMemo } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';
import { useNav } from '../app/navigation';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { Logo } from '../components/Logo';
import { TabBar } from '../components/TabBar';
import { Card, ProgressBar, Screen, TierBadge } from '../components/ui';
import { DAILY_REWARD, TIER_LABEL } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TYPE } from '../config/theme';
import { useTodayKey } from '../hooks/useTodayKey';
import { LEVEL_COUNT, levelId } from '../levels';
import { dailyTier } from '../levels/daily';
import { tierForLevel } from '../levels/tierParams';
import { playSfx } from '../services/audio';
import { deriveStats } from '../state/achievements';
import { useStore } from '../state/store';
import { plural } from '../utils/format';

export function HomeScreen() {
  const nav = useNav();
  const { save } = useStore();
  const today = useTodayKey();
  const stats = useMemo(() => deriveStats(save), [save]);

  // Continue an unfinished puzzle if there is one, otherwise the first uncleared level.
  const frontier = useMemo(() => {
    for (let n = 1; n <= save.progress.unlockedUpTo; n++) if (!save.progress.best[levelId(n)]) return n;
    return null; // everything unlocked is cleared (all 100 when unlockedUpTo is the last level)
  }, [save.progress]);
  const session = save.session;
  const resumeLevel = session && session.levelNumber > 0 ? session.levelNumber : null;
  const resumeDaily = session && session.levelNumber === 0 && session.dailyKey === today;
  const playLevel = resumeLevel ?? frontier;

  const daily = save.daily.records[today];
  const tier = dailyTier(today);

  const onPlay = () => {
    if (playLevel) nav.push({ name: 'game', mode: 'level', level: playLevel });
    else nav.push({ name: 'levels' });
  };

  let playLabel: string;
  if (resumeLevel) playLabel = `Continue · Level ${resumeLevel}`;
  else if (frontier) playLabel = frontier === 1 && stats.completedLevels === 0 ? 'Play' : `Play · Level ${frontier}`;
  else playLabel = 'Replay levels';

  return (
    <Screen bottomInset={false}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.hero}>
          <Logo size={76} />
          <Text style={[TYPE.display, styles.title]}>Arrow Flow</Text>
          <Text style={styles.tagline}>Slide every arrow out. Find the order.</Text>
        </View>

        <Card style={styles.card}>
          <View style={styles.cardHead}>
            <Text style={TYPE.heading}>{playLevel ? `Level ${playLevel}` : 'All levels cleared'}</Text>
            {playLevel ? <TierBadge tier={tierForLevel(playLevel)} small /> : null}
          </View>
          <ProgressBar value={stats.completedLevels / LEVEL_COUNT} />
          <View style={styles.metaRow}>
            <Text style={styles.meta}>
              {stats.completedLevels} of {LEVEL_COUNT} levels
            </Text>
            <View style={styles.starMeta}>
              <Icon name="star" size={15} filled color={COLORS.star} />
              <Text style={styles.meta}>{stats.totalStars}</Text>
            </View>
          </View>
          <Button label={playLabel} icon="play" onPress={onPlay} />
          <Button label="Choose level" icon="grid" variant="secondary" onPress={() => nav.push({ name: 'levels' })} />
        </Card>

        <Pressable
          onPress={() => {
            playSfx('tap');
            nav.resetTo({ name: 'daily' });
          }}
          accessibilityRole="button"
          accessibilityLabel="Daily Challenge"
          style={({ pressed }) => [styles.daily, pressed && styles.pressed]}
        >
          <View style={styles.dailyIcon}>
            <Icon name="calendar" size={24} color={COLORS.white} />
          </View>
          <View style={styles.dailyText}>
            <Text style={TYPE.heading}>Daily Challenge</Text>
            <Text style={styles.meta}>
              {daily?.completed
                ? 'Completed today'
                : resumeDaily
                  ? 'In progress'
                  : `Today: ${TIER_LABEL[tier]} · +${plural(DAILY_REWARD[tier], 'hint')}`}
            </Text>
          </View>
          {daily?.completed ? (
            <Icon name="check" size={22} color={COLORS.hint} strokeWidth={2.6} />
          ) : (
            <Icon name="chevron" size={20} color={COLORS.muted} />
          )}
        </Pressable>

        {!save.onboardingDone ? (
          <Pressable
            onPress={() => {
              playSfx('tap');
              nav.push({ name: 'help' });
            }}
            style={({ pressed }) => [styles.howTo, pressed && styles.pressed]}
            accessibilityRole="button"
          >
            <Icon name="help" size={20} color={COLORS.inkSoft} />
            <Text style={styles.howToText}>New here? See how to play</Text>
          </Pressable>
        ) : null}
      </ScrollView>
      <TabBar current="home" badge={daily?.completed ? null : 'daily'} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: SPACE.lg, gap: SPACE.lg, paddingBottom: SPACE.xxl },
  hero: { alignItems: 'center', paddingTop: SPACE.xl, paddingBottom: SPACE.sm, gap: SPACE.sm },
  title: { marginTop: SPACE.sm },
  tagline: { fontSize: 15, color: COLORS.inkSoft },
  card: { padding: SPACE.lg, gap: SPACE.md },
  cardHead: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginTop: -SPACE.xs },
  meta: { fontSize: 13, color: COLORS.inkSoft, fontWeight: '600' },
  starMeta: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  daily: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: SPACE.md,
    padding: SPACE.lg,
    backgroundColor: COLORS.surface,
    borderRadius: RADIUS.lg,
    borderWidth: 1,
    borderColor: COLORS.border,
  },
  dailyIcon: {
    width: 44,
    height: 44,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.hint,
    alignItems: 'center',
    justifyContent: 'center',
  },
  dailyText: { flex: 1, gap: 2 },
  pressed: { opacity: 0.8 },
  howTo: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: SPACE.sm, padding: SPACE.md },
  howToText: { fontSize: 14, color: COLORS.inkSoft, fontWeight: '600' },
});
