import type { NavigatorScreenParams } from '@react-navigation/native';
import type { NativeStackNavigationProp } from '@react-navigation/native-stack';

export type TabParamList = {
  Home: undefined;
  Categories: undefined;
  Favorites: undefined;
  Profile: undefined;
};

export type RootStackParamList = {
  Tabs: NavigatorScreenParams<TabParamList> | undefined;
  Preview: { wallpaperId: string; sessionKey?: string };
  Category: { categoryId: string; title?: string };
  Search: undefined;
  Legal: { document: 'privacy' | 'terms' };
};

export type RootNavigation = NativeStackNavigationProp<RootStackParamList>;
