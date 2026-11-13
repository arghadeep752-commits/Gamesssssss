import React, { useEffect, useRef, useState } from 'react';
import { StyleSheet, View, type LayoutChangeEvent } from 'react-native';
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated';

import type { CameraMode } from '../../../modules/camero-engine';
import type { ModeInfo } from '../../lib/camera';
import { useAccent } from '../../theme/accent';
import { palette } from '../../theme/tokens';
import { T } from '../../ui/T';
import { Tap } from '../../ui/Tap';

type Props = { modes: ModeInfo[]; mode: CameraMode; onChange: (m: CameraMode) => void; disabled?: boolean };

/** Horizontal list of capture modes; the selected one slides to the centre. */
export function ModeStrip({ modes, mode, onChange, disabled }: Props) {
  const accent = useAccent();
  const [width, setWidth] = useState(0);
  const layouts = useRef<Record<string, { x: number; w: number }>>({});
  const [, force] = useState(0);
  const offset = useSharedValue(0);

  const center = () => {
    const l = layouts.current[mode];
    if (!l || !width) return;
    offset.value = withTiming(width / 2 - (l.x + l.w / 2), { duration: 260, easing: Easing.out(Easing.cubic) });
  };

  useEffect(center, [mode, width, modes.length]);

  const style = useAnimatedStyle(() => ({ transform: [{ translateX: offset.value }] }));

  return (
    <View style={styles.root} onLayout={(e: LayoutChangeEvent) => setWidth(e.nativeEvent.layout.width)}>
      <Animated.View style={[styles.row, style]}>
        {modes.map((m) => {
          const selected = m.mode === mode;
          return (
            <Tap
              key={m.mode}
              disabled={disabled}
              haptic="selection"
              pressedOpacity={0.7}
              onPress={() => onChange(m.mode)}
              onLayout={(e: LayoutChangeEvent) => {
                const { x, width: w } = e.nativeEvent.layout;
                const prev = layouts.current[m.mode];
                if (!prev || prev.x !== x || prev.w !== w) {
                  layouts.current[m.mode] = { x, w };
                  force((n) => n + 1);
                  if (m.mode === mode) center();
                }
              }}
              style={styles.item}
            >
              <T variant="mode" color={selected ? palette.ink : palette.ash}>
                {m.label}
              </T>
              <View style={[styles.mark, { backgroundColor: selected ? accent : 'transparent' }]} />
            </Tap>
          );
        })}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: { height: 40, overflow: 'hidden', justifyContent: 'center' },
  row: { flexDirection: 'row', position: 'absolute', left: 0, alignItems: 'center' },
  item: { paddingHorizontal: 11, paddingVertical: 6, alignItems: 'center' },
  mark: { marginTop: 5, width: 14, height: 2, borderRadius: 1 },
});
