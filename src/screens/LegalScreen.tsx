import { ScrollView, StyleSheet, Text, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { LEGAL_DOCS, type LegalId } from '../legal/docs';
import { RoundBtn } from '../ui/kit';
import { SPACE, useTheme } from '../ui/theme';

/** Full-screen reader for the Privacy Policy, Terms, Licenses and About pages. */
export function LegalScreen({ doc, onBack }: { doc: LegalId; onBack: () => void }) {
  const t = useTheme();
  const insets = useSafeAreaInsets();
  const d = LEGAL_DOCS[doc];
  return (
    <Animated.View entering={FadeIn.duration(180)} style={[styles.root, { backgroundColor: t.bg, paddingTop: insets.top + 6 }]}>
      <View style={styles.header}>
        <RoundBtn icon="back" label="Back" onPress={onBack} size={42} />
        <Text style={[styles.title, { color: t.text }]} numberOfLines={1}>
          {d.title}
        </Text>
        <View style={styles.spacer} />
      </View>
      <ScrollView contentContainerStyle={[styles.body, { paddingBottom: insets.bottom + 32 }]}>
        {d.updated ? <Text style={[styles.updated, { color: t.sub }]}>{d.updated}</Text> : null}
        {d.sections.map((s, i) => (
          <View key={i} style={styles.section}>
            {s.h ? <Text style={[styles.h, { color: t.text }]}>{s.h}</Text> : null}
            {s.p.map((p, j) => (
              <Text key={j} style={[styles.p, { color: t.text }]} selectable>
                {p}
              </Text>
            ))}
          </View>
        ))}
      </ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1 },
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: SPACE.lg, gap: SPACE.md, paddingBottom: SPACE.sm },
  title: { flex: 1, fontSize: 20, fontWeight: '900', textAlign: 'center' },
  spacer: { width: 42 },
  body: { paddingHorizontal: SPACE.xl, gap: SPACE.lg },
  updated: { fontSize: 13, fontWeight: '700' },
  section: { gap: 8 },
  h: { fontSize: 17, fontWeight: '800' },
  p: { fontSize: 15, lineHeight: 22 },
});
