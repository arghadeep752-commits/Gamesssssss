import { useMemo, useState } from 'react';
import { Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { useNav } from '../app/navigation';
import { Button } from '../components/Button';
import { Icon } from '../components/Icon';
import { Sheet } from '../components/Sheet';
import { TabBar } from '../components/TabBar';
import { Card, ListRow, SectionTitle, Screen, StatTile } from '../components/ui';
import { COLORS, RADIUS, SPACE, TYPE } from '../config/theme';
import { LEVEL_COUNT } from '../levels';
import { playSfx } from '../services/audio';
import { ACHIEVEMENTS, deriveStats } from '../state/achievements';
import { setPlayerName } from '../state/progress';
import { MAX_NAME_LENGTH } from '../state/saveSchema';
import { useStore } from '../state/store';
import { confirmDeleteData } from './confirmDelete';

export function ProfileScreen() {
  const nav = useNav();
  const store = useStore();
  const { save } = store;
  const stats = useMemo(() => deriveStats(save), [save]);
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(save.profile.name);
  const unlocked = ACHIEVEMENTS.filter((a) => save.achievements[a.id]).length;
  const currentLevel = Math.min(LEVEL_COUNT, save.progress.unlockedUpTo);

  return (
    <Screen bottomInset={false}>
      <ScrollView contentContainerStyle={styles.scroll} showsVerticalScrollIndicator={false}>
        <View style={styles.header}>
          <View style={styles.avatar}>
            <Text style={styles.avatarText}>{save.profile.name.slice(0, 1).toUpperCase()}</Text>
          </View>
          <View style={styles.nameBox}>
            <Text style={TYPE.title} numberOfLines={1}>
              {save.profile.name}
            </Text>
            <Text style={styles.sub}>Local profile on this device</Text>
          </View>
          <Pressable
            onPress={() => {
              playSfx('tap');
              setDraft(save.profile.name);
              setEditing(true);
            }}
            hitSlop={10}
            accessibilityRole="button"
            accessibilityLabel="Edit name"
            style={styles.edit}
          >
            <Icon name="edit" size={20} color={COLORS.inkSoft} />
          </Pressable>
        </View>

        <View style={styles.stats}>
          <StatTile label="Current level" value={currentLevel} />
          <StatTile label="Levels cleared" value={stats.completedLevels} />
          <StatTile label="Total stars" value={stats.totalStars} />
          <StatTile label="Dailies done" value={save.daily.completedCount} />
          <StatTile label="Best streak" value={save.daily.bestStreak} />
          <StatTile label="Hints used" value={save.stats.hintsUsed} />
        </View>

        <SectionTitle>Progress</SectionTitle>
        <Card>
          <ListRow
            icon="trophy"
            label="Awards & achievements"
            value={`${unlocked}/${ACHIEVEMENTS.length}`}
            onPress={() => nav.push({ name: 'achievements' })}
            last
          />
        </Card>

        <SectionTitle>Game</SectionTitle>
        <Card>
          <ListRow icon="sliders" label="Settings" onPress={() => nav.push({ name: 'settings' })} />
          <ListRow icon="help" label="Help" onPress={() => nav.push({ name: 'help' })} />
          <ListRow icon="info" label="About" onPress={() => nav.push({ name: 'legal', doc: 'about' })} last />
        </Card>

        <SectionTitle>Privacy</SectionTitle>
        <Card>
          <ListRow icon="shield" label="Privacy Policy" onPress={() => nav.push({ name: 'legal', doc: 'privacy' })} />
          <ListRow icon="sliders" label="Privacy Preferences" onPress={() => nav.push({ name: 'privacy' })} />
          <ListRow icon="doc" label="Terms of Service" onPress={() => nav.push({ name: 'legal', doc: 'terms' })} />
          <ListRow icon="trash" label="Delete Local Game Data" danger onPress={() => confirmDeleteData(store, nav)} last />
        </Card>
      </ScrollView>
      <TabBar current="me" />

      {editing ? (
        <Sheet title="Your name" subtitle="Shown only on this device." reducedEffects={save.settings.reducedEffects}>
          <TextInput
            value={draft}
            onChangeText={setDraft}
            maxLength={MAX_NAME_LENGTH}
            autoFocus
            style={styles.input}
            placeholder="Guest"
            placeholderTextColor={COLORS.muted}
            returnKeyType="done"
            onSubmitEditing={() => {
              store.update((s) => setPlayerName(s, draft));
              setEditing(false);
            }}
            accessibilityLabel="Player name"
          />
          <Button
            label="Save"
            onPress={() => {
              store.update((s) => setPlayerName(s, draft));
              setEditing(false);
            }}
          />
          <Button label="Cancel" variant="ghost" onPress={() => setEditing(false)} />
        </Sheet>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { padding: SPACE.lg, gap: SPACE.lg, paddingBottom: SPACE.xxl },
  header: { flexDirection: 'row', alignItems: 'center', gap: SPACE.md, marginTop: SPACE.lg },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: COLORS.ink,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: { color: COLORS.white, fontSize: 24, fontWeight: '800' },
  nameBox: { flex: 1 },
  sub: { ...TYPE.caption, marginTop: 2 },
  edit: { width: 44, height: 44, alignItems: 'center', justifyContent: 'center' },
  stats: { flexDirection: 'row', flexWrap: 'wrap', gap: SPACE.sm },
  input: {
    borderWidth: 1,
    borderColor: COLORS.border,
    borderRadius: RADIUS.md,
    paddingHorizontal: SPACE.lg,
    paddingVertical: SPACE.md,
    fontSize: 17,
    color: COLORS.ink,
    backgroundColor: COLORS.background,
  },
});
