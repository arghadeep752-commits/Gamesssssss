import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Icon, useTheme, type IconName } from '@devdarshan/ui';
import { ActivityScreen } from '../screens/ActivityScreen';
import { AdminsScreen } from '../screens/AdminsScreen';
import { CategoriesScreen } from '../screens/CategoriesScreen';
import { CategoryEditorScreen } from '../screens/CategoryEditorScreen';
import { DashboardScreen } from '../screens/DashboardScreen';
import { HomeContentScreen } from '../screens/HomeContentScreen';
import { SettingsScreen } from '../screens/SettingsScreen';
import { WallpaperEditorScreen } from '../screens/WallpaperEditorScreen';
import { WallpapersScreen } from '../screens/WallpapersScreen';
import type { AdminStackParamList, AdminTabParamList } from './types';

const Stack = createNativeStackNavigator<AdminStackParamList>();
const Tabs = createBottomTabNavigator<AdminTabParamList>();

const TAB_ICONS: Record<keyof AdminTabParamList, IconName> = {
  Dashboard: 'barChart',
  Wallpapers: 'image',
  Categories: 'grid',
  Settings: 'sliders',
};

function TabNavigator() {
  const { colors } = useTheme();
  return (
    <Tabs.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: colors.primary,
        tabBarInactiveTintColor: colors.textSubtle,
        tabBarStyle: { backgroundColor: colors.tabBar, borderTopColor: colors.tabBarBorder },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        tabBarButtonTestID: `tab-${route.name}`,
        tabBarIcon: ({ color, focused }) => (
          <Icon name={TAB_ICONS[route.name]} size={22} color={color} strokeWidth={focused ? 2.1 : 1.8} />
        ),
        sceneStyle: { backgroundColor: colors.background },
      })}
    >
      <Tabs.Screen name="Dashboard" component={DashboardScreen} />
      <Tabs.Screen name="Wallpapers" component={WallpapersScreen} />
      <Tabs.Screen name="Categories" component={CategoriesScreen} />
      <Tabs.Screen name="Settings" component={SettingsScreen} />
    </Tabs.Navigator>
  );
}

export function RootNavigator() {
  const { colors } = useTheme();
  return (
    <Stack.Navigator
      screenOptions={{
        headerShown: false,
        contentStyle: { backgroundColor: colors.background },
        animation: 'slide_from_right',
        animationDuration: 220,
      }}
    >
      <Stack.Screen name="Tabs" component={TabNavigator} />
      <Stack.Screen name="WallpaperEditor" component={WallpaperEditorScreen} />
      <Stack.Screen name="CategoryEditor" component={CategoryEditorScreen} />
      <Stack.Screen name="HomeContent" component={HomeContentScreen} />
      <Stack.Screen name="Admins" component={AdminsScreen} />
      <Stack.Screen name="Activity" component={ActivityScreen} />
    </Stack.Navigator>
  );
}
