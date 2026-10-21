import { StyleSheet, View } from 'react-native';
import { formatPercent } from '@devdarshan/shared';
import { AppText, Button, ProgressBar, useTheme } from '@devdarshan/ui';
import type { ActionProgress } from '../features/useWallpaperActions';

const LABELS: Record<ActionProgress['kind'], string> = {
  set: 'Preparing wallpaper',
  download: 'Downloading full quality',
  share: 'Preparing to share',
};

const PHASES: Record<ActionProgress['phase'], string> = {
  downloading: '',
  applying: 'Applying wallpaper…',
  saving: 'Saving to your gallery…',
  opening: 'Opening share options…',
};

export function ActionProgressCard({ progress, onCancel }: { progress: ActionProgress; onCancel: () => void }) {
  const { colors, radii, spacing } = useTheme();
  const downloading = progress.phase === 'downloading';
  const title = downloading ? LABELS[progress.kind] : PHASES[progress.phase];
  return (
    <View
      accessibilityLiveRegion="polite"
      style={[styles.card, { backgroundColor: colors.surface, borderRadius: radii.lg, padding: spacing.lg }]}
    >
      <View style={styles.header}>
        <AppText variant="bodyStrong" style={{ flex: 1 }}>
          {title}
        </AppText>
        {downloading && progress.fraction !== null ? (
          <AppText variant="label" color="textMuted">
            {formatPercent(progress.fraction)}
          </AppText>
        ) : null}
      </View>
      <View style={{ marginTop: spacing.sm }}>
        <ProgressBar progress={progress.fraction ?? 0} indeterminate={progress.fraction === null} />
      </View>
      {downloading ? (
        <Button title="Cancel" variant="ghost" size="sm" onPress={onCancel} style={{ alignSelf: 'flex-end', marginTop: spacing.xs }} />
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    elevation: 4,
    shadowColor: '#000',
    shadowOpacity: 0.15,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 3 },
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
  },
});
