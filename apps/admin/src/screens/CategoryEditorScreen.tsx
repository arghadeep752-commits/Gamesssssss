import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { Alert, KeyboardAvoidingView, ScrollView, StyleSheet, View } from 'react-native';
import { LIMITS, categoryLabel, isValidSlug, slugForName, type Category } from '@devdarshan/shared';
import { categoryFormSchema, type CategoryFormValues } from '@devdarshan/shared/validation';
import {
  AppText,
  Button,
  Card,
  LoadingState,
  ProgressBar,
  ScreenHeader,
  SwitchRow,
  TextField,
  useTheme,
  useToast,
} from '@devdarshan/ui';
import { CategoryPicker } from '../components/CategoryPicker';
import { createCategory, deleteCategory, updateCategory, uploadCategoryCover, watchCategory } from '../data/categories';
import { adminKeys, useAllCategories } from '../data/queries';
import { useSession } from '../data/session';
import { describeError } from '../errors';
import { pickImage } from '../lib/pickImage';
import type { AdminNavigation, AdminStackParamList } from '../navigation/types';

export function CategoryEditorScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const { params } = useRoute<RouteProp<AdminStackParamList, 'CategoryEditor'>>();
  const { colors, radii, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const uid = user?.uid ?? '';
  const all = useAllCategories();

  const [categoryId, setCategoryId] = useState<string | null>(params.categoryId ?? null);
  const isNew = !params.categoryId;
  const [category, setCategory] = useState<Category | null>(null);
  const [loaded, setLoaded] = useState(isNew);
  const [slug, setSlug] = useState('');
  const [slugEdited, setSlugEdited] = useState(false);
  const [saving, setSaving] = useState(false);
  const [coverProgress, setCoverProgress] = useState<number | null>(null);
  const [moveTo, setMoveTo] = useState<string[]>([]);
  const [deleting, setDeleting] = useState(false);
  const filled = useRef(false);

  const form = useForm<CategoryFormValues>({
    resolver: zodResolver(categoryFormSchema),
    defaultValues: { name: '', nameHi: '', description: '', isActive: true },
  });
  const name = form.watch('name');
  const nameHi = form.watch('nameHi');

  useEffect(() => {
    if (!categoryId) return undefined;
    return watchCategory(
      categoryId,
      (c) => {
        setCategory(c);
        setLoaded(true);
      },
      () => setLoaded(true),
    );
  }, [categoryId]);

  useEffect(() => {
    if (!isNew && category && !filled.current) {
      filled.current = true;
      form.reset({ name: category.name, nameHi: category.nameHi, description: category.description, isActive: category.isActive });
    }
  }, [category, form, isNew]);

  useEffect(() => {
    if (isNew && !slugEdited) setSlug(slugForName(name || nameHi || ''));
  }, [isNew, name, nameHi, slugEdited]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: adminKeys.categories });
    void queryClient.invalidateQueries({ queryKey: adminKeys.dashboard });
  };

  const fail = (error: unknown) => {
    const friendly = describeError(error);
    toast.show({ tone: 'error', message: friendly.title, detail: friendly.message });
  };

  const onSave = form.handleSubmit(async (values) => {
    setSaving(true);
    try {
      if (!categoryId) {
        if (!isValidSlug(slug)) {
          toast.show({ tone: 'error', message: 'Invalid id', detail: 'Use 2–48 lowercase letters, numbers or hyphens.' });
          return;
        }
        const maxOrder = Math.max(0, ...(all.data ?? []).map((c) => c.sortOrder));
        await createCategory(slug, values, maxOrder + 10, uid);
        setCategoryId(slug);
        filled.current = true;
        toast.show({ tone: 'success', message: 'Category created', detail: 'Add a cover image if you like.' });
      } else {
        await updateCategory(categoryId, values, uid);
        toast.show({ tone: 'success', message: 'Category saved' });
      }
      invalidate();
    } catch (error) {
      fail(error);
    } finally {
      setSaving(false);
    }
  });

  const changeCover = async () => {
    if (!categoryId) return;
    try {
      const picked = await pickImage({ minShortEdge: 300, maxBytes: LIMITS.coverUploadMaxBytes });
      if (!picked) return;
      setCoverProgress(0);
      await uploadCategoryCover(categoryId, picked.uri, picked.ext, picked.mimeType, setCoverProgress);
      toast.show({ tone: 'success', message: 'Cover uploaded', detail: 'It appears once the server has processed it.' });
    } catch (error) {
      fail(error);
    } finally {
      setCoverProgress(null);
    }
  };

  const remove = () => {
    if (!categoryId) return;
    const target = moveTo[0] ?? null;
    Alert.alert(
      'Delete this category?',
      target
        ? `Its wallpapers will be moved to “${all.data?.find((c) => c.id === target)?.name ?? target}”. This cannot be undone.`
        : 'Wallpapers are never left without a category: if any use it, choose where to move them first, or hide the category instead.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            setDeleting(true);
            try {
              const result = await deleteCategory(categoryId, target);
              toast.show({ tone: 'success', message: 'Category deleted', detail: result.moved ? `${result.moved} wallpaper(s) moved.` : undefined });
              invalidate();
              navigation.goBack();
            } catch (error) {
              fail(error);
              setDeleting(false);
            }
          },
        },
      ],
    );
  };

  if (!loaded) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Category" onBack={() => navigation.goBack()} />
        <LoadingState />
      </View>
    );
  }

  const coverUri = category?.coverUrl ?? null;
  const others = (all.data ?? []).filter((c) => c.id !== categoryId);

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader
        title={categoryId ? (category ? categoryLabel(category) : 'Category') : 'New category'}
        subtitle={categoryId ? `id: ${categoryId}` : undefined}
        onBack={() => navigation.goBack()}
      />
      <KeyboardAvoidingView behavior="padding" style={styles.root}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxxl }} keyboardShouldPersistTaps="handled">
          <Controller
            control={form.control}
            name="name"
            render={({ field, fieldState }) => (
              <TextField
                label="Name (English)"
                placeholder="e.g. Shri Ram"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                maxLength={LIMITS.categoryNameMax}
              />
            )}
          />
          <Controller
            control={form.control}
            name="nameHi"
            render={({ field, fieldState }) => (
              <TextField
                label="Name (Hindi)"
                placeholder="e.g. श्री राम"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                maxLength={LIMITS.categoryNameMax}
              />
            )}
          />
          {!categoryId ? (
            <TextField
              label="Id (used in links; can't be changed later)"
              value={slug}
              onChangeText={(v) => {
                setSlugEdited(true);
                setSlug(v.toLowerCase().replace(/[^a-z0-9-]/g, ''));
              }}
              autoCapitalize="none"
              error={slug && !isValidSlug(slug) ? '2–48 lowercase letters, numbers or hyphens' : undefined}
            />
          ) : null}
          <Controller
            control={form.control}
            name="description"
            render={({ field, fieldState }) => (
              <TextField
                label="Description (optional)"
                value={field.value}
                onChangeText={field.onChange}
                onBlur={field.onBlur}
                error={fieldState.error?.message}
                maxLength={LIMITS.categoryDescriptionMax}
                multiline
                showCount
              />
            )}
          />
          <Controller
            control={form.control}
            name="isActive"
            render={({ field }) => (
              <SwitchRow
                label="Visible in the app"
                description="Hidden categories keep their wallpapers but disappear from browsing"
                value={field.value}
                onValueChange={field.onChange}
              />
            )}
          />
          <Button
            title={categoryId ? 'Save category' : 'Create category'}
            icon="check"
            onPress={onSave}
            loading={saving}
            fullWidth
            style={{ marginTop: spacing.lg }}
          />

          {categoryId ? (
            <>
              <AppText variant="subheading" style={{ marginTop: spacing.xxl, marginBottom: spacing.sm }}>
                Cover image
              </AppText>
              <View style={[styles.cover, { borderRadius: radii.md, backgroundColor: colors.surfaceAlt }]}>
                {coverUri ? (
                  <Image source={{ uri: coverUri }} contentFit="cover" style={StyleSheet.absoluteFill} transition={150} />
                ) : (
                  <AppText variant="caption" color="textMuted">
                    No cover yet: the app shows the Hindi name as artwork.
                  </AppText>
                )}
              </View>
              {coverProgress !== null ? (
                <View style={{ marginTop: spacing.sm }}>
                  <ProgressBar progress={coverProgress} />
                </View>
              ) : null}
              <Button
                title={coverUri ? 'Change cover' : 'Upload cover'}
                icon="image"
                variant="outline"
                onPress={changeCover}
                loading={coverProgress !== null}
                style={{ marginTop: spacing.sm }}
              />

              <Card style={{ marginTop: spacing.xxl, padding: spacing.lg, borderColor: colors.dangerSoft }}>
                <AppText variant="subheading" color="danger">
                  Delete category
                </AppText>
                <AppText variant="caption" color="textMuted" style={{ marginTop: spacing.xs, marginBottom: spacing.md }}>
                  Wallpapers are never orphaned. If any wallpaper uses this category, choose a category to move them to. To
                  keep everything, switch off “Visible in the app” instead.
                </AppText>
                <CategoryPicker label="Move its wallpapers to" categories={others} value={moveTo} onChange={setMoveTo} max={1} />
                <Button title="Delete category" icon="trash" variant="danger" onPress={remove} loading={deleting} fullWidth />
              </Card>
            </>
          ) : null}
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  cover: {
    height: 160,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
});
