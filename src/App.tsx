import { StatusBar } from 'expo-status-bar';
import React from 'react';
import { StyleSheet, View } from 'react-native';

import { CameraView } from '../modules/camero-engine';

export default function App() {
  return (
    <View style={styles.root}>
      <CameraView
        style={styles.root}
        active
        mode="photo"
        aspect="4:3"
        photo="{}"
        video="{}"
        grade="{}"
        overlay="{}"
        flash="off"
        torch={false}
        manual="{}"
        timelapseIntervalMs={1000}
      />
      <StatusBar style="light" />
    </View>
  );
}

const styles = StyleSheet.create({ root: { flex: 1, backgroundColor: '#000' } });
