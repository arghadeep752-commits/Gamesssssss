import React from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { palette, space } from '../../theme/tokens';
import { Header } from '../../ui/Header';
import { T } from '../../ui/T';

const SECTIONS: { title: string; body: string[] }[] = [
  {
    title: 'Everything stays on your phone',
    body: [
      'Camero Plus has no account, no ads and no analytics. It doesn’t upload your photos, videos or settings, and it doesn’t contact a server to work.',
      'Photos and videos are processed on the phone’s own processor and graphics chip.',
    ],
  },
  {
    title: 'Permissions',
    body: [
      'Camera: to take photos and videos. Camero Plus can’t work without it.',
      'Microphone: to record sound with videos. Without it, videos are saved silently.',
      'Photos and videos: to show what you’ve taken in the library and to edit it. On Android 10 and newer the camera still saves your shots without it; on Android 8 and 9 it’s also needed to save them.',
      'Location: never requested, and no location is written into your photos.',
    ],
  },
  {
    title: 'Where your files go',
    body: [
      'New photos and videos are saved to DCIM/Camero Plus, or to Pictures and Movies if you choose that in Settings. Other gallery apps can see them there.',
      'Edits are always saved as new files. The photo or video you started from is never changed.',
      'When a look is on, an untouched copy can also be kept in DCIM/Camero Plus/Originals. You can turn this off in Settings.',
    ],
  },
  {
    title: 'What the app keeps',
    body: [
      'Your settings, favourites, presets and notes about which files you edited are stored inside the app on this phone. Uninstalling Camero Plus or clearing its storage removes them. Your photos and videos stay.',
    ],
  },
  {
    title: 'Sharing',
    body: ['Files leave Camero Plus only when you tap Share and pick an app. That app’s own privacy terms apply from then on.'],
  },
];

export function PrivacyScreen() {
  const insets = useSafeAreaInsets();
  return (
    <View style={styles.root}>
      <Header title="Privacy" large />
      <ScrollView contentContainerStyle={{ paddingBottom: insets.bottom + space.xxl }}>
        {SECTIONS.map((s) => (
          <View key={s.title} style={styles.section}>
            <T variant="heading">{s.title}</T>
            {s.body.map((p) => (
              <T key={p} variant="body" color={palette.ash} style={styles.para}>
                {p}
              </T>
            ))}
          </View>
        ))}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: palette.black },
  section: { paddingHorizontal: space.lg, marginTop: space.lg, maxWidth: 640 },
  para: { marginTop: space.sm },
});
