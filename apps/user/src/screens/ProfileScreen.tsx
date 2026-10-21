import { useNavigation } from '@react-navigation/native';
import { Image } from 'expo-image';
import { useCallback, useEffect, useState, type ReactNode } from 'react';
import { Alert, Linking, ScrollView, StyleSheet, View } from 'react-native';
import { DevDarshanNative } from '@devdarshan/native';
import { formatBytes } from '@devdarshan/shared';
import {
  AppText,
  Avatar,
  Button,
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
import { useAppConfig } from '../data/appConfig';
import { useAuth } from '../data/auth';
import { useFavorites } from '../data/favorites';
import { describeError } from '../errors';
import type { RootNavigation } from '../navigation/types';
import { useSettings } from '../state/settings';
import { useSignInPrompt } from '../components/SignInSheet';

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

export function ProfileScreen() {
  const navigation = useNavigation<RootNavigation>();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const { user, signOut, deleteAccount, signingIn } = useAuth();
  const { ids } = useFavorites();
  const { config } = useAppConfig();
  const openSignIn = useSignInPrompt((s) => s.open);
  const themePreference = useSettings((s) => s.themePreference);
  const setThemePreference = useSettings((s) => s.setThemePreference);
  const [cacheBytes, setCacheBytes] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);

  const refreshCacheSize = useCallback(() => {
    DevDarshanNative.getCacheSize()
      .then(setCacheBytes)
      .catch(() => setCacheBytes(null));
  }, []);

  useEffect(() => {
    refreshCacheSize();
    return navigation.addListener('focus', refreshCacheSize);
  }, [navigation, refreshCacheSize]);

  const clearCache = async () => {
    await DevDarshanNative.clearCache().catch(() => 0);
    await Image.clearDiskCache().catch(() => false);
    await Image.clearMemoryCache().catch(() => false);
    refreshCacheSize();
    toast.show({ tone: 'success', message: 'Cache cleared' });
  };

  const confirmSignOut = () => {
    Alert.alert('Sign out?', 'Your liked wallpapers stay saved in your account.', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Sign out',
        style: 'destructive',
        onPress: () => {
          signOut().catch((error) => {
            const friendly = describeError(error);
            toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
          });
        },
      },
    ]);
  };

  const confirmDelete = () => {
    Alert.alert(
      'Delete your account?',
      'This permanently deletes your DevDarshan account and your liked wallpapers. Wallpapers saved in your gallery stay on your phone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            setBusy(true);
            try {
              const result = await deleteAccount();
              if (result.ok) toast.show({ tone: 'success', message: 'Your account was deleted' });
              else toast.show({ tone: 'warning', message: 'Account not deleted', detail: result.message });
            } catch (error) {
              const friendly = describeError(error);
              toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
            } finally {
              setBusy(false);
            }
          },
        },
      ],
    );
  };

  const supportEmail = config.supportEmail.trim();

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader title="Profile" />
      <ScrollView contentContainerStyle={{ paddingBottom: spacing.xxxl }}>
        <Card style={[styles.account, { marginHorizontal: spacing.lg, padding: spacing.lg }]}>
          <Avatar uri={user?.photoURL} name={user?.displayName} size={52} />
          <View style={{ flex: 1 }}>
            {user ? (
              <>
                <AppText variant="heading" numberOfLines={1}>
                  {user.displayName || 'Devotee'}
                </AppText>
                <AppText variant="caption" color="textMuted" numberOfLines={1}>
                  {user.email}
                </AppText>
              </>
            ) : (
              <>
                <AppText variant="heading">Welcome, devotee</AppText>
                <AppText variant="caption" color="textMuted">
                  Sign in to sync your liked wallpapers.
                </AppText>
              </>
            )}
          </View>
        </Card>
        {!user ? (
          <Button
            title="Sign in with Google"
            icon="logIn"
            onPress={() => openSignIn()}
            loading={signingIn}
            style={{ marginHorizontal: spacing.lg, marginTop: spacing.md }}
          />
        ) : null}

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

        <Section title="Your wallpapers">
          <ListRow
            icon="heart"
            title="Liked wallpapers"
            value={user ? String(ids.length) : undefined}
            onPress={() => navigation.navigate('Tabs', { screen: 'Favorites' })}
          />
          <Divider inset={52} />
          <ListRow icon="download" title="Downloads" subtitle="Saved in Gallery › Pictures/DevDarshan" />
          <Divider inset={52} />
          <ListRow
            icon="refresh"
            title="Clear image cache"
            subtitle={cacheBytes !== null ? `${formatBytes(cacheBytes)} of full-size images` : undefined}
            onPress={clearCache}
          />
        </Section>

        <Section title="About">
          <ListRow icon="shield" title="Privacy policy" onPress={() => navigation.navigate('Legal', { document: 'privacy' })} />
          <Divider inset={52} />
          <ListRow icon="fileText" title="Terms of use" onPress={() => navigation.navigate('Legal', { document: 'terms' })} />
          <Divider inset={52} />
          <ListRow
            icon="mail"
            title="Send feedback"
            subtitle={supportEmail || 'Support email not set yet'}
            onPress={
              supportEmail
                ? () => void Linking.openURL(`mailto:${supportEmail}?subject=${encodeURIComponent('DevDarshan feedback')}`)
                : undefined
            }
          />
          <Divider inset={52} />
          <ListRow icon="info" title="App version" value={versionLabel()} />
        </Section>

        {user ? (
          <Section title="Account">
            <ListRow icon="logOut" title="Sign out" onPress={confirmSignOut} />
            <Divider inset={52} />
            <ListRow icon="trash" title={busy ? 'Deleting…' : 'Delete account'} destructive onPress={busy ? undefined : confirmDelete} />
          </Section>
        ) : null}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  account: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
});
