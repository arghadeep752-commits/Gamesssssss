import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  Modal,
  Pressable,
  ScrollView,
  StyleSheet,
  Switch,
  Text,
  View,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { Settings } from '../state/settings';
import {
  THEMES,
  THEME_ORDER,
  ThemeId,
  buildPalette,
  fonts,
  usePalette,
} from '../theme/theme';
import { GlassButton } from './GlassButton';
import { Segmented } from './Segmented';

export const APP_VERSION = '2.0.0';

interface Props {
  visible: boolean;
  settings: Settings;
  historyCount: number;
  still: boolean;
  onChange: (patch: Partial<Settings>) => void;
  onClearHistory: () => void;
  onClose: () => void;
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const p = usePalette();
  return (
    <View style={styles.section}>
      <Text
        style={[styles.sectionTitle, { color: p.inkMuted }]}
        maxFontSizeMultiplier={1.3}
      >
        {title}
      </Text>
      {children}
    </View>
  );
}

function Swatch({
  id,
  selected,
  onPress,
}: {
  id: ThemeId;
  selected: boolean;
  onPress: () => void;
}) {
  const p = usePalette();
  const sample = buildPalette(id, p.scheme);
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="radio"
      accessibilityState={{ checked: selected }}
      accessibilityLabel={`${THEMES[id].name} color theme`}
      style={styles.swatchWrap}
    >
      <View
        style={[
          styles.swatchRing,
          { borderColor: selected ? p.ink : 'transparent' },
        ]}
      >
        <View
          style={[
            styles.swatch,
            {
              backgroundColor: sample.accent,
              backgroundImage: `${p.sheen}, ${sample.liquidGradient}`,
              borderColor: p.glassBorder,
            },
          ]}
        />
      </View>
      <Text
        maxFontSizeMultiplier={1.2}
        style={[
          styles.swatchLabel,
          {
            color: selected ? p.ink : p.inkMuted,
            fontFamily: selected ? fonts.medium : fonts.regular,
          },
        ]}
      >
        {THEMES[id].name}
      </Text>
    </Pressable>
  );
}

