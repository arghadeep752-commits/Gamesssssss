import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigation, useRoute, type RouteProp } from '@react-navigation/native';
import { useQueryClient } from '@tanstack/react-query';
import { Image } from 'expo-image';
import { useEffect, useRef, useState } from 'react';
import { Controller, useForm } from 'react-hook-form';
import { ActivityIndicator, Alert, KeyboardAvoidingView, ScrollView, StyleSheet, View } from 'react-native';
import { LIMITS, formatBytes, type Wallpaper } from '@devdarshan/shared';
import { parseTags, wallpaperFormSchema, type WallpaperFormValues } from '@devdarshan/shared/validation';
import {
  AppText,
  Button,
  Card,
  IconButton,
  LoadingState,
  ProgressBar,
  ScreenHeader,
  SegmentedControl,
  SwitchRow,
  TextField,
  useTheme,
  useToast,
} from '@devdarshan/ui';
import { CategoryPicker } from '../components/CategoryPicker';
import { StatusBadge } from '../components/StatusBadge';
import { adminKeys, useAllCategories } from '../data/queries';
import { useSession } from '../data/session';
import {
  beginReplacement,
  createWallpaperDraft,
  deleteWallpaper,
  markUploadFailed,
  retryProcessing,
  setFeatured,
  setPublished,
  updateWallpaperMeta,
  uploadWallpaperSource,
  watchWallpaper,
  type UploadHandle,
} from '../data/wallpapers';
import { describeError } from '../errors';
import { pickImage, type PickedImage } from '../lib/pickImage';
import type { AdminNavigation, AdminStackParamList } from '../navigation/types';

type Busy = null | 'save' | 'publish' | 'delete' | 'retry';

const EMPTY_FORM: WallpaperFormValues = {
  title: '',
  description: '',
  categoryIds: [],
  tagsText: '',
  featured: false,
  requestedStatus: 'published',
};

