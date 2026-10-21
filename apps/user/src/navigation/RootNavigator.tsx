import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { createNativeStackNavigator } from '@react-navigation/native-stack';
import { Icon, useTheme, type IconName } from '@devdarshan/ui';
import { CategoriesScreen } from '../screens/CategoriesScreen';
import { CategoryScreen } from '../screens/CategoryScreen';
import { FavoritesScreen } from '../screens/FavoritesScreen';
import { HomeScreen } from '../screens/HomeScreen';
import { LegalScreen } from '../screens/LegalScreen';
import { PreviewScreen } from '../screens/PreviewScreen';
import { ProfileScreen } from '../screens/ProfileScreen';
import { SearchScreen } from '../screens/SearchScreen';
import type { RootStackParamList, TabParamList } from './types';

const Stack = createNativeStackNavigator<RootStackParamList>();
const Tabs = createBottomTabNavigator<TabParamList>();

const TAB_ICONS: Record<keyof TabParamList, IconName> = {
  Home: 'home',
  Categories: 'grid',
  Favorites: 'heart',
  Profile: 'user',
};

const TAB_LABELS: Record<keyof TabParamList, string> = {
  Home: 'Home',
  Categories: 'Categories',
  Favorites: 'Liked',
  Profile: 'Profile',
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
        tabBarLabel: TAB_LABELS[route.name],
        tabBarButtonTestID: `tab-${route.name}`,
        tabBarIcon: ({ color, focused }) => (
          <Icon
            name={TAB_ICONS[route.name]}
            size={22}
            color={color}
            strokeWidth={focused ? 2.1 : 1.8}
            fill={focused && route.name === 'Favorites' ? color : 'none'}
          />
        ),
        sceneStyle: { backgroundColor: colors.background },
      })}
    >
      <Tabs.Screen name="Home" component={HomeScreen} />
      <Tabs.Screen name="Categories" component={CategoriesScreen} />
      <Tabs.Screen name="Favorites" component={FavoritesScreen} />
      <Tabs.Screen name="Profile" component={ProfileScreen} />
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
      <Stack.Screen name="Category" component={CategoryScreen} />
      <Stack.Screen name="Search" component={SearchScreen} options={{ animation: 'fade' }} />
      <Stack.Screen
        name="Preview"
        component={PreviewScreen}
        options={{ animation: 'fade', contentStyle: { backgroundColor: colors.previewBackground } }}
      />
      <Stack.Screen name="Legal" component={LegalScreen} />
    </Stack.Navigator>
  );
}
