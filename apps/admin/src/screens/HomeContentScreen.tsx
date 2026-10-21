import { useNavigation } from '@react-navigation/native';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useMemo, useState } from 'react';
import { FlatList, KeyboardAvoidingView, ScrollView, StyleSheet, View } from 'react-native';
import { collection, documentId, getDocs, limit, orderBy, query, where } from '@react-native-firebase/firestore';
import { COLLECTIONS, DEFAULT_HOME_SECTION_ORDER, LIMITS, toWallpaper, type HomeSection, type Wallpaper } from '@devdarshan/shared';
import {
  AppText,
  Button,
  Card,
  Divider,
  IconButton,
  LoadingState,
  ScreenHeader,
  Sheet,
  SwitchRow,
  TextField,
  useTheme,
  useToast,
} from '@devdarshan/ui';
import { CategoryPicker } from '../components/CategoryPicker';
import { WallpaperRow } from '../components/WallpaperRow';
import { saveAppConfig } from '../data/homeConfig';
import { adminKeys, useAllCategories, useAppConfigQuery } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import { db } from '../firebase';

const SECTION_LABELS: Record<HomeSection, string> = {
  featured: "Today's Darshan",
  categories: 'Explore by deity',
  festival: 'Festival collection',
  latest: 'Latest wallpapers',
};

async function fetchPublished(): Promise<Wallpaper[]> {
  const snap = await getDocs(
    query(collection(db, COLLECTIONS.wallpapers), where('status', '==', 'published'), orderBy('publishedAt', 'desc'), limit(100)),
  );
  return snap.docs.map((d) => toWallpaper(d.id, d.data()));
}

async function fetchByIds(ids: string[]): Promise<Map<string, Wallpaper>> {
  const map = new Map<string, Wallpaper>();
  for (let i = 0; i < ids.length; i += 30) {
    const chunk = ids.slice(i, i + 30);
    const snap = await getDocs(query(collection(db, COLLECTIONS.wallpapers), where(documentId(), 'in', chunk)));
    snap.docs.forEach((d) => map.set(d.id, toWallpaper(d.id, d.data())));
  }
  return map;
}

function move<T>(list: T[], index: number, delta: number): T[] {
  const target = index + delta;
  if (target < 0 || target >= list.length) return list;
  const next = [...list];
  const [item] = next.splice(index, 1);
  if (item !== undefined) next.splice(target, 0, item);
  return next;
}

