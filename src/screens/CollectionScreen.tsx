import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { SHAPES } from '../game/shapes';
import { skinById } from '../state/economy';
import { useStore } from '../state/store';
import { ProgressBar } from '../ui/kit';
import { ShapeThumb } from '../ui/ShapeThumb';
import { RADIUS, SPACE, useTheme } from '../ui/theme';

/** Every board outline in the game; cleared ones are revealed in colour. */
export function CollectionScreen() {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const { save } = useStore();
  const skin = skinById(save.skin);
  const ink = t.dark ? skin.dark : skin.light;
  const got = SHAPES.filter((s) => save.shapes[s.id]).length;

  return (
    <Animated.View collapsable={false} entering={FadeIn.duration(200)} style={styles.fill}>
      <ScrollView contentContainerStyle={[styles.root, { paddingTop: insets.top + 8 }]} showsVerticalScrollIndicator={false}>
        <Text style={[styles.h1, { color: t.text }]}>Collection</Text>
        <View style={[styles.summary, { backgroundColor: t.surface, borderColor: t.border }]}>
          <Text style={[styles.count, { color: t.text }]}>
            {got} <Text style={[styles.of, { color: t.sub }]}>/ {SHAPES.length} shapes</Text>
          </Text>
          <Text style={[styles.hint, { color: t.sub }]}>Every level is a picture. Clear it to add the shape here.</Text>
          <ProgressBar value={got / SHAPES.length} color={t.accent} track={t.surfaceAlt} height={7} />
        </View>
        <View style={styles.grid}>
          {SHAPES.map((s) => {
            const n = save.shapes[s.id] ?? 0;
            return (
              <View key={s.id} style={styles.cellWrap}>
                <View style={[styles.cell, { backgroundColor: t.surface, borderColor: n ? t.border : t.surfaceAlt }]}>
                  <ShapeThumb shape={s.id} size={56} color={n ? ink : t.faint} opacity={n ? 1 : 0.35} />
                  <Text style={[styles.name, { color: n ? t.text : t.faint }]} numberOfLines={1}>
                    {n ? s.name : '???'}
                  </Text>
                  {n > 1 ? <Text style={[styles.times, { color: t.sub }]}>×{n}</Text> : null}
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
  summary: { borderWidth: 1, borderRadius: RADIUS.lg, padding: SPACE.lg, gap: 8 },
  count: { fontSize: 26, fontWeight: '900' },
  of: { fontSize: 16, fontWeight: '700' },
  hint: { fontSize: 14, fontWeight: '500' },
  grid: { flexDirection: 'row', flexWrap: 'wrap', marginHorizontal: -4 },
  cellWrap: { width: '25%', padding: 4 },
  cell: { alignItems: 'center', borderWidth: 1.5, borderRadius: RADIUS.md, paddingVertical: SPACE.md, gap: 4 },
  name: { fontSize: 11, fontWeight: '800', paddingHorizontal: 2 },
  times: { position: 'absolute', top: 4, right: 6, fontSize: 11, fontWeight: '800' },
});
