import { memo, useEffect, useRef, type ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View, type StyleProp, type ViewStyle } from 'react-native';
import Animated, {
  Easing,
  FadeIn,
  FadeInDown,
  FadeOut,
  interpolateColor,
  useAnimatedStyle,
  useSharedValue,
  withSequence,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import { playSfx } from '../services/audio';
import { Icon, type IconName } from './Icon';
import { RADIUS, SPACE, useTheme } from './theme';

/** Pressable with a quick scale-down on touch (runs on the UI thread). */
export const Pressy = memo(function Pressy({
  onPress,
  style,
  children,
  disabled,
  sound = true,
  label,
  containerStyle,
}: {
  onPress: () => void;
  style?: StyleProp<ViewStyle>;
  /** Style for the outer touch area (e.g. flex: 1 inside a grid cell). */
  containerStyle?: StyleProp<ViewStyle>;
  children: ReactNode;
  disabled?: boolean;
  sound?: boolean;
  label?: string;
}) {
  const sc = useSharedValue(1);
  const st = useAnimatedStyle(() => ({ transform: [{ scale: sc.value }] }));
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={label}
      disabled={disabled}
      hitSlop={6}
      style={containerStyle}
      onPressIn={() => {
        sc.value = withTiming(0.94, { duration: 80 });
      }}
      onPressOut={() => {
        sc.value = withSpring(1, { damping: 14, stiffness: 320 });
      }}
      onPress={() => {
        if (sound) playSfx('tap');
        onPress();
      }}
    >
      <Animated.View style={[style, st, disabled && styles.disabled]}>{children}</Animated.View>
    </Pressable>
  );
});

export const Btn = memo(function Btn({
  label,
  onPress,
  icon,
  kind = 'primary',
  style,
  disabled,
}: {
  label: string;
  onPress: () => void;
  icon?: IconName;
  kind?: 'primary' | 'secondary' | 'gold';
  style?: StyleProp<ViewStyle>;
  disabled?: boolean;
}) {
  const t = useTheme();
  const bg = kind === 'primary' ? t.accent : kind === 'gold' ? t.gold : t.surface;
  const fg = kind === 'secondary' ? t.text : t.onAccent;
  return (
    <Pressy
      onPress={onPress}
      disabled={disabled}
      label={label}
      style={[styles.btn, { backgroundColor: bg, borderColor: kind === 'secondary' ? t.border : bg }, style]}
    >
      {icon ? <Icon name={icon} size={20} color={fg} filled={icon === 'play'} /> : null}
      <Text style={[styles.btnText, { color: fg }]} numberOfLines={1}>
        {label}
      </Text>
    </Pressy>
  );
});

export const RoundBtn = memo(function RoundBtn({
  icon,
  onPress,
  label,
  badge,
  size = 48,
  tint,
  bg,
  filled,
}: {
  icon: IconName;
  onPress: () => void;
  label: string;
  badge?: string | number;
  size?: number;
  tint?: string;
  bg?: string;
  filled?: boolean;
}) {
  const t = useTheme();
  return (
    <Pressy
      onPress={onPress}
      label={label}
      style={[
        styles.round,
        { width: size, height: size, borderRadius: size / 2, backgroundColor: bg ?? t.surface, borderColor: t.border },
      ]}
    >
      <Icon name={icon} size={Math.round(size * 0.48)} color={tint ?? t.text} filled={filled} />
      {badge !== undefined ? (
        <View style={[styles.badge, { backgroundColor: t.accent, borderColor: t.bg }]}>
          <Text style={styles.badgeText}>{badge}</Text>
        </View>
      ) : null}
    </Pressy>
  );
});

/** On/off switch with an animated knob. */
export const Toggle = memo(function Toggle({ value, onChange, label, icon }: { value: boolean; onChange: (v: boolean) => void; label: string; icon: IconName }) {
  const t = useTheme();
  const p = useSharedValue(value ? 1 : 0);
  useEffect(() => {
    p.value = withTiming(value ? 1 : 0, { duration: 170, easing: Easing.out(Easing.quad) });
  }, [value, p]);
  const track = useAnimatedStyle(() => ({ backgroundColor: interpolateColor(p.value, [0, 1], [t.surfaceAlt, t.accent]) }));
  const knob = useAnimatedStyle(() => ({ transform: [{ translateX: p.value * 20 }] }));
  return (
    <Pressable
      accessibilityRole="switch"
      accessibilityState={{ checked: value }}
      accessibilityLabel={label}
      onPress={() => {
        playSfx('tap');
        onChange(!value);
      }}
      style={styles.toggleRow}
    >
      <Icon name={icon} size={22} color={t.sub} />
      <Text style={[styles.toggleLabel, { color: t.text }]}>{label}</Text>
      <Animated.View style={[styles.track, track]}>
        <Animated.View style={[styles.knob, knob]} />
      </Animated.View>
    </Pressable>
  );
});

