import { StyleSheet, Text, View } from 'react-native';
import type { LegalDocName } from '../app/navigation';
import { Logo } from '../components/Logo';
import { Card, Page, Screen, TopBar } from '../components/ui';
import { ABOUT, PRIVACY_POLICY, TERMS, type LegalDoc } from '../config/legal';
import { COLORS, SPACE, TYPE } from '../config/theme';

const DOCS: Record<LegalDocName, LegalDoc> = { privacy: PRIVACY_POLICY, terms: TERMS, about: ABOUT };

export function LegalScreen({ doc }: { doc: LegalDocName }) {
  const d = DOCS[doc];
  return (
    <Screen>
      <TopBar title={d.title} />
      <Page>
        {doc === 'about' ? (
          <View style={styles.logo}>
            <Logo size={64} />
          </View>
        ) : null}
        <Text style={styles.updated}>{doc === 'about' ? d.updated : `Last updated ${d.updated}`}</Text>
        <Card style={styles.card}>
          {d.sections.map((s) => (
            <View key={s.heading} style={styles.section}>
              <Text style={TYPE.heading}>{s.heading}</Text>
              <Text style={styles.body}>{s.body}</Text>
            </View>
          ))}
        </Card>
      </Page>
    </Screen>
  );
}

const styles = StyleSheet.create({
  logo: { alignItems: 'center', marginTop: SPACE.sm },
  updated: { ...TYPE.caption, textAlign: 'center' },
  card: { padding: SPACE.lg, gap: SPACE.lg },
  section: { gap: SPACE.xs },
  body: { ...TYPE.body, color: COLORS.inkSoft },
});
