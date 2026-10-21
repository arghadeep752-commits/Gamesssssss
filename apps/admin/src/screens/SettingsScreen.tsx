import { useNavigation } from '@react-navigation/native';
import { useQueryClient } from '@tanstack/react-query';
import { useState, type ReactNode } from 'react';
import { Alert, ScrollView, View } from 'react-native';
import {
  AppText,
  Avatar,
  Card,
  Divider,
  ListRow,
  ScreenHeader,
  SegmentedControl,
  useTheme,
  useToast,
  type ThemePreference,
} from '@devdarshan/ui';
import { versionLabel } from '../config';
import { seedStarterCategories } from '../data/categories';
import { adminKeys } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import type { AdminNavigation } from '../navigation/types';
import { useSettings } from '../state/settings';

function Section({ title, children }: { title: string; children: ReactNode }) {
  const { spacing } = useTheme();
  return (
    <View style={{ marginTop: spacing.xl }}>
      <AppText variant="overline" color="textSubtle" style={{ paddingHorizontal: spacing.lg, marginBottom: spacing.sm }}>
        {title.toUpperCase()}
      </AppText>
      <Card style={{ marginHorizontal: spacing.lg, overflow: 'hidden' }}>{children}</Card>
    </View>
  );
}

export function SettingsScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user, signOut } = useSession();
  const themePreference = useSettings((s) => s.themePreference);
  const setThemePreference = useSettings((s) => s.setThemePreference);
  const [seeding, setSeeding] = useState(false);

  const seed = async () => {
    setSeeding(true);
    try {
      const result = await seedStarterCategories();
      toast.show({
        tone: 'success',
        message: result.created ? `Added ${result.created} starter categories` : 'All starter categories already exist',
      });
      void queryClient.invalidateQueries({ queryKey: adminKeys.categories });
    } catch (error) {
      const friendly = describeError(error);
      toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
    } finally {
      setSeeding(false);
    }
  };

  return (
    <View style={{ flex: 1, backgroundColor: colors.background }}>
      <ScreenHeader title="Settings" />
      <ScrollView contentContainerStyle={{ paddingBottom: spacing.xxxl }}>
        <Card style={{ marginHorizontal: spacing.lg, padding: spacing.lg, flexDirection: 'row', alignItems: 'center', gap: 14 }}>
          <Avatar uri={user?.photoURL} name={user?.displayName} size={48} />
          <View style={{ flex: 1 }}>
            <AppText variant="heading" numberOfLines={1}>
              {user?.displayName || 'Admin'}
            </AppText>
            <AppText variant="caption" color="textMuted" numberOfLines={1}>
              {user?.email}
            </AppText>
          </View>
        </Card>

        <Section title="Content">
          <ListRow icon="home" title="Home content" subtitle="Today's Darshan, home categories, festival, maintenance" onPress={() => navigation.navigate('HomeContent')} />
          <Divider inset={52} />
          <ListRow icon="grid" title={seeding ? 'Adding starter categories…' : 'Add starter categories'} subtitle="Creates any of the 20 starter categories that are missing" onPress={seeding ? undefined : seed} />
        </Section>

        <Section title="Team">
          <ListRow icon="users" title="Admins" onPress={() => navigation.navigate('Admins')} />
          <Divider inset={52} />
          <ListRow icon="clock" title="Activity log" onPress={() => navigation.navigate('Activity')} />
        </Section>

        <Section title="Appearance">
          <View style={{ padding: spacing.md }}>
            <SegmentedControl<ThemePreference>
              value={themePreference}
              onChange={setThemePreference}
              options={[
                { value: 'system', label: 'System', icon: 'smartphone' },
                { value: 'light', label: 'Light', icon: 'sun' },
                { value: 'dark', label: 'Dark', icon: 'moon' },
              ]}
            />
          </View>
        </Section>

        <Section title="Account">
          <ListRow icon="info" title="Version" value={versionLabel()} />
          <Divider inset={52} />
          <ListRow
            icon="logOut"
            title="Sign out"
            destructive
            onPress={() =>
              Alert.alert('Sign out?', undefined, [
                { text: 'Cancel', style: 'cancel' },
                { text: 'Sign out', style: 'destructive', onPress: () => void signOut() },
              ])
            }
          />
        </Section>
      </ScrollView>
    </View>
  );
}
