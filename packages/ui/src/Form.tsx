import { forwardRef, type ReactNode } from 'react';
import { StyleSheet, Switch, TextInput, View, type StyleProp, type TextInputProps, type ViewStyle } from 'react-native';
import { AppText } from './AppText';
import { Icon, type IconName } from './Icon';
import { useTheme } from './theme';
import { Touchable } from './Touchable';

export interface TextFieldProps extends TextInputProps {
  label?: string;
  helper?: string;
  error?: string | null;
  containerStyle?: StyleProp<ViewStyle>;
  leftIcon?: IconName;
  showCount?: boolean;
}

export const TextField = forwardRef<TextInput, TextFieldProps>(function TextField(
  { label, helper, error, containerStyle, leftIcon, showCount, multiline, maxLength, value, style, ...rest },
  ref,
) {
  const { colors, radii, spacing, type } = useTheme();
  return (
    <View style={[{ marginBottom: spacing.lg }, containerStyle]}>
      {label ? (
        <AppText variant="label" color="textMuted" style={{ marginBottom: spacing.xs }}>
          {label}
        </AppText>
      ) : null}
      <View
        style={[
          styles.inputWrap,
          {
            backgroundColor: colors.surface,
            borderColor: error ? colors.danger : colors.border,
            borderRadius: radii.md,
            minHeight: multiline ? 96 : 46,
            alignItems: multiline ? 'flex-start' : 'center',
          },
        ]}
      >
        {leftIcon ? (
          <View style={{ paddingLeft: spacing.md, paddingTop: multiline ? 12 : 0 }}>
            <Icon name={leftIcon} size={18} color={colors.textSubtle} />
          </View>
        ) : null}
        <TextInput
          ref={ref}
          value={value}
          multiline={multiline}
          maxLength={maxLength}
          placeholderTextColor={colors.textSubtle}
          selectionColor={colors.primary}
          cursorColor={colors.primary}
          textAlignVertical={multiline ? 'top' : 'center'}
          style={[
            styles.input,
            {
              color: colors.text,
              fontSize: type.body.fontSize,
              paddingHorizontal: spacing.md,
              paddingVertical: multiline ? spacing.md : 0,
            },
            style,
          ]}
          {...rest}
        />
      </View>
      {error || helper || (showCount && maxLength) ? (
        <View style={styles.footer}>
          <AppText variant="caption" color={error ? 'danger' : 'textSubtle'} style={{ flex: 1 }}>
            {error ?? helper ?? ''}
          </AppText>
          {showCount && maxLength ? (
            <AppText variant="caption" color="textSubtle">
              {(value ?? '').length}/{maxLength}
            </AppText>
          ) : null}
        </View>
      ) : null}
    </View>
  );
});

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
  icon?: IconName;
}

export function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
  style,
}: {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  style?: StyleProp<ViewStyle>;
}) {
  const { colors, radii } = useTheme();
  return (
    <View style={[styles.segmented, { backgroundColor: colors.surfaceAlt, borderRadius: radii.md }, style]} accessibilityRole="tablist">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Touchable
            key={option.value}
            onPress={() => onChange(option.value)}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            style={[
              styles.segment,
              {
                backgroundColor: selected ? colors.surface : 'transparent',
                borderRadius: radii.sm,
                elevation: selected ? 1 : 0,
              },
            ]}
          >
            {option.icon ? <Icon name={option.icon} size={16} color={selected ? colors.primary : colors.textMuted} /> : null}
            <AppText variant="label" color={selected ? 'text' : 'textMuted'} weight={selected ? '600' : '500'}>
              {option.label}
            </AppText>
          </Touchable>
        );
      })}
    </View>
  );
}

export function SwitchRow({
  label,
  description,
  value,
  onValueChange,
  disabled,
}: {
  label: string;
  description?: string;
  value: boolean;
  onValueChange: (value: boolean) => void;
  disabled?: boolean;
}) {
  const { colors, spacing } = useTheme();
  return (
    <View style={[styles.switchRow, { paddingVertical: spacing.sm }]}>
      <View style={{ flex: 1, paddingRight: spacing.md }}>
        <AppText variant="bodyStrong">{label}</AppText>
        {description ? (
          <AppText variant="caption" color="textMuted" style={{ marginTop: 2 }}>
            {description}
          </AppText>
        ) : null}
      </View>
      <Switch
        value={value}
        onValueChange={onValueChange}
        disabled={disabled}
        trackColor={{ false: colors.borderStrong, true: colors.primarySoft }}
        thumbColor={value ? colors.primary : colors.surface}
        accessibilityLabel={label}
      />
    </View>
  );
}

