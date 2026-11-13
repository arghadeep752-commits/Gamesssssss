import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { useAccent } from '../../theme/accent';
import { palette, radius, space } from '../../theme/tokens';
import { Icon, type IconName } from '../../ui/Icon';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type HeaderProps = {
  onClose: () => void;
  onUndo: () => void;
  onRedo: () => void;
  canUndo: boolean;
  canRedo: boolean;
  onSave: () => void;
  saveLabel: string;
  saveDisabled?: boolean;
};

export function EditorHeader({ onClose, onUndo, onRedo, canUndo, canRedo, onSave, saveLabel, saveDisabled }: HeaderProps) {
  const insets = useSafeAreaInsets();
  const accent = useAccent();
  return (
    <View style={[styles.header, { paddingTop: insets.top }]}>
      <Tap onPress={onClose} haptic="selection" style={styles.icon} accessibilityLabel="Close editor">
        <Icon name="close" />
      </Tap>
      <View style={styles.history}>
        <Tap onPress={onUndo} disabled={!canUndo} haptic="selection" style={styles.icon} accessibilityLabel="Undo">
          <Icon name="undo" />
        </Tap>
        <Tap onPress={onRedo} disabled={!canRedo} haptic="selection" style={styles.icon} accessibilityLabel="Redo">
          <Icon name="redo" />
        </Tap>
      </View>
      <Tap onPress={onSave} disabled={saveDisabled} haptic="light" style={[styles.save, { backgroundColor: accent }]}>
        <T variant="label" color={palette.black}>
          {saveLabel}
        </T>
      </Tap>
    </View>
  );
}

export type ToolTab<K extends string> = { key: K; label: string; icon: IconName; marked?: boolean };

export function ToolTabs<K extends string>({ tabs, value, onChange }: { tabs: ToolTab<K>[]; value: K; onChange: (k: K) => void }) {
  const insets = useSafeAreaInsets();
  const accent = useAccent();
  return (
    <View style={[styles.tabs, { paddingBottom: Math.max(insets.bottom, space.sm) }]}>
      {tabs.map((t) => {
        const selected = t.key === value;
        return (
          <Tap key={t.key} haptic="selection" onPress={() => onChange(t.key)} style={styles.tab} accessibilityState={{ selected }}>
            <Icon name={t.icon} size={22} color={selected ? palette.ink : palette.iron} />
            <View style={styles.tabLabelRow}>
              <T variant="caption" color={selected ? palette.ink : palette.ash}>
                {t.label}
              </T>
              {t.marked ? <View style={[styles.mark, { backgroundColor: accent }]} /> : null}
            </View>
          </Tap>
        );
      })}
    </View>
  );
}

/** Press and hold to see the picture without the look and adjustments. */
export function CompareButton({ onChange, active }: { onChange: (v: boolean) => void; active: boolean }) {
  return (
    <Tap
      onPressIn={() => onChange(true)}
      onPressOut={() => onChange(false)}
      pressedOpacity={1}
      haptic="selection"
      style={[styles.compare, active && styles.compareActive]}
      accessibilityLabel="Hold to compare with the original"
    >
      <Icon name="compare" size={20} color={active ? palette.black : palette.ink} />
    </Tap>
  );
}

export function BeforeTag() {
  return (
    <View style={styles.before} pointerEvents="none">
      <T variant="caption">Before</T>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.sm, backgroundColor: palette.black },
  icon: { width: 44, height: 52, alignItems: 'center', justifyContent: 'center' },
  history: { flex: 1, flexDirection: 'row', justifyContent: 'center' },
  save: { height: 34, paddingHorizontal: 16, borderRadius: radius.md, alignItems: 'center', justifyContent: 'center', marginRight: space.xs },
  tabs: { flexDirection: 'row', justifyContent: 'space-around', paddingTop: space.sm, backgroundColor: palette.black },
  tab: { minWidth: 56, alignItems: 'center', paddingVertical: 2 },
  tabLabelRow: { flexDirection: 'row', alignItems: 'center', marginTop: 3, gap: 4 },
  mark: { width: 4, height: 4, borderRadius: 2 },
  compare: {
    position: 'absolute',
    right: space.md,
    bottom: space.md,
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: palette.scrimStrong,
    alignItems: 'center',
    justifyContent: 'center',
  },
  compareActive: { backgroundColor: palette.ink },
  before: {
    position: 'absolute',
    left: space.md,
    top: space.md,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 6,
    backgroundColor: palette.scrimStrong,
  },
});
