import { memo, useCallback } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, useWindowDimensions, View } from 'react-native';
import { useNav } from '../app/navigation';
import { Icon } from '../components/Icon';
import { Stars } from '../components/Stars';
import { Screen, TopBar } from '../components/ui';
import { TIER_LABEL } from '../config/gameConfig';
import { COLORS, RADIUS, SPACE, TIER_COLORS, TYPE } from '../config/theme';
import type { Tier } from '../game/types';
import { LEVEL_COUNT, levelId } from '../levels';
import { tierForLevel } from '../levels/tierParams';
import { playSfx } from '../services/audio';
import type { BestResult } from '../state/saveSchema';
import { useStore } from '../state/store';

const COLUMNS = 5;
const GAP = 10;
const TIERS: readonly Tier[] = ['tutorial', 'easy', 'normal', 'hard', 'expert'];

const LevelTile = memo(function LevelTile({
  n,
  size,
  locked,
  best,
  onOpen,
}: {
  n: number;
  size: number;
  locked: boolean;
  best: BestResult | undefined;
  onOpen: (n: number) => void;
}) {
  return (
    <Pressable
      disabled={locked}
      onPress={() => onOpen(n)}
      accessibilityRole="button"
      accessibilityLabel={locked ? `Level ${n}, locked` : `Level ${n}${best ? `, ${best.stars} stars` : ''}`}
      style={({ pressed }) => [
        styles.tile,
        { width: size, height: size + 10 },
        best && styles.tileDone,
        locked && styles.tileLocked,
        pressed && styles.pressed,
      ]}
    >
      {locked ? (
        <Icon name="lock" size={18} color={COLORS.muted} />
      ) : (
        <>
          <Text style={[styles.num, best && styles.numDone]}>{n}</Text>
          <Stars count={best?.stars ?? 0} size={10} gap={1} />
        </>
      )}
    </Pressable>
  );
});

export function LevelSelectScreen() {
  const nav = useNav();
  const { save } = useStore();
  const { width } = useWindowDimensions();
  const size = Math.floor((Math.min(width, 520) - SPACE.lg * 2 - GAP * (COLUMNS - 1)) / COLUMNS);

  const open = useCallback(
    (n: number) => {
      playSfx('tap');
      nav.push({ name: 'game', mode: 'level', level: n });
    },
    [nav],
  );

  return (
    <Screen>
      <TopBar title="Levels" />
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        {TIERS.map((tier) => {
          const nums: number[] = [];
          for (let n = 1; n <= LEVEL_COUNT; n++) if (tierForLevel(n) === tier) nums.push(n);
          const done = nums.filter((n) => save.progress.best[levelId(n)]).length;
          return (
            <View key={tier} style={styles.section}>
              <View style={styles.sectionHead}>
                <View style={[styles.swatch, { backgroundColor: TIER_COLORS[tier] }]} />
                <Text style={TYPE.heading}>{TIER_LABEL[tier]}</Text>
                <Text style={styles.count}>
                  {done}/{nums.length}
                </Text>
              </View>
              <View style={[styles.grid, { gap: GAP }]}>
                {nums.map((n) => (
                  <LevelTile
                    key={n}
                    n={n}
                    size={size}
                    locked={n > save.progress.unlockedUpTo}
                    best={save.progress.best[levelId(n)]}
                    onOpen={open}
                  />
                ))}
              </View>
            </View>
          );
        })}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { paddingHorizontal: SPACE.lg, paddingBottom: SPACE.xxl, gap: SPACE.xl, alignSelf: 'center', maxWidth: 520 },
  section: { gap: SPACE.md },
  sectionHead: { flexDirection: 'row', alignItems: 'center', gap: SPACE.sm },
  swatch: { width: 10, height: 10, borderRadius: 5 },
  count: { marginLeft: 'auto', fontSize: 13, fontWeight: '600', color: COLORS.inkSoft },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  tile: {
    borderRadius: RADIUS.md,
    backgroundColor: COLORS.surface,
    borderWidth: 1,
    borderColor: COLORS.border,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
  },
  tileDone: { borderColor: COLORS.ink },
  tileLocked: { backgroundColor: COLORS.surfaceAlt, borderColor: COLORS.surfaceAlt },
  num: { fontSize: 18, fontWeight: '800', color: COLORS.inkSoft },
  numDone: { color: COLORS.ink },
  pressed: { opacity: 0.7 },
});
