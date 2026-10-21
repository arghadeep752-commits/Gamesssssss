import { useState } from 'react';
import { View } from 'react-native';
import { DevDarshanNative, nativeErrorMessage } from '@devdarshan/native';
import { AppText, Button, Card, useTheme } from '@devdarshan/ui';

interface CheckLine {
  label: string;
  ok: boolean;
  detail: string;
}

/**
 * Shown only in test builds (no Firebase project connected yet). It runs the real
 * native features on this device with a generated, labelled image:
 *
 *  - set it as the Home and Lock screen wallpaper (each reported separately);
 *  - save it to Pictures/DevDarshan;
 *  - open the share sheet with it.
 *
 * CI's emulator smoke test taps these buttons and then checks the system state
 * (dumpsys wallpaper, MediaStore, the resumed activity). Release builds never show it.
 */
export function SelfTestPanel() {
  const { colors, spacing } = useTheme();
  const [running, setRunning] = useState(false);
  const [lines, setLines] = useState<CheckLine[] | null>(null);
  const [imagePath, setImagePath] = useState<string | null>(null);
  const [shareNote, setShareNote] = useState<string | null>(null);

  const run = async () => {
    setRunning(true);
    setShareNote(null);
    const out: CheckLine[] = [];
    try {
      const image = await DevDarshanNative.createSelfTestImage();
      setImagePath(image.path);
      out.push({ label: 'Test image', ok: true, detail: `${image.width}×${image.height}` });
      try {
        const result = await DevDarshanNative.setWallpaper(image.path, 'both');
        out.push({ label: 'Home screen', ok: result.home === 'set', detail: result.home === 'set' ? 'set' : (result.homeError ?? result.home) });
        out.push({ label: 'Lock screen', ok: result.lock === 'set', detail: result.lock === 'set' ? 'set' : (result.lockError ?? result.lock) });
      } catch (error) {
        out.push({ label: 'Set wallpaper', ok: false, detail: nativeErrorMessage(error) });
      }
      try {
        const saved = await DevDarshanNative.saveToGallery(image.path, `DevDarshan-selftest-${Date.now()}.png`, image.mimeType);
        out.push({ label: 'Save to gallery', ok: true, detail: saved.location });
      } catch (error) {
        out.push({ label: 'Save to gallery', ok: false, detail: nativeErrorMessage(error) });
      }
    } catch (error) {
      out.push({ label: 'Test image', ok: false, detail: nativeErrorMessage(error) });
    }
    setLines(out);
    setRunning(false);
  };

  const share = async () => {
    if (!imagePath) return;
    try {
      const result = await DevDarshanNative.shareImage(imagePath, 'image/png', 'chooser', {
        text: 'DevDarshan self-test',
        chooserTitle: 'Share test image',
      });
      setShareNote(result.opened ? `Share sheet opened (${result.target})` : 'Share sheet did not open');
    } catch (error) {
      setShareNote(`Share failed: ${nativeErrorMessage(error)}`);
    }
  };

  const passed = lines !== null && lines.length > 0 && lines.every((l) => l.ok);

  return (
    <Card style={{ padding: spacing.lg, marginTop: spacing.xl, gap: spacing.sm }} testID="self-test-panel">
      <AppText variant="subheading">Device self-test</AppText>
      <AppText variant="caption" color="textMuted">
        Checks this phone's wallpaper, gallery and share support with a generated test image. Running it changes your
        wallpaper.
      </AppText>
      <Button title="Run self-test" icon="sliders" onPress={run} loading={running} testID="self-test-run" />
      {lines ? (
        <View style={{ gap: 4, marginTop: spacing.xs }}>
          {lines.map((line) => (
            <AppText key={line.label} variant="caption" style={{ color: line.ok ? colors.success : colors.danger }}>
              {line.ok ? '✓' : '✗'} {line.label}: {line.detail}
            </AppText>
          ))}
          <AppText variant="bodyStrong" testID="self-test-result" style={{ color: passed ? colors.success : colors.danger }}>
            {passed ? 'Self-test passed' : 'Self-test failed'}
          </AppText>
        </View>
      ) : null}
      {imagePath ? (
        <Button title="Open share sheet" icon="share" variant="outline" onPress={share} testID="self-test-share" />
      ) : null}
      {shareNote ? (
        <AppText variant="caption" color="textMuted" testID="self-test-share-result">
          {shareNote}
        </AppText>
      ) : null}
    </Card>
  );
}
