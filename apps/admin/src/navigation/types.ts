import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

export type AdminTabParamList = {
  Dashboard: undefined;
  Wallpapers: undefined;
  Categories: undefined;
  Settings: undefined;
};

export type AdminStackParamList = {
  Tabs: NavigatorScreenParams<AdminTabParamList> | undefined;
  WallpaperEditor: { wallpaperId?: string };
  CategoryEditor: { categoryId?: string };
  HomeContent: undefined;
  Admins: undefined;
  Activity: undefined;
};

export type AdminNavigation = NativeStackNavigationProp<AdminStackParamList>;