export interface ListRowProps {
  title: string;
  subtitle?: string;
  icon?: IconName;
  iconColor?: string;
  value?: string;
  onPress?: () => void;
  right?: ReactNode;
  destructive?: boolean;
  showChevron?: boolean;
  testID?: string;
}

export function ListRow({
  title,
  subtitle,
  icon,
  iconColor,
  value,
  onPress,
  right,
  destructive,
  showChevron = !!onPress,
  testID,
}: ListRowProps) {
  const { colors, spacing } = useTheme();
  const tint = destructive ? colors.danger : iconColor ?? colors.textMuted;
  return (
    <Touchable
      testID={testID}
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : undefined}
      style={[styles.listRow, { paddingHorizontal: spacing.lg }]}
    >
      {icon ? (
        <View style={{ width: 28 }}>
          <Icon name={icon} size={20} color={tint} />
        </View>
      ) : null}
      <View style={{ flex: 1 }}>
        <AppText variant="body" color={destructive ? 'danger' : 'text'}>
          {title}
        </AppText>
        {subtitle ? (
          <AppText variant="caption" color="textMuted" style={{ marginTop: 1 }}>
            {subtitle}
          </AppText>
        ) : null}
      </View>
      {value ? (
        <AppText variant="label" color="textMuted" style={{ marginLeft: spacing.sm }}>
          {value}
        </AppText>
      ) : null}
      {right}
      {showChevron ? <Icon name="chevronRight" size={18} color={colors.textSubtle} /> : null}
    </Touchable>
  );
}

export function SectionTitle({ title, action, onAction }: { title: string; action?: string; onAction?: () => void }) {
  const { spacing } = useTheme();
  return (
    <View style={[styles.sectionTitle, { paddingHorizontal: spacing.lg, marginTop: spacing.xl, marginBottom: spacing.sm }]}>
      <AppText variant="subheading" style={{ flex: 1 }}>
        {title}
      </AppText>
      {action && onAction ? (
        <Touchable onPress={onAction} accessibilityRole="button" style={styles.sectionAction}>
          <AppText variant="label" color="primary" weight="600">
            {action}
          </AppText>
        </Touchable>
      ) : null}
    </View>
  );
}

export function ProgressBar({ progress, indeterminate = false }: { progress: number; indeterminate?: boolean }) {
  const { colors, radii } = useTheme();
  const pct = indeterminate ? 0.35 : Math.min(1, Math.max(0, progress));
  return (
    <View
      accessibilityRole="progressbar"
      accessibilityValue={indeterminate ? undefined : { min: 0, max: 100, now: Math.round(pct * 100) }}
      style={[styles.track, { backgroundColor: colors.surfaceAlt, borderRadius: radii.pill }]}
    >
      <View style={[styles.fill, { width: `${pct * 100}%`, backgroundColor: colors.primary, borderRadius: radii.pill }]} />
    </View>
  );
}

const styles = StyleSheet.create({
  inputWrap: {
    flexDirection: 'row',
    borderWidth: StyleSheet.hairlineWidth * 2,
  },
  input: {
    flex: 1,
    minHeight: 44,
  },
  footer: {
    flexDirection: 'row',
    marginTop: 4,
    gap: 8,
  },
  segmented: {
    flexDirection: 'row',
    padding: 3,
    gap: 3,
  },
  segment: {
    flex: 1,
    height: 36,
    flexDirection: 'row',
    gap: 6,
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  switchRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  listRow: {
    minHeight: 52,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 10,
  },
  sectionTitle: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  sectionAction: {
    paddingHorizontal: 6,
    paddingVertical: 4,
    borderRadius: 6,
    overflow: 'hidden',
  },
  track: {
    height: 6,
    width: '100%',
    overflow: 'hidden',
  },
  fill: {
    height: 6,
  },
});
