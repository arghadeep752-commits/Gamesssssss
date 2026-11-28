import { memo } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';
import { getLevel } from '../game/levels';
import { monthKeyOf, monthProgress, prettyDate, todayKey } from '../state/dates';
import { CHEST_COINS, CHEST_EVERY, skinById } from '../state/economy';
import { useStore } from '../state/store';
import { Icon } from '../ui/Icon';
import { Btn, Chip, Pressy, ProgressBar, RoundBtn, TierBadge } from '../ui/kit';
import { MiniBoard } from '../ui/MiniBoard';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

/** Original logo mark: a snake-shaped arrow. */
const Logo = memo(function Logo({ color }: { color: string }) {
  return (
    <Svg width={54} height={54} viewBox="0 0 48 48">
      <Path d="M9 39V23h15V11h9" stroke={color} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d="M44 11L32 3.5v15z" fill={color} stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </Svg>
  );
});

export function HomeScreen({
  onPlay,
  onDaily,
  onSettings,
  onShop,
}: {
  onPlay: () => void;
  onDaily: () => void;
  onSettings: () => void;
  onShop: () => void;
}) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save } = useStore();
  const today = todayKey();
  const doneToday = !!save.daily[today];
  const month = monthProgress(monthKeyOf(today), save.daily);
  const next = getLevel(save.level);
  const skin = skinById(save.skin);
  const ink = t.dark ? skin.dark : skin.light;
  const toChest = CHEST_EVERY - save.chest;

  return (
    <Animated.View entering={FadeIn.duration(200)} style={styles.fill}>
      <ScrollView contentContainerStyle={[styles.root, { paddingTop: insets.top + 8 }]} showsVerticalScrollIndicator={false}>
        <View style={styles.topRow}>
          <View style={styles.chips}>
            <Chip coin text={String(save.coins)} onPress={onShop} label={`${save.coins} coins, open shop`} />
            <Chip icon="bulb" text={String(save.hints)} onPress={onShop} label={`${save.hints} hints`} />
          </View>
          <RoundBtn icon="gear" label="Settings" onPress={onSettings} size={42} />
        </View>

        <View style={styles.brand}>
          <Logo color={t.accent} />
          <Text style={[styles.brandTitle, { color: t.text }]}>Arrow Flow</Text>
          <Text style={[styles.brandSub, { color: t.sub }]}>Untangle the arrows. Tap them out in the right order.</Text>
        </View>

        <Pressy onPress={onPlay} label={`Play level ${save.level}`} style={[styles.levelCard, { backgroundColor: t.surface, borderColor: t.border }]}>
          <View style={styles.preview}>
            <MiniBoard level={next.level} maxW={170} maxH={150} ink={ink} dot={t.dot} />
          </View>
          <View style={styles.levelRow}>
            <Text style={[styles.levelLabel, { color: t.sub }]}>LEVEL</Text>
            <TierBadge tier={next.tier} />
          </View>
          <Text style={[styles.levelNum, { color: t.text }]}>{save.level}</Text>
        </Pressy>
        <Btn label="Play" icon="play" onPress={onPlay} style={styles.playBtn} />

        <View style={[styles.card, { backgroundColor: t.surface, borderColor: t.border }]}>
          <View style={[styles.cardIcon, { backgroundColor: t.goldSoft }]}>
            <Icon name="chest" size={24} color={t.gold} />
          </View>
          <View style={styles.cardBody}>
            <Text style={[styles.cardTitle, { color: t.text }]}>Reward chest</Text>
            <Text style={[styles.cardSub, { color: t.sub }]}>
              Clear {toChest} more {toChest === 1 ? 'level' : 'levels'} for {CHEST_COINS} coins + a hint
            </Text>
            <View style={styles.bar}>
              <ProgressBar value={save.chest / CHEST_EVERY} color={t.gold} track={t.surfaceAlt} height={5} />
            </View>
          </View>
        </View>

        <Pressy onPress={onDaily} label="Daily challenge" style={[styles.card, { backgroundColor: t.surface, borderColor: t.border }]}>
          <View style={[styles.cardIcon, { backgroundColor: doneToday ? t.success : t.accentSoft }]}>
            <Icon name={doneToday ? 'check' : 'calendar'} size={24} color={doneToday ? '#fff' : t.accent} strokeWidth={doneToday ? 3 : 2} />
          </View>
          <View style={styles.cardBody}>
            <Text style={[styles.cardTitle, { color: t.text }]}>Daily Challenge</Text>
            <Text style={[styles.cardSub, { color: t.sub }]}>
              {doneToday ? 'Done for today' : prettyDate(today)} · {month.done}/{month.total} this month
            </Text>
            <View style={styles.bar}>
              <ProgressBar value={month.done / month.total} color={t.gold} track={t.surfaceAlt} height={5} />
            </View>
          </View>
          <Icon name="trophy" size={26} color={month.done === month.total ? t.gold : t.faint} filled={month.done === month.total} />
        </Pressy>
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  fill: { flex: 1 },
  root: { flexGrow: 1, paddingHorizontal: SPACE.xl, gap: SPACE.lg, paddingBottom: SPACE.xl },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  chips: { flexDirection: 'row', gap: SPACE.sm },
  brand: { alignItems: 'center', gap: 4 },
  brandTitle: { fontSize: 32, fontWeight: '900', letterSpacing: 0.5, marginTop: 4 },
  brandSub: { fontSize: 14, fontWeight: '500', textAlign: 'center' },
  levelCard: { alignSelf: 'center', alignItems: 'center', borderWidth: 1, borderRadius: RADIUS.xl, paddingVertical: SPACE.lg, paddingHorizontal: SPACE.xxl, minWidth: 230 },
  preview: { height: 150, justifyContent: 'center', alignItems: 'center', marginBottom: SPACE.sm },
  levelRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  levelLabel: { fontSize: 13, fontWeight: '800', letterSpacing: 2 },
  levelNum: { fontSize: 42, fontWeight: '900', lineHeight: 48 },
  playBtn: { alignSelf: 'center', minWidth: 230 },
  card: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, borderWidth: 1, borderRadius: RADIUS.lg, padding: SPACE.lg },
  cardIcon: { width: 46, height: 46, borderRadius: 23, alignItems: 'center', justifyContent: 'center' },
  cardBody: { flex: 1, gap: 2 },
  cardTitle: { fontSize: 17, fontWeight: '800' },
  cardSub: { fontSize: 13, fontWeight: '500' },
  bar: { marginTop: 6 },
});
