import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

import type { Filter } from '../lib/media';

export type RootStackParamList = {
  Permissions: undefined;
  Camera: undefined;
  Gallery: { filter?: Filter } | undefined;
  Viewer: { id?: string; uri?: string; filter?: Filter };
  PhotoEditor: { id: string; uri: string };
  VideoEditor: { id: string; uri: string };
  Looks: undefined;
  Settings: undefined;
  CameraReport: undefined;
  Licenses: undefined;
  Privacy: undefined;
};

export type Nav = NativeStackNavigationProp<RootStackParamList>;
