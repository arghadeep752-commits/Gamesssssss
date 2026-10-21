import { View } from 'react-native';
import { categoryLabel, type Category } from '@devdarshan/shared';
import { AppText, Chip, useTheme } from '@devdarshan/ui';

/** Multi-select (or single-select with max=1) of the categories managed in the admin app. */
export function CategoryPicker({
  categories,
  value,
  onChange,
  max = 5,
  label,
  error,
}: {
  categories: Category[];
  value: string[];
  onChange: (ids: string[]) => void;
  max?: number;
  label?: string;
  error?: string;
}) {
  const { spacing } = useTheme();
  const toggle = (id: string) => {
    if (value.includes(id)) onChange(value.filter((v) => v !== id));
    else if (max === 1) onChange([id]);
    else if (value.length < max) onChange([...value, id]);
  };
  return (
    <View style={{ marginBottom: spacing.lg }}>
      {label ? (
        <AppText variant="label" color="textMuted" style={{ marginBottom: spacing.xs }}>
          {label}
          {max > 1 ? ` (${value.length}/${max})` : ''}
        </AppText>
      ) : null}
      <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: spacing.sm }}>
        {categories.map((c) => (
          <Chip
            key={c.id}
            label={`${categoryLabel(c)}${c.isActive ? '' : ' (hidden)'}`}
            selected={value.includes(c.id)}
            onPress={() => toggle(c.id)}
          />
        ))}
      </View>
      {categories.length === 0 ? (
        <AppText variant="caption" color="textMuted">
          No categories yet. Create them in the Categories tab first.
        </AppText>
      ) : null}
      {error ? (
        <AppText variant="caption" color="danger" style={{ marginTop: 4 }}>
          {error}
        </AppText>
      ) : null}
    </View>
  );
}