export function SettingsSheet({
  visible,
  settings,
  historyCount,
  still,
  onChange,
  onClearHistory,
  onClose,
}: Props) {
  const p = usePalette();
  const insets = useSafeAreaInsets();
  // The backdrop fades while the sheet springs up; the modal stays mounted
  // until the closing animation has finished.
  const [mounted, setMounted] = useState(visible);
  const [sheetHeight, setSheetHeight] = useState(700);
  const progress = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (visible) {
      setMounted(true);
      Animated.spring(progress, {
        toValue: 1,
        stiffness: still ? 1000 : 230,
        damping: still ? 100 : 26,
        mass: 1,
        useNativeDriver: true,
      }).start();
    } else {
      Animated.timing(progress, {
        toValue: 0,
        duration: still ? 0 : 220,
        easing: Easing.in(Easing.cubic),
        useNativeDriver: true,
      }).start(({ finished }) => finished && setMounted(false));
    }
  }, [visible, still, progress]);

  return (
    <Modal
      visible={mounted}
      transparent
      animationType="none"
      statusBarTranslucent
      navigationBarTranslucent
      onRequestClose={onClose}
    >
      <View style={styles.root}>
        <Animated.View
          style={[
            StyleSheet.absoluteFill,
            { backgroundColor: p.backdrop, opacity: progress },
          ]}
        >
          <Pressable
            style={StyleSheet.absoluteFill}
            onPress={onClose}
            accessibilityRole="button"
            accessibilityLabel="Close settings"
          />
        </Animated.View>
        <Animated.View
          onLayout={e => setSheetHeight(e.nativeEvent.layout.height)}
          style={[
            styles.sheet,
            {
              backgroundColor: p.sheet,
              backgroundImage: p.sheen,
              borderColor: p.sheetBorder,
              paddingBottom: insets.bottom + 18,
              transform: [
                {
                  translateY: progress.interpolate({
                    inputRange: [0, 1],
                    outputRange: [sheetHeight + 40, 0],
                  }),
                },
              ],
            },
          ]}
        >
          <View style={[styles.handle, { backgroundColor: p.inkFaint }]} />
          <View style={styles.header}>
            <Text
              style={[styles.title, { color: p.ink }]}
              accessibilityRole="header"
              maxFontSizeMultiplier={1.3}
            >
              Settings
            </Text>
            <GlassButton
              width={76}
              height={38}
              onPress={onClose}
              accessibilityLabel="Done"
            >
              <Text
                maxFontSizeMultiplier={1.2}
                style={[styles.doneText, { color: p.ink }]}
              >
                Done
              </Text>
            </GlassButton>
          </View>
          <ScrollView contentContainerStyle={styles.body} bounces={false}>
            <Section title="Color">
              <View style={styles.swatches}>
                {THEME_ORDER.map(id => (
                  <Swatch
                    key={id}
                    id={id}
                    selected={settings.palette === id}
                    onPress={() => onChange({ palette: id })}
                  />
                ))}
              </View>
            </Section>
            <Section title="Appearance">
              <Segmented
                accessibilityLabel="Appearance"
                value={settings.theme}
                still={still}
                onChange={theme => onChange({ theme })}
                options={[
                  { value: 'system', label: 'System' },
                  { value: 'light', label: 'Light' },
                  { value: 'dark', label: 'Dark' },
                ]}
              />
            </Section>
            <Section title="Number format">
              <Segmented
                accessibilityLabel="Number format"
                value={settings.grouping}
                still={still}
                onChange={grouping => onChange({ grouping })}
                options={[
                  {
                    value: 'intl',
                    label: '1,234,567',
                    a11y: 'International grouping',
                  },
                  {
                    value: 'indian',
                    label: '12,34,567',
                    a11y: 'Indian grouping',
                  },
                  { value: 'none', label: '1234567', a11y: 'No grouping' },
                ]}
              />
            </Section>
            <Section title="Angle unit">
              <Segmented
                accessibilityLabel="Angle unit"
                value={settings.angle}
                still={still}
                onChange={angle => onChange({ angle })}
                options={[
                  { value: 'deg', label: 'Degrees' },
                  { value: 'rad', label: 'Radians' },
                ]}
              />
            </Section>
            <View style={[styles.line, { borderColor: p.divider }]}>
              <Text
                style={[styles.lineLabel, { color: p.ink }]}
                maxFontSizeMultiplier={1.3}
              >
                Vibrate on key press
              </Text>
              <Switch
                value={settings.haptics}
                onValueChange={haptics => onChange({ haptics })}
                trackColor={{ false: p.segment, true: p.accent }}
                thumbColor="#FFFFFF"
                accessibilityLabel="Vibrate on key press"
              />
            </View>
            <View style={[styles.line, { borderColor: p.divider }]}>
              <View style={styles.lineText}>
                <Text
                  style={[styles.lineLabel, { color: p.ink }]}
                  maxFontSizeMultiplier={1.3}
                >
                  History
                </Text>
                <Text
                  style={[styles.lineDetail, { color: p.inkMuted }]}
                  maxFontSizeMultiplier={1.3}
                >
                  {historyCount === 0
                    ? 'Empty'
                    : `${historyCount} ${
                        historyCount === 1 ? 'calculation' : 'calculations'
                      } saved`}
                </Text>
              </View>
              <GlassButton
                width={124}
                height={38}
                tone="danger"
                disabled={historyCount === 0}
                onPress={onClearHistory}
                accessibilityLabel="Clear history"
              >
                <Text
                  maxFontSizeMultiplier={1.2}
                  style={[styles.clearText, { color: p.danger }]}
                >
                  Clear history
                </Text>
              </GlassButton>
            </View>
            <Text
              style={[styles.footer, { color: p.inkFaint }]}
              maxFontSizeMultiplier={1.3}
            >
              Calc Pro {APP_VERSION}
            </Text>
          </ScrollView>
        </Animated.View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
    justifyContent: 'flex-end',
  },
  sheet: {
    borderTopLeftRadius: 32,
    borderTopRightRadius: 32,
    borderWidth: 1,
    borderBottomWidth: 0,
    maxHeight: '90%',
    width: '100%',
    maxWidth: 560,
    alignSelf: 'center',
  },
  handle: {
    width: 38,
    height: 5,
    borderRadius: 3,
    alignSelf: 'center',
    marginTop: 10,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingLeft: 26,
    paddingRight: 20,
    paddingTop: 10,
  },
  title: {
    fontFamily: fonts.semibold,
    fontSize: 22,
    letterSpacing: -0.3,
  },
  doneText: {
    fontFamily: fonts.medium,
    fontSize: 15,
  },
  body: {
    paddingHorizontal: 22,
    paddingTop: 4,
  },
  section: {
    marginTop: 20,
  },
  sectionTitle: {
    fontFamily: fonts.medium,
    fontSize: 13,
    marginBottom: 10,
    marginLeft: 4,
  },
  swatches: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingHorizontal: 4,
  },
  swatchWrap: {
    alignItems: 'center',
    gap: 6,
    minWidth: 64,
  },
  swatchRing: {
    width: 58,
    height: 58,
    borderRadius: 29,
    borderWidth: 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  swatch: {
    width: 46,
    height: 46,
    borderRadius: 23,
    borderWidth: 1,
  },
  swatchLabel: {
    fontSize: 13,
  },
  line: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    borderTopWidth: StyleSheet.hairlineWidth,
    marginTop: 22,
    paddingTop: 16,
    paddingHorizontal: 4,
    gap: 12,
  },
  lineText: {
    flex: 1,
  },
  lineLabel: {
    fontFamily: fonts.regular,
    fontSize: 16,
  },
  lineDetail: {
    fontFamily: fonts.regular,
    fontSize: 13,
    marginTop: 2,
  },
  clearText: {
    fontFamily: fonts.medium,
    fontSize: 14,
  },
  footer: {
    fontFamily: fonts.regular,
    fontSize: 12,
    textAlign: 'center',
    marginTop: 28,
  },
});
