import { StyleSheet, Text, View } from 'react-native';
import { useNav } from '../app/navigation';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { Card, ListRow, Page, Screen, SectionTitle, ToggleRow, TopBar } from '../components/ui';
import { COLORS, SPACE, TYPE } from '../config/theme';
import { setSaveUnfinished } from '../state/progress';
import { useStore } from '../state/store';
import { confirmDeleteData } from './confirmDelete';

const STORED = [
  'Unlocked levels, best results and stars',
  'Hints, daily challenge records and streaks',
  'Achievements and your profile name',
  'Settings (sound, music, vibration, effects)',
];

export function PrivacyScreen() {
  const nav = useNav();
  const store = useStore();
  const { save } = store;

  return (
    <Screen>
      <TopBar title="Privacy Preferences" />
      <Page>
        <Card style={styles.summary}>
          <Icon name="shield" size={26} color={COLORS.hint} />
          <Text style={styles.summaryText}>
            Arrow Flow has no accounts, ads, analytics or tracking, and sends nothing over the internet. Everything below
            stays on this device.
          </Text>
        </Card>

        <SectionTitle>Choices</SectionTitle>
        <Card>
          <ToggleRow
            icon="restart"
            label="Save unfinished puzzles"
            detail="Lets you resume a level after closing the app. Turning this off deletes the saved puzzle now."
            value={save.privacy.saveUnfinished}
            onChange={(v) => store.update((s) => setSaveUnfinished(s, v))}
            last
          />
        </Card>

        <SectionTitle>Stored on this device</SectionTitle>
        <Card style={styles.list}>
          {[...STORED, save.privacy.saveUnfinished ? 'Your unfinished puzzle, if any' : null]
            .filter((x): x is string => !!x)
            .map((line) => (
              <View key={line} style={styles.item}>
                <View style={styles.bullet} />
                <Text style={styles.itemText}>{line}</Text>
              </View>
            ))}
        </Card>

        <Card>
          <ListRow icon="doc" label="Read the Privacy Policy" onPress={() => nav.push({ name: 'legal', doc: 'privacy' })} last />
        </Card>

        <Button label="Delete Local Game Data" icon="trash" variant="danger" onPress={() => confirmDeleteData(store, nav)} />
      </Page>
    </Screen>
  );
}

const styles = StyleSheet.create({
  summary: { flexDirection: 'row', gap: SPACE.md, padding: SPACE.lg, alignItems: 'center' },
  summaryText: { ...TYPE.body, flex: 1, fontSize: 14, lineHeight: 20, color: COLORS.inkSoft },
  list: { padding: SPACE.lg, gap: SPACE.sm },
  item: { flexDirection: 'row', alignItems: 'center', gap: SPACE.sm },
  bullet: { width: 6, height: 6, borderRadius: 3, backgroundColor: COLORS.muted },
  itemText: { fontSize: 14, color: COLORS.ink },
});
