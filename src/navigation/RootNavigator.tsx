import { createNativeStackNavigator } from '@react-navigation/native-stack';
import React from 'react';

import { CameraScreen } from '../screens/camera/CameraScreen';
import { PhotoEditorScreen } from '../screens/editor/PhotoEditorScreen';
import { VideoEditorScreen } from '../screens/editor/VideoEditorScreen';
import { GalleryScreen } from '../screens/library/GalleryScreen';
import { ViewerScreen } from '../screens/library/ViewerScreen';
import { PermissionsScreen } from '../screens/PermissionsScreen';
import { CameraReportScreen } from '../screens/settings/CameraReportScreen';
import { LicensesScreen } from '../screens/settings/LicensesScreen';
import { LooksScreen } from '../screens/settings/LooksScreen';
import { PrivacyScreen } from '../screens/settings/PrivacyScreen';
import { SettingsScreen } from '../screens/settings/SettingsScreen';
import { palette } from '../theme/tokens';
import type { RootStackParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();

export function RootNavigator({ initialRouteName }: { initialRouteName: keyof RootStackParamList }) {
  return (
    <Stack.Navigator
      initialRouteName={initialRouteName}
      screenOptions={{
        headerShown: false,
        animation: 'slide_from_right',
        contentStyle: { backgroundColor: palette.black },
        orientation: 'portrait',
      }}
    >
      <Stack.Screen name="Permissions" component={PermissionsScreen} options={{ animation: 'fade' }} />
      <Stack.Screen name="Camera" component={CameraScreen} options={{ animation: 'fade' }} />
      <Stack.Screen name="Gallery" component={GalleryScreen} />
      <Stack.Screen name="Viewer" component={ViewerScreen} options={{ animation: 'fade' }} />
      <Stack.Screen name="PhotoEditor" component={PhotoEditorScreen} options={{ animation: 'fade', gestureEnabled: false }} />
      <Stack.Screen name="VideoEditor" component={VideoEditorScreen} options={{ animation: 'fade', gestureEnabled: false }} />
      <Stack.Screen name="Looks" component={LooksScreen} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="CameraReport" component={CameraReportScreen} />
      <Stack.Screen name="Licenses" component={LicensesScreen} />
      <Stack.Screen name="Privacy" component={PrivacyScreen} />
    </Stack.Navigator>
  );
}
