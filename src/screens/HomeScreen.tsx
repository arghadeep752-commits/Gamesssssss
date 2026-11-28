import { memo } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import Svg, { Path } from 'react-native-svg';
import { getLevel } from '../game/levels';
import { monthKeyOf, monthProgress, prettyDate, todayKey } from '../state/dates';
import { useStore } from '../state/store';
import { Icon } from '../ui/Icon';
import { Btn, Pressy, ProgressBar, RoundBtn } from '../ui/kit';
import { MiniBoard } from '../ui/MiniBoard';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

/** Original logo mark: a snake-shaped arrow. */
const Logo = memo(function Logo({ color }: { color: string }) {
  return (
    <Svg width={58} height={58} viewBox="0 0 48 48">
      <Path d="M9 39V23h15V11h9" stroke={color} strokeWidth={6} strokeLinecap="round" strokeLinejoin="round" fill="none" />
      <Path d="M44 11L32 3.5v15z" fill={color} stroke={color} strokeWidth={2} strokeLinejoin="round" />
    </Svg>
  );
});

export function HomeScreen({ onPlay, onDaily, onSettings }: { onPlay: () => void; onDaily: () => void; onSettings: () => void }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save } = useStore();
  const today = todayKey();
  const doneToday = !!save.daily[today];
  const month = monthProgress(monthKeyOf(today), save.daily);
  const preview = getLevel(save.level);

  return (
    <Animated.View entering={FadeIn.duration(200)} style={styles.fill}>
      <ScrollView contentContainerStyle={[styles.root, { paddingTop: insets.top + 8 }]} showsVerticalScrollIndicator={false}>
      <View style={styles.topRow}>
        <View style={[styles.hintChip, { backgroundColor: t.surface, borderColor: t.border }]}>
          <Icon name="bulb" size={18} color={t.accent} />
          <Text style={[styles.hintChipText, { color: t.text }]}>{save.hints}</Text>
        </View>
        <RoundBtn icon="gear" label="Settings" onPress={onSettings} size={44} />
      </View>

      <View style={styles.brand}>
        <Logo color={t.accent} />
        <Text style={[styles.brandTitle, { color: t.text }]}>Arrow Flow</Text>
        <Text style={[styles.brandSub, { color: t.sub }]}>Tap the arrows out in the right order</Text>
      </View>

      <Pressy onPress={onPlay} label={`Play level ${save.level}`} style={[styles.levelCard, { backgroundColor: t.surface, borderColor: t.border }]}>
        <View style={styles.preview}>
          <MiniBoard level={preview} maxW={150} maxH={150} ink={t.ink} dot={t.dot} />
        </View>
        <Text style={[styles.levelLabel, { color: t.sub }]}>LEVEL</Text>
        <Text style={[styles.levelNum, { color: t.text }]}>{save.level}</Text>
      </Pressy>
      <Btn label="Play" icon="play" onPress={onPlay} style={styles.playBtn} />

      <Pressy onPress={onDaily} label="Daily challenge" style={[styles.daily, { backgroundColor: t.surface, borderColor: t.border }]}>
        <View style={[styles.dailyIcon, { backgroundColor: doneToday ? t.success : t.accentSoft }]}>
          <Icon name={doneToday ? 'check' : 'calendar'} size={24} color={doneToday ? '#fff' : t.accent} strokeWidth={doneToday ? 3 : 2} />
        </View>
        <View style={styles.dailyBody}>
          <Text style={[styles.dailyTitle, { color: t.text }]}>Daily Challenge</Text>
          <Text style={[styles.dailySub, { color: t.sub }]}>
            {doneToday ? 'Done for today' : prettyDate(today)} · {month.done}/{month.total}
          </Text>
          <View style={styles.dailyBar}>
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
  hintChip: { flexDirection: 'row', alignItems: 'center', gap: 6, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, height: 36 },
  hintChipText: { fontSize: 16, fontWeight: '800' },
  brand: { alignItems: 'center', gap: 4, marginTop: 4 },
  brandTitle: { fontSize: 34, fontWeight: '900', letterSpacing: 0.5, marginTop: 6 },
  brandSub: { fontSize: 15, fontWeight: '500' },
  levelCard: { alignSelf: 'center', alignItems: 'center', borderWidth: 1, borderRadius: RADIUS.xl, paddingVertical: SPACE.lg, paddingHorizontal: SPACE.xxl, minWidth: 220 },
  preview: { height: 150, justifyContent: 'center', alignItems: 'center', marginBottom: SPACE.sm },
  levelLabel: { fontSize: 13, fontWeight: '800', letterSpacing: 2 },
  levelNum: { fontSize: 44, fontWeight: '900', lineHeight: 50 },
  playBtn: { alignSelf: 'center', minWidth: 220 },
  daily: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, borderWidth: 1, borderRadius: RADIUS.lg, padding: SPACE.lg },
  dailyIcon: { width: 48, height: 48, borderRadius: 24, alignItems: 'center', justifyContent: 'center' },
  dailyBody: { flex: 1, gap: 2 },
  dailyTitle: { fontSize: 17, fontWeight: '800' },
  dailySub: { fontSize: 14, fontWeight: '500' },
  dailyBar: { marginTop: 6 },
});
