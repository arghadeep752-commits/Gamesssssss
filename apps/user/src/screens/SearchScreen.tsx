import { useNavigation } from '@react-navigation/native';
import { useEffect, useState } from 'react';
import { ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { parseSearchQuery } from '@devdarshan/shared';
import { AppText, Chip, EmptyState, Icon, IconButton, SectionTitle, useTheme } from '@devdarshan/ui';
import { OfflineBanner } from '../components/OfflineBanner';
import { WallpaperGrid } from '../components/WallpaperGrid';
import { useCategories, useSearch } from '../data/queries';
import type { RootNavigation } from '../navigation/types';
import { useOpenPreview } from '../navigation/useOpenPreview';
import { useSettings } from '../state/settings';

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

export function SearchScreen() {
  const navigation = useNavigation<RootNavigation>();
  const insets = useSafeAreaInsets();
  const { colors, radii, spacing, type } = useTheme();
  const [text, setText] = useState('');
  const debounced = useDebounced(text.trim(), 350);
  const search = useSearch(debounced);
  const categories = useCategories();
  const recent = useSettings((s) => s.recentSearches);
  const addRecent = useSettings((s) => s.addRecentSearch);
  const clearRecent = useSettings((s) => s.clearRecentSearches);
  const openPreview = useOpenPreview();

  const results = search.data ?? [];
  const hasQuery = parseSearchQuery(debounced).term !== null;

  useEffect(() => {
    if (hasQuery && results.length > 0) addRecent(debounced);
  }, [addRecent, debounced, hasQuery, results.length]);

  const suggestions = (
    <View>
      {recent.length > 0 ? (
        <>
          <SectionTitle title="Recent" action="Clear" onAction={clearRecent} />
          <View style={[styles.chips, { paddingHorizontal: spacing.lg }]}>
            {recent.map((term) => (
              <Chip key={term} label={term} icon="clock" onPress={() => setText(term)} />
            ))}
          </View>
        </>
      ) : null}
      {(categories.data ?? []).length > 0 ? (
        <>
          <SectionTitle title="Browse by deity" />
          <View style={[styles.chips, { paddingHorizontal: spacing.lg }]}>
            {(categories.data ?? []).slice(0, 16).map((c) => (
              <Chip key={c.id} label={c.name} onPress={() => navigation.navigate('Category', { categoryId: c.id, title: c.name })} />
            ))}
          </View>
        </>
      ) : null}
    </View>
  );

  return (
    <View style={[styles.root, { backgroundColor: colors.background, paddingTop: insets.top }]}>
      <View style={[styles.bar, { paddingHorizontal: spacing.sm }]}>
        <IconButton name="arrowLeft" accessibilityLabel="Go back" onPress={() => navigation.goBack()} />
        <View style={[styles.inputWrap, { backgroundColor: colors.surface, borderColor: colors.border, borderRadius: radii.pill }]}>
          <Icon name="search" size={18} color={colors.textSubtle} />
          <TextInput
            value={text}
            onChangeText={setText}
            autoFocus
            placeholder="Search Ram, Krishna, Mahadev…"
            placeholderTextColor={colors.textSubtle}
            returnKeyType="search"
            autoCorrect={false}
            autoCapitalize="none"
            selectionColor={colors.primary}
            style={[styles.input, { color: colors.text, fontSize: type.body.fontSize }]}
            accessibilityLabel="Search wallpapers"
            testID="search-input"
          />
          {text ? <IconButton name="x" accessibilityLabel="Clear search" size={18} onPress={() => setText('')} /> : null}
        </View>
      </View>
      <OfflineBanner />
      {hasQuery ? (
        <WallpaperGrid
          data={results}
          loading={search.isPending || (search.isFetching && results.length === 0)}
          error={search.error}
          onRetry={() => void search.refetch()}
          onOpen={(w) => openPreview(results, w)}
          header={
            results.length > 0 ? (
              <AppText variant="caption" color="textMuted" style={{ paddingHorizontal: spacing.sm, paddingBottom: spacing.sm }}>
                {results.length === 1 ? '1 wallpaper' : `${results.length} wallpapers`}
              </AppText>
            ) : null
          }
          empty={<EmptyState icon="search" title="No matches" message="Try another name, such as Hanuman, Ganesh or Durga." />}
        />
      ) : (
        <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={{ paddingBottom: 32 }}>
          {suggestions}
        </ScrollView>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  root: {
    flex: 1,
  },
  bar: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  inputWrap: {
    flex: 1,
    height: 44,
    flexDirection: 'row',
    alignItems: 'center',
    paddingLeft: 14,
    borderWidth: StyleSheet.hairlineWidth * 2,
    marginRight: 8,
  },
  input: {
    flex: 1,
    height: 44,
    paddingHorizontal: 8,
  },
  chips: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
});
