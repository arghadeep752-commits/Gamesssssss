import { useNavigation } from '@react-navigation/native';
import { useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Alert, ScrollView, StyleSheet, View } from 'react-native';
import { formatDate } from '@devdarshan/shared';
import { AppText, Badge, Button, Card, Divider, ErrorState, IconButton, LoadingState, ScreenHeader, TextField, useTheme, useToast } from '@devdarshan/ui';
import { setAdminRole } from '../data/admins';
import { adminKeys, useAdmins } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';

export function AdminsScreen() {
  const navigation = useNavigation();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const admins = useAdmins();
  const [email, setEmail] = useState('');
  const [busy, setBusy] = useState<string | null>(null);

  const refresh = () => queryClient.invalidateQueries({ queryKey: adminKeys.admins });
  const fail = (error: unknown) => {
    const friendly = describeError(error);
    toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
  };

  const add = async () => {
    const value = email.trim().toLowerCase();
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
      toast.show({ tone: 'error', message: 'Enter a valid email address' });
      return;
    }
    setBusy('add');
    try {
      await setAdminRole(value, true);
      setEmail('');
      toast.show({ tone: 'success', message: 'Admin added', detail: `${value} can now sign in to DevDarshan Admin.` });
      await refresh();
    } catch (error) {
      fail(error);
    } finally {
      setBusy(null);
    }
  };

  const remove = (adminEmail: string, uid: string) => {
    Alert.alert('Remove admin?', `${adminEmail} will lose access immediately.`, [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Remove',
        style: 'destructive',
        onPress: async () => {
          setBusy(uid);
          try {
            await setAdminRole(adminEmail, false);
            toast.show({ tone: 'success', message: 'Admin removed' });
            await refresh();
          } catch (error) {
            fail(error);
          } finally {
            setBusy(null);
          }
        },
      },
    ]);
  };

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader title="Admins" subtitle="Who can manage DevDarshan" onBack={() => navigation.goBack()} />
      <ScrollView contentContainerStyle={{ padding: spacing.lg, gap: spacing.lg }} keyboardShouldPersistTaps="handled">
        <Card style={{ overflow: 'hidden' }}>
          {admins.isPending ? (
            <LoadingState style={{ minHeight: 120 }} />
          ) : admins.error ? (
            <ErrorState onRetry={() => void admins.refetch()} />
          ) : (
            (admins.data ?? []).map((admin, index) => (
              <View key={admin.uid}>
                {index > 0 ? <Divider /> : null}
                <View style={[styles.row, { padding: spacing.lg }]}>
                  <View style={{ flex: 1 }}>
                    <AppText variant="bodyStrong" numberOfLines={1}>
                      {admin.displayName || admin.email}
                    </AppText>
                    <AppText variant="caption" color="textMuted" numberOfLines={1}>
                      {admin.email} · since {formatDate(admin.createdAt)}
                    </AppText>
                  </View>
                  {admin.uid === user?.uid ? <Badge label="YOU" tone="primary" /> : null}
                  {admin.uid !== user?.uid ? (
                    <IconButton
                      name="trash"
                      color={colors.danger}
                      accessibilityLabel={`Remove ${admin.email}`}
                      disabled={busy !== null}
                      onPress={() => remove(admin.email, admin.uid)}
                    />
                  ) : null}
                </View>
              </View>
            ))
          )}
        </Card>

        <Card style={{ padding: spacing.lg }}>
          <AppText variant="subheading">Add an admin</AppText>
          <AppText variant="caption" color="textMuted" style={{ marginTop: spacing.xs, marginBottom: spacing.md }}>
            They must sign in to DevDarshan Admin once with this Google account first.
          </AppText>
          <TextField
            label="Google account email"
            value={email}
            onChangeText={setEmail}
            autoCapitalize="none"
            keyboardType="email-address"
            placeholder="name@gmail.com"
          />
          <Button title="Add admin" icon="plus" onPress={add} loading={busy === 'add'} />
        </Card>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
});
