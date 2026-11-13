import { Image } from 'expo-image';
import React, { memo } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';

import type { LookInfo } from '../../../modules/camero-engine';
import type { Preset } from '../../state/library';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Props = {
  looks: LookInfo[];
  presets?: Preset[];
  selected: string;
  selectedPreset?: string | null;
  onSelect: (id: string) => void;
  onPreset?: (preset: Preset) => void;
  onPresetLongPress?: (preset: Preset) => void;
  /** Rendered thumbnails of the photo being edited, by look id ('none' for the original). */
  previews?: Record<string, string>;
};

const NEUTRAL = ['#2B2B2B', '#757575', '#C9C9C9'];

/** Tone signature: how the look renders a shadow, midtone and highlight grey. */
export const Swatch = memo(function Swatch({ colors, active, accent }: { colors: string[]; active: boolean; accent: string }) {
  return (
    <View style={[styles.swatch, { borderColor: active ? accent : 'transparent' }]}>
      {colors.slice(0, 3).map((c, i) => (
        <View key={i} style={[styles.swatchPart, { backgroundColor: c }]} />
      ))}
    </View>
  );
});

function Item({ label, colors, active, accent, onPress, onLongPress, preview }: {
  label: string;
  colors: string[];
  active: boolean;
  accent: string;
  onPress: () => void;
  onLongPress?: () => void;
  preview?: string;
}) {
  return (
    <Tap haptic="selection" pressedOpacity={0.7} onPress={onPress} onLongPress={onLongPress} style={styles.item}>
      {preview ? (
        <View style={[styles.preview, { borderColor: active ? accent : 'transparent' }]}>
          <Image source={{ uri: preview }} style={styles.previewImage} contentFit="cover" transition={120} />
        </View>
      ) : (
        <Swatch colors={colors} active={active} accent={accent} />
      )}
      <T variant="caption" color={active ? palette.ink : palette.ash} align="center" numberOfLines={2} style={styles.name}>
        {label}
      </T>
    </Tap>
  );
}

/** Collection name set vertically between groups, like edge markings on film stock. */
function GroupLabel({ text }: { text: string }) {
  return (
    <View style={styles.groupBox}>
      <T variant="caption" color={palette.iron} numberOfLines={1} style={styles.groupText}>
        {text}
      </T>
    </View>
  );
}

export function LookStrip({ looks, presets = [], selected, selectedPreset, onSelect, onPreset, onPresetLongPress, previews }: Props) {
  const accent = useAccent();
  const groups: Record<string, LookInfo[]> = {};
  for (const l of looks) (groups[l.collection] ??= []).push(l);
  const order = ['Natural', 'Everyday', 'Cinematic', 'Photography', 'Film'];
  const swatchOf = (id: string) => looks.find((l) => l.id === id)?.swatch ?? NEUTRAL;
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.row}>
      <Item
        label="Original"
        colors={NEUTRAL}
        active={selected === 'none' && !selectedPreset}
        accent={accent}
        preview={previews?.none}
        onPress={() => onSelect('none')}
      />
      {presets.length ? (
        <>
          <GroupLabel text="Saved" />
          {presets.map((p) => (
            <Item
              key={p.id}
              label={p.name}
              colors={swatchOf(p.grade.look)}
              active={selectedPreset === p.id}
              accent={accent}
              preview={previews?.[p.grade.look]}
              onPress={() => onPreset?.(p)}
              onLongPress={() => onPresetLongPress?.(p)}
            />
          ))}
        </>
      ) : null}
      {order
        .filter((c) => groups[c]?.length)
        .map((c) => (
          <React.Fragment key={c}>
            <GroupLabel text={c} />
            {groups[c].map((l) => (
              <Item
                key={l.id}
                label={l.name}
                colors={l.swatch}
                active={!selectedPreset && selected === l.id}
                accent={accent}
                preview={previews?.[l.id]}
                onPress={() => onSelect(l.id)}
              />
            ))}
          </React.Fragment>
        ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  row: { paddingHorizontal: 12, alignItems: 'flex-start' },
  item: { width: 74, alignItems: 'center', paddingVertical: 6 },
  swatch: { flexDirection: 'row', width: 54, height: 14, borderRadius: 4, overflow: 'hidden', borderWidth: 1.5 },
  swatchPart: { flex: 1 },
  name: { marginTop: 6, width: 70 },
  preview: { width: 58, height: 58, borderRadius: 8, borderWidth: 1.5, padding: 2 },
  previewImage: { flex: 1, borderRadius: 5 },
  groupBox: { width: 22, height: 56, marginLeft: 8, alignItems: 'center', justifyContent: 'center' },
  groupText: { width: 80, textAlign: 'center', transform: [{ rotate: '-90deg' }] },
});
