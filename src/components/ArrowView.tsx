import { memo, useEffect } from 'react';
import { StyleSheet } from 'react-native';
import Animated, {
  cancelAnimation,
  Easing,
  useAnimatedStyle,
  useSharedValue,
  withDelay,
  withRepeat,
  withSequence,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Path } from 'react-native-svg';
import { scheduleOnRN } from 'react-native-worklets';
import { COLORS } from '../config/theme';
import type { ArrowGeometry } from '../utils/arrowPath';

/**
 * One arrow. Visual state machine: IDLE -> MOVING -> (unmounted = REMOVED).
 * All motion runs on the UI thread through Reanimated shared values; the JS
 * thread only hears back once, when the exit glide has finished.
 */
export type ArrowPhase = 'idle' | 'moving';
export type ArrowTone = 'normal' | 'error' | 'hint' | 'blocker' | 'focus';

const TONE_COLOR: Record<ArrowTone, string> = {
  normal: COLORS.arrow,
  error: COLORS.error,
  hint: COLORS.hint,
  blocker: COLORS.blocker,
  focus: COLORS.hint,
};

// Material "accelerate" curve: exiting elements speed up as they leave.
const EXIT_EASING = Easing.bezier(0.4, 0, 1, 1);

interface Props {
  id: number;
  geom: ArrowGeometry;
  phase: ArrowPhase;
  exitMs: number;
  tone: ArrowTone;
  /** Increments to trigger a blocked "bump". */
  shakeSeq: number;
  pulse: boolean;
  reducedEffects: boolean;
  cell: number;
  onExited: (id: number) => void;
}

export const ArrowView = memo(function ArrowView({
  id,
  geom,
  phase,
  exitMs,
  tone,
  shakeSeq,
  pulse,
  reducedEffects,
  cell,
  onExited,
}: Props) {
  const travel = useSharedValue(0);
  const shake = useSharedValue(0);
  const fade = useSharedValue(1);
  const glow = useSharedValue(1);
  const { dx, dy } = geom;

  useEffect(() => {
    if (phase === 'moving') {
      travel.value = withTiming(geom.exitDistance, { duration: exitMs, easing: EXIT_EASING }, (finished) => {
        if (finished) scheduleOnRN(onExited, id);
      });
      fade.value = withDelay(exitMs * 0.45, withTiming(0, { duration: exitMs * 0.55 }));
    } else {
      // Back to IDLE (initial mount, or Undo while still gliding).
      cancelAnimation(travel);
      cancelAnimation(fade);
      travel.value = 0;
      fade.value = 1;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [phase]);

  useEffect(() => {
    if (shakeSeq <= 0) return;
    const a = Math.max(3, cell * 0.16);
    shake.value = withSequence(
      withTiming(a, { duration: 55 }),
      withTiming(-a * 0.55, { duration: 70 }),
      withTiming(a * 0.25, { duration: 45 }),
      withTiming(0, { duration: 40 }),
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [shakeSeq]);

  useEffect(() => {
    cancelAnimation(glow);
    if (pulse && !reducedEffects) {
      glow.value = 1;
      // Six half-cycles (about four seconds), ending fully visible.
      glow.value = withRepeat(withTiming(0.35, { duration: 700 }), 6, true);
    } else {
      glow.value = 1;
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [pulse, reducedEffects]);

  const animated = useAnimatedStyle(() => {
    const d = travel.value + shake.value;
    return {
      opacity: fade.value * glow.value,
      transform: [{ translateX: dx * d }, { translateY: dy * d }],
    };
  });

  const color = TONE_COLOR[tone];
  return (
    <Animated.View
      pointerEvents="none"
      renderToHardwareTextureAndroid={phase === 'moving'}
      style={[styles.box, { left: geom.left, top: geom.top, width: geom.width, height: geom.height }, animated]}
    >
      <Svg width={geom.width} height={geom.height}>
        <Path
          d={geom.body}
          stroke={color}
          strokeWidth={geom.strokeWidth}
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
        <Path d={geom.head} fill={color} stroke={color} strokeWidth={geom.strokeWidth * 0.5} strokeLinejoin="round" />
      </Svg>
    </Animated.View>
  );
});

const styles = StyleSheet.create({
  box: { position: 'absolute' },
});