/** Lives. A heart that is lost pops and fades to grey. */
export const Hearts = memo(function Hearts({ count, max = 3, size = 26 }: { count: number; max?: number; size?: number }) {
  const items = [];
  for (let i = 0; i < max; i++) items.push(<HeartPip key={i} full={i < count} size={size} />);
  return <View style={styles.hearts}>{items}</View>;
});

const HeartPip = memo(function HeartPip({ full, size }: { full: boolean; size: number }) {
  const t = useTheme();
  const sc = useSharedValue(1);
  const first = useRef(true);
  useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    sc.value = withSequence(withTiming(full ? 1.25 : 1.45, { duration: 110 }), withSpring(1, { damping: 9, stiffness: 260 }));
  }, [full, sc]);
  const st = useAnimatedStyle(() => ({ transform: [{ scale: sc.value }] }));
  return (
    <Animated.View style={st}>
      <Icon name="heart" size={size} color={full ? t.heart : t.heartEmpty} filled />
    </Animated.View>
  );
});

/** Thin progress bar; the fill grows with a transform (no layout per frame). */
export const ProgressBar = memo(function ProgressBar({ value, color, track, height = 6 }: { value: number; color: string; track: string; height?: number }) {
  const p = useSharedValue(value);
  useEffect(() => {
    p.value = withTiming(Math.max(0, Math.min(1, value)), { duration: 260, easing: Easing.out(Easing.quad) });
  }, [value, p]);
  const st = useAnimatedStyle(() => ({ transform: [{ scaleX: p.value }] }));
  return (
    <View style={[styles.bar, { height, borderRadius: height / 2, backgroundColor: track }]}>
      <Animated.View style={[StyleSheet.absoluteFill, { backgroundColor: color, borderRadius: height / 2, transformOrigin: '0% 50%' }, st]} />
    </View>
  );
});

/** Centered dialog with a dimmed backdrop. Render it only while open. */
export function Sheet({ children, onBackdrop }: { children: ReactNode; onBackdrop?: () => void }) {
  const t = useTheme();
  return (
    <Animated.View entering={FadeIn.duration(160)} exiting={FadeOut.duration(140)} style={[StyleSheet.absoluteFill, styles.sheetWrap]}>
      <Pressable style={[StyleSheet.absoluteFill, { backgroundColor: t.scrim }]} onPress={onBackdrop} accessibilityLabel="Close" />
      <Animated.View entering={FadeInDown.duration(260).easing(Easing.out(Easing.cubic))} style={[styles.sheet, { backgroundColor: t.surface }]}>
        {children}
      </Animated.View>
    </Animated.View>
  );
}

export const styles = StyleSheet.create({
  disabled: { opacity: 0.45 },
  btn: {
    height: 56,
    borderRadius: RADIUS.pill,
    paddingHorizontal: SPACE.xl,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: SPACE.sm,
    borderWidth: 1.5,
  },
  btnText: { fontSize: 18, fontWeight: '700', letterSpacing: 0.2 },
  round: { alignItems: 'center', justifyContent: 'center', borderWidth: 1 },
  badge: {
    position: 'absolute',
    top: -4,
    right: -4,
    minWidth: 22,
    height: 22,
    borderRadius: 11,
    paddingHorizontal: 5,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 2,
  },
  badgeText: { color: '#fff', fontSize: 12, fontWeight: '800' },
  toggleRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, gap: SPACE.md },
  toggleLabel: { flex: 1, fontSize: 17, fontWeight: '600' },
  track: { width: 48, height: 28, borderRadius: 14, padding: 3 },
  knob: { width: 22, height: 22, borderRadius: 11, backgroundColor: '#fff' },
  hearts: { flexDirection: 'row', gap: 6, alignItems: 'center' },
  bar: { width: '100%', overflow: 'hidden' },
  sheetWrap: { alignItems: 'center', justifyContent: 'center', padding: SPACE.xl, zIndex: 50, elevation: 50 },
  sheet: { width: '100%', maxWidth: 400, borderRadius: RADIUS.xl, padding: SPACE.xl, alignItems: 'stretch', gap: SPACE.md },
});