/** Everything the user app's home screen shows, plus maintenance and version controls. */
export function HomeContentScreen() {
  const navigation = useNavigation();
  const { colors, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const config = useAppConfigQuery();
  const categories = useAllCategories();

  const [featured, setFeatured] = useState<string[]>([]);
  const [homeCategories, setHomeCategories] = useState<string[]>([]);
  const [order, setOrder] = useState<HomeSection[]>([...DEFAULT_HOME_SECTION_ORDER]);
  const [festivalEnabled, setFestivalEnabled] = useState(false);
  const [festivalTitle, setFestivalTitle] = useState('');
  const [festivalTitleHi, setFestivalTitleHi] = useState('');
  const [festivalCategory, setFestivalCategory] = useState<string[]>([]);
  const [maintenance, setMaintenance] = useState(false);
  const [maintenanceMessage, setMaintenanceMessage] = useState('');
  const [minVersion, setMinVersion] = useState('0');
  const [updateUrl, setUpdateUrl] = useState('');
  const [supportEmail, setSupportEmail] = useState('');
  const [shareMessage, setShareMessage] = useState('');
  const [picking, setPicking] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const c = config.data;
    if (!c) return;
    setFeatured(c.featuredWallpaperIds);
    setHomeCategories(c.featuredCategoryIds);
    setOrder(c.homeSectionOrder.filter((s) => s !== 'latest'));
    setFestivalEnabled(c.festival.enabled);
    setFestivalTitle(c.festival.title);
    setFestivalTitleHi(c.festival.titleHi);
    setFestivalCategory(c.festival.categoryId ? [c.festival.categoryId] : []);
    setMaintenance(c.maintenanceMode);
    setMaintenanceMessage(c.maintenanceMessage);
    setMinVersion(String(c.minimumSupportedVersionCode));
    setUpdateUrl(c.updateUrl);
    setSupportEmail(c.supportEmail);
    setShareMessage(c.shareMessage);
  }, [config.data]);

  const featuredDocs = useQuery({
    queryKey: ['featured-docs', featured.join(',')],
    queryFn: () => fetchByIds(featured),
    enabled: featured.length > 0,
    placeholderData: (prev) => prev,
  });
  const published = useQuery({ queryKey: ['published-for-picker'], queryFn: fetchPublished, enabled: picking });
  const available = useMemo(() => (published.data ?? []).filter((w) => !featured.includes(w.id)), [featured, published.data]);

  const save = async () => {
    const version = Number.parseInt(minVersion || '0', 10);
    if (!Number.isFinite(version) || version < 0) {
      toast.show({ tone: 'error', message: 'Minimum version must be a whole number' });
      return;
    }
    if (festivalEnabled && festivalCategory.length === 0) {
      toast.show({ tone: 'error', message: 'Choose a category for the festival collection' });
      return;
    }
    setSaving(true);
    try {
      await saveAppConfig(
        {
          featuredWallpaperIds: featured.slice(0, LIMITS.featuredMax),
          featuredCategoryIds: homeCategories.slice(0, LIMITS.featuredCategoriesMax),
          homeSectionOrder: [...order, 'latest'],
          festival: { enabled: festivalEnabled, title: festivalTitle.trim(), titleHi: festivalTitleHi.trim(), categoryId: festivalCategory[0] ?? null },
          maintenanceMode: maintenance,
          maintenanceMessage: maintenanceMessage.trim(),
          minimumSupportedVersionCode: version,
          updateUrl: updateUrl.trim(),
          supportEmail: supportEmail.trim(),
          shareMessage: shareMessage.trim(),
        },
        user?.uid ?? '',
      );
      toast.show({ tone: 'success', message: 'Home content saved', detail: 'The user app updates right away.' });
      void queryClient.invalidateQueries({ queryKey: adminKeys.config });
    } catch (error) {
      const friendly = describeError(error);
      toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
    } finally {
      setSaving(false);
    }
  };

  if (config.isPending) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Home content" onBack={() => navigation.goBack()} />
        <LoadingState />
      </View>
    );
  }

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader title="Home content" subtitle="What the user app shows" onBack={() => navigation.goBack()} />
      <KeyboardAvoidingView behavior="padding" style={styles.root}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxxl, gap: spacing.lg }} keyboardShouldPersistTaps="handled">
          <Card style={{ overflow: 'hidden' }}>
            <View style={[styles.cardHead, { padding: spacing.lg }]}>
              <View style={{ flex: 1 }}>
                <AppText variant="subheading">Today's Darshan</AppText>
                <AppText variant="caption" color="textMuted">
                  {featured.length}/{LIMITS.featuredMax} featured, in this order
                </AppText>
              </View>
              <Button title="Add" icon="plus" size="sm" variant="secondary" onPress={() => setPicking(true)} disabled={featured.length >= LIMITS.featuredMax} />
            </View>
            {featured.map((id, index) => {
              const w = featuredDocs.data?.get(id);
              return (
                <View key={id}>
                  <Divider />
                  {w ? (
                    <WallpaperRow
                      wallpaper={w}
                      right={
                        <View style={styles.rowActions}>
                          <IconButton name="chevronUp" size={18} accessibilityLabel="Move up" disabled={index === 0} onPress={() => setFeatured(move(featured, index, -1))} />
                          <IconButton name="chevronDown" size={18} accessibilityLabel="Move down" disabled={index === featured.length - 1} onPress={() => setFeatured(move(featured, index, 1))} />
                          <IconButton name="x" size={18} accessibilityLabel="Remove" onPress={() => setFeatured(featured.filter((f) => f !== id))} />
                        </View>
                      }
                    />
                  ) : (
                    <View style={[styles.cardHead, { padding: spacing.lg }]}>
                      <AppText variant="caption" color="textMuted" style={{ flex: 1 }}>
                        {featuredDocs.isFetching ? 'Loading…' : `Missing wallpaper (${id})`}
                      </AppText>
                      <IconButton name="x" size={18} accessibilityLabel="Remove" onPress={() => setFeatured(featured.filter((f) => f !== id))} />
                    </View>
                  )}
                </View>
              );
            })}
          </Card>

          <Card style={{ padding: spacing.lg }}>
            <AppText variant="subheading">Home categories</AppText>
            <AppText variant="caption" color="textMuted" style={{ marginBottom: spacing.md }}>
              Pick the categories shown on the home strip, in order. Leave empty to show all visible categories.
            </AppText>
            <CategoryPicker categories={(categories.data ?? []).filter((c) => c.isActive)} value={homeCategories} onChange={setHomeCategories} max={LIMITS.featuredCategoriesMax} />
          </Card>

          <Card style={{ padding: spacing.lg }}>
            <SwitchRow label="Festival collection" description="A highlighted banner linking to one category" value={festivalEnabled} onValueChange={setFestivalEnabled} />
            {festivalEnabled ? (
              <View style={{ marginTop: spacing.md }}>
                <TextField label="Title" placeholder="e.g. Navratri Specials" value={festivalTitle} onChangeText={setFestivalTitle} maxLength={60} />
                <TextField label="Title (Hindi)" placeholder="e.g. नवरात्रि विशेष" value={festivalTitleHi} onChangeText={setFestivalTitleHi} maxLength={60} />
                <CategoryPicker label="Category" categories={categories.data ?? []} value={festivalCategory} onChange={setFestivalCategory} max={1} />
              </View>
            ) : null}
          </Card>

          <Card style={{ padding: spacing.lg }}>
            <AppText variant="subheading">Section order</AppText>
            <AppText variant="caption" color="textMuted" style={{ marginBottom: spacing.sm }}>
              The latest-wallpapers grid always comes last.
            </AppText>
            {order.map((section, index) => (
              <View key={section} style={styles.cardHead}>
                <AppText variant="body" style={{ flex: 1 }}>
                  {index + 1}. {SECTION_LABELS[section]}
                </AppText>
                <IconButton name="chevronUp" size={18} accessibilityLabel="Move up" disabled={index === 0} onPress={() => setOrder(move(order, index, -1))} />
                <IconButton name="chevronDown" size={18} accessibilityLabel="Move down" disabled={index === order.length - 1} onPress={() => setOrder(move(order, index, 1))} />
              </View>
            ))}
          </Card>

          <Card style={{ padding: spacing.lg }}>
            <AppText variant="subheading" style={{ marginBottom: spacing.sm }}>
              App settings
            </AppText>
            <SwitchRow label="Maintenance mode" description="Shows a 'back soon' screen to every user" value={maintenance} onValueChange={setMaintenance} />
            {maintenance ? (
              <TextField label="Maintenance message" value={maintenanceMessage} onChangeText={setMaintenanceMessage} maxLength={LIMITS.configTextMax} multiline />
            ) : null}
            <TextField
              label="Minimum supported version code"
              helper="Users on older builds are asked to update. 0 = off."
              value={minVersion}
              onChangeText={(v) => setMinVersion(v.replace(/[^0-9]/g, ''))}
              keyboardType="number-pad"
            />
            <TextField label="Update link" placeholder="https://…" value={updateUrl} onChangeText={setUpdateUrl} autoCapitalize="none" keyboardType="url" />
            <TextField label="Support email" placeholder="support@example.com" value={supportEmail} onChangeText={setSupportEmail} autoCapitalize="none" keyboardType="email-address" />
            <TextField label="Share message" placeholder="Shared from DevDarshan" value={shareMessage} onChangeText={setShareMessage} maxLength={LIMITS.configTextMax} />
          </Card>

          <Button title="Save home content" icon="check" onPress={save} loading={saving} fullWidth />
        </ScrollView>
      </KeyboardAvoidingView>

      <Sheet visible={picking} onClose={() => setPicking(false)} title="Add to Today's Darshan" subtitle="Recently published wallpapers">
        {published.isPending ? (
          <LoadingState style={{ minHeight: 200 }} />
        ) : (
          <FlatList
            style={{ maxHeight: 420 }}
            data={available}
            keyExtractor={(w) => w.id}
            ItemSeparatorComponent={() => <Divider inset={80} />}
            renderItem={({ item }) => (
              <WallpaperRow
                wallpaper={item}
                onPress={() => {
                  setFeatured([...featured, item.id]);
                  setPicking(false);
                }}
              />
            )}
            ListEmptyComponent={
              <AppText variant="caption" color="textMuted" style={{ padding: spacing.xl }}>
                No other published wallpapers.
              </AppText>
            }
          />
        )}
      </Sheet>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  cardHead: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  rowActions: {
    flexDirection: 'row',
  },
});
