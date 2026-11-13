import React, { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { hairline, palette, radius, space } from '../../theme/tokens';
import { Header } from '../../ui/Header';
import { Icon } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';
import { APACHE_2, MIT_BODY, OFL_INTER } from './licenseTexts';

type Item = { name: string; what: string; license: 'MIT' | 'Apache 2.0' | 'SIL OFL 1.1'; holder: string };

const ITEMS: Item[] = [
  { name: 'React Native', what: 'App framework', license: 'MIT', holder: 'Meta Platforms, Inc. and affiliates' },
  { name: 'React', what: 'User interface library', license: 'MIT', holder: 'Meta Platforms, Inc. and affiliates' },
  { name: 'Expo SDK', what: 'Native modules, media library, video player, images, fonts', license: 'MIT', holder: '650 Industries, Inc. (aka Expo)' },
  { name: 'AndroidX CameraX', what: 'Camera capture', license: 'Apache 2.0', holder: 'The Android Open Source Project' },
  { name: 'AndroidX Media3', what: 'Video playback and export', license: 'Apache 2.0', holder: 'The Android Open Source Project' },
  { name: 'AndroidX ExifInterface', what: 'Photo metadata', license: 'Apache 2.0', holder: 'The Android Open Source Project' },
  { name: 'React Navigation', what: 'Screens and navigation', license: 'MIT', holder: 'React Navigation contributors' },
  { name: 'React Native Reanimated', what: 'Animation', license: 'MIT', holder: 'Software Mansion' },
  { name: 'React Native Worklets', what: 'UI thread code', license: 'MIT', holder: 'Software Mansion' },
  { name: 'React Native Gesture Handler', what: 'Touch gestures', license: 'MIT', holder: 'Software Mansion' },
  { name: 'React Native Screens', what: 'Native screen containers', license: 'MIT', holder: 'Software Mansion' },
  { name: 'React Native SVG', what: 'Icons and dials', license: 'MIT', holder: 'Horcrux and contributors' },
  { name: 'React Native Safe Area Context', what: 'Screen insets', license: 'MIT', holder: 'Th3rd Wave' },
  { name: 'Async Storage', what: 'Settings storage', license: 'MIT', holder: 'React Native Community contributors' },
  { name: 'Zustand', what: 'App state', license: 'MIT', holder: 'Paul Henschel and contributors' },
  { name: 'Inter', what: 'Typeface', license: 'SIL OFL 1.1', holder: 'The Inter Project Authors' },
];

function textFor(item: Item): string {
  if (item.license === 'MIT') return `Copyright (c) ${item.holder}\n\n${MIT_BODY}`;
  if (item.license === 'SIL OFL 1.1') return OFL_INTER;
  return `Copyright (c) ${item.holder}\n\nLicensed under the Apache License, Version 2.0.\n\n${APACHE_2}`;
}

export function LicensesScreen() {
  const insets = useSafeAreaInsets();
  const [open, setOpen] = useState<string | null>(null);
  return (
    <View style={styles.root}>
      <Header title="Open-source licences" large />
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        <T variant="body" color={palette.ash} style={styles.intro}>
          Camero Plus is built with these open-source projects. Tap one to read its licence.
        </T>
        <View style={styles.card}>
          {ITEMS.map((item, i) => {
            const expanded = open === item.name;
            return (
              <View key={item.name} style={i < ITEMS.length - 1 && styles.rule}>
                <Tap onPress={() => setOpen(expanded ? null : item.name)} pressedOpacity={0.6} style={styles.row} accessibilityState={{ expanded }}>
                  <View style={styles.flex}>
                    <T variant="bodyStrong">{item.name}</T>
                    <T variant="caption" color={palette.ash}>
                      {item.what}
                    </T>
                  </View>
                  <T variant="label" color={palette.ash}>
                    {item.license}
                  </T>
                  <View style={{ transform: [{ rotate: expanded ? '90deg' : '0deg' }] }}>
                    <Icon name="chevron" size={18} color={palette.iron} />
                  </View>
                </Tap>
                {expanded ? (
                  <T variant="caption" color={palette.ash} style={styles.text} selectable>
                    {textFor(item)}
                  </T>
                ) : null}
              </View>
            );
          })}
        </View>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  flex: { flex: 1 },
  intro: { paddingHorizontal: space.lg, marginBottom: space.md },
  card: { marginHorizontal: space.lg, backgroundColor: palette.graphite, borderRadius: radius.md },
  row: { flexDirection: 'row', alignItems: 'center', gap: space.sm, paddingHorizontal: space.md, paddingVertical: space.md },
  rule: { borderBottomWidth: hairline, borderBottomColor: palette.rule },
  text: { paddingHorizontal: space.md, paddingBottom: space.md },
});
