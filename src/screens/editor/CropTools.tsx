import React from 'react';
import { StyleSheet, View } from 'react-native';

import { palette, space } from '../../theme/tokens';
import { Icon, type IconName } from '../../ui/Icon';
import { Segmented } from '../../ui/Segmented';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

export type AspectKey = 'free' | 'original' | 'square' | '4:5' | '3:4' | '9:16' | '16:9' | '4:3' | '3:2';

const ASPECTS: { value: AspectKey; label: string; ratio?: number }[] = [
  { value: 'free', label: 'Free' },
  { value: 'original', label: 'Original' },
  { value: 'square', label: 'Square', ratio: 1 },
  { value: '4:5', label: '4:5', ratio: 4 / 5 },
  { value: '3:4', label: '3:4', ratio: 3 / 4 },
  { value: '9:16', label: '9:16', ratio: 9 / 16 },
  { value: '16:9', label: '16:9', ratio: 16 / 9 },
  { value: '4:3', label: '4:3', ratio: 4 / 3 },
  { value: '3:2', label: '3:2', ratio: 3 / 2 },
];

/**
 * Locked crop ratio in normalized frame units (the crop rectangle lives in a unit square
 * stretched over the picture), or null for a free crop.
 */
export function ratioFor(key: AspectKey, frameAspect: number, _sourceAspect: number): number | null {
  if (key === 'free') return null;
  if (key === 'original') return 1;
  const r = ASPECTS.find((a) => a.value === key)?.ratio;
  return r ? r / frameAspect : null;
}

function ToolButton({ icon, label, onPress, disabled }: { icon: IconName; label: string; onPress: () => void; disabled?: boolean }) {
  return (
    <Tap haptic="selection" onPress={onPress} disabled={disabled} style={styles.tool}>
      <Icon name={icon} size={22} />
      <T variant="caption" color={palette.ash} style={styles.toolLabel}>
        {label}
      </T>
    </Tap>
  );
}

type Props = {
  aspect: AspectKey;
  onAspect: (k: AspectKey) => void;
  onRotate: () => void;
  onMirror: () => void;
  onReset: () => void;
  resetDisabled: boolean;
  outputLabel?: string;
};

export function CropTools({ aspect, onAspect, onRotate, onMirror, onReset, resetDisabled, outputLabel }: Props) {
  return (
    <View style={styles.root}>
      <View style={styles.aspects}>
        <Segmented scroll options={ASPECTS.map(({ value, label }) => ({ value, label }))} value={aspect} onChange={onAspect} />
      </View>
      <View style={styles.row}>
        <ToolButton icon="rotate" label="Rotate" onPress={onRotate} />
        <ToolButton icon="flipH" label="Mirror" onPress={onMirror} />
        <ToolButton icon="undo" label="Reset" onPress={onReset} disabled={resetDisabled} />
        <View style={styles.flex} />
        {outputLabel ? (
          <View style={styles.output}>
            <T variant="readout">{outputLabel}</T>
            <T variant="caption" color={palette.iron}>
              Saved size
            </T>
          </View>
        ) : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { gap: space.md },
  aspects: { paddingLeft: space.md },
  row: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.md, gap: space.xs },
  tool: { minWidth: 64, alignItems: 'center', paddingVertical: 4 },
  toolLabel: { marginTop: 3 },
  flex: { flex: 1 },
  output: { alignItems: 'flex-end', paddingRight: space.xs },
});
