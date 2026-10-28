import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';
import { Icon } from '../components/Icon';
import { Card, Page, ProgressBar, Screen, SectionTitle, TopBar } from '../components/ui';
import { TIER_LABEL } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TIER_COLORS, TYPE } from '../config/theme';
import type { Tier } from '../game/types';
import { LEVEL_COUNT, levelId } from '../levels';
import { tierForLevel } from '../levels/tierParams';
import { ACHIEVEMENTS, deriveStats } from '../state/achievements';
import { useStore } from '../state/store';

const TIERS: readonly Tier[] = ['tutorial', 'easy', 'normal', 'hard', 'expert'];

export function AchievementsScreen() {
  const { save } = useStore();
  const stats = useMemo(() => deriveStats(save), [save]);

  // Awards: one medal per tier, earned by clearing (silver) or 3-starring (gold) every level in it.
  const awards = useMemo(
    () =>
      TIERS.map((tier) => {
        let total = 0;
        let cleared = 0;
        let perfect = 0;
        for (let n = 1; n <= LEVEL_COUNT; n++) {
          if (tierForLevel(n) !== tier) continue;
          total++;
          const b = save.progress.best[levelId(n)];
          if (b) cleared++;
          if (b?.stars === 3) perfect++;
        }
        const state = perfect === total ? 'gold' : cleared === total ? 'silver' : 'none';
        return { tier, total, cleared, perfect, state };
      }),
    [save.progress.best],
  );

  return (
    <Screen>
      <TopBar title="Awards & Achievements" />
      <Page>
        <SectionTitle>Awards</SectionTitle>
        <Card style={styles.awards}>
          {awards.map((a) => (
            <View key={a.tier} style={styles.award} accessibilityLabel={`${TIER_LABEL[a.tier]} medal: ${a.state}`}>
              <View
                style={[
                  styles.medal,
                  a.state === 'gold' && { backgroundColor: COLORS.star },
                  a.state === 'silver' && { backgroundColor: TIER_COLORS[a.tier] },
                ]}
              >
                <Icon name="medal" size={24} color={a.state === 'none' ? COLORS.muted : COLORS.white} />
              </View>
              <Text style={styles.awardName}>{TIER_LABEL[a.tier]}</Text>
              <Text style={styles.awardSub}>
                {a.state === 'gold' ? 'All 3★' : `${a.cleared}/${a.total}`}
              </Text>
            </View>
          ))}
        </Card>
        <Text style={styles.legend}>Clear every level in a tier for a medal; earn 3 stars on all of them for gold.</Text>

        <SectionTitle>Achievements</SectionTitle>
        <Card>
          {ACHIEVEMENTS.map((a, i) => {
            const progress = Math.min(a.target, a.progress(save, stats));
            const done = !!save.achievements[a.id];
            return (
              <View key={a.id} style={[styles.row, i < ACHIEVEMENTS.length - 1 && styles.divider]}>
                <View style={[styles.badge, done && styles.badgeDone]}>
                  <Icon name={done ? 'trophy' : 'lock'} size={20} color={done ? COLORS.white : COLORS.muted} />
                </View>
                <View style={styles.text}>
                  <Text style={[styles.title, !done && styles.titleLocked]}>{a.title}</Text>
                  <Text style={styles.desc}>{a.description}</Text>
                  {!done && a.target > 1 ? (
                    <View style={styles.progress}>
                      <View style={styles.flex}>
                        <ProgressBar value={progress / a.target} color={COLORS.hint} />
                      </View>
                      <Text style={styles.count}>
                        {progress}/{a.target}
                      </Text>
                    </View>
                  ) : null}
                </View>
                {done ? <Icon name="check" size={20} color={COLORS.hint} strokeWidth={2.6} /> : null}
              </View>
            );
          })}
        </Card>
      </Page>
    </Screen>
  );
}

const styles = StyleSheet.create({
  awards: { flexDirection: 'row', justifyContent: 'space-between', padding: SPACE.md },
  award: { alignItems: 'center', gap: 4, flex: 1 },
  medal: {
    width: 46,
    height: 46,
    borderRadius: 23,
    backgroundColor: COLORS.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
  },
  awardName: { fontSize: 11, fontWeight: '700', color: COLORS.ink },
  awardSub: { fontSize: 11, color: COLORS.muted, fontWeight: '600' },
  legend: { ...TYPE.caption, marginTop: -SPACE.sm, marginHorizontal: SPACE.xs },
  row: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, padding: SPACE.lg },
  divider: { borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: COLORS.border },
  badge: {
    width: 40,
    height: 40,
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.surfaceAlt,
    alignItems: 'center',
    justifyContent: 'center',
  },
  badgeDone: { backgroundColor: COLORS.ink },
  text: { flex: 1, gap: 2 },
  title: { fontSize: 15, fontWeight: '700', color: COLORS.ink },
  titleLocked: { color: COLORS.inkSoft },
  desc: { fontSize: 13, color: COLORS.muted },
  progress: { flexDirection: 'row', alignItems: 'center', gap: SPACE.sm, marginTop: SPACE.xs },
  flex: { flex: 1 },
  count: { fontSize: 12, color: COLORS.inkSoft, fontWeight: '600' },
});
