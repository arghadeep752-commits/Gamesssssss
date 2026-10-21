import { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ADMIN_APP_NAME } from '@devdarshan/shared';
import { AppText, Badge, Button, Card, LoadingState, Logo, useTheme, useToast } from '@devdarshan/ui';
import { versionLabel } from '../config';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import { isBackendConfigured } from '../firebase';

/** Everything before admin access is confirmed: sign-in, verification and "not an admin". */
export function GateScreen() {
  const { colors, spacing } = useTheme();
  const insets = useSafeAreaInsets();
  const toast = useToast();
  const { status, user, signIn, signOut, claimAdmin, recheck } = useSession();
  const [busy, setBusy] = useState<'signin' | 'claim' | 'recheck' | null>(null);

  const run = async (kind: 'signin' | 'claim' | 'recheck', job: () => Promise<void>) => {
    setBusy(kind);
    try {
      await job();
    } catch (error) {
      const friendly = describeError(error);
      if (!friendly.silent) toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
    } finally {
      setBusy(null);
    }
  };

  let body;
  if (!isBackendConfigured) {
    body = (
      <Card style={{ padding: spacing.xl }}>
        <AppText variant="heading">Almost ready</AppText>
        <AppText variant="body" color="textMuted" style={{ marginTop: spacing.xs }}>
          This test build is not connected to the DevDarshan Firebase project yet. Install the release build to manage
          content.
        </AppText>
      </Card>
    );
  } else if (status === 'loading' || status === 'checking') {
    body = <LoadingState label={status === 'checking' ? 'Checking admin access…' : undefined} />;
  } else if (status === 'not-admin') {
    body = (
      <Card style={{ padding: spacing.xl, gap: spacing.md }}>
        <AppText variant="heading">Admin access needed</AppText>
        <AppText variant="body" color="textMuted">
          {user?.email ?? 'This account'} is signed in but is not a DevDarshan admin.
        </AppText>
        <AppText variant="caption" color="textSubtle">
          First-time setup: if this is the account named during setup, claim admin access below. Otherwise ask an existing
          admin to add {user?.email ?? 'you'} from Settings → Admins.
        </AppText>
        <Button title="Claim admin access" icon="shield" onPress={() => run('claim', claimAdmin)} loading={busy === 'claim'} />
        <Button title="Check again" variant="outline" onPress={() => run('recheck', recheck)} loading={busy === 'recheck'} />
        <Button title="Use another account" variant="ghost" onPress={() => run('signin', signOut)} />
      </Card>
    );
  } else {
    body = (
      <Card style={{ padding: spacing.xl, gap: spacing.md }}>
        <AppText variant="heading">Sign in to continue</AppText>
        <AppText variant="body" color="textMuted">
          Only approved admins can manage wallpapers, categories and the home screen.
        </AppText>
        <Button title="Sign in with Google" icon="logIn" onPress={() => run('signin', signIn)} loading={busy === 'signin'} testID="admin-sign-in" />
      </Card>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: colors.background, paddingTop: insets.top + 32, paddingBottom: insets.bottom + 16 }]}>
      <View style={styles.brand}>
        <Logo size={64} archColor={colors.primary} flameColor={colors.secondary} flameCoreColor={colors.surface} />
        <AppText variant="display" style={{ marginTop: spacing.md }}>
          {ADMIN_APP_NAME}
        </AppText>
        <Badge label="ADMIN" tone="primary" icon="shield" />
      </View>
      <View style={[styles.body, { paddingHorizontal: spacing.xl }]}>{body}</View>
      <AppText variant="caption" color="textSubtle" align="center">
        Version {versionLabel()}
      </AppText>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  brand: {
    alignItems: 'center',
    gap: 8,
  },
  body: {
    flex: 1,
    justifyContent: 'center',
  },
});
