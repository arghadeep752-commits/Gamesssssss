import { useEffect, useMemo, useState } from 'react';
import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { getDaily } from '../game/levels';
import { addMonths, daysInMonth, monthKeyOf, monthProgress, monthTitle, prettyDate, todayKey } from '../state/dates';
import { useStore } from '../state/store';
import { Icon } from '../ui/Icon';
import { Btn, Pressy, ProgressBar, RoundBtn } from '../ui/kit';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

const WEEK = ['S', 'M', 'T', 'W', 'T', 'F', 'S'];

export function DailyScreen({ onPlay }: { onPlay: (dateKey: string) => void }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save } = useStore();
  const today = todayKey();
  const thisMonth = monthKeyOf(today);
  const [month, setMonth] = useState(thisMonth);
  const [picked, setPicked] = useState(today);
  const firstMonth = save.since < addMonths(thisMonth, -11) ? save.since : addMonths(thisMonth, -11);

  const cells = useMemo(() => {
    const [y, m] = month.split('-').map(Number);
    const lead = new Date(y, m - 1, 1).getDay();
    const n = daysInMonth(y, m - 1);
    const out: (string | null)[] = [];
    for (let i = 0; i < lead; i++) out.push(null);
    for (let d = 1; d <= n; d++) out.push(`${month}-${String(d).padStart(2, '0')}`);
    while (out.length % 7) out.push(null);
    return out;
  }, [month]);

  const prog = monthProgress(month, save.daily);
  const complete = prog.done === prog.total;
  const selected = picked.startsWith(month) ? picked : null;
  const pickedDone = selected ? !!save.daily[selected] : false;

  // Build the picked puzzle in the background so Play opens instantly.
  useEffect(() => {
    if (!selected) return;
    const id = setTimeout(() => getDaily(selected), 150);
    return () => clearTimeout(id);
  }, [selected]);

  return (
    <Animated.View collapsable={false} entering={FadeIn.duration(200)} style={styles.fill}>
      <ScrollView contentContainerStyle={[styles.root, { paddingTop: insets.top + 8 }]} showsVerticalScrollIndicator={false}>
      <Text style={[styles.h1, { color: t.text }]}>Daily Challenges</Text>

      <View style={[styles.trophyCard, { backgroundColor: complete ? t.goldSoft : t.surface, borderColor: t.border }]}>
        <View style={[styles.trophyBadge, { backgroundColor: complete ? t.gold : t.surfaceAlt }]}>
          <Icon name="trophy" size={34} color={complete ? '#fff' : t.faint} filled={complete} />
        </View>
        <View style={styles.trophyBody}>
          <Text style={[styles.trophyTitle, { color: t.text }]}>{complete ? 'Trophy earned!' : `${monthTitle(month).split(' ')[0]} trophy`}</Text>
          <Text style={[styles.trophySub, { color: t.sub }]}>
            {prog.done} of {prog.total} days solved
          </Text>
          <View style={styles.bar}>
            <ProgressBar value={prog.done / prog.total} color={t.gold} track={t.surfaceAlt} height={7} />
          </View>
        </View>
      </View>

      <View style={[styles.calendar, { backgroundColor: t.surface, borderColor: t.border }]}>
        <View style={styles.monthRow}>
          <RoundBtn icon="chevronLeft" label="Previous month" size={38} onPress={() => month > firstMonth && setMonth(addMonths(month, -1))} />
          <Text style={[styles.monthTitle, { color: t.text }]}>{monthTitle(month)}</Text>
          <RoundBtn icon="chevronRight" label="Next month" size={38} onPress={() => month < thisMonth && setMonth(addMonths(month, 1))} />
        </View>
        <View style={styles.week}>
          {WEEK.map((w, i) => (
            <Text key={i} style={[styles.weekDay, { color: t.faint }]}>
              {w}
            </Text>
          ))}
        </View>
        <View style={styles.grid}>
          {cells.map((key, i) => {
            if (!key) return <View key={i} style={styles.cell} />;
            const day = Number(key.slice(8));
            const future = key > today;
            const done = !!save.daily[key];
            const isToday = key === today;
            const isPicked = key === selected;
            return (
              <View key={i} style={styles.cell}>
                <Pressy
                  disabled={future}
                  sound={!future}
                  label={prettyDate(key)}
                  onPress={() => setPicked(key)}
                  containerStyle={styles.fill}
                  style={[
                    styles.day,
                    done && { backgroundColor: t.accent },
                    !done && isToday && { borderColor: t.accent, borderWidth: 2 },
                    isPicked && !done && { backgroundColor: t.accentSoft },
                    isPicked && done && { borderColor: t.ink, borderWidth: 2 },
                  ]}
                >
                  {done ? (
                    <Icon name="check" size={18} color="#fff" strokeWidth={3} />
                  ) : (
                    <Text style={[styles.dayText, { color: future ? t.faint : t.text }]}>{day}</Text>
                  )}
                </Pressy>
              </View>
            );
          })}
        </View>
      </View>

      {selected ? (
        <Btn
          label={pickedDone ? `Replay ${prettyDate(selected).replace(/, \d{4}$/, '')}` : `Play ${prettyDate(selected).replace(/, \d{4}$/, '')}`}
          icon="play"
          kind={pickedDone ? 'secondary' : 'primary'}
          onPress={() => onPlay(selected)}
        />
      ) : (
        <Text style={[styles.pickHint, { color: t.sub }]}>Pick a day to play</Text>
      )}
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { paddingHorizontal: SPACE.xl, gap: SPACE.lg, paddingBottom: SPACE.xl },
  h1: { fontSize: 28, fontWeight: '900', marginTop: 4 },
  trophyCard: { flexDirection: 'row', alignItems: 'center', gap: SPACE.lg, borderWidth: 1, borderRadius: RADIUS.lg, padding: SPACE.lg },
  trophyBadge: { width: 60, height: 60, borderRadius: 30, alignItems: 'center', justifyContent: 'center' },
  trophyBody: { flex: 1, gap: 2 },
  trophyTitle: { fontSize: 18, fontWeight: '800' },
  trophySub: { fontSize: 14, fontWeight: '500' },
  bar: { marginTop: 8 },
  calendar: { borderWidth: 1, borderRadius: RADIUS.lg, padding: SPACE.md },
  monthRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginBottom: SPACE.sm },
  monthTitle: { fontSize: 17, fontWeight: '800' },
  week: { flexDirection: 'row' },
  weekDay: { width: `${100 / 7}%`, textAlign: 'center', fontSize: 12, fontWeight: '800', paddingVertical: 4 },
  grid: { flexDirection: 'row', flexWrap: 'wrap' },
  cell: { width: `${100 / 7}%`, aspectRatio: 1, padding: 3 },
  fill: { flex: 1 },
  day: { flex: 1, borderRadius: 999, alignItems: 'center', justifyContent: 'center', borderColor: 'transparent', borderWidth: 2 },
  dayText: { fontSize: 15, fontWeight: '700' },
  pickHint: { textAlign: 'center', fontSize: 15, fontWeight: '600' },
});
