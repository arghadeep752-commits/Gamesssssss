import React, { useEffect } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, {
  SensorType,
  useAnimatedSensor,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Line, Path, Rect } from 'react-native-svg';

import type { GridType } from '../../state/settings';
import { useAccent } from '../../theme/accent';
import { palette, type as typeScale } from '../../theme/tokens';
import { Icon } from '../../ui/Icon';
import { T } from '../../ui/T';

export function GridOverlay({ type, width, height }: { type: GridType; width: number; height: number }) {
  if (type === 'off' || !width || !height) return null;
  const lines: React.ReactNode[] = [];
  const stroke = { stroke: 'rgba(255,255,255,0.32)', strokeWidth: 0.8 };
  if (type === 'thirds' || type === 'golden') {
    const f = type === 'golden' ? 0.382 : 1 / 3;
    [f, 1 - f].forEach((p, i) => {
      lines.push(<Line key={`v${i}`} x1={width * p} x2={width * p} y1={0} y2={height} {...stroke} />);
      lines.push(<Line key={`h${i}`} y1={height * p} y2={height * p} x1={0} x2={width} {...stroke} />);
    });
  } else if (type === 'square') {
    const s = Math.min(width, height);
    lines.push(<Rect key="sq" x={(width - s) / 2} y={(height - s) / 2} width={s} height={s} fill="none" {...stroke} />);
    lines.push(<Line key="c1" x1={width / 2 - 8} x2={width / 2 + 8} y1={height / 2} y2={height / 2} {...stroke} />);
    lines.push(<Line key="c2" y1={height / 2 - 8} y2={height / 2 + 8} x1={width / 2} x2={width / 2} {...stroke} />);
  }
  return (
    <Svg pointerEvents="none" width={width} height={height} style={StyleSheet.absoluteFill}>
      {lines}
    </Svg>
  );
}

/** Horizon line driven by the gravity sensor on the UI thread. Turns accent when level. */
export function LevelIndicator() {
  const accent = useAccent();
  const sensor = useAnimatedSensor(SensorType.GRAVITY, { interval: 33 });
  const line = useAnimatedStyle(() => {
    const { x, y, z } = sensor.sensor.value;
    const flat = Math.abs(z) > 8.6;
    const roll = Math.atan2(x, y) * (180 / Math.PI);
    let angle = roll;
    if (angle > 45) angle -= 90;
    if (angle < -45) angle += 90;
    if (angle > 45) angle -= 90;
    const level = Math.abs(angle) < 1;
    return {
      opacity: flat ? 0 : 1,
      transform: [{ rotate: `${level ? 0 : angle}deg` }],
      backgroundColor: level ? accent : 'rgba(255,255,255,0.75)',
    };
  });
  return (
    <View pointerEvents="none" style={styles.levelWrap}>
      <Animated.View style={[styles.levelLine, line]} />
    </View>
  );
}

type FocusProps = {
  x: number;
  y: number;
  visible: number;
  locked: boolean;
  ev?: string;
};

/** Focus box built from the same corner brackets as the app icon. */
export function FocusReticle({ x, y, visible, locked, ev }: FocusProps) {
  const accent = useAccent();
  const scale = useSharedValue(1.25);
  const opacity = useSharedValue(0);
  useEffect(() => {
    if (!visible) return;
    scale.value = 1.25;
    scale.value = withTiming(1, { duration: 180 });
    opacity.value = withSequence(withTiming(1, { duration: 80 }), withDelay(locked ? 600000 : 2400, withTiming(0.35, { duration: 400 })));
  }, [visible, locked, scale, opacity]);
  const style = useAnimatedStyle(() => ({ opacity: opacity.value, transform: [{ scale: scale.value }] }));
  if (!visible) return null;
  const S = 76;
  const a = 14;
  const d = `M0 ${a}V0h${a}M${S - a} 0h${a}v${a}M${S} ${S - a}v${a}h-${a}M${a} ${S}H0v-${a}`;
  return (
    <Animated.View pointerEvents="none" style={[styles.focus, { left: x - S / 2, top: y - S / 2 }, style]}>
      <Svg width={S} height={S}>
        <Path d={d} stroke={accent} strokeWidth={1.6} fill="none" />
      </Svg>
      <View style={styles.evSide}>
        <Icon name="sun" size={16} color={accent} />
        {ev ? (
          <T variant="readout" color={accent} style={styles.evText}>
            {ev}
          </T>
        ) : null}
      </View>
      {locked ? (
        <View style={[styles.lockTag, { borderColor: accent }]}>
          <T variant="caption" color={accent}>
            AE/AF lock
          </T>
        </View>
      ) : null}
    </Animated.View>
  );
}

export function Countdown({ value }: { value: number }) {
  const scale = useSharedValue(1);
  useEffect(() => {
    scale.value = 1.15;
    scale.value = withTiming(1, { duration: 300 });
  }, [value, scale]);
  const style = useAnimatedStyle(() => ({ transform: [{ scale: scale.value }] }));
  if (value <= 0) return null;
  return (
    <View pointerEvents="none" style={styles.countdown}>
      <Animated.Text allowFontScaling={false} style={[typeScale.countdown, styles.countText, style]}>
        {value}
      </Animated.Text>
    </View>
  );
}

/** Brief dip to black when a photo is taken. */
export function CaptureFlash({ trigger }: { trigger: number }) {
  const o = useSharedValue(0);
  useEffect(() => {
    if (!trigger) return;
    o.value = withSequence(withTiming(0.85, { duration: 40 }), withTiming(0, { duration: 220 }));
  }, [trigger, o]);
  const style = useAnimatedStyle(() => ({ opacity: o.value }));
  return <Animated.View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.flash, style]} />;
}

const styles = StyleSheet.create({
  levelWrap: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
  levelLine: { width: 120, height: 1.5, borderRadius: 1 },
  focus: { position: 'absolute', width: 76, height: 76 },
  evSide: { position: 'absolute', left: 82, top: 0, height: 76, justifyContent: 'center', alignItems: 'center' },
  evText: { marginTop: 4 },
  lockTag: {
    position: 'absolute',
    top: -30,
    alignSelf: 'center',
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 4,
    borderWidth: 1,
    backgroundColor: palette.scrimStrong,
  },
  countdown: { ...StyleSheet.absoluteFillObject, alignItems: 'center', justifyContent: 'center' },
  countText: { color: palette.ink, opacity: 0.92 },
  flash: { backgroundColor: '#000' },
});