export function WallpaperEditorScreen() {
  const navigation = useNavigation<AdminNavigation>();
  const { params } = useRoute<RouteProp<AdminStackParamList, 'WallpaperEditor'>>();
  const { colors, radii, spacing } = useTheme();
  const toast = useToast();
  const queryClient = useQueryClient();
  const { user } = useSession();
  const uid = user?.uid ?? '';
  const categories = useAllCategories();

  const isNew = !params.wallpaperId;
  const [wallpaperId, setWallpaperId] = useState<string | null>(params.wallpaperId ?? null);
  const [wallpaper, setWallpaper] = useState<Wallpaper | null>(null);
  const [loaded, setLoaded] = useState(isNew);
  const [image, setImage] = useState<PickedImage | null>(null);
  const [uploadFraction, setUploadFraction] = useState<number | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [busy, setBusy] = useState<Busy>(null);
  const uploadHandle = useRef<UploadHandle | null>(null);
  const filled = useRef(false);

  const form = useForm<WallpaperFormValues>({ resolver: zodResolver(wallpaperFormSchema), defaultValues: EMPTY_FORM });

  useEffect(() => {
    if (!wallpaperId) return undefined;
    return watchWallpaper(
      wallpaperId,
      (next) => {
        setWallpaper(next);
        setLoaded(true);
      },
      () => setLoaded(true),
    );
  }, [wallpaperId]);

  useEffect(() => {
    if (!isNew && wallpaper && !filled.current) {
      filled.current = true;
      form.reset({
        title: wallpaper.title,
        description: wallpaper.description,
        categoryIds: wallpaper.categoryIds,
        tagsText: wallpaper.tags.join(', '),
        featured: wallpaper.featured,
        requestedStatus: wallpaper.requestedStatus,
      });
    }
  }, [form, isNew, wallpaper]);

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: adminKeys.wallpapersRoot });
    void queryClient.invalidateQueries({ queryKey: adminKeys.dashboard });
  };

  const showError = (error: unknown, fallback = 'Something went wrong') => {
    const friendly = describeError(error);
    if (!friendly.silent) toast.show({ tone: 'error', message: friendly.title || fallback, detail: friendly.message });
  };

  const choose = async () => {
    try {
      const picked = await pickImage({ minShortEdge: LIMITS.minShortEdgePx, maxBytes: LIMITS.uploadMaxBytes });
      if (picked) {
        setImage(picked);
        setUploadError(null);
      }
    } catch (error) {
      showError(error);
    }
  };

  const runUpload = async (id: string, picked: PickedImage) => {
    setUploadError(null);
    setUploadFraction(0);
    const handle = uploadWallpaperSource(id, picked.uri, picked.ext, picked.mimeType, setUploadFraction);
    uploadHandle.current = handle;
    try {
      await handle.done;
      setImage(null);
      toast.show({ tone: 'success', message: 'Uploaded', detail: 'The server is preparing the preview and thumbnails.' });
    } catch (error) {
      const message = describeError(error).message || 'Upload failed';
      setUploadError(message);
      await markUploadFailed(id, message, uid).catch(() => undefined);
    } finally {
      uploadHandle.current = null;
      setUploadFraction(null);
      invalidate();
    }
  };

  const onSubmit = form.handleSubmit(async (values) => {
    const input = {
      title: values.title.trim(),
      description: values.description.trim(),
      categoryIds: values.categoryIds,
      tags: parseTags(values.tagsText),
      requestedStatus: values.requestedStatus,
    };
    if (!wallpaperId) {
      if (!image) {
        toast.show({ tone: 'error', message: 'Choose an image first' });
        return;
      }
      setBusy('save');
      let id: string;
      try {
        id = await createWallpaperDraft(input, uid);
        setWallpaperId(id);
        filled.current = true;
      } catch (error) {
        setBusy(null);
        showError(error);
        return;
      }
      if (values.featured) {
        await setFeatured(id, true, uid).catch(() =>
          toast.show({ tone: 'warning', message: 'Not added to Today’s Darshan', detail: 'The featured list may be full (30).' }),
        );
      }
      setBusy(null);
      await runUpload(id, image);
      return;
    }
    setBusy('save');
    try {
      await updateWallpaperMeta(wallpaperId, input, uid);
      if (wallpaper && values.featured !== wallpaper.featured) await setFeatured(wallpaperId, values.featured, uid);
      toast.show({ tone: 'success', message: 'Changes saved' });
      invalidate();
    } catch (error) {
      showError(error);
    } finally {
      setBusy(null);
    }
  });

  const uploadReplacement = async () => {
    if (!wallpaperId || !image) return;
    try {
      await beginReplacement(wallpaperId, uid);
      await runUpload(wallpaperId, image);
    } catch (error) {
      showError(error);
    }
  };

  const retryOnServer = async () => {
    if (!wallpaperId) return;
    setBusy('retry');
    try {
      const result = await retryProcessing(wallpaperId);
      toast.show(
        result.ok
          ? { tone: 'success', message: 'Processed successfully' }
          : { tone: 'error', message: 'Processing failed again', detail: 'Replace the image with another file.' },
      );
    } catch (error) {
      showError(error);
    } finally {
      setBusy(null);
    }
  };

  const togglePublished = async () => {
    if (!wallpaperId || !wallpaper) return;
    setBusy('publish');
    try {
      const publish = wallpaper.status !== 'published';
      await setPublished(wallpaperId, publish, uid);
      toast.show({ tone: 'success', message: publish ? 'Published' : 'Moved to drafts', detail: publish ? 'It is now visible in the app.' : 'It is hidden from users.' });
      invalidate();
    } catch (error) {
      showError(error);
    } finally {
      setBusy(null);
    }
  };

  const confirmDelete = () => {
    if (!wallpaperId) return;
    Alert.alert(
      'Delete this wallpaper?',
      'It will be removed from the app, from everyone’s likes and from storage. This cannot be undone.',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Delete',
          style: 'destructive',
          onPress: async () => {
            setBusy('delete');
            try {
              uploadHandle.current?.cancel();
              await deleteWallpaper(wallpaperId);
              toast.show({ tone: 'success', message: 'Wallpaper deleted' });
              invalidate();
              navigation.goBack();
            } catch (error) {
              showError(error);
              setBusy(null);
            }
          },
        },
      ],
    );
  };

  if (!loaded) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Wallpaper" onBack={() => navigation.goBack()} />
        <LoadingState />
      </View>
    );
  }

  if (!isNew && !wallpaper) {
    return (
      <View style={[styles.root, { backgroundColor: colors.background }]}>
        <ScreenHeader title="Wallpaper" onBack={() => navigation.goBack()} />
        <AppText variant="body" color="textMuted" style={{ padding: spacing.xl }}>
          This wallpaper no longer exists.
        </AppText>
      </View>
    );
  }

  const uploading = uploadFraction !== null;
  const previewUri = image?.uri ?? wallpaper?.previewUrl ?? wallpaper?.thumbnailUrl ?? null;
  const canPublish = !!wallpaper && wallpaper.processing === 'ready' && wallpaper.status !== 'deleting';
  const requestedStatus = form.watch('requestedStatus');

  return (
    <View style={[styles.root, { backgroundColor: colors.background }]}>
      <ScreenHeader
        title={isNew ? 'Upload wallpaper' : 'Edit wallpaper'}
        onBack={() => navigation.goBack()}
        right={
          wallpaperId ? (
            <IconButton name="trash" accessibilityLabel="Delete wallpaper" color={colors.danger} onPress={confirmDelete} disabled={busy === 'delete'} />
          ) : null
        }
      />
      <KeyboardAvoidingView behavior="padding" style={styles.root}>
        <ScrollView contentContainerStyle={{ padding: spacing.lg, paddingBottom: spacing.xxxl }} keyboardShouldPersistTaps="handled">
          <View style={[styles.imageBox, { borderRadius: radii.lg, backgroundColor: wallpaper?.dominantColor ?? colors.surfaceAlt }]}>
            {previewUri ? (
              <Image source={{ uri: previewUri }} contentFit="contain" style={StyleSheet.absoluteFill} transition={150} />
            ) : (
              <AppText variant="body" color="textMuted" align="center" style={{ padding: spacing.xl }}>
                Choose a portrait image (JPEG, PNG or WebP, up to {formatBytes(LIMITS.uploadMaxBytes)}, at least {LIMITS.minShortEdgePx}px wide).
              </AppText>
            )}
            {wallpaper ? (
              <View style={styles.badge}>
                <StatusBadge wallpaper={wallpaper} />
              </View>
            ) : null}
          </View>

          {image ? (
            <AppText variant="caption" color="textMuted" style={{ marginTop: spacing.sm }}>
              Selected: {image.width} × {image.height}
              {image.fileSize ? ` · ${formatBytes(image.fileSize)}` : ''} · {image.ext.toUpperCase()}
            </AppText>
          ) : wallpaper && wallpaper.width ? (
            <AppText variant="caption" color="textMuted" style={{ marginTop: spacing.sm }}>
              Original: {wallpaper.width} × {wallpaper.height} · {formatBytes(wallpaper.fileSizeBytes)}
            </AppText>
          ) : null}

          <View style={[styles.row, { marginTop: spacing.md }]}>
            <Button
              title={image ? 'Choose another' : wallpaper ? 'Replace image' : 'Choose image'}
              icon="image"
              variant="outline"
              onPress={choose}
              disabled={uploading}
              style={{ flex: 1 }}
            />
            {wallpaperId && image && !uploading ? (
              <Button title="Upload new image" icon="upload" onPress={uploadReplacement} style={{ flex: 1 }} />
            ) : null}
          </View>

          {uploading ? (
            <Card style={{ marginTop: spacing.lg, padding: spacing.lg, gap: spacing.sm }}>
              <View style={styles.row}>
                <AppText variant="bodyStrong" style={{ flex: 1 }}>
                  Uploading… {Math.round((uploadFraction ?? 0) * 100)}%
                </AppText>
                <Button title="Cancel" size="sm" variant="ghost" onPress={() => uploadHandle.current?.cancel()} />
              </View>
              <ProgressBar progress={uploadFraction ?? 0} />
            </Card>
          ) : wallpaper && wallpaper.processing === 'processing' ? (
            <Card style={[styles.statusCard, { marginTop: spacing.lg, padding: spacing.lg }]}>
              <ActivityIndicator color={colors.primary} />
              <AppText variant="body" style={{ flex: 1 }}>
                Processing on the server: creating preview, thumbnail and a clean original…
              </AppText>
            </Card>
          ) : wallpaper && wallpaper.processing === 'failed' ? (
            <Card style={{ marginTop: spacing.lg, padding: spacing.lg, gap: spacing.sm, borderColor: colors.danger }}>
              <AppText variant="bodyStrong" color="danger">
                {wallpaper.status === 'published' ? 'The new image could not be processed' : 'Not ready yet'}
              </AppText>
              <AppText variant="caption" color="textMuted">
                {uploadError ?? wallpaper.processingError ?? 'The image could not be processed.'}
              </AppText>
              <View style={styles.row}>
                <Button title="Retry processing" size="sm" variant="secondary" onPress={retryOnServer} loading={busy === 'retry'} />
                {image ? <Button title="Retry upload" size="sm" variant="outline" onPress={uploadReplacement} /> : null}
              </View>
            </Card>
          ) : wallpaper && wallpaper.processing === 'uploading' && !uploading ? (
            <Card style={{ marginTop: spacing.lg, padding: spacing.lg, gap: spacing.xs }}>
              <AppText variant="bodyStrong">Waiting for the upload</AppText>
              <AppText variant="caption" color="textMuted">
                The upload was interrupted. Choose the image again and tap “Upload new image”. Unfinished drafts are cleaned up
                automatically after 24 hours.
              </AppText>
            </Card>
          ) : null}

          <View style={{ marginTop: spacing.xl }}>
            <Controller
              control={form.control}
              name="title"
              render={({ field, fieldState }) => (
                <TextField
                  label="Title"
                  placeholder="e.g. Shri Ram Darbar"
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  error={fieldState.error?.message}
                  maxLength={LIMITS.titleMax}
                  showCount
                />
              )}
            />
            <Controller
              control={form.control}
              name="categoryIds"
              render={({ field, fieldState }) => (
                <CategoryPicker
                  label="Categories"
                  categories={categories.data ?? []}
                  value={field.value}
                  onChange={field.onChange}
                  max={LIMITS.categoriesPerWallpaperMax}
                  error={fieldState.error?.message}
                />
              )}
            />
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
                  maxLength={LIMITS.descriptionMax}
                  multiline
                  showCount
                />
              )}
            />
            <Controller
              control={form.control}
              name="tagsText"
              render={({ field, fieldState }) => (
                <TextField
                  label="Tags"
                  helper="Separate with commas, e.g. ram, ayodhya, राम"
                  value={field.value}
                  onChangeText={field.onChange}
                  onBlur={field.onBlur}
                  error={fieldState.error?.message}
                  autoCapitalize="none"
                />
              )}
            />
            <Controller
              control={form.control}
              name="featured"
              render={({ field }) => (
                <SwitchRow
                  label="Feature in Today’s Darshan"
                  description="Shown at the top of the home screen"
                  value={field.value}
                  onValueChange={field.onChange}
                />
              )}
            />
            {isNew && !wallpaperId ? (
              <Controller
                control={form.control}
                name="requestedStatus"
                render={({ field }) => (
                  <View style={{ marginTop: spacing.md }}>
                    <AppText variant="label" color="textMuted" style={{ marginBottom: spacing.xs }}>
                      After processing
                    </AppText>
                    <SegmentedControl
                      value={field.value}
                      onChange={field.onChange}
                      options={[
                        { value: 'published', label: 'Publish', icon: 'eye' },
                        { value: 'draft', label: 'Keep as draft', icon: 'eyeOff' },
                      ]}
                    />
                  </View>
                )}
              />
            ) : null}
          </View>

          <View style={{ marginTop: spacing.xl, gap: spacing.sm }}>
            {!wallpaperId ? (
              <Button
                title={requestedStatus === 'published' ? 'Upload and publish' : 'Upload as draft'}
                icon="upload"
                onPress={onSubmit}
                loading={busy === 'save' || uploading}
                disabled={!image}
                fullWidth
                testID="editor-submit"
              />
            ) : (
              <>
                <Button title="Save changes" icon="check" onPress={onSubmit} loading={busy === 'save'} disabled={uploading} fullWidth />
                {wallpaper && wallpaper.status !== 'deleting' ? (
                  <Button
                    title={wallpaper.status === 'published' ? 'Unpublish' : 'Publish now'}
                    icon={wallpaper.status === 'published' ? 'eyeOff' : 'eye'}
                    variant={wallpaper.status === 'published' ? 'outline' : 'secondary'}
                    onPress={togglePublished}
                    loading={busy === 'publish'}
                    disabled={wallpaper.status !== 'published' && !canPublish}
                    fullWidth
                  />
                ) : null}
                {wallpaper && wallpaper.status === 'deleting' ? (
                  <Button title="Retry delete" icon="trash" variant="danger" onPress={confirmDelete} loading={busy === 'delete'} fullWidth />
                ) : null}
              </>
            )}
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  imageBox: {
    height: 380,
    overflow: 'hidden',
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    position: 'absolute',
    top: 10,
    left: 10,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  statusCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
});
